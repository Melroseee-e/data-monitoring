#!/usr/bin/env python3
"""
Fetch PUMP Top 500 holders from BubbleMaps and save complete holder data
"""

import json
import time
import hmac
import hashlib
import base64
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "data" / "pump_top500_holders.json"

BUBBLEMAPS_INTERNAL_API = "https://api.bubblemaps.io"
JWT_SECRET = "LTJBO6Dsb5dEJ9pS"

PUMP_CONTRACT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
PUMP_CHAIN = "solana"

def _b64url(data: bytes) -> str:
    """Base64url encode without padding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def make_jwt(path: str) -> str:
    """Create a HS256 JWT for BubbleMaps X-Validation header."""
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = _b64url(json.dumps({
        "data": path,
        "exp": now + 300,
        "iat": now,
    }).encode())
    signing_input = f"{header}.{payload}".encode()
    sig = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url(sig)}"

def fetch_pump_holders():
    """Fetch PUMP top 500 holders from BubbleMaps"""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = f"/addresses/token-top-holders?count=500&date={today}&nocache=false"
    token = make_jwt(path)

    url = f"{BUBBLEMAPS_INTERNAL_API}{path}"
    headers = {
        "X-Validation": token,
        "Content-Type": "application/json",
    }
    body = {"chain": PUMP_CHAIN, "address": PUMP_CONTRACT}

    print(f"Fetching PUMP top 500 holders from BubbleMaps...")
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=30)
        resp.raise_for_status()
        holders = resp.json()
        print(f"✅ Received {len(holders)} holders")
        return holders
    except requests.RequestException as e:
        print(f"❌ Error: {e}")
        return []

def analyze_holders(holders):
    """Analyze holder data and categorize"""
    cex_count = 0
    dex_count = 0
    whale_count = 0
    unknown_count = 0

    for holder in holders:
        details = holder.get("address_details", {})
        is_cex = details.get("is_cex", False)
        is_dex = details.get("is_dex", False)

        if is_cex:
            cex_count += 1
        elif is_dex:
            dex_count += 1
        elif holder.get("balance", 0) > 1_000_000_000:  # > 1B PUMP
            whale_count += 1
        else:
            unknown_count += 1

    return {
        "cex": cex_count,
        "dex": dex_count,
        "whales": whale_count,
        "unknown": unknown_count
    }

def main():
    holders = fetch_pump_holders()
    if not holders:
        print("No data received")
        return

    # Analyze
    stats = analyze_holders(holders)
    print(f"\nHolder breakdown:")
    print(f"  CEX: {stats['cex']}")
    print(f"  DEX: {stats['dex']}")
    print(f"  Whales (>1B): {stats['whales']}")
    print(f"  Unknown: {stats['unknown']}")

    # Save complete data
    output = {
        "metadata": {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "token": "PUMP",
            "contract": PUMP_CONTRACT,
            "chain": PUMP_CHAIN,
            "total_holders": len(holders),
            "stats": stats
        },
        "holders": holders
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✅ Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
