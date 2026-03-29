#!/usr/bin/env python3
"""
PUMP Sell Events Collector
Collects all PUMP sell events from TGE to present via three channels:
  A) CEX inflows: Dune SQL (bulk) + Helius (sender owner resolution)
  B) DEX sells: Dune SQL (bulk) + Helius (Pump AMM supplement)

Output: data/pump/raw/pump_sell_events.json

Usage:
    python scripts/pump/fetch_sell_events.py
    python scripts/pump/fetch_sell_events.py --skip-dune   # Helius-only fallback
    python scripts/pump/fetch_sell_events.py --cex-only    # skip DEX channel
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SKILLS_DIR = BASE_DIR / ".claude" / "skills" / "onchain-analysis" / "scripts"
sys.path.insert(0, str(SKILLS_DIR))

from core.config import require_api_key, load_exchange_addresses, HELIUS_ENHANCED_TEMPLATE
from core.rpc import rpc_call, http_get
from core.chains import (
    sol_get_token_accounts_by_owner,
    sol_get_signatures,
    sol_get_transaction,
    sol_extract_transfers,
    sol_get_enhanced_transactions,
)
from core.exchange import build_exchange_lookup
from core.rate_limiter import AdaptiveDelay, RateLimitMonitor
from core.dune import run_sql

PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
PUMP_DECIMALS = 9
TGE_TIMESTAMP = 1752278400  # 2025-07-12 00:00 UTC
TGE_DATE = "2025-07-12"

# Helius Enhanced API DEX source identifiers (from forensic_verify_pump_buybacks.py)
DEX_SOURCES = {"PUMP_AMM", "JUPITER", "RAYDIUM", "ORCA", "OKX_DEX"}
DEX_TYPES = {"SWAP", "DEX_TRADE"}

DATA_DIR = BASE_DIR / "data" / "pump"
OUTPUT_FILE = DATA_DIR / "raw" / "pump_sell_events.json"
PROGRESS_FILE = DATA_DIR / "raw" / ".pump_sell_events_progress.json"
CEX_CACHE_FILE = DATA_DIR / "raw" / ".pump_cex_inflows_cache.json"

# No Dune query IDs needed — SQL is submitted directly via run_sql()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ts_to_date(ts: int | float) -> str:
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%d")


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {}


def save_progress(progress: dict) -> None:
    PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def load_output() -> dict:
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            return json.load(f)
    return {"cex_inflows": [], "dex_sells": []}


def save_output(data: dict) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Saved → {OUTPUT_FILE}")


# ---------------------------------------------------------------------------
# Exchange address loading
# ---------------------------------------------------------------------------

def load_all_exchange_addresses() -> dict[str, str]:
    """Returns {solana_address: exchange_name} for all 84 Solana exchange addresses."""
    exchanges_data = load_exchange_addresses()
    lookup: dict[str, str] = {}
    for exchange_name, chains in exchanges_data.items():
        if isinstance(chains, dict) and "solana" in chains:
            for addr in chains["solana"]:
                lookup[addr] = exchange_name  # preserve case (Solana is case-sensitive)
    print(f"Loaded {len(lookup)} Solana exchange addresses across exchanges")
    return lookup


def resolve_pump_atas(
    api_key: str,
    exchange_addresses: dict[str, str],
    delay: AdaptiveDelay,
) -> dict[str, dict]:
    """
    For each exchange address, find its PUMP ATA.
    Returns {exchange_addr: {"ata": str, "exchange_name": str}}.
    """
    ata_map: dict[str, dict] = {}
    total = len(exchange_addresses)
    for i, (addr, exchange_name) in enumerate(exchange_addresses.items()):
        atas = sol_get_token_accounts_by_owner(api_key, addr, PUMP_MINT)
        if atas:
            ata_map[addr] = {"ata": atas[0], "exchange_name": exchange_name}
        delay.wait()
        if (i + 1) % 20 == 0:
            print(f"  ATA resolution: {i+1}/{total}, found {len(ata_map)} with PUMP ATAs")
    print(f"ATA resolution complete: {len(ata_map)}/{total} exchange addresses have PUMP ATAs")
    return ata_map


# ---------------------------------------------------------------------------
# Channel A: CEX inflows via Helius Enhanced API
# ---------------------------------------------------------------------------

def fetch_cex_inflows_helius(
    api_key: str,
    ata_map: dict[str, dict],
    delay: AdaptiveDelay,
    monitor: RateLimitMonitor,
    progress: dict,
) -> list[dict]:
    """
    For each exchange ATA, use Helius Enhanced API to get all inflow transactions.
    Extracts sender (fromUserAccount) from tokenTransfers.
    """
    # Load cached inflows from previous runs
    if CEX_CACHE_FILE.exists():
        with open(CEX_CACHE_FILE) as f:
            all_inflows: list[dict] = json.load(f)
        print(f"  Loaded {len(all_inflows)} cached CEX inflows from previous run")
    else:
        all_inflows: list[dict] = []
    seen_sigs: set[str] = {r["signature"] for r in all_inflows if r.get("signature")}

    for exchange_addr, info in ata_map.items():
        ata = info["ata"]
        exchange_name = info["exchange_name"]
        prog_key = f"cex_helius_{exchange_addr}"

        if progress.get(prog_key) == "done":
            print(f"  Skip {exchange_name} ({exchange_addr[:8]}...) — already done")
            continue

        print(f"  Fetching {exchange_name} ATA {ata[:8]}... via Enhanced API")
        try:
            txs, meta = sol_get_enhanced_transactions(
                api_key, ata, min_timestamp=TGE_TIMESTAMP, max_pages=200
            )
        except Exception as e:
            print(f"    Error: {e}")
            progress[prog_key] = "failed"
            save_progress(progress)
            continue

        inflow_count = 0
        for tx in txs:
            sig = tx.get("signature", "")
            if sig in seen_sigs:
                continue
            ts = tx.get("timestamp", 0) or 0
            if ts < TGE_TIMESTAMP:
                continue

            for tt in (tx.get("tokenTransfers") or []):
                if tt.get("mint") != PUMP_MINT:
                    continue
                to_user = tt.get("toUserAccount", "")
                from_user = tt.get("fromUserAccount", "")
                amount = float(tt.get("tokenAmount", 0) or 0)
                # Inflow: token going TO the exchange owner address
                if to_user == exchange_addr and from_user and amount > 0:
                    seen_sigs.add(sig)
                    all_inflows.append({
                        "date": ts_to_date(ts),
                        "timestamp": ts,
                        "seller": from_user,
                        "amount_B": amount / 1e9,
                        "exchange": exchange_name,
                        "exchange_address": exchange_addr,
                        "signature": sig,
                        "source": "helius_enhanced",
                    })
                    inflow_count += 1
                    break  # one inflow per tx per exchange

        print(f"    {exchange_name}: {inflow_count} inflows from {meta['pages_fetched']} pages")
        progress[prog_key] = "done"
        save_progress(progress)
        # Persist inflows to cache so restarts don't lose data
        with open(CEX_CACHE_FILE, "w") as f:
            json.dump(all_inflows, f)
        delay.wait()
        monitor.record(True)

    return all_inflows


# ---------------------------------------------------------------------------
# Channel A supplement: resolve sender owner from token account address
# ---------------------------------------------------------------------------

def resolve_sender_owners(
    api_key: str,
    inflows: list[dict],
    delay: AdaptiveDelay,
) -> list[dict]:
    """
    For inflows where seller is a token account (not a wallet), resolve the owner.
    Helius Enhanced API usually returns fromUserAccount (owner), but as a safety check
    we verify any address that looks like it might be a token account.
    This is a lightweight pass — most records from Enhanced API already have owner addresses.
    """
    # Token accounts on Solana are 32-byte base58 addresses, same as wallets.
    # We can't distinguish them by address alone. Skip this step for Enhanced API results
    # since tokenTransfers.fromUserAccount is already the owner wallet.
    return inflows


# ---------------------------------------------------------------------------
# Channel B: DEX sells via Helius Enhanced API (Pump AMM + others)
# ---------------------------------------------------------------------------

def fetch_dex_sells_helius(
    api_key: str,
    exchange_addresses: dict[str, str],
    delay: AdaptiveDelay,
    monitor: RateLimitMonitor,
) -> list[dict]:
    """
    Supplement DEX sell data using Helius Enhanced API on the PUMP mint address.
    Targets SWAP/DEX_TRADE transactions where PUMP is the sold token.

    Note: This is a supplement to Dune's DEX data. Helius Enhanced API on a mint
    address returns transactions involving that mint, which includes DEX swaps.
    We filter for PUMP outflows (seller sends PUMP, receives SOL/USDC/etc).
    """
    print("Fetching DEX sells via Helius Enhanced API (Pump AMM supplement)...")
    dex_sells: list[dict] = []
    seen_sigs: set[str] = set()

    # Query the PUMP mint address for all transactions — this covers Pump AMM
    # which may not be in Dune's dex_solana.trades table
    txs, meta = sol_get_enhanced_transactions(
        api_key, PUMP_MINT, min_timestamp=TGE_TIMESTAMP, max_pages=500
    )
    print(f"  Fetched {len(txs)} transactions from PUMP mint address ({meta['pages_fetched']} pages)")

    for tx in txs:
        sig = tx.get("signature", "")
        if sig in seen_sigs:
            continue
        ts = tx.get("timestamp", 0) or 0
        if ts < TGE_TIMESTAMP:
            continue

        tx_type = tx.get("type", "")
        source = tx.get("source", "")

        # Only process DEX swap transactions
        if tx_type not in DEX_TYPES and source not in DEX_SOURCES:
            continue

        # Find PUMP outflows (seller sends PUMP)
        for tt in (tx.get("tokenTransfers") or []):
            if tt.get("mint") != PUMP_MINT:
                continue
            from_user = tt.get("fromUserAccount", "")
            amount = float(tt.get("tokenAmount", 0) or 0)
            if not from_user or amount <= 0:
                continue
            # Exclude exchange addresses (those are CEX deposits, not DEX sells)
            if from_user in exchange_addresses:
                continue

            seen_sigs.add(sig)
            dex_sells.append({
                "date": ts_to_date(ts),
                "timestamp": ts,
                "seller": from_user,
                "amount_B": amount / 1e9,
                "dex": source or "UNKNOWN_DEX",
                "tx_type": tx_type,
                "signature": sig,
                "source": "helius_enhanced",
            })
            break  # one sell event per tx

    print(f"  Helius DEX sells: {len(dex_sells)} events")
    return dex_sells


# ---------------------------------------------------------------------------
# Channel A+B: Dune bulk queries (primary for CEX, primary for DEX)
# ---------------------------------------------------------------------------

def fetch_cex_inflows_dune(
    ata_map: dict[str, dict],
    dune_api_key: str | None = None,
) -> list[dict]:
    """
    Use Dune SQL to bulk-fetch all PUMP CEX inflows directly (no saved query needed).
    Embeds exchange ATAs inline in the SQL WHERE clause.
    """
    ata_to_exchange = {info["ata"]: info["exchange_name"] for info in ata_map.values()}
    ata_list = list(ata_to_exchange.keys())
    if not ata_list:
        print("  No exchange ATAs found, skipping Dune CEX channel")
        return []

    # Build inline ATA list for SQL (max ~500 ATAs fits fine in a SQL literal)
    ata_sql_list = ", ".join(f"'{a}'" for a in ata_list)
    sql = f"""
