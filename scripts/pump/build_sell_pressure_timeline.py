#!/usr/bin/env python3
"""
Build Sell Pressure Timeline

Creates daily phase aggregation using:
1. Daily netflow data
2. PUMP price action history
3. CEX Inflow / Outflow amounts
"""

import json
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "pump" / "derived"
NETFLOW_FILE = DATA_DIR / "pump_daily_netflow.json"
TIMELINE_FILE = DATA_DIR / "pump_sell_pressure_by_phase.json"

def main():
    if not NETFLOW_FILE.exists():
        print("Missing netflow file.")
        return

    with open(NETFLOW_FILE) as f:
        data = json.load(f)

    daily = data.get("daily", [])
    
    # We define phases manually based on PUMP history
    # Phase 1: Pre-Listing / Initial Distribution (Jul 12 - Aug 31)
    # Phase 2: Stagnation / Accumulation (Sep 01 - Nov 30)
    # Phase 3: Major Rally (Dec 01 - Mar 15)
    # Phase 4: Recent Action (Mar 16 - Present)
    
    phases = [
        {"name": "Pre-Listing & Initial", "start": "2025-07-12", "end": "2025-08-31", "type": "accumulation", "stats": {"inflow_B": 0, "outflow_B": 0, "net_B": 0}},
        {"name": "Stagnation", "start": "2025-09-01", "end": "2025-11-30", "type": "consolidation", "stats": {"inflow_B": 0, "outflow_B": 0, "net_B": 0}},
        {"name": "Major Rally", "start": "2025-12-01", "end": "2026-03-15", "type": "rally", "stats": {"inflow_B": 0, "outflow_B": 0, "net_B": 0}},
        {"name": "Recent Action", "start": "2026-03-16", "end": "2026-12-31", "type": "decline", "stats": {"inflow_B": 0, "outflow_B": 0, "net_B": 0}},
    ]

    for row in daily:
        date = row.get("date", "")
        inflow = row.get("cex_inflow_B", 0)
        outflow = row.get("cex_outflow_B", 0)
        net = outflow - inflow
        
        for p in phases:
            if p["start"] <= date <= p["end"]:
                p["stats"]["inflow_B"] += inflow
                p["stats"]["outflow_B"] += outflow
                p["stats"]["net_B"] += net
                break

    output = {
        "metadata": {
            "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "phases": phases,
        "daily_series": daily
    }

    with open(TIMELINE_FILE, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Saved timeline -> {TIMELINE_FILE}")

if __name__ == "__main__":
    main()
