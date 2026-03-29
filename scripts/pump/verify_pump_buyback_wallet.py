#!/usr/bin/env python3
"""
Verify PUMP token buyback wallet and query its current balance.

This script:
1. Loads Helius API key from .env
2. Queries the buyback wallet's PUMP token balance
3. Gets recent transaction count
4. Updates pump_addresses.json with current data
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")

HELIUS_API_KEY = os.environ.get("HELIUS_API_KEY", "")
if not HELIUS_API_KEY:
    print("ERROR: HELIUS_API_KEY not found in .env", file=sys.stderr)
    sys.exit(1)

HELIUS_RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
BUYBACK_WALLET = "3vkpy5YHqnqJTnA5doWTpcgKyZiYsaXYzYM9wm8s3WTi"
TREASURY_WALLET = "G8CcfRffqZWHSAQJXLDfwbAkGE95SddUqVXnTrL4kqjm"

ADDRESSES_FILE = BASE_DIR / "data" / "pump" / "core" / "pump_addresses.json"


def rpc_call(method: str, params: list) -> dict:
    """Make a JSON-RPC call to Helius."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": params
    }
    resp = requests.post(HELIUS_RPC, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise Exception(f"RPC error: {data['error']}")
    return data.get("result")


def get_token_balance(wallet: str, mint: str) -> float:
    """Get token balance for a wallet address."""
    try:
        # Get token accounts owned by wallet
        result = rpc_call("getTokenAccountsByOwner", [
            wallet,
            {"mint": mint},
            {"encoding": "jsonParsed"}
        ])

        if not result or not result.get("value"):
            return 0.0

        # Sum up all token account balances
        total = 0.0
        for account in result["value"]:
            parsed = account["account"]["data"]["parsed"]["info"]
            amount = float(parsed["tokenAmount"]["uiAmount"] or 0)
            total += amount

        return total
    except Exception as e:
        print(f"Error getting balance for {wallet}: {e}", file=sys.stderr)
        return 0.0


def get_recent_tx_count(wallet: str, limit: int = 100) -> int:
    """Get count of recent transactions for a wallet."""
    try:
        result = rpc_call("getSignaturesForAddress", [
            wallet,
            {"limit": limit}
        ])
        return len(result) if result else 0
    except Exception as e:
        print(f"Error getting transactions for {wallet}: {e}", file=sys.stderr)
        return 0


def main():
    print("=== PUMP Buyback Wallet Verification ===\n")

    # Query buyback wallet
    print(f"Querying buyback wallet: {BUYBACK_WALLET}")
    buyback_balance = get_token_balance(BUYBACK_WALLET, PUMP_MINT)
    buyback_tx_count = get_recent_tx_count(BUYBACK_WALLET, 1000)

    print(f"  Balance: {buyback_balance:,.2f} PUMP")
    print(f"  Recent transactions (last 1000): {buyback_tx_count}")

    # Query treasury wallet
    print(f"\nQuerying treasury wallet: {TREASURY_WALLET}")
    treasury_balance = get_token_balance(TREASURY_WALLET, PUMP_MINT)
    treasury_tx_count = get_recent_tx_count(TREASURY_WALLET, 1000)

    print(f"  Balance: {treasury_balance:,.2f} PUMP")
    print(f"  Recent transactions (last 1000): {treasury_tx_count}")

    # Update addresses file
    print(f"\nUpdating {ADDRESSES_FILE}...")
    with open(ADDRESSES_FILE, 'r') as f:
        data = json.load(f)

    # Update buyback wallet
    data["addresses"][BUYBACK_WALLET]["balance"] = buyback_balance
    data["addresses"][BUYBACK_WALLET]["last_checked"] = datetime.now().isoformat()
    data["addresses"][BUYBACK_WALLET]["recent_tx_count"] = buyback_tx_count

    # Update treasury wallet
    data["addresses"][TREASURY_WALLET]["balance"] = treasury_balance
    data["addresses"][TREASURY_WALLET]["last_checked"] = datetime.now().isoformat()
    data["addresses"][TREASURY_WALLET]["recent_tx_count"] = treasury_tx_count
    data["addresses"][TREASURY_WALLET]["verified"] = treasury_balance > 0  # Verify if has balance

    with open(ADDRESSES_FILE, 'w') as f:
        json.dump(data, f, indent=2)

    print("✓ Address data updated")

    # Summary
    print("\n=== Summary ===")
    print(f"Buyback wallet: {buyback_balance:,.2f} PUMP")
    print(f"Treasury wallet: {treasury_balance:,.2f} PUMP")
    print(f"Total in official wallets: {buyback_balance + treasury_balance:,.2f} PUMP")

    if treasury_balance > 0:
        print(f"\n✓ Treasury wallet verified (has {treasury_balance:,.2f} PUMP)")
    else:
        print("\n⚠ Treasury wallet has 0 balance - may need special query for Squads multisig")


if __name__ == "__main__":
    main()
