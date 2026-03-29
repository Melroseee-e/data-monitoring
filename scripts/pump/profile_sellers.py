#!/usr/bin/env python3
"""
PUMP Seller Profiler
Builds a two-source profile for every unique seller found in pump_sell_events.json:
  - Helius: current balance, account type, first PUMP receipt, upstream 1-hop
  - Dune:   batch historical stats (first activity, total txs, total transferred)
  - Local:  entity labels from pump_addresses.json + exchange_addresses_normalized.json

Output: data/pump/raw/pump_seller_profiles.json

Usage:
    python scripts/pump/profile_sellers.py
    python scripts/pump/profile_sellers.py --top 500   # profile top N sellers only
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

from core.config import require_api_key
from core.chains import (
    sol_get_token_accounts_by_owner,
    sol_get_account_info,
    sol_get_signatures,
    sol_get_transaction,
    sol_get_enhanced_transactions,
)
from core.rate_limiter import AdaptiveDelay, RateLimitMonitor
from core.config import load_exchange_addresses

PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
TGE_TIMESTAMP = 1752278400  # 2025-07-12 00:00 UTC
TOKEN_CUSTODIAN = "Cfq1ts1iFr1eUWWBm8eFxUzm5R3YA3UvMZznwiShbgZt"
SQUADS_V4_PROGRAM = "SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf"
SYSTEM_PROGRAM = "11111111111111111111111111111111"

DATA_DIR = BASE_DIR / "data" / "pump"
INPUT_FILE = DATA_DIR / "raw" / "pump_sell_events.json"
ADDRESSES_FILE = DATA_DIR / "core" / "pump_addresses.json"
OUTPUT_FILE = DATA_DIR / "raw" / "pump_seller_profiles.json"
PROGRESS_FILE = DATA_DIR / "raw" / ".pump_seller_profiles_progress.json"

DEX_SOURCES = {"PUMP_AMM", "JUPITER", "RAYDIUM", "ORCA", "OKX_DEX"}
DEX_TYPES = {"SWAP", "DEX_TRADE"}


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
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def load_existing_profiles() -> dict:
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            data = json.load(f)
            return data.get("sellers", {})
    return {}


def save_profiles(sellers: dict, summary: dict) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump({
            "metadata": {
                "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "total_sellers": len(sellers),
                **summary,
            },
            "sellers": sellers,
        }, f, ensure_ascii=False, indent=2)
    print(f"  Saved {len(sellers)} profiles → {OUTPUT_FILE}")


def load_known_addresses() -> dict[str, dict]:
    """Load pump_addresses.json → {address: {label, type}}"""
    if not ADDRESSES_FILE.exists():
        return {}
    with open(ADDRESSES_FILE) as f:
        data = json.load(f)
    return data.get("addresses", {})


def build_local_entity_lookup() -> dict[str, dict]:
    """
    Build a combined entity label lookup from local sources:
      1. pump_addresses.json  — team/investor/vesting/treasury/buyback labels
      2. exchange_addresses_normalized.json — exchange name labels

    Returns {address: {"name": str, "type": str, "has_entity": True}}
    """
    lookup: dict[str, dict] = {}

    # Source 1: pump_addresses.json
    known = load_known_addresses()
    for addr, info in known.items():
        lookup[addr] = {
            "name": info.get("label", addr[:8] + "..."),
            "type": info.get("type", "unknown"),
            "has_entity": True,
        }

    # Source 2: exchange addresses
    try:
        exchanges_data = load_exchange_addresses()
        for exchange_name, chains in exchanges_data.items():
            if isinstance(chains, dict) and "solana" in chains:
                for addr in chains["solana"]:
                    if addr not in lookup:
                        lookup[addr] = {
                            "name": exchange_name,
                            "type": "exchange",
                            "has_entity": True,
                        }
    except Exception:
        pass

    return lookup


# ---------------------------------------------------------------------------
# Step 1: Aggregate sell events by seller
# ---------------------------------------------------------------------------

def aggregate_sellers(events_data: dict) -> dict[str, dict]:
    """
    Group sell events by seller address.
    Returns {seller: {total_sell_B, cex_sell_B, dex_sell_B, exchanges, dexes,
                       first_sell_date, last_sell_date, sell_count, events}}
    """
    sellers: dict[str, dict] = defaultdict(lambda: {
        "total_sell_B": 0.0,
        "cex_sell_B": 0.0,
        "dex_sell_B": 0.0,
        "exchanges_used": set(),
        "dexes_used": set(),
        "first_sell_ts": None,
        "last_sell_ts": None,
        "sell_count": 0,
    })

    for r in events_data.get("cex_inflows", []):
        addr = r.get("seller", "")
        if not addr:
            continue
        s = sellers[addr]
        s["total_sell_B"] += r.get("amount_B", 0)
        s["cex_sell_B"] += r.get("amount_B", 0)
        s["exchanges_used"].add(r.get("exchange", "Unknown"))
        s["sell_count"] += 1
        ts = r.get("timestamp", 0)
        if ts:
            s["first_sell_ts"] = min(s["first_sell_ts"] or ts, ts)
            s["last_sell_ts"] = max(s["last_sell_ts"] or ts, ts)

    for r in events_data.get("dex_sells", []):
        addr = r.get("seller", "")
        if not addr:
            continue
        s = sellers[addr]
        s["total_sell_B"] += r.get("amount_B", 0)
        s["dex_sell_B"] += r.get("amount_B", 0)
        s["dexes_used"].add(r.get("dex", "Unknown"))
        s["sell_count"] += 1
        ts = r.get("timestamp", 0)
        if ts:
            s["first_sell_ts"] = min(s["first_sell_ts"] or ts, ts)
            s["last_sell_ts"] = max(s["last_sell_ts"] or ts, ts)

    # Convert sets to lists and add derived fields
    result = {}
    for addr, s in sellers.items():
        cex_b = s["cex_sell_B"]
        dex_b = s["dex_sell_B"]
        sell_type = "both" if cex_b > 0 and dex_b > 0 else ("cex_only" if cex_b > 0 else "dex_only")
        result[addr] = {
            "total_sell_B": round(s["total_sell_B"], 6),
            "cex_sell_B": round(cex_b, 6),
            "dex_sell_B": round(dex_b, 6),
            "sell_type": sell_type,
            "sell_count": s["sell_count"],
            "exchanges_used": sorted(s["exchanges_used"]),
            "dexes_used": sorted(s["dexes_used"]),
            "first_sell_date": ts_to_date(s["first_sell_ts"]) if s["first_sell_ts"] else None,
            "last_sell_date": ts_to_date(s["last_sell_ts"]) if s["last_sell_ts"] else None,
        }
    return result


def classify_size_tier(total_sell_B: float) -> str:
    if total_sell_B >= 10.0:
        return "Mega"
    if total_sell_B >= 1.0:
        return "Large"
    if total_sell_B >= 0.1:
        return "Medium"
    if total_sell_B >= 0.01:
        return "Small"
    return "Micro"


# ---------------------------------------------------------------------------
# Step 2: Helius — current balance
# ---------------------------------------------------------------------------

def fetch_current_balance(api_key: str, owner: str) -> float:
    """Get current PUMP balance for owner wallet. Returns amount in B (billions)."""
    atas = sol_get_token_accounts_by_owner(api_key, owner, PUMP_MINT)
    if not atas:
        return 0.0
    # Sum all ATAs (usually just one)
    total = 0.0
    for ata in atas:
        from core.chains import sol_get_token_balance
        bal = sol_get_token_balance(api_key, ata)
        if bal:
            ui = bal.get("uiAmount") or 0
            total += float(ui)
    return round(total / 1e9, 6)  # convert to billions


# ---------------------------------------------------------------------------
# Step 3: Helius — account type
# ---------------------------------------------------------------------------

def fetch_account_type(api_key: str, address: str) -> str:
    """
    Determine account type:
    - "multisig": owner is Squads v4 program
    - "program_owned": owner is not system program
    - "regular_wallet": owner is system program
    """
    info = sol_get_account_info(api_key, address)
    if not info:
        return "unknown"
    owner = ""
    data = info.get("data", {})
    if isinstance(data, dict):
        parsed = data.get("parsed", {})
        if isinstance(parsed, dict):
            owner = parsed.get("info", {}).get("owner", "")
    if not owner:
        owner = info.get("owner", "")
    if owner == SQUADS_V4_PROGRAM:
        return "multisig"
    if owner and owner != SYSTEM_PROGRAM:
        return "program_owned"
    return "regular_wallet"


# ---------------------------------------------------------------------------
# Step 4: Helius — first PUMP receipt
# ---------------------------------------------------------------------------

def fetch_first_pump_receipt(api_key: str, owner: str, delay: AdaptiveDelay) -> dict | None:
    """
    Find the earliest PUMP receipt for this owner.
    Strategy: get owner's PUMP ATA → paginate ALL signatures to find oldest →
    parse that tx to find who sent PUMP.
    Returns {date, timestamp, source_address, amount_B, signature} or None.
    """
    atas = sol_get_token_accounts_by_owner(api_key, owner, PUMP_MINT)
    if not atas:
        return None
    ata = atas[0]

    # Paginate to find the oldest signature
    oldest_sig = None
    oldest_ts = None
    before = None
    for _ in range(200):  # max 200 pages × 1000 = 200K sigs
        sigs = sol_get_signatures(api_key, ata, limit=1000, before=before)
        if not sigs:
            break
        # Signatures are returned newest-first; last item is oldest in this page
        last = sigs[-1]
        sig_ts = last.get("blockTime", 0) or 0
        if oldest_ts is None or sig_ts < oldest_ts:
            oldest_ts = sig_ts
            oldest_sig = last.get("signature")
        if len(sigs) < 1000:
            break  # last page
        before = last.get("signature")
        delay.wait()

    if not oldest_sig:
        return None

    # Parse the oldest transaction to find who sent PUMP
    tx = sol_get_transaction(api_key, oldest_sig)
    if not tx:
        return None

    transfers = []
    meta = tx.get("meta", {}) or {}
    tx_msg = tx.get("transaction", {}).get("message", {}) or {}
    # Try jsonParsed instructions first
    for instr in tx_msg.get("instructions", []):
        parsed = instr.get("parsed", {})
        if isinstance(parsed, dict) and parsed.get("type") == "transfer":
            info = parsed.get("info", {})
            if info.get("mint") == PUMP_MINT or info.get("destination") == ata:
                transfers.append({
                    "source": info.get("authority") or info.get("source", ""),
                    "amount_B": float(info.get("tokenAmount", {}).get("uiAmount", 0) or 0) / 1e9,
                })

    # Fallback: use pre/postTokenBalances
    if not transfers:
        from core.chains import sol_extract_transfers
        raw_transfers = sol_extract_transfers(tx, PUMP_MINT)
        for t in raw_transfers:
            if t.get("to_address") == owner:
                transfers.append({
                    "source": t.get("from_address", ""),
                    "amount_B": t.get("amount", 0) / (10 ** t.get("decimals", 9)) / 1e9,
                })

    source_addr = transfers[0]["source"] if transfers else ""
    amount_B = transfers[0]["amount_B"] if transfers else 0.0

    return {
        "date": ts_to_date(oldest_ts) if oldest_ts else None,
        "timestamp": oldest_ts,
        "source_address": source_addr,
        "amount_B": round(amount_B, 6),
        "signature": oldest_sig,
    }


# ---------------------------------------------------------------------------
# Step 5: Helius — upstream 1-hop (first N PUMP receipts)
# ---------------------------------------------------------------------------

def fetch_upstream_1hop(api_key: str, owner: str, limit: int = 10) -> list[dict]:
    """
    Get first `limit` PUMP-receiving transactions for this owner via Enhanced API.
    Returns [{source, amount_B, date, timestamp, tx_type, source_program}].
    Caps at 5 Enhanced API pages to avoid runaway on high-activity wallets.
    """
    txs, _ = sol_get_enhanced_transactions(
        api_key, owner, min_timestamp=TGE_TIMESTAMP, max_pages=5
    )

    receipts = []
    for tx in txs:
        for tt in (tx.get("tokenTransfers") or []):
            if tt.get("mint") != PUMP_MINT:
                continue
            to_user = tt.get("toUserAccount", "")
            from_user = tt.get("fromUserAccount", "")
            amount = float(tt.get("tokenAmount", 0) or 0)
            if to_user == owner and from_user and amount > 0:
                receipts.append({
                    "source": from_user,
                    "amount_B": round(amount / 1e9, 6),
                    "date": ts_to_date(tx.get("timestamp", 0)),
                    "timestamp": tx.get("timestamp", 0),
                    "tx_type": tx.get("type", ""),
                    "source_program": tx.get("source", ""),
                })
                if len(receipts) >= limit:
                    break
        if len(receipts) >= limit:
            break

    return receipts


# ---------------------------------------------------------------------------
# Step 6: Classify origin
# ---------------------------------------------------------------------------

def classify_origin(
    address: str,
    first_receipt: dict | None,
    upstream_1hop: list[dict],
    known_addresses: dict[str, dict],
) -> str:
    """
    Classify seller origin:
    - known type from pump_addresses.json (team/investor/vesting/insider/treasury)
    - tge_direct: first receipt from Token Custodian
    - tge_indirect: first receipt from a tge_direct address within 30 days of TGE
    - secondary_market: first receipt via DEX swap
    - unknown: cannot determine
    """
    if address in known_addresses:
        return known_addresses[address].get("type", "known")

    if first_receipt:
        source = first_receipt.get("source_address", "")
        receipt_ts = first_receipt.get("timestamp", 0) or 0

        if source == TOKEN_CUSTODIAN:
            return "tge_direct"

        # Check if source is itself a tge_direct address
        if source in known_addresses:
            src_type = known_addresses[source].get("type", "")
            if src_type in ("team", "investor", "vesting", "insider", "token_custodian"):
                return "tge_indirect"

        # Check if receipt was within 30 days of TGE and source is a known TGE recipient
        days_from_tge = (receipt_ts - TGE_TIMESTAMP) / 86400 if receipt_ts else 999
        if days_from_tge <= 30 and source:
            # Check upstream_1hop for custodian chain
            for hop in upstream_1hop:
                if hop.get("source") == TOKEN_CUSTODIAN:
                    return "tge_indirect"

    # Check if any upstream hop is a DEX swap
    for hop in upstream_1hop:
        if hop.get("tx_type") in DEX_TYPES or hop.get("source_program") in DEX_SOURCES:
            return "secondary_market"

    if first_receipt and first_receipt.get("source_address"):
        return "unknown"

    return "unknown"


# ---------------------------------------------------------------------------
# Main profiling loop
# ---------------------------------------------------------------------------

def profile_seller(
    api_key: str,
    address: str,
    sell_stats: dict,
    known_addresses: dict[str, dict],
    delay: AdaptiveDelay,
    monitor: RateLimitMonitor,
) -> dict:
    """Build complete profile for one seller address."""
    profile = dict(sell_stats)  # copy sell stats
    profile["address"] = address
    profile["size_tier"] = classify_size_tier(sell_stats["total_sell_B"])

    # Known address shortcut
    if address in known_addresses:
        known = known_addresses[address]
        profile["known_label"] = known.get("label")
        profile["origin"] = known.get("type", "known")
        profile["account_type"] = "multisig" if "Squads" in (known.get("label") or "") else "regular_wallet"
        profile["current_balance_B"] = known.get("balance", 0) / 1e9 if known.get("balance") else 0.0
        profile["first_pump_receipt"] = None
        profile["upstream_1hop"] = []
        return profile

    profile["known_label"] = None

    # Helius: current balance
    try:
        profile["current_balance_B"] = fetch_current_balance(api_key, address)
        delay.wait()
        monitor.record(True)
    except Exception as e:
        profile["current_balance_B"] = None
        monitor.record(False)

    # Helius: account type
    try:
        profile["account_type"] = fetch_account_type(api_key, address)
        delay.wait()
        monitor.record(True)
    except Exception as e:
        profile["account_type"] = "unknown"
        monitor.record(False)

    # Helius: first PUMP receipt
    try:
        profile["first_pump_receipt"] = fetch_first_pump_receipt(api_key, address, delay)
        monitor.record(True)
    except Exception as e:
        profile["first_pump_receipt"] = None
        monitor.record(False)

    # Helius: upstream 1-hop
    try:
        profile["upstream_1hop"] = fetch_upstream_1hop(api_key, address)
        delay.wait()
        monitor.record(True)
    except Exception as e:
        profile["upstream_1hop"] = []
        monitor.record(False)

    # Classify origin
    profile["origin"] = classify_origin(
        address,
        profile.get("first_pump_receipt"),
        profile.get("upstream_1hop", []),
        known_addresses,
    )

    return profile


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Profile PUMP sellers (Helius + Dune + local labels)")
    parser.add_argument("--top", type=int, default=0, help="Profile only top N sellers by volume (0 = all)")
    parser.add_argument("--skip-helius", action="store_true", help="Skip Helius API calls, use local labels only")
    args = parser.parse_args()

    helius_key = None if args.skip_helius else require_api_key("solana")

    delay = AdaptiveDelay(initial=0.3, min_delay=0.1, max_delay=3.0)
    monitor = RateLimitMonitor(window_size=100)

    # Load inputs
    if not INPUT_FILE.exists():
        print(f"ERROR: {INPUT_FILE} not found. Run fetch_sell_events.py first.", file=sys.stderr)
        sys.exit(1)
    with open(INPUT_FILE) as f:
        events_data = json.load(f)

    known_addresses = load_known_addresses()
    print(f"Loaded {len(known_addresses)} known addresses")

    # Aggregate sellers
    print("Aggregating sell events by seller...")
    all_sellers = aggregate_sellers(events_data)
    print(f"Found {len(all_sellers)} unique sellers")

    # Sort by total sell volume, optionally limit
    sorted_sellers = sorted(all_sellers.items(), key=lambda x: -x[1]["total_sell_B"])
    if args.top:
        sorted_sellers = sorted_sellers[:args.top]
        print(f"Profiling top {args.top} sellers by volume")

    # Load existing profiles for resume
    existing_profiles = load_existing_profiles()
    progress = load_progress()
    print(f"Resuming: {len(existing_profiles)} profiles already done")

    sellers_out: dict[str, dict] = dict(existing_profiles)

    # Profile each seller
    total = len(sorted_sellers)
    for i, (address, sell_stats) in enumerate(sorted_sellers):
        if address in existing_profiles:
            continue

        if args.skip_helius:
            # Fast path: local classification only
            profile = dict(sell_stats)
            profile["address"] = address
            profile["size_tier"] = classify_size_tier(sell_stats["total_sell_B"])

            # Known address shortcut
            if address in known_addresses:
                known = known_addresses[address]
                profile["known_label"] = known.get("label")
                profile["origin"] = known.get("type", "known")
                profile["account_type"] = "multisig" if "Squads" in (known.get("label") or "") else "regular_wallet"
            else:
                profile["known_label"] = None
                profile["origin"] = "unknown"
                profile["account_type"] = "unknown"

            profile["current_balance_B"] = None
            profile["first_pump_receipt"] = None
            profile["upstream_1hop"] = []
        else:
            profile = profile_seller(
                helius_key, address, sell_stats, known_addresses, delay, monitor
            )

        sellers_out[address] = profile

        if (i + 1) % 50 == 0:
            print(f"  Progress: {i+1}/{total}")
            save_profiles(sellers_out, {"profiled": len(sellers_out)})
            if not args.skip_helius:
                print(f"    rate_limit_rate: {1-monitor.success_rate():.1%}")
                monitor.print_stats()

    # Local entity label lookup (pump_addresses.json + exchange addresses)
    print("\nApplying local entity labels...")
    entity_lookup = build_local_entity_lookup()
    labeled = 0
    for addr in sellers_out:
        if addr in entity_lookup:
            sellers_out[addr]["arkham_entity"] = entity_lookup[addr]
            labeled += 1
        else:
            sellers_out[addr]["arkham_entity"] = {"name": None, "type": "unknown", "has_entity": False}
    print(f"  Labeled {labeled}/{len(sellers_out)} sellers from local address registry")

    # Build classification summary
    origin_counts: dict[str, int] = defaultdict(int)
    size_counts: dict[str, int] = defaultdict(int)
    type_counts: dict[str, int] = defaultdict(int)
    for p in sellers_out.values():
        origin_counts[p.get("origin", "unknown")] += 1
        size_counts[p.get("size_tier", "unknown")] += 1
        type_counts[p.get("account_type", "unknown")] += 1

    summary = {
        "profiled": len(sellers_out),
        "by_origin": dict(origin_counts),
        "by_size_tier": dict(size_counts),
        "by_account_type": dict(type_counts),
        "with_known_entity": sum(1 for p in sellers_out.values() if p.get("arkham_entity", {}).get("has_entity")),
    }

    save_profiles(sellers_out, summary)

    print("\n=== Profile Summary ===")
    print(f"Total profiled: {len(sellers_out)}")
    print(f"By origin: {dict(origin_counts)}")
    print(f"By size:   {dict(size_counts)}")


if __name__ == "__main__":
    main()
