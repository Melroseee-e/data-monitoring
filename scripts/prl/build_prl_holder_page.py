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


def infer_summary_lines(summary: dict[str, Any]) -> list[str]:
    snapshot = summary["snapshot"]
    recent = summary["recent_activity_non_infra"]
    cohort = summary["cohort_summary_non_infra"]

    lines: list[str] = []
    top10 = snapshot["top10_share"]
    if top10 >= 0.6:
        lines.append(f"Top10 地址极度集中，占总供应 {fmt_pct(top10)}。")
    elif top10 >= 0.4:
        lines.append(f"Top10 地址集中度偏高，占总供应 {fmt_pct(top10)}。")
    else:
        lines.append(f"Top10 地址集中度中等，占总供应 {fmt_pct(top10)}。")

    label_share = snapshot["bubblemaps_labeled_share"]
    lines.append(f"BubbleMaps 显式标签覆盖 {snapshot['bubblemaps_labeled_count']} 个地址、{fmt_pct(label_share)} 的供应量，实体识别只能视作下限。")

    withdraw_total = recent["recent_30d_cex_withdraw_total"]
    deposit_total = recent["recent_30d_cex_deposit_total"]
    if withdraw_total > deposit_total * 1.2:
        lines.append(f"近 30 天从交易所提出明显强于向交易所存入，提出 {fmt_num(withdraw_total, 2)} PRL，存入 {fmt_num(deposit_total, 2)} PRL。")
    elif deposit_total > withdraw_total * 1.2:
        lines.append(f"近 30 天向交易所存入明显强于提出，存入 {fmt_num(deposit_total, 2)} PRL，提出 {fmt_num(withdraw_total, 2)} PRL。")
    else:
        lines.append(f"近 30 天交易所双向流动接近平衡，提出 {fmt_num(withdraw_total, 2)} PRL，存入 {fmt_num(deposit_total, 2)} PRL。")

    new_share = cohort.get("new_wallet", {}).get("share_supply", 0.0)
    return_share = cohort.get("return_wallet", {}).get("share_supply", 0.0)
    if new_share > return_share * 1.2:
        lines.append(f"当前非基础设施筹码几乎全部由新进地址控制，新钱包占 {fmt_pct(new_share)}。")
    elif return_share > new_share * 1.2:
        lines.append(f"回流钱包占比高于新钱包，老筹码重新活跃的迹象更强。")

    return lines


def section_table(title: str, note: str, headers: list[str], rows: list[list[str]]) -> str:
    thead = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{cell}</td>" for cell in row)
        body_rows.append(f"<tr>{cells}</tr>")
    body = "\n".join(body_rows) if body_rows else f"<tr><td colspan=\"{len(headers)}\">No data.</td></tr>"
    return f"""
    <section class="panel table-panel">
      <div class="panel-head">
        <div>
          <div class="eyebrow">Table</div>
          <h3>{esc(title)}</h3>
        </div>
        <div class="note">{esc(note)}</div>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr>{thead}</tr></thead>
          <tbody>{body}</tbody>
        </table>
      </div>
    </section>
    """


