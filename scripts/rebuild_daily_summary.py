import os
import json
from collections import defaultdict
from datetime import datetime

def rebuild():
    history_dir = "data/history"
    daily_data = defaultdict(lambda: defaultdict(lambda: {
        "total_inflow": 0.0,
        "total_outflow": 0.0,
        "net_flow": 0.0,
        "exchanges": defaultdict(lambda: {"inflow": 0.0, "outflow": 0.0, "net_flow": 0.0})
    }))

    files = sorted([f for f in os.listdir(history_dir) if f.endswith(".jsonl")])
    print(f"Processing {len(files)} files...")

    for filename in files:
        path = os.path.join(history_dir, filename)
        date_str = filename.split(".")[0] # YYYY-MM-DD
        
        with open(path, "r") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    tokens = entry.get("tokens", {})
                    for symbol, data in tokens.items():
                        daily_entry = daily_data[date_str][symbol]
                        daily_entry["total_inflow"] += data.get("total_inflow", 0.0)
                        daily_entry["total_outflow"] += data.get("total_outflow", 0.0)
                        daily_entry["net_flow"] += data.get("net_flow", 0.0)
                        
                        deployments = data.get("deployments", [])
                        for dep in deployments:
                            ex_flows = dep.get("exchange_flows", {})
                            for ex, flows in ex_flows.items():
                                ex_entry = daily_entry["exchanges"][ex]
                                ex_entry["inflow"] += flows.get("inflow", 0.0)
                                ex_entry["outflow"] += flows.get("outflow", 0.0)
                                ex_entry["net_flow"] += flows.get("net_flow", 0.0)
                except Exception as e:
                    print(f"Error parsing line in {filename}: {e}")

    # Convert to list format
    result = []
    sorted_dates = sorted(daily_data.keys())
    for date in sorted_dates:
        tokens_out = {}
        for symbol, data in daily_data[date].items():
            # Convert exchange defaultdict to regular dict
            exchanges_out = {}
            for ex, ex_data in data["exchanges"].items():
                exchanges_out[ex] = dict(ex_data)
            
            token_data = dict(data)
            token_data["exchanges"] = exchanges_out
            tokens_out[symbol] = token_data
            
        result.append({
            "date": date,
            "tokens": tokens_out
        })

    with open("data/daily_summary.json", "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"Successfully rebuilt daily_summary.json with {len(result)} days.")

if __name__ == "__main__":
    rebuild()
