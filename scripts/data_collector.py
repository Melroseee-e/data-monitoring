#!/usr/bin/env python3
"""
Data collector for on-chain token exchange flow monitoring.

APIs used:
  - Ethereum: Etherscan (tokentx endpoint)
  - BSC:      BSCTrace / NodeReal (eth_getLogs JSON-RPC)
  - Solana:   Helius (standard RPC via getTokenAccountsByOwner + getTransaction)

Reads:  data/tokens.json, data/exchange_addresses_normalized.json
Writes: data/latest_data.json, data/history/<date>.jsonl, data/history_summary.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
TOKENS_FILE = BASE_DIR / "data" / "tokens.json"
EXCHANGES_FILE = BASE_DIR / "data" / "exchange_addresses_normalized.json"
OUTPUT_FILE = BASE_DIR / "data" / "latest_data.json"
HISTORY_DIR = BASE_DIR / "data" / "history"
HISTORY_SUMMARY_FILE = BASE_DIR / "data" / "history_summary.json"

# API endpoints
ETHERSCAN_API = "https://api.etherscan.io/v2/api"
BSCTRACE_RPC = "https://bsc-mainnet.nodereal.io/v1/{api_key}"
HELIUS_RPC = "https://mainnet.helius-rpc.com/?api-key={api_key}"

# ERC-20 Transfer event signature
TRANSFER_EVENT_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# How far back to look (seconds)
LOOKBACK_SECONDS = 3600  # 1 hour


def get_env(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        print(f"WARNING: {name} not set, skipping related chains", file=sys.stderr)
    return val


def get_env_list(*names: str) -> list[str]:
    """Read one or more env vars as a deduplicated list of comma-separated values."""
    values = []
    seen = set()
    for name in names:
        raw = os.environ.get(name, "")
        if not raw:
            continue
        for part in raw.split(","):
            value = part.strip()
            if not value or value in seen:
                continue
            seen.add(value)
            values.append(value)
    if not values and names:
        print(f"WARNING: none of {', '.join(names)} set, skipping related chains", file=sys.stderr)
    return values


def floor_to_hour_iso_utc(dt: datetime) -> str:
    """Floor datetime to UTC hour and format as ISO Z."""
    dt_utc = dt.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_to_hour_iso_utc(ts: str) -> str | None:
    """Parse arbitrary ISO timestamp and return floored UTC hour ISO Z."""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None
    return floor_to_hour_iso_utc(dt)


def load_exchange_lookup(exchanges_data: dict) -> dict:
    """Build chain -> address -> exchange_name lookup."""
    lookup = defaultdict(dict)
    for exchange_name, chains in exchanges_data.items():
        for chain, addresses in chains.items():
            for addr in addresses:
                # Solana addresses are case-sensitive, EVM addresses are not
                key = addr if chain == "solana" else addr.lower()
                lookup[chain][key] = exchange_name
    return dict(lookup)


def get_exchange_addresses_for_chain(exchanges_data: dict, chain: str) -> list[str]:
    """Get all exchange addresses for a specific chain."""
    addresses = []
    for _name, chains in exchanges_data.items():
        if chain in chains:
            addresses.extend(chains[chain])
    return addresses


# ── Ethereum (Etherscan) ──────────────────────────────────────────────


def get_current_block_etherscan(api_key: str) -> int | None:
    """Get latest Ethereum block number from Etherscan."""
    params = {"chainid": "1", "module": "proxy", "action": "eth_blockNumber", "apikey": api_key}
    try:
        resp = requests.get(ETHERSCAN_API, params=params, timeout=15)
        return int(resp.json()["result"], 16)
    except Exception as e:
        print(f"  ERROR getting ETH block number: {e}")
        return None


def get_eth_token_transfers(api_key: str, contract: str, start_block: int) -> list[dict]:
    """Fetch ERC-20 token transfers via Etherscan tokentx endpoint."""
    params = {
        "chainid": "1",
        "module": "account",
        "action": "tokentx",
        "contractaddress": contract,
        "startblock": start_block,
        "endblock": 99999999,
        "sort": "desc",
        "apikey": api_key,
    }
    try:
        resp = requests.get(ETHERSCAN_API, params=params, timeout=30)
        data = resp.json()
        if data.get("status") == "1" and data.get("result"):
            return data["result"]
        return []
    except Exception as e:
        print(f"  ERROR fetching ETH transfers: {e}")
        return []


def process_evm_transfers(
    transfers: list[dict], exchange_lookup: dict, decimals: int | None = None
) -> dict:
    """Match EVM transfers against exchange addresses, compute flows."""
    inflows = defaultdict(float)
    outflows = defaultdict(float)
    tx_count_in = defaultdict(int)
    tx_count_out = defaultdict(int)

    for tx in transfers:
        to_addr = tx.get("to", "").lower()
        from_addr = tx.get("from", "").lower()
        token_decimals = decimals or int(tx.get("tokenDecimal", 18))
        value = int(tx.get("value", 0)) / (10 ** token_decimals)

        if to_addr in exchange_lookup:
            ex_name = exchange_lookup[to_addr]
            inflows[ex_name] += value
            tx_count_in[ex_name] += 1

        if from_addr in exchange_lookup:
            ex_name = exchange_lookup[from_addr]
            outflows[ex_name] += value
            tx_count_out[ex_name] += 1

    result = {}
    all_exchanges = set(inflows.keys()) | set(outflows.keys())
    for ex in sorted(all_exchanges):
        result[ex] = {
            "inflow": round(inflows[ex], 4),
            "outflow": round(outflows[ex], 4),
            "net_flow": round(inflows[ex] - outflows[ex], 4),
            "inflow_tx_count": tx_count_in[ex],
            "outflow_tx_count": tx_count_out[ex],
        }
    return result


# ── BSC (BSCTrace / NodeReal JSON-RPC) ────────────────────────────────


def rpc_call(rpc_url: str, method: str, params: list, max_retries: int = 5) -> dict | list | None:
    """Make a JSON-RPC call with retry/backoff for transient failures."""
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    for attempt in range(max_retries):
        try:
            resp = requests.post(rpc_url, json=payload, timeout=30)
            # Helius can return HTTP 429 at transport level
            if resp.status_code == 429:
                wait_s = min(30, 2 ** attempt)
                print(f"  RPC rate limited ({method}), retry in {wait_s}s...")
                time.sleep(wait_s)
                continue

            resp.raise_for_status()
            data = resp.json()
            err = data.get("error")
            if err:
                # Helius JSON-RPC rate-limit code
                if err.get("code") == -32429:
                    wait_s = min(30, 2 ** attempt)
                    print(f"  RPC error ({method}): {err} -> retry in {wait_s}s...")
                    time.sleep(wait_s)
                    continue
                print(f"  RPC error ({method}): {err}")
                return None
            return data.get("result")
        except requests.exceptions.RequestException as e:
            wait_s = min(30, 2 ** attempt)
            if attempt < max_retries - 1:
                print(f"  ERROR in RPC {method}: {e} -> retry in {wait_s}s...")
                time.sleep(wait_s)
                continue
            print(f"  ERROR in RPC {method}: {e}")
            return None
        except Exception as e:
            print(f"  ERROR in RPC {method}: {e}")
            return None
    return None


def _helius_error_requires_rotation(status_code: int | None, err: dict | None) -> bool:
    """Return True when the current Helius key is likely exhausted or blocked."""
    if status_code in {401, 402, 403}:
        return True
    if status_code == 429:
        return True
    if not err:
        return False

    message = " ".join(
        str(err.get(field, ""))
        for field in ("message", "details", "data")
    ).lower()
    if any(
        marker in message
        for marker in ("credit", "quota", "billing", "exhaust", "insufficient", "limit exceeded")
    ):
        return True
    return False


def helius_rpc_call(
    rpc_urls: list[str], method: str, params: list, max_retries_per_key: int = 5
) -> dict | list | None:
    """Call Helius RPC and rotate across multiple keys on quota/rate-limit failures."""
    if not rpc_urls:
        return None

    for key_index, rpc_url in enumerate(rpc_urls, start=1):
        for attempt in range(max_retries_per_key):
            try:
                resp = requests.post(
                    rpc_url,
                    json={"jsonrpc": "2.0", "method": method, "params": params, "id": 1},
                    timeout=30,
                )
                if resp.status_code == 429:
                    wait_s = min(30, 2 ** attempt)
                    if key_index < len(rpc_urls):
                        print(
                            f"  RPC rate limited ({method}) on Helius key {key_index}, rotating..."
                        )
                        break
                    print(f"  RPC rate limited ({method}), retry in {wait_s}s...")
                    time.sleep(wait_s)
                    continue

                if resp.status_code in {401, 402, 403}:
                    if key_index < len(rpc_urls):
                        print(
                            f"  RPC auth/quota error ({method}) on Helius key {key_index}, rotating..."
                        )
                        break
                    print(f"  RPC auth/quota error ({method}): HTTP {resp.status_code}")
                    return None

                resp.raise_for_status()
                data = resp.json()
                err = data.get("error")
                if err:
                    if _helius_error_requires_rotation(None, err):
                        if key_index < len(rpc_urls):
                            print(
                                f"  RPC error ({method}) on Helius key {key_index}: {err} -> rotating..."
                            )
                            break
                        wait_s = min(30, 2 ** attempt)
                        print(f"  RPC error ({method}): {err} -> retry in {wait_s}s...")
                        time.sleep(wait_s)
                        continue
                    print(f"  RPC error ({method}): {err}")
                    return None
                return data.get("result")
            except requests.exceptions.RequestException as e:
                wait_s = min(30, 2 ** attempt)
                if attempt < max_retries_per_key - 1:
                    print(f"  ERROR in RPC {method}: {e} -> retry in {wait_s}s...")
                    time.sleep(wait_s)
                    continue
                if key_index < len(rpc_urls):
                    print(
                        f"  ERROR in RPC {method} on Helius key {key_index}: {e} -> rotating..."
                    )
                    break
                print(f"  ERROR in RPC {method}: {e}")
                return None
            except Exception as e:
                print(f"  ERROR in RPC {method}: {e}")
                return None

    return None


def get_bsc_transfers(api_key: str, contract: str, start_block: int) -> list[dict]:
    """Fetch ERC-20 Transfer events on BSC using eth_getLogs via NodeReal."""
    rpc_url = BSCTRACE_RPC.format(api_key=api_key)

    # Get current block
    current_block = rpc_call(rpc_url, "eth_blockNumber", [])
    if not current_block:
        return []
    current_block_int = int(current_block, 16)
    print(f"    BSC current block: {current_block_int}, querying from {start_block}")

    logs = rpc_call(rpc_url, "eth_getLogs", [{
        "address": contract,
        "topics": [TRANSFER_EVENT_TOPIC],
        "fromBlock": hex(start_block),
        "toBlock": "latest",
    }])

    if not logs:
        return []

    transfers = []
    for log in logs:
        topics = log.get("topics", [])
        if len(topics) < 3:
            continue
        transfers.append({
            "from": "0x" + topics[1][-40:],
            "to": "0x" + topics[2][-40:],
            "value": str(int(log.get("data", "0x0"), 16)),
            "blockNumber": str(int(log.get("blockNumber", "0x0"), 16)),
            "transactionHash": log.get("transactionHash", ""),
        })

    return transfers


def process_bsc_transfers(
    transfers: list[dict], exchange_lookup: dict, decimals: int = 18
) -> dict:
    """Match BSC log-decoded transfers against exchange addresses."""
    inflows = defaultdict(float)
    outflows = defaultdict(float)
    tx_count_in = defaultdict(int)
    tx_count_out = defaultdict(int)

    for tx in transfers:
        to_addr = tx["to"].lower()
        from_addr = tx["from"].lower()
        value = int(tx["value"]) / (10 ** decimals)

        if to_addr in exchange_lookup:
            ex_name = exchange_lookup[to_addr]
            inflows[ex_name] += value
            tx_count_in[ex_name] += 1

        if from_addr in exchange_lookup:
            ex_name = exchange_lookup[from_addr]
            outflows[ex_name] += value
            tx_count_out[ex_name] += 1

    result = {}
    all_exchanges = set(inflows.keys()) | set(outflows.keys())
    for ex in sorted(all_exchanges):
        result[ex] = {
            "inflow": round(inflows[ex], 4),
            "outflow": round(outflows[ex], 4),
            "net_flow": round(inflows[ex] - outflows[ex], 4),
            "inflow_tx_count": tx_count_in[ex],
            "outflow_tx_count": tx_count_out[ex],
        }
    return result


# ── Solana (Helius RPC) ───────────────────────────────────────────────


def get_solana_transfers_helius(
    api_keys: list[str], token_mint: str, exchange_addresses: list[str],
    lookback_seconds: int = 3600,
) -> list[dict]:
    """
    Fetch SPL token transfers to/from exchange addresses via Helius RPC.

    Strategy (credit-efficient):
    1. getTokenAccountsByOwner per exchange address (1 credit each)
    2. getSignaturesForAddress per found token account (1 credit each)
    3. getTransaction per signature for transfer details (1 credit each)
    """
    if not api_keys:
        return []

    rpc_urls = [HELIUS_RPC.format(api_key=api_key) for api_key in api_keys]
    cutoff_time = int(time.time()) - lookback_seconds
    all_transfers = []

    # Map: token_account_pubkey -> exchange_address
    ata_to_exchange = {}

    # Step 1: Find ATAs for each exchange address
    for addr in exchange_addresses:
        result = helius_rpc_call(rpc_urls, "getTokenAccountsByOwner", [
            addr,
            {"mint": token_mint},
            {"encoding": "jsonParsed"},
        ])
        if not result or not result.get("value"):
            continue
        for acct in result["value"]:
            ata_to_exchange[acct["pubkey"]] = addr
        time.sleep(0.1)  # rate limit

    if not ata_to_exchange:
        print(f"    No exchange ATAs found for mint {token_mint[:8]}...")
        return []

    print(f"    Found {len(ata_to_exchange)} exchange ATAs")

    # Step 2: Get recent signatures for each ATA
    signatures_to_fetch = []
    for ata_pubkey, _ex_addr in ata_to_exchange.items():
        sigs = helius_rpc_call(rpc_urls, "getSignaturesForAddress", [
            ata_pubkey,
            {"limit": 20},
        ])
        if not sigs:
            continue
        for sig_info in sigs:
            block_time = sig_info.get("blockTime", 0)
            if block_time and block_time < cutoff_time:
                break
            if sig_info.get("err"):
                continue
            signatures_to_fetch.append(sig_info["signature"])
        time.sleep(0.1)

    # Deduplicate signatures (same tx may touch multiple exchange ATAs)
    signatures_to_fetch = list(dict.fromkeys(signatures_to_fetch))
    print(f"    Fetching {len(signatures_to_fetch)} transactions")

    # Step 3: Parse each transaction
    for sig in signatures_to_fetch:
        tx_data = helius_rpc_call(rpc_urls, "getTransaction", [
            sig,
            {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0},
        ])
        if not tx_data:
            continue

        meta = tx_data.get("meta", {})
        if meta.get("err"):
            continue

        # Extract SPL token transfers from inner instructions and main instructions
        parsed_transfers = _extract_spl_transfers(tx_data, token_mint)
        for t in parsed_transfers:
            t["signature"] = sig
            t["blockTime"] = tx_data.get("blockTime", 0)
        all_transfers.extend(parsed_transfers)
        time.sleep(0.1)

    return all_transfers


def _extract_spl_transfers(tx_data: dict, target_mint: str) -> list[dict]:
    """Extract SPL token transfer details from a parsed transaction."""
    transfers = []
    meta = tx_data.get("meta", {})

    # Use pre/post token balances to detect transfers
    pre_balances = {}
    for b in meta.get("preTokenBalances", []):
        if b.get("mint") == target_mint:
            owner = b.get("owner", "")
            amount = int(b.get("uiTokenAmount", {}).get("amount", "0"))
            pre_balances[owner] = amount

    post_balances = {}
    for b in meta.get("postTokenBalances", []):
        if b.get("mint") == target_mint:
            owner = b.get("owner", "")
            amount = int(b.get("uiTokenAmount", {}).get("amount", "0"))
            decimals = b.get("uiTokenAmount", {}).get("decimals", 9)
            post_balances[owner] = (amount, decimals)

    # Find accounts with balance changes
    all_owners = set(pre_balances.keys()) | set(post_balances.keys())
    increases = {}  # owner -> amount increased
    decreases = {}  # owner -> amount decreased

    for owner in all_owners:
        pre = pre_balances.get(owner, 0)
        post_amount, decimals = post_balances.get(owner, (0, 9))
        diff = post_amount - pre
        if diff > 0:
            increases[owner] = (diff, decimals)
        elif diff < 0:
            decreases[owner] = (abs(diff), decimals)

    # Pair senders (decreases) with receivers (increases)
    for sender, (send_amount, decimals) in decreases.items():
        for receiver, (recv_amount, _) in increases.items():
            # Match if amounts are close (accounting for fees)
            if abs(send_amount - recv_amount) <= max(send_amount * 0.01, 1):
                transfers.append({
                    "from_address": sender,
                    "to_address": receiver,
                    "amount": recv_amount,
                    "decimals": decimals,
                })
                break

    # If no pairs matched, record individual changes
    if not transfers and (increases or decreases):
        for receiver, (amount, decimals) in increases.items():
            transfers.append({
                "from_address": "",
                "to_address": receiver,
                "amount": amount,
                "decimals": decimals,
            })
        for sender, (amount, decimals) in decreases.items():
            transfers.append({
                "from_address": sender,
                "to_address": "",
                "amount": amount,
                "decimals": decimals,
            })

    return transfers


def process_solana_transfers(transfers: list[dict], exchange_lookup: dict) -> dict:
    """Match Solana transfers against exchange addresses."""
    inflows = defaultdict(float)
    outflows = defaultdict(float)
    tx_count_in = defaultdict(int)
    tx_count_out = defaultdict(int)

    for tx in transfers:
        to_addr = tx.get("to_address", "")  # Solana addresses are case-sensitive
        from_addr = tx.get("from_address", "")  # Solana addresses are case-sensitive
        decimals = int(tx.get("decimals", 9))
        amount = int(tx.get("amount", 0)) / (10 ** decimals)

        if to_addr in exchange_lookup:
            ex_name = exchange_lookup[to_addr]
            inflows[ex_name] += amount
            tx_count_in[ex_name] += 1

        if from_addr in exchange_lookup:
            ex_name = exchange_lookup[from_addr]
            outflows[ex_name] += amount
            tx_count_out[ex_name] += 1

    result = {}
    all_exchanges = set(inflows.keys()) | set(outflows.keys())
    for ex in sorted(all_exchanges):
        result[ex] = {
            "inflow": round(inflows[ex], 4),
            "outflow": round(outflows[ex], 4),
            "net_flow": round(inflows[ex] - outflows[ex], 4),
            "inflow_tx_count": tx_count_in[ex],
            "outflow_tx_count": tx_count_out[ex],
        }
    return result


# ── Main ──────────────────────────────────────────────────────────────


def collect_token_data(
    symbol: str,
    chain: str,
    contract: str,
    exchange_lookup: dict,
    exchanges_data: dict,
    api_keys: dict,
) -> dict:
    """Collect exchange flow data for a single token deployment."""
    print(f"  Collecting {symbol} on {chain}...")

    chain_lookup = exchange_lookup.get(chain, {})
    if not chain_lookup:
        print(f"    No exchange addresses configured for {chain}")
        return {}

    if chain == "ethereum":
        api_key = api_keys.get("ethereum", "")
        if not api_key:
            print(f"    Skipping — no ETHERSCAN_API_KEY")
            return {}

        current_block = get_current_block_etherscan(api_key)
        if not current_block:
            return {}

        blocks_per_hour = 300  # ~12s per block
        start_block = max(0, current_block - blocks_per_hour)
        transfers = get_eth_token_transfers(api_key, contract, start_block)
        print(f"    Found {len(transfers)} transfers")
        time.sleep(0.25)
        return process_evm_transfers(transfers, chain_lookup)

    elif chain == "bsc":
        api_key = api_keys.get("bsc", "")
        if not api_key:
            print(f"    Skipping — no BSCTrace_API_KEY")
            return {}

        rpc_url = BSCTRACE_RPC.format(api_key=api_key)
        current_block = rpc_call(rpc_url, "eth_blockNumber", [])
        if not current_block:
            return {}

        current_block_int = int(current_block, 16)
        blocks_per_hour = 1200  # ~3s per block
        start_block = max(0, current_block_int - blocks_per_hour)

        transfers = get_bsc_transfers(api_key, contract, start_block)
        print(f"    Found {len(transfers)} transfers")
        return process_bsc_transfers(transfers, chain_lookup)

    elif chain == "solana":
        solana_api_keys = api_keys.get("solana", [])
        if not solana_api_keys:
            print(f"    Skipping — no HELIUS_API_KEY / HELIUS_API_KEYS")
            return {}

        sol_exchange_addrs = get_exchange_addresses_for_chain(exchanges_data, "solana")
        transfers = get_solana_transfers_helius(
            solana_api_keys, contract, sol_exchange_addrs, LOOKBACK_SECONDS
        )
        print(f"    Found {len(transfers)} transfers")
        return process_solana_transfers(transfers, chain_lookup)

    else:
        print(f"    Unsupported chain: {chain}")
        return {}


def _build_token_summary_entry(tdata: dict) -> dict:
    token_entry = {
        "total_inflow": tdata.get("total_inflow", 0),
        "total_outflow": tdata.get("total_outflow", 0),
        "net_flow": tdata.get("net_flow", 0),
    }
    exchange_summary = {}
    for dep in tdata.get("deployments", []):
        for ex, flows in dep.get("exchange_flows", {}).items():
            if ex not in exchange_summary:
                exchange_summary[ex] = {"inflow": 0, "outflow": 0, "net_flow": 0}
            exchange_summary[ex]["inflow"] += flows.get("inflow", 0)
            exchange_summary[ex]["outflow"] += flows.get("outflow", 0)
            exchange_summary[ex]["net_flow"] += flows.get("net_flow", 0)
    if exchange_summary:
        token_entry["exchanges"] = exchange_summary
    return token_entry


def _merge_token_deployments(existing_token: dict, incoming_token: dict) -> dict:
    """Merge two token payloads by deployment key (chain+contract)."""
    merged = {"deployments": []}
    dep_map = {}

    for dep in existing_token.get("deployments", []):
        key = (dep.get("chain"), dep.get("contract"))
        dep_map[key] = dep

    for dep in incoming_token.get("deployments", []):
        key = (dep.get("chain"), dep.get("contract"))
        dep_map[key] = dep

    merged["deployments"] = sorted(
        dep_map.values(),
        key=lambda d: (str(d.get("chain", "")), str(d.get("contract", "")))
    )

    total_inflow = 0.0
    total_outflow = 0.0
    for dep in merged["deployments"]:
        for flows in dep.get("exchange_flows", {}).values():
            total_inflow += float(flows.get("inflow", 0) or 0)
            total_outflow += float(flows.get("outflow", 0) or 0)

    merged["total_inflow"] = round(total_inflow, 4)
    merged["total_outflow"] = round(total_outflow, 4)
    merged["net_flow"] = round(total_inflow - total_outflow, 4)
    return merged


def upsert_history_snapshot(history_file: Path, output: dict) -> None:
    """Upsert one hourly snapshot by timestamp instead of always appending."""
    existing_by_ts = {}
    if history_file.exists():
        with open(history_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    ts = row.get("timestamp")
                    if ts:
                        existing_by_ts[ts] = row
                except json.JSONDecodeError:
                    continue

    ts = output["timestamp"]
    if ts in existing_by_ts:
        base = existing_by_ts[ts]
        base.setdefault("tokens", {})
        for symbol, new_token in output.get("tokens", {}).items():
            if symbol in base["tokens"]:
                base["tokens"][symbol] = _merge_token_deployments(base["tokens"][symbol], new_token)
            else:
                base["tokens"][symbol] = new_token
        base["lookback_seconds"] = output.get("lookback_seconds", base.get("lookback_seconds", LOOKBACK_SECONDS))
    else:
        existing_by_ts[ts] = output

    with open(history_file, "w") as f:
        for row_ts in sorted(existing_by_ts.keys()):
            f.write(json.dumps(existing_by_ts[row_ts]) + "\n")


def generate_history_summary():
    """Generate history_summary.json from recent hourly snapshots."""
    summary_by_ts = {}
    if not HISTORY_DIR.exists():
        return

    for file in sorted(HISTORY_DIR.glob("*.jsonl")):
        with open(file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                raw_ts = record.get("timestamp")
                if not raw_ts:
                    continue
                hour_ts = parse_iso_to_hour_iso_utc(raw_ts)
                if not hour_ts:
                    continue

                entry = summary_by_ts.setdefault(hour_ts, {"timestamp": hour_ts, "tokens": {}})
                for symbol, tdata in record.get("tokens", {}).items():
                    # Prefer exact-on-hour source for this bucket if both exist.
                    # Otherwise keep first-seen token in this hour bucket.
                    if symbol in entry["tokens"] and raw_ts != hour_ts:
                        continue
                    entry["tokens"][symbol] = _build_token_summary_entry(tdata)

    summary = sorted(summary_by_ts.values(), key=lambda x: x.get("timestamp", ""))
    # Keep recent window for frontend performance (7 days x 24 hourly points)
    summary = summary[-168:]

    with open(HISTORY_SUMMARY_FILE, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"History summary: {len(summary)} entries -> {HISTORY_SUMMARY_FILE}")


def main():
    with open(TOKENS_FILE) as f:
        tokens = json.load(f)

    with open(EXCHANGES_FILE) as f:
        exchanges_raw = json.load(f)

    exchange_lookup = load_exchange_lookup(exchanges_raw)

    api_keys = {
        "ethereum": get_env("ETHERSCAN_API_KEY"),
        "bsc": get_env("BSCTrace_API_KEY"),
        "solana": get_env_list("HELIUS_API_KEYS", "HELIUS_API_KEY", "HELIUS_API_KEY_2"),
    }

    now = datetime.now(timezone.utc)
    timestamp = floor_to_hour_iso_utc(now)
    snapshot_hour_dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    output = {
        "timestamp": timestamp,
        "lookback_seconds": LOOKBACK_SECONDS,
        "tokens": {},
    }

    for symbol, deployments in tokens.items():
        print(f"\n{'='*40}")
        print(f"Processing {symbol}")
        token_data = {"deployments": []}

        for dep in deployments:
            chain = dep["chain"]
            contract = dep["contract"]

            flows = collect_token_data(
                symbol, chain, contract, exchange_lookup, exchanges_raw, api_keys
            )

            deployment_result = {
                "chain": chain,
                "contract": contract,
                "exchange_flows": flows,
            }
            token_data["deployments"].append(deployment_result)

        total_inflow = 0
        total_outflow = 0
        for dep_data in token_data["deployments"]:
            for ex_flows in dep_data["exchange_flows"].values():
                total_inflow += ex_flows["inflow"]
                total_outflow += ex_flows["outflow"]

        token_data["total_inflow"] = round(total_inflow, 4)
        token_data["total_outflow"] = round(total_outflow, 4)
        token_data["net_flow"] = round(total_inflow - total_outflow, 4)

        output["tokens"][symbol] = token_data

    # Write latest data
    with open(OUTPUT_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWritten to {OUTPUT_FILE}")

    # Append to history
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    history_file = HISTORY_DIR / f"{snapshot_hour_dt.strftime('%Y-%m-%d')}.jsonl"
    upsert_history_snapshot(history_file, output)
    print(f"Upserted to {history_file}")

    # Generate history summary for frontend
    generate_history_summary()


if __name__ == "__main__":
    main()
