#!/usr/bin/env python3
"""Audit all observable PUMP inflows into official buyback custody accounts."""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


BASE_DIR = Path(__file__).resolve().parents[2]
OUT_DERIVED = BASE_DIR / "data" / "pump" / "derived"
OUT_RAW = BASE_DIR / "data" / "pump" / "raw"
OUT_REPORTS = BASE_DIR / "data" / "pump" / "reports"

PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"

TARGETS = [
    {
        "owner": "G8CcfRffqZWHSAQJXLDfwbAkGE95SddUqVXnTrL4kqjm",
        "token_account": "HdtUyEC7TeLGrA7ddRRJWM6nUYk5UZsL9pJuWnXAFQ32",
        "label": "g8_primary_holder",
    },
    {
        "owner": "8PSmqJy63d4cAKRLKUitJCBLSjuL1cvZxC53vdCyjUey",
        "token_account": "2KEsnhnFiey3iA5zaenFVRSmuAGZdm7RbuG5VuAN69e1",
        "label": "8ps_secondary_holder",
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


def http_get(url: str, *, params: dict[str, Any] | None = None, retries: int = 5) -> Any:
    backoff = 1.0
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=60)
            if resp.status_code == 429:
                time.sleep(backoff)
                backoff = min(backoff * 2, 8.0)
                continue
            resp.raise_for_status()
            return resp.json()
        except Exception:
            if attempt == retries:
                raise
            time.sleep(backoff)
            backoff = min(backoff * 2, 8.0)
    raise RuntimeError("unreachable")


def fetch_all_enhanced_txs(address: str, label: str, page_limit: int = 100, max_pages: int = 500) -> tuple[list[dict[str, Any]], dict[str, Any]]:
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
        print(
            f"[{label}] fetched page {pages_fetched}, rows={len(rows)}, total={len(out)}",
            flush=True,
        )
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


def is_inflow(tt: dict[str, Any], target: dict[str, str]) -> bool:
    if tt.get("mint") != PUMP_MINT:
        return False
    to_token = tt.get("toTokenAccount")
    to_user = tt.get("toUserAccount")
    if to_token == target["token_account"]:
        return True
    if to_user == target["owner"]:
        return True
    return False


def parse_inflow_events(txs: list[dict[str, Any]], target: dict[str, str]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    sender_owner_totals: dict[str, dict[str, Any]] = {}
    sender_token_totals: dict[str, dict[str, Any]] = {}
    unresolved_sender_count = 0

    for idx, tx in enumerate(txs, start=1):
        signature = str(tx.get("signature") or "")
        ts = int(tx.get("timestamp", 0) or 0)
        transfers = [tt for tt in (tx.get("tokenTransfers") or []) if is_inflow(tt, target)]
        if not transfers:
            continue

        inflow_senders = []
        total_pump_in = 0.0
        for tt in transfers:
            amount = float(tt.get("tokenAmount", 0.0) or 0.0)
            if amount <= 0:
                continue
            sender_owner = tt.get("fromUserAccount") or "UNKNOWN_OWNER"
            sender_token = tt.get("fromTokenAccount") or "UNKNOWN_TOKEN_ACCOUNT"
            inflow_senders.append(
                {
                    "sender_owner": sender_owner,
                    "sender_token_account": sender_token,
                    "pump_amount": amount,
                }
            )
            total_pump_in += amount

            owner_bucket = sender_owner_totals.setdefault(
                sender_owner,
                {
                    "sender_owner": sender_owner,
                    "inflow_events": 0,
                    "cumulative_pump_sent": 0.0,
                    "first_seen_ts": ts,
                    "last_seen_ts": ts,
                    "sample_token_accounts": set(),
                },
            )
            owner_bucket["inflow_events"] += 1
            owner_bucket["cumulative_pump_sent"] += amount
            owner_bucket["first_seen_ts"] = min(owner_bucket["first_seen_ts"], ts)
            owner_bucket["last_seen_ts"] = max(owner_bucket["last_seen_ts"], ts)
            if sender_token != "UNKNOWN_TOKEN_ACCOUNT":
                owner_bucket["sample_token_accounts"].add(sender_token)

            token_bucket = sender_token_totals.setdefault(
                sender_token,
                {
                    "sender_token_account": sender_token,
                    "sender_owner": sender_owner,
                    "inflow_events": 0,
                    "cumulative_pump_sent": 0.0,
                    "first_seen_ts": ts,
                    "last_seen_ts": ts,
                },
            )
            token_bucket["inflow_events"] += 1
            token_bucket["cumulative_pump_sent"] += amount
            token_bucket["first_seen_ts"] = min(token_bucket["first_seen_ts"], ts)
            token_bucket["last_seen_ts"] = max(token_bucket["last_seen_ts"], ts)

        if not inflow_senders:
            unresolved_sender_count += 1
            continue

        inflow_senders.sort(key=lambda row: row["pump_amount"], reverse=True)
        events.append(
            {
                "signature": signature,
                "timestamp": ts,
                "datetime_utc": dt_utc(ts),
                "date": date_utc(ts),
                "source": tx.get("source"),
                "type": tx.get("type"),
                "description": tx.get("description"),
                "target_owner": target["owner"],
                "target_token_account": target["token_account"],
                "pump_in": total_pump_in,
                "sender_count": len(inflow_senders),
                "senders": inflow_senders,
            }
        )

        if idx % 100 == 0:
            print(
                f"[{target['label']}] scanned {idx}/{len(txs)} enhanced txs, inflow_events={len(events)}",
                flush=True,
            )

    owner_rows = []
    for bucket in sender_owner_totals.values():
        owner_rows.append(
            {
                "sender_owner": bucket["sender_owner"],
                "inflow_events": bucket["inflow_events"],
                "cumulative_pump_sent": bucket["cumulative_pump_sent"],
                "first_seen_ts": bucket["first_seen_ts"],
                "first_seen_utc": dt_utc(bucket["first_seen_ts"]),
                "last_seen_ts": bucket["last_seen_ts"],
                "last_seen_utc": dt_utc(bucket["last_seen_ts"]),
                "sample_token_accounts": sorted(bucket["sample_token_accounts"]),
            }
        )
    owner_rows.sort(key=lambda row: row["cumulative_pump_sent"], reverse=True)

    token_rows = []
    for bucket in sender_token_totals.values():
        token_rows.append(
            {
                "sender_token_account": bucket["sender_token_account"],
                "sender_owner": bucket["sender_owner"],
                "inflow_events": bucket["inflow_events"],
                "cumulative_pump_sent": bucket["cumulative_pump_sent"],
                "first_seen_ts": bucket["first_seen_ts"],
                "first_seen_utc": dt_utc(bucket["first_seen_ts"]),
                "last_seen_ts": bucket["last_seen_ts"],
                "last_seen_utc": dt_utc(bucket["last_seen_ts"]),
            }
        )
    token_rows.sort(key=lambda row: row["cumulative_pump_sent"], reverse=True)

    return {
        "audit_summary": {
            "inflow_event_count": len(events),
            "total_pump_in_observed": sum(row["pump_in"] for row in events),
            "unique_sender_owner_count": len(owner_rows),
            "unique_sender_token_account_count": len(token_rows),
            "unresolved_sender_event_count": unresolved_sender_count,
        },
        "sender_owner_summary": owner_rows,
        "sender_token_account_summary": token_rows,
        "events": events,
    }


def audit_target(target: dict[str, str]) -> dict[str, Any]:
    txs, fetch_meta = fetch_all_enhanced_txs(target["token_account"], target["label"])
    parsed = parse_inflow_events(txs, target)
    return {
        "target": target,
        "fetch_meta": fetch_meta,
        **parsed,
    }


def render_report(audits: list[dict[str, Any]]) -> str:
    lines = [
        "# PUMP Buyback Custody Inflow Audit",
        "",
        f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}",
        "",
        "This report audits all observable PUMP inflows into the two custody addresses disclosed by `fees.pump.fun`.",
        "",
    ]
    for audit in audits:
        target = audit["target"]
        summary = audit["audit_summary"]
        lines.extend(
            [
                f"## {target['label']}",
                "",
                f"- Owner: `{target['owner']}`",
                f"- Token account: `{target['token_account']}`",
                f"- Enhanced tx fetched: `{audit['fetch_meta']['transaction_count']}`",
                f"- Oldest seen date: `{audit['fetch_meta']['oldest_seen_date']}`",
                f"- Inflow events: `{summary['inflow_event_count']}`",
                f"- Total observed PUMP inflow: `{summary['total_pump_in_observed']:.6f}`",
                f"- Unique sender owners: `{summary['unique_sender_owner_count']}`",
                "",
                "### Top sender owners",
                "",
                "| Sender owner | Events | PUMP sent | First seen | Last seen |",
                "|---|---:|---:|---|---|",
            ]
        )
        for row in audit["sender_owner_summary"][:20]:
            lines.append(
                f"| `{row['sender_owner']}` | {row['inflow_events']} | {row['cumulative_pump_sent']:.6f} | "
                f"{row['first_seen_utc']} | {row['last_seen_utc']} |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    OUT_DERIVED.mkdir(parents=True, exist_ok=True)
    OUT_RAW.mkdir(parents=True, exist_ok=True)
    OUT_REPORTS.mkdir(parents=True, exist_ok=True)

    audits = [audit_target(target) for target in TARGETS]
    payload = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "pump_mint": PUMP_MINT,
            "helius_api_key_suffix": HELIUS_API_KEY[-6:],
            "targets": TARGETS,
        },
        "audits": audits,
    }

    raw_path = OUT_RAW / "pump_buyback_custody_inflow_audit.json"
    raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_rows = []
    for audit in audits:
        for row in audit["sender_owner_summary"]:
            summary_rows.append(
                {
                    "target_label": audit["target"]["label"],
                    "target_owner": audit["target"]["owner"],
                    "target_token_account": audit["target"]["token_account"],
                    **row,
                }
            )
    summary_path = OUT_DERIVED / "pump_buyback_custody_sender_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "metadata": payload["metadata"],
                "rows": summary_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    report_path = OUT_REPORTS / "pump_buyback_custody_inflow_audit_20260325.md"
    report_path.write_text(render_report(audits) + "\n", encoding="utf-8")

    print(raw_path)
    print(summary_path)
    print(report_path)


if __name__ == "__main__":
    main()
