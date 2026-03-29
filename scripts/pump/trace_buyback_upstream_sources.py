#!/usr/bin/env python3
"""Trace upstream sources feeding the known PUMP custody feeder token accounts."""

from __future__ import annotations

import json
import os
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


BASE_DIR = Path(__file__).resolve().parents[2]
OUT_RAW = BASE_DIR / "data" / "pump" / "raw"
OUT_DERIVED = BASE_DIR / "data" / "pump" / "derived"
OUT_REPORTS = BASE_DIR / "data" / "pump" / "reports"

PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"

CHAINS = [
    {
        "chain_id": "g8_chain",
        "custody_owner": "G8CcfRffqZWHSAQJXLDfwbAkGE95SddUqVXnTrL4kqjm",
        "custody_token_account": "HdtUyEC7TeLGrA7ddRRJWM6nUYk5UZsL9pJuWnXAFQ32",
        "feeder_owner": "99mRw3EzdJZWEUjgp1nrU4WeHsukUBjbh7gYE7pm4F3c",
        "feeder_token_account": "9WtcfpuiF6dVKroycsi3E1k7vYQP8XmT7RBjcptdcfjX",
        "label": "G8 custody branch",
    },
    {
        "chain_id": "8ps_chain",
        "custody_owner": "8PSmqJy63d4cAKRLKUitJCBLSjuL1cvZxC53vdCyjUey",
        "custody_token_account": "2KEsnhnFiey3iA5zaenFVRSmuAGZdm7RbuG5VuAN69e1",
        "feeder_owner": "9jHrTCwpDANHLNQz5cem6XLUBM8KiTWKe766Br6KVCXM",
        "feeder_token_account": "HxT8kiUKxJ7jdvWfDeRZQzQia4wyRCNN2iRBjMUzcimN",
        "label": "8PS custody branch",
    },
]


def load_repo_env() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def resolve_helius_api_key() -> str:
    load_repo_env()
    key = (
        os.getenv("HELIUS_API_KEY_2")
        or os.getenv("HELIUS_API_KEY")
        or "6bb10a8e-f7b7-4216-a9ad-54d7cd762b0e"
    )
    return key


HELIUS_API_KEY = resolve_helius_api_key()


def dt_utc(ts: int | float | None) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def date_utc(ts: int | float | None) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%d")


def http_get(url: str, *, params: dict[str, Any] | None = None, retries: int = 6) -> Any:
    backoff = 1.0
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=60)
            if resp.status_code == 429:
                time.sleep(backoff)
                backoff = min(backoff * 2, 12.0)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if attempt == retries:
                raise
            time.sleep(backoff)
            backoff = min(backoff * 2, 12.0)
    raise RuntimeError("unreachable")


def fetch_all_enhanced_txs(address: str, label: str, page_limit: int = 100, max_pages: int = 800) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    url = f"https://api.helius.xyz/v0/addresses/{address}/transactions"
    before: str | None = None
    out: list[dict[str, Any]] = []
    pages_fetched = 0
    oldest_seen_ts: int | None = None

    while pages_fetched < max_pages:
        pages_fetched += 1
        params: dict[str, Any] = {"api-key": HELIUS_API_KEY, "limit": page_limit}
        if before:
            params["before"] = before
        rows = http_get(url, params=params)
        if not rows:
            break
        out.extend(rows)
        print(f"[{label}] fetched page {pages_fetched}, rows={len(rows)}, total={len(out)}", flush=True)
        page_oldest = min(int(row.get("timestamp", 0) or 0) for row in rows)
        oldest_seen_ts = page_oldest if oldest_seen_ts is None else min(oldest_seen_ts, page_oldest)
        before = rows[-1].get("signature")
        if not before or len(rows) < page_limit:
            break
        time.sleep(0.06)

    times = [int(row.get("timestamp", 0) or 0) for row in out if row.get("timestamp")]
    return out, {
        "pages_fetched": pages_fetched,
        "transaction_count": len(out),
        "newest_seen_ts": max(times) if times else None,
        "oldest_seen_ts": min(times) if times else oldest_seen_ts,
        "newest_seen_date": date_utc(max(times)) if times else None,
        "oldest_seen_date": date_utc(min(times)) if times else date_utc(oldest_seen_ts),
        "page_limit": page_limit,
        "max_pages_hit": pages_fetched >= max_pages and len(out) >= page_limit * max_pages,
    }


