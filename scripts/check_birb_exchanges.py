import json
with open("data/daily_summary.json") as f:
    daily = json.load(f)

for day in daily:
    t = day.get("tokens", {}).get("BIRB")
    if t and t.get("exchanges"):
        print(f"Date: {day['date']}, Exchanges: {t['exchanges']}")
        break
