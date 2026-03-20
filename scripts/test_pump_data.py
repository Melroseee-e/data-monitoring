import json

def check_data():
    with open('data/history_summary.json', 'r') as f:
        history = json.load(f)
    
    with open('data/daily_summary.json', 'r') as f:
        daily = json.load(f)
        
    print(f"PUMP in daily_summary.json:")
    pump_daily = [d for d in daily if "PUMP" in d.get("tokens", {})]
    print(f"  Found {len(pump_daily)} entries.")
    if pump_daily:
        print(f"  First entry: {pump_daily[0]['date']}")
    else:
        print("  NONE! PUMP is missing from daily_summary.json!")
        
    print(f"\nPUMP in history_summary.json:")
    pump_history = [d for d in history if "PUMP" in d.get("tokens", {})]
    print(f"  Found {len(pump_history)} entries.")
    if pump_history:
        print(f"  First entry: {pump_history[0]['timestamp']}")
        
check_data()
