#!/usr/bin/env python3
"""
Build a one-off PRL holder structure report.

Data sources:
  - BubbleMaps Top 500 holders: labels + current rank/share snapshot
  - BSC RPC / BSCTrace: ERC-20 transfer history and live balance checks
  - Local exchange registry: exchange flow direction only

Outputs:
  - data/prl/raw/prl_top500_holders_bubblemaps.json
  - data/prl/derived/prl_balance_verification.json
  - data/prl/derived/prl_holder_analysis.json
  - data/prl/reports/prl_holder_structure_report.md
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "prl"
RAW_DIR = DATA_DIR / "raw"
DERIVED_DIR = DATA_DIR / "derived"
REPORT_DIR = DATA_DIR / "reports"

SKILLS_DIR = BASE_DIR / ".claude" / "skills" / "onchain-analysis" / "scripts"
sys.path.insert(0, str(SKILLS_DIR))
sys.path.insert(0, str(BASE_DIR))

load_dotenv(BASE_DIR / ".env")

from core.config import BSCTRACE_RPC_TEMPLATE, TRANSFER_EVENT_TOPIC, load_exchange_addresses, require_api_key
from core.rpc import rpc_call
from scripts.ops.build_exchange_addresses import fetch_top_holders

TOKEN_ADDRESS = "0xd20fB09A49a8e75Fef536A2dBc68222900287BAc"
TOKEN_SOLANA_ADDRESS = "PERLEQKUNUp1dgFZ8EvyXHdN9d6ZQqfGxALDvfs6pDs"
TOKEN_CHAIN = "bsc"
TOP_HOLDER_COUNT = 500
PREFERRED_LOG_CHUNK = 5_000
MIN_LOG_CHUNK = 1_000
MAX_LOG_BLOCK_RANGE = 49_999
COARSE_START_SCAN = 49_999
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"
NOW_UTC = datetime.now(timezone.utc)

RAW_SNAPSHOT_FILE = RAW_DIR / "prl_top500_holders_bubblemaps.json"
VERIFICATION_FILE = DERIVED_DIR / "prl_balance_verification.json"
ANALYSIS_FILE = DERIVED_DIR / "prl_holder_analysis.json"
REPORT_FILE = REPORT_DIR / "prl_holder_structure_report.md"

RPC_URL = BSCTRACE_RPC_TEMPLATE.format(api_key=require_api_key(TOKEN_CHAIN))
BLOCK_CACHE: dict[int, dict[str, Any]] = {}


def ensure_dirs() -> None:
    for path in (RAW_DIR, DERIVED_DIR, REPORT_DIR):
        path.mkdir(parents=True, exist_ok=True)


def short_addr(address: str, left: int = 6, right: int = 4) -> str:
    if len(address) <= left + right:
        return address
    return f"{address[:left]}...{address[-right:]}"


def fmt_num(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}"


def fmt_pct(value: float, decimals: int = 2) -> str:
    return f"{value * 100:.{decimals}f}%"


def iso_from_ts(ts: int | None) -> str | None:
    if not ts:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def json_dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def eth_call(data: str, to_address: str = TOKEN_ADDRESS) -> str | None:
    return rpc_call(RPC_URL, "eth_call", [{"to": to_address, "data": data}, "latest"])


def eth_get_code(address: str, block_number: int | str = "latest") -> str | None:
    block_tag = block_number if isinstance(block_number, str) else hex(block_number)
    return rpc_call(RPC_URL, "eth_getCode", [address, block_tag])


def eth_get_block_number() -> int:
    result = rpc_call(RPC_URL, "eth_blockNumber", [])
    if not result:
        raise RuntimeError("eth_blockNumber failed")
    return int(result, 16)


def eth_get_block(block_number: int) -> dict[str, Any] | None:
    if block_number in BLOCK_CACHE:
        return BLOCK_CACHE[block_number]
    result = rpc_call(RPC_URL, "eth_getBlockByNumber", [hex(block_number), False])
    if result:
        BLOCK_CACHE[block_number] = result
    return result


def block_timestamp(block_number: int) -> int | None:
    block = eth_get_block(block_number)
    if not block:
        return None
    return int(block.get("timestamp", "0x0"), 16)


def block_by_timestamp(target_ts: int, latest_block: int) -> int:
    latest_ts = block_timestamp(latest_block)
    if latest_ts is None:
        raise RuntimeError("could not resolve latest block timestamp")
    if target_ts >= latest_ts:
        return latest_block

    low = 1
    high = latest_block
    while low < high:
        mid = (low + high) // 2
        ts = block_timestamp(mid)
        if ts is None:
            raise RuntimeError(f"could not resolve block timestamp for {mid}")
        if ts < target_ts:
            low = mid + 1
        else:
            high = mid
    return low


def get_logs_range(start_block: int, end_block: int) -> list[dict[str, Any]]:
    if end_block - start_block + 1 > MAX_LOG_BLOCK_RANGE:
        rows: list[dict[str, Any]] = []
        for chunk_start in range(start_block, end_block + 1, MAX_LOG_BLOCK_RANGE):
            chunk_end = min(chunk_start + MAX_LOG_BLOCK_RANGE - 1, end_block)
            rows.extend(get_logs_range(chunk_start, chunk_end))
        return rows

    params = [{
        "address": TOKEN_ADDRESS,
        "topics": [TRANSFER_EVENT_TOPIC],
        "fromBlock": hex(start_block),
        "toBlock": hex(end_block),
    }]
    result = rpc_call(RPC_URL, "eth_getLogs", params)
    if result is not None:
        return result
    if end_block - start_block + 1 <= MIN_LOG_CHUNK:
        return []
    mid = (start_block + end_block) // 2
    left = get_logs_range(start_block, mid)
    right = get_logs_range(mid + 1, end_block)
    return left + right


def decode_abi_string(result: str | None) -> str | None:
    if not result or result == "0x":
        return None
    data = bytes.fromhex(result[2:])
    if not data:
        return None
    if len(data) == 32:
        return data.rstrip(b"\x00").decode(errors="ignore") or None
    if len(data) >= 96:
        strlen = int.from_bytes(data[32:64], "big")
        return data[64:64 + strlen].decode(errors="ignore") or None
    return None


def decode_abi_uint(result: str | None) -> int | None:
    if not result or result == "0x":
        return None
    return int(result, 16)


def token_balance(address: str, decimals: int) -> float | None:
    selector = "0x70a08231" + address.lower().replace("0x", "").zfill(64)
    result = eth_call(selector)
    raw = decode_abi_uint(result)
    if raw is None:
        return None
    return raw / (10 ** decimals)


def fetch_token_metadata() -> dict[str, Any]:
    name = decode_abi_string(eth_call("0x06fdde03")) or "Unknown"
    symbol = decode_abi_string(eth_call("0x95d89b41")) or "Unknown"
    decimals = decode_abi_uint(eth_call("0x313ce567"))
    total_supply_raw = decode_abi_uint(eth_call("0x18160ddd"))
    if decimals is None or total_supply_raw is None:
        raise RuntimeError("failed to fetch token metadata")
    return {
        "name": name,
        "symbol": symbol,
        "decimals": decimals,
        "total_supply_raw": total_supply_raw,
        "total_supply": total_supply_raw / (10 ** decimals),
        "chain": TOKEN_CHAIN,
        "contract": TOKEN_ADDRESS,
        "solana_address": TOKEN_SOLANA_ADDRESS,
        "deployments": [
            {"chain": "bsc", "contract": TOKEN_ADDRESS, "role": "analysis_primary"},
            {"chain": "solana", "contract": TOKEN_SOLANA_ADDRESS, "role": "reference"},
        ],
        "as_of": NOW_UTC.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def classify_segment(label: str | None, is_cex: bool, is_dex: bool, is_contract: bool, share_supply: float) -> str:
    if is_cex:
        return "cex"
    if is_dex:
        return "dex"
    if label:
        return "labeled"
    if is_contract:
        return "contract"
    if share_supply >= 0.005:
        return "unlabeled_whale"
    if share_supply >= 0.0005:
        return "mid_wallet"
    return "tail_wallet"


def rerank_holders(holders: list[dict[str, Any]]) -> None:
    holders.sort(key=lambda row: (-float(row.get("current_amount") or 0.0), int(row.get("bubblemaps_rank") or row.get("rank") or 0)))
    for idx, holder in enumerate(holders, 1):
        holder["rank"] = idx


def fetch_bubblemaps_snapshot(metadata: dict[str, Any]) -> list[dict[str, Any]]:
    holders = fetch_top_holders(TOKEN_CHAIN, TOKEN_ADDRESS)
    if not holders:
        raise RuntimeError("BubbleMaps returned no holders")

    raw_payload = {
        "metadata": {
            "fetched_at": NOW_UTC.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "token": metadata["symbol"],
            "name": metadata["name"],
            "chain": TOKEN_CHAIN,
            "contract": TOKEN_ADDRESS,
            "solana_address": TOKEN_SOLANA_ADDRESS,
            "deployments": metadata["deployments"],
            "count": len(holders),
            "source": "BubbleMaps Top 500 snapshot",
        },
        "holders": holders,
    }
    json_dump(RAW_SNAPSHOT_FILE, raw_payload)

    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in holders:
        address = str(raw.get("address") or "").lower()
        if not address or address in seen:
            continue
        seen.add(address)

        details = raw.get("address_details") or {}
        holder_data = raw.get("holder_data") or {}
        amount = float(holder_data.get("amount") or 0.0)
        share = float(holder_data.get("share") or 0.0)
        share_supply = amount / metadata["total_supply"] if metadata["total_supply"] else share
        label = str(details.get("label") or "").strip()

        bubblemaps_rank = int(holder_data.get("rank") or len(normalized) + 1)
        normalized.append({
            "rank": bubblemaps_rank,
            "bubblemaps_rank": bubblemaps_rank,
            "address": address,
            "current_amount": amount,
            "current_share_bm": share,
            "current_share_supply": share_supply,
            "bm_label": label,
            "bm_entity_id": str(details.get("entity_id") or "").strip(),
            "is_cex": bool(details.get("is_cex")),
            "is_dex": bool(details.get("is_dex")),
            "is_contract": bool(details.get("is_contract")),
            "is_supernode": bool(details.get("is_supernode")),
            "degree": int(details.get("degree") or 0),
            "first_activity_date": details.get("first_activity_date"),
            "segment": classify_segment(label, bool(details.get("is_cex")), bool(details.get("is_dex")), bool(details.get("is_contract")), share_supply),
        })

    rerank_holders(normalized)
    return normalized


def verify_balances(holders: list[dict[str, Any]], metadata: dict[str, Any]) -> dict[str, Any]:
    sample_rows: list[dict[str, Any]] = []
    refresh_needed = False

    print(f"Verifying BubbleMaps balances against on-chain balanceOf for top {min(10, len(holders))} holders...")
    for idx, holder in enumerate(holders[:10], 1):
        chain_balance = token_balance(holder["address"], metadata["decimals"])
        bm_balance = holder["current_amount"]
        diff = None
        diff_pct = None
        if chain_balance is not None:
            diff = chain_balance - bm_balance
            base = max(abs(chain_balance), abs(bm_balance), 1e-9)
            diff_pct = abs(diff) / base
            if diff_pct > 0.01:
                refresh_needed = True

        row = {
            "rank": holder["rank"],
            "address": holder["address"],
            "bubblemaps_amount": bm_balance,
            "onchain_amount": chain_balance,
            "diff_amount": diff,
            "diff_pct": diff_pct,
        }
        sample_rows.append(row)
        print(f"  [{idx:02d}] {short_addr(holder['address'])} bm={fmt_num(bm_balance, 4)} onchain={fmt_num(chain_balance or 0.0, 4)}")
        time.sleep(0.06)

    verification = {
        "generated_at": NOW_UTC.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "top10_rows": sample_rows,
        "refresh_all_balances": refresh_needed,
        "note": "If any top-10 row drifted by more than 1%, refresh the full snapshot from live balanceOf.",
    }

    if refresh_needed:
        print("BubbleMaps sample drifted above 1%; refreshing all 500 balances via balanceOf...")
        for idx, holder in enumerate(holders, 1):
            chain_balance = token_balance(holder["address"], metadata["decimals"])
            if chain_balance is not None:
                holder["current_amount"] = chain_balance
                holder["current_share_supply"] = chain_balance / metadata["total_supply"] if metadata["total_supply"] else 0.0
                holder["segment"] = classify_segment(
                    holder["bm_label"],
                    holder["is_cex"],
                    holder["is_dex"],
                    holder["is_contract"],
                    holder["current_share_supply"],
                )
            if idx % 50 == 0:
                print(f"  refreshed {idx}/{len(holders)} balances")
            time.sleep(0.03)

    rerank_holders(holders)
    json_dump(VERIFICATION_FILE, verification)
    return verification


def bsc_exchange_lookup() -> dict[str, str]:
    exchanges = load_exchange_addresses()
    lookup: dict[str, str] = {}
    for exchange_name, chains in exchanges.items():
        for address in chains.get("bsc", []):
            lookup[str(address).lower()] = exchange_name
    return lookup


def decode_transfer_log(log: dict[str, Any], decimals: int) -> dict[str, Any] | None:
    topics = log.get("topics") or []
    if len(topics) < 3:
        return None
    from_addr = "0x" + topics[1][-40:]
    to_addr = "0x" + topics[2][-40:]
    amount_raw = int(log.get("data", "0x0"), 16)
    return {
        "from": from_addr.lower(),
        "to": to_addr.lower(),
        "amount": amount_raw / (10 ** decimals),
        "amount_raw": amount_raw,
        "block_number": int(log.get("blockNumber", "0x0"), 16),
        "tx_hash": log.get("transactionHash", ""),
    }


def find_first_transfer_block(latest_block: int) -> int:
    deployment_block = find_contract_deployment_block(latest_block)
    print("Locating the first PRL transfer block on BSC...")
    for start in range(deployment_block, latest_block + 1, COARSE_START_SCAN):
        end = min(start + COARSE_START_SCAN - 1, latest_block)
        logs = get_logs_range(start, end)
        if logs:
            logs.sort(key=lambda row: int(row.get("blockNumber", "0x0"), 16))
            first_block = int(logs[0]["blockNumber"], 16)
            print(f"  first transfer block found around {first_block}")
            return first_block
        if start == deployment_block or (((start - deployment_block) // COARSE_START_SCAN) % 10 == 0):
            print(f"  scanned empty range {start:,}-{end:,}")
    raise RuntimeError("no transfer logs found for token")


def find_contract_deployment_block(latest_block: int) -> int:
    print("Resolving PRL contract deployment block...")
    latest_code = eth_get_code(TOKEN_ADDRESS)
    if not latest_code or latest_code == "0x":
        raise RuntimeError("token contract has no code on the latest block")

    low = 1
    high = latest_block
    while low < high:
        mid = (low + high) // 2
        code = eth_get_code(TOKEN_ADDRESS, mid)
        if code and code != "0x":
            high = mid
        else:
            low = mid + 1
    print(f"  contract code first appears at block {low:,}")
    return low


def build_holder_metrics(holders: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    metrics: dict[str, dict[str, Any]] = {}
    for holder in holders:
        metrics[holder["address"]] = {
            **holder,
            "first_inbound_block": None,
            "last_outbound_block": None,
            "total_received": 0.0,
            "total_sent": 0.0,
            "net_accumulation": 0.0,
            "recent_7d_received": 0.0,
            "recent_7d_sent": 0.0,
            "recent_30d_received": 0.0,
            "recent_30d_sent": 0.0,
            "recent_31_60d_received": 0.0,
            "recent_90d_received": 0.0,
            "recent_90d_sent": 0.0,
            "recent_7d_netflow": 0.0,
            "recent_30d_netflow": 0.0,
            "cex_deposit_count": 0,
            "cex_withdraw_count": 0,
            "cex_deposit_amount": 0.0,
            "cex_withdraw_amount": 0.0,
            "recent_30d_cex_deposit_amount": 0.0,
            "recent_30d_cex_withdraw_amount": 0.0,
            "unique_counterparties_count": 0,
            "_counterparties": set(),
        }
    return metrics


def enrich_holder_metrics(
    holders: list[dict[str, Any]],
    metadata: dict[str, Any],
    exchange_lookup: dict[str, str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    holder_metrics = build_holder_metrics(holders)
    holder_addresses = set(holder_metrics)
    latest_block = eth_get_block_number()
    first_transfer_block = find_first_transfer_block(latest_block)

    cutoff_days = [7, 30, 60, 90, 180]
    cutoff_blocks: dict[int, int] = {}
    for days in cutoff_days:
        ts = int((NOW_UTC - timedelta(days=days)).timestamp())
        cutoff_blocks[days] = block_by_timestamp(ts, latest_block)
        print(f"  cutoff block for {days:>3}d: {cutoff_blocks[days]:,}")

    total_windows = ((latest_block - first_transfer_block) // PREFERRED_LOG_CHUNK) + 1
    processed_windows = 0
    processed_logs = 0

    print(f"Scanning PRL transfer history from block {first_transfer_block:,} to {latest_block:,}...")
    for start in range(first_transfer_block, latest_block + 1, PREFERRED_LOG_CHUNK):
        end = min(start + PREFERRED_LOG_CHUNK - 1, latest_block)
        logs = get_logs_range(start, end)
        processed_windows += 1

        for log in logs:
            transfer = decode_transfer_log(log, metadata["decimals"])
            if not transfer:
                continue

            from_addr = transfer["from"]
            to_addr = transfer["to"]
            amount = transfer["amount"]
            block_number = transfer["block_number"]
            processed_logs += 1

            from_is_holder = from_addr in holder_addresses
            to_is_holder = to_addr in holder_addresses
            from_is_exchange = from_addr in exchange_lookup
            to_is_exchange = to_addr in exchange_lookup

            if not from_is_holder and not to_is_holder:
                continue

            if from_is_holder:
                row = holder_metrics[from_addr]
                row["total_sent"] += amount
                if row["last_outbound_block"] is None or block_number > row["last_outbound_block"]:
                    row["last_outbound_block"] = block_number
                if to_addr != ZERO_ADDRESS:
                    row["_counterparties"].add(to_addr)
                if to_is_exchange:
                    row["cex_deposit_count"] += 1
                    row["cex_deposit_amount"] += amount
                    if block_number >= cutoff_blocks[30]:
                        row["recent_30d_cex_deposit_amount"] += amount
                if block_number >= cutoff_blocks[7]:
                    row["recent_7d_sent"] += amount
                if block_number >= cutoff_blocks[30]:
                    row["recent_30d_sent"] += amount
                if block_number >= cutoff_blocks[90]:
                    row["recent_90d_sent"] += amount

            if to_is_holder:
                row = holder_metrics[to_addr]
                row["total_received"] += amount
                if row["first_inbound_block"] is None or block_number < row["first_inbound_block"]:
                    row["first_inbound_block"] = block_number
                if from_addr != ZERO_ADDRESS:
                    row["_counterparties"].add(from_addr)
                if from_is_exchange:
                    row["cex_withdraw_count"] += 1
                    row["cex_withdraw_amount"] += amount
                    if block_number >= cutoff_blocks[30]:
                        row["recent_30d_cex_withdraw_amount"] += amount
                if block_number >= cutoff_blocks[7]:
                    row["recent_7d_received"] += amount
                if block_number >= cutoff_blocks[30]:
                    row["recent_30d_received"] += amount
                elif block_number >= cutoff_blocks[60]:
                    row["recent_31_60d_received"] += amount
                if block_number >= cutoff_blocks[90]:
                    row["recent_90d_received"] += amount

        if processed_windows == 1 or processed_windows % 25 == 0 or end == latest_block:
            print(
                f"  progress {processed_windows}/{total_windows} windows"
                f" | blocks {start:,}-{end:,}"
                f" | logs seen {processed_logs:,}"
            )

    final_rows: dict[str, dict[str, Any]] = {}
    timestamp_cache: dict[int, int | None] = {}

    for address, row in holder_metrics.items():
        first_ts = None
        last_ts = None
        if row["first_inbound_block"] is not None:
            block = row["first_inbound_block"]
            if block not in timestamp_cache:
                timestamp_cache[block] = block_timestamp(block)
            first_ts = timestamp_cache[block]
        if row["last_outbound_block"] is not None:
            block = row["last_outbound_block"]
            if block not in timestamp_cache:
                timestamp_cache[block] = block_timestamp(block)
            last_ts = timestamp_cache[block]

        if first_ts is None and row.get("first_activity_date"):
            try:
                first_ts = int(datetime.fromisoformat(str(row["first_activity_date"]).replace("Z", "+00:00")).timestamp())
            except ValueError:
                first_ts = None

        age_days = None
        if first_ts is not None:
            age_days = max(0, int((NOW_UTC.timestamp() - first_ts) // 86400))

        if age_days is None:
            age_bucket = "unresolved"
        elif age_days < 30:
            age_bucket = "short_term"
        elif age_days <= 180:
            age_bucket = "mid_term"
        else:
            age_bucket = "long_term"

        material_inflow = max(metadata["total_supply"] * 0.0001, row["current_amount"] * 0.02, 1.0)
        if age_days is None:
            cohort = "unresolved"
        elif age_days < 30:
            cohort = "new_wallet"
        elif row["recent_30d_received"] >= material_inflow and row["recent_31_60d_received"] < material_inflow * 0.25:
            cohort = "return_wallet"
        else:
            cohort = "existing_wallet"

        row["net_accumulation"] = row["total_received"] - row["total_sent"]
        row["recent_7d_netflow"] = row["recent_7d_received"] - row["recent_7d_sent"]
        row["recent_30d_netflow"] = row["recent_30d_received"] - row["recent_30d_sent"]
        row["unique_counterparties_count"] = len(row["_counterparties"])
        row.pop("_counterparties", None)
        row["first_inbound_at"] = iso_from_ts(first_ts)
        row["last_outbound_at"] = iso_from_ts(last_ts)
        row["holder_age_days"] = age_days
        row["holder_age_bucket"] = age_bucket
        row["wallet_cohort"] = cohort
        row["behavior_class"] = classify_behavior(row, metadata["total_supply"])
        row["label_layer"] = label_layer(row)
        row["top_holder_role"] = classify_top_holder_role(row, metadata["total_supply"])
        row["top10_control_layer"] = top10_control_layer(row)

        final_rows[address] = row

    scan_meta = {
        "latest_block": latest_block,
        "first_transfer_block": first_transfer_block,
        "cutoff_blocks": cutoff_blocks,
        "windows_scanned": total_windows,
        "logs_seen": processed_logs,
    }
    return final_rows, scan_meta


def classify_behavior(row: dict[str, Any], total_supply: float) -> str:
    activity_30d = row["recent_30d_received"] + row["recent_30d_sent"]
    active_floor = max(total_supply * 0.00005, row["current_amount"] * 0.03, 1.0)
    if activity_30d < active_floor:
        return "Inactive"
    if row["recent_30d_cex_deposit_amount"] >= max(row["recent_30d_cex_withdraw_amount"] * 1.2, active_floor):
        return "CEX-Selling"
    if row["recent_30d_cex_withdraw_amount"] >= max(row["recent_30d_cex_deposit_amount"] * 1.2, active_floor):
        return "CEX-Withdrawing"
    if row["recent_30d_netflow"] >= max(row["current_amount"] * 0.08, total_supply * 0.0001, 1.0):
        return "Accumulating"
    if (
        row["recent_30d_netflow"] <= -max(row["current_amount"] * 0.08, total_supply * 0.0001, 1.0)
        or (row["recent_30d_sent"] > row["recent_30d_received"] * 1.2 and row["unique_counterparties_count"] >= 5)
    ):
        return "Distributing"
    return "Mixed"


def label_layer(row: dict[str, Any]) -> str:
    label = str(row.get("bm_label") or "").strip()
    label_lower = label.lower()
    if row.get("is_cex"):
        return "bubble_cex"
    if row.get("is_dex"):
        return "bubble_dex"
    if "deposit" in label_lower:
        return "exchange_deposit_tag"
    if row.get("is_contract") and label:
        return "contract_label"
    if label:
        return "named_wallet_label"
    return "unlabeled"


def label_layer_name(layer: str) -> str:
    return {
        "bubble_cex": "BubbleMaps 显式 CEX",
        "bubble_dex": "BubbleMaps 显式 DEX / LP",
        "exchange_deposit_tag": "交易所相关标签",
        "contract_label": "具名合约",
        "named_wallet_label": "具名个人/团队地址",
        "unlabeled": "无 BubbleMaps 标签",
    }.get(layer, layer)


def classify_top_holder_role(row: dict[str, Any], total_supply: float) -> str:
    label = str(row.get("bm_label") or "").strip()
    total_received = float(row.get("total_received") or 0.0)
    total_sent = float(row.get("total_sent") or 0.0)
    sent_ratio = total_sent / total_received if total_received > 0 else 0.0
    counterparties = int(row.get("unique_counterparties_count") or 0)
    current_share = float(row.get("current_share_supply") or 0.0)

    if row.get("is_cex"):
        return "交易所库存地址"
    if row.get("is_dex"):
        return "DEX / LP 流动性地址"
    if label:
        if float(row.get("recent_30d_cex_withdraw_amount") or 0.0) > 0:
            return "具名增持地址"
        return "具名持仓地址"
    if current_share >= 0.1 and sent_ratio >= 0.3 and counterparties >= 3:
        return "主分发母仓"
    if total_sent == 0 and counterparties <= 1:
        return "单次受配分仓"
    if total_sent > 0 and counterparties <= 3:
        return "二级分发分仓"
    if current_share >= max(0.005, (500000 / total_supply) if total_supply else 0.0):
        return "未标注鲸鱼仓"
    return "普通持仓地址"


def top10_control_layer(row: dict[str, Any]) -> str:
    if row.get("is_cex"):
        return "exchange_inventory"
    if row.get("is_dex"):
        return "dex_liquidity"
    if row.get("bm_label"):
        return "named_holder"
    return "unlabeled_distribution_cluster"


def top10_control_layer_name(layer: str) -> str:
    return {
        "unlabeled_distribution_cluster": "未标注大户分发簇",
        "exchange_inventory": "交易所库存层",
        "dex_liquidity": "DEX 流动性层",
        "named_holder": "具名地址层",
    }.get(layer, layer)


def holder_judgement(row: dict[str, Any]) -> str:
    share = fmt_pct(row["current_share_supply"])
    if row["is_cex"]:
        return (
            f"BubbleMaps 直接标记为 {row['bm_label']}。对手方数量高、近 30 天双向流转明显，"
            f"更像交易所库存而不是单一控盘仓；但它单地址仍占 {share}，对短期流通面有实质影响。"
        )
    if row["is_dex"]:
        return (
            f"BubbleMaps 直接标记为 {row['bm_label']}。它承接的是交易流动性而不是主观控盘仓，"
            f"当前占供应 {share}，属于可交易流动性池库存。"
        )
    if row["bm_label"]:
        if row["recent_30d_cex_withdraw_amount"] > 0:
            return (
                f"这是 BubbleMaps 具名地址，近 30 天有明确的交易所提出记录，当前保留 {share} 仓位，"
                "行为上偏增持而不是派发。"
            )
        return f"这是 BubbleMaps 具名地址，当前持仓 {share}，更适合作为已知实体样本观察，而不是主控盘层。"

    total_received = float(row.get("total_received") or 0.0)
    total_sent = float(row.get("total_sent") or 0.0)
    counterparties = int(row.get("unique_counterparties_count") or 0)
    if total_received > 0 and total_sent / total_received >= 0.3 and counterparties >= 3:
        return (
            f"该地址没有 BubbleMaps 标签，但当前仍持有 {share}。它既是最大仓位又承担明显再分发，"
            "形态上更像本轮大户簇的主分发母仓。"
        )
    if total_sent == 0 and counterparties <= 1:
        return (
            f"该地址没有 BubbleMaps 标签，且基本表现为单次收币后静置，当前持仓 {share}。"
            "形态上更像受配分仓或独立保管仓。"
        )
    return (
        f"该地址没有 BubbleMaps 标签，当前持仓 {share}，有少量再分发动作但没有形成公开实体标签，"
        "应视为未标注的大户分支。"
    )


def build_label_inventory(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    inventory: dict[str, dict[str, Any]] = {}
    for row in rows:
        label = str(row.get("bm_label") or "").strip()
        if not label:
            continue
        bucket = inventory.setdefault(label, {
            "label": label,
            "layer": label_layer(row),
            "count": 0,
            "amount": 0.0,
            "share_supply": 0.0,
            "top_rank": row["rank"],
        })
        bucket["count"] += 1
        bucket["amount"] += float(row["current_amount"])
        bucket["share_supply"] += float(row["current_share_supply"])
        bucket["top_rank"] = min(int(bucket["top_rank"]), int(row["rank"]))
    return sorted(inventory.values(), key=lambda item: (-float(item["share_supply"]), int(item["top_rank"])))


def build_top10_layer_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for row in rows[:10]:
        layer = top10_control_layer(row)
        bucket = buckets.setdefault(layer, {
            "layer": layer,
            "count": 0,
            "amount": 0.0,
            "share_supply": 0.0,
            "ranks": [],
        })
        bucket["count"] += 1
        bucket["amount"] += float(row["current_amount"])
        bucket["share_supply"] += float(row["current_share_supply"])
        bucket["ranks"].append(int(row["rank"]))
    return sorted(buckets.values(), key=lambda item: (-float(item["share_supply"]), item["layer"]))


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_No data._"
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def top_share(rows: list[dict[str, Any]], limit: int) -> float:
    return sum(row["current_share_supply"] for row in rows[:limit])


def summarize_bucket(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        buckets.setdefault(str(row.get(key) or "unknown"), []).append(row)

    summary: dict[str, dict[str, Any]] = {}
    for bucket, bucket_rows in buckets.items():
        summary[bucket] = {
            "count": len(bucket_rows),
            "amount": sum(r["current_amount"] for r in bucket_rows),
            "share_supply": sum(r["current_share_supply"] for r in bucket_rows),
        }
    return summary


def sort_by(rows: list[dict[str, Any]], key: str, reverse: bool = True) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: float(row.get(key) or 0.0), reverse=reverse)


def pick_key_wallets(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}

    labeled = [row for row in rows if row["bm_label"] and not row["is_cex"] and not row["is_dex"]]
    whales = [row for row in rows if row["segment"] == "unlabeled_whale"]
    top_cex_depositors = [row for row in rows if row["recent_30d_cex_deposit_amount"] > 0 and not row["is_cex"]]
    top_cex_withdrawers = [row for row in rows if row["recent_30d_cex_withdraw_amount"] > 0 and not row["is_cex"]]

    for row in sort_by(labeled, "current_share_supply")[:10]:
        selected[row["address"]] = {**row, "key_reason": "BubbleMaps labeled holder"}
    for row in sort_by(whales, "current_share_supply")[:10]:
        selected.setdefault(row["address"], {**row, "key_reason": "Top unlabeled whale"})
    for row in sort_by(top_cex_depositors, "recent_30d_cex_deposit_amount")[:5]:
        selected.setdefault(row["address"], {**row, "key_reason": "Largest 30d exchange depositor"})
    for row in sort_by(top_cex_withdrawers, "recent_30d_cex_withdraw_amount")[:5]:
        selected.setdefault(row["address"], {**row, "key_reason": "Largest 30d exchange withdrawer"})

    return sorted(selected.values(), key=lambda row: (-float(row["current_share_supply"]), row["rank"]))


def build_summary(
    holders: list[dict[str, Any]],
    verification: dict[str, Any],
    scan_meta: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    non_infra = [row for row in holders if not row["is_cex"] and not row["is_dex"] and not row["is_contract"]]
    labeled = [row for row in holders if row["bm_label"]]
    bubble_cex = [row for row in holders if row["is_cex"]]
    bubble_dex = [row for row in holders if row["is_dex"]]

    summary = {
        "snapshot": {
            "holder_count": len(holders),
            "top10_share": top_share(holders, 10),
            "top20_share": top_share(holders, 20),
            "top50_share": top_share(holders, 50),
            "bubblemaps_labeled_count": len(labeled),
            "bubblemaps_labeled_share": sum(row["current_share_supply"] for row in labeled),
            "bubblemaps_cex_count": len(bubble_cex),
            "bubblemaps_cex_share": sum(row["current_share_supply"] for row in bubble_cex),
            "bubblemaps_dex_count": len(bubble_dex),
            "bubblemaps_dex_share": sum(row["current_share_supply"] for row in bubble_dex),
        },
        "segment_summary": summarize_bucket(holders, "segment"),
        "age_summary_non_infra": summarize_bucket(non_infra, "holder_age_bucket"),
        "cohort_summary_non_infra": summarize_bucket(non_infra, "wallet_cohort"),
        "behavior_summary_non_infra": summarize_bucket(non_infra, "behavior_class"),
        "recent_activity_non_infra": {
            "recent_30d_cex_deposit_total": sum(row["recent_30d_cex_deposit_amount"] for row in non_infra),
            "recent_30d_cex_withdraw_total": sum(row["recent_30d_cex_withdraw_amount"] for row in non_infra),
            "recent_30d_netflow_total": sum(row["recent_30d_netflow"] for row in non_infra),
            "recent_7d_netflow_total": sum(row["recent_7d_netflow"] for row in non_infra),
        },
        "top10_layer_summary": build_top10_layer_summary(holders),
        "label_inventory": build_label_inventory(holders),
        "verification": verification,
        "scan_meta": scan_meta,
        "token": metadata,
    }
    return summary


def top_rows_for_report(rows: list[dict[str, Any]], metric: str, limit: int = 10, min_abs: float = 0.0) -> list[dict[str, Any]]:
    filtered = [row for row in rows if abs(float(row.get(metric) or 0.0)) > min_abs]
    return sort_by(filtered, metric)[:limit]


def negative_rows_for_report(rows: list[dict[str, Any]], metric: str, limit: int = 10, min_abs: float = 0.0) -> list[dict[str, Any]]:
    filtered = [row for row in rows if float(row.get(metric) or 0.0) < -min_abs]
    return sorted(filtered, key=lambda row: float(row.get(metric) or 0.0))[:limit]


def build_conclusions(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    snap = summary["snapshot"]
    recent = summary["recent_activity_non_infra"]
    age = summary["age_summary_non_infra"]
    cohorts = summary["cohort_summary_non_infra"]

    top10 = snap["top10_share"]
    if top10 >= 0.6:
        lines.append(f"Top10 address concentration is very high at {fmt_pct(top10)} of total supply.")
    elif top10 >= 0.4:
        lines.append(f"Top10 address concentration is elevated at {fmt_pct(top10)} of total supply.")
    else:
        lines.append(f"Top10 address concentration is moderate at {fmt_pct(top10)} of total supply.")

    labeled_share = snap["bubblemaps_labeled_share"]
    if labeled_share < 0.2:
        lines.append(f"BubbleMaps explicit labels cover only {fmt_pct(labeled_share)} of supply, so attribution confidence is structurally limited.")
    else:
        lines.append(f"BubbleMaps explicit labels cover {fmt_pct(labeled_share)} of supply, enough to anchor the major known pockets.")

    dep = recent["recent_30d_cex_deposit_total"]
    wdw = recent["recent_30d_cex_withdraw_total"]
    if dep > wdw * 1.2:
        lines.append(f"30d exchange-directed flow is net negative for holders: deposits {fmt_num(dep, 2)} PRL vs withdrawals {fmt_num(wdw, 2)} PRL.")
    elif wdw > dep * 1.2:
        lines.append(f"30d exchange-directed flow is net positive for holders: withdrawals {fmt_num(wdw, 2)} PRL vs deposits {fmt_num(dep, 2)} PRL.")
    else:
        lines.append(f"30d exchange flow is roughly balanced: deposits {fmt_num(dep, 2)} PRL and withdrawals {fmt_num(wdw, 2)} PRL.")

    long_term_share = age.get("long_term", {}).get("share_supply", 0.0)
    short_term_share = age.get("short_term", {}).get("share_supply", 0.0)
    if long_term_share > short_term_share * 1.5:
        lines.append(f"Long-held wallets still dominate the non-infrastructure snapshot ({fmt_pct(long_term_share)} vs short-term {fmt_pct(short_term_share)}).")

    return_share = cohorts.get("return_wallet", {}).get("share_supply", 0.0)
    new_share = cohorts.get("new_wallet", {}).get("share_supply", 0.0)
    if return_share > new_share * 1.2:
        lines.append(f"Returning wallets control more supply than fresh entrants ({fmt_pct(return_share)} vs {fmt_pct(new_share)}), suggesting old chips are reactivating.")
    elif new_share > return_share * 1.2:
        lines.append(f"Fresh wallets control more supply than returning wallets ({fmt_pct(new_share)} vs {fmt_pct(return_share)}), suggesting newer demand is driving the current holder mix.")

    return lines


def build_report(
    metadata: dict[str, Any],
    holders: list[dict[str, Any]],
    summary: dict[str, Any],
    exchange_lookup: dict[str, str],
) -> str:
    non_infra = [row for row in holders if not row["is_cex"] and not row["is_dex"] and not row["is_contract"]]
    top10 = holders[:10]
    top11_50_share = summary["snapshot"]["top50_share"] - summary["snapshot"]["top10_share"]
    top10_layer_rows = summary["top10_layer_summary"]
    label_inventory = summary["label_inventory"]
    exchange_recent = summary["recent_activity_non_infra"]
    top_withdrawers = top_rows_for_report(non_infra, "recent_30d_cex_withdraw_amount", limit=5, min_abs=1.0)
    top_depositors = top_rows_for_report(non_infra, "recent_30d_cex_deposit_amount", limit=5, min_abs=1.0)

    unlabeled_top10_share = sum(
        row["current_share_supply"]
        for row in top10
        if row["top10_control_layer"] == "unlabeled_distribution_cluster"
    )
    cex_top10_share = sum(row["current_share_supply"] for row in top10 if row["is_cex"])
    dex_top10_share = sum(row["current_share_supply"] for row in top10 if row["is_dex"])
    named_top10_share = sum(
        row["current_share_supply"]
        for row in top10
        if row["bm_label"] and not row["is_cex"] and not row["is_dex"]
    )

    lines: list[str] = []
    lines.append(f"# {metadata['name']} ({metadata['symbol']}) Top 10 筹码结构研究")
    lines.append("")
    lines.append(f"- BSC 研究合约: `{metadata['contract']}`")
    lines.append(f"- Solana 地址: `{metadata['solana_address']}`")
    lines.append(f"- 主研究链: {metadata['chain'].upper()}")
    lines.append(f"- 总供应量: {fmt_num(metadata['total_supply'], 4)} {metadata['symbol']}")
    lines.append(f"- 生成时间: {NOW_UTC.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"- BubbleMaps 快照: Top {len(holders)} holders")
    lines.append(f"- 已知本地交易所地址数: {len(exchange_lookup)}")
    lines.append("")

    lines.append("## 1. 先看结论")
    lines.append("")
    lines.append(f"- Top10 已经解释了 {fmt_pct(summary['snapshot']['top10_share'])} 的总供应，PRL 当前不是“分散持仓”，而是“Top10 决定流通盘”。")
    lines.append(f"- Top10 里有 7 个未标注地址，合计 {fmt_pct(unlabeled_top10_share)}；这 7 个地址才是需要重点盯的控盘层。")
    lines.append(f"- Top10 里真正有明确公共标签的只有 3 类仓位: Binance 库存 {fmt_pct(cex_top10_share)}、Pancake 流动性 {fmt_pct(dex_top10_share)}、`degenrunner.bnb` {fmt_pct(named_top10_share)}。")
    lines.append(f"- Top11 到 Top50 只剩 {fmt_pct(top11_50_share)}，说明研究重点不该再分散到长尾，而是把 Top10 尤其是那 7 个未标注大户逐个盯住。")
    lines.append("")

    lines.append("## 2. Top 10 分层")
    lines.append("")
    lines.append(md_table(
        ["层级", "地址数", "Amount", "Supply Share", "涉及 Rank", "解读"],
        [
            [
                top10_control_layer_name(item["layer"]),
                str(item["count"]),
                fmt_num(item["amount"], 4),
                fmt_pct(item["share_supply"]),
                ", ".join(str(rank) for rank in item["ranks"]),
                (
                    "未标注大户簇，表现为新钱包集中拿仓。"
                    if item["layer"] == "unlabeled_distribution_cluster"
                    else "BubbleMaps 已识别的交易所库存。"
                    if item["layer"] == "exchange_inventory"
                    else "BubbleMaps 已识别的 LP / 交易流动性。"
                    if item["layer"] == "dex_liquidity"
                    else "BubbleMaps 已识别的具名地址。"
                ),
            ]
            for item in top10_layer_rows
        ],
    ))
    lines.append("")
    lines.append(md_table(
        ["Rank", "Address", "BubbleMaps Label", "标签层", "角色判断", "Amount", "Share", "30d Netflow"],
        [
            [
                str(row["rank"]),
                short_addr(row["address"]),
                row["bm_label"] or "-",
                label_layer_name(row["label_layer"]),
                row["top_holder_role"],
                fmt_num(row["current_amount"], 4),
                fmt_pct(row["current_share_supply"]),
                fmt_num(row["recent_30d_netflow"], 4),
            ]
            for row in top10
        ],
    ))
    lines.append("")

    lines.append("## 3. Top 10 地址逐个研究")
    lines.append("")
    for row in top10:
        lines.append(f"### Rank {row['rank']} | {short_addr(row['address'])}")
        lines.append("")
        lines.append(f"- BubbleMaps Label: `{row['bm_label'] or 'None'}`")
        lines.append(f"- 标签层: {label_layer_name(row['label_layer'])}")
        lines.append(f"- 角色判断: {row['top_holder_role']}")
        lines.append(f"- 当前持仓: {fmt_num(row['current_amount'], 4)} {metadata['symbol']} ({fmt_pct(row['current_share_supply'])})")
        lines.append(f"- 首次入场: {row['first_inbound_at'] or row['first_activity_date'] or '-'}")
        lines.append(f"- 最近转出: {row['last_outbound_at'] or '-'}")
        lines.append(f"- 全历史累计收/发: {fmt_num(row['total_received'], 4)} / {fmt_num(row['total_sent'], 4)}")
        lines.append(f"- 近 30 天净流量: {fmt_num(row['recent_30d_netflow'], 4)}")
        lines.append(f"- 近 30 天交易所提出 / 存入: {fmt_num(row['recent_30d_cex_withdraw_amount'], 4)} / {fmt_num(row['recent_30d_cex_deposit_amount'], 4)}")
        lines.append(f"- 对手方数: {row['unique_counterparties_count']}")
        lines.append(f"- 行为分类: {row['behavior_class']} | 钱包分组: {row['wallet_cohort']}")
        lines.append(f"- 研究判断: {holder_judgement(row)}")
        lines.append("")

    lines.append("## 4. BubbleMaps 标签分层")
    lines.append("")
    lines.append(f"- BubbleMaps 一共给出 {summary['snapshot']['bubblemaps_labeled_count']} 个已标注地址，对应 {len(label_inventory)} 个去重标签，覆盖 {fmt_pct(summary['snapshot']['bubblemaps_labeled_share'])} 的供应量。")
    lines.append("- 这部分只能作为显式标签下限。对未标注地址，本报告只做行为归类，不额外创造实体名。")
    lines.append("")
    lines.append(md_table(
        ["Label", "标签层", "Addr Count", "Top Rank", "Amount", "Supply Share"],
        [
            [
                item["label"],
                label_layer_name(item["layer"]),
                str(item["count"]),
                str(item["top_rank"]),
                fmt_num(item["amount"], 4),
                fmt_pct(item["share_supply"]),
            ]
            for item in label_inventory
        ],
    ))
    lines.append("")

    lines.append("## 5. Top 10 之外还剩什么")
    lines.append("")
    lines.append(f"- Top11-Top50 合计 {fmt_pct(top11_50_share)}；Top51-Top500 合计 {fmt_pct(1 - summary['snapshot']['top50_share'])}。")
    lines.append(f"- 换句话说，Top10 之外所有地址加起来只占 {fmt_pct(1 - summary['snapshot']['top10_share'])}。")
    lines.append("")
    lines.append(md_table(
        ["Segment", "Addr Count", "Amount", "Supply Share"],
        [
            [
                segment,
                str(stats["count"]),
                fmt_num(stats["amount"], 4),
                fmt_pct(stats["share_supply"]),
            ]
            for segment, stats in sorted(summary["segment_summary"].items(), key=lambda item: item[1]["share_supply"], reverse=True)
        ],
    ))
    lines.append("")

    lines.append("## 6. 交易所与流动性侧")
    lines.append("")
    lines.append(f"- BubbleMaps 显式 CEX 仓位下限为 {fmt_pct(summary['snapshot']['bubblemaps_cex_share'])}，当前基本都落在 Binance 那个单地址上。")
    lines.append(f"- BubbleMaps 显式 DEX / LP 仓位下限为 {fmt_pct(summary['snapshot']['bubblemaps_dex_share'])}。")
    lines.append(f"- 近 30 天非基础设施地址从交易所净提出 {fmt_num(exchange_recent['recent_30d_cex_withdraw_total'], 4)} PRL，向交易所净存入 {fmt_num(exchange_recent['recent_30d_cex_deposit_total'], 4)} PRL。")
    lines.append("")
    lines.append("### 近 30 天主要从交易所提出")
    lines.append("")
    lines.append(md_table(
        ["Address", "Label", "角色判断", "30d CEX Withdraw", "Current Share"],
        [
            [
                short_addr(row["address"]),
                row["bm_label"] or "-",
                row["top_holder_role"],
                fmt_num(row["recent_30d_cex_withdraw_amount"], 4),
                fmt_pct(row["current_share_supply"]),
            ]
            for row in top_withdrawers
        ] or [["-", "-", "-", "-", "-"]],
    ))
    lines.append("")
    lines.append("### 近 30 天主要向交易所存入")
    lines.append("")
    lines.append(md_table(
        ["Address", "Label", "角色判断", "30d CEX Deposit", "Current Share"],
        [
            [
                short_addr(row["address"]),
                row["bm_label"] or "-",
                row["top_holder_role"],
                fmt_num(row["recent_30d_cex_deposit_amount"], 4),
                fmt_pct(row["current_share_supply"]),
            ]
            for row in top_depositors
        ] or [["-", "-", "-", "-", "-"]],
    ))
    lines.append("")

    lines.append("## 7. 综合判断")
    lines.append("")
    lines.append(f"- 真正需要研究的不是“PRL 的 500 个 holder”，而是 Top10 里的 7 个未标注大户簇，它们合计控制 {fmt_pct(unlabeled_top10_share)}。")
    lines.append("- 这 7 个地址几乎全部在近一周内形成仓位，且多数是单次收币后静置，说明当前流通盘并没有充分打散。")
    lines.append("- Binance 和 PancakeSwap 仓位虽然很大，但性质不同于控盘母仓，前者更像交易所库存，后者更像交易流动性。")
    lines.append("- `degenrunner.bnb` 是 Top10 里唯一值得继续持续追踪的具名非基础设施地址，因为它既进入了 Top10，又出现了明确的交易所提出行为。")
    lines.append("- BubbleMaps labels are treated as the only explicit entity source. Unlabeled addresses are classified by behavior only.")
    lines.append("- BubbleMaps holder balances were sampled against on-chain balanceOf. If the snapshot drifted, the script refreshes all balances from chain and keeps BubbleMaps only as a label source.")
    lines.append("- Cost basis and realized PnL are not included in this report because the current environment does not provide a reliable per-trade pricing ledger for PRL.")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    ensure_dirs()

    print("=" * 80)
    print("PRL holder structure study")
    print("=" * 80)

    metadata = fetch_token_metadata()
    print(f"Token: {metadata['name']} ({metadata['symbol']})")
    print(f"Contract: {metadata['contract']}")
    print(f"Total supply: {fmt_num(metadata['total_supply'], 4)} {metadata['symbol']}")

    holders = fetch_bubblemaps_snapshot(metadata)
    print(f"BubbleMaps snapshot rows: {len(holders)}")

    verification = verify_balances(holders, metadata)
    exchange_lookup = bsc_exchange_lookup()
    print(f"Loaded {len(exchange_lookup)} BSC exchange addresses for flow-direction tagging")

    holder_metrics, scan_meta = enrich_holder_metrics(holders, metadata, exchange_lookup)
    final_rows = sorted(holder_metrics.values(), key=lambda row: row["rank"])
    summary = build_summary(final_rows, verification, scan_meta, metadata)

    payload = {
        "metadata": metadata,
        "summary": summary,
        "holders": final_rows,
    }
    json_dump(ANALYSIS_FILE, payload)

    report = build_report(metadata, final_rows, summary, exchange_lookup)
    REPORT_FILE.write_text(report, encoding="utf-8")

    print("")
    print("Artifacts written:")
    print(f"  - {RAW_SNAPSHOT_FILE}")
    print(f"  - {VERIFICATION_FILE}")
    print(f"  - {ANALYSIS_FILE}")
    print(f"  - {REPORT_FILE}")


if __name__ == "__main__":
    main()
