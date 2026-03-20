import json
with open("data/latest_data.json") as f:
    data = json.load(f)
if "deployments" in data["tokens"].get("PUMP", {}):
    print("Has deployments")
else:
    print("Keys in PUMP:", list(data["tokens"].get("PUMP", {}).keys()))
