#!/usr/bin/env python3
"""
Generate TGE cumulative net flow chart data.
Reads all history JSONL files and computes per-token daily cumulative net flow from TGE.
Output: data/tge_chart_data.json
"""

import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

BASE_DIR = Path(__file__).parent.parent
HISTORY_DIR = BASE_DIR / "data" / "history"
TGE_CONFIG_FILE = BASE_DIR / "data" / "tge_final_config.json"
OUTPUT_FILE = BASE_DIR / "data" / "tge_chart_data.json"
TGE_NETFLOWS_FILE = BASE_DIR / "data" / "tge_netflows.json"

# TGE dates per token (from tge_final_config.json)
TGE_DATES = {
    "UAI": "2025-11-06",
    "BIRB": "2026-01-28",
    "AZTEC": "2025-07-01",
    "TRIA": "2026-01-16",
    "SKR": "2026-01-21",
    "GWEI": "2026-02-05",
    "SPACE": "2026-01-29",
    "PUMP": "2026-01-21",
}

def main():
    print("[generate_tge_chart_data] Starting...", flush=True)

    # Load TGE config for dates
    if TGE_CONFIG_FILE.exists():
        with open(TGE_CONFIG_FILE) as f:
            tge_config = json.load(f)
        for token, info in tge_config.get("tokens", {}).items():
            date = info.get("final_tge", {}).get("date")
            if date:
                TGE_DATES[token] = date
        print(f"[generate_tge_chart_data] Loaded TGE dates: {TGE_DATES}", flush=True)

    # Per-token, per-date net flow accumulation
    # Structure: {token: {date: net_flow}}
    token_daily_net = defaultdict(lambda: defaultdict(float))

    files = sorted(HISTORY_DIR.glob("*.jsonl"))
    print(f"[generate_tge_chart_data] Processing {len(files)} history files...", flush=True)

    for f in files:
        date_str = f.stem  # e.g. "2026-03-11"
        with open(f) as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except Exception as e:
                    print(f"  [WARN] Parse error in {f.name}: {e}", flush=True)
                    continue

                ts = data.get("timestamp", "")
                entry_date = ts[:10] if ts else date_str

                for token, info in data.get("tokens", {}).items():
                    tge_date = TGE_DATES.get(token)
                    if not tge_date:
                        continue
                    if entry_date < tge_date:
                        continue  # Before TGE, skip

                    for dep in info.get("deployments", []):
                        ef = dep.get("exchange_flows", {})
                        if not isinstance(ef, dict):
                            continue
                        for exch, flows in ef.items():
                            if not isinstance(flows, dict):
                                continue
                            net = flows.get("net_flow", 0) or 0
                            token_daily_net[token][entry_date] += net

    print(f"[generate_tge_chart_data] Tokens with data: {list(token_daily_net.keys())}", flush=True)

    # Build cumulative series per token
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tokens": {}
    }

    cumulative_totals = {}

    for token, daily_net in sorted(token_daily_net.items()):
        tge_date = TGE_DATES.get(token, "")
        dates = sorted(daily_net.keys())

        # Build cumulative series
        cumulative = 0.0
        series = []
        for date in dates:
            cumulative += daily_net[date]
            series.append({"date": date, "cumulative_net": round(cumulative, 4)})

        result["tokens"][token] = {
            "tge_date": tge_date,
            "series": series,
            "final_cumulative": round(cumulative, 4),
            "days_tracked": len(dates)
        }
        cumulative_totals[token] = round(cumulative, 4)
        print(f"  {token}: {len(dates)} days, final cumulative: {cumulative:+,.2f}", flush=True)

    # Write output
    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)
    print(f"[generate_tge_chart_data] Written to {OUTPUT_FILE}", flush=True)

    # Also update tge_netflows.json with latest data
    tge_netflows = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tokens": {}
    }
    for token, data in result["tokens"].items():
        tge_netflows["tokens"][token] = {
            "cumulative_netflow": data["final_cumulative"],
            "tge_date": data["tge_date"],
            "days_tracked": data["days_tracked"]
        }
    with open(TGE_NETFLOWS_FILE, "w") as f:
        json.dump(tge_netflows, f, indent=2)
    print(f"[generate_tge_chart_data] Updated {TGE_NETFLOWS_FILE}", flush=True)
    print("[generate_tge_chart_data] Done!", flush=True)

if __name__ == "__main__":
    main()