def trace_chain(chain: dict[str, str]) -> dict[str, Any]:
    txs, fetch_meta = fetch_all_enhanced_txs(chain["feeder_token_account"], chain["chain_id"])
    events: list[dict[str, Any]] = []
    by_sender_owner: dict[str, dict[str, Any]] = {}
    by_sender_token: dict[str, dict[str, Any]] = {}
    source_type_counter: Counter[tuple[str, str]] = Counter()

    for idx, tx in enumerate(txs, start=1):
        transfers = [
            tt
            for tt in (tx.get("tokenTransfers") or [])
            if tt.get("mint") == PUMP_MINT
            and (
                tt.get("toTokenAccount") == chain["feeder_token_account"]
                or tt.get("toUserAccount") == chain["feeder_owner"]
            )
        ]
        if not transfers:
            continue

        ts = int(tx.get("timestamp", 0) or 0)
        event_senders = []
        total_in = 0.0
        for tt in transfers:
            amount = float(tt.get("tokenAmount", 0.0) or 0.0)
            if amount <= 0:
                continue
            sender_owner = tt.get("fromUserAccount") or "UNKNOWN_OWNER"
            sender_token_account = tt.get("fromTokenAccount") or "UNKNOWN_TOKEN_ACCOUNT"
            total_in += amount
            event_senders.append(
                {
                    "sender_owner": sender_owner,
                    "sender_token_account": sender_token_account,
                    "pump_amount": amount,
                }
            )

            owner_bucket = by_sender_owner.setdefault(
                sender_owner,
                {
                    "sender_owner": sender_owner,
                    "cumulative_pump_sent": 0.0,
                    "transfer_count": 0,
                    "first_seen_ts": ts,
                    "last_seen_ts": ts,
                    "sample_token_accounts": set(),
                    "source_type_counter": Counter(),
                },
            )
            owner_bucket["cumulative_pump_sent"] += amount
            owner_bucket["transfer_count"] += 1
            owner_bucket["first_seen_ts"] = min(owner_bucket["first_seen_ts"], ts)
            owner_bucket["last_seen_ts"] = max(owner_bucket["last_seen_ts"], ts)
            if sender_token_account != "UNKNOWN_TOKEN_ACCOUNT":
                owner_bucket["sample_token_accounts"].add(sender_token_account)
            owner_bucket["source_type_counter"][(str(tx.get("source") or ""), str(tx.get("type") or ""))] += 1

            token_bucket = by_sender_token.setdefault(
                sender_token_account,
                {
                    "sender_token_account": sender_token_account,
                    "sender_owner": sender_owner,
                    "cumulative_pump_sent": 0.0,
                    "transfer_count": 0,
                    "first_seen_ts": ts,
                    "last_seen_ts": ts,
                },
            )
            token_bucket["cumulative_pump_sent"] += amount
            token_bucket["transfer_count"] += 1
            token_bucket["first_seen_ts"] = min(token_bucket["first_seen_ts"], ts)
            token_bucket["last_seen_ts"] = max(token_bucket["last_seen_ts"], ts)

        if not event_senders:
            continue

        source_type_counter[(str(tx.get("source") or ""), str(tx.get("type") or ""))] += 1
        events.append(
            {
                "signature": tx.get("signature"),
                "timestamp": ts,
                "datetime_utc": dt_utc(ts),
                "date": date_utc(ts),
                "source": tx.get("source"),
                "type": tx.get("type"),
                "description": tx.get("description"),
                "pump_in": total_in,
                "senders": event_senders,
            }
        )

        if idx % 100 == 0:
            print(f"[{chain['chain_id']}] scanned {idx}/{len(txs)} txs, inflow_events={len(events)}", flush=True)

    owner_rows = []
    for row in by_sender_owner.values():
        top_source_type = [
            {"source": s, "type": t, "count": c}
            for (s, t), c in row["source_type_counter"].most_common(10)
        ]
        owner_rows.append(
            {
                "sender_owner": row["sender_owner"],
                "cumulative_pump_sent": row["cumulative_pump_sent"],
                "transfer_count": row["transfer_count"],
                "first_seen_ts": row["first_seen_ts"],
                "first_seen_utc": dt_utc(row["first_seen_ts"]),
                "last_seen_ts": row["last_seen_ts"],
                "last_seen_utc": dt_utc(row["last_seen_ts"]),
                "sample_token_accounts": sorted(row["sample_token_accounts"]),
                "top_source_type": top_source_type,
            }
        )
    owner_rows.sort(key=lambda item: item["cumulative_pump_sent"], reverse=True)

    token_rows = []
    for row in by_sender_token.values():
        token_rows.append(
            {
                "sender_token_account": row["sender_token_account"],
                "sender_owner": row["sender_owner"],
                "cumulative_pump_sent": row["cumulative_pump_sent"],
                "transfer_count": row["transfer_count"],
                "first_seen_ts": row["first_seen_ts"],
                "first_seen_utc": dt_utc(row["first_seen_ts"]),
                "last_seen_ts": row["last_seen_ts"],
                "last_seen_utc": dt_utc(row["last_seen_ts"]),
            }
        )
    token_rows.sort(key=lambda item: item["cumulative_pump_sent"], reverse=True)

    source_type_rows = [
        {"source": s, "type": t, "count": c}
        for (s, t), c in source_type_counter.most_common(50)
    ]

    return {
        "chain": chain,
        "fetch_meta": fetch_meta,
        "summary": {
            "event_count": len(events),
            "total_pump_in": sum(row["pump_in"] for row in events),
            "unique_sender_owner_count": len(owner_rows),
            "unique_sender_token_count": len(token_rows),
        },
        "sender_owner_summary": owner_rows,
        "sender_token_summary": token_rows,
        "source_type_summary": source_type_rows,
        "events": events,
    }


