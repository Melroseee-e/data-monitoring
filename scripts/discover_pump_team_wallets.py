#!/usr/bin/env python3
"""
Discover PUMP team wallets by tracking news-reported CEX deposits.

Strategy:
1. Load Bitget and Kraken Solana addresses
2. Query these addresses for large PUMP transfers around reported dates
3. Identify sender addresses (likely team wallets)
4. Verify by checking balances and transaction patterns
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

HELIUS_API_KEY = os.environ.get("HELIUS_API_KEY", "")
if not HELIUS_API_KEY:
    print("ERROR: HELIUS_API_KEY not found")
    exit(1)

HELIUS_RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"

EXCHANGES_FILE = BASE_DIR / "data" / "exchange_addresses.json"  # Use raw file instead
ADDRESSES_FILE = BASE_DIR / "data" / "pump_addresses.json"

# News-reported deposit events
NEWS_EVENTS = [
    {
        "date": "2026-03-05",
        "exchange": "Bitget",
        "amount": 1_757_000_000,  # 1.757B PUMP
        "value_usd": 3_540_000,
        "tolerance_days": 2  # Search ±2 days
    },
    {
        "date": "2026-02-26",
        "exchange": "Kraken",
        "amount": 11_200_000_000,  # 11.2B PUMP
        "value_usd": 21_200_000,
        "tolerance_days": 2
    }
]


def rpc_call(method: str, params: list) -> dict:
    """Make JSON-RPC call to Helius."""
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    resp = requests.post(HELIUS_RPC, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise Exception(f"RPC error: {data['error']}")
    return data.get("result")


def get_exchange_addresses(exchange_name: str) -> list[str]:
    """Get Solana addresses for an exchange from raw exchange_addresses.json."""
    with open(EXCHANGES_FILE, 'r') as f:
        data = json.load(f)

    addresses = []
    for name, chains in data.items():
        if exchange_name.lower() in name.lower() and 'solana' in chains:
            addresses.extend(chains['solana'])

    return addresses


def date_to_timestamp(date_str: str) -> int:
    """Convert YYYY-MM-DD to Unix timestamp."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return int(dt.timestamp())


def get_signatures_in_timerange(address: str, start_ts: int, end_ts: int) -> list[dict]:
    """Get all transaction signatures for an address in a time range."""
    all_sigs = []
    before = None

    while True:
        params = [address, {"limit": 1000}]
        if before:
            params[1]["before"] = before

        sigs = rpc_call("getSignaturesForAddress", params)
        if not sigs:
            break

        for sig in sigs:
            block_time = sig.get("blockTime", 0)
            if block_time < start_ts:
                return all_sigs  # Past our range
            if block_time <= end_ts:
                all_sigs.append(sig)

        before = sigs[-1]["signature"]

        # Safety: stop if we've gone too far back
        if sigs[-1].get("blockTime", 0) < start_ts - 86400 * 30:  # 30 days before
            break

    return all_sigs


def parse_spl_transfer(tx: dict, mint: str) -> list[dict]:
    """Parse SPL token transfers from a transaction."""
    transfers = []

    # Get pre and post token balances
    pre_balances = {
        b["accountIndex"]: b
        for b in tx.get("meta", {}).get("preTokenBalances", [])
        if b.get("mint") == mint
    }
    post_balances = {
        b["accountIndex"]: b
        for b in tx.get("meta", {}).get("postTokenBalances", [])
        if b.get("mint") == mint
    }

    # Find accounts with balance changes
    all_indices = set(pre_balances.keys()) | set(post_balances.keys())
    account_keys = tx["transaction"]["message"]["accountKeys"]

    for idx in all_indices:
        pre = pre_balances.get(idx, {}).get("uiTokenAmount", {}).get("uiAmount", 0)
        post = post_balances.get(idx, {}).get("uiTokenAmount", {}).get("uiAmount", 0)
        change = post - pre

        if abs(change) > 0:
            owner = (pre_balances.get(idx) or post_balances.get(idx)).get("owner")
            transfers.append({
                "owner": owner,
                "change": change,
                "account": account_keys[idx] if idx < len(account_keys) else None
            })

    return transfers


