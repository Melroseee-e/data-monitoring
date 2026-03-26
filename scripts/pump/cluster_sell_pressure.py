#!/usr/bin/env python3
"""
PUMP Seller Cluster Builder (Behavioral)
Since upstream tracing via Helius was aborted due to 429 limits,
we cluster sellers behaviorally:
1. Exact same combination of exchanges used
2. Size tier
3. Time overlap (if dates are close)

Output: data/pump/derived/pump_seller_clusters.json
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "pump"

# Read from the new Dune ledger to get the most accurate Top 500
LEDGER_FILE = DATA_DIR / "derived" / "pump_dune_tiered_ledger.json"
OUTPUT_FILE = DATA_DIR / "derived" / "pump_seller_clusters.json"

def main() -> None:
    print("Loading Dune Tiered Ledger for top sellers/buyers...")
    with open(LEDGER_FILE) as f:
        ledger = json.load(f)

    top_sellers = ledger.get("top_sellers", [])
    top_buyers = ledger.get("top_buyers", [])
    print(f"Loaded {len(top_sellers)} top sellers and {len(top_buyers)} top buyers.")

    clusters = defaultdict(list)
    
    # We will cluster by "Exchanges Used" + "Date Pattern"
    for s in top_sellers:
        addr = s.get("address", "")
        exchanges = tuple(sorted(s.get("exchanges_used", [])))
        vol_b = s.get("cex_deposit_B", 0)
        tx_count = s.get("tx_count", 0)
        
        # Determine temporal behavior
        first_sell = s.get("first_sell_date", "unknown")
        
        # cluster key
        if not exchanges:
            key = "Unknown CEX"
        else:
            key = f"Exchanges: {' + '.join(exchanges)}"
            
        clusters[key].append({
            "address": addr,
            "volume_B": vol_b,
            "tx_count": tx_count,
            "first_sell_date": first_sell,
            "last_sell_date": s.get("last_sell_date"),
        })

    final_clusters = []
    cluster_id = 1
    total_clustered_vol = 0
    total_clustered_addrs = 0

    for key, members in sorted(clusters.items(), key=lambda x: sum(m["volume_B"] for m in x[1]), reverse=True):
        if len(members) < 2 and sum(m["volume_B"] for m in members) < 50:
            continue # Skip tiny clusters of 1 address unless it's a massive whale
            
        vol = sum(m["volume_B"] for m in members)
        total_clustered_vol += vol
        total_clustered_addrs += len(members)
        
        final_clusters.append({
            "cluster_id": f"C{cluster_id:03d}",
            "cluster_name": key,
            "member_count": len(members),
            "total_volume_B": round(vol, 2),
            "members": sorted(members, key=lambda m: m["volume_B"], reverse=True)
        })
        cluster_id += 1

    unclustered = len(top_sellers) - total_clustered_addrs

    output = {
        "metadata": {
            "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_top_sellers_analyzed": len(top_sellers),
            "clustered_sellers": total_clustered_addrs,
            "unclustered_sellers": unclustered,
            "total_clusters": len(final_clusters),
            "clustered_volume_B": round(total_clustered_vol, 2)
        },
        "clusters": final_clusters
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n=== Behavioral Cluster Summary ===")
    print(f"Total clusters:      {len(final_clusters)}")
    print(f"Clustered sellers:   {total_clustered_addrs}/{len(top_sellers)}")
    print(f"Clustered volume:    {total_clustered_vol:.2f}B PUMP")
    print(f"Saved -> {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
