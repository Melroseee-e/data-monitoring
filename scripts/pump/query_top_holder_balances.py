#!/usr/bin/env python3
"""
Query actual PUMP balances for top non-CEX/DEX holders
BubbleMaps shows 0 for all balances, need to query via Helius
"""

import os
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
if not HELIUS_API_KEY:
    raise ValueError("HELIUS_API_KEY not found")

HELIUS_RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"

HOLDERS_FILE = BASE_DIR / "data" / "pump" / "raw" / "pump_top500_holders.json"
OUTPUT_FILE = BASE_DIR / "data" / "pump" / "raw" / "pump_top_holders_with_balances.json"

def get_token_balance(address, mint=PUMP_MINT):
    """Get PUMP token balance for an address"""
    try:
        response = requests.post(
            HELIUS_RPC,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getTokenAccountsByOwner",
                "params": [
                    address,
                    {"mint": mint},
                    {"encoding": "jsonParsed"}
                ]
            },
            timeout=30
        )
        result = response.json()

        if "result" in result and result["result"]["value"]:
            token_account = result["result"]["value"][0]
            balance_raw = int(token_account["account"]["data"]["parsed"]["info"]["tokenAmount"]["amount"])
            decimals = token_account["account"]["data"]["parsed"]["info"]["tokenAmount"]["decimals"]
            balance = balance_raw / (10 ** decimals)
            return balance
        return 0
    except Exception as e:
        print(f"Error querying {address[:8]}...: {e}")
        return None

def main():
    print("=" * 80)
    print("Querying Actual PUMP Balances for Top Holders")
    print("=" * 80)

    # Load Top 500 holders
    with open(HOLDERS_FILE, 'r') as f:
        data = json.load(f)

    holders = data.get("holders", [])

    # Filter non-CEX/DEX holders
    non_cex_dex = []
    for i, holder in enumerate(holders, 1):
        details = holder.get("address_details", {})
        is_cex = details.get("is_cex", False)
        is_dex = details.get("is_dex", False)

        if not is_cex and not is_dex:
            non_cex_dex.append({
                "rank": i,
                "address": holder.get("address", ""),
                "label": details.get("label", ""),
                "entity_id": details.get("entity_id", "")
            })

    print(f"\nFound {len(non_cex_dex)} non-CEX/DEX holders")
    print(f"Querying balances for top 50...")

    # Query balances for top 50
    results = []
    for i, holder in enumerate(non_cex_dex[:50], 1):
        address = holder["address"]
        print(f"[{i}/50] Querying {address[:8]}...{address[-8:]}", end=" ")

        balance = get_token_balance(address)
        if balance is not None:
            holder["balance"] = balance
            holder["balance_billions"] = balance / 1_000_000_000
            results.append(holder)
            print(f"✅ {balance:,.0f} PUMP ({balance/1e9:.2f}B)")
        else:
            print("❌ Failed")

        time.sleep(0.5)  # Rate limiting

    # Sort by balance
    results.sort(key=lambda x: x["balance"], reverse=True)

    # Print top 20
    print("\n" + "=" * 80)
    print("TOP 20 NON-CEX/DEX HOLDERS BY ACTUAL BALANCE")
    print("=" * 80)
    for i, holder in enumerate(results[:20], 1):
        print(f"{i:2d}. #{holder['rank']:3d} | {holder['address'][:8]}...{holder['address'][-8:]} | "
              f"{holder['balance_billions']:>8.2f}B PUMP | {holder['label'] or 'No label'}")

    # Save results
    output = {
        "generated_at": data["metadata"]["fetched_at"],
        "total_queried": len(results),
        "holders_with_balance": results
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Results saved to {OUTPUT_FILE}")

    # Summary stats
    total_balance = sum(h["balance"] for h in results)
    print(f"\n📊 SUMMARY:")
    print(f"Total balance (top 50 non-CEX/DEX): {total_balance:,.0f} PUMP ({total_balance/1e9:.2f}B)")
    print(f"Average balance: {total_balance/len(results):,.0f} PUMP")
    print(f"Holders with >1B PUMP: {sum(1 for h in results if h['balance'] > 1e9)}")

if __name__ == "__main__":
    main()
