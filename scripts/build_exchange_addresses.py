#!/usr/bin/env python3
"""
Fetch exchange (CEX) addresses from BubbleMaps for all tracked tokens.
Uses BubbleMaps' internal frontend API — no API key required.
Returns top 300 holders with labels (is_cex, is_dex, label, entity_id).

Outputs data/exchange_addresses.json grouped by exchange name and chain.

Usage:
    python scripts/build_exchange_addresses.py
"""

import json
import time
import hmac
import hashlib
import base64
import struct
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
TOKENS_FILE = BASE_DIR / "data" / "tokens.json"
OUTPUT_FILE = BASE_DIR / "data" / "exchange_addresses.json"

BUBBLEMAPS_INTERNAL_API = "https://api.bubblemaps.io"
# JWT signing secret from BubbleMaps frontend JS bundle
JWT_SECRET = "LTJBO6Dsb5dEJ9pS"

CHAIN_MAP = {
    "ethereum": "eth",
    "bsc": "bsc",
    "solana": "solana",
}

TOP_HOLDERS_COUNT = 500  # API hard cap


def _b64url(data: bytes) -> str:
    """Base64url encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_jwt(path: str) -> str:
    """Create a HS256 JWT for BubbleMaps X-Validation header (no external lib needed)."""
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = _b64url(json.dumps({
        "data": path,
        "exp": now + 300,  # 5 min expiry
        "iat": now,
    }).encode())
    signing_input = f"{header}.{payload}".encode()
    sig = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url(sig)}"


def fetch_top_holders(chain: str, contract: str) -> list[dict]:
    """Fetch top holders with labels from BubbleMaps internal API."""
    bm_chain = CHAIN_MAP.get(chain)
    if not bm_chain:
        print(f"  WARNING: unsupported chain '{chain}', skipping")
        return []

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = f"/addresses/token-top-holders?count={TOP_HOLDERS_COUNT}&date={today}&nocache=false"
    token = make_jwt(path)

    url = f"{BUBBLEMAPS_INTERNAL_API}{path}"
    headers = {
        "X-Validation": token,
        "Content-Type": "application/json",
    }
    body = {"chain": bm_chain, "address": contract}

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        print(f"  ERROR fetching {chain}/{contract}: {e}")
        return []


CEX_ENTITY_IDS = {
    'binance', 'gate.io', 'kucoin', 'kraken', 'bitget', 'okx', 'huobi', 'htx',
    'bybit', 'coinbase', 'crypto.com', 'mexc', 'bitmart', 'mxc', 'weex',
    'cobo_com', 'lbank', 'bithumb', 'coinone', 'korbit', 'upbit', 'bitrue',
    'bitvavo', 'hitbtc', 'coinex', 'xt.com', 'ourbit', 'kanga', 'gopax',
    'blockchain.com', 'changenow', 'backpack', 'robinhood', 'wintermute'
}


def extract_cex_addresses(holders: list[dict]) -> list[dict]:
    """Filter holders that are CEX (by is_cex flag OR entity_id), return [{address, label}]."""
    results = []
    for holder in holders:
        details = holder.get("address_details", {})
        entity_id = (details.get("entity_id") or "").lower()
        is_cex = details.get("is_cex", False)

        # Match by is_cex flag OR known entity_id
        if is_cex or entity_id in CEX_ENTITY_IDS:
            label = details.get("label") or entity_id or "Unknown CEX"
            address = holder.get("address", "")
            if address:
                results.append({"address": address, "label": label})
    return results


def main():
    with open(TOKENS_FILE) as f:
        tokens = json.load(f)

    # exchange_name -> chain -> set of addresses
    exchanges = defaultdict(lambda: defaultdict(set))

    for symbol, deployments in tokens.items():
        for dep in deployments:
            chain = dep["chain"]
            contract = dep["contract"]
            print(f"Fetching top {TOP_HOLDERS_COUNT} holders for {symbol} on {chain}...")

            holders = fetch_top_holders(chain, contract)
            cex_list = extract_cex_addresses(holders)

            for entry in cex_list:
                exchanges[entry["label"]][chain].add(entry["address"])

            print(f"  {len(holders)} holders returned, {len(cex_list)} are CEX")
            time.sleep(1.5)  # be polite to the server

    # Convert sets to sorted lists
    output = {}
    for exchange_name in sorted(exchanges):
        output[exchange_name] = {}
        for chain in sorted(exchanges[exchange_name]):
            output[exchange_name][chain] = sorted(exchanges[exchange_name][chain])

    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)

    total = sum(
        len(addrs) for chains in output.values() for addrs in chains.values()
    )
    print(f"\nDone. {len(output)} exchanges, {total} addresses total.")
    print(f"Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
