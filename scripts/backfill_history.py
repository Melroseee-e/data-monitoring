#!/usr/bin/env python3
"""
Historical data backfill script - fetches token transfers from TGE to present.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

import requests
from dotenv import load_dotenv

# Force unbuffered output for GitHub Actions
sys.stdout.reconfigure(line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TOKENS_FILE = BASE_DIR / "data" / "tokens.json"
EXCHANGES_FILE = BASE_DIR / "data" / "exchange_addresses_normalized.json"
HISTORY_DIR = BASE_DIR / "data" / "history"

ETHERSCAN_API = "https://api.etherscan.io/v2/api"
BSCTRACE_RPC = "https://bsc-mainnet.nodereal.io/v1/{api_key}"
HELIUS_RPC = "https://mainnet.helius-rpc.com/?api-key={api_key}"

TRANSFER_EVENT_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# TGE block numbers (using hybrid strategy: exchange first transfer > contract deployment > news TGE)
TGE_BLOCKS = {
    # AZTEC: News TGE (2026-02-12) - contract deployment was test/early deploy
    "AZTEC": {"ethereum": 24416000, "date": "2026-02-12"},

    # UAI: News TGE (2025-11-06) - no on-chain data available
    "UAI": {"bsc": 43500000, "date": "2025-11-06"},

    # SPACE: Exchange first transfer (2026-01-29) - most accurate
    "SPACE": {"ethereum": 24340673, "bsc": 44800000, "date": "2026-01-29"},

    # GWEI: Exchange first transfer (2026-02-05) - most accurate
    "GWEI": {"ethereum": 24389809, "date": "2026-02-05"},

    # TRIA: Contract deployment (2026-01-16) - no exchange first transfer found
    "TRIA": {"ethereum": 24249417, "bsc": 45200000, "date": "2026-01-16"},

    # SKR: News TGE (2026-01-21) - Solana
    "SKR": {"solana": "2026-01-21T00:00:00Z", "date": "2026-01-21"},

    # BIRB: News TGE (2026-01-28) - Solana
    "BIRB": {"solana": "2026-01-28T00:00:00Z", "date": "2026-01-28"}
}

def load_exchange_lookup(exchanges_data):
    lookup = defaultdict(dict)
    for exchange_name, chains in exchanges_data.items():
        for chain, addresses in chains.items():
            for addr in addresses:
                lookup[chain][addr.lower()] = exchange_name
    return dict(lookup)

def get_current_block_eth(api_key):
    try:
        params = {"chainid": "1", "module": "proxy", "action": "eth_blockNumber", "apikey": api_key}
        resp = requests.get(ETHERSCAN_API, params=params, timeout=15)
        resp.raise_for_status()
        return int(resp.json()["result"], 16)
    except Exception as e:
        print(f"ERROR getting ETH block: {e}", flush=True)
        raise

def get_current_block_bsc(api_key):
    try:
        rpc = BSCTRACE_RPC.format(api_key=api_key)
        payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
        resp = requests.post(rpc, json=payload, timeout=15)
        resp.raise_for_status()
        block_num = int(resp.json()["result"], 16)

        # Sanity check: BSC genesis was 2020-09-01, block time ~3s
        # As of 2026-03, max reasonable block should be ~60M
        MAX_REASONABLE_BLOCK = 65000000
        if block_num > MAX_REASONABLE_BLOCK:
            print(f"WARNING: BSC block {block_num:,} seems too high (max expected ~{MAX_REASONABLE_BLOCK:,})", flush=True)
            print(f"         Using estimated block based on time instead", flush=True)
            # Estimate based on time: BSC genesis + (current_time - genesis_time) / 3
            genesis_ts = 1598918400  # 2020-09-01 00:00:00 UTC
            current_ts = int(time.time())
            estimated_block = (current_ts - genesis_ts) // 3
            print(f"         Estimated current block: {estimated_block:,}", flush=True)
            return estimated_block

        return block_num
    except Exception as e:
        print(f"ERROR getting BSC block: {e}", flush=True)
        raise

def fetch_eth_transfers_range(api_key, contract, start_block, end_block):
    params = {
        "chainid": "1", "module": "account", "action": "tokentx",
        "contractaddress": contract, "startblock": start_block,
        "endblock": end_block, "sort": "asc", "apikey": api_key
    }
    resp = requests.get(ETHERSCAN_API, params=params, timeout=30)
    data = resp.json()
    return data.get("result", []) if data.get("status") == "1" else []

def fetch_bsc_transfers_range(api_key, contract, start_block, end_block):
    rpc = BSCTRACE_RPC.format(api_key=api_key)
    payload = {
        "jsonrpc": "2.0", "method": "eth_getLogs", "id": 1,
        "params": [{
            "fromBlock": hex(start_block), "toBlock": hex(end_block),
            "address": contract, "topics": [TRANSFER_EVENT_TOPIC]
        }]
    }
    resp = requests.post(rpc, json=payload, timeout=30)
    return resp.json().get("result", [])

def process_eth_transfers(transfers, exchange_lookup, decimals=18):
    flows = defaultdict(lambda: {"inflow": 0, "outflow": 0, "inflow_tx_count": 0, "outflow_tx_count": 0})
    for tx in transfers:
        from_addr = tx.get("from", "").lower()
        to_addr = tx.get("to", "").lower()
        value = float(tx.get("value", 0)) / (10 ** decimals)

        if from_addr in exchange_lookup:
            flows[exchange_lookup[from_addr]]["outflow"] += value
            flows[exchange_lookup[from_addr]]["outflow_tx_count"] += 1
        if to_addr in exchange_lookup:
            flows[exchange_lookup[to_addr]]["inflow"] += value
            flows[exchange_lookup[to_addr]]["inflow_tx_count"] += 1

    for ex in flows:
        flows[ex]["net_flow"] = flows[ex]["inflow"] - flows[ex]["outflow"]
    return dict(flows)

def rpc_call(url, method, params):
    """Generic JSON-RPC call."""
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        return result.get("result")
    except Exception as e:
        print(f"RPC call failed: {method} - {e}", flush=True)
        return None

def fetch_solana_signatures_since(api_key, token_mint, exchange_addresses, start_time_iso):
    """Fetch all Solana signatures for a token since start_time."""
    rpc_url = HELIUS_RPC.format(api_key=api_key)
    start_timestamp = int(datetime.fromisoformat(start_time_iso.replace('Z', '+00:00')).timestamp())

    # Step 1: Find all ATAs for exchange addresses
    ata_to_exchange = {}
    print(f"  Finding ATAs for {len(exchange_addresses)} exchanges...", flush=True)
    for addr in exchange_addresses:
        result = rpc_call(rpc_url, "getTokenAccountsByOwner", [
            addr,
            {"mint": token_mint},
            {"encoding": "jsonParsed"},
        ])
        if result and result.get("value"):
            for acct in result["value"]:
                ata_to_exchange[acct["pubkey"]] = addr
        time.sleep(0.1)

    if not ata_to_exchange:
        print(f"  No ATAs found for token {token_mint[:8]}...", flush=True)
        return []

    print(f"  Found {len(ata_to_exchange)} ATAs", flush=True)

    # Step 2: Fetch all signatures for each ATA (paginated)
    all_signatures = []
    for ata_pubkey, ex_addr in ata_to_exchange.items():
        print(f"  Fetching signatures for ATA {ata_pubkey[:8]}...", flush=True)
        before = None
        page_count = 0

        while True:
            params = [ata_pubkey, {"limit": 1000}]
            if before:
                params[1]["before"] = before

            sigs = rpc_call(rpc_url, "getSignaturesForAddress", params)
            if not sigs:
                break

            page_count += 1
            print(f"    Page {page_count}: {len(sigs)} signatures", flush=True)

            # Filter by time
            filtered = []
            for sig_info in sigs:
                block_time = sig_info.get("blockTime")
                if block_time and block_time >= start_timestamp:
                    filtered.append({
                        "signature": sig_info["signature"],
                        "blockTime": block_time,
                        "ata": ata_pubkey,
                        "exchange": ex_addr
                    })
                else:
                    # Reached transactions before start_time, stop pagination
                    print(f"    Reached start time, stopping pagination", flush=True)
                    return all_signatures + filtered

            all_signatures.extend(filtered)

            # Check if we need to continue pagination
            if len(sigs) < 1000:
                break

            before = sigs[-1]["signature"]
            time.sleep(0.2)

    print(f"  Total signatures collected: {len(all_signatures)}", flush=True)
    return all_signatures

def parse_solana_transaction(api_key, signature):
    """Parse a Solana transaction to extract SPL token transfer details."""
    rpc_url = HELIUS_RPC.format(api_key=api_key)

    tx = rpc_call(rpc_url, "getTransaction", [
        signature,
        {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
    ])

    if not tx or not tx.get("meta"):
        return None

    block_time = tx.get("blockTime")
    if not block_time:
        return None

    # Parse token transfers from meta.postTokenBalances and preTokenBalances
    pre_balances = {b["accountIndex"]: b for b in tx["meta"].get("preTokenBalances", [])}
    post_balances = {b["accountIndex"]: b for b in tx["meta"].get("postTokenBalances", [])}

    transfers = []
    for idx, post in post_balances.items():
        pre = pre_balances.get(idx, {})
        pre_amount = int(pre.get("uiTokenAmount", {}).get("amount", 0))
        post_amount = int(post.get("uiTokenAmount", {}).get("amount", 0))

        if post_amount != pre_amount:
            decimals = post.get("uiTokenAmount", {}).get("decimals", 9)
            amount = abs(post_amount - pre_amount)
            account = post.get("owner")

            transfers.append({
                "account": account,
                "amount": amount,
                "decimals": decimals,
                "blockTime": block_time,
                "direction": "in" if post_amount > pre_amount else "out"
            })

    return transfers

def process_bsc_transfers(logs, exchange_lookup, decimals=18):
    flows = defaultdict(lambda: {"inflow": 0, "outflow": 0, "inflow_tx_count": 0, "outflow_tx_count": 0})
    for log in logs:
        topics = log.get("topics", [])
        if len(topics) < 3:
            continue
        from_addr = "0x" + topics[1][-40:]
        to_addr = "0x" + topics[2][-40:]
        value = int(log.get("data", "0x0"), 16) / (10 ** decimals)

        if from_addr.lower() in exchange_lookup:
            flows[exchange_lookup[from_addr.lower()]]["outflow"] += value
            flows[exchange_lookup[from_addr.lower()]]["outflow_tx_count"] += 1
        if to_addr.lower() in exchange_lookup:
            flows[exchange_lookup[to_addr.lower()]]["inflow"] += value
            flows[exchange_lookup[to_addr.lower()]]["inflow_tx_count"] += 1

    for ex in flows:
        flows[ex]["net_flow"] = flows[ex]["inflow"] - flows[ex]["outflow"]
    return dict(flows)

def aggregate_by_hour(transfers_by_timestamp, token_name, chain, contract, exchange_flows):
    """Group transfers into hourly snapshots."""
    hourly_data = {}
    for ts_str, flows in exchange_flows.items():
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        hour_key = dt.replace(minute=0, second=0, microsecond=0).isoformat().replace('+00:00', 'Z')

        if hour_key not in hourly_data:
            hourly_data[hour_key] = {}

        for exchange, flow_data in flows.items():
            if exchange not in hourly_data[hour_key]:
                hourly_data[hour_key][exchange] = {"inflow": 0, "outflow": 0, "net_flow": 0, "inflow_tx_count": 0, "outflow_tx_count": 0}
            hourly_data[hour_key][exchange]["inflow"] += flow_data["inflow"]
            hourly_data[hour_key][exchange]["outflow"] += flow_data["outflow"]
            hourly_data[hour_key][exchange]["net_flow"] += flow_data["net_flow"]
            hourly_data[hour_key][exchange]["inflow_tx_count"] += flow_data["inflow_tx_count"]
            hourly_data[hour_key][exchange]["outflow_tx_count"] += flow_data["outflow_tx_count"]

    return hourly_data

def aggregate_by_hour_solana(exchange_flows, token_name, chain, contract):
    """Group Solana transfers into hourly snapshots."""
    hourly_data = {}
    for ts_str, flows in exchange_flows.items():
        dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
        hour_key = dt.replace(minute=0, second=0, microsecond=0).isoformat().replace('+00:00', 'Z')

        if hour_key not in hourly_data:
            hourly_data[hour_key] = {}

        for exchange, flow_data in flows.items():
            if exchange not in hourly_data[hour_key]:
                hourly_data[hour_key][exchange] = {"inflow": 0, "outflow": 0, "net_flow": 0, "inflow_tx_count": 0, "outflow_tx_count": 0}
            hourly_data[hour_key][exchange]["inflow"] += flow_data["inflow"]
            hourly_data[hour_key][exchange]["outflow"] += flow_data["outflow"]
            hourly_data[hour_key][exchange]["net_flow"] += flow_data["net_flow"]
            hourly_data[hour_key][exchange]["inflow_tx_count"] += flow_data["inflow_tx_count"]
            hourly_data[hour_key][exchange]["outflow_tx_count"] += flow_data["outflow_tx_count"]

    return hourly_data

def write_to_jsonl(hourly_data, token_name, chain, contract):
    """Write hourly snapshots to daily JSONL files with smart merging."""
    by_date = defaultdict(list)
    for hour_ts, flows in sorted(hourly_data.items()):
        dt = datetime.fromisoformat(hour_ts.replace('Z', '+00:00'))
        date_key = dt.strftime('%Y-%m-%d')

        total_inflow = sum(f["inflow"] for f in flows.values())
        total_outflow = sum(f["outflow"] for f in flows.values())

        snapshot = {
            "timestamp": hour_ts,
            "lookback_seconds": 3600,
            "tokens": {
                token_name: {
                    "deployments": [{
                        "chain": chain,
                        "contract": contract,
                        "exchange_flows": flows
                    }],
                    "total_inflow": total_inflow,
                    "total_outflow": total_outflow,
                    "net_flow": total_inflow - total_outflow
                }
            }
        }
        by_date[date_key].append(snapshot)

    for date_key, snapshots in by_date.items():
        file_path = HISTORY_DIR / f"{date_key}.jsonl"

        # Read existing data and index by timestamp
        existing_data = {}
        if file_path.exists():
            with open(file_path, 'r') as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        existing_data[record["timestamp"]] = record

        # Merge new snapshots into existing data
        for snap in snapshots:
            ts = snap["timestamp"]
            if ts in existing_data:
                # Merge tokens: add new token to existing record
                existing_data[ts]["tokens"][token_name] = snap["tokens"][token_name]
            else:
                # New timestamp: add entire snapshot
                existing_data[ts] = snap

        # Write back all data sorted by timestamp
        with open(file_path, 'w') as f:
            for ts in sorted(existing_data.keys()):
                f.write(json.dumps(existing_data[ts]) + '\n')

        print(f"    Wrote {len(snapshots)} snapshots to {date_key}.jsonl", flush=True)

def backfill_token(token_name, deployments, exchange_lookup, api_keys):
    print(f"\n=== Backfilling {token_name} ===", flush=True)
    tge_info = TGE_BLOCKS.get(token_name, {})

    for deployment in deployments:
        chain = deployment["chain"]
        contract = deployment["contract"]

        if chain == "solana":
            api_key = api_keys.get("solana")
            if not api_key:
                print(f"  No Helius API key, skipping", flush=True)
                continue

            start_time = tge_info.get("solana")
            if not start_time:
                print(f"  No TGE time for Solana, skipping", flush=True)
                continue

            print(f"  Solana: {contract} from {start_time}", flush=True)

            # Get exchange addresses for Solana
            sol_exchange_lookup = exchange_lookup.get("solana", {})
            sol_exchanges = list(sol_exchange_lookup.keys())

            if not sol_exchanges:
                print(f"  No Solana exchange addresses configured", flush=True)
                continue

            # Fetch all signatures since TGE
            signatures = fetch_solana_signatures_since(api_key, contract, sol_exchanges, start_time)

            if not signatures:
                print(f"  No signatures found", flush=True)
                continue

            # Parse transactions in batches
            print(f"  Parsing {len(signatures)} transactions...", flush=True)
            exchange_flows = {}

            for i, sig_info in enumerate(signatures):
                if i % 100 == 0:
                    print(f"    Progress: {i}/{len(signatures)}", flush=True)

                transfers = parse_solana_transaction(api_key, sig_info["signature"])
                if not transfers:
                    continue

                ts = datetime.fromtimestamp(sig_info["blockTime"], tz=timezone.utc).isoformat().replace('+00:00', 'Z')
                if ts not in exchange_flows:
                    exchange_flows[ts] = {}

                # Match transfers to exchanges
                sol_exchange_lookup = exchange_lookup.get("solana", {})
                for transfer in transfers:
                    account = transfer.get("account", "").lower()
                    if account in sol_exchange_lookup:
                        ex = sol_exchange_lookup[account]
                        if ex not in exchange_flows[ts]:
                            exchange_flows[ts][ex] = {"inflow": 0, "outflow": 0, "net_flow": 0, "inflow_tx_count": 0, "outflow_tx_count": 0}

                        amount = transfer["amount"] / (10 ** transfer["decimals"])
                        if transfer["direction"] == "in":
                            exchange_flows[ts][ex]["inflow"] += amount
                            exchange_flows[ts][ex]["inflow_tx_count"] += 1
                        else:
                            exchange_flows[ts][ex]["outflow"] += amount
                            exchange_flows[ts][ex]["outflow_tx_count"] += 1

                time.sleep(0.05)  # Rate limiting

            # Calculate net flows
            for ts in exchange_flows:
                for ex in exchange_flows[ts]:
                    exchange_flows[ts][ex]["net_flow"] = exchange_flows[ts][ex]["inflow"] - exchange_flows[ts][ex]["outflow"]

            # Aggregate by hour and write
            hourly_data = aggregate_by_hour_solana(exchange_flows, token_name, chain, contract)
            write_to_jsonl(hourly_data, token_name, chain, contract)
            continue

        start_block = tge_info.get(chain)
        if not start_block:
            print(f"  No TGE block for {chain}, skipping", flush=True)
            continue

        all_transfers = []

        if chain == "ethereum":
            api_key = api_keys.get("eth")
            if not api_key:
                continue
            current_block = get_current_block_eth(api_key)
            print(f"  ETH: {contract} from block {start_block} to {current_block}", flush=True)

            block_range = 10000
            for block in range(start_block, current_block, block_range):
                end = min(block + block_range - 1, current_block)
                print(f"    Fetching blocks {block}-{end}...", flush=True)
                transfers = fetch_eth_transfers_range(api_key, contract, block, end)
                all_transfers.extend(transfers)
                print(f"      Got {len(transfers)} transfers", flush=True)
                time.sleep(0.2)

            exchange_flows = {}
            for tx in all_transfers:
                ts = datetime.fromtimestamp(int(tx.get("timeStamp", 0)), tz=timezone.utc).isoformat().replace('+00:00', 'Z')
                if ts not in exchange_flows:
                    exchange_flows[ts] = {}

                from_addr = tx.get("from", "").lower()
                to_addr = tx.get("to", "").lower()
                value = float(tx.get("value", 0)) / 1e18

                if from_addr in exchange_lookup.get("ethereum", {}):
                    ex = exchange_lookup["ethereum"][from_addr]
                    if ex not in exchange_flows[ts]:
                        exchange_flows[ts][ex] = {"inflow": 0, "outflow": 0, "net_flow": 0, "inflow_tx_count": 0, "outflow_tx_count": 0}
                    exchange_flows[ts][ex]["outflow"] += value
                    exchange_flows[ts][ex]["outflow_tx_count"] += 1

                if to_addr in exchange_lookup.get("ethereum", {}):
                    ex = exchange_lookup["ethereum"][to_addr]
                    if ex not in exchange_flows[ts]:
                        exchange_flows[ts][ex] = {"inflow": 0, "outflow": 0, "net_flow": 0, "inflow_tx_count": 0, "outflow_tx_count": 0}
                    exchange_flows[ts][ex]["inflow"] += value
                    exchange_flows[ts][ex]["inflow_tx_count"] += 1

            for ts in exchange_flows:
                for ex in exchange_flows[ts]:
                    exchange_flows[ts][ex]["net_flow"] = exchange_flows[ts][ex]["inflow"] - exchange_flows[ts][ex]["outflow"]

            hourly_data = aggregate_by_hour(all_transfers, token_name, chain, contract, exchange_flows)
            write_to_jsonl(hourly_data, token_name, chain, contract)

        elif chain == "bsc":
            api_key = api_keys.get("bsc")
            if not api_key:
                continue
            current_block = get_current_block_bsc(api_key)
            print(f"  BSC: {contract} from block {start_block} to {current_block}", flush=True)

            block_range = 5000
            all_logs = []
            for block in range(start_block, current_block, block_range):
                end = min(block + block_range - 1, current_block)
                print(f"    Fetching blocks {block}-{end}...", flush=True)
                logs = fetch_bsc_transfers_range(api_key, contract, block, end)
                all_logs.extend(logs)
                print(f"      Got {len(logs)} logs", flush=True)
                time.sleep(0.2)

            exchange_flows = {}
            for log in all_logs:
                block_num = int(log.get("blockNumber", "0x0"), 16)
                # BSC timestamp estimation: Calculate based on block number
                # BSC block time: ~3 seconds
                # Use TGE block as reference point instead of genesis
                # Estimate: current_time - (current_block - block_num) * 3
                blocks_ago = current_block - block_num
                estimated_timestamp = int(time.time()) - (blocks_ago * 3)
                ts = datetime.fromtimestamp(estimated_timestamp, tz=timezone.utc).isoformat().replace('+00:00', 'Z')

                topics = log.get("topics", [])
                if len(topics) < 3:
                    continue

                from_addr = "0x" + topics[1][-40:]
                to_addr = "0x" + topics[2][-40:]
                value = int(log.get("data", "0x0"), 16) / 1e18

                if ts not in exchange_flows:
                    exchange_flows[ts] = {}

                if from_addr.lower() in exchange_lookup.get("bsc", {}):
                    ex = exchange_lookup["bsc"][from_addr.lower()]
                    if ex not in exchange_flows[ts]:
                        exchange_flows[ts][ex] = {"inflow": 0, "outflow": 0, "net_flow": 0, "inflow_tx_count": 0, "outflow_tx_count": 0}
                    exchange_flows[ts][ex]["outflow"] += value
                    exchange_flows[ts][ex]["outflow_tx_count"] += 1

                if to_addr.lower() in exchange_lookup.get("bsc", {}):
                    ex = exchange_lookup["bsc"][to_addr.lower()]
                    if ex not in exchange_flows[ts]:
                        exchange_flows[ts][ex] = {"inflow": 0, "outflow": 0, "net_flow": 0, "inflow_tx_count": 0, "outflow_tx_count": 0}
                    exchange_flows[ts][ex]["inflow"] += value
                    exchange_flows[ts][ex]["inflow_tx_count"] += 1

            for ts in exchange_flows:
                for ex in exchange_flows[ts]:
                    exchange_flows[ts][ex]["net_flow"] = exchange_flows[ts][ex]["inflow"] - exchange_flows[ts][ex]["outflow"]

            hourly_data = aggregate_by_hour(all_logs, token_name, chain, contract, exchange_flows)
            write_to_jsonl(hourly_data, token_name, chain, contract)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Backfill historical token data")
    parser.add_argument("--token", type=str, help="Specific token to backfill (e.g., AZTEC). If not specified, backfills all tokens.")
    args = parser.parse_args()

    HISTORY_DIR.mkdir(exist_ok=True)

    with open(TOKENS_FILE) as f:
        tokens = json.load(f)
    with open(EXCHANGES_FILE) as f:
        exchanges = json.load(f)

    exchange_lookup = load_exchange_lookup(exchanges)

    api_keys = {
        "eth": os.getenv("ETHERSCAN_API_KEY", ""),
        "bsc": os.getenv("BSCTrace_API_KEY", ""),
        "helius": os.getenv("HELIUS_API_KEY", "")
    }

    # Validate API keys
    print("=== API Key Status ===", flush=True)
    for key_name, key_value in api_keys.items():
        status = "✓ SET" if key_value else "✗ MISSING"
        print(f"  {key_name}: {status}", flush=True)
    print("", flush=True)

    # Filter tokens if specific token requested
    if args.token:
        if args.token not in tokens:
            print(f"Error: Token '{args.token}' not found in tokens.json", flush=True)
            sys.exit(1)
        tokens_to_process = {args.token: tokens[args.token]}
        print(f"Processing single token: {args.token}", flush=True)
    else:
        tokens_to_process = tokens
        print(f"Processing all {len(tokens)} tokens", flush=True)

    for token_name, deployments in tokens_to_process.items():
        backfill_token(token_name, deployments, exchange_lookup, api_keys)

    print("\n✓ Backfill complete", flush=True)

if __name__ == "__main__":
    main()
