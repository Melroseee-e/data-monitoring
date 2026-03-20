import json

def test():
    with open('data/daily_summary.json') as f:
        daily = json.load(f)
    with open('data/history_summary.json') as f:
        history = json.load(f)
    with open('data/latest_data.json') as f:
        latest = json.load(f)

    token = "AZTEC" # User screenshot shows AZTEC header? No, wait. 
    # Actually the screenshot header says "AZTEC ethereum" but the values are different.
    # Wait! The user provided a screenshot of the table.
    
    # Let's check PUMP.
    token = "PUMP"
    aggregated = {}
    
    for entry in daily:
        t = entry.get("tokens", {}).get(token)
        if t:
            exchanges = t.get("exchanges", {})
            for ex, flows in exchanges.items():
                if ex not in aggregated:
                    aggregated[ex] = {"in": 0, "out": 0, "net": 0}
                aggregated[ex]["in"] += flows.get("inflow", 0)
                aggregated[ex]["out"] += flows.get("outflow", 0)
                aggregated[ex]["net"] += flows.get("net_flow", 0)
                
    print(f"Aggregated exchanges for {token}:")
    for ex, val in aggregated.items():
        print(f"  {ex}: in={val['in']}, out={val['out']}, net={val['net']}")

test()
