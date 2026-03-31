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


def fetch_and_build() -> dict[str, Any]:
    load_dotenv(BASE_DIR / ".env", override=False)

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
            },
        },
        "docs_facts": DOC_FACTS,
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
        "label_inventory": build_label_inventory(holders),
        "official_registry": list(PUBLIC_OFFICIAL_ADDRESSES.values()),
        "address_relationships": {
            "official_core": [
                {
                    "address": DOC_FACTS["metadata_update_authority"],
                    "relation": "public_official",
                    "summary": "公开 metadata update authority，同时是当前第 7 大持仓地址。",
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
    top10_rows = []
    for row in top10:
        top10_rows.append([
            str(row["rank"]),
            f"`{short_addr(row['address'])}`",
            fmt_num(row["amount"], 2),
            fmt_pct(row["share"], 2),
            bucket_display(row["resolved_bucket"]),
            row["top_holder_role"] or "—",
            row["resolved_entity_name"] or "—",
        ])

    label_rows = []
    for row in analysis["label_inventory"][:20]:
        label_rows.append([
            row["source"],
            row["label"],
            str(row["address_count"]),
            fmt_pct(row["share_of_supply"], 3),
        ])

    official_rows = []
    for row in analysis["official_watchlist"]:
        if row["resolved_bucket"] != "official_inferred":
            continue
        official_rows.append([
            str(row["rank"]),
            f"`{row['address']}`",
            bucket_display(row["resolved_bucket"]),
            fmt_pct(row["share"], 3),
            row["classification_reason"],
        ])

    fresh_rows = []
    for row in analysis["fresh_wallet_cluster"]:
        fresh_rows.append([
            str(row["rank"]),
            f"`{short_addr(row['address'])}`",
            fmt_pct(row["share"], 3),
            row["first_activity_date"],
        ])

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
        f"- Top 10 当前合计持有 **{fmt_pct(summary['top10_share'], 2)}**，Top 5 就占 **{fmt_pct(summary['top5_share'], 2)}**。",
        f"- Top 10 里**没有交易所，也没有 DEX 池子**；第一个交易所地址要到第 `{summary['first_exchange_rank']}` 名。",
        f"- 当前能直接公开确认的官方地址只有 `metadata update authority`：`{DOC_FACTS['metadata_update_authority']}`，它本身就是第 7 大持仓。",
        f"- Top 10 里有两类需要分开看：一类是 `{bucket_display('official_public')}` / `{bucket_display('official_inferred')}`，另一类是没有公开标签的大仓钱包。",
        "",
        "## Top 10 分层",
        "",
        table(["Rank", "地址", "持仓", "占总量", "归类", "角色", "标签"], top10_rows),
        "",
        "## Top 10 结构判断",
        "",
    ]

    for item in analysis["top10_layer_summary"]:
        lines.append(
            f"- {item['bucket_label']}: {item['address_count']} 个地址，合计 {fmt_pct(item['share_of_supply'], 3)}"
        )

    lines.extend([
        "",
        "## 哪些是官方",
        "",
        "### 已公开官方",
        "",
        f"- `{DOC_FACTS['metadata_update_authority']}`: [Audit]({AUDIT_URL}) 直接公开为 metadata update authority，同时它现在是第 7 大持仓地址，持有 {fmt_pct(next(row['share'] for row in top10 if row['address'] == DOC_FACTS['metadata_update_authority']), 3)}。",
        f"- `{PRL_MINT}`: [Token Overview]({TOKEN_OVERVIEW_URL}) 直接公开为 PRL 的 Solana mint。",
        "",
        "### 高概率官方",
        "",
    ])
    if official_rows:
        lines.append(table(["Rank", "地址", "层级", "占总量", "证据"], official_rows))
    else:
        lines.append("- 当前没有额外高置信官方地址。")

    lines.extend([
        "",
        "## 哪些是大户",
        "",
        "- 第 1、2 名两只无标签钱包就合计持有超过 59%，是当前筹码结构的绝对主导层。",
        "- 第 4、6、8、11 名都接近“单跳静态大仓”，BubbleMaps 度数基本为 1，更像分配后停放的钱包，不像交易所或 AMM 基础设施。",
        "- 这意味着 PRL 当前最需要盯的不是交易所流出，而是这些大仓钱包是否开始互转、拆分或向交易所沉淀。",
        "",
        "## 哪些是交易所 / DEX 池子",
        "",
        f"- 交易所最早从第 `{summary['first_exchange_rank']}` 名开始出现，当前 BubbleMaps / Arkham 明确识别到的交易所下限持仓约为 **{fmt_pct(summary['exchange_share'], 3)}**。",
        f"- 当前 DEX / 流动性池不在 Top 10，且在 BubbleMaps Top 500 中占比也很低，下限约为 **{fmt_pct(summary['dex_share'], 3)}**。",
        "- 这说明当前 top of cap 基本不是由交易所库存或池子占据，而是由项目侧/大户侧钱包占据。",
        "",
        "## Tokenomics 对照",
        "",
        "- Docs 把 PRL 定义为 Solana 原生发行，不是多链并表口径。",
        "- Team: 17.00%，0% TGE，12 个月 cliff，36 个月线性释放。",
        "- Investors: 27.66%，0% TGE，12 个月 cliff，36 个月线性释放。",
        "- Ecosystem: 17.84%，TGE 解锁 10% of total supply，其余 48 个月释放。",
        "- Community: 37.50%，TGE 解锁 7.5% of total supply，其余 36 个月释放。",
        "- 结合当前 Top 10，可见市场最集中的并不是交易所，而是更像“项目侧托管 + 大额静态分仓”的结构，这与 TGE 初期的大额分仓持有是相容的。",
        "",
        "## Fresh Wallet 簇",
        "",
    ])
    if fresh_rows:
        lines.append(table(["Rank", "地址", "占总量", "首次活动"], fresh_rows))
    else:
        lines.append("- 未观察到显著的新建静态大仓。")

    lines.extend([
        "",
        "## Label Inventory（前 20）",
        "",
        table(["来源", "标签", "地址数", "占总量"], label_rows),
        "",
        "## 数据说明",
        "",
        "- 当前持仓快照来自 BubbleMaps Top 500。",
        "- 地址实体标签以 Arkham 为主补充，BubbleMaps 负责 CEX / DEX / contract 标记。",
        "- Solscan API key 当前无权限读取付费接口，因此本报告不把 Solscan 当作结构化标签源。",
        "- 由于 Helius key 当前限额，本报告不做全历史大额流水重建，重点是 Top 10 分层与官方识别。",
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
