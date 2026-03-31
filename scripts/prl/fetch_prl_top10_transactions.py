#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
SKILLS_DIR = BASE_DIR / ".claude" / "skills" / "onchain-analysis" / "scripts"
import sys
sys.path.insert(0, str(SKILLS_DIR))

load_dotenv(BASE_DIR / ".env", override=False)

from core.helius import helius_http_get, resolve_helius_api_keys

ANALYSIS_PATH = BASE_DIR / "data" / "prl" / "derived" / "prl_holder_analysis.json"
RAW_DIR = BASE_DIR / "data" / "prl" / "raw" / "top10_helius_history"
DERIVED_PATH = BASE_DIR / "data" / "prl" / "derived" / "prl_top10_transaction_summary.json"

PRL_MINT = "PERLEQKUNUp1dgFZ8EvyXHdN9d6ZQqfGxALDvfs6pDs"
TOP_INVESTOR_ALLOCATION = 276_600_000.0
COMMUNITY_LOCKED_POST_TGE = 300_000_000.0
ECOSYSTEM_LOCKED_POST_TGE = 78_400_000.0
SYSTEM_PROGRAM = "11111111111111111111111111111111"


def log(message: str) -> None:
    stamp = datetime.now(tz=timezone.utc).strftime("%H:%M:%S")
    print(f"[{stamp}] {message}", flush=True)


def iso_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_float(value: Any) -> float:
    if value in (None, "", "null"):
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def fmt_num(value: float) -> str:
    return f"{value:,.2f}"


def short_addr(address: str) -> str:
    return f"{address[:6]}...{address[-4:]}" if len(address) > 12 else address


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_analysis() -> dict[str, Any]:
    return json.loads(ANALYSIS_PATH.read_text(encoding="utf-8"))


def load_keys() -> list[str]:
    keys = resolve_helius_api_keys()
    if not keys:
        raise RuntimeError("No Helius keys found")
    return keys


class HeliusRotator:
    def __init__(self, keys: list[str]) -> None:
        self.keys = keys
        self.cursor = 0
        self.usage = Counter()

    def fetch_page(self, address: str, *, before: str | None, limit: int) -> list[dict[str, Any]]:
        key = self.keys[self.cursor]
        self.cursor = (self.cursor + 1) % len(self.keys)
        url = f"https://api.helius.xyz/v0/addresses/{address}/transactions"
        params: dict[str, Any] = {"api-key": key, "limit": limit}
        if before:
            params["before"] = before
        data = helius_http_get(
            url,
            params=params,
            timeout=30,
            max_retries_per_key=4,
            preferred_key=key,
        )
        self.usage[key[-6:]] += 1
        if not isinstance(data, list):
            raise RuntimeError(f"unexpected payload {type(data).__name__}")
        return data


def parse_first_activity(value: str | None) -> int:
    if not value:
        return 0
    cleaned = value.replace("Z", "+00:00")
    return int(datetime.fromisoformat(cleaned).timestamp()) - 86400


def fetch_history(rotator: HeliusRotator, address: str, *, min_timestamp: int, page_limit: int = 100, max_pages: int = 120) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    before: str | None = None
    out: list[dict[str, Any]] = []
    oldest_seen: int | None = None
    page = 0
    for page in range(1, max_pages + 1):
        items = rotator.fetch_page(address, before=before, limit=page_limit)
        if not items:
            break
        out.extend(items)
        page_oldest = min(int(item.get("timestamp", 0) or 0) for item in items)
        oldest_seen = page_oldest if oldest_seen is None else min(oldest_seen, page_oldest)
        before = items[-1].get("signature")
        if not before:
            break
        if page_oldest and page_oldest < min_timestamp:
            break
        time.sleep(0.04)
    filtered = [item for item in out if int(item.get("timestamp", 0) or 0) >= min_timestamp]
    return filtered, {
        "pages_fetched": page,
        "oldest_seen_ts": oldest_seen,
        "total_before_filter": len(out),
        "total_after_filter": len(filtered),
    }


def extract_prl_transfers(address: str, tx: dict[str, Any]) -> list[dict[str, Any]]:
    timestamp = int(tx.get("timestamp", 0) or 0)
    signature = tx.get("signature")
    source = tx.get("source")
    tx_type = tx.get("type")
    events: list[dict[str, Any]] = []
    for row in tx.get("tokenTransfers") or []:
        if row.get("mint") != PRL_MINT:
            continue
        from_owner = row.get("fromUserAccount")
        to_owner = row.get("toUserAccount")
        token_amount = safe_float(row.get("tokenAmount"))
        if token_amount <= 0:
            raw = row.get("rawTokenAmount") or {}
            token_amount = safe_float(raw.get("tokenAmount"))
            decimals = int(raw.get("decimals") or 0)
            if decimals:
                token_amount = token_amount / (10 ** decimals)
        if token_amount <= 0:
            continue
        if from_owner == address:
            direction = "out"
            counterparty = to_owner or ""
        elif to_owner == address:
            direction = "in"
            counterparty = from_owner or ""
        else:
            continue
        events.append({
            "signature": signature,
            "timestamp": timestamp,
            "source": source,
            "type": tx_type,
            "direction": direction,
            "counterparty": counterparty,
            "amount": token_amount,
        })
    return events


def detect_release_status(summary: dict[str, Any]) -> str:
    out_count = summary["outbound_transfer_count"]
    out_cp = summary["unique_outgoing_counterparties"]
    if out_count == 0:
        return "static_unreleased_like"
    if out_count <= 2 and out_cp <= 2:
        return "mostly_static_light_release"
    if out_count >= 50 or out_cp >= 20:
        return "active_release_or_distribution"
    return "moderate_distribution"


