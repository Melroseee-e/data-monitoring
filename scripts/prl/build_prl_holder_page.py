#!/usr/bin/env python3
from __future__ import annotations

import html
import time
import json
import hmac
import hashlib
import base64
from pathlib import Path
from typing import Any
from datetime import datetime, timezone

import requests

BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_FILE = BASE_DIR / "data" / "prl" / "derived" / "prl_holder_analysis.json"
OUTPUT_FILE = BASE_DIR / "web" / "prl_holder_structure.html"

BSC_CONTRACT = "0xd20fB09A49a8e75Fef536A2dBc68222900287BAc"
BSC_TOTAL_SUPPLY = 83_448_737.510778
BSC_SOLANA_PEER = "HfXxndwJekWeExQyPgE32dCLLh2QbVrcU3AtE2bL4fdh"
BSC_SOLANA_ESCROW_TOKEN_ACCOUNT = "96Pn2C665uvfiV968PYV1exdNUn3qvbBqHhX2n1kSkgw"
BSC_SOLANA_PEER_PROGRAM = "76fxTpnrukUr6i36wK8K4UJsABtAaPJxP9nZytQKTaPU"
BSC_LAYERZERO_ENDPOINT = "0x1a44076050125825900e736c501f859c50fe728c"
BUBBLEMAPS_INTERNAL_API = "https://api.bubblemaps.io"
BUBBLEMAPS_JWT_SECRET = "LTJBO6Dsb5dEJ9pS"
BSC_TOP_HOLDERS_FALLBACK = [
    {
        "rank": 1,
        "address": "0x0350c44e15ada696992d44b13225e0853277adc0",
        "amount": 43_160_000.0,
        "label": "-",
        "holder_type": "未标注大户",
    },
    {
        "rank": 2,
        "address": "0xc3c74940e878b0e9ac86a12b0125c4df1a8f22d7",
        "amount": 10_000_000.0,
        "label": "-",
        "holder_type": "未标注大户",
    },
    {
        "rank": 3,
        "address": "0x73d8bd54f7cf5fab43fe4ef40a62d390644946db",
        "amount": 5_892_437.95799694,
        "label": "Binance Wallet Proxy (EIP-1967 Transparent)",
        "holder_type": "交易所",
    },
    {
        "rank": 4,
        "address": "0x5861703aa2c6acd7a3902e5a06f6aedba0eae257",
        "amount": 5_000_000.0,
        "label": "-",
        "holder_type": "未标注大户",
    },
    {
        "rank": 5,
        "address": "0x5a4c318d66c0cf8ef381320a5d49f8a329414f50",
        "amount": 5_000_000.0,
        "label": "-",
        "holder_type": "未标注大户",
    },
    {
        "rank": 6,
        "address": "0xccf4d99cb373e054cc8dbf31dca37b8528ec5b55",
        "amount": 5_000_000.0,
        "label": "-",
        "holder_type": "未标注大户",
    },
    {
        "rank": 7,
        "address": "0x0c4bb5b2a4cff8c035b590da8e0cf650f63f8c61",
        "amount": 4_499_990.0,
        "label": "-",
        "holder_type": "未标注大户",
    },
    {
        "rank": 8,
        "address": "0x238a358808379702088667322f80ac48bad5e6c4",
        "amount": 2_631_759.34214794,
        "label": "PancakeSwap Vault (0x23...e6c4)",
        "holder_type": "DEX 池子",
    },
    {
        "rank": 9,
        "address": "0x1026efec22061b9f463b63e75e8b531a76404820",
        "amount": 490_624.25512711,
        "label": "-",
        "holder_type": "未标注大户",
    },
    {
        "rank": 10,
        "address": "0x372386969100562870d156b64fe05c26c2adc168",
        "amount": 238_064.21390527,
        "label": "-",
        "holder_type": "未标注大户",
    },
]


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_bubblemaps_jwt(path: str) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    now = int(time.time())
    payload = _b64url(json.dumps({
        "data": path,
        "exp": now + 300,
        "iat": now,
    }).encode())
    signing_input = f"{header}.{payload}".encode()
    sig = hmac.new(BUBBLEMAPS_JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{header}.{payload}.{_b64url(sig)}"


def fetch_bsc_top_holders(count: int = 500) -> list[dict[str, Any]]:
    path = f"/addresses/token-top-holders?count={count}&date={datetime.now(timezone.utc).strftime('%Y-%m-%d')}&nocache=false"
    headers = {
        "X-Validation": make_bubblemaps_jwt(path),
        "Content-Type": "application/json",
    }
    body = {"chain": "bsc", "address": BSC_CONTRACT}
    response = requests.post(f"{BUBBLEMAPS_INTERNAL_API}{path}", headers=headers, json=body, timeout=60)
    response.raise_for_status()
    return response.json()


def fmt_num(value: float, decimals: int = 2) -> str:
    number = float(value)
    if abs(number) >= 1_000_000:
        scaled = number / 1_000_000
        if decimals <= 0:
            text = f"{scaled:,.0f}"
        else:
            text = f"{scaled:,.{decimals}f}".rstrip("0").rstrip(".")
        return f"{text}M"
    if decimals <= 0:
        return f"{number:,.0f}"
    return f"{number:,.{decimals}f}".rstrip("0").rstrip(".")


def fmt_pct(value: float, decimals: int = 2) -> str:
    return f"{float(value) * 100:.{decimals}f}%"


def fmt_num_pct(amount: float, total: float, num_decimals: int = 0, pct_decimals: int = 2) -> str:
    if not total:
        return fmt_num(amount, num_decimals)
    return f"{fmt_num(amount, num_decimals)} ({fmt_pct(float(amount) / float(total), pct_decimals)})"


def short_addr(address: str, left: int = 6, right: int = 4) -> str:
    if len(address) <= left + right:
        return address
    return f"{address[:left]}...{address[-right:]}"


def esc(value: Any) -> str:
    return html.escape(str(value))


def solscan_url(address: str) -> str:
    return f"https://solscan.io/account/{address}"


def bscscan_url(address: str) -> str:
    return f"https://bscscan.com/address/{address}"


def bucket_label(bucket: str) -> str:
    return {
        "official_public": "已公开官方",
        "official_inferred": "高概率官方",
        "exchange": "交易所",
        "dex_pool": "DEX 池子",
        "whale": "大户",
        "unknown": "其他/未定",
    }.get(bucket, bucket)


def normalize_tag(bucket: str | None) -> str:
    bucket = (bucket or "").lower()
    if bucket in {"official", "official_public", "official_inferred"}:
        return "官方"
    if bucket in {"exchange", "cex"}:
        return "CEX"
    if bucket in {"dex", "dex_pool"}:
        return "DEX"
    return "大户"


def tag_badge(tag: str) -> str:
    css = {
        "官方": "tag-official",
        "大户": "tag-whale",
        "CEX": "tag-cex",
        "DEX": "tag-dex",
    }.get(tag, "tag-whale")
    return f"<span class=\"tag-badge {css}\">{esc(tag)}</span>"


def holder_title(row: dict[str, Any]) -> str:
    return row.get("research_label") or row.get("resolved_entity_name") or "No BubbleMaps / Arkham label"


def first_seen_text(value: str | None) -> str:
    if not value:
        return "-"
    return value[:10]


def market_holder_type(row: dict[str, Any]) -> str:
    label = (row.get("resolved_entity_name") or row.get("research_label") or "").lower()
    if "custody" in label or "fireblocks" in label:
        return "托管 / 机构痕迹"
    if label:
        return "已标注非官方"
    return "未标注大户"


def classify_bsc_holder(holder: dict[str, Any]) -> str:
    details = holder.get("address_details", {})
    if details.get("is_cex"):
        return "exchange"
    if details.get("is_dex"):
        return "dex"
    if details.get("label"):
        return "labeled_non_exchange"
    return "unlabeled_whale"


def summarize_bsc_holders(holders: list[dict[str, Any]], cutoff: int) -> dict[str, Any]:
    sample = [row for row in holders if int(row["holder_data"]["rank"]) <= cutoff]
    summary = {
        "cutoff": cutoff,
        "total_amount": sum(float(row["holder_data"]["amount"]) for row in sample),
        "counts": {"unlabeled_whale": 0, "labeled_non_exchange": 0, "exchange": 0, "dex": 0},
        "amounts": {"unlabeled_whale": 0.0, "labeled_non_exchange": 0.0, "exchange": 0.0, "dex": 0.0},
    }
    for row in sample:
        bucket = classify_bsc_holder(row)
        amount = float(row["holder_data"]["amount"])
        summary["counts"][bucket] += 1
        summary["amounts"][bucket] += amount
    return summary


def bsc_label_or_role(holder: dict[str, Any]) -> str:
    details = holder.get("address_details", {})
    label = details.get("label")
    if label:
        return str(label)
    bucket = classify_bsc_holder(holder)
    if bucket == "exchange":
        return "交易所"
    if bucket == "dex":
        return "DEX 池子"
    if bucket == "labeled_non_exchange":
        return "已标注非官方"
    return "未标注大户"


def bsc_first_seen(holder: dict[str, Any]) -> str:
    value = holder.get("address_details", {}).get("first_activity_date")
    return first_seen_text(value)


def bsc_relations_text(holder: dict[str, Any]) -> str:
    details = holder.get("address_details", {})
    return f"{details.get('degree', 0)} / {details.get('inward_relations', 0)} / {details.get('outward_relations', 0)}"


def bsc_working_takeaway(holder: dict[str, Any]) -> str:
    details = holder.get("address_details", {})
    amount = float(holder["holder_data"]["amount"])
    rank = int(holder["holder_data"]["rank"])
    outward = int(details.get("outward_relations") or 0)
    degree = int(details.get("degree") or 0)
    bucket = classify_bsc_holder(holder)

    if bucket == "exchange":
        return "交易所库存，不视作独立大户。"
    if bucket == "dex":
        return "DEX / LP 库存，不视作独立大户。"
    if rank == 1:
        return "核心大仓，更像 BNB 映射层的分发母仓。"
    if amount in {10_000_000.0, 5_000_000.0} or abs(amount - 4_499_990.0) < 1:
        return "整数/近整数分仓，更像规则化拆分出来的分仓。"
    if degree <= 8 and outward == 0:
        return "关系很少且几乎不外发，更像静态持仓仓位。"
    return "未标注大户，但更偏次级流通持仓而不是基础设施。"


def build_bsc_snapshot() -> dict[str, Any]:
    try:
        holders = fetch_bsc_top_holders(500)
        source = "live"
    except Exception:
        holders = []
        for row in BSC_TOP_HOLDERS_FALLBACK:
            holders.append({
                "address": row["address"],
                "address_details": {
                    "label": None if row["label"] == "-" else row["label"],
                    "degree": 0,
                    "is_supernode": False,
                    "is_contract": row["holder_type"] == "DEX 池子",
                    "is_cex": row["holder_type"] == "交易所",
                    "is_dex": row["holder_type"] == "DEX 池子",
                    "entity_id": None,
                    "inward_relations": 0,
                    "outward_relations": 0,
                    "first_activity_date": None,
                },
                "holder_data": {
                    "amount": row["amount"],
                    "rank": row["rank"],
                    "share": row["amount"] / BSC_TOTAL_SUPPLY,
                },
            })
        source = "fallback"

    top10 = [row for row in holders if int(row["holder_data"]["rank"]) <= 10]
    top20_summary = summarize_bsc_holders(holders, 20)
    top50_summary = summarize_bsc_holders(holders, 50)
    core_whales = [
        row for row in holders
        if classify_bsc_holder(row) == "unlabeled_whale" and float(row["holder_data"]["amount"]) >= 4_000_000
    ]
    core_whales = sorted(core_whales, key=lambda row: float(row["holder_data"]["amount"]), reverse=True)
    return {
        "source": source,
        "holders": holders,
        "top10": top10,
        "top20_summary": top20_summary,
        "top50_summary": top50_summary,
        "core_whales": core_whales,
    }


def rank_ref(address: str, rank_map: dict[str, int]) -> str:
    rank = rank_map.get(address)
    if rank:
        return f"地址{rank}"
    return short_addr(address)


def top_rank_ref(address: str, rank_map: dict[str, int]) -> str | None:
    rank = rank_map.get(address)
    if rank:
        return f"Top {rank}"
    return None


def counterparty_text(entry: dict[str, Any] | None, rank_map: dict[str, int]) -> str:
    if not entry:
        return "-"
    counterparty = entry.get("counterparty") or "unknown"
    amount = float(entry.get("amount") or 0.0)
    return f"{rank_ref(counterparty, rank_map)} / {fmt_num(amount, 2)} PRL"


def stat_card(label: str, value: str, note: str, tone: str = "warm") -> str:
    return f"""
    <article class="stat stat-{esc(tone)}">
      <div class="stat-label">{esc(label)}</div>
      <div class="stat-value">{esc(value)}</div>
      <div class="stat-note">{esc(note)}</div>
    </article>
    """


def info_card(title: str, body: str, tone: str = "sand") -> str:
    return f"""
    <article class="info-card info-{esc(tone)}">
      <h3>{esc(title)}</h3>
      <p>{body}</p>
    </article>
    """


def table_section(title: str, subtitle: str, headers: list[str], rows: list[list[str]]) -> str:
    thead = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>")
    if not body:
        body.append(f"<tr><td colspan=\"{len(headers)}\">No data.</td></tr>")
    return f"""
    <section class="panel table-panel section">
      <div class="section-head">
        <div>
          <div class="eyebrow">Data Slice</div>
          <h2>{esc(title)}</h2>
        </div>
        <p>{esc(subtitle)}</p>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr>{thead}</tr></thead>
          <tbody>{''.join(body)}</tbody>
        </table>
      </div>
    </section>
    """


def build_page(data: dict[str, Any], bsc_snapshot: dict[str, Any]) -> str:
    metadata = data["metadata"]
    summary = data["summary"]
    docs = data["docs_facts"]
    top10 = data["top10_holders"]
    holders = data["holders"]
    tokenomics_alignment = data["tokenomics_alignment"]

    symbol = metadata["token"]
    name = metadata["name"]
    generated_at = metadata["generated_at"]
    total_supply = metadata["total_supply"]
    top10_rank_map = {row["address"]: int(row["rank"]) for row in top10}

    official_top10_share = sum(row["share"] for row in top10 if row["resolved_bucket"] in {"official_public", "official_inferred"})
    top11_50_share = sum(row["share"] for row in holders if 11 <= int(row["rank"]) <= 50)
    bsc_top10_holders = bsc_snapshot["top10"]
    bsc_top20_summary = bsc_snapshot["top20_summary"]
    bsc_top50_summary = bsc_snapshot["top50_summary"]
    bsc_core_whales = bsc_snapshot["core_whales"]
    bsc_top10_total_share = sum(float(row["holder_data"]["amount"]) for row in bsc_top10_holders) / total_supply
    bsc_core_whale_amount = sum(float(row["holder_data"]["amount"]) for row in bsc_core_whales)
    whale_candidates = [
        row for row in holders
        if row.get("resolved_bucket") not in {"official_public", "official_inferred", "exchange", "dex_pool"}
        and float(row.get("share") or 0) >= 0.0001
    ][:8]

    stat_cards = "".join([
        stat_card("Official Share", fmt_pct(official_top10_share), "当前已识别官方样仓位。", "sand"),
        stat_card("Top 10 Share", fmt_pct(summary["top10_share"]), "顶层筹码集中度。", "blue"),
        stat_card("BNB Bridged Slice", fmt_num_pct(BSC_TOTAL_SUPPLY, total_supply, 2), "当前映射到 BNB 的总量。", "cool"),
        stat_card("TGE Unlocked", fmt_num_pct(summary["tge_unlocked_amount"], total_supply, 0), "docs 理论已解锁量。", "rose"),
    ])

    tokenomics_rows = []
    for item in tokenomics_alignment:
        docs_col = (
            f"<strong>{esc(fmt_pct(item['allocation_pct']))}</strong><br>"
            f"{esc(fmt_num(item['allocation_amount'], 0))} PRL"
        )
        unlock_col = (
            f"TGE {esc(fmt_num_pct(item['tge_unlocked_amount'], total_supply, 0))}<br>"
            f"Locked {esc(fmt_num_pct(item['locked_after_tge'], total_supply, 0))}"
        )
        vesting_col = (
            f"Cliff {esc(item.get('cliff') or 'N/A')}<br>"
            f"Vesting {esc(item.get('vesting') or '-')}"
        )
        matched_parts = []
        rank_parts = []
        for addr in item["matched_addresses"]:
            role_label = addr["role"] or "地址"
            matched_parts.append(
                f"{esc(role_label)} <a href=\"{esc(solscan_url(addr['address']))}\" target=\"_blank\" rel=\"noreferrer\"><code>{esc(short_addr(addr['address']))}</code></a>"
            )
            rank_parts.append(
                f"{esc(role_label)} · {esc(top_rank_ref(addr['address'], top10_rank_map) or '非 Top 10')}"
            )
        matched_col = "<br>".join(matched_parts) or "未识别"
        rank_col = "<br>".join(rank_parts) or "-"
        tokenomics_rows.append([
            tag_badge("官方"),
            esc(item["bucket"]),
            docs_col,
            unlock_col,
            vesting_col,
            matched_col,
            rank_col,
            esc(item["summary"] or "-"),
        ])

    top10_rows = []
    for row in top10:
        current_col = (
            f"{esc(fmt_num(row['amount'], 2))} PRL<br>"
            f"{esc(fmt_pct(row['share'], 3))}"
        )
        top10_rows.append([
            tag_badge(normalize_tag(row.get("resolved_bucket"))),
            esc(str(row["rank"])),
            f"<a href=\"{esc(solscan_url(row['address']))}\" target=\"_blank\" rel=\"noreferrer\"><code>{esc(short_addr(row['address']))}</code></a>",
            current_col,
            esc(row.get("tokenomics_bucket") or "-"),
            esc(row.get("top_holder_role") or "-"),
            esc(row.get("tx_release_status_label") or "-"),
            esc(row.get("classification_reason") or "-"),
        ])

    whale_rows = []
    for row in whale_candidates:
        whale_rows.append([
            tag_badge("大户"),
            esc(str(row["rank"])),
            f"<a href=\"{esc(solscan_url(row['address']))}\" target=\"_blank\" rel=\"noreferrer\"><code>{esc(short_addr(row['address']))}</code></a>",
            f"{esc(fmt_num(row['amount'], 2))} PRL<br>{esc(fmt_pct(row['share'], 3))}",
            esc(holder_title(row).replace("No BubbleMaps / Arkham label", "无外部标签")),
            esc(market_holder_type(row)),
            esc(first_seen_text(row.get("first_activity_date"))),
        ])

    bsc_core_rows = []
    for row in bsc_core_whales:
        details = row["address_details"]
        bsc_core_rows.append([
            tag_badge("大户"),
            esc(str(row["holder_data"]["rank"])),
            f"<a href=\"{esc(bscscan_url(row['address']))}\" target=\"_blank\" rel=\"noreferrer\"><code>{esc(short_addr(row['address']))}</code></a>",
            f"{esc(fmt_num(row['holder_data']['amount'], 2))} PRL",
            esc(fmt_pct(float(row["holder_data"]["amount"]) / total_supply, 3)),
            esc(bsc_first_seen(row)),
            esc(bsc_relations_text(row)),
            esc(bsc_working_takeaway(row)),
        ])

    combined_rank_rows = []
    combined_rank_entries: list[dict[str, Any]] = []
    for row in top10:
        relation = "主发行层"
        if row["address"] == BSC_SOLANA_PEER:
            relation = "BNB 映射总量上层 peer / store"
        combined_rank_entries.append({
            "tag": normalize_tag(row.get("resolved_bucket")),
            "amount": float(row["amount"]),
            "chain": "Solana",
            "address_cell": f"<a href=\"{esc(solscan_url(row['address']))}\" target=\"_blank\" rel=\"noreferrer\"><code>{esc(short_addr(row['address']))}</code></a>",
            "current": f"{esc(fmt_num(row['amount'], 2))} PRL",
            "share": esc(fmt_pct(row["amount"] / total_supply, 3)),
            "label": esc(row.get("top_holder_role") or row.get("tokenomics_bucket") or "-"),
            "relation": esc(relation),
        })
    for row in bsc_top10_holders:
        amount = float(row["holder_data"]["amount"])
        bsc_tag = normalize_tag(classify_bsc_holder(row))
        combined_rank_entries.append({
            "tag": bsc_tag,
            "amount": amount,
            "chain": "BNB",
            "address_cell": f"<a href=\"{esc(bscscan_url(row['address']))}\" target=\"_blank\" rel=\"noreferrer\"><code>{esc(short_addr(row['address']))}</code></a>",
            "current": f"{esc(fmt_num(amount, 2))} PRL",
            "share": esc(fmt_pct(amount / total_supply, 3)),
            "label": esc(bsc_label_or_role(row)),
            "relation": "BNB 映射流通下游",
        })
    combined_rank_entries.sort(key=lambda item: item["amount"], reverse=True)
    for idx, item in enumerate(combined_rank_entries, start=1):
        combined_rank_rows.append([
            tag_badge(item["tag"]),
            esc(str(idx)),
            esc(item["chain"]),
            item["address_cell"],
            item["current"],
            item["share"],
            item["label"],
            esc(item["relation"]),
        ])

    source_path = "https://github.com/Melroseee-e/data-monitoring"
    report_md = "../data/prl/reports/prl_holder_structure_report.md"
    analysis_json = "../data/prl/derived/prl_holder_analysis.json"
    tx_json = "../data/prl/derived/prl_top10_transaction_summary.json"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(name)} ({esc(symbol)}) Top 10 Intelligence Report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;700;800&family=JetBrains+Mono:wght@400;600&family=Noto+Sans+SC:wght@400;500;700;900&display=swap" rel="stylesheet">
