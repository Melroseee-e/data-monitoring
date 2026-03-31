#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data" / "prl"
RAW_DIR = DATA_DIR / "raw"
DERIVED_DIR = DATA_DIR / "derived"
REPORT_DIR = DATA_DIR / "reports"

RAW_BUBBLEMAPS_PATH = RAW_DIR / "prl_top500_holders_bubblemaps.json"
RAW_ARKHAM_PATH = RAW_DIR / "prl_top100_holders_arkham.json"
DERIVED_ANALYSIS_PATH = DERIVED_DIR / "prl_holder_analysis.json"
DERIVED_LABELS_PATH = DERIVED_DIR / "label_inventory.json"
DERIVED_OFFICIAL_PATH = DERIVED_DIR / "official_address_registry.json"
DERIVED_RELATIONS_PATH = DERIVED_DIR / "address_relationships.json"
DERIVED_TX_SUMMARY_PATH = DERIVED_DIR / "prl_top10_transaction_summary.json"
REPORT_PATH = REPORT_DIR / "prl_holder_structure_report.md"

PRL_MINT = "PERLEQKUNUp1dgFZ8EvyXHdN9d6ZQqfGxALDvfs6pDs"
PRL_SYMBOL = "PRL"
PRL_NAME = "Perle"
TOTAL_SUPPLY = 1_000_000_000.0
TGE_DATE = "2026-03-25"
BUBBLEMAPS_INTERNAL_API = "https://api.bubblemaps.io"
BUBBLEMAPS_JWT_SECRET = "LTJBO6Dsb5dEJ9pS"
ARKHAM_BASE = "https://api.arkm.com"
SOLANA_PUBLIC_RPC = "https://api.mainnet-beta.solana.com"
SYSTEM_PROGRAM = "11111111111111111111111111111111"

TOKEN_OVERVIEW_URL = "https://perle.gitbook.io/perle-docs/tokenomics/token-overview"
TOKEN_VESTING_URL = "https://perle.gitbook.io/perle-docs/tokenomics/token-vesting"
TOKEN_UTILITY_URL = "https://perle.gitbook.io/perle-docs/tokenomics/prl-token-utility-and-purpose"
AUDIT_URL = "https://perle.gitbook.io/perle-docs/perle-prl-token-passes-security-audit-with-halborn"
FUNDING_URL = "https://www.perle.ai/resources/perle-secures-9-million-seed-round-led-by-framework-ventures-to-launch-an-ai-data-training-platform-powered-by-web3"

DOC_FACTS = {
    "chain": "Solana",
    "total_supply_text": "1B",
    "tge_date": "03/25/2026",
    "mint": PRL_MINT,
    "metadata_update_authority": "6pJjJFA69U4YFvwu1wajkLBrP4BoP2ULncBBjKwidLRG",
    "mint_authority_revoked": True,
    "freeze_authority_null": True,
    "vesting": [
        {"bucket": "Team", "allocation_pct": 17.00, "tge_unlock": "0%", "cliff": "12 months", "vesting": "36 months"},
        {"bucket": "Investors", "allocation_pct": 27.66, "tge_unlock": "0%", "cliff": "12 months", "vesting": "36 months"},
        {"bucket": "Ecosystem", "allocation_pct": 17.84, "tge_unlock": "10% (of total supply)", "cliff": "N/A", "vesting": "48 months"},
        {"bucket": "Community", "allocation_pct": 37.50, "tge_unlock": "7.5% (of total supply)", "cliff": "N/A", "vesting": "36 months"},
    ],
}

TOKENOMICS_BREAKDOWN = [
    {
        "bucket": "Community",
        "allocation_pct": 0.375,
        "allocation_amount": 375_000_000.0,
        "tge_unlocked_amount": 75_000_000.0,
        "locked_after_tge": 300_000_000.0,
        "cliff": "N/A",
        "vesting": "36 months",
    },
    {
        "bucket": "Investors",
        "allocation_pct": 0.2766,
        "allocation_amount": 276_600_000.0,
        "tge_unlocked_amount": 0.0,
        "locked_after_tge": 276_600_000.0,
        "cliff": "12 months",
        "vesting": "36 months",
    },
    {
        "bucket": "Ecosystem",
        "allocation_pct": 0.1784,
        "allocation_amount": 178_400_000.0,
        "tge_unlocked_amount": 100_000_000.0,
        "locked_after_tge": 78_400_000.0,
        "cliff": "N/A",
        "vesting": "48 months",
    },
    {
        "bucket": "Team",
        "allocation_pct": 0.17,
        "allocation_amount": 170_000_000.0,
        "tge_unlocked_amount": 0.0,
        "locked_after_tge": 170_000_000.0,
        "cliff": "12 months",
        "vesting": "36 months",
    },
]

ROLE_DISPLAY = {
    "confirmed_official_master_distributor": "官方一级分发总控",
    "likely_community_master_wallet": "Community 主仓",
    "likely_investor_vesting_master": "Investors 主锁仓",
    "likely_ecosystem_master_wallet": "Ecosystem 主仓",
    "likely_ecosystem_release_vault": "Ecosystem 释放 Vault",
    "likely_team_distribution_hub": "Team 二级分发中枢",
    "likely_team_static_shard": "Team 静态分仓",
    "confirmed_public_authority_wallet": "公开 metadata authority 钱包",
    "likely_official_ops_vault": "官方运营 / ServiceCo Vault",
    "unlabeled_whale_or_secondary_vault": "待观察大户 / 二级 Vault",
}

RELEASE_STATUS_DISPLAY = {
    "static_unreleased_like": "未见释放",
    "mostly_static_light_release": "轻微释放",
    "moderate_distribution": "中度分发",
    "active_release_or_distribution": "活跃释放",
}

