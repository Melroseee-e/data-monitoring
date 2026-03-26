#!/usr/bin/env python3
"""
Enrich top sellers and buyers from Dune ledger with Arkham entity tags.
Designed to be very efficient with API credits (1000 addresses = 250 credits).

Usage:
  python scripts/pump/enrich_top_traders_arkham.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SKILLS_DIR = BASE_DIR / ".claude" / "skills" / "onchain-analysis" / "scripts"
sys.path.insert(0, str(SKILLS_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from core.arkham import batch_lookup_addresses

DATA_DIR = BASE_DIR / "data" / "pump" / "derived"
LEDGER_FILE = DATA_DIR / "pump_dune_tiered_ledger.json"
ENRICHED_SELLERS = DATA_DIR / "pump_top_sellers_enriched.json"
ENRICHED_BUYERS = DATA_DIR / "pump_top_buyers_enriched.json"


def main() -> None:
    if not LEDGER_FILE.exists():
        print(f"ERROR: {LEDGER_FILE} not found. Run build_ledger_tiered_dune.py first.")
        sys.exit(1)

    print("Loading Dune tiered ledger...")
    with open(LEDGER_FILE) as f:
        ledger = json.load(f)

    top_sellers = ledger.get("top_sellers", [])
    top_buyers = ledger.get("top_buyers", [])

    if not top_sellers and not top_buyers:
        print("No top sellers or buyers found in ledger.")
        sys.exit(1)

    # Collect unique addresses
    addresses_to_lookup = set()
    for s in top_sellers:
        if "address" in s: addresses_to_lookup.add(s["address"])
    for b in top_buyers:
        if "address" in b: addresses_to_lookup.add(b["address"])

    addresses = list(addresses_to_lookup)
    print(f"Found {len(addresses)} unique addresses to lookup on Arkham.")

    # Only look up first 1000 (Arkham batch limit)
    # They are already top N, so taking first 1000 is perfectly fine.
    lookup_batch = addresses[:1000]

    print(f"Calling Arkham API for {len(lookup_batch)} addresses (cost: 250 credits max)...")
    arkham_results = batch_lookup_addresses(lookup_batch)

    labeled_count = sum(1 for v in arkham_results.values() if v.get("has_entity", False))
    print(f"Arkham returned entity tags for {labeled_count} addresses.")

    # Enrich sellers
    enriched_sellers = []
    for s in top_sellers:
        addr = s.get("address")
        if addr in arkham_results:
            s["arkham_entity"] = arkham_results[addr]
        else:
            s["arkham_entity"] = {"has_entity": False}
        enriched_sellers.append(s)

    # Enrich buyers
    enriched_buyers = []
    for b in top_buyers:
        addr = b.get("address")
        if addr in arkham_results:
            b["arkham_entity"] = arkham_results[addr]
        else:
            b["arkham_entity"] = {"has_entity": False}
        enriched_buyers.append(b)

    # Save
    ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with open(ENRICHED_SELLERS, "w") as f:
        json.dump({"generated_at": ts, "sellers": enriched_sellers}, f, indent=2)

    with open(ENRICHED_BUYERS, "w") as f:
        json.dump({"generated_at": ts, "buyers": enriched_buyers}, f, indent=2)

    print(f"\nSaved enriched sellers -> {ENRICHED_SELLERS}")
    print(f"Saved enriched buyers  -> {ENRICHED_BUYERS}")


if __name__ == "__main__":
    main()
