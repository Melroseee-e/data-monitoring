import json
with open("data/daily_summary.json") as f:
    daily = json.load(f)
with open("data/history_summary.json") as f:
    history = json.load(f)

daily_records = [d for d in daily if "BIRB" in d.get("tokens", {})]
history_records = [d for d in history if "BIRB" in d.get("tokens", {})]

print(f"BIRB daily records: {len(daily_records)}")
print(f"BIRB history records: {len(history_records)}")

if history_records:
    print("First history sample:", history_records[0]["tokens"]["BIRB"])
