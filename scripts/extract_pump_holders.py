#!/usr/bin/env python3
"""
Extract PUMP Top 500 holders from exchange_addresses.json
The data_collector.py fetches holders but stores them in exchange_addresses.json
We need to extract PUMP-specific data for analysis
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EXCHANGE_FILE = BASE_DIR / "data" / "exchange_addresses.json"
OUTPUT_FILE = BASE_DIR / "data" / "pump_top500_holders.json"

def extract_pump_holders():
    """Extract PUMP holders from exchange_addresses.json"""

    # The exchange_addresses.json is updated by data_collector.py
    # but it doesn't store holder data, only exchange addresses

    # We need to check if BubbleMaps API was called and where the data went
    print("Checking exchange_addresses.json structure...")

    if not EXCHANGE_FILE.exists():
        print(f"Error: {EXCHANGE_FILE} not found")
        return

    with open(EXCHANGE_FILE, 'r') as f:
        data = json.load(f)

    # Check structure
    print(f"Keys in exchange_addresses.json: {list(data.keys())[:10]}")
    print(f"Total entries: {len(data)}")

    # The file structure is: {exchange_name: {chain: [addresses]}}
    # BubbleMaps data might be stored differently

    # Let's check if there's holder data embedded
    for key, value in list(data.items())[:5]:
        print(f"\nSample entry: {key}")
        print(f"  Type: {type(value)}")
        if isinstance(value, dict):
            print(f"  Keys: {list(value.keys())}")

if __name__ == "__main__":
    extract_pump_holders()
