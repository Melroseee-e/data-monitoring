#!/usr/bin/env python3
"""
Enrich seller profiles with Arkham entity labels.
Cost: ceil(13647 / 1000) = 14 calls × 250 credits = 3,500 credits total.

Usage:
  python scripts/pump/enrich_sellers_arkham.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parents[2]
SKILLS_DIR = BASE_DIR / ".claude" / "skills" / "onchain-analysis" / "scripts"
sys.path.insert(0, str(SKILLS_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from core.arkham import batch_lookup_addresses, get_token_holders

PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
DATA_DIR = BASE_DIR / "data" / "pump"
PROFILES_FILE = DATA_DIR / "raw" / "pump_seller_profiles.json"
OUTPUT_FILE   = DATA_DIR / "derived" / "pump_sellers_arkham_enriched.json"
HOLDERS_FILE  = DATA_DIR / "derived" / "pump_top_holders_arkham.json"


def main() -> None:
    print(f"[{datetime.now(tz=timezone.utc).strftime('%H:%M:%S')}] Arkham enrichment starting...")

    # --- Step 1: Top holders from Arkham ---
    print("\n=== Step 1: PUMP top holders from Arkham (30 credits) ===")
    holders = get_token_holders("solana", PUMP_MINT)
    print(f"  Got {len(holders)} top holders")
    for h in holders[:10]:
        label = h.get("entity_name") or h.get("label") or "unknown"
        print(f"  {h['address'][:12]}... {h['balance']/1e9:.2f}B ({h['pct_of_cap']*100:.1f}%) — {label}")

    HOLDERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HOLDERS_FILE, "w") as f:
        json.dump({
            "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pump_mint": PUMP_MINT,
            "holders": holders,
        }, f, ensure_ascii=False, indent=2)
    print(f"  Saved → {HOLDERS_FILE}")

    # --- Step 2: Batch label all seller addresses ---
    print("\n=== Step 2: Batch label 13,647 seller addresses ===")
    if not PROFILES_FILE.exists():
        print(f"ERROR: {PROFILES_FILE} not found. Run profile_sellers.py first.")
        sys.exit(1)

    with open(PROFILES_FILE) as f:
        profiles_data = json.load(f)

    sellers = profiles_data.get("sellers", profiles_data)
    if isinstance(sellers, dict) and "sellers" in sellers:
        sellers = sellers["sellers"]

    addresses = list(sellers.keys())
    print(f"  {len(addresses)} addresses to label")
    print(f"  Estimated cost: {(len(addresses) + 999) // 1000} calls × 250 credits = {((len(addresses) + 999) // 1000) * 250} credits")

    arkham_labels = batch_lookup_addresses(addresses, chain="solana")
    labeled_count = sum(1 for v in arkham_labels.values() if v.get("has_entity"))
    print(f"  Labeled {labeled_count}/{len(addresses)} addresses with Arkham entities")

    # --- Step 3: Merge into profiles ---
    print("\n=== Step 3: Merging labels into profiles ===")
    enriched = {}
    entity_type_dist: dict[str, int] = {}

    for addr, profile in sellers.items():
        arkham = arkham_labels.get(addr, {
            "entity_name": None, "entity_type": None,
            "entity_id": None, "entity_website": None,
            "label": None, "has_entity": False,
        })
        enriched[addr] = {**profile, "arkham": arkham}
        if arkham.get("has_entity"):
            et = arkham.get("entity_type") or "unknown"
            entity_type_dist[et] = entity_type_dist.get(et, 0) + 1

    # Summary
    summary = {
        "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_sellers": len(enriched),
        "arkham_labeled": labeled_count,
        "arkham_label_rate": f"{labeled_count/len(enriched)*100:.1f}%",
        "entity_type_distribution": dict(sorted(entity_type_dist.items(), key=lambda x: -x[1])),
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump({"summary": summary, "sellers": enriched}, f, ensure_ascii=False, indent=2)

    print(f"\n=== Summary ===")
    print(f"Total sellers:    {summary['total_sellers']:,}")
    print(f"Arkham labeled:   {labeled_count:,} ({summary['arkham_label_rate']})")
    print(f"Entity types:     {entity_type_dist}")
    print(f"\nOutput → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
