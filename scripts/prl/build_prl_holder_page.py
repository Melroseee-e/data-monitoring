#!/usr/bin/env python3
"""
Generate the public PRL holder structure HTML page.

Input:
  - data/prl/derived/prl_holder_analysis.json

Output:
  - web/prl_holder_structure.html
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_FILE = BASE_DIR / "data" / "prl" / "derived" / "prl_holder_analysis.json"
OUTPUT_FILE = BASE_DIR / "web" / "prl_holder_structure.html"


def fmt_num(value: float, decimals: int = 2) -> str:
    return f"{value:,.{decimals}f}"


def fmt_pct(value: float, decimals: int = 2) -> str:
    return f"{value * 100:.{decimals}f}%"


def short_addr(address: str, left: int = 6, right: int = 4) -> str:
    if len(address) <= left + right:
        return address
    return f"{address[:left]}...{address[-right:]}"


def esc(value: Any) -> str:
    return html.escape(str(value))


def label_layer_name(layer: str) -> str:
    return {
        "bubble_cex": "BubbleMaps 显式 CEX",
        "bubble_dex": "BubbleMaps 显式 DEX / LP",
        "exchange_deposit_tag": "交易所相关标签",
        "contract_label": "具名合约",
        "named_wallet_label": "具名个人/团队地址",
        "unlabeled": "无 BubbleMaps 标签",
    }.get(layer, layer)


def top10_layer_name(layer: str) -> str:
    return {
        "unlabeled_distribution_cluster": "未标注大户分发簇",
        "exchange_inventory": "交易所库存层",
        "dex_liquidity": "DEX 流动性层",
        "named_holder": "具名地址层",
    }.get(layer, layer)


def holder_note(row: dict[str, Any]) -> str:
    share = fmt_pct(row["current_share_supply"])
    if row["is_cex"]:
        return f"BubbleMaps 直接标记为 {row['bm_label']}，更像交易所库存而不是单一控盘仓。"
    if row["is_dex"]:
        return f"BubbleMaps 直接标记为 {row['bm_label']}，这部分更像交易流动性库存。"
    if row["bm_label"]:
        if row["recent_30d_cex_withdraw_amount"] > 0:
            return f"具名地址且近 30 天有交易所提出记录，当前保留 {share}，行为偏增持。"
        return f"具名地址，当前持仓 {share}，适合作为已知实体样本持续追踪。"
    if row["top_holder_role"] == "主分发母仓":
        return f"无 BubbleMaps 标签，但既是最大仓位又承担明显再分发，形态上更像本轮大户簇母仓。"
    if row["top_holder_role"] == "单次受配分仓":
        return f"无 BubbleMaps 标签，基本表现为单次收币后静置，形态上更像受配分仓。"
    return "无 BubbleMaps 标签，有少量再分发动作，应视为未标注大户分支。"


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
    <section class="panel table-panel">
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


def build_page(data: dict[str, Any]) -> str:
    metadata = data["metadata"]
    summary = data["summary"]
    holders = data["holders"]

    top10 = holders[:10]
    label_inventory = summary.get("label_inventory", [])
    top10_layers = summary.get("top10_layer_summary", [])
    recent = summary["recent_activity_non_infra"]
    non_infra = [row for row in holders if not row["is_cex"] and not row["is_dex"] and not row["is_contract"]]
    top_withdrawers = sorted(
        [row for row in non_infra if row["recent_30d_cex_withdraw_amount"] > 0],
        key=lambda row: float(row["recent_30d_cex_withdraw_amount"]),
        reverse=True,
    )[:5]
    top_depositors = sorted(
        [row for row in non_infra if row["recent_30d_cex_deposit_amount"] > 0],
        key=lambda row: float(row["recent_30d_cex_deposit_amount"]),
        reverse=True,
    )[:5]

    unlabeled_top10_share = sum(
        row["current_share_supply"]
        for row in top10
        if row["top10_control_layer"] == "unlabeled_distribution_cluster"
    )
    top11_50_share = summary["snapshot"]["top50_share"] - summary["snapshot"]["top10_share"]

    stat_cards = "".join([
        stat_card("Top 10 Share", fmt_pct(summary["snapshot"]["top10_share"]), "Top 10 已经决定当前流通盘。"),
        stat_card("Unlabeled Cluster", fmt_pct(unlabeled_top10_share), "7 个未标注地址构成主要控制层。", "cool"),
        stat_card("Binance Inventory", fmt_pct(summary["snapshot"]["bubblemaps_cex_share"]), "BubbleMaps 显式识别到的 CEX 下限仓位。", "blue"),
        stat_card("LP / DEX", fmt_pct(summary["snapshot"]["bubblemaps_dex_share"]), "BubbleMaps 显式识别到的 DEX / LP 仓位。", "rose"),
    ])

    layer_cards = "".join(
        info_card(
            top10_layer_name(item["layer"]),
            (
                f"<strong>{fmt_pct(item['share_supply'])}</strong> of supply, "
                f"{item['count']} addresses, ranks {', '.join(str(rank) for rank in item['ranks'])}."
            ),
            "sand" if item["layer"] == "unlabeled_distribution_cluster" else "ink",
        )
        for item in top10_layers
    )

    dossier_cards = []
    for row in top10:
        address_url = f"https://bscscan.com/address/{row['address']}"
        dossier_cards.append(f"""
        <article class="dossier">
          <div class="dossier-top">
            <div class="rank-chip">#{row['rank']}</div>
            <a class="address-link" href="{esc(address_url)}" target="_blank" rel="noreferrer">{esc(short_addr(row['address']))}</a>
          </div>
          <div class="dossier-label">{esc(row['bm_label'] or 'No BubbleMaps label')}</div>
          <div class="pill-row">
            <span class="pill">{esc(label_layer_name(row['label_layer']))}</span>
            <span class="pill">{esc(row['top_holder_role'])}</span>
            <span class="pill">{esc(row['behavior_class'])}</span>
          </div>
          <div class="dossier-metric">{esc(fmt_pct(row['current_share_supply']))}</div>
          <div class="dossier-sub">Current share of total supply</div>
          <dl class="facts">
            <div><dt>Amount</dt><dd>{esc(fmt_num(row['current_amount'], 4))} PRL</dd></div>
            <div><dt>First inbound</dt><dd>{esc(row['first_inbound_at'] or row['first_activity_date'] or '-')}</dd></div>
            <div><dt>30d netflow</dt><dd>{esc(fmt_num(row['recent_30d_netflow'], 4))}</dd></div>
            <div><dt>Counterparties</dt><dd>{esc(row['unique_counterparties_count'])}</dd></div>
          </dl>
          <p class="note">{esc(holder_note(row))}</p>
        </article>
        """)

    label_rows = [
        [
            esc(item["label"]),
            esc(label_layer_name(item["layer"])),
            esc(item["count"]),
            esc(item["top_rank"]),
            esc(fmt_num(item["amount"], 4)),
            esc(fmt_pct(item["share_supply"])),
        ]
        for item in label_inventory
    ]

    exchange_withdraw_rows = [
        [
            f"<code>{esc(short_addr(row['address']))}</code>",
            esc(row["bm_label"] or "-"),
            esc(row["top_holder_role"]),
            esc(fmt_num(row["recent_30d_cex_withdraw_amount"], 4)),
            esc(fmt_pct(row["current_share_supply"])),
        ]
        for row in top_withdrawers
    ]
    exchange_deposit_rows = [
        [
            f"<code>{esc(short_addr(row['address']))}</code>",
            esc(row["bm_label"] or "-"),
            esc(row["top_holder_role"]),
            esc(fmt_num(row["recent_30d_cex_deposit_amount"], 4)),
            esc(fmt_pct(row["current_share_supply"])),
        ]
        for row in top_depositors
    ]

    source_path = "https://github.com/Melroseee-e/data-monitoring"
    report_md = "../data/prl/reports/prl_holder_structure_report.md"
    analysis_json = "../data/prl/derived/prl_holder_analysis.json"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(metadata['name'])} ({esc(metadata['symbol'])}) Top 10 筹码结构</title>
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
          <h1>{esc(metadata['name'])}<br>{esc(metadata['symbol'])} Top 10</h1>
          <p>
            这份页面不再把 500 个地址摊平展示，而是直接围绕控制流通盘的 Top 10 展开。
            重点是把 Top 10 的角色分清楚，尤其是那 7 个未标注大户地址，它们当前合计控制
            <strong>{esc(fmt_pct(unlabeled_top10_share))}</strong> 的总供应。
          </p>
        </div>
        <div class="meta-box">
          <div class="meta-line">
            <span class="meta-pill">BSC <code>{esc(short_addr(metadata['contract'], 10, 8))}</code></span>
            <span class="meta-pill">SOL <code>{esc(short_addr(metadata['solana_address'], 10, 8))}</code></span>
          </div>
          <div class="meta-line">
            <span class="meta-pill">Total Supply <strong>{esc(fmt_num(metadata['total_supply'], 2))}</strong></span>
            <span class="meta-pill">Snapshot <strong>Top {esc(summary['snapshot']['holder_count'])}</strong></span>
          </div>
          <div class="meta-line">
            <span class="meta-pill">Top 11-50 <strong>{esc(fmt_pct(top11_50_share))}</strong></span>
            <span class="meta-pill">Generated <strong>{esc(metadata['as_of'])}</strong></span>
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
          <div class="eyebrow">Control Layers</div>
          <h2>Top 10 分层</h2>
        </div>
        <p>Top 10 基本可以拆成四层: 未标注大户分发簇、交易所库存、DEX 流动性和具名地址。先把层拆开，再研究单个地址。</p>
      </div>
      <div class="layer-grid">{layer_cards}</div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <div class="eyebrow">Top 10 Dossiers</div>
          <h2>逐个地址研究</h2>
        </div>
        <p>每个卡片都给出 BubbleMaps 标签状态、角色判断、当前持仓、时间特征和一句话研究结论。</p>
      </div>
      <div class="dossier-grid">{''.join(dossier_cards)}</div>
    </section>

    {table_section(
        "BubbleMaps 标签清单",
        f"当前去重标签 {len(label_inventory)} 个。标签只能视作显式下限，未标注地址只做行为归类。",
        ["Label", "标签层", "Addr Count", "Top Rank", "Amount", "Supply Share"],
        label_rows,
    )}

    {table_section(
        "近 30 天主要从交易所提出",
        f"非基础设施地址 30 天内从交易所提出 {fmt_num(recent['recent_30d_cex_withdraw_total'], 4)} PRL。",
        ["Address", "Label", "角色判断", "30d CEX Withdraw", "Current Share"],
        exchange_withdraw_rows,
    )}

    {table_section(
        "近 30 天主要向交易所存入",
        f"非基础设施地址 30 天内向交易所存入 {fmt_num(recent['recent_30d_cex_deposit_total'], 4)} PRL。",
        ["Address", "Label", "角色判断", "30d CEX Deposit", "Current Share"],
        exchange_deposit_rows,
    )}

    <section class="panel section">
      <div class="section-head">
        <div>
          <div class="eyebrow">Reading Notes</div>
          <h2>如何读这份结构</h2>
        </div>
        <p>PRL 现在的核心不是长尾，而是 Top 10 尤其是未标注大户簇。Top 10 之外所有地址加起来只占 {esc(fmt_pct(1 - summary['snapshot']['top10_share']))}。</p>
      </div>
      <div class="layer-grid">
        {info_card("核心风险", f"Top 10 占 {fmt_pct(summary['snapshot']['top10_share'])}，筹码极度集中。", "sand")}
        {info_card("显式标签下限", f"BubbleMaps 只显式覆盖 {fmt_pct(summary['snapshot']['bubblemaps_labeled_share'])} 的供应量。", "ink")}
        {info_card("交易所侧", f"Binance 下限仓位 {fmt_pct(summary['snapshot']['bubblemaps_cex_share'])}，会影响短期流通面。", "ink")}
        {info_card("流动性侧", f"Pancake / Uniswap 等 DEX 标签合计 {fmt_pct(summary['snapshot']['bubblemaps_dex_share'])}。", "ink")}
      </div>
    </section>

    <footer class="footer">
      Source:
      <a href="{esc(source_path)}" target="_blank" rel="noreferrer">GitHub Repo</a> |
      <a href="{esc(report_md)}" target="_blank" rel="noreferrer">Markdown Report</a> |
      <a href="{esc(analysis_json)}" target="_blank" rel="noreferrer">Analysis JSON</a>
    </footer>
  </main>
</body>
</html>
"""


def main() -> None:
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(build_page(data), encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