<style>
:root {{
  --bg: #f4efe4;
  --bg-2: #eadfce;
  --ink: #171717;
  --ink-soft: #495163;
  --line: rgba(23, 23, 23, 0.12);
  --panel: rgba(255,255,255,0.78);
  --panel-strong: rgba(255,255,255,0.92);
  --sand: #d8832d;
  --sand-deep: #9b4f17;
  --blue: #1967c8;
  --teal: #0c8d7a;
  --rose: #b13d5d;
  --shadow: 0 24px 80px rgba(31, 26, 18, 0.12);
  --mono: "JetBrains Mono", monospace;
  --display: "Manrope", "Noto Sans SC", sans-serif;
  --body: "Noto Sans SC", sans-serif;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{
  font-family: var(--body);
  color: var(--ink);
  background:
    radial-gradient(circle at 15% 20%, rgba(216,131,45,0.16), transparent 26%),
    radial-gradient(circle at 84% 16%, rgba(25,103,200,0.12), transparent 22%),
    linear-gradient(180deg, #f7f1e8 0%, #f4efe4 42%, #eadfce 100%);
  min-height: 100vh;
}}
body::before {{
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(23,23,23,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(23,23,23,0.03) 1px, transparent 1px);
  background-size: 30px 30px;
  mask-image: linear-gradient(180deg, rgba(0,0,0,0.32), transparent 88%);
}}
a {{ color: inherit; text-decoration: none; }}
code {{
  font-family: var(--mono);
  font-size: 0.9em;
  background: rgba(23,23,23,0.06);
  padding: 0.18rem 0.38rem;
  border-radius: 0.45rem;
}}
.shell {{
  width: min(1240px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 28px 0 64px;
}}
.hero {{
  position: relative;
  overflow: hidden;
  background: linear-gradient(140deg, rgba(255,255,255,0.82), rgba(255,250,242,0.94));
  border: 1px solid rgba(23,23,23,0.08);
  border-radius: 28px;
  padding: 28px;
  box-shadow: var(--shadow);
}}
.hero::after {{
  content: "";
  position: absolute;
  right: -60px;
  top: -80px;
  width: 240px;
  height: 240px;
  background: radial-gradient(circle, rgba(216,131,45,0.22), transparent 66%);
}}
.eyebrow {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-family: var(--mono);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--sand-deep);
  font-size: 12px;
}}
.hero h1 {{
  margin: 12px 0 10px;
  font-family: var(--display);
  font-size: clamp(2.2rem, 5vw, 4.4rem);
  line-height: 0.95;
  letter-spacing: -0.05em;
}}
.hero p {{
  max-width: 760px;
  margin: 0;
  color: var(--ink-soft);
  font-size: 1rem;
  line-height: 1.7;
}}
.hero-grid {{
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 24px;
  align-items: end;
}}
.meta-box {{
  display: grid;
  gap: 10px;
  justify-items: start;
}}
.meta-line {{
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  color: var(--ink-soft);
}}
.meta-pill {{
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 999px;
  background: rgba(23,23,23,0.05);
  border: 1px solid rgba(23,23,23,0.06);
}}
.section {{
  margin-top: 26px;
}}
.stats {{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}}
.stat, .panel, .info-card, .dossier {{
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 24px;
  box-shadow: 0 14px 44px rgba(31, 26, 18, 0.08);
  backdrop-filter: blur(18px);
}}
.stat {{
  padding: 18px;
}}
.stat-label {{
  font-size: 12px;
  font-family: var(--mono);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--ink-soft);
}}
.stat-value {{
  margin-top: 12px;
  font-family: var(--display);
  font-size: clamp(1.8rem, 3.1vw, 2.7rem);
  font-weight: 800;
  letter-spacing: -0.05em;
}}
.stat-note {{
  margin-top: 8px;
  font-size: 0.95rem;
  color: var(--ink-soft);
  line-height: 1.55;
}}
.stat-cool .stat-value {{ color: var(--teal); }}
.stat-blue .stat-value {{ color: var(--blue); }}
.stat-rose .stat-value {{ color: var(--rose); }}
.section-head {{
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: end;
  margin-bottom: 14px;
}}
.section-head h2 {{
  margin: 6px 0 0;
  font-family: var(--display);
  font-size: clamp(1.35rem, 2.2vw, 2rem);
  letter-spacing: -0.04em;
}}
.section-head p {{
  margin: 0;
  max-width: 560px;
  color: var(--ink-soft);
  line-height: 1.65;
}}
.layer-grid {{
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}}
.info-card {{
  padding: 18px;
}}
.info-card h3 {{
  margin: 0 0 10px;
  font-family: var(--display);
  font-size: 1.12rem;
}}
.info-card p {{
  margin: 0;
  color: var(--ink-soft);
  line-height: 1.6;
}}
.info-ink {{
  background: rgba(255,255,255,0.88);
}}
.dossier-grid {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}}
.dossier {{
  padding: 18px;
  background: linear-gradient(180deg, rgba(255,255,255,0.92), rgba(255,248,241,0.74));
}}
.dossier-top {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}}
.rank-chip {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 56px;
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(216,131,45,0.14);
  color: var(--sand-deep);
  font-family: var(--mono);
  font-weight: 700;
}}
.address-link {{
  font-family: var(--mono);
  color: var(--blue);
  font-weight: 600;
}}
.dossier-label {{
  margin-top: 12px;
  font-size: 1.05rem;
  font-weight: 700;
}}
.pill-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}}
.pill {{
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(23,23,23,0.06);
  color: var(--ink-soft);
  font-size: 12px;
}}
.tag-badge {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 56px;
  padding: 6px 10px;
  border-radius: 999px;
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
  border: 1px solid transparent;
}}
.tag-official {{
  background: rgba(216,131,45,0.14);
  color: var(--sand-deep);
  border-color: rgba(216,131,45,0.24);
}}
.tag-whale {{
  background: rgba(177,61,93,0.12);
  color: var(--rose);
  border-color: rgba(177,61,93,0.20);
}}
.tag-cex {{
  background: rgba(25,103,200,0.12);
  color: var(--blue);
  border-color: rgba(25,103,200,0.20);
}}
.tag-dex {{
  background: rgba(12,141,122,0.12);
  color: var(--teal);
  border-color: rgba(12,141,122,0.20);
}}
.dossier-metric {{
  margin-top: 18px;
  font-family: var(--display);
  font-size: 2.2rem;
  font-weight: 800;
  letter-spacing: -0.05em;
}}
.dossier-sub {{
  color: var(--ink-soft);
  font-size: 0.95rem;
}}
.facts {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 18px 0 0;
}}
.facts div {{
  padding: 12px;
  border-radius: 16px;
  background: rgba(23,23,23,0.04);
}}
.facts dt {{
  font-family: var(--mono);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-soft);
}}
.facts dd {{
  margin: 8px 0 0;
  font-weight: 700;
}}
.note {{
  margin: 16px 0 0;
  color: var(--ink-soft);
  line-height: 1.65;
}}
.panel {{
  padding: 18px;
}}
.table-wrap {{
  overflow-x: auto;
  margin-top: 12px;
}}
table {{
  width: 100%;
  border-collapse: collapse;
  min-width: 720px;
}}
th, td {{
  text-align: left;
  padding: 12px 10px;
  border-bottom: 1px solid rgba(23,23,23,0.08);
  vertical-align: top;
}}
th {{
  font-family: var(--mono);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-soft);
}}
td {{
  color: var(--ink);
}}
.footer {{
  margin-top: 28px;
  padding: 18px 22px;
  border-radius: 22px;
  background: rgba(23,23,23,0.88);
  color: rgba(255,255,255,0.86);
}}
.footer a {{
  color: #fff;
  text-decoration: underline;
}}
@media (max-width: 1080px) {{
  .hero-grid,
  .stats,
  .layer-grid,
  .dossier-grid {{
    grid-template-columns: 1fr;
  }}
}}
@media (max-width: 720px) {{
  .shell {{
    width: min(100vw - 20px, 1240px);
    padding-top: 16px;
  }}
  .hero, .panel, .stat, .info-card, .dossier {{
    border-radius: 20px;
  }}
  .facts {{
    grid-template-columns: 1fr;
  }}
  .section-head {{
    flex-direction: column;
    align-items: start;
  }}
}}
</style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="hero-grid">
        <div>
          <div class="eyebrow">PRL Holder Structure / BubbleMaps + Onchain</div>
          <h1>{esc(name)}<br>{esc(symbol)} Top 10</h1>
          <p>
            Top 10 当前控制 <strong>{esc(fmt_pct(summary['top10_share']))}</strong> 的总供应。
            <code>6pJj...dLRG</code> 是公开官方 + 一级分发总控；Top 10 基本对应 Community / Investors / Ecosystem / Team / Ops。
          </p>
        </div>
        <div class="meta-box">
          <div class="meta-line">
            <span class="meta-pill">SOL <code>{esc(short_addr(metadata['contract'], 10, 8))}</code></span>
            <span class="meta-pill">Authority <code>{esc(short_addr(docs['metadata_update_authority'], 10, 8))}</code></span>
          </div>
          <div class="meta-line">
            <span class="meta-pill">Total Supply <strong>{esc(fmt_num(total_supply, 0))}</strong></span>
            <span class="meta-pill">BNB Slice <strong>{esc(fmt_pct(BSC_TOTAL_SUPPLY / total_supply, 3))}</strong></span>
          </div>
          <div class="meta-line">
            <span class="meta-pill">Top 11-50 <strong>{esc(fmt_pct(top11_50_share))}</strong></span>
            <span class="meta-pill">Generated <strong>{esc(generated_at)}</strong></span>
          </div>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="stats">{stat_cards}</div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <div class="eyebrow">Tokenomics</div>
          <h2>完整代币经济与链上对位</h2>
        </div>
        <p>docs 配额、unlock、vesting、链上候选。</p>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Tag</th><th>Bucket</th><th>Docs</th><th>Unlock</th><th>Vesting</th><th>Current Matching Addresses</th><th>Address Rank</th><th>Why It Fits</th></tr></thead>
          <tbody>{''.join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in tokenomics_rows)}</tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <div class="eyebrow">Top 10</div>
          <h2>Top 10 综合总表</h2>
        </div>
        <p>角色、释放状态、推断理由。</p>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Tag</th><th>Rank</th><th>Address</th><th>Current</th><th>Bucket</th><th>Role</th><th>Release</th><th>Why It Fits</th></tr></thead>
          <tbody>{''.join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in top10_rows)}</tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <div class="eyebrow">Whales</div>
          <h2>非官方大户表</h2>
        </div>
        <p>排除官方、交易所、DEX 后按余额排序。</p>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Tag</th><th>Rank</th><th>Address</th><th>Current</th><th>Label</th><th>Type</th><th>First Seen</th></tr></thead>
          <tbody>{''.join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in whale_rows)}</tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <div class="eyebrow">BNB Bridge</div>
          <h2>BNB 跨链桥与前排大户</h2>
        </div>
        <p>BSC 侧是 LayerZero OFT 映射层，不是额外新增 supply。</p>
      </div>
      <div class="layer-grid">
        {info_card("BNB Bridged Slice", f"当前映射到 BNB 的 PRL 是 {fmt_num(BSC_TOTAL_SUPPLY, 2)}，占官方 1B 总量的 {fmt_pct(BSC_TOTAL_SUPPLY / total_supply, 3)}。", "sand")}
        {info_card("Bridge Model", "BSC PRL 是 LayerZero V2 OFT，不是额外新增 supply。", "ink")}
        {info_card("1:1 Match", f"BNB totalSupply 与 Solana escrow 现在都约为 {fmt_num(BSC_TOTAL_SUPPLY, 2)} PRL，链上是 1:1 对齐。", "ink")}
        {info_card("Solana Peer", f"BSC OFT 的 `peers(30168)` 指向 <code>{short_addr(BSC_SOLANA_PEER)}</code>，它是上层 peer / store，不是普通钱包。", "ink")}
        {info_card("Current BNB Top 10", f"BNB 前十按官方 1B 总量口径当前合计占 {fmt_pct(bsc_top10_total_share, 2)}。前排仍以未标注大户为主，交易所只有 Binance，DEX 主要是 PancakeSwap / Uniswap。", "ink")}
        {info_card("Top 20 Structure", f"BNB Top 20 里未标注地址有 {bsc_top20_summary['counts']['unlabeled_whale']} 个，合计 {fmt_num(bsc_top20_summary['amounts']['unlabeled_whale'], 2)} PRL，占官方总量 {fmt_pct(bsc_top20_summary['amounts']['unlabeled_whale'] / total_supply, 3)}。", "ink")}
        {info_card("Top 50 Structure", f"BNB Top 50 里未标注地址有 {bsc_top50_summary['counts']['unlabeled_whale']} 个，合计 {fmt_num(bsc_top50_summary['amounts']['unlabeled_whale'], 2)} PRL，占官方总量 {fmt_pct(bsc_top50_summary['amounts']['unlabeled_whale'] / total_supply, 3)}。", "ink")}
        {info_card("Core 6 Whales", f"前 6 个核心未标注大户合计 {fmt_num(bsc_core_whale_amount, 2)} PRL，占官方总量 {fmt_pct(bsc_core_whale_amount / total_supply, 3)}。结构更像分发分仓，不像自然形成的市场鲸鱼。", "sand")}
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Tag</th><th>BNB Rank</th><th>Address</th><th>Current</th><th>Total Supply Share</th><th>First Seen</th><th>Relations</th><th>Working Read</th></tr></thead>
          <tbody>{''.join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in bsc_core_rows)}</tbody>
        </table>
      </div>
      <div class="section-head">
        <div>
          <div class="eyebrow">Overall Rank</div>
          <h2>Solana + BNB 统一总榜</h2>
        </div>
        <p>按官方 <code>1B total supply</code> 口径统一重排。</p>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Tag</th><th>Overall Rank</th><th>Chain</th><th>Address</th><th>Current</th><th>Total Supply Share</th><th>Label / Role</th><th>Relation</th></tr></thead>
          <tbody>{''.join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in combined_rank_rows)}</tbody>
        </table>
      </div>
      <p class="note">统一排行全部按官方 <code>1B total supply</code> 口径计算。BNB 行是 Solana bridge slice 的下游流通分布，用于看跨链控盘结构，不可与 Solana 行直接相加。当前最有信息量的是前 6 个未标注大户：它们合计 {fmt_num(bsc_core_whale_amount, 2)} PRL，占 BNB 映射盘约 {fmt_pct(bsc_core_whale_amount / BSC_TOTAL_SUPPLY, 2)}，而且 10M / 5M / 5M / 5M / 4.5M 的整额分仓与集中出现时间，更像规则化分发。</p>
    </section>

    <section class="panel section">
      <div class="section-head">
        <div>
          <div class="eyebrow">Market Structure</div>
          <h2>整体结论</h2>
        </div>
        <p>四句话看完整体结构。</p>
      </div>
      <div class="layer-grid">
        {info_card("Solana 主发行层", f"Top 10 当前控制 {fmt_pct(summary['top10_share'])}，其中官方公开 + 高概率官方合计 {fmt_pct(official_top10_share)}。这一层更像官方配额地图，不像自然市场分布。", "sand")}
        {info_card("BNB 映射层", f"当前跨链到 BNB 的 PRL 是 {fmt_num(BSC_TOTAL_SUPPLY, 2)}，占官方总量 {fmt_pct(BSC_TOTAL_SUPPLY / total_supply, 3)}。这部分是映射流通，不是新增 supply。", "ink")}
        {info_card("BNB 大户结构", f"BNB 前 6 个未标注大户合计 {fmt_num(bsc_core_whale_amount, 2)}，占 BNB 映射盘 {fmt_pct(bsc_core_whale_amount / BSC_TOTAL_SUPPLY, 2)}。10M / 5M / 5M / 5M / 4.5M 的整额分仓更像规则化分发。", "rose")}
        {info_card("交易所与 DEX", f"Solana 主层第一个交易所只到第 {summary['first_exchange_rank']}，交易所下限仓位 {fmt_pct(summary['exchange_share'])}；DEX / LP 下限仓位 {fmt_pct(summary['dex_share'])}。二级市场基础设施不是当前主矛盾。", "ink")}
        {info_card("核心判断", "当前最重要的不是追零散散户，而是盯官方配额释放、Solana 到 BNB 的映射分发，以及 BNB 侧那几个规则化分仓的大户是否继续外流。", "sand")}
      </div>
    </section>

    <footer class="footer">
      Source:
      <a href="{esc(source_path)}" target="_blank" rel="noreferrer">GitHub Repo</a> |
      <a href="{esc(report_md)}" target="_blank" rel="noreferrer">Markdown Report</a> |
      <a href="{esc(analysis_json)}" target="_blank" rel="noreferrer">Analysis JSON</a> |
      <a href="{esc(tx_json)}" target="_blank" rel="noreferrer">Top 10 Tx JSON</a>
    </footer>
  </main>
</body>
</html>
"""


def main() -> None:
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    bsc_snapshot = build_bsc_snapshot()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(build_page(data, bsc_snapshot), encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
