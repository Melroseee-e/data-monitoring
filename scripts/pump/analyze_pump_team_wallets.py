#!/usr/bin/env python3
"""
PUMP Team & Investor Wallet Analysis
Traces all PUMP-related activity for confirmed team/investor wallets
since TGE (2025-07-12).

Target wallets:
  - Team #1:     77DsB9kw8u8eKesicT44hGirsj5A2SicGdFPQZZEzPXe
  - Investor #1: 9UcygiamY92yGntGkUkBKi4SdApxkBMZd9QSo6wMC2dN
  - Aug21 Trio:  85WTujfJ..., 96HiV4cG..., ERRGqu3d...

Output: data/pump/core/pump_team_analysis.json
"""

import json
import time
import requests
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

HELIUS_API_KEY = "6bb10a8e-f7b7-4216-a9ad-54d7cd762b0e"
HELIUS_API_BASE = f"https://api.helius.xyz/v0"
HELIUS_RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
TOKEN_CUSTODIAN = "Cfq1ts1iFr1eUWWBm8eFxUzm5R3YA3UvMZznwiShbgZt"
TGE_TIMESTAMP = 1752278400  # 2025-07-12 00:00 UTC

BASE_DIR = Path(__file__).resolve().parents[2]
OUTPUT_FILE = BASE_DIR / "data" / "pump" / "core" / "pump_team_analysis.json"
ADDRESSES_FILE = BASE_DIR / "data" / "pump" / "core" / "pump_addresses.json"
EXCHANGE_FILE = BASE_DIR / "data" / "exchange_addresses_normalized.json"

# Target wallets
TARGET_WALLETS = {
    "77DsB9kw8u8eKesicT44hGirsj5A2SicGdFPQZZEzPXe": {
        "label": "Team Wallet #1 (CONFIRMED)",
        "type": "team",
        "expected_received_B": 3.75,
        "received_date": "2025-07-14",
    },
    "9UcygiamY92yGntGkUkBKi4SdApxkBMZd9QSo6wMC2dN": {
        "label": "Investor Wallet #1 (CONFIRMED)",
        "type": "investor",
        "expected_received_B": 20.0,
        "received_date": "2025-07-14",
    },
    "85WTujfJ9meJq5hfjAeb5gftj7n8Q7QTsZJbRqMD5ERS": {
        "label": "Investor Aug21 #1",
        "type": "investor",
        "expected_received_B": 30.0,
        "received_date": "2025-08-21",
    },
    "96HiV4cGWTJNCjGVff3RTHgPXmpYz7MSrGTAmxNKVWM9": {
        "label": "Investor Aug21 #2",
        "type": "investor",
        "expected_received_B": 23.0,
        "received_date": "2025-08-21",
    },
    "ERRGqu3dh6zYBg7MNAHKL33TyVb7efMmaKxnmdukdNYa": {
        "label": "Investor Aug21 #3",
        "type": "investor",
        "expected_received_B": 17.0,
        "received_date": "2025-08-21",
    },
}


def load_cex_lookup():
    """Build {solana_address: exchange_name} lookup from exchange_addresses_normalized.json."""
    with open(EXCHANGE_FILE) as f:
        data = json.load(f)
    lookup = {}
    for exchange_name, chains in data.items():
        if isinstance(chains, dict) and "solana" in chains:
            for addr in chains["solana"]:
                lookup[addr] = exchange_name
    print(f"Loaded {len(lookup)} Solana CEX addresses")
    return lookup


def rpc_call(method, params):
    resp = requests.post(
        HELIUS_RPC,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=30,
    )
    data = resp.json()
    if "error" in data:
        print(f"  RPC error: {data['error']}")
        return None
    return data.get("result")


def get_pump_balance(address):
    """Get current PUMP token balance for a wallet."""
    result = rpc_call("getTokenAccountsByOwner", [
        address,
        {"mint": PUMP_MINT},
        {"encoding": "jsonParsed"},
    ])
    if result and result.get("value"):
        total = sum(
            a["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"] or 0
            for a in result["value"]
        )
        return total
    return 0.0


