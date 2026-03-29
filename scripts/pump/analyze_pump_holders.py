#!/usr/bin/env python3
"""
Analyze PUMP Top 500 holders to identify:
1. Non-CEX/DEX whales (potential team/investor wallets)
2. Addresses matching research findings
3. Large holders without labels
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
HOLDERS_FILE = BASE_DIR / "data" / "pump" / "raw" / "pump_top500_holders.json"
ADDRESSES_FILE = BASE_DIR / "data" / "pump" / "core" / "pump_addresses.json"

def load_known_addresses():
    """Load known addresses from pump_addresses.json"""
    with open(ADDRESSES_FILE, 'r') as f:
        data = json.load(f)
    return data.get("addresses", {})

def analyze_top_holders():
    """Analyze top holders and identify whales"""
    with open(HOLDERS_FILE, 'r') as f:
        data = json.load(f)

    holders = data.get("holders", [])
    known_addresses = load_known_addresses()

    print("=" * 80)
    print("PUMP Top 500 Holder Analysis")
    print("=" * 80)

    # Categorize holders
    cex_holders = []
    dex_holders = []
    whale_holders = []
    unknown_holders = []

    for i, holder in enumerate(holders, 1):
        address = holder.get("address", "")
        balance = holder.get("balance", 0)
        details = holder.get("address_details", {})

        is_cex = details.get("is_cex", False)
        is_dex = details.get("is_dex", False)
        label = details.get("label", "")
        entity_id = details.get("entity_id", "")

        holder_info = {
            "rank": i,
            "address": address,
            "balance": balance,
            "label": label,
            "entity_id": entity_id,
            "is_known": address in known_addresses
        }

        if is_cex:
            cex_holders.append(holder_info)
        elif is_dex:
            dex_holders.append(holder_info)
        elif balance > 1_000_000_000:  # > 1B PUMP
            whale_holders.append(holder_info)
        else:
            unknown_holders.append(holder_info)

    # Print whales (>1B PUMP, non-CEX/DEX)
    print(f"\n🐋 WHALES (>1B PUMP, non-CEX/DEX): {len(whale_holders)}")
    print("-" * 80)
    for whale in whale_holders[:20]:  # Top 20 whales
        known_marker = "✅" if whale["is_known"] else "❓"
        print(f"{known_marker} #{whale['rank']:3d} | {whale['address'][:8]}...{whale['address'][-8:]} | "
              f"{whale['balance']:>15,.0f} PUMP | {whale['label'] or 'No label'}")

    # Check for known addresses in Top 500
    print(f"\n✅ KNOWN ADDRESSES IN TOP 500:")
    print("-" * 80)
    found_known = False
    for holder in holders:
        address = holder.get("address", "")
        if address in known_addresses:
            found_known = True
            balance = holder.get("balance", 0)
            rank = holders.index(holder) + 1
            known_info = known_addresses[address]
            print(f"#{rank:3d} | {address[:8]}...{address[-8:]} | {balance:>15,.0f} PUMP")
            print(f"      Label: {known_info.get('label', 'N/A')}")
            print(f"      Type: {known_info.get('type', 'N/A')}")
            print()

    if not found_known:
        print("None of the known addresses are in Top 500")

    # Top 10 non-CEX/DEX holders
    print(f"\n📊 TOP 10 NON-CEX/DEX HOLDERS:")
    print("-" * 80)
    non_cex_dex = [h for h in holders if not h.get("address_details", {}).get("is_cex")
                   and not h.get("address_details", {}).get("is_dex")]

    for i, holder in enumerate(non_cex_dex[:10], 1):
        address = holder.get("address", "")
        balance = holder.get("balance", 0)
        details = holder.get("address_details", {})
        label = details.get("label", "No label")
        rank = holders.index(holder) + 1

        known_marker = "✅" if address in known_addresses else "❓"
        print(f"{known_marker} #{rank:3d} | {address[:8]}...{address[-8:]} | "
              f"{balance:>15,.0f} PUMP | {label}")

    # Summary
    print(f"\n📈 SUMMARY:")
    print("-" * 80)
    print(f"Total holders: {len(holders)}")
    print(f"CEX: {len(cex_holders)}")
    print(f"DEX: {len(dex_holders)}")
    print(f"Whales (>1B): {len(whale_holders)}")
    print(f"Others: {len(unknown_holders)}")
    print(f"Known addresses found: {sum(1 for h in holders if h.get('address') in known_addresses)}")

    # Save whale list
    whale_output = {
        "generated_at": data["metadata"]["fetched_at"],
        "criteria": ">1B PUMP, non-CEX/DEX",
        "total_whales": len(whale_holders),
        "whales": whale_holders
    }

    whale_file = BASE_DIR / "data" / "pump" / "raw" / "pump_whale_addresses.json"
    with open(whale_file, 'w') as f:
        json.dump(whale_output, f, indent=2)

    print(f"\n✅ Whale list saved to {whale_file}")

if __name__ == "__main__":
    analyze_top_holders()
