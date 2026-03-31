#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_FILE = BASE_DIR / "data" / "prl" / "derived" / "prl_holder_analysis.json"
OUTPUT_FILE = BASE_DIR / "web" / "prl_holder_structure.html"


def fmt_num(value: float, decimals: int = 2) -> str:
    return f"{float(value):,.{decimals}f}"


def fmt_pct(value: float, decimals: int = 2) -> str:
    return f"{float(value) * 100:.{decimals}f}%"


def short_addr(address: str, left: int = 6, right: int = 4) -> str:
    if len(address) <= left + right:
        return address
    return f"{address[:left]}...{address[-right:]}"


def esc(value: Any) -> str:
    return html.escape(str(value))


def solscan_url(address: str) -> str:
    return f"https://solscan.io/account/{address}"


def bucket_label(bucket: str) -> str:
    return {
        "official_public": "已公开官方",
        "official_inferred": "高概率官方",
        "exchange": "交易所",
        "dex_pool": "DEX 池子",
        "whale": "大户",
        "unknown": "其他/未定",
    }.get(bucket, bucket)


def holder_title(row: dict[str, Any]) -> str:
    return row.get("resolved_entity_name") or "No BubbleMaps / Arkham label"


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


def build_page(data: dict[str, Any]) -> str:
    metadata = data["metadata"]
    summary = data["summary"]
    docs = data["docs_facts"]
    top10 = data["top10_holders"]
    holders = data["holders"]
    label_inventory = data["label_inventory"]
    top10_layers = data["top10_layer_summary"]

    symbol = metadata["token"]
    name = metadata["name"]
    generated_at = metadata["generated_at"]
    total_supply = metadata["total_supply"]

    top11_50_share = sum(row["share"] for row in holders if 11 <= int(row["rank"]) <= 50)
    unlabeled_top10_share = sum(row["share"] for row in top10 if row["resolved_bucket"] == "whale")
    official_top10_share = sum(row["share"] for row in top10 if row["resolved_bucket"] in {"official_public", "official_inferred"})

    official_top10 = [row for row in top10 if row["resolved_bucket"] in {"official_public", "official_inferred"}]
    exchange_rows = [row for row in holders if row["resolved_bucket"] == "exchange"][:8]
    fresh_rows = data["fresh_wallet_cluster"][:8]

    stat_cards = "".join([
        stat_card("Top 10 Share", fmt_pct(summary["top10_share"]), "Top 10 仍然决定当前绝大多数流通盘。"),
        stat_card("Whale Layer", fmt_pct(unlabeled_top10_share), "Top 10 内未标注大户层占比。", "cool"),
        stat_card("Official Layer", fmt_pct(official_top10_share), "已公开官方 + 高概率官方合计。", "blue"),
        stat_card("CEX Lower Bound", fmt_pct(summary["exchange_share"]), "BubbleMaps / Arkham 当前识别到的交易所下限仓位。", "rose"),
    ])

    layer_cards = "".join(
        info_card(
            item["bucket_label"],
            (
                f"<strong>{fmt_pct(item['share_of_supply'])}</strong> of supply, "
                f"{item['address_count']} addresses in Top 10."
            ),
            "sand" if item["bucket"] == "whale" else "ink",
        )
        for item in top10_layers
    )

    dossier_cards = []
    for row in top10:
        facts = [
            ("Amount", f"{fmt_num(row['amount'], 2)} PRL"),
            ("First Seen", row.get("first_activity_date") or "-"),
            ("Degree", str(row.get("degree", 0))),
            ("Bucket", bucket_label(row["resolved_bucket"])),
        ]
        facts_html = "".join(
            f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>"
            for k, v in facts
        )
        label = holder_title(row)
        tags = [
            bucket_label(row["resolved_bucket"]),
            row.get("top_holder_role") or "Top holder",
            f"Confidence: {row.get('confidence', 'n/a')}",
        ]
        tag_html = "".join(f"<span class=\"pill\">{esc(tag)}</span>" for tag in tags if tag)
        dossier_cards.append(f"""
        <article class="dossier">
          <div class="dossier-top">
            <div class="rank-chip">#{row['rank']}</div>
            <a class="address-link" href="{esc(solscan_url(row['address']))}" target="_blank" rel="noreferrer">{esc(short_addr(row['address']))}</a>
          </div>
          <div class="dossier-label">{esc(label)}</div>
          <div class="pill-row">{tag_html}</div>
          <div class="dossier-metric">{esc(fmt_pct(row['share']))}</div>
          <div class="dossier-sub">Current share of total supply</div>
          <dl class="facts">{facts_html}</dl>
          <p class="note">{esc(row.get('evidence_summary') or row.get('classification_reason') or '')}</p>
        </article>
        """)

    label_rows = [
        [
            esc(item["label"]),
            esc(item["source"]),
            esc(item["address_count"]),
            esc(fmt_pct(item["share_of_supply"], 3)),
            esc(", ".join(short_addr(addr) for addr in item["sample_addresses"][:3])),
        ]
        for item in label_inventory[:20]
    ]

    official_rows = [
        [
            f"<code>{esc(short_addr(row['address']))}</code>",
            esc(bucket_label(row["resolved_bucket"])),
            esc(row.get("resolved_entity_name") or "-"),
            esc(fmt_pct(row["share"], 3)),
            esc(row.get("classification_reason") or "-"),
        ]
        for row in official_top10
    ]

    exchange_table_rows = [
        [
            f"<code>{esc(short_addr(row['address']))}</code>",
            esc(row.get("resolved_entity_name") or row.get("bubblemaps_label") or "-"),
            esc(fmt_pct(row["share"], 3)),
            esc(str(row["rank"])),
            esc(row.get("arkham_entity_name") or row.get("arkham_label") or "-"),
        ]
        for row in exchange_rows
    ]

    fresh_table_rows = [
        [
            f"<code>{esc(short_addr(row['address']))}</code>",
            esc(str(row["rank"])),
            esc(fmt_pct(row["share"], 3)),
            esc(row.get("first_activity_date") or "-"),
        ]
        for row in fresh_rows
    ]

    source_path = "https://github.com/Melroseee-e/data-monitoring"
    report_md = "../data/prl/reports/prl_holder_structure_report.md"
    analysis_json = "../data/prl/derived/prl_holder_analysis.json"

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
            这份页面沿用上一版 intelligence UI，只重写内容口径。
            现在研究对象只保留 Solana 主部署，Top 10 当前合计控制
            <strong>{esc(fmt_pct(summary['top10_share']))}</strong> 的总供应。
            重点不是长尾，而是把 Top 10 里的官方、高概率官方、大户、交易所和 DEX 层彻底分清楚。
          </p>
        </div>
        <div class="meta-box">
          <div class="meta-line">
            <span class="meta-pill">SOL <code>{esc(short_addr(metadata['contract'], 10, 8))}</code></span>
            <span class="meta-pill">Authority <code>{esc(short_addr(docs['metadata_update_authority'], 10, 8))}</code></span>
          </div>
          <div class="meta-line">
            <span class="meta-pill">Total Supply <strong>{esc(fmt_num(total_supply, 0))}</strong></span>
            <span class="meta-pill">Snapshot <strong>Top 500</strong></span>
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
          <div class="eyebrow">Control Layers</div>
          <h2>Top 10 分层</h2>
        </div>
        <p>这版直接用你之前那套 UI 去读 Solana PRL。先看 Top 10 的层，再看每个地址的 dossier，不把 500 个地址平铺稀释掉。</p>
      </div>
      <div class="layer-grid">{layer_cards}</div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <div class="eyebrow">Top 10 Dossiers</div>
          <h2>逐个地址研究</h2>
        </div>
        <p>每个卡片都保留上一版的情报档案式阅读方式，但内容改成 Solana 版本的官方识别、账户形态和证据摘要。</p>
      </div>
      <div class="dossier-grid">{''.join(dossier_cards)}</div>
    </section>

    {table_section(
        "官方地址与高概率官方",
        f"公开官方现在只有 1 个硬证据地址；其余只放进高概率官方层，不和公开事实混写。",
        ["Address", "Bucket", "Label", "Share", "Reason"],
        official_rows,
    )}

    {table_section(
        "BubbleMaps / Arkham 标签清单",
        f"当前汇总前 20 个主要标签，方便继续追地址，不再把标签当成唯一判断依据。",
        ["Label", "Source", "Addr Count", "Supply Share", "Samples"],
        label_rows,
    )}

    {table_section(
        "交易所层样本",
        f"交易所不在 Top 10；第一个交易所只排到第 {summary['first_exchange_rank']} 名，当前下限仓位约 {fmt_pct(summary['exchange_share'])}。",
        ["Address", "Label", "Share", "Rank", "Entity"],
        exchange_table_rows,
    )}

    {table_section(
        "Fresh Static Wallets",
        "这些地址更像 TGE 后的单跳静态分仓，不像交易所或 DEX 池子。",
        ["Address", "Rank", "Share", "First Activity"],
        fresh_table_rows,
    )}

    <section class="panel section">
      <div class="section-head">
        <div>
          <div class="eyebrow">Reading Notes</div>
          <h2>如何读这份结构</h2>
        </div>
        <p>你之前那版 UI 的重点就是“快速看懂控制层”。这版也保持一样：先官方，再大户，再交易所和 DEX。Top 10 之外所有地址加起来只占 {esc(fmt_pct(1 - summary['top10_share']))}。</p>
      </div>
      <div class="layer-grid">
        {info_card("官方口径", f"Docs 明确把 PRL 定义在 Solana，公开 authority 地址是 {short_addr(docs['metadata_update_authority'])}。", "sand")}
        {info_card("核心风险", f"Top 10 占 {fmt_pct(summary['top10_share'])}，而且其中大户层就有 {fmt_pct(unlabeled_top10_share)}。", "ink")}
        {info_card("交易所侧", f"交易所下限仓位目前只有 {fmt_pct(summary['exchange_share'])}，并不主导顶层筹码。", "ink")}
        {info_card("流动性侧", f"DEX / LP 下限仓位约 {fmt_pct(summary['dex_share'])}，不在 Top 10 主控制层。", "ink")}
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