def fetch_enhanced_transactions(address, before=None, limit=100):
    """Fetch parsed transactions from Helius Enhanced API."""
    params = {"api-key": HELIUS_API_KEY, "limit": limit}
    if before:
        params["before"] = before

    url = f"{HELIUS_API_BASE}/addresses/{address}/transactions"
    for attempt in range(3):
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 429:
            wait = 5 * (attempt + 1)
            print(f"  Rate limited, sleeping {wait}s...")
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            print(f"  Error {resp.status_code}: {resp.text[:200]}")
            return []
        return resp.json()
    return []


def fetch_all_transactions(address, stop_before_ts=None):
    """Fetch complete transaction history for a wallet."""
    all_txs = []
    before = None
    page = 0

    while True:
        page += 1
        txs = fetch_enhanced_transactions(address, before=before, limit=100)

        if not txs:
            break

        all_txs.extend(txs)

        oldest_ts = min(tx.get("timestamp", 0) for tx in txs)
        newest_ts = max(tx.get("timestamp", 0) for tx in txs)
        oldest_date = datetime.fromtimestamp(oldest_ts, tz=timezone.utc).strftime("%Y-%m-%d") if oldest_ts else "?"
        newest_date = datetime.fromtimestamp(newest_ts, tz=timezone.utc).strftime("%Y-%m-%d") if newest_ts else "?"

        print(f"  Page {page}: {len(txs)} txs | {oldest_date} → {newest_date} | total: {len(all_txs)}")

        # Stop if we've gone past TGE
        if stop_before_ts and oldest_ts < stop_before_ts:
            print(f"  Reached pre-TGE, stopping.")
            break

        if len(txs) < 100:
            break

        before = txs[-1]["signature"]
        time.sleep(0.3)

    return all_txs


