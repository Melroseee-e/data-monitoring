#!/usr/bin/env python3
"""
Finalize pump_sell_events.json from cache file, skipping ATA resolution.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "pump"
CEX_CACHE_FILE = DATA_DIR / "raw" / ".pump_cex_inflows_cache.json"
OUTPUT_FILE = DATA_DIR / "raw" / "pump_sell_events.json"

PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
TGE_DATE = "2025-07-12"
TGE_TIMESTAMP = 1752336000

def main():
    print("Loading cached CEX inflows...")
    if not CEX_CACHE_FILE.exists():
        print(f"ERROR: Cache file not found: {CEX_CACHE_FILE}")
        return

    with open(CEX_CACHE_FILE) as f:
        cex_inflows = json.load(f)

    print(f"Loaded {len(cex_inflows)} CEX inflow records from cache")

    # Compute summary
    all_sellers = {r["seller"] for r in cex_inflows if r.get("seller")}
    cex_volume = sum(r.get("amount_B", 0) for r in cex_inflows)

    exchange_volumes = {}
    for r in cex_inflows:
        ex = r.get("exchange", "Unknown")
        exchange_volumes[ex] = exchange_volumes.get(ex, 0) + r.get("amount_B", 0)

    top_exchanges = dict(sorted(exchange_volumes.items(), key=lambda x: -x[1])[:10])

    summary = {
        "total_cex_events": len(cex_inflows),
        "total_dex_events": 0,
        "total_unique_sellers": len(all_sellers),
        "total_cex_volume_B": round(cex_volume, 4),
        "total_dex_volume_B": 0.0,
        "total_sell_volume_B": round(cex_volume, 4),
        "top_exchanges": top_exchanges,
        "top_dexes": {},
    }

    output = {
        "metadata": {
            "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "pump_mint": PUMP_MINT,
            "tge_date": TGE_DATE,
            "tge_timestamp": TGE_TIMESTAMP,
            "sources": ["helius_enhanced"],
            "note": "CEX-only data from cache, DEX skipped due to API limitations",
            **summary,
        },
        "cex_inflows": sorted(cex_inflows, key=lambda x: x.get("timestamp", 0)),
        "dex_sells": [],
    }

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("\n=== Summary ===")
    print(f"CEX inflows:    {summary['total_cex_events']:,} events, {summary['total_cex_volume_B']:.2f}B PUMP")
    print(f"DEX sells:      0 events (skipped)")
    print(f"Total volume:   {summary['total_sell_volume_B']:.2f}B PUMP")
    print(f"Unique sellers: {summary['total_unique_sellers']:,}")
    print(f"\nTop 5 exchanges:")
    for ex, vol in list(top_exchanges.items())[:5]:
        print(f"  {ex}: {vol:.2f}B")
    print(f"\nOutput: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