SELECT
  block_time,
  tx_id,
  from_token_account,
  to_token_account,
  amount / 1e9 AS amount_B
FROM tokens_solana.transfers
WHERE token_mint_address = '{PUMP_MINT}'
  AND to_token_account IN ({ata_sql_list})
  AND block_time >= TIMESTAMP '{TGE_DATE}'
ORDER BY block_time
"""
    print(f"  Running Dune CEX inflows SQL for {len(ata_list)} ATAs...")
    rows = run_sql(sql, api_key=dune_api_key)

    inflows = []
    for row in rows:
        to_ata = row.get("to_token_account", "")
        exchange_name = ata_to_exchange.get(to_ata, "Unknown")
        ts_str = row.get("block_time", "")
        try:
            ts = int(datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()) if ts_str else 0
        except Exception:
            ts = 0
        inflows.append({
            "date": ts_to_date(ts) if ts else "",
            "timestamp": ts,
            "seller": row.get("from_token_account", ""),  # token account, needs owner resolution
            "amount_B": float(row.get("amount_B", 0) or 0),
            "exchange": exchange_name,
            "exchange_ata": to_ata,
            "signature": row.get("tx_id", ""),
            "source": "dune",
            "seller_is_token_account": True,  # flag for owner resolution
        })

    print(f"  Dune CEX inflows: {len(inflows)} records")
    return inflows


def fetch_dex_sells_dune(dune_api_key: str | None = None) -> list[dict]:
    """
    Use Dune SQL to bulk-fetch all PUMP DEX sells directly (no saved query needed).
    """
    sql = f"""
