import json
with open("data/daily_summary.json") as f:
    data = json.load(f)
for i, d in enumerate(data):
    if "PUMP" in d.get("tokens", {}):
        t = d["tokens"]["PUMP"]
        if t.get("total_inflow", 0) > 0 or t.get("total_outflow", 0) > 0:
            print(f"First non-zero index: {i}, date: {d['date']}, data: {t}")
            break