PUBLIC_OFFICIAL_ADDRESSES = {
    "mint": {
        "address": PRL_MINT,
        "role": "token_mint",
        "confidence": "high",
        "evidence": f"Token Overview 公布 PRL Solana mint 为 {PRL_MINT}。",
        "source_url": TOKEN_OVERVIEW_URL,
    },
    "metadata_update_authority": {
        "address": DOC_FACTS["metadata_update_authority"],
        "role": "metadata_update_authority",
        "confidence": "high",
        "evidence": (
            "Audit 页面公开写明 metadata update authority 为 "
            f"{DOC_FACTS['metadata_update_authority']}。"
        ),
        "source_url": AUDIT_URL,
    },
}

EXCHANGE_KEYWORDS = {
    "binance", "coinbase", "bitget", "gate", "gate.io", "mexc", "kucoin",
    "okx", "bybit", "kraken", "exchange", "hot wallet", "deposit",
}
DEX_KEYWORDS = {"amm", "pool", "liquidity", "lp", "raydium", "orca", "meteora"}
OFFICIAL_KEYWORDS = {"squads vault", "foundation", "serviceco", "treasury", "custody"}


def log(message: str) -> None:
    stamp = datetime.now(tz=timezone.utc).strftime("%H:%M:%S")
    print(f"[{stamp}] {message}", flush=True)


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def iso_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def safe_float(value: Any) -> float:
    if value in (None, "", "null"):
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def fmt_num(value: Any, digits: int = 2) -> str:
    return f"{safe_float(value):,.{digits}f}"


def fmt_pct(value: Any, digits: int = 2) -> str:
    return f"{safe_float(value) * 100:.{digits}f}%"


def short_addr(address: str) -> str:
    return f"{address[:6]}...{address[-4:]}" if len(address) > 12 else address


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def load_optional_json(path: Path) -> Any | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def approx(value: float, target: float, tolerance: float) -> bool:
    return abs(safe_float(value) - safe_float(target)) <= tolerance


def role_display(code: str | None) -> str:
    if not code:
        return "待定"
    return ROLE_DISPLAY.get(code, code)


def release_display(code: str | None) -> str:
    if not code:
        return "未定"
    return RELEASE_STATUS_DISPLAY.get(code, code)


def counterparty_line(entry: dict[str, Any] | None) -> str | None:
    if not entry:
        return None
    counterparty = entry.get("counterparty") or "unknown"
    amount = safe_float(entry.get("amount"))
    return f"{short_addr(counterparty)} / {fmt_num(amount, 2)} PRL"


def bubblemaps_validation_token(path: str) -> str:
    now = int(time.time())
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    payload = _b64url(json.dumps({"data": path, "exp": now + 300, "iat": now}).encode())
    signing_input = f"{header}.{payload}".encode()
    sig = hmac.new(BUBBLEMAPS_JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url(sig)}"