def find_team_wallet_from_deposit(event: dict) -> dict | None:
    """Find team wallet by tracking a specific deposit event."""
    print(f"\n{'='*60}")
    print(f"Tracking {event['exchange']} deposit on {event['date']}")
    print(f"Expected amount: {event['amount']:,.0f} PUMP (${event['value_usd']:,.0f})")

    # Get exchange addresses
    exchange_addrs = get_exchange_addresses(event['exchange'])
    if not exchange_addrs:
        print(f"  ✗ No {event['exchange']} addresses found")
        return None

    print(f"  Found {len(exchange_addrs)} {event['exchange']} addresses")

    # Calculate time range
    center_ts = date_to_timestamp(event['date'])
    start_ts = center_ts - event['tolerance_days'] * 86400
    end_ts = center_ts + event['tolerance_days'] * 86400

    # Search each exchange address
    for ex_addr in exchange_addrs:
        print(f"\n  Checking {ex_addr[:8]}...")

        # Get signatures in time range
        sigs = get_signatures_in_timerange(ex_addr, start_ts, end_ts)
        print(f"    {len(sigs)} transactions in time range")

        if not sigs:
            continue

        # Get transaction details in batches
        for i in range(0, len(sigs), 50):
            batch = sigs[i:i+50]
            sig_list = [s["signature"] for s in batch]

            try:
                txs = rpc_call("getTransactions", [sig_list, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
            except:
                # Fallback to individual calls
                txs = []
                for sig in sig_list:
                    try:
                        tx = rpc_call("getTransaction", [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])
                        txs.append(tx)
                    except:
                        continue

            # Parse each transaction
            for tx in txs:
                if not tx:
                    continue

                transfers = parse_spl_transfer(tx, PUMP_MINT)

                # Look for large incoming transfer matching the amount
                for transfer in transfers:
                    if transfer["owner"] == ex_addr and transfer["change"] > 0:
                        # This is an incoming transfer to the exchange
                        amount = transfer["change"]

                        # Check if amount matches (within 5% tolerance)
                        expected = event["amount"]
                        if abs(amount - expected) / expected < 0.05:
                            # Found it! Now find the sender
                            sender = None
                            for t in transfers:
                                if t["change"] < 0:  # Outgoing = sender
                                    sender = t["owner"]
                                    break

                            if sender:
                                block_time = tx.get("blockTime", 0)
                                date = datetime.fromtimestamp(block_time).strftime("%Y-%m-%d %H:%M:%S")
                                print(f"\n    ✓ FOUND MATCH!")
                                print(f"      Amount: {amount:,.2f} PUMP")
                                print(f"      Date: {date}")
                                print(f"      Sender: {sender}")
                                print(f"      Signature: {tx['transaction']['signatures'][0]}")

                                return {
                                    "wallet": sender,
                                    "amount": amount,
                                    "date": date,
                                    "exchange": event["exchange"],
                                    "exchange_address": ex_addr,
                                    "signature": tx["transaction"]["signatures"][0]
                                }

    print(f"  ✗ No matching deposit found")
    return None


def main():
    print("=== PUMP Team Wallet Discovery ===")
    print("Tracking news-reported CEX deposits to find sender addresses\n")

    discovered_wallets = []

    for event in NEWS_EVENTS:
        result = find_team_wallet_from_deposit(event)
        if result:
            discovered_wallets.append(result)

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY: Discovered {len(discovered_wallets)} team wallet(s)")

    if discovered_wallets:
        # Update addresses file
        with open(ADDRESSES_FILE, 'r') as f:
            addr_data = json.load(f)

        for i, wallet in enumerate(discovered_wallets, 1):
            wallet_addr = wallet["wallet"]

            # Add to addresses
            addr_data["addresses"][wallet_addr] = {
                "label": f"Team Wallet #{i}",
                "type": "team",
                "verified": True,
                "source": f"Tracked from {wallet['exchange']} deposit on {wallet['date']}",
                "notes": f"Deposited {wallet['amount']:,.0f} PUMP to {wallet['exchange']}",
                "balance": None,
                "last_checked": None,
                "discovery_signature": wallet["signature"]
            }

            # Add to team group
            if wallet_addr not in addr_data["address_groups"]["team"]:
                addr_data["address_groups"]["team"].append(wallet_addr)

            # Update news event
            for event in addr_data["news_reported_events"]:
                if event["exchange"] == wallet["exchange"] and event["date"] == wallet["date"][:10]:
                    event["wallet"] = wallet_addr
                    event["verified"] = True

            print(f"\n  #{i}: {wallet_addr}")
            print(f"      {wallet['amount']:,.0f} PUMP → {wallet['exchange']} on {wallet['date']}")

        # Save
        with open(ADDRESSES_FILE, 'w') as f:
            json.dump(addr_data, f, indent=2)

        print(f"\n✓ Updated {ADDRESSES_FILE}")
    else:
        print("\n  No team wallets discovered")


if __name__ == "__main__":
    main()
