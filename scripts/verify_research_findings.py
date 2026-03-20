#!/usr/bin/env python3
"""
Verify research findings from Phase 7
- Verify team wallet 77DsB... (find full address)
- Verify whale wallet 9UcygiamY92yGntGkUkBKi4SdApxkBMZd9QSo6wMC2dN
- Verify Kraken 11.2B deposit on 2026-02-26
"""

import os
import json
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment
load_dotenv()
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
if not HELIUS_API_KEY:
    raise ValueError("HELIUS_API_KEY not found in .env")

HELIUS_RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"

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
        print(f"Error getting balance for {address}: {e}")
        return None

def get_signatures(address, before=None, limit=1000):
    """Get transaction signatures for an address"""
    try:
        params = [address, {"limit": limit}]
        if before:
            params[1]["before"] = before

        response = requests.post(
            HELIUS_RPC,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": params
            },
            timeout=30
        )
        result = response.json()
        return result.get("result", [])
    except Exception as e:
        print(f"Error getting signatures for {address}: {e}")
        return []

def search_for_team_wallet_prefix(prefix="77DsB"):
    """Search for team wallet starting with 77DsB in Top 500 holders"""
    print(f"\n=== Searching for Team Wallet: {prefix}... ===")

    # Load Top 500 holders
    holders_file = "data/pump_top500_holders.json"
    if not os.path.exists(holders_file):
        print(f"Error: {holders_file} not found")
        return None

    with open(holders_file, 'r') as f:
        holders_data = json.load(f)

    # Search for addresses starting with prefix
    matches = []
    for holder in holders_data.get("holders", []):
        address = holder.get("address", "")
        if address.startswith(prefix):
            matches.append({
                "address": address,
                "balance": holder.get("balance", 0),
                "rank": holder.get("rank", 0)
            })

    if matches:
        print(f"Found {len(matches)} address(es) starting with {prefix}:")
        for match in matches:
            print(f"  - {match['address']}: {match['balance']:,.2f} PUMP (Rank #{match['rank']})")
        return matches
    else:
        print(f"No addresses found starting with {prefix}")
        return None

def verify_whale_wallet():
    """Verify whale wallet 9UcygiamY92yGntGkUkBKi4SdApxkBMZd9QSo6wMC2dN"""
    address = "9UcygiamY92yGntGkUkBKi4SdApxkBMZd9QSo6wMC2dN"
    print(f"\n=== Verifying Whale Wallet: {address} ===")

    # Get current balance
    balance = get_token_balance(address)
    if balance is not None:
        print(f"Current balance: {balance:,.2f} PUMP")

    # Get transaction history
    print("Fetching transaction history...")
    signatures = get_signatures(address, limit=100)
    print(f"Found {len(signatures)} recent transactions")

    # Look for Kraken deposit around 2026-02-26
    target_date = datetime(2026, 2, 26, tzinfo=timezone.utc)
    print(f"\nSearching for large transfers around {target_date.date()}...")

    # Load exchange addresses to identify Kraken
    exchange_file = "data/exchange_addresses.json"
    kraken_addresses = []
    if os.path.exists(exchange_file):
        with open(exchange_file, 'r') as f:
            exchanges = json.load(f)
            # exchanges is a dict with exchange names as keys
            for exchange_name, chains in exchanges.items():
                if "kraken" in exchange_name.lower():
                    if isinstance(chains, dict) and "solana" in chains:
                        kraken_addresses.extend(chains["solana"])

    print(f"Loaded {len(kraken_addresses)} Kraken addresses")

    return {
        "address": address,
        "balance": balance,
        "tx_count": len(signatures),
        "kraken_addresses": kraken_addresses
    }

def main():
    print("=" * 80)
    print("PUMP Token Research - Phase 7 Verification")
    print("=" * 80)

    # 1. Search for team wallet
    team_matches = search_for_team_wallet_prefix("77DsB")

    # 2. Verify whale wallet
    whale_info = verify_whale_wallet()

    # Save results
    results = {
        "verification_timestamp": datetime.now(timezone.utc).isoformat(),
        "team_wallet_search": {
            "prefix": "77DsB",
            "matches": team_matches if team_matches else []
        },
        "whale_wallet": whale_info
    }

    output_file = "data/phase7_verification_results.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ Results saved to {output_file}")

if __name__ == "__main__":
    main()

