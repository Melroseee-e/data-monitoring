#!/usr/bin/env python3
"""
Normalize exchange address labels.

Merges variants like "Binance Deposit", "Binance Hot Wallet (0x14...1c48)"
into a single canonical name "Binance".

Reads:  data/exchange_addresses.json
Writes: data/exchange_addresses_normalized.json
"""

import json
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_FILE = BASE_DIR / "data" / "exchange_addresses.json"
OUTPUT_FILE = BASE_DIR / "data" / "exchange_addresses_normalized.json"

# Keyword → canonical name (order matters: first match wins)
KEYWORD_MAP = [
    ("binance", "Binance"),
    ("okx", "OKX"),
    ("bybit", "Bybit"),
    ("kucoin", "KuCoin"),
    ("gate", "Gate.io"),
    ("kraken", "Kraken"),
    ("coinbase", "Coinbase"),
    ("htx", "HTX"),
    ("mexc", "MEXC"),
    ("mxc", "MEXC"),
    ("bitget", "Bitget"),
    ("bithumb", "Bithumb"),
    ("crypto.com", "Crypto.com"),
    ("bitmart", "BitMart"),
    ("bingx", "BingX"),
    ("korbit", "Korbit"),
    ("coinone", "Coinone"),
    ("upbit", "Upbit"),
    ("lbank", "LBank"),
    ("hitbtc", "HitBTC"),
    ("phemex", "Phemex"),
    ("poloniex", "Poloniex"),
    ("bitvavo", "Bitvavo"),
    ("bitrue", "Bitrue"),
    ("coinex", "CoinEx"),
    ("changenow", "ChangeNOW"),
    ("backpack", "Backpack"),
    ("robinhood", "Robinhood"),
    ("xt.com", "XT.com"),
    ("weex", "WEEX"),
    ("ourbit", "Ourbit"),
    ("cex.io", "CEX.io"),
    ("gopax", "GOPAX"),
    ("kanga", "Kanga"),
    ("indodax", "Indodax"),
    ("wintermute", "Wintermute"),
    ("blockchain.com", "Blockchain.com"),
    ("cobo", "Cobo"),
]


def normalize_exchange_name(label: str) -> str:
    """Map a raw exchange label to its canonical name."""
    label_lower = label.lower()
    for keyword, canonical in KEYWORD_MAP:
        if keyword in label_lower:
            return canonical
    return label  # keep original if no match


def main():
    with open(INPUT_FILE) as f:
        raw = json.load(f)

    # Merge addresses under canonical exchange names
    # Structure: {canonical_name: {chain: [addresses]}}
    normalized: dict[str, dict[str, list[str]]] = {}

    for label, chains in raw.items():
        if label.startswith("_"):
            continue
        canonical = normalize_exchange_name(label)

        if canonical not in normalized:
            normalized[canonical] = {}

        for chain, addresses in chains.items():
            if chain not in normalized[canonical]:
                normalized[canonical][chain] = []
            for addr in addresses:
                if addr not in normalized[canonical][chain]:
                    normalized[canonical][chain].append(addr)

    # Sort by canonical name
    normalized = dict(sorted(normalized.items()))

    # Stats
    original_count = len(raw)
    merged_count = len(normalized)
    total_addresses = sum(
        len(addrs)
        for chains in normalized.values()
        for addrs in chains.values()
    )

    print(f"Normalized: {original_count} labels -> {merged_count} exchanges")
    print(f"Total addresses: {total_addresses}")
    print(f"\nTop exchanges by address count:")
    ranking = sorted(
        normalized.items(),
        key=lambda x: sum(len(a) for a in x[1].values()),
        reverse=True,
    )
    for name, chains in ranking[:15]:
        count = sum(len(a) for a in chains.values())
        chain_list = ", ".join(f"{c}({len(a)})" for c, a in chains.items())
        print(f"  {name}: {count} addresses [{chain_list}]")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(normalized, f, indent=2)
    print(f"\nWritten to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