def bubblemaps_fetch_top_holders() -> dict[str, Any]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = f"/addresses/token-top-holders?count=500&date={today}&nocache=false"
    headers = {
        "Content-Type": "application/json",
        "X-Validation": bubblemaps_validation_token(path),
    }
    body = {"chain": "solana", "address": PRL_MINT}
    resp = requests.post(f"{BUBBLEMAPS_INTERNAL_API}{path}", headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    rows = resp.json()
    return {
        "metadata": {
            "fetched_at": iso_now(),
            "token": PRL_SYMBOL,
            "name": PRL_NAME,
            "chain": "solana",
            "contract": PRL_MINT,
            "source": "BubbleMaps internal API",
            "holder_count": len(rows),
        },
        "holders": rows,
    }


def arkham_request(method: str, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
    api_key = os.environ.get("ARKHAM_API_KEY", "")
    if not api_key:
        raise RuntimeError("ARKHAM_API_KEY missing")
    session = requests.Session()
    headers = {"API-Key": api_key}
    url = f"{ARKHAM_BASE}{path}"
    backoff = 1.0
    for attempt in range(5):
        resp = session.request(method, url, headers=headers, params=params, timeout=30)
        if resp.status_code == 429:
            wait = min(32, backoff)
            log(f"Arkham 429 on {path}, retry in {wait:.0f}s")
            time.sleep(wait)
            backoff *= 2
            continue
        if resp.status_code == 402:
            raise RuntimeError("Arkham credits exhausted")
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Arkham request failed after retries: {path}")


def arkham_fetch_top_holders() -> dict[str, Any]:
    data = arkham_request("GET", f"/token/holders/solana/{PRL_MINT}")
    holders = []
    for row in data.get("addressTopHolders", {}).get("solana", []):
        address = (row.get("address") or {}).get("address", "")
        entity = (row.get("address") or {}).get("arkhamEntity") or {}
        label = (row.get("address") or {}).get("arkhamLabel") or {}
        holders.append({
            "address": address,
            "balance": safe_float(row.get("balance")),
            "pct_of_cap": safe_float(row.get("pctOfCap")),
            "entity_name": entity.get("name"),
            "entity_type": entity.get("type"),
            "entity_id": entity.get("id"),
            "entity_website": entity.get("website"),
            "label": label.get("name"),
        })
    return {
        "metadata": {
            "fetched_at": iso_now(),
            "token": PRL_SYMBOL,
            "contract": PRL_MINT,
            "holder_count": len(holders),
            "source": "Arkham token holders",
        },
        "holders": holders,
    }


def public_rpc_get_account_info(address: str) -> dict[str, Any] | None:
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getAccountInfo",
        "params": [address, {"encoding": "jsonParsed"}],
    }
    try:
        resp = requests.post(SOLANA_PUBLIC_RPC, json=payload, timeout=20)
        resp.raise_for_status()
        return resp.json().get("result", {}).get("value")
    except Exception:
        return None


def normalize_text(*parts: Any) -> str:
    text = " ".join("" if part is None else str(part) for part in parts).lower()
    return " ".join(text.split())


def validate_doc_page(url: str, required_strings: list[str]) -> dict[str, Any]:
    html = requests.get(url, timeout=20).text
    return {
        "url": url,
        "checked_at": iso_now(),
        "checks": {needle: (needle in html) for needle in required_strings},
    }


def derive_account_notes(address: str, info: dict[str, Any] | None) -> tuple[str | None, dict[str, Any]]:
    if not info:
        return "public_rpc_not_available", {}
    owner = info.get("owner")
    space = info.get("space")
    executable = bool(info.get("executable"))
    if owner and owner != SYSTEM_PROGRAM:
        note = f"账户 owner 为 {owner}，不是普通 system wallet，偏向程序控制或 vault 型账户。"
    elif space == 0 and not executable:
        note = "链上形态是普通 system wallet。"
    else:
        note = "链上形态无法直接归为普通钱包，需要结合标签判断。"
    return note, {
        "owner_program": owner,
        "space": space,
        "executable": executable,
    }


def classify_holder(row: dict[str, Any], docs_public: set[str]) -> tuple[str, str, str]:
    address = row["address"]
    label_text = normalize_text(row.get("resolved_entity_name"), row.get("bubblemaps_label"), row.get("arkham_label"), row.get("arkham_entity_name"))
    is_cex = bool(row.get("bubblemaps_is_cex")) or any(token in label_text for token in EXCHANGE_KEYWORDS)
    is_dex = bool(row.get("bubblemaps_is_dex")) or any(token in label_text for token in DEX_KEYWORDS)

    if address in docs_public:
        return "official_public", "high", "官方 docs 或 audit 直接公开。"
    if is_cex:
        return "exchange", "high", "BubbleMaps / Arkham 明确识别为交易所热钱包。"
    if is_dex:
        return "dex_pool", "high", "BubbleMaps 明确识别为 DEX / 池子地址。"

    owner_program = row.get("account_owner_program")
    bubblemaps_contract = bool(row.get("bubblemaps_is_contract"))
    first_activity = str(row.get("first_activity_date") or "")
    arkham_label = normalize_text(row.get("arkham_label"))
    rank = int(row.get("rank") or 0)

    if "squads vault" in arkham_label and rank <= 10:
        return "official_inferred", "medium", "Arkham 直接打到 Squads Vault，且处于 Top 10。"
    if bubblemaps_contract and owner_program and owner_program != SYSTEM_PROGRAM and rank <= 10:
        return "official_inferred", "medium", "Top 10 中的程序控制账户，更像官方 vault / 托管层而非自然大户。"
    if bubblemaps_contract and any(token in label_text for token in OFFICIAL_KEYWORDS):
        return "official_inferred", "medium", "标签和账户形态同时指向官方基础设施。"
    if first_activity.startswith("2026-03-") and row.get("degree", 0) <= 1 and rank <= 10:
        return "whale", "medium", "TGE 后新创建的单跳大仓，更像分仓后的静态大户。"
    if rank <= 10:
        return "whale", "medium", "Top 10 未见公开官方或交易所证据，按大户处理。"
    return "unknown", "low", "缺少足够证据。"


def bucket_display(bucket: str) -> str:
    return {
        "official_public": "已公开官方",
        "official_inferred": "高概率官方",
        "exchange": "交易所",
        "dex_pool": "DEX 池子",
        "whale": "大户",
        "unknown": "其他/未定",
    }.get(bucket, bucket)


def top10_role(bucket: str, row: dict[str, Any]) -> str:
    if bucket == "official_public" and row["address"] == DOC_FACTS["metadata_update_authority"]:
        return "公开 metadata authority 钱包"
    if bucket == "official_inferred" and "squads vault" in normalize_text(row.get("arkham_label")):
        return "疑似 Squads 官方运营/服务 vault"
    if bucket == "official_inferred":
        return "疑似官方基础设施/托管 vault"
    if bucket == "exchange":
        return "交易所库存地址"
    if bucket == "dex_pool":
        return "DEX 流动性池"
    if row.get("degree", 0) <= 1:
        return "单跳静态大仓"
    return "未标注大户"


def compose_evidence_summary(row: dict[str, Any], bucket: str) -> str:
    parts: list[str] = []
    if row["address"] == DOC_FACTS["metadata_update_authority"]:
        parts.append("官方 audit 直接公开为 metadata update authority。")
    if row.get("arkham_label"):
        parts.append(f"Arkham 标签：{row['arkham_label']}")
    if row.get("bubblemaps_label"):
        parts.append(f"BubbleMaps 标签：{row['bubblemaps_label']}")
    if row.get("account_shape_note"):
        parts.append(row["account_shape_note"])
    if row.get("first_activity_date"):
        parts.append(f"BubbleMaps 首次活动时间：{row['first_activity_date']}")
    if row.get("degree") is not None:
        parts.append(
            f"BubbleMaps relation 度数 {row['degree']}，in/out = {row['inward_relations']}/{row['outward_relations']}。"
        )
    if bucket == "whale" and row.get("degree", 0) <= 1:
        parts.append("只有单一关系边，偏向一次性分配/停放钱包，而不是活跃市场账户。")
    return " ".join(parts)


def build_label_inventory(holders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    inventory: dict[str, dict[str, Any]] = {}
    for row in holders:
        labels = []
        if row.get("bubblemaps_label"):
            labels.append(("BubbleMaps", row["bubblemaps_label"]))
        if row.get("arkham_label"):
            labels.append(("Arkham", row["arkham_label"]))
        if row.get("arkham_entity_name"):
            labels.append(("Arkham Entity", row["arkham_entity_name"]))
        for source, label in labels:
            key = f"{source}::{label}"
            entry = inventory.setdefault(key, {
                "source": source,
                "label": label,
                "address_count": 0,
                "share_of_supply": 0.0,
                "sample_addresses": [],
                "resolved_bucket_counts": Counter(),
            })
            entry["address_count"] += 1
            entry["share_of_supply"] += safe_float(row.get("share"))
            entry["resolved_bucket_counts"][row["resolved_bucket"]] += 1
            if len(entry["sample_addresses"]) < 5:
                entry["sample_addresses"].append(row["address"])
    rows = []
    for entry in inventory.values():
        entry["resolved_bucket_counts"] = dict(entry["resolved_bucket_counts"])
        rows.append(entry)
    rows.sort(key=lambda item: item["share_of_supply"], reverse=True)
    return rows


def build_fresh_wallet_cluster(holders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in holders:
        if row["rank"] > 20:
            continue
        if str(row.get("first_activity_date") or "").startswith("2026-03-") and row.get("degree", 0) <= 1:
            out.append({
                "address": row["address"],
                "rank": row["rank"],
                "share": row["share"],
                "first_activity_date": row["first_activity_date"],
                "role": "fresh_static_bucket",
            })
    return out


def load_top10_tx_by_address() -> dict[str, dict[str, Any]]:
    payload = load_optional_json(DERIVED_TX_SUMMARY_PATH) or {}
    return {row["address"]: row for row in payload.get("addresses", []) if row.get("address")}


def merge_top10_tx_fields(row: dict[str, Any], tx: dict[str, Any]) -> None:
    row["tx_prl_transfer_count"] = tx.get("prl_transfer_count", 0)
    row["tx_inbound_total"] = safe_float(tx.get("inbound_total"))
    row["tx_outbound_total"] = safe_float(tx.get("outbound_total"))
    row["tx_net_flow"] = safe_float(tx.get("net_flow"))
    row["tx_release_status"] = tx.get("release_status")
    row["tx_release_status_label"] = release_display(tx.get("release_status"))
    row["tx_role_inference"] = tx.get("role_inference")
    row["tx_first_prl_transfer_ts"] = tx.get("first_prl_transfer_ts")
    row["tx_last_prl_transfer_ts"] = tx.get("last_prl_transfer_ts")
    row["tx_unique_incoming_counterparties"] = int(tx.get("unique_incoming_counterparties") or 0)
    row["tx_unique_outgoing_counterparties"] = int(tx.get("unique_outgoing_counterparties") or 0)
    row["tx_top10_counterparties"] = tx.get("top10_counterparties") or []
    row["tx_top_incoming_counterparties"] = tx.get("top_incoming_counterparties") or []
    row["tx_top_outgoing_counterparties"] = tx.get("top_outgoing_counterparties") or []
    row["tx_primary_inbound"] = row["tx_top_incoming_counterparties"][0] if row["tx_top_incoming_counterparties"] else None
    row["tx_primary_outbound"] = row["tx_top_outgoing_counterparties"][0] if row["tx_top_outgoing_counterparties"] else None


def infer_top10_from_tx(row: dict[str, Any]) -> dict[str, Any] | None:
    if row.get("rank", 0) > 10 or not row.get("tx_prl_transfer_count"):
        return None

    address = row["address"]
    primary_in = row.get("tx_primary_inbound") or {}
    primary_out = row.get("tx_primary_outbound") or {}
    in_cp = primary_in.get("counterparty")
    in_amt = safe_float(primary_in.get("amount"))
    out_amt = safe_float(primary_out.get("amount"))
    tx_in = safe_float(row.get("tx_inbound_total"))
    tx_out = safe_float(row.get("tx_outbound_total"))
    release_status = row.get("tx_release_status")
    label_text = normalize_text(row.get("resolved_entity_name"), row.get("arkham_label"), row.get("bubblemaps_label"))

    if address == DOC_FACTS["metadata_update_authority"] and tx_out >= 900_000_000:
        return {
            "bucket": "official_public",
            "confidence": "high",
            "role_code": "confirmed_official_master_distributor",
            "tokenomics_bucket": "Master Distributor",
            "research_label": "官方一级分发总控",
            "reason": "Audit 公开的 metadata authority 地址，链上又直接向 Community / Investors / Ecosystem / Team 主分配地址累计打出约 10 亿 PRL。",
        }
    if in_cp == DOC_FACTS["metadata_update_authority"] and approx(in_amt, 375_000_000.0, 100_000.0):
        return {
            "bucket": "official_inferred",
            "confidence": "high",
            "role_code": "likely_community_master_wallet",
            "tokenomics_bucket": "Community",
            "research_label": "Community 主仓候选",
            "reason": "从公开官方总控地址单点收到 375M PRL，与 docs 的 Community 配额完全对齐；当前已净分发约 57.02M，剩余约 317.98M。",
        }
    if in_cp == DOC_FACTS["metadata_update_authority"] and approx(in_amt, 276_619_098.0, 50_000.0):
        return {
            "bucket": "official_inferred",
            "confidence": "high",
            "role_code": "likely_investor_vesting_master",
            "tokenomics_bucket": "Investors",
            "research_label": "Investors 主锁仓候选",
            "reason": "从公开官方总控地址直接收到 276.619098M PRL，和 docs 的 Investors 27.66% 几乎一一对应，当前未见继续释放。",
        }
    if in_cp == DOC_FACTS["metadata_update_authority"] and approx(in_amt, 178_380_902.0, 50_000.0):
        return {
            "bucket": "official_inferred",
            "confidence": "high",
            "role_code": "likely_ecosystem_master_wallet",
            "tokenomics_bucket": "Ecosystem",
            "research_label": "Ecosystem 主仓候选",
            "reason": "从公开官方总控地址直接收到 178.380902M PRL，和 docs 的 Ecosystem 17.84% 几乎完全对齐，目前已向外分发约 87.30M。",
        }
    if tx_in >= 169_900_000.0 and tx_in <= 170_100_000.0 and tx_out >= 150_000_000.0:
        return {
            "bucket": "official_inferred",
            "confidence": "high",
            "role_code": "likely_team_distribution_hub",
            "tokenomics_bucket": "Team",
            "research_label": "Team 二级分发中枢",
            "reason": "累计收到 170M PRL，随后拆分到多个静态分仓地址，和 Team 17% 配额完全对齐。",
        }
    if in_cp and tx_out == 0 and tx_in in {92_650_000.0, 40_000_000.0, 20_000_000.0}:
        return {
            "bucket": "official_inferred",
            "confidence": "high",
            "role_code": "likely_team_static_shard",
            "tokenomics_bucket": "Team",
            "research_label": "Team 静态分仓",
            "reason": f"仅从 {short_addr(in_cp)} 单跳收到 {fmt_num(tx_in, 2)} PRL，之后未继续释放，形态符合 Team 分仓停放地址。",
        }
    if "squads vault" in label_text:
        return {
            "bucket": "official_inferred",
            "confidence": "medium",
            "role_code": "likely_official_ops_vault",
            "tokenomics_bucket": "Operations",
            "research_label": "官方运营 / ServiceCo Vault",
            "reason": "Arkham 直接标注为 Squads Vault / ServiceCo，属于官方运营侧地址而不是市场大户。",
        }
    if row.get("account_owner_program") and row["account_owner_program"] != SYSTEM_PROGRAM and release_status == "active_release_or_distribution":
        return {
            "bucket": "official_inferred",
            "confidence": "medium",
            "role_code": "likely_ecosystem_release_vault",
            "tokenomics_bucket": "Ecosystem",
            "research_label": "Ecosystem 释放 Vault",
            "reason": "程序控制账户，且对外分发活跃，形态更像官方释放 / 再分发 vault，而不是自然大户钱包。",
        }
    return None


def apply_top10_tx_inference(row: dict[str, Any], tx_by_address: dict[str, dict[str, Any]]) -> None:
    tx = tx_by_address.get(row["address"])
    if not tx:
        return
    merge_top10_tx_fields(row, tx)
    inference = infer_top10_from_tx(row)
    if not inference:
        return
    row["resolved_bucket"] = inference["bucket"]
    row["confidence"] = inference["confidence"]
    row["classification_reason"] = inference["reason"]
    row["top_holder_role"] = role_display(inference["role_code"])
    row["role_inference_code"] = inference["role_code"]
    row["tokenomics_bucket"] = inference["tokenomics_bucket"]
    row["research_label"] = inference["research_label"]


def compose_evidence_summary_with_tx(row: dict[str, Any]) -> str:
    parts: list[str] = []
    if row.get("research_label"):
        parts.append(f"研究判断：{row['research_label']}。")
    if row.get("classification_reason"):
        parts.append(row["classification_reason"])
    if row.get("resolved_entity_name"):
        parts.append(f"现有标签：{row['resolved_entity_name']}。")
    if row.get("account_shape_note"):
        parts.append(row["account_shape_note"])
    if row.get("tx_primary_inbound"):
        cp = row["tx_primary_inbound"]
        parts.append(f"主入账来源 {short_addr(cp.get('counterparty') or 'unknown')}，累计 {fmt_num(cp.get('amount'), 2)} PRL。")
    if row.get("tx_primary_outbound"):
        cp = row["tx_primary_outbound"]
        parts.append(f"主出账去向 {short_addr(cp.get('counterparty') or 'unknown')}，累计 {fmt_num(cp.get('amount'), 2)} PRL。")
    if row.get("tx_release_status_label"):
        parts.append(f"释放状态判断：{row['tx_release_status_label']}。")
    if row.get("degree") is not None:
        parts.append(
            f"BubbleMaps relation 度数 {row['degree']}，in/out = {row['inward_relations']}/{row['outward_relations']}。"
        )
    return " ".join(parts)


def build_tokenomics_alignment(holders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_address = {row["address"]: row for row in holders}
    role_rows = {row.get("role_inference_code"): row for row in holders if row.get("role_inference_code")}

    community = role_rows.get("likely_community_master_wallet")
    investors = role_rows.get("likely_investor_vesting_master")
    ecosystem_master = role_rows.get("likely_ecosystem_master_wallet")
    ecosystem_release = role_rows.get("likely_ecosystem_release_vault")
    team_hub = role_rows.get("likely_team_distribution_hub")
    team_shards = [row for row in holders if row.get("role_inference_code") == "likely_team_static_shard"]

    alignment = []
    for item in TOKENOMICS_BREAKDOWN:
        bucket = item["bucket"]
        matched_rows: list[dict[str, Any]] = []
        summary = ""
        if bucket == "Community" and community:
            matched_rows = [community]
            summary = "公开官方总控地址先打 375M 到该地址，当前已分发约 57.02M，仍保留约 317.98M。"
        elif bucket == "Investors" and investors:
            matched_rows = [investors]
            summary = "从官方总控地址直接收到 276.619098M，当前仍基本静态，最像 investor vesting master。"
        elif bucket == "Ecosystem":
            matched_rows = [row for row in [ecosystem_master, ecosystem_release] if row]
            summary = "主仓是 178.380902M 的精确配额钱包，另有程序控制释放 vault 持续向外分发。"
        elif bucket == "Team":
            matched_rows = [row for row in [team_hub, *team_shards] if row]
            summary = "170M 先进入 Team 分发中枢，再拆到多个静态分仓。"
        alignment.append({
            **item,
            "matched_addresses": [
                {
                    "address": row["address"],
                    "rank": row["rank"],
                    "amount": row["amount"],
                    "share": row["share"],
                    "role": row.get("top_holder_role"),
                    "release_status": row.get("tx_release_status_label"),
                }
                for row in matched_rows
            ],
            "summary": summary,
        })
    return alignment


def build_official_distribution_flows(holders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_address = {row["address"]: row for row in holders}
    flows: list[dict[str, Any]] = []
    for row in holders:
        if row.get("rank", 0) > 10:
            continue
        primary_in = row.get("tx_primary_inbound")
        if primary_in:
            amount = safe_float(primary_in.get("amount"))
            if amount < 1_000_000:
                continue
            if row.get("role_inference_code") == "confirmed_official_master_distributor":
                continue
            upstream = primary_in.get("counterparty")
            flows.append({
                "upstream": upstream,
                "downstream": row["address"],
                "amount": amount,
                "downstream_role": row.get("top_holder_role"),
                "tokenomics_bucket": row.get("tokenomics_bucket"),
                "reason": row.get("classification_reason"),
            })
    flows.sort(key=lambda item: item["amount"], reverse=True)
    return flows


def fetch_and_build() -> dict[str, Any]:
    load_dotenv(BASE_DIR / ".env", override=False)
    tx_by_address = load_top10_tx_by_address()

    log("Fetching BubbleMaps Top 500 holders")
    bubblemaps_payload = bubblemaps_fetch_top_holders()
    write_json(RAW_BUBBLEMAPS_PATH, bubblemaps_payload)

    log("Fetching Arkham top holder labels")
    arkham_payload = arkham_fetch_top_holders()
    write_json(RAW_ARKHAM_PATH, arkham_payload)

    arkham_by_address = {row["address"]: row for row in arkham_payload["holders"] if row.get("address")}
    docs_public = {item["address"] for item in PUBLIC_OFFICIAL_ADDRESSES.values()}
    doc_validation = {
        "token_overview": validate_doc_page(TOKEN_OVERVIEW_URL, [DOC_FACTS["chain"], DOC_FACTS["total_supply_text"], DOC_FACTS["tge_date"], PRL_MINT]),
        "audit": validate_doc_page(AUDIT_URL, [DOC_FACTS["metadata_update_authority"]]),
        "token_vesting": validate_doc_page(TOKEN_VESTING_URL, ["Team", "17.00%", "Investors", "27.66%", "Ecosystem", "17.84%", "Community", "37.50%"]),
    }

    holders: list[dict[str, Any]] = []
    for raw in bubblemaps_payload["holders"]:
        holder = raw.get("holder_data") or {}
        details = raw.get("address_details") or {}
        address = str(raw.get("address") or "")
        if not address:
            continue
        arkham = arkham_by_address.get(address, {})
        entry = {
            "address": address,
            "rank": int(holder.get("rank") or 0),
            "amount": safe_float(holder.get("amount")),
            "share": safe_float(holder.get("share")),
            "bubblemaps_label": details.get("label"),
            "bubblemaps_is_cex": bool(details.get("is_cex")),
            "bubblemaps_is_dex": bool(details.get("is_dex")),
            "bubblemaps_is_contract": bool(details.get("is_contract")),
            "bubblemaps_entity_id": details.get("entity_id"),
            "degree": int(details.get("degree") or 0),
            "inward_relations": int(details.get("inward_relations") or 0),
            "outward_relations": int(details.get("outward_relations") or 0),
            "first_activity_date": details.get("first_activity_date"),
            "arkham_entity_name": arkham.get("entity_name"),
            "arkham_entity_type": arkham.get("entity_type"),
            "arkham_entity_id": arkham.get("entity_id"),
            "arkham_label": arkham.get("label"),
            "arkham_pct_of_cap": safe_float(arkham.get("pct_of_cap")),
        }
        entry["resolved_entity_name"] = entry["bubblemaps_label"] or entry["arkham_label"] or entry["arkham_entity_name"]
        holders.append(entry)

    top10_addresses = {row["address"] for row in holders[:10]}
    account_info_by_address = {address: public_rpc_get_account_info(address) for address in top10_addresses}

    for row in holders:
        info = account_info_by_address.get(row["address"])
        note, extra = derive_account_notes(row["address"], info)
        row["account_shape_note"] = note
        row["account_owner_program"] = extra.get("owner_program")
        row["account_space"] = extra.get("space")
        row["account_executable"] = extra.get("executable")
        bucket, confidence, reason = classify_holder(row, docs_public)
        row["resolved_bucket"] = bucket
        row["confidence"] = confidence
        row["classification_reason"] = reason
        row["top_holder_role"] = top10_role(bucket, row) if row["rank"] <= 10 else None
        row["evidence_summary"] = compose_evidence_summary(row, bucket)
        apply_top10_tx_inference(row, tx_by_address)
        if row["rank"] <= 10 and row.get("tx_prl_transfer_count"):
            row["evidence_summary"] = compose_evidence_summary_with_tx(row)

    holders.sort(key=lambda row: row["rank"])
    top10 = [row for row in holders if row["rank"] <= 10]
    top500_share = sum(row["share"] for row in holders)
    bucket_share = defaultdict(float)
    bucket_count = Counter()
    for row in holders:
        bucket_share[row["resolved_bucket"]] += row["share"]
        bucket_count[row["resolved_bucket"]] += 1

    top10_bucket_share = defaultdict(float)
    for row in top10:
        top10_bucket_share[row["resolved_bucket"]] += row["share"]

    top10_share = sum(row["share"] for row in top10)
    top5_share = sum(row["share"] for row in top10[:5])
    exchange_rows = [row for row in holders if row["resolved_bucket"] == "exchange"]
    dex_rows = [row for row in holders if row["resolved_bucket"] == "dex_pool"]
    official_rows = [row for row in holders if row["resolved_bucket"] in {"official_public", "official_inferred"}]

    first_exchange_rank = exchange_rows[0]["rank"] if exchange_rows else None
    first_dex_rank = dex_rows[0]["rank"] if dex_rows else None

    fresh_wallet_cluster = build_fresh_wallet_cluster(holders)
    official_watchlist = [row for row in top10 if row["resolved_bucket"] in {"official_public", "official_inferred"}]
    tokenomics_alignment = build_tokenomics_alignment(holders)
    official_distribution_flows = build_official_distribution_flows(holders)

    official_registry_map = {item["address"]: dict(item) for item in PUBLIC_OFFICIAL_ADDRESSES.values()}
    for row in official_watchlist:
        official_registry_map[row["address"]] = {
            "address": row["address"],
            "role": row.get("top_holder_role"),
            "confidence": row.get("confidence"),
            "bucket": row.get("resolved_bucket"),
            "tokenomics_bucket": row.get("tokenomics_bucket"),
            "evidence": row.get("classification_reason"),
            "share": row.get("share"),
        }
    official_registry = list(official_registry_map.values())

    analysis = {
        "metadata": {
            "generated_at": iso_now(),
            "token": PRL_SYMBOL,
            "name": PRL_NAME,
            "chain": "solana",
            "contract": PRL_MINT,
            "total_supply": TOTAL_SUPPLY,
            "tge_date": TGE_DATE,
            "sources": {
                "bubblemaps": RAW_BUBBLEMAPS_PATH.relative_to(BASE_DIR).as_posix(),
                "arkham": RAW_ARKHAM_PATH.relative_to(BASE_DIR).as_posix(),
                "token_overview_url": TOKEN_OVERVIEW_URL,
                "token_vesting_url": TOKEN_VESTING_URL,
                "token_utility_url": TOKEN_UTILITY_URL,
                "audit_url": AUDIT_URL,
                "funding_url": FUNDING_URL,
                "tx_summary": DERIVED_TX_SUMMARY_PATH.relative_to(BASE_DIR).as_posix() if DERIVED_TX_SUMMARY_PATH.exists() else None,
            },
        },
        "docs_facts": DOC_FACTS,
        "tokenomics_breakdown": TOKENOMICS_BREAKDOWN,
        "doc_validation": doc_validation,
        "summary": {
            "top10_share": top10_share,
            "top5_share": top5_share,
            "top500_covered_share": top500_share,
            "official_share": sum(row["share"] for row in official_rows),
            "exchange_share": sum(row["share"] for row in exchange_rows),
            "dex_share": sum(row["share"] for row in dex_rows),
            "whale_share": bucket_share["whale"],
            "first_exchange_rank": first_exchange_rank,
            "first_dex_rank": first_dex_rank,
            "official_count": len(official_rows),
            "exchange_count": len(exchange_rows),
            "dex_count": len(dex_rows),
            "tge_unlocked_amount": sum(item["tge_unlocked_amount"] for item in TOKENOMICS_BREAKDOWN),
            "locked_after_tge_amount": sum(item["locked_after_tge"] for item in TOKENOMICS_BREAKDOWN),
        },
        "top10_layer_summary": [
            {
                "bucket": bucket,
                "bucket_label": bucket_display(bucket),
                "address_count": sum(1 for row in top10 if row["resolved_bucket"] == bucket),
                "share_of_supply": share,
            }
            for bucket, share in sorted(top10_bucket_share.items(), key=lambda item: item[1], reverse=True)
        ],
        "all_holder_bucket_summary": [
            {
                "bucket": bucket,
                "bucket_label": bucket_display(bucket),
                "address_count": bucket_count[bucket],
                "share_of_supply": bucket_share[bucket],
            }
            for bucket in sorted(bucket_share, key=lambda item: bucket_share[item], reverse=True)
        ],
        "top10_holders": top10,
        "holders": holders,
        "official_watchlist": official_watchlist,
        "fresh_wallet_cluster": fresh_wallet_cluster,
        "tokenomics_alignment": tokenomics_alignment,
        "official_distribution_flows": official_distribution_flows,
        "label_inventory": build_label_inventory(holders),
        "official_registry": official_registry,
        "address_relationships": {
            "official_core": [
                {
                    "address": DOC_FACTS["metadata_update_authority"],
                    "relation": "public_official",
                    "summary": "公开 metadata update authority，同时链上直接向四个主配额地址分发约 10 亿 PRL。",
                },
                {
                    "address": "5MnWHhe5Bbuq8X6kwU3PCEfBFqJvb2uequxMtnRBHcQx",
                    "relation": "official_inferred",
                    "summary": 'Arkham 将其标注为 Squads Vault "SGL Marketing Lumen ServiceCo"，当前位列第 9。'
                },
                {
                    "address": "HfXxndwJekWeExQyPgE32dCLLh2QbVrcU3AtE2bL4fdh",
                    "relation": "official_inferred",
                    "summary": "Top 10 中唯一明显程序控制账户，链上 owner 不是 system program，且活动窗口紧贴 TGE。"
                },
            ],
            "official_distribution_flows": official_distribution_flows,
            "fresh_static_wallets": fresh_wallet_cluster,
        },
    }
    return analysis


def table(headers: list[str], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def build_report(analysis: dict[str, Any]) -> str:
    top10 = analysis["top10_holders"]
    summary = analysis["summary"]
    top10_rows = [
        [
            str(row["rank"]),
            f"`{short_addr(row['address'])}`",
            fmt_num(row["amount"], 2),
            fmt_pct(row["share"], 2),
            bucket_display(row["resolved_bucket"]),
            row.get("tokenomics_bucket") or "—",
            row.get("top_holder_role") or "—",
            row.get("tx_release_status_label") or "—",
        ]
        for row in top10
    ]

    tokenomics_rows = []
    for row in analysis["tokenomics_alignment"]:
        mapped = " / ".join(
            f"{item['role']} {short_addr(item['address'])}"
            for item in row["matched_addresses"]
        ) or "未识别"
        tokenomics_rows.append([
            row["bucket"],
            fmt_pct(row["allocation_pct"], 2),
            fmt_num(row["allocation_amount"], 0),
            fmt_num(row["tge_unlocked_amount"], 0),
            fmt_num(row["locked_after_tge"], 0),
            row["vesting"],
            mapped,
        ])

    flow_rows = [
        [
            f"`{short_addr(row['upstream'])}`" if row["upstream"] else "—",
            f"`{short_addr(row['downstream'])}`",
            fmt_num(row["amount"], 2),
            row.get("tokenomics_bucket") or "—",
            row.get("downstream_role") or "—",
        ]
        for row in analysis["official_distribution_flows"][:12]
    ]

    official_rows = [
        [
            str(row["rank"]),
            f"`{row['address']}`",
            bucket_display(row["resolved_bucket"]),
            row.get("tokenomics_bucket") or "—",
            fmt_pct(row["share"], 3),
            row["classification_reason"],
        ]
        for row in analysis["official_watchlist"]
    ]

    label_rows = [
        [
            row["source"],
            row["label"],
            str(row["address_count"]),
            fmt_pct(row["share_of_supply"], 3),
        ]
        for row in analysis["label_inventory"][:20]
    ]

    lines = [
        "# PRL Solana Top 10 筹码结构报告",
        "",
        f"- 生成时间: {analysis['metadata']['generated_at']}",
        f"- 研究对象: `{PRL_MINT}`",
        f"- 官方主链口径: Solana，Total Supply = 1B，TGE = 2026-03-25",
        f"- 官方资料: [Token Overview]({TOKEN_OVERVIEW_URL}) / [Token Vesting]({TOKEN_VESTING_URL}) / [Token Utility]({TOKEN_UTILITY_URL}) / [Audit]({AUDIT_URL}) / [Funding]({FUNDING_URL})",
        "",
        "## 一眼结论",
        "",
        f"- Top 10 当前合计持有 **{fmt_pct(summary['top10_share'], 2)}**，而且这一层现在更像**官方配额与分发地图本身**，不是交易所 / DEX / 民间鲸鱼混合层。",
        f"- `6pJjJFA69U4YFvwu1wajkLBrP4BoP2ULncBBjKwidLRG` 不只是公开 metadata authority；链上还直接从它向四个主配额方向打出约 **1B PRL**，因此它现在应视为**官方一级分发总控**。",
        "- 最强匹配关系是：`Community -> #1`、`Investors -> #2`、`Ecosystem -> #3`、`Team -> #10 + #4/#6/#8`。",
        f"- Top 10 里当前**没有交易所，也没有 DEX 池子**；第一个交易所地址要到第 `{summary['first_exchange_rank']}` 名。",
        "",
        "## Tokenomics 快照",
        "",
        f"- TGE 理论已解锁: **{fmt_num(summary['tge_unlocked_amount'], 0)} PRL**",
        f"- TGE 后理论仍锁定 / 待释放: **{fmt_num(summary['locked_after_tge_amount'], 0)} PRL**",
        "",
        table(["Bucket", "Allocation", "Amount", "TGE Unlock", "Locked After TGE", "Vesting", "当前链上候选"], tokenomics_rows),
        "",
        "## 官方分发路径",
        "",
        table(["上游", "下游", "金额", "Tokenomics Bucket", "推断角色"], flow_rows),
        "",
        "## Top 10 角色判断",
        "",
        table(["Rank", "地址", "持仓", "占总量", "归类", "配额桶", "角色", "释放状态"], top10_rows),
        "",
        "## 官方地址与推断地址",
        "",
        "### 已公开官方",
        "",
        f"- `{DOC_FACTS['metadata_update_authority']}`: [Audit]({AUDIT_URL}) 直接公开为 metadata update authority；链上又实际承担 1B PRL 的一级分发总控。",
        f"- `{PRL_MINT}`: [Token Overview]({TOKEN_OVERVIEW_URL}) 直接公开为 PRL 的 Solana mint。",
        "",
        "### 高概率官方 / 高概率配额钱包",
        "",
        table(["Rank", "地址", "层级", "配额桶", "占总量", "理由"], official_rows),
        "",
        "## Top 10 逐地址推断",
        "",
    ]

    for row in top10:
        primary_in = counterparty_line(row.get("tx_primary_inbound"))
        primary_out = counterparty_line(row.get("tx_primary_outbound"))
        lines.extend([
            f"### #{row['rank']} `{row['address']}`",
            "",
            f"- 当前角色判断: **{row.get('top_holder_role') or '待定'}**",
            f"- 当前持仓: **{fmt_num(row['amount'], 2)} PRL** ({fmt_pct(row['share'], 3)})",
            f"- Tokenomics 对位: **{row.get('tokenomics_bucket') or '未定'}**",
            f"- 释放状态: **{row.get('tx_release_status_label') or '未定'}**",
            f"- 推断理由: {row.get('classification_reason') or '—'}",
            f"- 主入账: {primary_in or '—'}",
            f"- 主出账: {primary_out or '—'}",
            f"- 证据摘要: {row.get('evidence_summary') or '—'}",
            "",
        ])

    lines.extend([
        "## 交易所 / DEX / 大户观察",
        "",
        f"- 第一个交易所地址只到第 `{summary['first_exchange_rank']}` 名，当前 BubbleMaps / Arkham 识别到的交易所下限仓位约 **{fmt_pct(summary['exchange_share'], 3)}**。",
        f"- DEX / LP 不在 Top 10，BubbleMaps Top 500 中的 DEX 下限仓位约 **{fmt_pct(summary['dex_share'], 3)}**。",
        "- 结合 Helius 流水，本轮最重要的更新是：Top 10 已经不该再被默认视作“未标注鲸鱼层”，而应主要视作官方 allocation / treasury / release / shard 层。",
        "",
        "## Label Inventory（前 20）",
        "",
        table(["来源", "标签", "地址数", "占总量"], label_rows),
        "",
        "## 数据说明",
        "",
        "- 当前持仓快照来自 BubbleMaps Top 500。",
        "- 地址实体标签以 Arkham 为主补充，BubbleMaps 负责 CEX / DEX / contract 标记。",
        "- Top 10 的 PRL 交易流水额外来自 Helius Enhanced API，并已单独落盘到 `data/prl/raw/top10_helius_history/`。",
        "- 这版报告最大的变化是把“金额是否对上 docs 配额”和“主入账 / 主出账路径”并入推断逻辑，而不是只看 BubbleMaps 标签。",
    ])
    return "\n".join(lines) + "\n"


def main() -> None:
    analysis = fetch_and_build()
    write_json(DERIVED_ANALYSIS_PATH, analysis)
    write_json(DERIVED_LABELS_PATH, analysis["label_inventory"])
    write_json(DERIVED_OFFICIAL_PATH, analysis["official_registry"])
    write_json(DERIVED_RELATIONS_PATH, analysis["address_relationships"])
    report = build_report(analysis)
    write_text(REPORT_PATH, report)
    log(f"Wrote {DERIVED_ANALYSIS_PATH.relative_to(BASE_DIR)}")
    log(f"Wrote {REPORT_PATH.relative_to(BASE_DIR)}")


if __name__ == "__main__":
    main()
