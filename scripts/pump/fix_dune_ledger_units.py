#!/usr/bin/env python3
"""
Fix the units in the pump_dune_tiered_ledger.json without re-running Dune queries.
Original Dune query used `amount_display / 1e3`.
PUMP has 6 decimals, so `amount_display` = PUMP tokens.
`amount_display / 1e3` = PUMP tokens / 1000 = "thousands of PUMP".
To get "billions of PUMP" (which the _B suffixes imply), we need to divide the current values by 1e6.
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "pump" / "derived"
LEDGER_FILE = DATA_DIR / "pump_dune_tiered_ledger.json"
NETFLOW_FILE = DATA_DIR / "pump_daily_netflow.json"

def fix_units(val):
    if val is None:
        return None
    # val is currently PUMP / 1000. Divide by 1,000,000 to get Billions of PUMP.
    return float(val) / 1e6

def main():
    print(f"Loading {LEDGER_FILE}...")
    with open(LEDGER_FILE) as f:
        data = json.load(f)

    # 1. overall_stats
    if data.get("overall_stats"):
        for row in data["overall_stats"]:
            if "total_volume_B" in row: row["total_volume_B"] = fix_units(row["total_volume_B"])
            if "total_volume_b" in row: row["total_volume_b"] = fix_units(row["total_volume_b"])

    # 2. exchange_flow
    if data.get("exchange_flow"):
        for row in data["exchange_flow"]:
            if "inflow_B" in row: row["inflow_B"] = fix_units(row["inflow_B"])
            if "outflow_B" in row: row["outflow_B"] = fix_units(row["outflow_B"])
            if "inflow_b" in row: row["inflow_b"] = fix_units(row["inflow_b"])
            if "outflow_b" in row: row["outflow_b"] = fix_units(row["outflow_b"])

    # 3. top_sellers
    if data.get("top_sellers"):
        for row in data["top_sellers"]:
            if "cex_deposit_B" in row: row["cex_deposit_B"] = fix_units(row["cex_deposit_B"])
            if "cex_deposit_b" in row: row["cex_deposit_b"] = fix_units(row["cex_deposit_b"])

    # 4. top_buyers
    if data.get("top_buyers"):
        for row in data["top_buyers"]:
            if "cex_withdraw_B" in row: row["cex_withdraw_B"] = fix_units(row["cex_withdraw_B"])
            if "cex_withdraw_b" in row: row["cex_withdraw_b"] = fix_units(row["cex_withdraw_b"])

    # 5. size_tiers
    if data.get("size_tiers"):
        for row in data["size_tiers"]:
            if "total_sent_B" in row: row["total_sent_B"] = fix_units(row["total_sent_B"])
            if "avg_sent_B" in row: row["avg_sent_B"] = fix_units(row["avg_sent_B"])
            if "total_sent_b" in row: row["total_sent_b"] = fix_units(row["total_sent_b"])
            if "avg_sent_b" in row: row["avg_sent_b"] = fix_units(row["avg_sent_b"])

    # 6. daily_netflow
    if data.get("daily_netflow"):
        for row in data["daily_netflow"]:
            if "cex_inflow_B" in row: row["cex_inflow_B"] = fix_units(row["cex_inflow_B"])
            if "cex_outflow_B" in row: row["cex_outflow_B"] = fix_units(row["cex_outflow_B"])
            if "cex_inflow_b" in row: row["cex_inflow_b"] = fix_units(row["cex_inflow_b"])
            if "cex_outflow_b" in row: row["cex_outflow_b"] = fix_units(row["cex_outflow_b"])

    print("Writing fixed data...")
    with open(LEDGER_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Also update the daily netflow separate file
    if NETFLOW_FILE.exists():
        with open(NETFLOW_FILE) as f:
            netflow_data = json.load(f)

        if netflow_data.get("daily"):
            for row in netflow_data["daily"]:
                if "cex_inflow_B" in row: row["cex_inflow_B"] = fix_units(row["cex_inflow_B"])
                if "cex_outflow_B" in row: row["cex_outflow_B"] = fix_units(row["cex_outflow_B"])
                if "cex_inflow_b" in row: row["cex_inflow_b"] = fix_units(row["cex_inflow_b"])
                if "cex_outflow_b" in row: row["cex_outflow_b"] = fix_units(row["cex_outflow_b"])

            with open(NETFLOW_FILE, "w") as f:
                json.dump(netflow_data, f, ensure_ascii=False, indent=2)

    print("Done. Units are now correct (Billions of PUMP).")

if __name__ == "__main__":
    main()
