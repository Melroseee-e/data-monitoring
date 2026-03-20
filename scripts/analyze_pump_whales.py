#!/usr/bin/env python3
"""
PUMP Token Whale & Top Holder Analysis
Fetches top token accounts via getTokenLargestAccounts, resolves owner wallets,
classifies each (official/CEX/vesting/independent), then traces PUMP activity
for independent whale addresses since TGE (2025-07-12).

Output: data/pump_whale_analysis.json
"""

import json
import time
import requests
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

HELIUS_API_KEY = "6bb10a8e-f7b7-4216-a9ad-54d7cd762b0e"
HELIUS_RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
HELIUS_BASE = "https://api.helius.xyz/v0"

PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
TGE_TIMESTAMP = 1752278400  # 2025-07-12 00:00 UTC

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "data" / "pump_whale_analysis.json"
EXCHANGE_FILE = BASE_DIR / "data" / "exchange_addresses_normalized.json"
ADDRESSES_FILE = BASE_DIR / "data" / "pump_addresses.json"

# Addresses to exclude from "independent whale" classification
OFFICIAL_ADDRESSES = {
    "Cfq1ts1iFr1eUWWBm8eFxUzm5R3YA3UvMZznwiShbgZt": "Token Custodian",
    "G8CcfRffqZWHSAQJXLDfwbAkGE95SddUqVXnTrL4kqjm": "Buyback Treasury",
    "3vkpy5YHqnqJTnA5doWTpcgKyZiYsaXYzYM9wm8s3WTi": "Buyback Wallet",
    "8UhbNoBXmGoxJr2TeWW8wmSMoWmjS2rTT2tVJxzuTogC": "Community Reserve",
    "9pkFKCR1mdS31JxjKdtmWg2awZUg6vJUYVY722DAcXzv": "Squads Vault #1",
    "BBvQteuawKB2UtExfevL8HYLjWWsgmWXsp922vFbvCfT": "Squads Vault #2",
    "GTeSSwovPiVirpvWJpThUWiLDSLsuApmJw621Yom3MhB": "Squads Vault #3",
    "AvqFxKNrYZNvxsj2oWhLW8det68HzCXBqswshoD2TdT6": "Operational Vault",
    "GhFaBi8sy3M5mgG97YguQ6J3f7XH4JwV5CoW8MbzRgAU": "Squads Vault #4",
    "5v7ZZg1D1si417WhUQF9Br2dRQEnd1sTbCfesscUCVKE": "Squads Vault #5",
    "2WHL4XiNGKW9NgSwsJeG7WG2kD35Bi44rZoLrXHEz3dw": "Operational Wallet",
    "77DsB9kw8u8eKesicT44hGirsj5A2SicGdFPQZZEzPXe": "Team Wallet #1",
    "9UcygiamY92yGntGkUkBKi4SdApxkBMZd9QSo6wMC2dN": "Investor Wallet #1",
    "85WTujfJ9meJq5hfjAeb5gftj7n8Q7QTsZJbRqMD5ERS": "Aug21 Investor #1",
    "96HiV4cGWTJNCjGVff3RTHgPXmpYz7MSrGTAmxNKVWM9": "Aug21 Investor #2",
    "ERRGqu3dh6zYBg7MNAHKL33TyVb7efMmaKxnmdukdNYa": "Aug21 Investor #3",
    "5D95TQGUmg71zrM7CJZiTKpjr3QshNcaZVkrLi8Uh3CG": "ICO Distribution PDA",
}


def load_cex_lookup():
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
        return None
    return data.get("result")


def get_token_largest_accounts():
    """Get top 20 PUMP token accounts."""
    result = rpc_call("getTokenLargestAccounts", [PUMP_MINT, {"commitment": "confirmed"}])
    if result:
        return result.get("value", [])
    return []


def get_account_owner(token_account_address):
    """Resolve the owner wallet of a token account."""
    result = rpc_call("getAccountInfo", [token_account_address, {"encoding": "jsonParsed"}])
    if result and result.get("value"):
        parsed = result["value"].get("data", {}).get("parsed", {})
        return parsed.get("info", {}).get("owner", None)
    return None