def infer_role(holder: dict[str, Any], summary: dict[str, Any]) -> str:
    amount = holder["amount"]
    bucket = holder["resolved_bucket"]
    label = (holder.get("resolved_entity_name") or "").lower()
    release_status = summary["release_status"]
    if holder["address"] == "6pJjJFA69U4YFvwu1wajkLBrP4BoP2ULncBBjKwidLRG":
        return "confirmed_official_operational_wallet"
    if "squads vault" in label:
        return "likely_official_ops_vault"
    if abs(amount - TOP_INVESTOR_ALLOCATION) < 500_000:
        return "likely_investor_vesting_master"
    if holder.get("account_owner_program") and holder["account_owner_program"] != SYSTEM_PROGRAM:
        if abs(amount - ECOSYSTEM_LOCKED_POST_TGE) < 8_000_000 or release_status == "active_release_or_distribution":
            return "likely_ecosystem_release_vault"
        return "program_controlled_official_vault"
    if abs(amount - COMMUNITY_LOCKED_POST_TGE) < 25_000_000:
        return "likely_community_treasury_or_locked_master"
    if release_status == "static_unreleased_like" and holder.get("degree", 0) <= 1:
        return "static_shard_or_split_vault"
    if release_status == "active_release_or_distribution":
        return "active_distribution_wallet"
    return "unlabeled_whale_or_secondary_vault"


def counterparties_table(transfers: list[dict[str, Any]], direction: str, limit: int = 10) -> list[dict[str, Any]]:
    totals = defaultdict(float)
    counts = Counter()
    for event in transfers:
        if event["direction"] != direction:
            continue
        cp = event["counterparty"] or "unknown"
        totals[cp] += event["amount"]
        counts[cp] += 1
    rows = [
        {"counterparty": cp, "amount": amt, "count": counts[cp]}
        for cp, amt in totals.items()
    ]
    rows.sort(key=lambda row: row["amount"], reverse=True)
    return rows[:limit]


def analyze_address(holder: dict[str, Any], history: list[dict[str, Any]], history_meta: dict[str, Any], top10_set: set[str]) -> dict[str, Any]:
    prl_transfers: list[dict[str, Any]] = []
    for tx in history:
        prl_transfers.extend(extract_prl_transfers(holder["address"], tx))

    in_total = sum(event["amount"] for event in prl_transfers if event["direction"] == "in")
    out_total = sum(event["amount"] for event in prl_transfers if event["direction"] == "out")
    in_count = sum(1 for event in prl_transfers if event["direction"] == "in")
    out_count = sum(1 for event in prl_transfers if event["direction"] == "out")
    in_cp = {event["counterparty"] for event in prl_transfers if event["direction"] == "in" and event["counterparty"]}
    out_cp = {event["counterparty"] for event in prl_transfers if event["direction"] == "out" and event["counterparty"]}
    top10_peers = sorted({event["counterparty"] for event in prl_transfers if event["counterparty"] in top10_set and event["counterparty"] != holder["address"]})

    summary = {
        "address": holder["address"],
        "rank": holder["rank"],
        "amount": holder["amount"],
        "share": holder["share"],
        "resolved_bucket": holder["resolved_bucket"],
        "existing_label": holder.get("resolved_entity_name"),
        "history_meta": history_meta,
        "prl_transfer_count": len(prl_transfers),
        "inbound_transfer_count": in_count,
        "outbound_transfer_count": out_count,
        "inbound_total": in_total,
        "outbound_total": out_total,
        "net_flow": in_total - out_total,
        "unique_incoming_counterparties": len(in_cp),
        "unique_outgoing_counterparties": len(out_cp),
        "top10_counterparties": top10_peers,
        "top_incoming_counterparties": counterparties_table(prl_transfers, "in"),
        "top_outgoing_counterparties": counterparties_table(prl_transfers, "out"),
        "first_prl_transfer_ts": min((event["timestamp"] for event in prl_transfers), default=None),
        "last_prl_transfer_ts": max((event["timestamp"] for event in prl_transfers), default=None),
        "sample_events": prl_transfers[:20],
    }
    summary["release_status"] = detect_release_status(summary)
    summary["role_inference"] = infer_role(holder, summary)
    return summary


def main() -> None:
    analysis = load_analysis()
    holders = analysis["top10_holders"]
    top10_set = {row["address"] for row in holders}
    keys = load_keys()
    rotator = HeliusRotator(keys)
    out_rows = []

    for holder in holders:
        address = holder["address"]
        min_ts = parse_first_activity(holder.get("first_activity_date"))
        log(f"Fetching {holder['rank']} {short_addr(address)} from {holder.get('first_activity_date')}")
        history, meta = fetch_history(rotator, address, min_timestamp=min_ts)
        raw_payload = {
            "metadata": {
                "fetched_at": iso_now(),
                "address": address,
                "rank": holder["rank"],
                "min_timestamp": min_ts,
                "history_meta": meta,
            },
            "transactions": history,
        }
        write_json(RAW_DIR / f"{address}.json", raw_payload)
        out_rows.append(analyze_address(holder, history, meta, top10_set))
        log(
            f"  PRL txs={out_rows[-1]['prl_transfer_count']} "
            f"in={fmt_num(out_rows[-1]['inbound_total'])} out={fmt_num(out_rows[-1]['outbound_total'])} "
            f"role={out_rows[-1]['role_inference']}"
        )

    payload = {
        "metadata": {
            "generated_at": iso_now(),
            "token": "PRL",
            "mint": PRL_MINT,
            "address_count": len(out_rows),
            "helius_key_suffixes_used": sorted(rotator.usage),
            "helius_request_counts": dict(rotator.usage),
        },
        "addresses": out_rows,
    }
    write_json(DERIVED_PATH, payload)
    log(f"Wrote {DERIVED_PATH.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