def classify_tx(tx, wallet_addr, cex_lookup):
    """
    Classify a transaction for a given wallet address.
    Returns dict with type, pump amounts, and destination info.
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
        "pump_in": 0.0,
        "pump_out": 0.0,
        "pump_source": None,
        "pump_destination": None,
        "from_custodian": False,
        "to_cex": False,
        "cex_name": None,
        "to_wallet": None,
        "source": source,
        "tx_type": tx_type,
    }

    for tt in token_transfers:
        if tt.get("mint") != PUMP_MINT:
            continue
        amount = tt.get("tokenAmount", 0) or 0
        from_acc = tt.get("fromUserAccount", "") or ""
        to_acc = tt.get("toUserAccount", "") or ""

        if to_acc == wallet_addr:
            result["pump_in"] += amount
            result["pump_source"] = from_acc
            if from_acc == TOKEN_CUSTODIAN:
                result["from_custodian"] = True

        if from_acc == wallet_addr:
            result["pump_out"] += amount
            result["pump_destination"] = to_acc
            # Check if destination is a CEX
            if to_acc in cex_lookup:
                result["to_cex"] = True
                result["cex_name"] = cex_lookup[to_acc]
            else:
                result["to_wallet"] = to_acc

    # Classify type
    if result["from_custodian"] and result["pump_in"] > 0:
        result["type"] = "received_from_custodian"
    elif result["pump_in"] > 0 and tx_type in ("SWAP", "DEX_TRADE"):
        result["type"] = "dex_swap_in"  # received from DEX swap
    elif result["pump_out"] > 0:
        if result["to_cex"]:
            result["type"] = "cex_deposit"
        elif tx_type in ("SWAP", "DEX_TRADE"):
            result["type"] = "dex_swap_out"
        elif result["pump_destination"]:
            result["type"] = "wallet_transfer"
        else:
            result["type"] = "pump_out_unknown"
    elif result["pump_in"] > 0:
        result["type"] = "pump_received"
    else:
        result["type"] = "other"

    return result


def analyze_wallet(address, wallet_info, cex_lookup):
    """Fetch and analyze all transactions for a wallet."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {wallet_info['label']}")
    print(f"Address:   {address}")
    print(f"Expected:  {wallet_info['expected_received_B']}B PUMP received {wallet_info['received_date']}")
    print(f"{'='*60}")

    # Get current balance
    current_balance = get_pump_balance(address)
    print(f"Current PUMP balance: {current_balance/1e9:.3f}B")

    # Fetch all transactions since TGE
    txs = fetch_all_transactions(address, stop_before_ts=TGE_TIMESTAMP)

    # Classify each tx
    classified = []
    for tx in txs:
        c = classify_tx(tx, address, cex_lookup)
        classified.append(c)

    # Summary stats
    pump_in_total = sum(c["pump_in"] for c in classified if c["pump_in"] > 0)
    pump_out_total = sum(c["pump_out"] for c in classified if c["pump_out"] > 0)
    from_custodian_total = sum(c["pump_in"] for c in classified if c["from_custodian"])
    cex_deposits = [c for c in classified if c["type"] == "cex_deposit"]
    wallet_transfers = [c for c in classified if c["type"] == "wallet_transfer"]
    dex_swaps_out = [c for c in classified if c["type"] == "dex_swap_out"]

    total_to_cex = sum(c["pump_out"] for c in cex_deposits)
    total_to_wallets = sum(c["pump_out"] for c in wallet_transfers)
    total_to_dex = sum(c["pump_out"] for c in dex_swaps_out)

    # CEX breakdown
    cex_breakdown = defaultdict(float)
    for c in cex_deposits:
        if c["cex_name"]:
            cex_breakdown[c["cex_name"]] += c["pump_out"]

    # Wallet transfer destinations
    wallet_dest_breakdown = defaultdict(float)
    for c in wallet_transfers:
        if c["pump_destination"]:
            wallet_dest_breakdown[c["pump_destination"]] += c["pump_out"]

    # Timeline of significant outflows (>100M PUMP = >0.1B)
    significant_outflows = sorted(
        [c for c in classified if c["pump_out"] > 100_000_000],
        key=lambda x: x["timestamp"],
    )

    sell_rate = (pump_out_total / from_custodian_total * 100) if from_custodian_total > 0 else 0.0

    print(f"\nResults:")
    print(f"  Total PUMP received:        {pump_in_total/1e9:.3f}B")
    print(f"  From Token Custodian:       {from_custodian_total/1e9:.3f}B")
    print(f"  Total PUMP sent out:        {pump_out_total/1e9:.3f}B")
    print(f"  → To CEX:                   {total_to_cex/1e9:.3f}B")
    print(f"  → To wallets:               {total_to_wallets/1e9:.3f}B")
    print(f"  → Via DEX:                  {total_to_dex/1e9:.3f}B")
    print(f"  Current balance:            {current_balance/1e9:.3f}B")
    print(f"  Sell rate (out/received):   {sell_rate:.1f}%")
    print(f"  CEX breakdown:")
    for cex, amt in sorted(cex_breakdown.items(), key=lambda x: x[1], reverse=True):
        print(f"    {cex}: {amt/1e9:.3f}B")
    print(f"  Significant outflows ({len(significant_outflows)}):")
    for c in significant_outflows[:10]:
        dest = c["cex_name"] if c["to_cex"] else (c["pump_destination"][:16] + "..." if c["pump_destination"] else "?")
        print(f"    {c['date']}: {c['pump_out']/1e9:.3f}B → {dest} ({c['type']})")

    return {
        "address": address,
        "label": wallet_info["label"],
        "type": wallet_info["type"],
        "expected_received_B": wallet_info["expected_received_B"],
        "received_date": wallet_info["received_date"],
        "current_balance": current_balance,
        "current_balance_B": round(current_balance / 1e9, 4),
        "total_txs": len(classified),
        "pump_stats": {
            "total_received": round(pump_in_total, 2),
            "from_custodian": round(from_custodian_total, 2),
            "total_sent": round(pump_out_total, 2),
            "to_cex": round(total_to_cex, 2),
            "to_wallets": round(total_to_wallets, 2),
            "via_dex": round(total_to_dex, 2),
            "sell_rate_pct": round(sell_rate, 2),
            "current_balance": round(current_balance, 2),
        },
        "cex_breakdown": {
            k: round(v, 2) for k, v in sorted(cex_breakdown.items(), key=lambda x: x[1], reverse=True)
        },
        "wallet_transfer_destinations": {
            k: round(v, 2) for k, v in sorted(wallet_dest_breakdown.items(), key=lambda x: x[1], reverse=True)[:10]
        },
        "significant_outflows": [
            {
                "date": c["date"],
                "pump_out": round(c["pump_out"], 2),
                "pump_out_B": round(c["pump_out"] / 1e9, 4),
                "type": c["type"],
                "destination": c["cex_name"] if c["to_cex"] else c["pump_destination"],
                "signature": c["signature"],
            }
            for c in significant_outflows
        ],
        "all_transactions_classified": [
            {
                "date": c["date"],
                "type": c["type"],
                "pump_in": round(c["pump_in"], 2),
                "pump_out": round(c["pump_out"], 2),
                "from_custodian": c["from_custodian"],
                "to_cex": c["to_cex"],
                "cex_name": c["cex_name"],
                "pump_destination": c["pump_destination"],
                "source": c["source"],
                "signature": c["signature"],
            }
            for c in classified
            if c["pump_in"] > 0 or c["pump_out"] > 0
        ],
    }


