#!/usr/bin/env python3
"""
PUMP Token Buyback Wallet Analysis
Traces all buyback activity from 3vkpy5YHqnqJTnA5doWTpcgKyZiYsaXYzYM9wm8s3WTi
since TGE (2025-07-16, first buyback date)

Output: data/pump_buyback_analysis.json
"""

import json
import time
import requests
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

HELIUS_API_KEY = "6bb10a8e-f7b7-4216-a9ad-54d7cd762b0e"
HELIUS_RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
HELIUS_API_BASE = f"https://api.helius.xyz/v0"

BUYBACK_ADDR = "3vkpy5YHqnqJTnA5doWTpcgKyZiYsaXYzYM9wm8s3WTi"
TREASURY_ADDR = "G8CcfRffqZWHSAQJXLDfwbAkGE95SddUqVXnTrL4kqjm"
PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "data" / "pump_buyback_analysis.json"

# TGE was 2025-07-12, first buyback was 2025-07-16
TGE_TIMESTAMP = 1752278400  # 2025-07-12 00:00 UTC
FIRST_BUYBACK_DATE = "2025-07-16"


def rpc_call(method, params):
    """Standard Solana JSON-RPC call."""
    resp = requests.post(
        HELIUS_RPC,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=30
    )
    data = resp.json()
    if "error" in data:
        print(f"  RPC error: {data['error']}")
        return None
    return data.get("result")


def fetch_enhanced_transactions(address, before=None, limit=100):
    """Fetch parsed transactions from Helius Enhanced API."""
    params = {"api-key": HELIUS_API_KEY, "limit": limit}
    if before:
        params["before"] = before

    url = f"{HELIUS_API_BASE}/addresses/{address}/transactions"
    resp = requests.get(url, params=params, timeout=30)
    if resp.status_code == 429:
        print("  Rate limited, sleeping 5s...")
        time.sleep(5)
        resp = requests.get(url, params=params, timeout=30)
    if resp.status_code != 200:
        print(f"  Error {resp.status_code}: {resp.text[:200]}")
        return []
    return resp.json()


def get_pump_balance(address):
    """Get current PUMP token balance."""
    result = rpc_call("getTokenAccountsByOwner", [
        address,
        {"mint": PUMP_MINT},
        {"encoding": "jsonParsed"}
    ])
    if result and result.get("value"):
        total = sum(
            a["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"] or 0
            for a in result["value"]
        )
        return total
    return 0.0


def classify_tx(tx, buyback_addr, treasury_addr, pump_mint):
    """
    Classify a transaction as:
    - 'buyback': PUMP tokens received by buyback wallet (DEX swap)
    - 'treasury_transfer': PUMP sent from buyback wallet to treasury
    - 'sol_receive': SOL received (funding for buybacks)
    - 'other': other activity

    Returns dict with type, pump_amount, sol_amount, details
    """
    token_transfers = tx.get("tokenTransfers", []) or []
    native_transfers = tx.get("nativeTransfers", []) or []
    tx_type = tx.get("type", "UNKNOWN")
    source = tx.get("source", "UNKNOWN")

    result = {
        "signature": tx.get("signature"),
        "timestamp": tx.get("timestamp"),
        "date": datetime.fromtimestamp(tx.get("timestamp", 0), tz=timezone.utc).strftime("%Y-%m-%d"),
        "type": "other",
        "pump_in": 0.0,    # PUMP received by buyback wallet
        "pump_out": 0.0,   # PUMP sent from buyback wallet
        "sol_in": 0.0,     # SOL received by buyback wallet
        "sol_out": 0.0,    # SOL spent
        "treasury_transfer": False,
        "dex": source,
        "tx_type": tx_type,
    }

    # Process token transfers
    for tt in token_transfers:
        if tt.get("mint") != pump_mint:
            continue
        amount = tt.get("tokenAmount", 0) or 0
        from_acc = tt.get("fromUserAccount", "") or ""
        to_acc = tt.get("toUserAccount", "") or ""

        if to_acc == buyback_addr:
            result["pump_in"] += amount
        if from_acc == buyback_addr:
            result["pump_out"] += amount
            if to_acc == treasury_addr:
                result["treasury_transfer"] = True

    # Process native (SOL) transfers
    for nt in native_transfers:
        amount_sol = (nt.get("amount", 0) or 0) / 1e9
        from_acc = nt.get("fromUserAccount", "") or ""
        to_acc = nt.get("toUserAccount", "") or ""
        if to_acc == buyback_addr:
            result["sol_in"] += amount_sol
        if from_acc == buyback_addr:
            result["sol_out"] += amount_sol

    # Classify
    if result["pump_in"] > 0 and tx_type in ("SWAP", "DEX_TRADE"):
        result["type"] = "buyback"
    elif result["pump_in"] > 0:
        # Could still be a swap even without explicit type
        result["type"] = "buyback"
    elif result["treasury_transfer"] and result["pump_out"] > 0:
        result["type"] = "treasury_transfer"
    elif result["sol_in"] > 0 and result["pump_in"] == 0 and result["pump_out"] == 0:
        result["type"] = "sol_receive"
    else:
        result["type"] = "other"

    return result


