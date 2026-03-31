#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]
ANALYSIS_PATH = BASE_DIR / "data" / "prl" / "derived" / "prl_holder_analysis.json"
OUT_HTML = BASE_DIR / "web" / "prl_holder_structure.html"

DOC_LINKS = {
    "token_overview": "https://perle.gitbook.io/perle-docs/tokenomics/token-overview",
    "token_vesting": "https://perle.gitbook.io/perle-docs/tokenomics/token-vesting",
    "token_utility": "https://perle.gitbook.io/perle-docs/tokenomics/prl-token-utility-and-purpose",
    "audit": "https://perle.gitbook.io/perle-docs/perle-prl-token-passes-security-audit-with-halborn",
    "funding": "https://www.perle.ai/resources/perle-secures-9-million-seed-round-led-by-framework-ventures-to-launch-an-ai-data-training-platform-powered-by-web3",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_num(value: float, digits: int = 2) -> str:
    return f"{float(value):,.{digits}f}"


def fmt_pct(value: float, digits: int = 2) -> str:
    return f"{float(value) * 100:.{digits}f}%"


def short_addr(address: str) -> str:
    return f"{address[:6]}...{address[-4:]}" if len(address) > 12 else address


def solscan_link(address: str) -> str:
    safe = html.escape(address)
    return f'<a href="https://solscan.io/account/{safe}" target="_blank" rel="noreferrer">{safe}</a>'


def bucket_label(bucket: str) -> str:
    return {
        "official_public": "已公开官方",
        "official_inferred": "高概率官方",
        "exchange": "交易所",
        "dex_pool": "DEX 池子",
        "whale": "大户",
        "unknown": "其他/未定",
    }.get(bucket, bucket)


def bucket_class(bucket: str) -> str:
    return {
        "official_public": "badge badge-official",
        "official_inferred": "badge badge-official-soft",
        "exchange": "badge badge-exchange",
        "dex_pool": "badge badge-dex",
        "whale": "badge badge-whale",
        "unknown": "badge badge-unknown",
    }.get(bucket, "badge badge-unknown")


def card(title: str, value: str, note: str) -> str:
    return f"""
    <section class="stat-card">
      <div class="stat-kicker">{html.escape(title)}</div>
      <div class="stat-value">{html.escape(value)}</div>
      <div class="stat-note">{html.escape(note)}</div>
    </section>
    """


def render_bucket_strip(rows: list[dict[str, Any]]) -> str:
    items = []
    for row in rows:
        items.append(
            f"""
            <div class="bucket-strip-item">
              <span class="{bucket_class(row['bucket'])}">{html.escape(row['bucket_label'])}</span>
              <strong>{fmt_pct(row['share_of_supply'], 2)}</strong>
              <span>{row['address_count']} 个地址</span>
            </div>
            """
        )
    return "\n".join(items)


def render_top10_table(rows: list[dict[str, Any]]) -> str:
    out = []
    for row in rows:
        out.append(
            f"""
            <tr>
              <td>{row['rank']}</td>
              <td class="mono">{solscan_link(row['address'])}</td>
              <td>{fmt_num(row['amount'], 2)}</td>
              <td>{fmt_pct(row['share'], 3)}</td>
              <td><span class="{bucket_class(row['resolved_bucket'])}">{bucket_label(row['resolved_bucket'])}</span></td>
              <td>{html.escape(row.get('top_holder_role') or '—')}</td>
              <td>{html.escape(row.get('resolved_entity_name') or '—')}</td>
            </tr>
            """
        )
    return "\n".join(out)


def render_profiles(rows: list[dict[str, Any]]) -> str:
    cards = []
    for row in rows:
        cards.append(
            f"""
            <article class="profile-card">
              <div class="profile-head">
                <div>
                  <div class="profile-rank">Top {row['rank']}</div>
                  <div class="profile-address mono">{solscan_link(row['address'])}</div>
                </div>
                <div class="profile-metrics">
                  <span class="{bucket_class(row['resolved_bucket'])}">{bucket_label(row['resolved_bucket'])}</span>
                  <strong>{fmt_pct(row['share'], 3)}</strong>
                </div>
              </div>
              <div class="profile-role">{html.escape(row.get('top_holder_role') or '—')}</div>
              <div class="profile-grid">
                <div><span>持仓</span>{fmt_num(row['amount'], 2)} PRL</div>
                <div><span>首次活动</span>{html.escape(row.get('first_activity_date') or '—')}</div>
                <div><span>BubbleMaps 度数</span>{row.get('degree', 0)}</div>
                <div><span>标签</span>{html.escape(row.get('resolved_entity_name') or '未标注')}</div>
              </div>
              <p class="profile-evidence">{html.escape(row.get('evidence_summary') or row.get('classification_reason') or '')}</p>
            </article>
            """
        )
    return "\n".join(cards)


def render_label_rows(rows: list[dict[str, Any]]) -> str:
    out = []
    for row in rows[:18]:
        out.append(
            f"""
            <tr>
              <td>{html.escape(row['source'])}</td>
              <td>{html.escape(row['label'])}</td>
              <td>{row['address_count']}</td>
              <td>{fmt_pct(row['share_of_supply'], 3)}</td>
            </tr>
            """
        )
    return "\n".join(out)


def render_docs_table(vesting_rows: list[dict[str, Any]]) -> str:
    out = []
    for row in vesting_rows:
        out.append(
            f"""
            <tr>
              <td>{html.escape(row['bucket'])}</td>
              <td>{row['allocation_pct']:.2f}%</td>
              <td>{html.escape(row['tge_unlock'])}</td>
              <td>{html.escape(row['cliff'])}</td>
              <td>{html.escape(row['vesting'])}</td>
            </tr>
            """
        )
    return "\n".join(out)


def build_html(data: dict[str, Any]) -> str:
    summary = data["summary"]
    top10 = data["top10_holders"]
    docs = data["docs_facts"]
    official_public = next(row for row in top10 if row["address"] == docs["metadata_update_authority"])
    first_exchange = summary.get("first_exchange_rank") or "未识别"
    first_dex = summary.get("first_dex_rank") or "未识别"

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>PRL Solana Top 10 Holder Structure</title>
  <style>
    :root {{
      --bg: #f4efe6;
      --paper: rgba(255,255,255,0.82);
      --ink: #15110d;
      --muted: #695f56;
      --line: rgba(28, 20, 14, 0.10);
      --official: #0c6b58;
      --official-soft: #2d9380;
      --exchange: #1859a8;
      --dex: #9b5417;
      --whale: #7d1d1d;
      --unknown: #6b7280;
      --accent: #d9b76a;
      --shadow: 0 18px 50px rgba(41, 26, 18, 0.10);
      --radius: 24px;
      --mono: "SFMono-Regular", "JetBrains Mono", Menlo, monospace;
      --body: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
    }}

    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: var(--body);
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(217,183,106,0.30), transparent 34%),
        radial-gradient(circle at bottom right, rgba(12,107,88,0.18), transparent 30%),
        linear-gradient(180deg, #f8f4ee 0%, var(--bg) 100%);
    }}
    a {{ color: inherit; }}
    .page {{
      width: min(1220px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 40px 0 80px;
    }}
    .hero {{
      background: linear-gradient(135deg, rgba(255,255,255,0.92), rgba(255,248,236,0.86));
      border: 1px solid var(--line);
      border-radius: 34px;
      box-shadow: var(--shadow);
      padding: 34px;
      position: relative;
      overflow: hidden;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      right: -40px;
      top: -40px;
      width: 220px;
      height: 220px;
      background: radial-gradient(circle, rgba(12,107,88,0.18), transparent 68%);
      pointer-events: none;
    }}
    .eyebrow {{
      font-size: 13px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 12px;
    }}
    h1 {{
      font-size: clamp(32px, 5vw, 58px);
      line-height: 0.98;
      margin: 0 0 14px;
      max-width: 760px;
    }}
    .hero-copy {{
      max-width: 820px;
      font-size: 18px;
      line-height: 1.65;
      color: var(--muted);
    }}
    .hero-meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 14px;
      margin-top: 26px;
    }}
    .meta-card {{
      background: rgba(255,255,255,0.72);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px 16px;
    }}
    .meta-card span {{
      display: block;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.10em;
      color: var(--muted);
      margin-bottom: 6px;
    }}
    .mono {{ font-family: var(--mono); font-size: 13px; word-break: break-all; }}
    .section {{
      margin-top: 28px;
      background: var(--paper);
      backdrop-filter: blur(14px);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 28px;
    }}
    .section h2 {{
      margin: 0 0 8px;
      font-size: 28px;
    }}
    .section-intro {{
      margin: 0 0 18px;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.7;
    }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 14px;
      margin-top: 24px;
    }}
    .stat-card {{
      background: rgba(255,255,255,0.8);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
    }}
    .stat-kicker {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.10em;
    }}
    .stat-value {{
      font-size: 34px;
      line-height: 1;
      margin: 10px 0 8px;
    }}
    .stat-note {{
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }}
    .bucket-strip {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 12px;
    }}
    .bucket-strip-item {{
      padding: 16px;
      border-radius: 16px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.72);
      display: flex;
      flex-direction: column;
      gap: 8px;
    }}
    .bucket-strip-item strong {{
      font-size: 28px;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      width: fit-content;
      padding: 6px 10px;
      border-radius: 999px;
      font-size: 12px;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      font-weight: 700;
      color: white;
    }}
    .badge-official {{ background: var(--official); }}
    .badge-official-soft {{ background: var(--official-soft); }}
    .badge-exchange {{ background: var(--exchange); }}
    .badge-dex {{ background: var(--dex); }}
    .badge-whale {{ background: var(--whale); }}
    .badge-unknown {{ background: var(--unknown); }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}
    th, td {{
      text-align: left;
      padding: 12px 10px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .callout-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 14px;
      margin-top: 16px;
    }}
    .callout {{
      border-radius: 18px;
      border: 1px solid var(--line);
      padding: 18px;
      background: rgba(255,255,255,0.72);
    }}
    .callout h3 {{
      margin: 0 0 10px;
      font-size: 18px;
    }}
    .callout p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.65;
    }}
    .profiles {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
    }}
    .profile-card {{
      border-radius: 22px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.76);
      padding: 18px;
    }}
    .profile-head {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: flex-start;
      margin-bottom: 14px;
    }}
    .profile-rank {{
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 8px;
    }}
    .profile-address {{
      font-size: 13px;
    }}
    .profile-metrics {{
      display: flex;
      flex-direction: column;
      gap: 8px;
      align-items: flex-end;
    }}
    .profile-metrics strong {{
      font-size: 22px;
    }}
    .profile-role {{
      font-size: 19px;
      margin-bottom: 12px;
    }}
    .profile-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px 14px;
      margin-bottom: 14px;
      color: var(--muted);
      font-size: 14px;
    }}
    .profile-grid span {{
      display: block;
      color: var(--ink);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.07em;
      margin-bottom: 3px;
    }}
    .profile-evidence {{
      margin: 0;
      color: var(--muted);
      line-height: 1.7;
    }}
    .footer-note {{
      margin-top: 18px;
      font-size: 14px;
      color: var(--muted);
      line-height: 1.7;
    }}
    @media (max-width: 720px) {{
      .page {{ width: min(100vw - 20px, 1220px); padding-top: 18px; }}
      .hero, .section {{ padding: 20px; border-radius: 22px; }}
      .profile-grid {{ grid-template-columns: 1fr; }}
      table {{ display: block; overflow-x: auto; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <section class="hero">
      <div class="eyebrow">Perle / PRL • Solana Holder Structure</div>
      <h1>Top 10 基本不是交易所，而是项目侧与大户侧钱包。</h1>
      <p class="hero-copy">
        当前 PRL 的关键问题不是“CEX 上有多少货”，而是 Top 10 里哪些地址可以直接确认属于官方，哪些只是高概率官方托管层，哪些其实是未标注大户。
        这页把 Top 10 分成四层：官方、交易所、DEX 池子、大户，并把每个 Top 10 的证据链单独展开。
      </p>
      <div class="hero-meta">
        <div class="meta-card">
          <span>Solana Mint</span>
          <div class="mono">{solscan_link(data['metadata']['contract'])}</div>
        </div>
        <div class="meta-card">
          <span>公开官方地址</span>
          <div class="mono">{solscan_link(docs['metadata_update_authority'])}</div>
        </div>
        <div class="meta-card">
          <span>TGE / Supply</span>
          <div>{docs['tge_date']} / {docs['total_supply_text']}</div>
        </div>
        <div class="meta-card">
          <span>资料来源</span>
          <div><a href="{DOC_LINKS['token_overview']}" target="_blank" rel="noreferrer">Docs</a> / <a href="{DOC_LINKS['audit']}" target="_blank" rel="noreferrer">Audit</a> / <a href="{DOC_LINKS['token_vesting']}" target="_blank" rel="noreferrer">Vesting</a></div>
        </div>
      </div>
      <div class="stats">
        {card("Top 10 占比", fmt_pct(summary['top10_share'], 2), "前十名合计控制的供应量")}
        {card("Top 5 占比", fmt_pct(summary['top5_share'], 2), "前五名已经足以决定盘面结构")}
        {card("首个交易所排名", str(first_exchange), "Top 10 内没有交易所地址")}
        {card("首个 DEX 排名", str(first_dex), "Top 10 内没有 DEX 池子")}
      </div>
    </section>

    <section class="section">
      <h2>Top 10 分层总览</h2>
      <p class="section-intro">
        这四层是页面的主阅读顺序。先看官方，再看大户，然后看交易所和 DEX。当前 Top 10 里最重要的事实是：
        <strong>没有交易所，也没有池子；主要是官方相关地址和未标注大户。</strong>
      </p>
      <div class="bucket-strip">
        {render_bucket_strip(data['top10_layer_summary'])}
      </div>
      <div class="callout-grid">
        <div class="callout">
          <h3>已公开官方</h3>
          <p>目前只有一个硬证据地址进入 Top 10：{html.escape(short_addr(docs['metadata_update_authority']))}。它来自官方 audit，而不是链上行为猜测。</p>
        </div>
        <div class="callout">
          <h3>高概率官方</h3>
          <p>Top 10 里还有至少两类地址带有官方基础设施特征：一个被 Arkham 识别成 Squads Vault，另一个是明显程序控制账户。</p>
        </div>
        <div class="callout">
          <h3>大户层</h3>
          <p>第 1、2 名两只无标签大仓合计已超过 59%。它们才是 PRL 当前筹码最需要盯的风险源。</p>
        </div>
      </div>
    </section>

    <section class="section">
      <h2>Top 10 表</h2>
      <p class="section-intro">
        这张表只回答一个问题：Top 10 每个地址现在到底属于哪一层。
      </p>
      <table>
        <thead>
          <tr>
            <th>Rank</th>
            <th>地址</th>
            <th>持仓</th>
            <th>占总量</th>
            <th>归类</th>
            <th>角色</th>
            <th>标签</th>
          </tr>
        </thead>
        <tbody>
          {render_top10_table(top10)}
        </tbody>
      </table>
    </section>

    <section class="section">
      <h2>Top 10 单地址画像</h2>
      <p class="section-intro">
        每个 Top 10 地址都拆成一张卡。这里不只看 label，还把第一次活动时间、BubbleMaps 关系度和链上账户形态一起放进来，避免把静态分仓看成自然大户。
      </p>
      <div class="profiles">
        {render_profiles(top10)}
      </div>
    </section>

    <section class="section">
      <h2>官方地址证据链</h2>
      <p class="section-intro">
        “官方”被拆成两层：已公开官方只接受 docs / audit 明示；高概率官方则保留为推测层，不和公开事实混写。
      </p>
      <div class="callout-grid">
        <div class="callout">
          <h3>已公开官方</h3>
          <p>
            Metadata update authority 是 <span class="mono">{solscan_link(docs['metadata_update_authority'])}</span>，
            这是官方 audit 页面直接写明的地址。它现在也是第 7 大持仓，持有 {fmt_pct(official_public['share'], 3)}。
          </p>
        </div>
        <div class="callout">
          <h3>高概率官方</h3>
          <p>
            第 9 名被 Arkham 标成 Squads Vault “SGL Marketing Lumen ServiceCo”；第 5 名是程序控制账户，
            且第一次活动紧贴 TGE。两者都更像项目侧基础设施，而不是普通大户。
          </p>
        </div>
        <div class="callout">
          <h3>还不能直接判官方</h3>
          <p>
            其余几只大仓虽然集中度极高，但如果没有公开文档、明确标签或明显程序控制证据，页面一律继续放在“大户层”。
          </p>
        </div>
      </div>
    </section>

    <section class="section">
      <h2>交易所与 DEX 池子</h2>
      <p class="section-intro">
        这部分的重点不是 Top 10，而是提醒你：交易所和池子并不主导当前顶层筹码。
      </p>
      <div class="callout-grid">
        <div class="callout">
          <h3>交易所</h3>
          <p>BubbleMaps / Arkham 目前把 Bitget、Coinbase、Gate、MEXC、Kucoin 识别在 Top 500 内，但最早也只排到第 {first_exchange} 名，合计下限仓位约 {fmt_pct(summary['exchange_share'], 3)}。</p>
        </div>
        <div class="callout">
          <h3>DEX 池子</h3>
          <p>当前 DEX / LP 不在 Top 10，整体占比也很低。这意味着顶层筹码不是“池子锁仓”，而是项目侧和大额钱包自持。</p>
        </div>
        <div class="callout">
          <h3>市场含义</h3>
          <p>如果后面盘面松动，最该盯的是 Top 10 大仓是否开始分拆转移，而不是先去盯交易所库存。</p>
        </div>
      </div>
    </section>

    <section class="section">
      <h2>Tokenomics 对照</h2>
      <p class="section-intro">
        Docs 明确把 PRL 定义为 Solana 原生 token。下面这张表是官方释放口径，用来约束 Top 10 的解释范围，避免把 TGE 初期的大额分仓误判成异常操盘。
      </p>
      <table>
        <thead>
          <tr>
            <th>Bucket</th>
            <th>Allocation</th>
            <th>TGE Unlock</th>
            <th>Cliff</th>
            <th>Vesting</th>
          </tr>
        </thead>
        <tbody>
          {render_docs_table(docs['vesting'])}
        </tbody>
      </table>
      <p class="footer-note">
        当前 Top 10 结构与 docs 的一个关键吻合点是：交易所和池子都没有占据顶层，说明筹码上层更像分配/托管层而不是二级市场流动层。
      </p>
    </section>

    <section class="section">
      <h2>Label Inventory</h2>
      <p class="section-intro">
        这里汇总了目前抓到的主要标签。高可读页面只解释 Top 10，但底层 label 清单依然保留，方便继续深挖。
      </p>
      <table>
        <thead>
          <tr>
            <th>来源</th>
            <th>标签</th>
            <th>地址数</th>
            <th>占总量</th>
          </tr>
        </thead>
        <tbody>
          {render_label_rows(data['label_inventory'])}
        </tbody>
      </table>
      <p class="footer-note">
        数据源说明：持仓快照来自 BubbleMaps Top 500；实体标签由 Arkham 补充；官方口径来自 Perle docs 与 audit 页面。Solscan 仅用于外链跳转，不作为本页结构化标签源。
      </p>
    </section>
  </main>
</body>
</html>
"""


def main() -> None:
    data = load_json(ANALYSIS_PATH)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(build_html(data), encoding="utf-8")
    print(f"Wrote {OUT_HTML}")


if __name__ == "__main__":
    main()
