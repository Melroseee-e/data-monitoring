import json
with open("data/daily_summary.json") as f:
    daily = json.load(f)
with open("data/history_summary.json") as f:
    history = json.load(f)

for day in daily:
    t = day.get("tokens", {}).get("BIRB")
    if t:
        print(f"Daily BIRB on {day['date']}: {t.get('total_inflow')}, {t.get('total_outflow')}")

for hour in history:
    t = hour.get("tokens", {}).get("BIRB")
    if t:
        print(f"History BIRB on {hour['timestamp']}: {t.get('total_inflow')}, {t.get('total_outflow')}")