def fetch_all_buyback_transactions():
    """Fetch complete transaction history for buyback wallet."""
    print(f"\nFetching all transactions for buyback wallet: {BUYBACK_ADDR}")
    print(f"(This may take a while due to rate limits)\n")

    all_txs = []
    before = None
    page = 0

    while True:
        page += 1
        txs = fetch_enhanced_transactions(BUYBACK_ADDR, before=before, limit=100)

        if not txs:
            print(f"  Page {page}: No more transactions (total: {len(all_txs)})")
            break

        all_txs.extend(txs)

        # Stop if we've gone past TGE date
        oldest_ts = min(tx.get("timestamp", 0) for tx in txs)
        oldest_date = datetime.fromtimestamp(oldest_ts, tz=timezone.utc).strftime("%Y-%m-%d") if oldest_ts else "unknown"
        newest_ts = max(tx.get("timestamp", 0) for tx in txs)
        newest_date = datetime.fromtimestamp(newest_ts, tz=timezone.utc).strftime("%Y-%m-%d") if newest_ts else "unknown"

        print(f"  Page {page}: {len(txs)} txs | {oldest_date} → {newest_date} | total: {len(all_txs)}")

        if oldest_ts < TGE_TIMESTAMP:
            print(f"  Reached pre-TGE transactions, stopping.")
            break

        before = txs[-1]["signature"]
        time.sleep(0.3)  # rate limit courtesy

    print(f"\nTotal transactions fetched: {len(all_txs)}")
    return all_txs


def analyze_transactions(raw_txs):
    """Parse and analyze all fetched transactions."""
    classified = []
    for tx in raw_txs:
        c = classify_tx(tx, BUYBACK_ADDR, TREASURY_ADDR, PUMP_MINT)
        classified.append(c)
    return classified


def compute_statistics(classified_txs):
    """Compute comprehensive buyback statistics."""
    buybacks = [t for t in classified_txs if t["type"] == "buyback"]
    treasury_transfers = [t for t in classified_txs if t["type"] == "treasury_transfer"]
    sol_receives = [t for t in classified_txs if t["type"] == "sol_receive"]

    # --- Daily stats ---
    daily = defaultdict(lambda: {
        "pump_bought": 0.0,
        "sol_spent": 0.0,
        "pump_sent_to_treasury": 0.0,
        "buyback_count": 0,
        "treasury_transfer_count": 0
    })

    for tx in buybacks:
        d = tx["date"]
        daily[d]["pump_bought"] += tx["pump_in"]
        daily[d]["sol_spent"] += tx["sol_out"]
        daily[d]["buyback_count"] += 1

    for tx in treasury_transfers:
        d = tx["date"]
        daily[d]["pump_sent_to_treasury"] += tx["pump_out"]
        daily[d]["treasury_transfer_count"] += 1

    # --- Monthly stats ---
    monthly = defaultdict(lambda: {
        "pump_bought": 0.0,
        "sol_spent": 0.0,
        "pump_sent_to_treasury": 0.0,
        "buyback_count": 0,
    })
    for tx in buybacks:
        mo = tx["date"][:7]  # "YYYY-MM"
        monthly[mo]["pump_bought"] += tx["pump_in"]
        monthly[mo]["sol_spent"] += tx["sol_out"]
        monthly[mo]["buyback_count"] += 1
    for tx in treasury_transfers:
        mo = tx["date"][:7]
        monthly[mo]["pump_sent_to_treasury"] += tx["pump_out"]

    # --- DEX distribution ---
    dex_stats = defaultdict(lambda: {"pump_bought": 0.0, "tx_count": 0})
    for tx in buybacks:
        dex = tx["dex"] or "UNKNOWN"
        dex_stats[dex]["pump_bought"] += tx["pump_in"]
        dex_stats[dex]["tx_count"] += 1

    # --- Cumulative ---
    total_pump_bought = sum(t["pump_in"] for t in buybacks)
    total_sol_spent = sum(t["sol_out"] for t in buybacks)
    total_pump_to_treasury = sum(t["pump_out"] for t in treasury_transfers)
    total_sol_received = sum(t["sol_in"] for t in sol_receives)

    # --- Price estimation ---
    # SOL price at various points (rough estimates)
    avg_price_pump_per_sol = (total_pump_bought / total_sol_spent) if total_sol_spent > 0 else 0

    # Get current balance
    current_balance = get_pump_balance(BUYBACK_ADDR)

    stats = {
        "summary": {
            "analysis_date": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "first_tx_date": min((t["date"] for t in classified_txs), default="N/A"),
            "last_tx_date": max((t["date"] for t in classified_txs), default="N/A"),
            "total_txs": len(classified_txs),
            "buyback_txs": len(buybacks),
            "treasury_transfer_txs": len(treasury_transfers),
            "sol_receive_txs": len(sol_receives),
            "other_txs": len(classified_txs) - len(buybacks) - len(treasury_transfers) - len(sol_receives),
        },
        "buyback_totals": {
            "total_pump_bought": round(total_pump_bought, 2),
            "total_sol_spent": round(total_sol_spent, 4),
            "total_sol_received_as_funding": round(total_sol_received, 4),
            "avg_pump_per_sol": round(avg_price_pump_per_sol, 2),
            "total_pump_to_treasury": round(total_pump_to_treasury, 2),
            "current_buyback_wallet_pump_balance": round(current_balance, 2),
        },
        "monthly": {
            k: {kk: round(vv, 4) for kk, vv in v.items()}
            for k, v in sorted(monthly.items())
        },
        "daily": {
            k: {kk: round(vv, 4) for kk, vv in v.items()}
            for k, v in sorted(daily.items())
        },
        "dex_distribution": {
            k: {kk: round(vv, 4) if isinstance(vv, float) else vv for kk, vv in v.items()}
            for k, v in sorted(dex_stats.items(), key=lambda x: x[1]["pump_bought"], reverse=True)
        },
        "top_10_largest_buybacks": sorted(
            [{"date": t["date"], "pump_in": round(t["pump_in"], 2), "sol_out": round(t["sol_out"], 6),
              "dex": t["dex"], "signature": t["signature"]}
             for t in buybacks],
            key=lambda x: x["pump_in"],
            reverse=True
        )[:10],
        "treasury_transfer_events": sorted(
            [{"date": t["date"], "pump_out": round(t["pump_out"], 2), "signature": t["signature"]}
             for t in treasury_transfers],
            key=lambda x: x["date"]
        ),
    }

    return stats


