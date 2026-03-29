#!/usr/bin/env python3
"""
Build full-history PUMP token-purchase execution clusters on Solana.

Outputs:
- data/pump/derived/buyback_execution_cluster_registry.json
- data/pump/derived/buyback_execution_daily_map.json
- data/pump/raw/buyback_execution_tx_index.json
- data/pump/reports/pump_token_purchases_cluster_report.md
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import audit_pump_buyback_reconciliation as audit
import forensic_verify_pump_buybacks as fv


BASE_DIR = Path(__file__).resolve().parents[2]
PUMP_DIR = BASE_DIR / "data" / "pump"

OFFICIAL_START_DATE = "2025-07-15"
PREP_WINDOW_START_DATE = "2025-07-12"
PREP_WINDOW_END_DATE = "2025-07-14"

KNOWN_HOLDER_OWNERS = {
    audit.TREASURY_WALLET,
    audit.SECONDARY_HOLDER,
}


def date_range_days(start: str, end: str) -> list[str]:
    cur = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt = datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    days: list[str] = []
    while cur <= end_dt:
        days.append(cur.strftime("%Y-%m-%d"))
        cur = cur + timedelta(days=1)
    return days


def cluster_id_for_owner(owner: str) -> str:
    if owner == audit.BUYBACK_WALLET:
        return "cluster_3vk_legacy"
    if owner == audit.SECONDARY_HOLDER:
        return "cluster_8ps_secondary_holder"
    if owner == audit.TREASURY_WALLET:
        return "cluster_g8_treasury_holder"
    if owner == audit.STAKING_DISTRIBUTOR:
        return "cluster_staking_distributor"
    return f"cluster_{owner[:8].lower()}"


def cluster_label_for_owner(owner: str) -> str:
    if owner == audit.BUYBACK_WALLET:
        return "3VK legacy direct executor"
    if owner == audit.SECONDARY_HOLDER:
        return "8PS secondary holder / squads holder"
    if owner == audit.TREASURY_WALLET:
        return "G8 treasury holder"
    if owner == audit.STAKING_DISTRIBUTOR:
        return "staking distributor"
    return f"{owner[:8]} execution cluster"


def fetch_token_account_history(
    *,
    helius_key: str,
    owner: str,
    helius_rpc: str,
    max_pages: int,
    page_limit: int,
) -> tuple[str | None, list[dict[str, Any]], dict[str, Any]]:
    token_accounts = audit.get_pump_token_accounts_by_owner(helius_rpc, owner)
    token_account = token_accounts[0]["pubkey"] if token_accounts else None
    if not token_account:
        return None, [], {}
    txs, meta = audit.fetch_all_history(
        helius_key=helius_key,
        address=token_account,
        min_ts=audit.TGE_TS,
        max_pages=max_pages,
        page_limit=page_limit,
    )
    return token_account, txs, meta


def parse_owner_swap_buy_legs(owner: str, txs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tx in txs:
        source = str(tx.get("source") or "")
        tx_type = str(tx.get("type") or "")
        if source not in audit.AUTOMATION_PROGRAM_SOURCES and tx_type not in fv.DEX_TYPES:
            continue
        sig = str(tx.get("signature") or "")
        ts = int(tx.get("timestamp", 0) or 0)
        if not sig or ts <= 0:
            continue
        pump_in = 0.0
        counterparties: Counter[str] = Counter()
        for tt in tx.get("tokenTransfers", []) or []:
            if str(tt.get("mint") or "") != audit.PUMP_MINT:
                continue
            amount = float(tt.get("tokenAmount") or 0.0)
            if amount <= 0:
                continue
            if str(tt.get("toUserAccount") or "") == owner:
                pump_in += amount
                counterparty = str(tt.get("fromUserAccount") or tt.get("fromTokenAccount") or "UNKNOWN")
                counterparties[counterparty] += amount
        if pump_in <= 0:
            continue
        rows.append({
            "cluster_owner": owner,
            "cluster_id": cluster_id_for_owner(owner),
            "signature": sig,
            "timestamp": ts,
            "datetime_utc": fv.dt_utc(ts),
            "date": fv.date_utc(ts),
            "source": source,
            "type": tx_type,
            "leg_type": "direct_buy",
            "pump_amount": round(pump_in, 6),
            "counterparties": [
                {"address": addr, "pump_amount": round(amount, 6)}
                for addr, amount in counterparties.most_common()
            ],
            "description": str(tx.get("description") or ""),
        })
    rows.sort(key=lambda row: (row["timestamp"], row["signature"]))
    return rows


def parse_forward_legs(
    *,
    owner: str,
    token_account: str | None,
    token_txs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not token_account:
        return []
    parsed = audit.parse_token_account_rows(
        txs=token_txs,
        token_account=token_account,
        owner=owner,
    )
    out: list[dict[str, Any]] = []
    for row in parsed:
        for receiver in row.get("outflow_receivers", []) or []:
            to_address = str(receiver.get("address") or "")
            amount = float(receiver.get("pump_amount") or 0.0)
            if amount <= 0:
                continue
            out.append({
                "cluster_owner": owner,
                "cluster_id": cluster_id_for_owner(owner),
                "signature": row["signature"],
                "timestamp": row["timestamp"],
                "datetime_utc": row["datetime_utc"],
                "date": row["date"],
                "source": row["helius_source"],
                "type": row["helius_type"],
                "leg_type": "forward_transfer",
                "pump_amount": round(amount, 6),
                "to_address": to_address,
                "description": row["description"],
            })
    out.sort(key=lambda row: (row["timestamp"], row["signature"]))
    return out


def parse_holder_inflow_legs_by_sender(
    *,
    sender: str,
    holder_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in holder_rows:
        amount = 0.0
        for inflow in row.get("inflow_senders", []) or []:
            if str(inflow.get("address") or "") == sender:
                amount += float(inflow.get("pump_amount") or 0.0)
        if amount <= 0:
            continue
        out.append({
            "cluster_owner": sender,
            "cluster_id": cluster_id_for_owner(sender),
            "signature": row["signature"],
            "timestamp": row["timestamp"],
            "datetime_utc": row["datetime_utc"],
            "date": row["date"],
            "source": row["helius_source"],
            "type": row["helius_type"],
            "leg_type": "forward_transfer",
            "pump_amount": round(amount, 6),
            "to_address": audit.SECONDARY_HOLDER,
            "description": row["description"],
        })
    out.sort(key=lambda row: (row["timestamp"], row["signature"]))
    return out


def aggregate_by_day(rows: list[dict[str, Any]], amount_key: str = "pump_amount") -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    for row in rows:
        out[str(row["date"])] += float(row.get(amount_key) or 0.0)
    return {day: round(value, 6) for day, value in sorted(out.items())}


def leg_signatures_by_day(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        out[str(row["date"])].append(str(row["signature"]))
    return {day: sigs for day, sigs in sorted(out.items())}


def get_relay_candidates(
    holder_rows: list[dict[str, Any]],
    *,
    min_amount: float = 1_000_000,
) -> list[tuple[str, float]]:
    sender_totals = audit.top_sender_totals(holder_rows)
    out: list[tuple[str, float]] = []
    for sender, amount in sender_totals.most_common():
        if not sender or amount < min_amount:
            continue
        if sender in KNOWN_HOLDER_OWNERS:
            continue
        out.append((sender, round(float(amount), 6)))
    return out


def build_cluster_registry(
    *,
    helius_rpc: str,
    owner_summaries: dict[str, dict[str, Any]],
    owner_token_accounts: dict[str, list[dict[str, Any]]],
    shared_squads_accounts: list[dict[str, Any]],
    relay_candidates: list[dict[str, Any]],
    cluster_direct_rows: dict[str, list[dict[str, Any]]],
    cluster_forward_rows: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    cluster_members: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for owner, summary in owner_summaries.items():
        cluster_id = cluster_id_for_owner(owner)
        accounts = owner_token_accounts.get(owner, [])
        cluster_members[cluster_id].append({
            "address": owner,
            "role": "owner",
            "account_owner": None,
            "account_executable": None,
            "current_pump_balance": round(sum(float(x.get("ui_amount") or 0.0) for x in accounts), 6),
            "first_seen": summary.get("first_seen_utc"),
            "last_seen": summary.get("last_seen_utc"),
            "source_counts": summary.get("source_counts") or {},
            "type_counts": summary.get("type_counts") or {},
        })
        for account in accounts:
            cluster_members[cluster_id].append({
                "address": str(account.get("pubkey") or ""),
                "role": "token_account",
                "account_owner": owner,
                "account_executable": False,
                "current_pump_balance": round(float(account.get("ui_amount") or 0.0), 6),
                "first_seen": None,
                "last_seen": None,
                "source_counts": {},
                "type_counts": {},
            })

    shared_rows_by_owner: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in shared_squads_accounts:
        for owner in row.get("owners") or []:
            shared_rows_by_owner[str(owner)].append(row)

    clusters: list[dict[str, Any]] = []
    for cluster_id, members in sorted(cluster_members.items()):
        owner_row = next((row for row in members if row["role"] == "owner"), None)
        if not owner_row:
            continue
        owner = str(owner_row["address"])
        label = cluster_label_for_owner(owner)
        role = "holder_support"
        evidence_level = "probable"
        notes: list[str] = []
        if owner == audit.BUYBACK_WALLET:
            role = "direct_executor"
            evidence_level = "confirmed"
            notes.append("Direct buyback wallet with observable swap legs.")
        elif owner == audit.SECONDARY_HOLDER:
            role = "holder_support"
            evidence_level = "probable"
            notes.append("fees.pump.fun disclosed holder with Squads multisig activity.")
        elif any(r["address"] == owner for r in relay_candidates):
            role = "relay_executor"
            evidence_level = "probable"
            notes.append("Receives PUMP from swap legs and forwards into disclosed holder path.")

        shared_accounts = shared_rows_by_owner.get(owner, [])
        direct_rows = cluster_direct_rows.get(cluster_id, [])
        forward_rows = cluster_forward_rows.get(cluster_id, [])
        clusters.append({
            "cluster_id": cluster_id,
            "label": label,
            "classification": role,
            "evidence_level": evidence_level,
            "first_seen": owner_row.get("first_seen"),
            "last_seen": owner_row.get("last_seen"),
            "direct_buy_pump_total": round(sum(float(row["pump_amount"]) for row in direct_rows), 6),
            "forward_to_disclosed_holder_pump_total": round(
                sum(float(row["pump_amount"]) for row in forward_rows if row.get("to_address") in KNOWN_HOLDER_OWNERS),
                6,
            ),
            "shared_squads_accounts": shared_accounts,
            "members": members,
            "notes": notes,
        })

    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "official_start_date": OFFICIAL_START_DATE,
        "prep_window_start_date": PREP_WINDOW_START_DATE,
        "prep_window_end_date": PREP_WINDOW_END_DATE,
        "clusters": clusters,
    }


def build_daily_map(
    *,
    official: dict[str, Any],
    registry: dict[str, Any],
    cluster_direct_rows: dict[str, list[dict[str, Any]]],
    cluster_forward_rows: dict[str, list[dict[str, Any]]],
    holder_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    official_daily = official.get("dailyBuybacks", {}) or {}
    last_official_day = max(
        (day for day, row in official_daily.items() if float((row or {}).get("pumpTokensBought") or 0.0) >= 0.0),
        default=OFFICIAL_START_DATE,
    )
    days = date_range_days(OFFICIAL_START_DATE, last_official_day)

    direct_by_cluster_day = {
        cluster_id: aggregate_by_day(rows)
        for cluster_id, rows in cluster_direct_rows.items()
    }
    forward_by_cluster_day = {
        cluster_id: aggregate_by_day(rows)
        for cluster_id, rows in cluster_forward_rows.items()
    }
    direct_sig_by_cluster_day = {
        cluster_id: leg_signatures_by_day(rows)
        for cluster_id, rows in cluster_direct_rows.items()
    }
    forward_sig_by_cluster_day = {
        cluster_id: leg_signatures_by_day(rows)
        for cluster_id, rows in cluster_forward_rows.items()
    }
    holder_net_by_day = aggregate_by_day(holder_rows, "pump_net")
    cluster_label_map = {
        str(cluster["cluster_id"]): str(cluster["label"])
        for cluster in registry.get("clusters", []) or []
    }

    daily_rows: list[dict[str, Any]] = []
    for day in days:
        official_row = official_daily.get(day, {}) or {}
        official_pump = round(float(official_row.get("pumpTokensBought") or 0.0), 6)
        cluster_matches: list[dict[str, Any]] = []

        for cluster_id in sorted(set(direct_by_cluster_day) | set(forward_by_cluster_day)):
            direct_pump = float((direct_by_cluster_day.get(cluster_id) or {}).get(day) or 0.0)
            forward_pump = float((forward_by_cluster_day.get(cluster_id) or {}).get(day) or 0.0)
            supporting_holder_net = 0.0
            evidence_level = "unresolved"
            execution_equivalent = 0.0
            if cluster_id != "cluster_3vk_legacy":
                supporting_holder_net = max(float(holder_net_by_day.get(day) or 0.0), 0.0)
            if forward_pump > 0 and supporting_holder_net > 0:
                execution_equivalent = max(direct_pump, min(forward_pump, supporting_holder_net))
                evidence_level = "confirmed" if direct_pump > 0 else "probable"
            elif direct_pump > 0:
                execution_equivalent = direct_pump
                evidence_level = "confirmed"
            elif forward_pump > 0:
                execution_equivalent = forward_pump
                evidence_level = "probable"
            if execution_equivalent <= 0:
                continue
            signatures = sorted({
                *((direct_sig_by_cluster_day.get(cluster_id) or {}).get(day) or []),
                *((forward_sig_by_cluster_day.get(cluster_id) or {}).get(day) or []),
            })
            cluster_matches.append({
                "cluster_id": cluster_id,
                "label": cluster_label_map.get(cluster_id, cluster_id),
                "evidence_level": evidence_level,
                "direct_buy_pump": round(direct_pump, 6),
                "forward_to_disclosed_holder_pump": round(forward_pump, 6),
                "supporting_holder_net_pump": round(supporting_holder_net, 6),
                "execution_equivalent_pump": round(execution_equivalent, 6),
                "key_signatures": signatures[:20],
            })

        explained_pump = round(sum(float(row["execution_equivalent_pump"]) for row in cluster_matches), 6)
        unresolved_pump = round(official_pump - explained_pump, 6)
        daily_rows.append({
            "date": day,
            "official_pump_bought": official_pump,
            "official_tx_count": int(official_row.get("transactionCount") or 0),
            "matched_clusters": cluster_matches,
            "explained_pump": explained_pump,
            "unresolved_pump": unresolved_pump,
        })

    summary = {
        "official_total_pump": round(sum(float(row["official_pump_bought"]) for row in daily_rows), 6),
        "explained_total_pump": round(sum(float(row["explained_pump"]) for row in daily_rows), 6),
        "unresolved_total_pump": round(sum(float(row["unresolved_pump"]) for row in daily_rows), 6),
    }
    official_total = float(summary["official_total_pump"] or 0.0)
    summary["coverage_ratio"] = round(
        float(summary["explained_total_pump"]) / official_total, 6
    ) if official_total > 0 else 0.0

    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "official_last_updated": official.get("lastUpdated"),
        "official_start_date": OFFICIAL_START_DATE,
        "prep_window_start_date": PREP_WINDOW_START_DATE,
        "prep_window_end_date": PREP_WINDOW_END_DATE,
        "summary": summary,
        "days": daily_rows,
    }


def write_report(
    *,
    path: Path,
    official: dict[str, Any],
    registry: dict[str, Any],
    daily_map: dict[str, Any],
    relay_candidates: list[dict[str, Any]],
) -> None:
    summary = daily_map["summary"]
    clusters = registry["clusters"]
    unresolved_top = sorted(
        (row for row in daily_map["days"] if abs(float(row["unresolved_pump"])) > 0),
        key=lambda row: abs(float(row["unresolved_pump"])),
        reverse=True,
    )[:12]

    with open(path, "w", encoding="utf-8") as f:
        f.write("# PUMP Token Purchases Execution Cluster Report\n\n")
        f.write(f"- Generated at (UTC): {daily_map['generated_at_utc']}\n")
        f.write(f"- Official endpoint: `{audit.OFFICIAL_BUYBACK_URL}`\n")
        f.write(f"- Official start date used: `{OFFICIAL_START_DATE}`\n")
        f.write(f"- Prep window used: `{PREP_WINDOW_START_DATE}` to `{PREP_WINDOW_END_DATE}`\n\n")

        f.write("## Headline\n\n")
        f.write(
            f"- Official cumulative token purchases: **{float(official.get('totalPumpTokensBought') or 0.0):,.2f} PUMP**.\n"
        )
        f.write(
            f"- Current execution-cluster model explains **{float(summary['explained_total_pump']):,.2f} PUMP** "
            f"({float(summary['coverage_ratio']):.2%} of official).\n"
        )
        f.write(
            f"- Unresolved remainder: **{float(summary['unresolved_total_pump']):,.2f} PUMP**.\n"
        )
        if relay_candidates:
            f.write(
                f"- Strongest non-3VK relay candidate so far: `{relay_candidates[0]['address']}` "
                f"with **{float(relay_candidates[0]['observed_secondary_holder_inflow_pump']):,.2f} PUMP** forwarded into disclosed holder path.\n"
            )

        f.write("\n## Cluster Registry\n\n")
        f.write("| cluster_id | label | classification | evidence | direct_buy_total | forward_total |\n")
        f.write("|---|---|---|---|---:|---:|\n")
        for cluster in clusters:
            f.write(
                f"| `{cluster['cluster_id']}` | {cluster['label']} | {cluster['classification']} | "
                f"{cluster['evidence_level']} | {float(cluster['direct_buy_pump_total']):,.2f} | "
                f"{float(cluster['forward_to_disclosed_holder_pump_total']):,.2f} |\n"
            )

        f.write("\n## Relay Candidates\n\n")
        if relay_candidates:
            for relay in relay_candidates:
                f.write(
                    f"- `{relay['address']}` with token account `{relay.get('token_account') or '-'}` "
                    f"sent **{float(relay['observed_secondary_holder_inflow_pump']):,.2f} PUMP** into disclosed holder path and shows "
                    f"`{', '.join(relay['source_counts'][:6])}` activity.\n"
                )
        else:
            f.write("- None found above threshold.\n")

        f.write("\n## Largest Unresolved Days\n\n")
        f.write("| date | official_pump | explained_pump | unresolved_pump |\n")
        f.write("|---|---:|---:|---:|\n")
        for row in unresolved_top:
            f.write(
                f"| {row['date']} | {float(row['official_pump_bought']):,.2f} | "
                f"{float(row['explained_pump']):,.2f} | {float(row['unresolved_pump']):,.2f} |\n"
            )

        f.write("\n## Notes\n\n")
        f.write("- `2025-07-15` is treated as the first official token-purchase day.\n")
        f.write("- `2025-07-12` to `2025-07-14` are retained as setup/prep context, not official purchase days.\n")
        f.write("- `8PS` is treated as a disclosed holder/supporting path, not as the default direct executor.\n")
        f.write("- `9jHr` is treated as a relay/execution cluster candidate, not as a one-to-one replacement for the entire official series.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build full-history PUMP token-purchase execution clusters.")
    parser.add_argument("--max-pages", type=int, default=200, help="Max owner-history pages for direct wallets.")
    parser.add_argument("--page-limit", type=int, default=100, help="Helius page size.")
    parser.add_argument("--holder-pages", type=int, default=40, help="Max token-account pages for 8PS holder path.")
    parser.add_argument("--relay-owner-pages", type=int, default=40, help="Max owner-history pages for relay candidates.")
    parser.add_argument("--relay-token-pages", type=int, default=40, help="Max token-account pages for relay candidates.")
    args = parser.parse_args()

    helius_key, helius_rpc = audit.load_runtime_config()

    print("Fetching official buyback API ...", flush=True)
    official = audit.fetch_official_buybacks()

    print("Fetching 3VK owner history ...", flush=True)
    owner_histories: dict[str, list[dict[str, Any]]] = {}
    owner_fetch_meta: dict[str, Any] = {}
    txs, meta = audit.fetch_all_history(
        helius_key=helius_key,
        address=audit.BUYBACK_WALLET,
        min_ts=audit.TGE_TS,
        max_pages=args.max_pages,
        page_limit=args.page_limit,
    )
    owner_histories[audit.BUYBACK_WALLET] = txs
    owner_fetch_meta[audit.BUYBACK_WALLET] = meta

    print("Fetching 8PS owner and token-account history ...", flush=True)
    txs, meta = audit.fetch_all_history(
        helius_key=helius_key,
        address=audit.SECONDARY_HOLDER,
        min_ts=audit.TGE_TS,
        max_pages=min(args.max_pages, 10),
        page_limit=args.page_limit,
    )
    owner_histories[audit.SECONDARY_HOLDER] = txs
    owner_fetch_meta[audit.SECONDARY_HOLDER] = meta
    secondary_token_account, secondary_token_txs, secondary_token_meta = fetch_token_account_history(
        helius_key=helius_key,
        owner=audit.SECONDARY_HOLDER,
        helius_rpc=helius_rpc,
        max_pages=args.holder_pages,
        page_limit=args.page_limit,
    )
    holder_rows = audit.parse_token_account_rows(
        txs=secondary_token_txs,
        token_account=secondary_token_account or "",
        owner=audit.SECONDARY_HOLDER,
    ) if secondary_token_account else []

    print("Discovering relay candidates from 8PS holder path ...", flush=True)
    relay_candidates: list[dict[str, Any]] = []
    cluster_direct_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    cluster_forward_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)

    direct_buy_legs, _, _ = fv.parse_buyback_legs(owner_histories[audit.BUYBACK_WALLET])
    cluster_direct_rows[cluster_id_for_owner(audit.BUYBACK_WALLET)] = [
        {
            "cluster_owner": audit.BUYBACK_WALLET,
            "cluster_id": cluster_id_for_owner(audit.BUYBACK_WALLET),
            "signature": row["signature"],
            "timestamp": row["timestamp"],
            "datetime_utc": row["datetime_utc"],
            "date": row["date"],
            "source": row["helius_source"],
            "type": row["helius_type"],
            "leg_type": "direct_buy",
            "pump_amount": row["pump_amount"],
            "counterparties": row.get("senders_to_buyback", []),
            "description": "",
        }
        for row in direct_buy_legs
    ]

    owner_token_accounts: dict[str, list[dict[str, Any]]] = {
        audit.BUYBACK_WALLET: audit.get_pump_token_accounts_by_owner(helius_rpc, audit.BUYBACK_WALLET),
        audit.SECONDARY_HOLDER: audit.get_pump_token_accounts_by_owner(helius_rpc, audit.SECONDARY_HOLDER),
    }

    relay_seeds = get_relay_candidates(holder_rows)
    for relay_owner, observed_amount in relay_seeds:
        print(f"Fetching relay owner history: {relay_owner} ...", flush=True)
        relay_owner_txs, relay_owner_meta = audit.fetch_all_history(
            helius_key=helius_key,
            address=relay_owner,
            min_ts=audit.TGE_TS,
            max_pages=args.relay_owner_pages,
            page_limit=args.page_limit,
        )
        owner_histories[relay_owner] = relay_owner_txs
        owner_fetch_meta[relay_owner] = relay_owner_meta
        relay_token_account, relay_token_txs, relay_token_meta = fetch_token_account_history(
            helius_key=helius_key,
            owner=relay_owner,
            helius_rpc=helius_rpc,
            max_pages=args.relay_token_pages,
            page_limit=args.page_limit,
        )
        owner_token_accounts[relay_owner] = audit.get_pump_token_accounts_by_owner(helius_rpc, relay_owner)
        relay_candidates.append({
            "address": relay_owner,
            "observed_secondary_holder_inflow_pump": observed_amount,
            "token_account": relay_token_account,
            "source_counts": list((audit.summarize_owner_activity(relay_owner_txs).get("source_counts") or {}).keys()),
        })
        cluster_direct_rows[cluster_id_for_owner(relay_owner)] = parse_owner_swap_buy_legs(relay_owner, relay_owner_txs)
        forward_rows = parse_forward_legs(
            owner=relay_owner,
            token_account=relay_token_account,
            token_txs=relay_token_txs,
        )
        holder_inflow_rows = parse_holder_inflow_legs_by_sender(
            sender=relay_owner,
            holder_rows=holder_rows,
        )
        dedup: dict[tuple[str, str, float], dict[str, Any]] = {}
        for row in [*forward_rows, *holder_inflow_rows]:
            key = (str(row["signature"]), str(row.get("to_address") or ""), float(row["pump_amount"]))
            dedup[key] = row
        cluster_forward_rows[cluster_id_for_owner(relay_owner)] = sorted(
            dedup.values(),
            key=lambda row: (row["timestamp"], row["signature"]),
        )
        owner_fetch_meta[f"{relay_owner}_token_account"] = relay_token_meta

    print("Building shared Squads skeleton ...", flush=True)
    shared_tracker: dict[str, dict[str, Any]] = {}
    for owner, tx_rows in owner_histories.items():
        counter = audit.summarize_squads_accounts(tx_rows, owner)
        for address, appearances in counter.items():
            if not address or address in {owner, "11111111111111111111111111111111", "ComputeBudget111111111111111111111111111111"}:
                continue
            bucket = shared_tracker.setdefault(address, {"owners": set(), "appearances": 0})
            bucket["owners"].add(owner)
            bucket["appearances"] += int(appearances)

    shared_squads_accounts: list[dict[str, Any]] = []
    for address, payload in sorted(
        shared_tracker.items(),
        key=lambda item: (len(item[1]["owners"]), item[1]["appearances"]),
        reverse=True,
    ):
        if len(payload["owners"]) < 2:
            continue
        meta = audit.fetch_account_meta(helius_rpc, address)
        shared_squads_accounts.append({
            "address": address,
            "owners": sorted(payload["owners"]),
            "appearances": payload["appearances"],
            "owner": meta.get("owner"),
            "executable": meta.get("executable"),
        })

    print("Building owner summaries ...", flush=True)
    owner_summaries = {
        owner: audit.summarize_owner_activity(txs)
        for owner, txs in owner_histories.items()
    }

    print("Building outputs ...", flush=True)
    registry = build_cluster_registry(
        helius_rpc=helius_rpc,
        owner_summaries=owner_summaries,
        owner_token_accounts=owner_token_accounts,
        shared_squads_accounts=shared_squads_accounts,
        relay_candidates=relay_candidates,
        cluster_direct_rows=cluster_direct_rows,
        cluster_forward_rows=cluster_forward_rows,
    )
    daily_map = build_daily_map(
        official=official,
        registry=registry,
        cluster_direct_rows=cluster_direct_rows,
        cluster_forward_rows=cluster_forward_rows,
        holder_rows=holder_rows,
    )

    tx_legs = []
    for rows in cluster_direct_rows.values():
        tx_legs.extend(rows)
    for rows in cluster_forward_rows.values():
        tx_legs.extend(rows)
    tx_legs.sort(key=lambda row: (row["timestamp"], row["signature"], row["leg_type"]))

    derived_registry_path = PUMP_DIR / "derived" / "buyback_execution_cluster_registry.json"
    derived_daily_map_path = PUMP_DIR / "derived" / "buyback_execution_daily_map.json"
    raw_tx_index_path = PUMP_DIR / "raw" / "buyback_execution_tx_index.json"
    report_path = PUMP_DIR / "reports" / "pump_token_purchases_cluster_report.md"

    fv.save_json(derived_registry_path, registry)
    fv.save_json(derived_daily_map_path, daily_map)
    fv.save_json(
        raw_tx_index_path,
        {
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "official_start_date": OFFICIAL_START_DATE,
            "prep_window_start_date": PREP_WINDOW_START_DATE,
            "prep_window_end_date": PREP_WINDOW_END_DATE,
            "owner_fetch_meta": owner_fetch_meta,
            "secondary_holder_token_account": secondary_token_account,
            "relay_candidates": relay_candidates,
            "shared_squads_accounts": shared_squads_accounts,
            "tx_legs": tx_legs,
        },
    )
    write_report(
        path=report_path,
        official=official,
        registry=registry,
        daily_map=daily_map,
        relay_candidates=relay_candidates,
    )

    print("Generated:")
    print(f"- {derived_registry_path}")
    print(f"- {derived_daily_map_path}")
    print(f"- {raw_tx_index_path}")
    print(f"- {report_path}")


if __name__ == "__main__":
    main()
