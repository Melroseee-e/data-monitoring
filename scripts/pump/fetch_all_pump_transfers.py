#!/usr/bin/env python3
"""
PUMP Full Transfer History Collector
=====================================
Fetches ALL PUMP token transfer transactions from TGE to present.

Strategy:
  1. getSignaturesForAddress(PUMP_MINT) → paginate through all ~167k signatures
  2. Batch getTransaction (50/batch, jsonParsed) → parse pre/postTokenBalances
  3. Tag each transfer: cex_inflow / cex_outflow / wallet_to_wallet / dex_swap
  4. Per-address ledger: cumulative buy_B, sell_B, cex_buy_B, cex_sell_B

Credit usage: ~167k signatures / 50 per batch = 3,340 batches × 20 credits = ~67k credits
Estimated time: 3-5 hours (conservative rate limiting)

Output:
  data/pump/raw/pump_all_transfers.jsonl   — one JSON line per transfer
  data/pump/derived/pump_address_ledger.json — per-address aggregated stats

Usage:
  python scripts/pump/fetch_all_pump_transfers.py
  python scripts/pump/fetch_all_pump_transfers.py --resume   # resume from checkpoint
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SKILLS_DIR = BASE_DIR / ".claude" / "skills" / "onchain-analysis" / "scripts"
sys.path.insert(0, str(SKILLS_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from core.config import require_api_key, get_all_solana_keys, load_exchange_addresses, HELIUS_RPC_TEMPLATE
from core.rpc import rpc_call, get_session
from core.rate_limiter import AdaptiveDelay, RateLimitMonitor


class KeyRotator:
    """Rotate through multiple Helius API keys on credit exhaustion."""
    def __init__(self, keys: list[str]):
        self.keys = keys
        self.idx = 0
        print(f"KeyRotator: {len(keys)} Helius keys available")

    @property
    def current(self) -> str:
        if self.idx >= len(self.keys):
            return self.keys[-1]  # stay on last key rather than crash
        return self.keys[self.idx]

    def rotate(self) -> bool:
        """Switch to next key. Returns False if all keys exhausted."""
        self.idx += 1
        if self.idx >= len(self.keys):
            # Wrap around to first key as last resort
            print(f"  All {len(self.keys)} keys tried, wrapping to key 1 (may retry after cooldown)")
            self.idx = 0
            time.sleep(30)  # brief cooldown before reusing keys
            return True
        print(f"  Rotating to Helius key {self.idx + 1}/{len(self.keys)}")
        return True

    def rpc_url(self) -> str:
        return HELIUS_RPC_TEMPLATE.format(api_key=self.current)

PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
PUMP_DECIMALS = 9
TGE_TIMESTAMP = 1752278400   # 2025-07-12 00:00 UTC
TGE_DATE = "2025-07-12"

DATA_DIR = BASE_DIR / "data" / "pump"
TRANSFERS_FILE   = DATA_DIR / "raw"     / "pump_all_transfers.jsonl"
CHECKPOINT_FILE  = DATA_DIR / "raw"     / ".pump_transfers_checkpoint.json"
LEDGER_FILE      = DATA_DIR / "derived" / "pump_address_ledger.json"
PROGRESS_LOG     = DATA_DIR / "raw"     / ".pump_transfers_progress.log"

BATCH_SIZE = 50        # transactions per getTransaction batch
SIG_PAGE   = 1000      # signatures per getSignaturesForAddress page


# ---------------------------------------------------------------------------
# Exchange address lookup
# ---------------------------------------------------------------------------

def build_cex_lookup() -> dict[str, str]:
    """Returns {solana_address: exchange_name} for all Solana CEX addresses."""
    exchanges_data = load_exchange_addresses()
    lookup: dict[str, str] = {}
    for exchange_name, chains in exchanges_data.items():
        if isinstance(chains, dict) and "solana" in chains:
            for addr in chains["solana"]:
                lookup[addr] = exchange_name
    print(f"Loaded {len(lookup)} Solana CEX addresses")
    return lookup


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE) as f:
            return json.load(f)
    return {"last_sig": None, "sigs_collected": 0, "batches_processed": 0, "transfers_written": 0}


def save_checkpoint(cp: dict) -> None:
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(cp, f, indent=2)


def log(msg: str) -> None:
    ts = datetime.now(tz=timezone.utc).strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(PROGRESS_LOG, "a") as f:
        f.write(line + "\n")


# ---------------------------------------------------------------------------
# Phase 1: Collect all signatures
# ---------------------------------------------------------------------------

def collect_signatures(rotator: "KeyRotator", checkpoint: dict) -> list[str]:
    """
    Page through getSignaturesForAddress for PUMP_MINT.
    Returns list of all signatures (oldest-first ordering preserved).
    Resume-safe: if checkpoint has signatures already, reload from JSONL.
    """
    # If we have a JSONL file already, extract processed sigs to avoid reprocessing
    processed_sigs: set[str] = set()
    if TRANSFERS_FILE.exists():
        with open(TRANSFERS_FILE) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    processed_sigs.add(rec.get("signature", ""))
                except Exception:
                    pass
        log(f"Found {len(processed_sigs)} already-processed signatures in JSONL")

    # Collect ALL signatures (newest → oldest), then reverse
    all_sigs: list[str] = []
    before: str | None = None
    page = 0
    delay = AdaptiveDelay(initial=0.3, min_delay=0.1, max_delay=5.0)

    log("Phase 1: Collecting all signatures via getSignaturesForAddress...")

    while True:
        opts: dict = {"limit": SIG_PAGE}
        if before:
            opts["before"] = before

        result = rpc_call(rotator.rpc_url(), "getSignaturesForAddress", [PUMP_MINT, opts])
        if not result:
            # Try rotating key before giving up
            if rotator.rotate():
                log(f"  Rotated key, retrying page {page+1}...")
                continue
            break

        page_sigs = [r["signature"] for r in result if not r.get("err")]
        # Filter to TGE and later (blockTime >= TGE_TIMESTAMP)
        page_sigs_filtered = [
            r["signature"] for r in result
            if not r.get("err") and (r.get("blockTime") or 0) >= TGE_TIMESTAMP
        ]

        # If the oldest sig in this page is before TGE, stop
        oldest_ts = min((r.get("blockTime") or 0) for r in result) if result else 0
        if oldest_ts < TGE_TIMESTAMP and oldest_ts > 0:
            # Only keep sigs at or after TGE
            all_sigs.extend(page_sigs_filtered)
            page += 1
            log(f"  Page {page}: {len(page_sigs_filtered)} sigs (reached TGE boundary, stopping)")
            break

        all_sigs.extend(page_sigs_filtered)
        before = result[-1]["signature"]
        page += 1

        if page % 10 == 0:
            log(f"  Page {page}: {len(all_sigs)} total sigs so far")

        if len(result) < SIG_PAGE:
            # Reached the end
            break

        delay.wait()

    # Reverse to oldest-first
    all_sigs.reverse()

    # Remove already-processed
    new_sigs = [s for s in all_sigs if s not in processed_sigs]
    log(f"Phase 1 complete: {len(all_sigs)} total sigs, {len(new_sigs)} unprocessed")
    return new_sigs, len(processed_sigs)


# ---------------------------------------------------------------------------
# Phase 2: Batch fetch + parse transactions
# ---------------------------------------------------------------------------

def batch_get_transactions(rotator: "KeyRotator", signatures: list[str]) -> list[dict | None]:
    """
    Use Helius batch getTransaction (up to 50 per call via their batch endpoint).
    Auto-rotates to next key on credit exhaustion.
    """
    rpc_url = rotator.rpc_url()
    session = get_session(rpc_url)

    # Helius supports JSON-RPC batch (array of requests)
    payload = [
        {
            "jsonrpc": "2.0",
            "id": i,
            "method": "getTransaction",
            "params": [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
        }
        for i, sig in enumerate(signatures)
    ]

    backoff = 1.0
    for attempt in range(6):
        try:
            rpc_url = rotator.rpc_url()
            session = get_session(rpc_url)
            resp = session.post(rpc_url, json=payload, timeout=60)
            if resp.status_code == 429:
                wait = min(32, backoff)
                print(f"  Batch 429, retry in {wait:.0f}s...", flush=True)
                time.sleep(wait)
                backoff = min(backoff * 2, 32)
                continue
            # Check for credit exhaustion in response body
            try:
                body = resp.json()
                if isinstance(body, dict):
                    err = body.get("error", {})
                    if err.get("code") == -32429 or "max usage" in str(err).lower():
                        print(f"  Credit exhausted on key {rotator.idx+1}, rotating...", flush=True)
                        if rotator.rotate():
                            backoff = 1.0
                            continue
                        return [None] * len(signatures)
            except Exception:
                pass
            resp.raise_for_status()
            results = resp.json()
            if isinstance(results, list):
                return [r.get("result") for r in sorted(results, key=lambda x: x.get("id", 0))]
            return [results.get("result")]
        except Exception as e:
            if attempt < 5:
                wait = min(32, backoff)
                print(f"  Batch error: {e}, retry in {wait:.0f}s...", flush=True)
                time.sleep(wait)
                backoff = min(backoff * 2, 32)
            else:
                print(f"  Batch failed after 6 attempts: {e}", flush=True)
                return [None] * len(signatures)

    return [None] * len(signatures)


def extract_transfers(tx_data: dict, sig: str, cex_lookup: dict[str, str]) -> list[dict]:
    """
    Extract PUMP token transfers from a parsed transaction.
    Uses pre/postTokenBalances diff for accuracy.
    Tags each transfer: cex_inflow, cex_outflow, dex_swap, wallet_to_wallet.
    """
    if not tx_data:
        return []

    meta = tx_data.get("meta", {})
    if meta.get("err"):
        return []

    block_time = tx_data.get("blockTime", 0) or 0
    if block_time < TGE_TIMESTAMP:
        return []

    # Build pre/post balance maps: {owner: amount_raw}
    pre: dict[str, int] = {}
    for b in meta.get("preTokenBalances", []):
        if b.get("mint") == PUMP_MINT:
            owner = b.get("owner", "")
            if owner:
                pre[owner] = int(b.get("uiTokenAmount", {}).get("amount", "0") or "0")

    post: dict[str, int] = {}
    for b in meta.get("postTokenBalances", []):
        if b.get("mint") == PUMP_MINT:
            owner = b.get("owner", "")
            if owner:
                post[owner] = int(b.get("uiTokenAmount", {}).get("amount", "0") or "0")

    all_owners = set(pre) | set(post)
    increases: dict[str, int] = {}
    decreases: dict[str, int] = {}

    for owner in all_owners:
        pre_amt = pre.get(owner, 0)
        post_amt = post.get(owner, 0)
        diff = post_amt - pre_amt
        if diff > 0:
            increases[owner] = diff
        elif diff < 0:
            decreases[owner] = abs(diff)

    if not increases and not decreases:
        return []

    # Detect if this is a DEX swap (no net sender in normal wallet→wallet sense)
    # Heuristic: if a program account changes (Pump AMM, Raydium, etc.), it's a DEX swap
    tx_msg = tx_data.get("transaction", {}).get("message", {})
    account_keys = tx_msg.get("accountKeys", [])
    # Known DEX program IDs
    DEX_PROGRAMS = {
        "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P",   # Pump.fun AMM
        "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",  # Raydium v4
        "JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",  # Jupiter v6
        "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",   # Orca Whirlpool
        "9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP",  # Orca v1
    }
    is_dex = any(
        (a.get("pubkey") if isinstance(a, dict) else a) in DEX_PROGRAMS
        for a in account_keys
    )

    date_str = datetime.fromtimestamp(block_time, tz=timezone.utc).strftime("%Y-%m-%d")

    transfers = []
    # Pair decreases with increases
    for sender, send_amt in decreases.items():
        for receiver, recv_amt in increases.items():
            # Allow 1% slippage (fees, rounding)
            if abs(send_amt - recv_amt) <= max(send_amt * 0.02, 100):
                amount_B = send_amt / 10 ** PUMP_DECIMALS

                # Classify transfer type
                sender_is_cex = sender in cex_lookup
                receiver_is_cex = receiver in cex_lookup

                if is_dex:
                    transfer_type = "dex_swap"
                elif sender_is_cex and not receiver_is_cex:
                    transfer_type = "cex_outflow"    # CEX → wallet (buy/withdraw)
                elif receiver_is_cex and not sender_is_cex:
                    transfer_type = "cex_inflow"     # wallet → CEX (sell/deposit)
                elif sender_is_cex and receiver_is_cex:
                    transfer_type = "cex_internal"   # CEX → CEX (internal move)
                else:
                    transfer_type = "wallet_to_wallet"

                transfers.append({
                    "signature": sig,
                    "timestamp": block_time,
                    "date": date_str,
                    "from_address": sender,
                    "to_address": receiver,
                    "amount_B": round(amount_B, 9),
                    "transfer_type": transfer_type,
                    "from_exchange": cex_lookup.get(sender),
                    "to_exchange": cex_lookup.get(receiver),
                })
                break

    # Handle unpaired (mint/burn or DEX with pool account)
    if not transfers:
        for receiver, recv_amt in increases.items():
            amount_B = recv_amt / 10 ** PUMP_DECIMALS
            transfers.append({
                "signature": sig,
                "timestamp": block_time,
                "date": date_str,
                "from_address": "",
                "to_address": receiver,
                "amount_B": round(amount_B, 9),
                "transfer_type": "mint_or_unpaired",
                "from_exchange": None,
                "to_exchange": cex_lookup.get(receiver),
            })
        for sender, send_amt in decreases.items():
            amount_B = send_amt / 10 ** PUMP_DECIMALS
            transfers.append({
                "signature": sig,
                "timestamp": block_time,
                "date": date_str,
                "from_address": sender,
                "to_address": "",
                "amount_B": round(amount_B, 9),
                "transfer_type": "burn_or_unpaired",
                "from_exchange": cex_lookup.get(sender),
                "to_exchange": None,
            })

    return transfers


# ---------------------------------------------------------------------------
# Phase 3: Build per-address ledger
# ---------------------------------------------------------------------------

def build_ledger(cex_lookup: dict[str, str]) -> dict:
    """
    Read the JSONL transfers file and build per-address aggregated stats.
    """
    log("Phase 3: Building per-address ledger from JSONL...")

    ledger: dict[str, dict] = defaultdict(lambda: {
        "total_received_B": 0.0,
        "total_sent_B": 0.0,
        "cex_inflow_B": 0.0,      # amount sent TO a CEX (sells)
        "cex_outflow_B": 0.0,     # amount received FROM a CEX (buys)
        "dex_buy_B": 0.0,         # received via DEX swap
        "dex_sell_B": 0.0,        # sent via DEX swap
        "w2w_received_B": 0.0,    # wallet-to-wallet received
        "w2w_sent_B": 0.0,        # wallet-to-wallet sent
        "tx_count": 0,
        "first_activity_date": None,
        "last_activity_date": None,
        "exchanges_deposited": set(),  # CEXes received PUMP from this wallet
        "exchanges_withdrawn": set(),  # CEXes sent PUMP to this wallet
    })

    transfer_count = 0
    with open(TRANSFERS_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue

            transfer_count += 1
            tt = r.get("transfer_type", "")
            amt = r.get("amount_B", 0)
            date = r.get("date", "")
            frm = r.get("from_address", "")
            to = r.get("to_address", "")

            def update_dates(addr: str):
                e = ledger[addr]
                if date:
                    if e["first_activity_date"] is None or date < e["first_activity_date"]:
                        e["first_activity_date"] = date
                    if e["last_activity_date"] is None or date > e["last_activity_date"]:
                        e["last_activity_date"] = date
                e["tx_count"] += 1

            if tt == "cex_inflow":
                # wallet → CEX: sender is selling
                if frm and frm not in cex_lookup:
                    ledger[frm]["cex_inflow_B"] += amt
                    ledger[frm]["total_sent_B"] += amt
                    if r.get("to_exchange"):
                        ledger[frm]["exchanges_deposited"].add(r["to_exchange"])
                    update_dates(frm)
                # CEX receives
                if to and to in cex_lookup:
                    ledger[to]["cex_outflow_B"] += amt   # from CEX perspective, inflow = outflow to others
                    ledger[to]["total_received_B"] += amt
                    update_dates(to)

            elif tt == "cex_outflow":
                # CEX → wallet: receiver is buying/withdrawing
                if to and to not in cex_lookup:
                    ledger[to]["cex_outflow_B"] += amt
                    ledger[to]["total_received_B"] += amt
                    if r.get("from_exchange"):
                        ledger[to]["exchanges_withdrawn"].add(r["from_exchange"])
                    update_dates(to)
                if frm and frm in cex_lookup:
                    ledger[frm]["cex_inflow_B"] += amt
                    ledger[frm]["total_sent_B"] += amt
                    update_dates(frm)

            elif tt == "dex_swap":
                if frm:
                    ledger[frm]["dex_sell_B"] += amt
                    ledger[frm]["total_sent_B"] += amt
                    update_dates(frm)
                if to:
                    ledger[to]["dex_buy_B"] += amt
                    ledger[to]["total_received_B"] += amt
                    update_dates(to)

            elif tt == "wallet_to_wallet":
                if frm:
                    ledger[frm]["w2w_sent_B"] += amt
                    ledger[frm]["total_sent_B"] += amt
                    update_dates(frm)
                if to:
                    ledger[to]["w2w_received_B"] += amt
                    ledger[to]["total_received_B"] += amt
                    update_dates(to)

            elif tt in ("mint_or_unpaired",):
                if to:
                    ledger[to]["total_received_B"] += amt
                    update_dates(to)
            elif tt in ("burn_or_unpaired",):
                if frm:
                    ledger[frm]["total_sent_B"] += amt
                    update_dates(frm)

    log(f"  Processed {transfer_count} transfers, {len(ledger)} unique addresses")

    # Post-process: convert sets to lists, add derived fields
    result = {}
    for addr, data in ledger.items():
        net_B = data["total_received_B"] - data["total_sent_B"]
        total_sell_B = data["cex_inflow_B"] + data["dex_sell_B"]
        total_buy_B  = data["cex_outflow_B"] + data["dex_buy_B"]

        # Size tier by total activity volume
        total_volume = data["total_received_B"] + data["total_sent_B"]
        if total_volume >= 20.0:
            size_tier = "Mega"
        elif total_volume >= 2.0:
            size_tier = "Large"
        elif total_volume >= 0.2:
            size_tier = "Medium"
        elif total_volume >= 0.02:
            size_tier = "Small"
        else:
            size_tier = "Micro"

        is_cex = addr in cex_lookup

        result[addr] = {
            "address": addr,
            "is_cex": is_cex,
            "cex_name": cex_lookup.get(addr),
            "size_tier": size_tier,
            "total_received_B": round(data["total_received_B"], 6),
            "total_sent_B": round(data["total_sent_B"], 6),
            "net_B": round(net_B, 6),                   # positive = net buyer, negative = net seller
            "total_sell_B": round(total_sell_B, 6),     # CEX deposit + DEX sell
            "total_buy_B": round(total_buy_B, 6),       # CEX withdraw + DEX buy
            "cex_inflow_B": round(data["cex_inflow_B"], 6),
            "cex_outflow_B": round(data["cex_outflow_B"], 6),
            "dex_sell_B": round(data["dex_sell_B"], 6),
            "dex_buy_B": round(data["dex_buy_B"], 6),
            "w2w_sent_B": round(data["w2w_sent_B"], 6),
            "w2w_received_B": round(data["w2w_received_B"], 6),
            "tx_count": data["tx_count"],
            "first_activity_date": data["first_activity_date"],
            "last_activity_date": data["last_activity_date"],
            "exchanges_deposited": sorted(data["exchanges_deposited"]),
            "exchanges_withdrawn": sorted(data["exchanges_withdrawn"]),
        }

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(description="Fetch all PUMP transfers from TGE to present")
    parser.add_argument("--ledger-only", action="store_true", help="Skip collection, just rebuild ledger from existing JSONL")
    args = parser.parse_args()

    PROGRESS_LOG.parent.mkdir(parents=True, exist_ok=True)

    log("=" * 60)
    log(f"PUMP Full Transfer History — {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    log("=" * 60)

    cex_lookup = build_cex_lookup()

    if not args.ledger_only:
        all_keys = get_all_solana_keys()
        if not all_keys:
            log("ERROR: No Helius API keys found")
            return
        rotator = KeyRotator(all_keys)
        checkpoint = load_checkpoint()

        # Phase 1: Collect signatures
        new_sigs, already_done = collect_signatures(rotator, checkpoint)

        if not new_sigs:
            log("No new signatures to process. Running ledger build only.")
        else:
            # Phase 2: Batch fetch and parse
            log(f"Phase 2: Processing {len(new_sigs)} signatures in batches of {BATCH_SIZE}...")
            delay = AdaptiveDelay(initial=0.4, min_delay=0.2, max_delay=8.0)
            monitor = RateLimitMonitor(window_size=200)

            TRANSFERS_FILE.parent.mkdir(parents=True, exist_ok=True)
            total_transfers = 0
            batches_done = 0
            total_batches = (len(new_sigs) + BATCH_SIZE - 1) // BATCH_SIZE

            with open(TRANSFERS_FILE, "a") as out_f:
                for batch_start in range(0, len(new_sigs), BATCH_SIZE):
                    batch_sigs = new_sigs[batch_start: batch_start + BATCH_SIZE]
                    tx_results = batch_get_transactions(rotator, batch_sigs)

                    for sig, tx_data in zip(batch_sigs, tx_results):
                        if not tx_data:
                            continue
                        transfers = extract_transfers(tx_data, sig, cex_lookup)
                        for t in transfers:
                            out_f.write(json.dumps(t, ensure_ascii=False) + "\n")
                            total_transfers += 1

                    batches_done += 1
                    monitor.record(True)

                    if batches_done % 20 == 0:
                        out_f.flush()
                        progress_pct = (already_done + batch_start + len(batch_sigs)) / (already_done + len(new_sigs)) * 100
                        log(f"  Batch {batches_done}/{total_batches} | {progress_pct:.1f}% | {total_transfers} transfers | key={rotator.idx+1}/{len(rotator.keys)}")
                        checkpoint["batches_processed"] = already_done // BATCH_SIZE + batches_done
                        checkpoint["transfers_written"] = total_transfers
                        save_checkpoint(checkpoint)

                    delay.wait()

            log(f"Phase 2 complete: {total_transfers} new transfers written")

    # Phase 3: Build ledger
    if not TRANSFERS_FILE.exists():
        log("ERROR: No transfers JSONL found. Run without --ledger-only first.")
        return

    ledger = build_ledger(cex_lookup)

    # Summary stats
    non_cex = {a: d for a, d in ledger.items() if not d["is_cex"]}
    sellers  = {a: d for a, d in non_cex.items() if d["total_sell_B"] > 0}
    buyers   = {a: d for a, d in non_cex.items() if d["total_buy_B"] > 0}
    net_sellers = {a: d for a, d in non_cex.items() if d["net_B"] < 0}
    net_buyers  = {a: d for a, d in non_cex.items() if d["net_B"] > 0}

    size_dist: dict[str, int] = {}
    for d in non_cex.values():
        t = d["size_tier"]
        size_dist[t] = size_dist.get(t, 0) + 1

    summary = {
        "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pump_mint": PUMP_MINT,
        "tge_date": TGE_DATE,
        "total_addresses": len(ledger),
        "non_cex_addresses": len(non_cex),
        "addresses_with_any_sell": len(sellers),
        "addresses_with_any_buy": len(buyers),
        "net_sellers": len(net_sellers),
        "net_buyers": len(net_buyers),
        "size_distribution": size_dist,
        "total_cex_inflow_B": round(sum(d["cex_inflow_B"] for d in non_cex.values()), 2),
        "total_cex_outflow_B": round(sum(d["cex_outflow_B"] for d in non_cex.values()), 2),
        "total_dex_sell_B": round(sum(d["dex_sell_B"] for d in non_cex.values()), 2),
        "total_dex_buy_B": round(sum(d["dex_buy_B"] for d in non_cex.values()), 2),
    }

    LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_FILE, "w") as f:
        json.dump({"summary": summary, "addresses": ledger}, f, ensure_ascii=False, indent=2)

    log(f"\n{'='*60}")
    log("=== SUMMARY ===")
    log(f"Total addresses:      {summary['total_addresses']:,}")
    log(f"Non-CEX addresses:    {summary['non_cex_addresses']:,}")
    log(f"Ever sold (CEX+DEX):  {summary['addresses_with_any_sell']:,}")
    log(f"Ever bought (CEX+DEX):{summary['addresses_with_any_buy']:,}")
    log(f"Net sellers:          {summary['net_sellers']:,}")
    log(f"Net buyers:           {summary['net_buyers']:,}")
    log(f"Size dist:            {size_dist}")
    log(f"CEX inflow total:     {summary['total_cex_inflow_B']:.2f}B PUMP")
    log(f"CEX outflow total:    {summary['total_cex_outflow_B']:.2f}B PUMP")
    log(f"DEX sell total:       {summary['total_dex_sell_B']:.2f}B PUMP")
    log(f"DEX buy total:        {summary['total_dex_buy_B']:.2f}B PUMP")
    log(f"\nLedger saved → {LEDGER_FILE}")


if __name__ == "__main__":
    main()