def main():
    print("=" * 80)
    print("PUMP Buyback Wallet Analysis".center(80))
    print(f"Wallet: {BUYBACK_ADDR}".center(80))
    print("=" * 80)

    # Step 1: Fetch all transactions
    raw_txs = fetch_all_buyback_transactions()

    if not raw_txs:
        print("ERROR: No transactions fetched. Check API key and address.")
        return

    # Step 2: Classify all transactions
    print("\nClassifying transactions...")
    classified = analyze_transactions(raw_txs)

    buyback_count = sum(1 for t in classified if t["type"] == "buyback")
    treasury_count = sum(1 for t in classified if t["type"] == "treasury_transfer")
    sol_count = sum(1 for t in classified if t["type"] == "sol_receive")
    print(f"  Buybacks:          {buyback_count}")
    print(f"  Treasury transfers: {treasury_count}")
    print(f"  SOL receives:      {sol_count}")
    print(f"  Other:             {len(classified) - buyback_count - treasury_count - sol_count}")

    # Step 3: Compute statistics
    print("\nComputing statistics...")
    stats = compute_statistics(classified)

    # Step 4: Print summary
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)

    totals = stats["buyback_totals"]
    print(f"\n  Total PUMP bought:          {totals['total_pump_bought']:>15,.2f} PUMP")
    print(f"  Total SOL spent:            {totals['total_sol_spent']:>15,.4f} SOL")
    print(f"  Total SOL received:         {totals['total_sol_received_as_funding']:>15,.4f} SOL")
    print(f"  Avg PUMP per SOL:           {totals['avg_pump_per_sol']:>15,.2f}")
    print(f"  PUMP sent to treasury:      {totals['total_pump_to_treasury']:>15,.2f} PUMP")
    print(f"  Current wallet balance:     {totals['current_buyback_wallet_pump_balance']:>15,.2f} PUMP")

    print(f"\n  Date range: {stats['summary']['first_tx_date']} → {stats['summary']['last_tx_date']}")
    print(f"  Total transactions: {stats['summary']['total_txs']}")

    print("\n  Monthly breakdown (PUMP bought):")
    for month, data in stats["monthly"].items():
        pump = data.get("pump_bought", 0)
        sol = data.get("sol_spent", 0)
        txs = data.get("buyback_count", 0)
        bar = "█" * min(int(pump / 1e9), 50)
        print(f"  {month}: {pump/1e9:>8.2f}B PUMP | {sol:>8,.1f} SOL | {txs:>4} txs  {bar}")

    print("\n  DEX distribution:")
    for dex, data in stats["dex_distribution"].items():
        pump = data.get("pump_bought", 0)
        txs = data.get("tx_count", 0)
        print(f"  {dex:<20}: {pump/1e9:>8.2f}B PUMP | {txs:>4} txs")

    print("\n  Top 5 largest single buybacks:")
    for i, b in enumerate(stats["top_10_largest_buybacks"][:5], 1):
        print(f"  {i}. {b['date']} — {b['pump_in']/1e9:.3f}B PUMP via {b['dex']}")

    # Step 5: Save output
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(stats, f, indent=2)
    print(f"\n✅ Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