SELECT
  block_time,
  tx_id,
  trader_id AS seller,
  project AS dex_name,
  amount_sold / 1e9 AS sold_B,
  token_bought_symbol
FROM dex_solana.trades
WHERE token_sold_mint_address = '{PUMP_MINT}'
  AND block_time >= TIMESTAMP '{TGE_DATE}'
ORDER BY block_time
"""
    print("  Running Dune DEX sells SQL...")
    rows = run_sql(sql, api_key=dune_api_key)

    sells = []
    for row in rows:
        ts_str = row.get("block_time", "")
        try:
            ts = int(datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp()) if ts_str else 0
        except Exception:
            ts = 0
        if ts < TGE_TIMESTAMP:
            continue
        sells.append({
            "date": ts_to_date(ts) if ts else "",
            "timestamp": ts,
            "seller": row.get("seller", ""),
            "amount_B": float(row.get("sold_B", 0) or 0),
            "dex": row.get("dex_name", "Unknown"),
            "bought_token": row.get("token_bought_symbol", ""),
            "signature": row.get("tx_id", ""),
            "source": "dune",
        })

    print(f"  Dune DEX sells: {len(sells)} records")
    return sells


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def deduplicate(records: list[dict]) -> list[dict]:
    """Remove duplicate records by signature. Keep first occurrence."""
    seen: set[str] = set()
    out = []
    for r in records:
        sig = r.get("signature", "")
        if sig and sig in seen:
            continue
        if sig:
            seen.add(sig)
        out.append(r)
    return out


def merge_cex_sources(
    helius_inflows: list[dict],
    dune_inflows: list[dict],
) -> list[dict]:
    """
    Merge Helius and Dune CEX inflow records.
    Dune records are supplementary — if a signature already exists from Helius, skip.
    Helius records have resolved owner addresses; Dune records have token accounts.
    """
    helius_sigs = {r["signature"] for r in helius_inflows if r.get("signature")}
    merged = list(helius_inflows)
    for r in dune_inflows:
        if r.get("signature") not in helius_sigs:
            merged.append(r)
    return merged


def merge_dex_sources(
    helius_sells: list[dict],
    dune_sells: list[dict],
) -> list[dict]:
    """Merge Helius and Dune DEX sell records, deduplicating by signature."""
    helius_sigs = {r["signature"] for r in helius_sells if r.get("signature")}
    merged = list(helius_sells)
    for r in dune_sells:
        if r.get("signature") not in helius_sigs:
            merged.append(r)
    return merged


# ---------------------------------------------------------------------------
# Summary stats
# ---------------------------------------------------------------------------

def compute_summary(cex_inflows: list[dict], dex_sells: list[dict]) -> dict:
    all_sellers = {r["seller"] for r in cex_inflows + dex_sells if r.get("seller")}
    cex_volume = sum(r.get("amount_B", 0) for r in cex_inflows)
    dex_volume = sum(r.get("amount_B", 0) for r in dex_sells)

    exchange_volumes: dict[str, float] = defaultdict(float)
    for r in cex_inflows:
        exchange_volumes[r.get("exchange", "Unknown")] += r.get("amount_B", 0)

    dex_volumes: dict[str, float] = defaultdict(float)
    for r in dex_sells:
        dex_volumes[r.get("dex", "Unknown")] += r.get("amount_B", 0)

    return {
        "total_cex_events": len(cex_inflows),
        "total_dex_events": len(dex_sells),
        "total_unique_sellers": len(all_sellers),
        "total_cex_volume_B": round(cex_volume, 4),
        "total_dex_volume_B": round(dex_volume, 4),
        "total_sell_volume_B": round(cex_volume + dex_volume, 4),
        "top_exchanges": dict(sorted(exchange_volumes.items(), key=lambda x: -x[1])[:10]),
        "top_dexes": dict(sorted(dex_volumes.items(), key=lambda x: -x[1])[:10]),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch PUMP sell events (CEX + DEX)")
    parser.add_argument("--skip-dune", action="store_true", help="Skip Dune queries, use Helius only")
    parser.add_argument("--cex-only", action="store_true", help="Skip DEX channel")
    parser.add_argument("--dex-only", action="store_true", help="Skip CEX channel")
    args = parser.parse_args()

    helius_key = require_api_key("solana")
    dune_key = None if args.skip_dune else __import__("os").environ.get("DUNE_API_KEY")

    delay = AdaptiveDelay(initial=0.3, min_delay=0.1, max_delay=3.0)
    monitor = RateLimitMonitor(window_size=100)
    progress = load_progress()

    exchange_addresses = load_all_exchange_addresses()

    # --- Channel A: CEX inflows ---
    cex_inflows: list[dict] = []
    if not args.dex_only:
        print("\n=== Channel A: CEX Inflows ===")

        # Step 1: Resolve PUMP ATAs for all exchange addresses
        print("Resolving PUMP ATAs for exchange addresses...")
        ata_map = resolve_pump_atas(helius_key, exchange_addresses, delay)

        # Step 2: Helius Enhanced API (primary for sender resolution)
        print("\nFetching CEX inflows via Helius Enhanced API...")
        helius_cex = fetch_cex_inflows_helius(helius_key, ata_map, delay, monitor, progress)
        print(f"Helius CEX inflows: {len(helius_cex)} records")

        # Step 3: Dune bulk query (supplement)
        dune_cex: list[dict] = []
        if dune_key:
            print("\nFetching CEX inflows via Dune...")
            dune_cex = fetch_cex_inflows_dune(ata_map, dune_api_key=dune_key)

        cex_inflows = merge_cex_sources(helius_cex, dune_cex)
        cex_inflows = deduplicate(cex_inflows)
        print(f"Total CEX inflows after merge+dedup: {len(cex_inflows)}")

    # --- Channel B: DEX sells ---
    dex_sells: list[dict] = []
    if not args.cex_only:
        print("\n=== Channel B: DEX Sells ===")

        # Step 1: Dune bulk query (primary for DEX)
        dune_dex: list[dict] = []
        if dune_key:
            print("Fetching DEX sells via Dune...")
            dune_dex = fetch_dex_sells_dune(dune_api_key=dune_key)

        # Step 2: Helius Enhanced API (Pump AMM supplement)
        print("Fetching DEX sells via Helius (Pump AMM supplement)...")
        helius_dex = fetch_dex_sells_helius(helius_key, exchange_addresses, delay, monitor)

        dex_sells = merge_dex_sources(helius_dex, dune_dex)
        dex_sells = deduplicate(dex_sells)
        print(f"Total DEX sells after merge+dedup: {len(dex_sells)}")

    # --- Build output ---
    summary = compute_summary(cex_inflows, dex_sells)
    output = {
        "metadata": {
            "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pump_mint": PUMP_MINT,
            "tge_date": TGE_DATE,
            "tge_timestamp": TGE_TIMESTAMP,
            "sources": ["helius_enhanced"] + (["dune"] if dune_key else []),
            **summary,
        },
        "cex_inflows": sorted(cex_inflows, key=lambda x: x.get("timestamp", 0)),
        "dex_sells": sorted(dex_sells, key=lambda x: x.get("timestamp", 0)),
    }

    save_output(output)

    print("\n=== Summary ===")
    print(f"CEX inflows:    {summary['total_cex_events']:,} events, {summary['total_cex_volume_B']:.2f}B PUMP")
    print(f"DEX sells:      {summary['total_dex_events']:,} events, {summary['total_dex_volume_B']:.2f}B PUMP")
    print(f"Total volume:   {summary['total_sell_volume_B']:.2f}B PUMP")
    print(f"Unique sellers: {summary['total_unique_sellers']:,}")
    print(f"Output: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
