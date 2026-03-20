import json
with open("data/latest_data.json") as f:
    data = json.load(f)
token = data["tokens"].get("BIRB")
if token:
    print("BIRB found in latest_data")
    print("Total Inflow:", token.get("total_inflow"))
    print("Deployments count:", len(token.get("deployments", [])))
    if token.get("deployments"):
        print("Exchange flows in first deployment:", token["deployments"][0].get("exchange_flows"))
else:
    print("BIRB NOT FOUND in latest_data")
