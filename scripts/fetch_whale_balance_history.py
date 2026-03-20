#!/usr/bin/env python3
"""
Fetch daily PUMP balance history for top whale addresses.
Strategy (credit-efficient):
  1. getTokenAccountsByOwner → find PUMP ATA for each wallet
  2. getSignaturesForAddress → get all tx signatures with timestamps
  3. For each date, pick the LAST signature of that day
  4. getTransaction on only those ~N_dates signatures → postTokenBalance
  5. Forward-fill dates with no transactions
"""

import json
import os
import time
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "data" / "pump_whale_balance_history.json"
WHALE_FILE = BASE_DIR / "data" / "pump_whale_addresses.json"

HELIUS_KEY = os.getenv("HELIUS_API_KEY", "")
RPC_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_KEY}"
PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"

TGE_DATE = datetime(2025, 7, 12, tzinfo=timezone.utc).date()
TODAY = datetime.now(timezone.utc).date()

THRESHOLD_B = 0.5  # process all whales >0.5B

# ── helpers ──────────────────────────────────────────────────────────────────

def rpc(method, params, retries=3):
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    for attempt in range(retries):
        try:
            r = requests.post(RPC_URL, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                print(f"    RPC error: {data['error']}")
                return None
            return data.get("result")
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"    Request failed: {e}")
                return None

def find_pump_ata(owner: str) -> str | None:
    """Find the PUMP token account for a given owner wallet."""
    result = rpc("getTokenAccountsByOwner", [
        owner,
        {"mint": PUMP_MINT},
        {"encoding": "jsonParsed"}
    ])
    if not result:
        return None
    accounts = result.get("value", [])
    if not accounts:
        return None
    # Return the account with the highest balance
    best = max(accounts, key=lambda a: float(
        a.get("account", {}).get("data", {}).get("parsed", {})
        .get("info", {}).get("tokenAmount", {}).get("uiAmount", 0) or 0
    ))
    return best["pubkey"]

def get_all_signatures(ata: str) -> list[dict]:
    """Get all signatures for an ATA, paginated (oldest→newest)."""
    all_sigs = []
    before = None
    page = 0
    while True:
        params = [ata, {"limit": 1000, "commitment": "finalized"}]
        if before:
            params[1]["before"] = before
        result = rpc("getSignaturesForAddress", params)
        if not result:
            break
        all_sigs.extend(result)
        page += 1
        if len(result) < 1000:
            break
        before = result[-1]["signature"]
        time.sleep(0.3)
    # Sort oldest first
    all_sigs.sort(key=lambda s: s.get("blockTime", 0))
    return all_sigs

def get_token_balance_from_tx(sig: str, ata: str) -> float | None:
    """Extract PUMP postTokenBalance from a transaction."""
    result = rpc("getTransaction", [
        sig,
        {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0,
         "commitment": "finalized"}
    ])
    if not result:
        return None
    post_balances = result.get("meta", {}).get("postTokenBalances", [])
    accounts = result.get("transaction", {}).get("message", {}).get("accountKeys", [])

    # Method 1: Match by ATA account index (most precise)
    ata_index = None
    for i, acc in enumerate(accounts):
        key = acc if isinstance(acc, str) else acc.get("pubkey", "")
        if key == ata:
            ata_index = i
            break
    if ata_index is not None:
        for bal in post_balances:
            if bal.get("accountIndex") == ata_index:
                ui = bal.get("uiTokenAmount", {}).get("uiAmount")
                if ui is not None:
                    return float(ui)

    # Method 2: Fallback - match by mint only if single PUMP account in tx
    pump_balances = [b for b in post_balances if b.get("mint") == PUMP_MINT]
    if len(pump_balances) == 1:
        ui = pump_balances[0].get("uiTokenAmount", {}).get("uiAmount")
        if ui is not None:
            return float(ui)

    return None

def build_daily_snapshots(sigs: list[dict], ata: str) -> dict[str, float]:
    """
    For each date, pick the last signature of that day and fetch its balance.
    Returns {date_str: balance}.
    """
    # Group sigs by date, keep last
    date_to_last_sig = {}
    for s in sigs:
        bt = s.get("blockTime")
        if not bt:
            continue
        d = datetime.fromtimestamp(bt, tz=timezone.utc).date()
        if d < TGE_DATE:
            continue
        date_to_last_sig[d] = s["signature"]

    snapshots = {}
    dates_sorted = sorted(date_to_last_sig.keys())
    total = len(dates_sorted)
    for i, d in enumerate(dates_sorted):
        sig = date_to_last_sig[d]
        bal = get_token_balance_from_tx(sig, ata)
        snapshots[str(d)] = bal if bal is not None else None
        print(f"      [{i+1}/{total}] {d}: {bal/1e9:.3f}B" if bal else
              f"      [{i+1}/{total}] {d}: parse failed")
        time.sleep(0.15)

    return snapshots

