import json

with open('data/daily_summary.json') as f:
    daily = json.load(f)
with open('data/history_summary.json') as f:
    history = json.load(f)

pump_in_daily = any("PUMP" in d.get("tokens", {}) for d in daily)
pump_in_history = any("PUMP" in d.get("tokens", {}) for d in history)

print(f"PUMP in daily: {pump_in_daily}")
print(f"PUMP in history: {pump_in_history}")