def build_edges(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges = []
    for trace in traces:
        chain = trace["chain"]
        for row in trace["sender_owner_summary"]:
            edges.append(
                {
                    "chain_id": chain["chain_id"],
                    "from": row["sender_owner"],
                    "to": chain["feeder_owner"],
                    "pump_amount": row["cumulative_pump_sent"],
                    "kind": "upstream_to_feeder",
                }
            )
        feeder_to_custody = None
        # downstream amount comes from existing custody audit result if available later; fallback to total upstream
        feeder_to_custody = {
            "chain_id": chain["chain_id"],
            "from": chain["feeder_owner"],
            "to": chain["custody_owner"],
            "pump_amount": trace["summary"]["total_pump_in"],
            "kind": "feeder_to_custody",
        }
        edges.append(feeder_to_custody)
    return edges


def render_mermaid(traces: list[dict[str, Any]]) -> str:
    lines = ["flowchart LR"]
    for trace in traces:
        chain = trace["chain"]
        feeder = chain["feeder_owner"][:6]
        custody = chain["custody_owner"][:6]
        lines.append(f'  {feeder}["{chain["feeder_owner"]}<br/>{chain["label"]} feeder"] -->|{trace["summary"]["total_pump_in"]:.2f} PUMP| {custody}["{chain["custody_owner"]}<br/>custody"]')
        for i, row in enumerate(trace["sender_owner_summary"][:8], start=1):
            node = f'{chain["chain_id"].replace("_","")}{i}'
            lines.append(f'  {node}["{row["sender_owner"]}<br/>{row["cumulative_pump_sent"]:.2f} PUMP"] --> {feeder}')
    return "\n".join(lines)


def render_report(traces: list[dict[str, Any]]) -> str:
    mermaid = render_mermaid(traces)
    lines = [
        "# PUMP Buyback Upstream Trace",
        "",
        f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "",
        "This report traces one more hop upstream from the known feeder token accounts into the official custody holders.",
        "",
        "## Flow Overview",
        "",
        "```mermaid",
        mermaid,
        "```",
        "",
    ]
    for trace in traces:
        chain = trace["chain"]
        summary = trace["summary"]
        lines.extend(
            [
                f"## {chain['label']}",
                "",
                f"- Upstream feeder owner: `{chain['feeder_owner']}`",
                f"- Upstream feeder token account: `{chain['feeder_token_account']}`",
                f"- Custody owner: `{chain['custody_owner']}`",
                f"- Custody token account: `{chain['custody_token_account']}`",
                f"- Enhanced tx fetched: `{trace['fetch_meta']['transaction_count']}`",
                f"- Oldest seen date: `{trace['fetch_meta']['oldest_seen_date']}`",
                f"- Max pages hit: `{trace['fetch_meta']['max_pages_hit']}`",
                f"- Inflow events into feeder: `{summary['event_count']}`",
                f"- Total observed upstream PUMP into feeder: `{summary['total_pump_in']:.6f}`",
                "",
                "### Top upstream sender owners",
                "",
                "| Sender owner | PUMP sent | Transfers | First seen | Last seen | Top source/type |",
                "|---|---:|---:|---|---|---|",
            ]
        )
        for row in trace["sender_owner_summary"][:20]:
            top = row["top_source_type"][0] if row["top_source_type"] else {"source": "", "type": "", "count": 0}
            lines.append(
                f"| `{row['sender_owner']}` | {row['cumulative_pump_sent']:.6f} | {row['transfer_count']} | "
                f"{row['first_seen_utc']} | {row['last_seen_utc']} | "
                f"`{top['source']}/{top['type']}` x {top['count']} |"
            )
        lines.append("")
    return "\n".join(lines)


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>PUMP Buyback Upstream Flow</title>
  <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
  <style>
    :root {{
      --bg: #0e1116;
      --panel: #151b22;
      --text: #eef2f8;
      --muted: #9fb0c3;
      --line: #243041;
      --accent: #7de2b8;
      --accent2: #8fb8ff;
    }}
    body {{
      margin: 0;
      background: radial-gradient(circle at top, #1a2330, var(--bg) 45%);
      color: var(--text);
      font-family: "Iosevka Etoile", "SF Mono", "Menlo", monospace;
    }}
    .wrap {{
      max-width: 1400px;
      margin: 0 auto;
      padding: 32px 24px 48px;
    }}
    h1, h2 {{ margin: 0 0 12px; }}
    p {{ color: var(--muted); line-height: 1.5; }}
    .panel {{
      background: rgba(21, 27, 34, 0.86);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 18px;
      margin-top: 18px;
      box-shadow: 0 18px 50px rgba(0,0,0,.28);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      font-size: 13px;
    }}
    th, td {{
      text-align: left;
      padding: 10px 8px;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-weight: 600; }}
    .mono {{ font-family: inherit; word-break: break-all; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>PUMP Buyback Upstream Flow</h1>
    <p>This artifact traces one hop upstream beyond the known feeder token accounts into the official custody holders. It is designed to answer where the feeder balances came from and which transaction sources likely reflect buyback execution.</p>
    <div class="panel">
      <div id="sankey" style="height: 720px;"></div>
    </div>
    <div class="panel">
      <h2>Top Upstream Rows</h2>
      <div id="tables"></div>
    </div>
  </div>
  <script>
    const payload = __PAYLOAD__;
    const nodes = [];
    const nodeIndex = new Map();
    function getNode(label) {{
      if (!nodeIndex.has(label)) {{
        nodeIndex.set(label, nodes.length);
        nodes.push(label);
      }}
      return nodeIndex.get(label);
    }}
    const links = [];
    for (const edge of payload.edges) {{
      links.push({{
        source: getNode(edge.from),
        target: getNode(edge.to),
        value: edge.pump_amount
      }});
    }}
    Plotly.newPlot('sankey', [{{
      type: 'sankey',
      arrangement: 'snap',
      node: {{
        label: nodes,
        color: nodes.map((_, i) => i % 2 === 0 ? 'rgba(125,226,184,0.82)' : 'rgba(143,184,255,0.82)'),
        pad: 22,
        thickness: 18,
        line: {{ color: 'rgba(36,48,65,1)', width: 1 }}
      }},
      link: {{
        source: links.map(l => l.source),
        target: links.map(l => l.target),
        value: links.map(l => l.value),
        color: links.map((_, i) => i % 2 === 0 ? 'rgba(125,226,184,0.30)' : 'rgba(143,184,255,0.30)')
      }}
    }}], {{
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: {{ color: '#eef2f8', size: 13, family: 'Iosevka Etoile, SF Mono, Menlo, monospace' }},
      margin: {{ l: 10, r: 10, t: 10, b: 10 }}
    }}, {{displayModeBar: false, responsive: true}});

    const tables = document.getElementById('tables');
    for (const trace of payload.traces) {{
      const panel = document.createElement('div');
      panel.innerHTML = `<h2>${{trace.chain.label}}</h2>`;
      const table = document.createElement('table');
      table.innerHTML = `
        <thead>
          <tr>
            <th>Sender owner</th>
            <th>PUMP sent</th>
            <th>Transfers</th>
            <th>Top source/type</th>
          </tr>
        </thead>
        <tbody>
          ${trace.sender_owner_summary.slice(0, 15).map(row => {
            const top = (row.top_source_type && row.top_source_type[0]) || {source: '', type: '', count: 0};
            return `<tr>
              <td class="mono">${row.sender_owner}</td>
              <td>${row.cumulative_pump_sent.toFixed(6)}</td>
              <td>${row.transfer_count}</td>
              <td class="mono">${top.source}/${top.type} x ${top.count}</td>
            </tr>`;
          }).join('')}
        </tbody>`;
      panel.appendChild(table);
      tables.appendChild(panel);
    }}
  </script>
</body>
</html>
"""


def render_html(traces: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    payload = {
        "traces": [
            {
                "chain": trace["chain"],
                "sender_owner_summary": trace["sender_owner_summary"],
            }
            for trace in traces
        ],
        "edges": edges,
    }
    return HTML_TEMPLATE.replace("__PAYLOAD__", json.dumps(payload))


def main() -> None:
    OUT_RAW.mkdir(parents=True, exist_ok=True)
    OUT_DERIVED.mkdir(parents=True, exist_ok=True)
    OUT_REPORTS.mkdir(parents=True, exist_ok=True)

    traces = [trace_chain(chain) for chain in CHAINS]
    edges = build_edges(traces)

    raw_payload = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "pump_mint": PUMP_MINT,
            "helius_api_key_suffix": HELIUS_API_KEY[-6:],
        },
        "traces": traces,
    }
    summary_rows = []
    for trace in traces:
        for row in trace["sender_owner_summary"]:
            summary_rows.append(
                {
                    "chain_id": trace["chain"]["chain_id"],
                    "feeder_owner": trace["chain"]["feeder_owner"],
                    "feeder_token_account": trace["chain"]["feeder_token_account"],
                    "custody_owner": trace["chain"]["custody_owner"],
                    **row,
                }
            )
    raw_path = OUT_RAW / "pump_buyback_upstream_trace.json"
    raw_path.write_text(json.dumps(raw_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_path = OUT_DERIVED / "pump_buyback_upstream_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "metadata": raw_payload["metadata"],
                "rows": summary_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    edges_path = OUT_DERIVED / "pump_buyback_flow_edges.json"
    edges_path.write_text(
        json.dumps({"metadata": raw_payload["metadata"], "edges": edges}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    report_path = OUT_REPORTS / "pump_buyback_upstream_report_20260326.md"
    report_path.write_text(render_report(traces) + "\n", encoding="utf-8")

    html_path = OUT_REPORTS / "pump_buyback_upstream_sankey_20260326.html"
    html_path.write_text(render_html(traces, edges), encoding="utf-8")

    print(raw_path)
    print(summary_path)
    print(edges_path)
    print(report_path)
    print(html_path)


if __name__ == "__main__":
    main()