def get_pump_balance(owner_address):
    """Get current PUMP balance for an owner wallet."""
    result = rpc_call("getTokenAccountsByOwner", [
        owner_address,
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
    """Fetch parsed transactions via Helius Enhanced API."""
    params = {"api-key": HELIUS_API_KEY, "limit": limit}
    if before:
        params["before"] = before
    url = f"{HELIUS_BASE}/addresses/{address}/transactions"
    for attempt in range(3):
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 429:
            wait = 5 * (attempt + 1)
            print(f"  Rate limited, sleeping {wait}s...")
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            return []
        return resp.json()
    return []


def fetch_all_transactions(address, stop_before_ts=None, max_pages=30):
    """Fetch complete transaction history for a wallet (capped at max_pages)."""
    all_txs = []
    before = None
    page = 0

    while page < max_pages:
        page += 1
        txs = fetch_enhanced_transactions(address, before=before, limit=100)
        if not txs:
            break

        all_txs.extend(txs)
        oldest_ts = min(tx.get("timestamp", 0) for tx in txs)
        newest_ts = max(tx.get("timestamp", 0) for tx in txs)
        oldest_date = datetime.fromtimestamp(oldest_ts, tz=timezone.utc).strftime("%Y-%m-%d") if oldest_ts else "?"
        print(f"    Page {page}: {len(txs)} txs | {oldest_date} → now | total={len(all_txs)}")

        if stop_before_ts and oldest_ts < stop_before_ts:
            break
        if len(txs) < 100:
            break

        before = txs[-1]["signature"]
        time.sleep(0.3)

    return all_txs


def analyze_whale(address, label, balance_B, cex_lookup):
    """Analyze PUMP activity for an independent whale address."""
    print(f"\n  → {label[:40]} ({balance_B:.3f}B)")

    txs = fetch_all_transactions(address, stop_before_ts=TGE_TIMESTAMP, max_pages=20)

    total_pump_in = 0.0
    total_pump_out = 0.0
    total_to_cex = 0.0
    total_to_dex = 0.0
    total_to_wallets = 0.0
    cex_breakdown = defaultdict(float)
    outflow_events = []

    for tx in txs:
        ts = tx.get("timestamp", 0)
        date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d") if ts else "?"
        tx_type = tx.get("type", "UNKNOWN")

        for tt in (tx.get("tokenTransfers") or []):
            if tt.get("mint") != PUMP_MINT:
                continue
            amount = tt.get("tokenAmount", 0) or 0
            from_acc = tt.get("fromUserAccount", "") or ""
            to_acc = tt.get("toUserAccount", "") or ""

            if to_acc == address:
                total_pump_in += amount

            if from_acc == address and amount > 0:
                total_pump_out += amount
                if to_acc in cex_lookup:
                    total_to_cex += amount
                    cex_breakdown[cex_lookup[to_acc]] += amount
                elif tx_type in ("SWAP", "DEX_TRADE"):
                    total_to_dex += amount
                else:
                    total_to_wallets += amount

                if amount > 100_000_000:  # >100M
                    outflow_events.append({
                        "date": date,
                        "amount_B": round(amount / 1e9, 4),
                        "destination": cex_lookup.get(to_acc, to_acc[:20] + "..."),
                        "type": "cex" if to_acc in cex_lookup else ("dex" if tx_type in ("SWAP", "DEX_TRADE") else "wallet"),
                        "signature": tx.get("signature", ""),
                    })

    sell_rate = (total_pump_out / balance_B / 1e9 * 100) if balance_B > 0 else 0.0

    # Activity classification
    if total_pump_out == 0:
        activity = "HOLDING"
    elif total_to_cex > total_pump_out * 0.5:
        activity = "CEX_SELLING"
    elif total_to_dex > total_pump_out * 0.5:
        activity = "DEX_SELLING"
    else:
        activity = "DISTRIBUTING"

    return {
        "address": address,
        "label": label,
        "current_balance_B": round(balance_B, 4),
        "total_pump_in_B": round(total_pump_in / 1e9, 4),
        "total_pump_out_B": round(total_pump_out / 1e9, 4),
        "to_cex_B": round(total_to_cex / 1e9, 4),
        "to_dex_B": round(total_to_dex / 1e9, 4),
        "to_wallets_B": round(total_to_wallets / 1e9, 4),
        "sell_rate_pct": round(sell_rate, 2),
        "activity": activity,
        "cex_breakdown": {k: round(v / 1e9, 4) for k, v in sorted(cex_breakdown.items(), key=lambda x: x[1], reverse=True)},
        "significant_outflows": sorted(outflow_events, key=lambda x: x["date"])[-20:],
        "tx_count": len(txs),
    }


def main():
    print("=" * 70)
    print("PUMP Whale & Top Holder Analysis".center(70))
    print("=" * 70)

    cex_lookup = load_cex_lookup()

    # Step 1: Get top 20 PUMP token accounts
    print("\nFetching top PUMP token accounts...")
    top_accounts = get_token_largest_accounts()
    print(f"Got {len(top_accounts)} accounts")

    # Step 2: Resolve owners
    print("\nResolving owner wallets...")
    holders = []
    for acc in top_accounts:
        ta = acc["address"]
        balance = acc["uiAmount"] or 0
        owner = get_account_owner(ta)
        if owner:
            holders.append({
                "token_account": ta,
                "owner": owner,
                "balance_B": round(balance / 1e9, 4),
            })
        time.sleep(0.1)

    print(f"\nTop holders with owners ({len(holders)}):")
    print(f"{'Rank':<5} {'Owner':<45} {'Balance':>10} {'Type'}")
    print("-" * 80)

    # Step 3: Classify each holder
    classified = []
    for i, h in enumerate(holders, 1):
        owner = h["owner"]
        bal = h["balance_B"]

        if owner in OFFICIAL_ADDRESSES:
            cat = "official"
            label = OFFICIAL_ADDRESSES[owner]
        elif owner in cex_lookup:
            cat = "cex"
            label = f"CEX: {cex_lookup[owner]}"
        else:
            cat = "whale"
            label = f"Unknown Whale #{i}"

        h["category"] = cat
        h["label"] = label
        classified.append(h)
        print(f"{i:<5} {owner[:44]:<45} {bal:>9.3f}B  [{cat}] {label}")

    # Step 4: Analyze independent whale wallets
    print("\n\nAnalyzing independent whale wallets...")
    whale_wallets = [h for h in classified if h["category"] == "whale"]
    whale_analyses = {}

    for h in whale_wallets:
        addr = h["owner"]
        bal = h["balance_B"]
        label = h["label"]
        analysis = analyze_whale(addr, label, bal, cex_lookup)
        whale_analyses[addr] = analysis
        time.sleep(0.5)

    # Step 5: Also pull known tracked wallets for comparison
    known_tracked = {
        "9UcygiamY92yGntGkUkBKi4SdApxkBMZd9QSo6wMC2dN": {
            "label": "Investor Wallet #1 (Squads/Kraken)", "balance_B": 8.8,
            "current_balance_B": 8.8, "total_pump_out_B": 11.2, "to_cex_B": 11.2,
            "sell_rate_pct": 56.0, "activity": "CEX_SELLING",
            "cex_breakdown": {"Kraken": 11.2}, "category": "investor"
        },
        "85WTujfJ9meJq5hfjAeb5gftj7n8Q7QTsZJbRqMD5ERS": {
            "label": "Aug21 Investor #1 (LOCKED)", "balance_B": 30.0,
            "current_balance_B": 30.0, "total_pump_out_B": 0.0, "to_cex_B": 0.0,
            "sell_rate_pct": 0.0, "activity": "HOLDING", "category": "investor"
        },
        "96HiV4cGWTJNCjGVff3RTHgPXmpYz7MSrGTAmxNKVWM9": {
            "label": "Aug21 Investor #2 (LOCKED)", "balance_B": 23.0,
            "current_balance_B": 23.0, "total_pump_out_B": 0.0, "to_cex_B": 0.0,
            "sell_rate_pct": 0.0, "activity": "HOLDING", "category": "investor"
        },
        "ERRGqu3dh6zYBg7MNAHKL33TyVb7efMmaKxnmdukdNYa": {
            "label": "Aug21 Investor #3 (LOCKED)", "balance_B": 17.0,
            "current_balance_B": 17.0, "total_pump_out_B": 0.0, "to_cex_B": 0.0,
            "sell_rate_pct": 0.0, "activity": "HOLDING", "category": "investor"
        },
    }

    # Step 6: CEX holdings summary
    cex_holdings = {}
    for h in classified:
        if h["category"] == "cex":
            ex_name = cex_lookup.get(h["owner"], h["owner"])
            cex_holdings[ex_name] = cex_holdings.get(ex_name, 0) + h["balance_B"]

    total_cex_B = sum(cex_holdings.values())

    # Step 7: Supply breakdown
    total_supply_B = 1_000_000.0 / 1000  # 1T / 1000 = 1000B
    # Approximate current distribution
    token_custodian_B = next((h["balance_B"] for h in classified if h["label"] == "Token Custodian"), 0)
    buyback_treasury_B = next((h["balance_B"] for h in classified if h["label"] == "Buyback Treasury"), 0)
    community_reserve_B = next((h["balance_B"] for h in classified if h["label"] == "Community Reserve"), 0)

    # All vesting/official non-custodian/non-buyback
    vesting_B = sum(h["balance_B"] for h in classified if h["category"] == "official"
                    and h["label"] not in ("Token Custodian", "Buyback Treasury", "Community Reserve",
                                           "Operational Vault", "Operational Wallet",
                                           "Buyback Wallet", "ICO Distribution PDA"))

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY".center(70))
    print("=" * 70)

    print(f"\nCEX Holdings (on-chain):")
    for ex, bal in sorted(cex_holdings.items(), key=lambda x: x[1], reverse=True):
        print(f"  {ex:<20} {bal:.3f}B")
    print(f"  {'TOTAL':<20} {total_cex_B:.3f}B")

    print(f"\nIndependent Whales:")
    for addr, a in whale_analyses.items():
        print(f"  {a['label'][:35]:<35} {a['current_balance_B']:>8.3f}B  sell={a['sell_rate_pct']:.1f}%  {a['activity']}")

    # Build output
    output = {
        "metadata": {
            "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "token": "PUMP",
            "contract": PUMP_MINT,
            "data_source": "Helius RPC getTokenLargestAccounts + Enhanced API",
            "notes": "Top 20 PUMP token accounts resolved to owner wallets, classified, and analyzed",
        },
        "supply_breakdown": {
            "total_supply_B": 1000.0,
            "token_custodian_locked_B": round(token_custodian_B, 3),
            "buyback_treasury_B": round(buyback_treasury_B, 3),
            "community_reserve_B": round(community_reserve_B, 3),
            "vesting_locked_B": round(vesting_B, 3),
            "cex_hot_wallets_B": round(total_cex_B, 3),
            "known_investors_B": round(sum(v["current_balance_B"] for v in known_tracked.values()), 3),
            "independent_whales_B": round(sum(a["current_balance_B"] for a in whale_analyses.values()), 3),
        },
        "cex_holdings": {
            k: round(v, 4)
            for k, v in sorted(cex_holdings.items(), key=lambda x: x[1], reverse=True)
        },
        "top_holders_classified": [
            {
                "rank": i + 1,
                "owner": h["owner"],
                "token_account": h["token_account"],
                "balance_B": h["balance_B"],
                "category": h["category"],
                "label": h["label"],
            }
            for i, h in enumerate(classified)
        ],
        "independent_whale_analysis": whale_analyses,
        "known_investor_summary": known_tracked,
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n✅ Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