def main():
    print("=" * 70)
    print("PUMP Team & Investor Wallet Analysis".center(70))
    print("=" * 70)

    cex_lookup = load_cex_lookup()

    results = {}
    summary_rows = []

    for address, wallet_info in TARGET_WALLETS.items():
        result = analyze_wallet(address, wallet_info, cex_lookup)
        results[address] = result
        summary_rows.append({
            "label": wallet_info["label"],
            "address": address[:20] + "...",
            "received_B": wallet_info["expected_received_B"],
            "sent_B": round(result["pump_stats"]["total_sent"] / 1e9, 3),
            "to_cex_B": round(result["pump_stats"]["to_cex"] / 1e9, 3),
            "current_B": round(result["current_balance"] / 1e9, 3),
            "sell_rate": f"{result['pump_stats']['sell_rate_pct']:.1f}%",
        })
        time.sleep(1)  # Brief pause between wallets

    # Print final summary table
    print("\n" + "=" * 70)
    print("SUMMARY".center(70))
    print("=" * 70)
    print(f"{'Wallet':<35} {'Recv':>8} {'Sent':>8} {'CEX':>8} {'Hold':>8} {'SellRate':>9}")
    print("-" * 70)
    for row in summary_rows:
        print(f"{row['label']:<35} {row['received_B']:>7.2f}B {row['sent_B']:>7.2f}B {row['to_cex_B']:>7.2f}B {row['current_B']:>7.2f}B {row['sell_rate']:>9}")

    total_received = sum(w["expected_received_B"] for w in TARGET_WALLETS.values())
    total_sent = sum(r["pump_stats"]["total_sent"] / 1e9 for r in results.values())
    total_to_cex = sum(r["pump_stats"]["to_cex"] / 1e9 for r in results.values())
    total_current = sum(r["current_balance"] / 1e9 for r in results.values())

    print("-" * 70)
    print(f"{'TOTAL':<35} {total_received:>7.2f}B {total_sent:>7.2f}B {total_to_cex:>7.2f}B {total_current:>7.2f}B")

    # Build output
    output = {
        "metadata": {
            "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "token": "PUMP",
            "contract": PUMP_MINT,
            "wallets_analyzed": len(TARGET_WALLETS),
            "analysis_method": "Helius Enhanced API - full transaction trace from TGE",
        },
        "summary": {
            "total_received_B": total_received,
            "total_sent_B": round(total_sent, 3),
            "total_to_cex_B": round(total_to_cex, 3),
            "total_current_hold_B": round(total_current, 3),
            "overall_sell_rate_pct": round(total_sent / total_received * 100, 1) if total_received > 0 else 0,
        },
        "wallets": results,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n✅ Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