def build_page(data: dict[str, Any]) -> str:
    metadata = data["metadata"]
    summary = data["summary"]
    holders = data["holders"]

    top20 = holders[:20]
    non_infra = [row for row in holders if not row["is_cex"] and not row["is_dex"] and not row["is_contract"]]
    key_wallets = sorted(
        [row for row in non_infra if row["current_share_supply"] >= 0.0001 or row["bm_label"] or row["recent_30d_cex_withdraw_amount"] > 0 or row["recent_30d_cex_deposit_amount"] > 0],
        key=lambda row: (-float(row["current_share_supply"]), row["rank"]),
    )[:20]
    top_accumulators = sorted(
        [row for row in non_infra if row["recent_30d_netflow"] > 0],
        key=lambda row: float(row["recent_30d_netflow"]),
        reverse=True,
    )[:8]
    top_withdrawers = sorted(
        [row for row in non_infra if row["recent_30d_cex_withdraw_amount"] > 0],
        key=lambda row: float(row["recent_30d_cex_withdraw_amount"]),
        reverse=True,
    )[:8]
    top_depositors = sorted(
        [row for row in non_infra if row["recent_30d_cex_deposit_amount"] > 0],
        key=lambda row: float(row["recent_30d_cex_deposit_amount"]),
        reverse=True,
    )[:8]

    summary_lines = infer_summary_lines(summary)
    segment_rows = [
        [
            esc(name),
            esc(stats["count"]),
            esc(fmt_num(stats["amount"], 4)),
            esc(fmt_pct(stats["share_supply"])),
        ]
        for name, stats in sorted(summary["segment_summary"].items(), key=lambda item: item[1]["share_supply"], reverse=True)
    ]
    age_rows = [
        [
            esc(name),
            esc(stats["count"]),
            esc(fmt_num(stats["amount"], 4)),
            esc(fmt_pct(stats["share_supply"])),
        ]
        for name, stats in sorted(summary["age_summary_non_infra"].items(), key=lambda item: item[1]["share_supply"], reverse=True)
    ]
    cohort_rows = [
        [
            esc(name),
            esc(stats["count"]),
            esc(fmt_num(stats["amount"], 4)),
            esc(fmt_pct(stats["share_supply"])),
        ]
        for name, stats in sorted(summary["cohort_summary_non_infra"].items(), key=lambda item: item[1]["share_supply"], reverse=True)
    ]
    top20_rows = [
        [
            f"<span class='rank'>{row['rank']}</span>",
            f"<code>{esc(short_addr(row['address']))}</code>",
            esc(row["bm_label"] or "-"),
            f"<span class='seg seg-{esc(row['segment'])}'>{esc(row['segment'])}</span>",
            esc(fmt_num(row["current_amount"], 4)),
            esc(fmt_pct(row["current_share_supply"])),
        ]
        for row in top20
    ]
    key_wallet_rows = [
        [
            f"<code>{esc(short_addr(row['address']))}</code>",
            esc(row.get("bm_label") or "-"),
            f"<span class='beh beh-{esc(str(row['behavior_class']).lower())}'>{esc(row['behavior_class'])}</span>",
            esc(fmt_num(row["recent_30d_netflow"], 4)),
            esc(fmt_num(row["recent_30d_cex_withdraw_amount"], 4)),
            esc(fmt_num(row["recent_30d_cex_deposit_amount"], 4)),
            esc(fmt_pct(row["current_share_supply"])),
        ]
        for row in key_wallets
    ]
    accumulator_rows = [
        [
            f"<code>{esc(short_addr(row['address']))}</code>",
            esc(row["bm_label"] or "-"),
            esc(fmt_num(row["recent_30d_netflow"], 4)),
            esc(fmt_num(row["recent_7d_netflow"], 4)),
            esc(row["wallet_cohort"]),
            f"<span class='beh beh-{esc(str(row['behavior_class']).lower())}'>{esc(row['behavior_class'])}</span>",
        ]
        for row in top_accumulators
    ]
    withdrawer_rows = [
        [
            f"<code>{esc(short_addr(row['address']))}</code>",
            esc(row["bm_label"] or "-"),
            esc(fmt_num(row["recent_30d_cex_withdraw_amount"], 4)),
            esc(fmt_num(row["recent_30d_netflow"], 4)),
            f"<span class='beh beh-{esc(str(row['behavior_class']).lower())}'>{esc(row['behavior_class'])}</span>",
        ]
        for row in top_withdrawers
    ]
    depositor_rows = [
        [
            f"<code>{esc(short_addr(row['address']))}</code>",
            esc(row["bm_label"] or "-"),
            esc(fmt_num(row["recent_30d_cex_deposit_amount"], 4)),
            esc(fmt_num(row["recent_30d_netflow"], 4)),
            f"<span class='beh beh-{esc(str(row['behavior_class']).lower())}'>{esc(row['behavior_class'])}</span>",
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
<title>{esc(metadata['name'])} ({esc(metadata['symbol'])}) 筹码结构 | On-Chain Data Monitoring</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet">
<style>
:root {{
  --bg: #f2efe8;
  --bg-soft: #fbf8f2;
  --panel: rgba(255,255,255,0.84);
  --panel-strong: rgba(255,255,255,0.94);
  --panel-muted: rgba(255,255,255,0.74);
  --text: #17202c;
  --text-soft: #4b5a6b;
  --text-muted: #748294;
  --border: rgba(23,32,44,0.12);
  --accent: #c05f1a;
  --accent-2: #0d9c78;
  --accent-3: #1f6fe5;
  --accent-4: #bf3358;
  --shadow: 0 28px 72px rgba(26, 37, 51, 0.12);
  --shadow-soft: 0 10px 28px rgba(26, 37, 51, 0.08);
  --mono: "JetBrains Mono", monospace;
  --body: "Noto Sans SC", sans-serif;
}}
* {{ box-sizing: border-box; }}
html, body {{ margin: 0; padding: 0; }}
body {{
  min-height: 100vh;
  font-family: var(--body);
  color: var(--text);
  background:
    radial-gradient(circle at 10% 12%, rgba(192,95,26,0.12), transparent 24%),
    radial-gradient(circle at 82% 14%, rgba(13,156,120,0.10), transparent 22%),
    radial-gradient(circle at 80% 82%, rgba(31,111,229,0.10), transparent 20%),
    linear-gradient(180deg, #f8f5ef 0%, #f2efe8 46%, #e9e2d6 100%);
  -webkit-font-smoothing: antialiased;
}}
body::before {{
  content: "";
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(23,32,44,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(23,32,44,0.03) 1px, transparent 1px);
  background-size: 34px 34px;
  mask-image: linear-gradient(180deg, rgba(0,0,0,0.3), transparent 84%);
  pointer-events: none;
}}
a {{ color: inherit; }}
.shell {{
  position: relative;
  max-width: 1520px;
  margin: 0 auto;
  padding: 24px 24px 54px;
}}
.hero, .panel {{
  border: 1px solid var(--border);
  border-radius: 28px;
  background: linear-gradient(180deg, var(--panel-strong), var(--panel));
  box-shadow: var(--shadow);
}}
.hero {{
  overflow: hidden;
}}
.hero-inner, .panel-inner {{
  padding: 28px;
}}
.hero-grid {{
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(320px, 0.75fr);
  gap: 18px;
  align-items: start;
}}
.eyebrow {{
  margin: 0 0 8px;
  font-size: 12px;
  color: var(--text-soft);
  text-transform: uppercase;
  letter-spacing: 0.14em;
}}
.title {{
  margin: 0;
  font-size: clamp(34px, 4vw, 60px);
  line-height: 1.02;
  letter-spacing: -0.05em;
}}
.subtitle {{
  max-width: 860px;
  margin: 14px 0 0;
  color: var(--text-soft);
  line-height: 1.9;
  font-size: 15px;
}}
.hero-kpis {{
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}}
.meta-stack {{
  display: grid;
  gap: 14px;
}}
.pill-row {{
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}}
.pill {{
  display: inline-flex;
  gap: 8px;
  align-items: center;
  border: 1px solid var(--border);
  background: rgba(255,255,255,0.68);
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--text-soft);
}}
.pill strong {{
  font-family: var(--mono);
  color: var(--text);
  font-size: 12px;
}}
.kpi, .note-card, .summary-card {{
  border: 1px solid var(--border);
  background: rgba(255,255,255,0.72);
  border-radius: 20px;
  box-shadow: var(--shadow-soft);
}}
.kpi {{
  padding: 16px;
}}
.kpi-label {{
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-soft);
}}
.kpi-value {{
  margin-top: 10px;
  font-size: 30px;
  line-height: 1;
  font-weight: 800;
  letter-spacing: -0.05em;
}}
.kpi-sub {{
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.7;
}}
.accent-1 {{ color: var(--accent); }}
.accent-2 {{ color: var(--accent-2); }}
.accent-3 {{ color: var(--accent-3); }}
.accent-4 {{ color: var(--accent-4); }}
.layout {{
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
  gap: 18px;
  margin-top: 18px;
}}
.stack {{
  display: grid;
  gap: 18px;
}}
.panel {{
  overflow: hidden;
}}
.panel-head {{
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 18px 22px;
  border-bottom: 1px solid var(--border);
  background: rgba(250,247,241,0.82);
}}
.panel-head h3 {{
  margin: 0;
  font-size: 15px;
}}
.note {{
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.7;
  max-width: 420px;
  text-align: right;
}}
.summary-card {{
  padding: 18px;
}}
.summary-card ul {{
  margin: 0;
  padding-left: 20px;
  color: var(--text-soft);
  line-height: 1.95;
}}
.summary-card li + li {{ margin-top: 6px; }}
.source-links {{
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 14px;
}}
.source-link {{
  text-decoration: none;
  border: 1px solid var(--border);
  padding: 8px 12px;
  border-radius: 999px;
  background: rgba(255,255,255,0.62);
  color: var(--text-soft);
  font-size: 12px;
}}
.source-link:hover {{
  color: var(--text);
  transform: translateY(-1px);
}}
.bars {{
  display: grid;
  gap: 12px;
}}
.bar-row {{
  display: grid;
  gap: 6px;
}}
.bar-label {{
  display: flex;
  justify-content: space-between;
  gap: 12px;
  font-size: 12px;
  color: var(--text-soft);
}}
.bar-track {{
  height: 12px;
  background: rgba(23,32,44,0.08);
  border-radius: 999px;
  overflow: hidden;
}}
.bar-fill {{
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--accent), #eb9b55);
}}
.bar-fill.alt {{
  background: linear-gradient(90deg, var(--accent-3), #6aa6ff);
}}
.bar-fill.green {{
  background: linear-gradient(90deg, var(--accent-2), #4dd5b3);
}}
.table-wrap {{
  overflow: auto;
}}
table {{
  width: 100%;
  border-collapse: collapse;
}}
th, td {{
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  text-align: left;
  vertical-align: top;
}}
th {{
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-soft);
  background: rgba(250,247,241,0.64);
}}
td {{
  font-size: 13px;
  color: var(--text);
}}
tbody tr:hover td {{
  background: rgba(255,255,255,0.56);
}}
code {{
  font-family: var(--mono);
  font-size: 12px;
}}
.rank {{
  display: inline-flex;
  width: 28px;
  height: 28px;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(23,32,44,0.08);
  font-family: var(--mono);
  font-size: 12px;
}}
.seg, .beh {{
  display: inline-flex;
  align-items: center;
  padding: 4px 9px;
  border-radius: 999px;
  border: 1px solid transparent;
  font-size: 11px;
  line-height: 1;
  white-space: nowrap;
}}
.seg-unlabeled_whale {{ background: rgba(192,95,26,0.10); color: #9b4b11; border-color: rgba(192,95,26,0.24); }}
.seg-cex {{ background: rgba(191,51,88,0.10); color: #9d1f46; border-color: rgba(191,51,88,0.24); }}
.seg-dex {{ background: rgba(31,111,229,0.10); color: #1556b3; border-color: rgba(31,111,229,0.24); }}
.seg-labeled {{ background: rgba(13,156,120,0.10); color: #0c7c5f; border-color: rgba(13,156,120,0.24); }}
.seg-mid_wallet, .seg-tail_wallet, .seg-contract {{ background: rgba(23,32,44,0.07); color: var(--text-soft); border-color: rgba(23,32,44,0.12); }}
.beh-accumulating, .beh-cex-withdrawing {{ background: rgba(13,156,120,0.10); color: #0d7a5e; border-color: rgba(13,156,120,0.24); }}
.beh-distributing, .beh-cex-selling {{ background: rgba(191,51,88,0.10); color: #9d1f46; border-color: rgba(191,51,88,0.24); }}
.beh-mixed {{ background: rgba(31,111,229,0.10); color: #1556b3; border-color: rgba(31,111,229,0.24); }}
.beh-inactive {{ background: rgba(23,32,44,0.07); color: var(--text-soft); border-color: rgba(23,32,44,0.12); }}
.footer {{
  margin-top: 18px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.8;
  text-align: center;
}}
@media (max-width: 1080px) {{
  .hero-grid, .layout {{
    grid-template-columns: 1fr;
  }}
}}
@media (max-width: 720px) {{
  .shell {{
    padding: 14px 14px 34px;
  }}
  .hero-inner, .panel-inner {{
    padding: 18px;
  }}
  .hero-kpis {{
    grid-template-columns: 1fr;
  }}
  .panel-head {{
    display: block;
  }}
  .note {{
    margin-top: 8px;
    text-align: left;
  }}
}}
</style>
</head>
<body>
  <div class="shell">
    <section class="hero">
      <div class="hero-inner">
        <div class="hero-grid">
          <div>
            <p class="eyebrow">On-Chain Holder Structure</p>
            <h1 class="title">{esc(metadata['name'])} ({esc(metadata['symbol'])})</h1>
            <p class="subtitle">
              基于 BubbleMaps Top 500 持仓快照、BSC 全历史 Transfer 聚合与本地交易所地址表生成的公开版筹码结构页。
              BubbleMaps 仅作为显式标签源，持仓量以链上 <code>balanceOf</code> 校验后的结果为准。
            </p>
            <div class="pill-row">
              <div class="pill"><span>合约</span><strong>{esc(metadata['contract'])}</strong></div>
              <div class="pill"><span>链</span><strong>{esc(str(metadata['chain']).upper())}</strong></div>
              <div class="pill"><span>总供应</span><strong>{esc(fmt_num(metadata['total_supply'], 4))}</strong></div>
              <div class="pill"><span>更新时间</span><strong>{esc(metadata['as_of'])}</strong></div>
            </div>
          </div>
          <div class="meta-stack">
            <div class="hero-kpis">
              <div class="kpi">
                <div class="kpi-label">Top10 Share</div>
                <div class="kpi-value accent-1">{esc(fmt_pct(summary['snapshot']['top10_share']))}</div>
                <div class="kpi-sub">Top20: {esc(fmt_pct(summary['snapshot']['top20_share']))} · Top50: {esc(fmt_pct(summary['snapshot']['top50_share']))}</div>
              </div>
              <div class="kpi">
                <div class="kpi-label">Labeled Supply</div>
                <div class="kpi-value accent-2">{esc(fmt_pct(summary['snapshot']['bubblemaps_labeled_share']))}</div>
                <div class="kpi-sub">{esc(summary['snapshot']['bubblemaps_labeled_count'])} 个 BubbleMaps 显式标签地址</div>
              </div>
              <div class="kpi">
                <div class="kpi-label">30d CEX Withdraw</div>
                <div class="kpi-value accent-3">{esc(fmt_num(summary['recent_activity_non_infra']['recent_30d_cex_withdraw_total'], 0))}</div>
                <div class="kpi-sub">非基础设施地址近 30 天从交易所提出 PRL</div>
              </div>
              <div class="kpi">
                <div class="kpi-label">30d CEX Deposit</div>
                <div class="kpi-value accent-4">{esc(fmt_num(summary['recent_activity_non_infra']['recent_30d_cex_deposit_total'], 0))}</div>
                <div class="kpi-sub">非基础设施地址近 30 天向交易所存入 PRL</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <div class="layout">
      <div class="stack">
        <section class="panel">
          <div class="panel-head">
            <div>
              <div class="eyebrow">Takeaways</div>
              <h3>核心结论</h3>
            </div>
            <div class="note">当前页为公开版 HTML。研究原始 Markdown 与 JSON 产物链接放在右侧。</div>
          </div>
          <div class="panel-inner summary-card">
            <ul>
              {"".join(f"<li>{esc(line)}</li>" for line in summary_lines)}
            </ul>
          </div>
        </section>

        {section_table("Segment Summary", "按当前持仓分层。BubbleMaps 仅提供标签，排序与金额已按链上余额重排。", ["Segment", "Addr Count", "Amount", "Supply Share"], segment_rows)}
        {section_table("Top 20 Holders", "Top holders after on-chain balance refresh.", ["Rank", "Address", "BubbleMaps Label", "Segment", "Amount", "Share"], top20_rows)}
        {section_table("Holder Age Buckets", "仅统计非基础设施地址。", ["Age Bucket", "Addr Count", "Amount", "Supply Share"], age_rows)}
        {section_table("Wallet Cohorts", "new_wallet / return_wallet / existing_wallet 口径见研究脚本。", ["Cohort", "Addr Count", "Amount", "Supply Share"], cohort_rows)}
        {section_table("Key Wallets", "按当前份额、BubbleMaps 标签以及近 30 天交易所双向流动筛选。", ["Address", "Label", "Behavior", "30d Netflow", "30d CEX Withdraw", "30d CEX Deposit", "Current Share"], key_wallet_rows)}
        {section_table("Top 30d Accumulators", "非基础设施地址近 30 天净流入。", ["Address", "Label", "30d Netflow", "7d Netflow", "Cohort", "Behavior"], accumulator_rows)}
        {section_table("Top 30d Exchange Withdrawers", "近 30 天从交易所提出 PRL 最多的地址。", ["Address", "Label", "30d CEX Withdraw", "30d Netflow", "Behavior"], withdrawer_rows)}
        {section_table("Top 30d Exchange Depositors", "近 30 天向交易所存入 PRL 最多的地址。", ["Address", "Label", "30d CEX Deposit", "30d Netflow", "Behavior"], depositor_rows)}
      </div>

      <div class="stack">
        <section class="panel">
          <div class="panel-head">
            <div>
              <div class="eyebrow">Concentration</div>
              <h3>集中度条形图</h3>
            </div>
            <div class="note">横轴按总供应占比。</div>
          </div>
          <div class="panel-inner">
            <div class="bars">
              <div class="bar-row">
                <div class="bar-label"><span>Top 10</span><strong>{esc(fmt_pct(summary['snapshot']['top10_share']))}</strong></div>
                <div class="bar-track"><div class="bar-fill" style="width:{summary['snapshot']['top10_share'] * 100:.2f}%"></div></div>
              </div>
              <div class="bar-row">
                <div class="bar-label"><span>Top 20</span><strong>{esc(fmt_pct(summary['snapshot']['top20_share']))}</strong></div>
                <div class="bar-track"><div class="bar-fill alt" style="width:{summary['snapshot']['top20_share'] * 100:.2f}%"></div></div>
              </div>
              <div class="bar-row">
                <div class="bar-label"><span>Top 50</span><strong>{esc(fmt_pct(summary['snapshot']['top50_share']))}</strong></div>
                <div class="bar-track"><div class="bar-fill green" style="width:{summary['snapshot']['top50_share'] * 100:.2f}%"></div></div>
              </div>
              <div class="bar-row">
                <div class="bar-label"><span>BubbleMaps Labeled</span><strong>{esc(fmt_pct(summary['snapshot']['bubblemaps_labeled_share']))}</strong></div>
                <div class="bar-track"><div class="bar-fill alt" style="width:{summary['snapshot']['bubblemaps_labeled_share'] * 100:.2f}%"></div></div>
              </div>
              <div class="bar-row">
                <div class="bar-label"><span>BubbleMaps CEX</span><strong>{esc(fmt_pct(summary['snapshot']['bubblemaps_cex_share']))}</strong></div>
                <div class="bar-track"><div class="bar-fill" style="width:{summary['snapshot']['bubblemaps_cex_share'] * 100:.2f}%"></div></div>
              </div>
            </div>
          </div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <div>
              <div class="eyebrow">Method</div>
              <h3>方法与限制</h3>
            </div>
            <div class="note">这部分决定如何阅读页面结论。</div>
          </div>
          <div class="panel-inner summary-card">
            <ul>
              <li>BubbleMaps 只作为显式标签源，不对无标签地址发明实体名。</li>
              <li>BubbleMaps 快照与链上余额出现漂移时，页面自动采用链上 <code>balanceOf</code> 重算当前持仓。</li>
              <li>交易所方向识别使用本地 exchange registry，仅用于判断提出 / 存入，不给无标签地址公开补名。</li>
              <li>本页未包含成本、PNL 与逐笔成交归因，因为当前环境下没有可用的 PRL 历史价格账本。</li>
            </ul>
          </div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <div>
              <div class="eyebrow">Artifacts</div>
              <h3>源文件</h3>
            </div>
            <div class="note">GitHub Pages 会直接托管这些静态产物。</div>
          </div>
          <div class="panel-inner summary-card">
            <div class="source-links">
              <a class="source-link" href="{report_md}">Markdown 报告</a>
              <a class="source-link" href="{analysis_json}">Analysis JSON</a>
              <a class="source-link" href="{source_path}">GitHub Repo</a>
              <a class="source-link" href="./pump_behavior_chart.html">返回公开页</a>
            </div>
          </div>
        </section>
      </div>
    </div>

    <div class="footer">
      Generated from <code>data/prl/derived/prl_holder_analysis.json</code> by <code>scripts/prl/build_prl_holder_page.py</code>.
    </div>
  </div>
</body>
</html>
"""


def main() -> None:
    data = json.loads(INPUT_FILE.read_text(encoding="utf-8"))
    OUTPUT_FILE.write_text(build_page(data), encoding="utf-8")
    print(f"wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
