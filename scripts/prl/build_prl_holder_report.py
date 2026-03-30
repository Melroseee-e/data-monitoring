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
    key_wallets = pick_key_wallets(non_infra)
    top_accumulators = top_rows_for_report(non_infra, "recent_30d_netflow", limit=8, min_abs=1.0)
    top_distributors = negative_rows_for_report(non_infra, "recent_30d_netflow", limit=8, min_abs=1.0)
    top_depositors = top_rows_for_report(non_infra, "recent_30d_cex_deposit_amount", limit=8, min_abs=1.0)
    top_withdrawers = top_rows_for_report(non_infra, "recent_30d_cex_withdraw_amount", limit=8, min_abs=1.0)
    bubble_cex = [row for row in holders if row["is_cex"]]
    top20 = holders[:20]

    lines: list[str] = []
    lines.append(f"# {metadata['name']} ({metadata['symbol']}) 筹码结构研究")
    lines.append("")
    lines.append(f"- 合约: `{metadata['contract']}`")
    lines.append(f"- 链: {metadata['chain'].upper()}")
    lines.append(f"- 总供应量: {fmt_num(metadata['total_supply'], 4)} {metadata['symbol']}")
    lines.append(f"- 生成时间: {NOW_UTC.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"- BubbleMaps 快照: Top {len(holders)} holders")
    lines.append(f"- 已知本地交易所地址数: {len(exchange_lookup)}")
    lines.append("")

    lines.append("## 1. 当前筹码结构")
    lines.append("")
    lines.append(f"- Top10 / Top20 / Top50 持仓占比分别为 {fmt_pct(summary['snapshot']['top10_share'])} / {fmt_pct(summary['snapshot']['top20_share'])} / {fmt_pct(summary['snapshot']['top50_share'])}。")
    lines.append(f"- BubbleMaps 显式标签覆盖 {summary['snapshot']['bubblemaps_labeled_count']} 个地址，合计 {fmt_pct(summary['snapshot']['bubblemaps_labeled_share'])} 的总供应。")
    lines.append(f"- BubbleMaps 显式 CEX 仅识别到 {summary['snapshot']['bubblemaps_cex_count']} 个地址，当前合计 {fmt_pct(summary['snapshot']['bubblemaps_cex_share'])} 的总供应。这一数值按下限理解。")
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
            for segment, stats in sorted(
                summary["segment_summary"].items(),
                key=lambda item: item[1]["share_supply"],
                reverse=True,
            )
        ],
    ))
    lines.append("")
    lines.append("### Top 20 持仓快照")
    lines.append("")
    lines.append(md_table(
        ["Rank", "Address", "BubbleMaps Label", "Segment", "Amount", "Share"],
        [
            [
                str(row["rank"]),
                short_addr(row["address"]),
                row["bm_label"] or "-",
                row["segment"],
                fmt_num(row["current_amount"], 4),
                fmt_pct(row["current_share_supply"]),
            ]
            for row in top20
        ],
    ))
    lines.append("")

    lines.append("## 2. 持仓年龄与回流/新进")
    lines.append("")
    lines.append("- 该部分仅统计非基础设施地址，即排除 BubbleMaps 标记的 CEX / DEX / contract。")
    lines.append("- `new_wallet`: 首次入场 < 30 天。")
    lines.append("- `return_wallet`: 首次入场 >= 30 天，近 30 天重新净流入，且 31-60 天窗口未出现同等级增持。")
    lines.append("")
    lines.append(md_table(
        ["Age Bucket", "Addr Count", "Amount", "Supply Share"],
        [
            [bucket, str(stats["count"]), fmt_num(stats["amount"], 4), fmt_pct(stats["share_supply"])]
            for bucket, stats in sorted(
                summary["age_summary_non_infra"].items(),
                key=lambda item: item[1]["share_supply"],
                reverse=True,
            )
        ],
    ))
    lines.append("")
    lines.append(md_table(
        ["Cohort", "Addr Count", "Amount", "Supply Share"],
        [
            [bucket, str(stats["count"]), fmt_num(stats["amount"], 4), fmt_pct(stats["share_supply"])]
            for bucket, stats in sorted(
                summary["cohort_summary_non_infra"].items(),
                key=lambda item: item[1]["share_supply"],
                reverse=True,
            )
        ],
    ))
    lines.append("")

    lines.append("## 3. CEX 相关筹码")
    lines.append("")
    lines.append("- 显式持仓只展示 BubbleMaps 直接标注为 CEX 的地址。")
    lines.append("- 交易所方向识别使用本地 exchange registry，只用于判断 `向交易所 / 从交易所` 流向，不用于给无标签地址命名。")
    lines.append("")
    lines.append("### BubbleMaps 显式 CEX 持仓")
    lines.append("")
    lines.append(md_table(
        ["Rank", "Address", "Label", "Amount", "Share"],
        [
            [
                str(row["rank"]),
                short_addr(row["address"]),
                row["bm_label"] or row["bm_entity_id"] or "-",
                fmt_num(row["current_amount"], 4),
                fmt_pct(row["current_share_supply"]),
            ]
            for row in bubble_cex
        ] or [["-", "-", "-", "-", "-"]],
    ))
    lines.append("")
    lines.append("### 近 30 天主要向交易所存入")
    lines.append("")
    lines.append(md_table(
        ["Address", "Label", "30d CEX Deposit", "Behavior", "Current Share"],
        [
            [
                short_addr(row["address"]),
                row["bm_label"] or "-",
                fmt_num(row["recent_30d_cex_deposit_amount"], 4),
                row["behavior_class"],
                fmt_pct(row["current_share_supply"]),
            ]
            for row in top_depositors
        ] or [["-", "-", "-", "-", "-"]],
    ))
    lines.append("")
    lines.append("### 近 30 天主要从交易所提出")
    lines.append("")
    lines.append(md_table(
        ["Address", "Label", "30d CEX Withdraw", "Behavior", "Current Share"],
        [
            [
                short_addr(row["address"]),
                row["bm_label"] or "-",
                fmt_num(row["recent_30d_cex_withdraw_amount"], 4),
                row["behavior_class"],
                fmt_pct(row["current_share_supply"]),
            ]
            for row in top_withdrawers
        ] or [["-", "-", "-", "-", "-"]],
    ))
    lines.append("")

    lines.append("## 4. 关键钱包")
    lines.append("")
    lines.append(md_table(
        ["Address", "Reason", "Label", "Behavior", "30d Netflow", "Current Share"],
        [
            [
                short_addr(row["address"]),
                row["key_reason"],
                row["bm_label"] or "-",
                row["behavior_class"],
                fmt_num(row["recent_30d_netflow"], 4),
                fmt_pct(row["current_share_supply"]),
            ]
            for row in key_wallets[:20]
        ],
    ))
    lines.append("")

    lines.append("## 5. 近期活动")
    lines.append("")
    lines.append(f"- 非基础设施地址 30d 净流量合计: {fmt_num(summary['recent_activity_non_infra']['recent_30d_netflow_total'], 4)} {metadata['symbol']}")
    lines.append(f"- 非基础设施地址 7d 净流量合计: {fmt_num(summary['recent_activity_non_infra']['recent_7d_netflow_total'], 4)} {metadata['symbol']}")
    lines.append("")
    lines.append("### 近 30 天主要增持")
    lines.append("")
    lines.append(md_table(
        ["Address", "Label", "30d Netflow", "7d Netflow", "Cohort", "Behavior"],
        [
            [
                short_addr(row["address"]),
                row["bm_label"] or "-",
                fmt_num(row["recent_30d_netflow"], 4),
                fmt_num(row["recent_7d_netflow"], 4),
                row["wallet_cohort"],
                row["behavior_class"],
            ]
            for row in top_accumulators
        ] or [["-", "-", "-", "-", "-", "-"]],
    ))
    lines.append("")
    lines.append("### 近 30 天主要减持")
    lines.append("")
    lines.append(md_table(
        ["Address", "Label", "30d Netflow", "7d Netflow", "Cohort", "Behavior"],
        [
            [
                short_addr(row["address"]),
                row["bm_label"] or "-",
                fmt_num(row["recent_30d_netflow"], 4),
                fmt_num(row["recent_7d_netflow"], 4),
                row["wallet_cohort"],
                row["behavior_class"],
            ]
            for row in top_distributors
        ] or [["-", "-", "-", "-", "-", "-"]],
    ))
    lines.append("")

    lines.append("## 6. 综合判断与风险")
    lines.append("")
    for bullet in build_conclusions(summary):
        lines.append(f"- {bullet}")
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