def forward_fill(snapshots: dict[str, float]) -> dict[str, float]:
    """Fill in all dates from TGE to today, carrying forward last known balance."""
    filled = {}
    last_val = 0.0
    d = TGE_DATE
    while d <= TODAY:
        ds = str(d)
        if ds in snapshots and snapshots[ds] is not None:
            last_val = snapshots[ds]
        filled[ds] = last_val
        d += timedelta(days=1)
    return filled

# ── main ─────────────────────────────────────────────────────────────────────

def main():
    whales = json.load(open(WHALE_FILE))["whales"]
    targets = [w for w in whales if w["amount_B"] >= THRESHOLD_B]
    targets.sort(key=lambda x: x["amount_B"], reverse=True)

    print(f"Processing {len(targets)} whale addresses (>{THRESHOLD_B}B PUMP)")
    print(f"Date range: {TGE_DATE} → {TODAY} ({(TODAY - TGE_DATE).days + 1} days)\n")

    # Load existing results to skip already-processed addresses
    if OUTPUT_FILE.exists():
        existing = json.load(open(OUTPUT_FILE))
        results = existing.get("data", {})
        skip_count = sum(1 for w in targets if w["address"] in results)
        print(f"Skipping {skip_count} already-processed addresses\n")
    else:
        results = {}
    credit_estimate = 0

    for i, whale in enumerate(targets):
        addr = whale["address"]

        # Skip already processed
        if addr in results:
            print(f"[{i+1}/{len(targets)}] SKIP {addr[:8]}... (already done)")
            continue
        addr = whale["address"]
        label = whale.get("known_label") or whale.get("label") or "Unknown"
        amt = whale["amount_B"]
        print(f"\n[{i+1}/{len(targets)}] {addr[:8]}...{addr[-8:]} | {amt:.3f}B | {label}")

        # Step 1: Find ATA
        print("  → Finding PUMP ATA...")
        ata = find_pump_ata(addr)
        credit_estimate += 1
        if not ata:
            print("  ⚠ No PUMP ATA found, skipping")
            results[addr] = {"label": label, "amount_B": amt, "ata": None, "history": {}}
            continue
        print(f"  ✅ ATA: {ata[:8]}...{ata[-8:]}")

        # Step 2: Get all signatures
        print("  → Fetching signatures...")
        sigs = get_all_signatures(ata)
        credit_estimate += max(1, len(sigs) // 100)
        print(f"  ✅ {len(sigs)} signatures found")

        if not sigs:
            results[addr] = {"label": label, "amount_B": amt, "ata": ata, "history": {}}
            continue

        # Step 3: Build daily snapshots (only fetch 1 tx per date)
        print(f"  → Fetching daily snapshots...")
        raw_snapshots = build_daily_snapshots(sigs, ata)
        credit_estimate += len(raw_snapshots)

        # Step 4: Forward-fill
        history = forward_fill(raw_snapshots)

        results[addr] = {
            "label": label,
            "amount_B": amt,
            "ata": ata,
            "total_signatures": len(sigs),
            "snapshot_dates": len(raw_snapshots),
            "history": history  # {date_str: balance_in_raw_units}
        }

        print(f"  ✅ Done: {len(raw_snapshots)} snapshot dates → {len(history)} filled days")
        print(f"  Credits used so far: ~{credit_estimate}")

        # Save incrementally
        output = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "threshold_B": THRESHOLD_B,
            "tge_date": str(TGE_DATE),
            "total_days": (TODAY - TGE_DATE).days + 1,
            "addresses_processed": i + 1,
            "total_addresses": len(targets),
            "credit_estimate": credit_estimate,
            "data": results
        }
        with open(OUTPUT_FILE, "w") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        time.sleep(0.5)

    print(f"\n{'='*60}")
    print(f"✅ Complete! Processed {len(results)} addresses")
    print(f"   Estimated credits used: {credit_estimate}")
    print(f"   Output: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
