#!/usr/bin/env python3
"""
Audit PUMP buyback reconciliation across:
1) Official fees.pump.fun daily buyback API
2) Directly observed 3VK buyback execution
3) Cluster-holder accumulation across known/site-disclosed treasury holders

Outputs:
- data/pump/derived/buyback_candidate_registry.json
- data/pump/derived/buyback_daily_reconciliation.json
- data/pump/raw/buyback_cluster_audit_ledger.json
- data/pump/reports/pump_buyback_gap_audit.md
"""

from __future__ import annotations

import argparse
import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

import forensic_verify_pump_buybacks as fv


BASE_DIR = Path(__file__).resolve().parents[2]
PUMP_DIR = BASE_DIR / "data" / "pump"

OFFICIAL_BUYBACK_URL = "https://fees.pump.fun/api/buybacks"
DEFAULT_HELIUS_API_KEY = "6bb10a8e-f7b7-4216-a9ad-54d7cd762b0e"

BUYBACK_WALLET = fv.BUYBACK_WALLET
BUYBACK_TOKEN_ACCOUNT = fv.BUYBACK_TOKEN_ACCOUNT
TREASURY_WALLET = fv.TREASURY_WALLET
TREASURY_TOKEN_ACCOUNT = fv.TREASURY_TOKEN_ACCOUNT
STAKING_DISTRIBUTOR = fv.STAKING_DISTRIBUTOR
PUMP_MINT = fv.PUMP_MINT
TGE_TS = fv.TGE_TS

SITE_DISCLOSED_HOLDERS = {
    TREASURY_WALLET: "fees.pump.fun disclosed holder",
    "8PSmqJy63d4cAKRLKUitJCBLSjuL1cvZxC53vdCyjUey": "fees.pump.fun disclosed holder",
}
SECONDARY_HOLDER = "8PSmqJy63d4cAKRLKUitJCBLSjuL1cvZxC53vdCyjUey"

DEFAULT_MAX_PAGES = 500
DEFAULT_PAGE_LIMIT = 100
SQUADS_PROGRAM_ID = "SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf"
AUTOMATION_PROGRAM_SOURCES = {"SQUADS_V4", "JUPITER", "PUMP_AMM", "RAYDIUM", "ORCA", "OKX"}
LOOKUP_TABLE_OWNER = "AddressLookupTab1e1111111111111111111111111"


def load_runtime_config() -> tuple[str, str]:
    load_dotenv(BASE_DIR / ".env")
    helius_key = os.environ.get("HELIUS_API_KEY", "").strip() or DEFAULT_HELIUS_API_KEY
    helius_rpc = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"
    return helius_key, helius_rpc


def fetch_official_buybacks() -> dict[str, Any]:
    resp = requests.get(OFFICIAL_BUYBACK_URL, timeout=40)
    resp.raise_for_status()
    return resp.json()


def get_pump_token_accounts_by_owner(helius_rpc: str, owner: str) -> list[dict[str, Any]]:
    result = fv.rpc_call(
        helius_rpc,
        "getTokenAccountsByOwner",
        [owner, {"mint": PUMP_MINT}, {"encoding": "jsonParsed"}],
    )
    out = []
    for row in (result or {}).get("value", []) or []:
        info = ((row.get("account") or {}).get("data") or {}).get("parsed", {}).get("info", {})
        amount = (((info.get("tokenAmount") or {}).get("uiAmount")) or 0.0)
        out.append({
            "pubkey": row.get("pubkey"),
            "ui_amount": float(amount or 0.0),
            "mint": (info.get("mint") or ""),
            "owner": (info.get("owner") or ""),
        })
    return out


def fetch_all_history(
    *,
    helius_key: str,
    address: str,
    min_ts: int = TGE_TS,
    max_pages: int = DEFAULT_MAX_PAGES,
    page_limit: int = DEFAULT_PAGE_LIMIT,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    return fv.fetch_all_enhanced_txs(
        helius_key=helius_key,
        address=address,
        min_ts=min_ts,
        max_pages=max_pages,
        page_limit=page_limit,
    )


def summarize_owner_activity(txs: list[dict[str, Any]]) -> dict[str, Any]:
    src_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    by_day: Counter[str] = Counter()
    first_ts = None
    last_ts = None
    for tx in txs:
        ts = int(tx.get("timestamp", 0) or 0)
        if ts <= 0:
            continue
        src_counter[str(tx.get("source") or "UNKNOWN")] += 1
        type_counter[str(tx.get("type") or "UNKNOWN")] += 1
        by_day[fv.date_utc(ts)] += 1
        first_ts = ts if first_ts is None else min(first_ts, ts)
        last_ts = ts if last_ts is None else max(last_ts, ts)
    return {
        "tx_count": len(txs),
        "first_seen_utc": fv.dt_utc(first_ts),
        "last_seen_utc": fv.dt_utc(last_ts),
        "source_counts": dict(src_counter.most_common()),
        "type_counts": dict(type_counter.most_common()),
        "active_days": len(by_day),
    }


def parse_token_account_rows(
    *,
    txs: list[dict[str, Any]],
    token_account: str,
    owner: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tx in txs:
        sig = str(tx.get("signature") or "")
        ts = int(tx.get("timestamp", 0) or 0)
        if not sig or ts <= 0:
            continue

        pump_in = 0.0
        pump_out = 0.0
        inflow_senders: dict[str, float] = defaultdict(float)
        outflow_receivers: dict[str, float] = defaultdict(float)

        for tt in tx.get("tokenTransfers", []) or []:
            if str(tt.get("mint") or "") != PUMP_MINT:
                continue
            amount = float(tt.get("tokenAmount", 0.0) or 0.0)
            if amount <= 0:
                continue

            from_user = str(tt.get("fromUserAccount") or "")
            to_user = str(tt.get("toUserAccount") or "")
            from_token = str(tt.get("fromTokenAccount") or "")
            to_token = str(tt.get("toTokenAccount") or "")

            if to_token == token_account or to_user == owner:
                sender = from_user or from_token or "UNKNOWN"
                inflow_senders[sender] += amount
                pump_in += amount

            if from_token == token_account or from_user == owner:
                receiver = to_user or to_token or "UNKNOWN"
                outflow_receivers[receiver] += amount
                pump_out += amount

        if pump_in <= 0 and pump_out <= 0:
            continue

        rows.append({
            "signature": sig,
            "timestamp": ts,
            "datetime_utc": fv.dt_utc(ts),
            "date": fv.date_utc(ts),
            "helius_source": str(tx.get("source") or "UNKNOWN"),
            "helius_type": str(tx.get("type") or "UNKNOWN"),
            "description": str(tx.get("description") or ""),
            "token_account": token_account,
            "owner": owner,
            "pump_in": round(pump_in, 6),
            "pump_out": round(pump_out, 6),
            "pump_net": round(pump_in - pump_out, 6),
            "inflow_senders": [
                {"address": a, "pump_amount": round(v, 6)}
                for a, v in sorted(inflow_senders.items(), key=lambda kv: kv[1], reverse=True)
            ],
            "outflow_receivers": [
                {"address": a, "pump_amount": round(v, 6)}
                for a, v in sorted(outflow_receivers.items(), key=lambda kv: kv[1], reverse=True)
            ],
        })

    rows.sort(key=lambda r: (r["timestamp"], r["signature"]))
    return rows


def aggregate_amount_by_day(rows: list[dict[str, Any]], amount_key: str) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    for row in rows:
        out[str(row["date"])] += float(row.get(amount_key) or 0.0)
    return {k: round(v, 6) for k, v in sorted(out.items())}


def top_sender_totals(rows: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        for sender in row.get("inflow_senders", []) or []:
            counter[str(sender.get("address") or "")] += float(sender.get("pump_amount") or 0.0)
    return counter


def summarize_squads_accounts(txs: list[dict[str, Any]], focal_address: str) -> Counter[str]:
    counter: Counter[str] = Counter()
    for tx in txs:
        if str(tx.get("source") or "") != "SQUADS_V4" and str(tx.get("type") or "") != "CREATE_MULTISIG":
            continue
        for row in tx.get("accountData") or []:
            account = str(row.get("account") or "")
            if not account or account == focal_address:
                continue
            counter[account] += 1
    return counter


def fetch_account_meta(helius_rpc: str, address: str) -> dict[str, Any]:
    result = fv.rpc_call(helius_rpc, "getAccountInfo", [address, {"encoding": "base64"}])
    value = (result or {}).get("value") or {}
    return {
        "address": address,
        "owner": str(value.get("owner") or ""),
        "executable": bool(value.get("executable") or False),
        "lamports": int(value.get("lamports") or 0),
        "space": int(value.get("space") or 0),
    }


def build_dynamic_roles(
    *,
    relay_candidates: list[dict[str, Any]],
    shared_account_meta: dict[str, dict[str, Any]],
) -> dict[str, tuple[str, str, str]]:
    roles: dict[str, tuple[str, str, str]] = {}

    for relay in relay_candidates:
        address = str(relay.get("address") or "")
        if not address:
            continue
        roles[address] = (
            "secondary-holder execution relay candidate",
            "program_executor_candidate",
            "probable",
        )
        token_account = str(relay.get("token_account") or "")
        if token_account:
            roles[token_account] = (
                "secondary-holder execution relay token account",
                "program_executor_candidate",
                "probable",
            )

    for address, meta in shared_account_meta.items():
        owner = str(meta.get("owner") or "")
        if address == SQUADS_PROGRAM_ID or bool(meta.get("executable")):
            roles[address] = ("Squads V4 program", "automation_program", "confirmed")
        elif owner == SQUADS_PROGRAM_ID:
            roles[address] = ("Squads-owned program account", "squads_program_account", "probable")
        elif owner == LOOKUP_TABLE_OWNER:
            roles[address] = ("address lookup table used by Squads flow", "automation_lookup_table", "probable")
        else:
            roles[address] = ("shared Squads flow account", "shared_squads_account", "probable")

    return roles


def classify_treasury_row(row: dict[str, Any]) -> str:
    senders = {str(x.get("address") or "") for x in row.get("inflow_senders", []) or []}
    source = str(row.get("helius_source") or "")
    tx_type = str(row.get("helius_type") or "")

    if STAKING_DISTRIBUTOR in senders:
        return "staking_inflow"
    if BUYBACK_WALLET in senders:
        return "direct_3vk_transfer"
    if SECONDARY_HOLDER in senders:
        return "cluster_internal_from_8ps"
    if source == "SQUADS_V4" or tx_type == "CREATE_MULTISIG":
        return "probable_programmatic_inflow"
    if source in {"PUMP_FUN", "PUMP_AMM", "JUPITER", "RAYDIUM", "ORCA", "OKX"}:
        return "probable_programmatic_inflow"
    if senders & set(SITE_DISCLOSED_HOLDERS):
        return "probable_programmatic_inflow"
    return "other_inflow"


def classify_secondary_holder_row(row: dict[str, Any]) -> str:
    senders = {str(x.get("address") or "") for x in row.get("inflow_senders", []) or []}
    source = str(row.get("helius_source") or "")
    tx_type = str(row.get("helius_type") or "")

    if senders & {TREASURY_WALLET, TREASURY_TOKEN_ACCOUNT, BUYBACK_WALLET, BUYBACK_TOKEN_ACCOUNT}:
        return "cluster_internal_inflow"
    if source == "SQUADS_V4" or tx_type == "CREATE_MULTISIG":
        return "probable_programmatic_inflow"
    if source in {"PUMP_FUN", "PUMP_AMM", "JUPITER", "RAYDIUM", "ORCA", "OKX"}:
        return "probable_programmatic_inflow"
    return "other_inflow"


def build_reconciliation(
    *,
    official_daily: dict[str, Any],
    direct_buy_by_day: dict[str, float],
    direct_transfer_by_day: dict[str, float],
    holder_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    holder_daily: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in holder_rows:
        day = str(row["date"])
        classification = str(row.get("classification") or "unclassified")
        holder_daily[day]["secondary_holder_net_delta_pump"] += float(row.get("pump_net") or 0.0)
        holder_daily[day]["secondary_holder_inflow_pump"] += float(row.get("pump_in") or 0.0)
        holder_daily[day]["secondary_holder_outflow_pump"] += float(row.get("pump_out") or 0.0)
        holder_daily[day][f"secondary_holder_{classification}_pump"] += float(row.get("pump_in") or 0.0)

    days = sorted({
        *official_daily.keys(),
        *direct_buy_by_day.keys(),
        *direct_transfer_by_day.keys(),
        *holder_daily.keys(),
    })

    rows: list[dict[str, Any]] = []
    for day in days:
        official = official_daily.get(day, {}) or {}
        official_pump = float(official.get("pumpTokensBought") or 0.0)
        direct_buy = float(direct_buy_by_day.get(day) or 0.0)
        direct_transfer = float(direct_transfer_by_day.get(day) or 0.0)

        holder = holder_daily.get(day, {})

        holder_net = float(holder.get("secondary_holder_net_delta_pump") or 0.0)
        cluster_non_staking_net = direct_transfer + holder_net
        probable_hidden = max(holder_net, 0.0)

        row = {
            "date": day,
            "official_pump_bought": round(official_pump, 6),
            "official_tx_count": int(official.get("transactionCount") or 0),
            "official_buyback_usd": round(float(official.get("buybackUsd") or 0.0), 2),
            "confirmed_direct_buy_pump": round(direct_buy, 6),
            "confirmed_3vk_to_cluster_pump": round(direct_transfer, 6),
            "g8_confirmed_direct_transfer_pump": round(direct_transfer, 6),
            "secondary_holder_net_delta_pump": round(holder_net, 6),
            "cluster_non_staking_net_delta_pump": round(cluster_non_staking_net, 6),
            "probable_hidden_execution_pump": round(probable_hidden, 6),
            "gap_vs_direct_pump": round(official_pump - direct_buy, 6),
            "gap_vs_cluster_non_staking_pump": round(official_pump - max(cluster_non_staking_net, 0.0), 6),
        }
        rows.append(row)

    summary = {
        "official_total_pump": round(sum(float(r["official_pump_bought"]) for r in rows), 6),
        "direct_total_pump": round(sum(float(r["confirmed_direct_buy_pump"]) for r in rows), 6),
        "direct_transfer_total_pump": round(sum(float(r["confirmed_3vk_to_cluster_pump"]) for r in rows), 6),
        "cluster_non_staking_total_pump": round(sum(float(r["cluster_non_staking_net_delta_pump"]) for r in rows), 6),
        "probable_hidden_total_pump": round(sum(float(r["probable_hidden_execution_pump"]) for r in rows), 6),
    }
    official_total = float(summary["official_total_pump"] or 0.0)
    summary["coverage_vs_official_direct_ratio"] = round(
        float(summary["direct_total_pump"]) / official_total, 6
    ) if official_total > 0 else 0.0
    summary["coverage_vs_official_cluster_non_staking_ratio"] = round(
        max(float(summary["cluster_non_staking_total_pump"]), 0.0) / official_total, 6
    ) if official_total > 0 else 0.0
    return rows, summary


def build_candidate_registry(
    *,
    owner_summaries: dict[str, dict[str, Any]],
    owner_token_accounts: dict[str, list[dict[str, Any]]],
    treasury_rows: list[dict[str, Any]],
    holder_rows: list[dict[str, Any]],
    secondary_token_account: str | None,
    dynamic_roles: dict[str, tuple[str, str, str]],
    shared_account_meta: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    treasury_sender_totals = top_sender_totals(treasury_rows)
    holder_sender_totals = top_sender_totals(holder_rows)

    candidates: list[dict[str, Any]] = []
    known_roles = {
        BUYBACK_WALLET: ("Pump.fun buyback wallet", "direct_executor", "confirmed"),
        TREASURY_WALLET: ("Pump.fun treasury owner", "treasury_holder", "confirmed"),
        TREASURY_TOKEN_ACCOUNT: ("Pump.fun treasury token account", "treasury_holder", "confirmed"),
        STAKING_DISTRIBUTOR: ("PUMP staking distributor", "staking_related", "confirmed"),
        SECONDARY_HOLDER: ("fees.pump.fun secondary holder", "program_executor_candidate", "probable"),
    }
    if secondary_token_account:
        known_roles[secondary_token_account] = (
            "fees.pump.fun secondary holder token account",
            "program_executor_candidate",
            "probable",
        )
    known_roles.update(dynamic_roles)

    all_addresses = {
        *known_roles.keys(),
        *owner_summaries.keys(),
        *treasury_sender_totals.keys(),
        *holder_sender_totals.keys(),
        *shared_account_meta.keys(),
    }

    for address in sorted(a for a in all_addresses if a):
        label, role, confidence = known_roles.get(address, ("Unlabeled candidate", "possible_treasury_sender", "possible"))
        summary = owner_summaries.get(address, {})
        token_accounts = owner_token_accounts.get(address, [])
        notes: list[str] = []
        account_meta = shared_account_meta.get(address) or {}

        if address == SECONDARY_HOLDER:
            source_counts = summary.get("source_counts") or {}
            if "SQUADS_V4" in source_counts:
                notes.append("Owner activity includes SQUADS_V4 interactions.")
            type_counts = summary.get("type_counts") or {}
            if "CREATE_MULTISIG" in type_counts:
                notes.append("Owner activity includes CREATE_MULTISIG.")
            if token_accounts:
                notes.append("fees.pump.fun discloses this holder alongside G8 treasury.")

        treasury_inflow = round(float(treasury_sender_totals.get(address) or 0.0), 6)
        holder_inflow = round(float(holder_sender_totals.get(address) or 0.0), 6)
        if address not in known_roles:
            if treasury_inflow >= 1_000_000:
                notes.append("Observed sending >=1M PUMP into treasury token account.")
            if holder_inflow >= 1_000_000:
                notes.append("Observed sending >=1M PUMP into secondary disclosed holder account.")
        if account_meta:
            if account_meta.get("owner") == SQUADS_PROGRAM_ID:
                notes.append("Account is owned by Squads V4 program.")
            elif account_meta.get("owner") == LOOKUP_TABLE_OWNER:
                notes.append("Account is an address lookup table used in Squads flow.")
            if account_meta.get("executable"):
                notes.append("Executable program account.")

        candidates.append({
            "address": address,
            "label": label,
            "cluster": "pump_buyback_audit",
            "role": role,
            "confidence": confidence,
            "first_seen": summary.get("first_seen_utc"),
            "last_seen": summary.get("last_seen_utc"),
            "current_pump_balance": round(sum(float(x.get("ui_amount") or 0.0) for x in token_accounts), 6),
            "token_accounts": [x.get("pubkey") for x in token_accounts],
            "observed_treasury_inflow_pump": treasury_inflow,
            "observed_secondary_holder_inflow_pump": holder_inflow,
            "discovery_basis": notes,
            "related_programs": list((summary.get("source_counts") or {}).keys())[:10],
            "account_owner": account_meta.get("owner"),
            "account_executable": account_meta.get("executable"),
        })

    return {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "site_disclosed_holders": SITE_DISCLOSED_HOLDERS,
        "candidates": candidates,
    }


def top_gap_rows(rows: list[dict[str, Any]], key: str, limit: int = 12) -> list[dict[str, Any]]:
    filtered = [r for r in rows if abs(float(r.get(key) or 0.0)) > 0]
    return sorted(filtered, key=lambda r: abs(float(r.get(key) or 0.0)), reverse=True)[:limit]


def write_report(
    *,
    path: Path,
    official: dict[str, Any],
    reconciliation_rows: list[dict[str, Any]],
    reconciliation_summary: dict[str, Any],
    candidate_registry: dict[str, Any],
    owner_summaries: dict[str, dict[str, Any]],
    treasury_rows: list[dict[str, Any]],
    holder_rows: list[dict[str, Any]],
    relay_candidates: list[dict[str, Any]],
    shared_squads_accounts: list[dict[str, Any]],
) -> None:
    direct_cov = float(reconciliation_summary.get("coverage_vs_official_direct_ratio") or 0.0)
    cluster_cov = float(reconciliation_summary.get("coverage_vs_official_cluster_non_staking_ratio") or 0.0)

    treasury_sender_totals: Counter[str] = Counter()
    holder_sender_totals: Counter[str] = Counter()
    for row in treasury_rows:
        for s in row.get("inflow_senders", []) or []:
            treasury_sender_totals[str(s.get("address") or "")] += float(s.get("pump_amount") or 0.0)
    for row in holder_rows:
        for s in row.get("inflow_senders", []) or []:
            holder_sender_totals[str(s.get("address") or "")] += float(s.get("pump_amount") or 0.0)

    with open(path, "w", encoding="utf-8") as f:
        f.write("# PUMP Buyback Gap Audit\n\n")
        f.write(f"- Generated at (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n")
        f.write(f"- Official endpoint: `{OFFICIAL_BUYBACK_URL}`\n")
        f.write("- Chain source: Helius Enhanced API + Solana RPC\n\n")

        f.write("## Key Verdict\n\n")
        f.write(
            f"- Official cumulative buybacks: **{float(official.get('totalPumpTokensBought') or 0.0):,.2f} PUMP** "
            f"on **{float(official.get('totalBuybackUsd') or 0.0):,.2f} USD**.\n"
        )
        f.write(
            f"- Directly observed 3VK buybacks explain **{float(reconciliation_summary['direct_total_pump']):,.2f} PUMP** "
            f"({direct_cov:.2%} of official).\n"
        )
        f.write(
            f"- Cluster non-staking net accumulation across disclosed holders explains "
            f"**{float(reconciliation_summary['cluster_non_staking_total_pump']):,.2f} PUMP** "
            f"({cluster_cov:.2%} of official).\n"
        )
        second = next((c for c in candidate_registry["candidates"] if c["address"] == SECONDARY_HOLDER), None)
        if second:
            f.write(
                f"- `8PS...` is no longer a safe 'Top Whale' label. It is a **probable program/multisig-related holder**: "
                f"fees.pump.fun discloses it as a holder, it currently holds **{float(second['current_pump_balance']):,.2f} PUMP**, "
                f"has a dedicated PUMP token account, and owner activity includes `SQUADS_V4` / `CREATE_MULTISIG`.\n"
            )
        f.write(
            "- Existing '3VK is the only official buyback address' language is too strong. "
            "The defensible statement is: **3VK is the only directly confirmed executor in our current on-chain model; "
            "other holder/program paths exist and remain only partially attributed.**\n\n"
        )

        f.write("## Automation / Squads Findings\n\n")
        if relay_candidates:
            for relay in relay_candidates:
                f.write(
                    f"- `{relay['address']}` sent **{float(relay['observed_secondary_holder_inflow_pump']):,.2f} PUMP** into `8PS...`, "
                    f"has owner activity with `{', '.join(relay['source_counts'][:6])}`, and is a **probable execution relay** rather than a passive holder.\n"
                )
        if shared_squads_accounts:
            for row in shared_squads_accounts[:8]:
                owner = row.get("owner") or "-"
                f.write(
                    f"- Shared Squads account `{row['address']}` appears across `{', '.join(row['owners'])}` "
                    f"({row['appearances']} sightings), owner program `{owner}`.\n"
                )
        f.write("\n")

        f.write("## Candidate Registry\n\n")
        f.write("| address | label | role | confidence | current_pump_balance | notes |\n")
        f.write("|---|---|---|---|---:|---|\n")
        for c in candidate_registry["candidates"]:
            notes = "; ".join(str(x) for x in (c.get("discovery_basis") or [])) or "-"
            f.write(
                f"| `{c['address']}` | {c['label']} | {c['role']} | {c['confidence']} | "
                f"{float(c.get('current_pump_balance') or 0.0):,.2f} | {notes} |\n"
            )

        f.write("\n## Owner Activity Snapshot\n\n")
        for address in [BUYBACK_WALLET, TREASURY_WALLET, SECONDARY_HOLDER]:
            summary = owner_summaries.get(address) or {}
            f.write(f"### `{address}`\n\n")
            f.write(f"- tx_count: {summary.get('tx_count', 0)}\n")
            f.write(f"- first_seen: {summary.get('first_seen_utc') or '-'}\n")
            f.write(f"- last_seen: {summary.get('last_seen_utc') or '-'}\n")
            f.write(f"- source_counts: {json.dumps(summary.get('source_counts') or {}, ensure_ascii=False)}\n")
            f.write(f"- type_counts: {json.dumps(summary.get('type_counts') or {}, ensure_ascii=False)}\n\n")

        f.write("## Top PUMP Senders Into Treasury Token Account\n\n")
        f.write("| sender | PUMP sent to Hdt |\n")
        f.write("|---|---:|\n")
        for sender, amount in treasury_sender_totals.most_common(12):
            f.write(f"| `{sender}` | {amount:,.2f} |\n")

        f.write("\n## Top PUMP Senders Into Secondary Holder Token Account\n\n")
        f.write("| sender | PUMP sent to 8PS TA |\n")
        f.write("|---|---:|\n")
        for sender, amount in holder_sender_totals.most_common(12):
            f.write(f"| `{sender}` | {amount:,.2f} |\n")

        f.write("\n## Largest Gap Days\n\n")
        f.write("### Gap vs Direct 3VK Execution\n\n")
        f.write("| date | official_pump | direct_3vk | gap |\n")
        f.write("|---|---:|---:|---:|\n")
        for row in top_gap_rows(reconciliation_rows, "gap_vs_direct_pump"):
            f.write(
                f"| {row['date']} | {float(row['official_pump_bought']):,.2f} | "
                f"{float(row['confirmed_direct_buy_pump']):,.2f} | {float(row['gap_vs_direct_pump']):,.2f} |\n"
            )

        f.write("\n### Gap vs Cluster Non-Staking Net Delta\n\n")
        f.write("| date | official_pump | cluster_non_staking_net | gap |\n")
        f.write("|---|---:|---:|---:|\n")
        for row in top_gap_rows(reconciliation_rows, "gap_vs_cluster_non_staking_pump"):
            f.write(
                f"| {row['date']} | {float(row['official_pump_bought']):,.2f} | "
                f"{float(row['cluster_non_staking_net_delta_pump']):,.2f} | {float(row['gap_vs_cluster_non_staking_pump']):,.2f} |\n"
            )

        f.write("\n## Notes\n\n")
        f.write("- Official endpoint is daily aggregated and does not disclose execution addresses.\n")
        f.write("- 3VK direct buys and treasury-holder accumulation are different observability layers; they should not be naively summed.\n")
        f.write("- This v1 uses directly observed `3vk -> G8` transfers plus `8PS` token-account flow. It does not attempt full historical parsing of `Hdt...` because recent staking density makes that path too noisy for same-turn execution.\n")
        f.write("- This script automates on-chain + official reconciliation only. Dune / Arkham / DefiLlama remain secondary validation layers.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit PUMP buyback mismatch against official daily data.")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES, help="Max Helius pages per address.")
    parser.add_argument("--page-limit", type=int, default=DEFAULT_PAGE_LIMIT, help="Helius page size.")
    args = parser.parse_args()

    helius_key, helius_rpc = load_runtime_config()

    print("Fetching official buyback API ...", flush=True)
    official = fetch_official_buybacks()
    official_daily = official.get("dailyBuybacks", {}) or {}

    print("Resolving owner token accounts ...", flush=True)
    owner_token_accounts = {
        BUYBACK_WALLET: get_pump_token_accounts_by_owner(helius_rpc, BUYBACK_WALLET),
        TREASURY_WALLET: get_pump_token_accounts_by_owner(helius_rpc, TREASURY_WALLET),
        SECONDARY_HOLDER: get_pump_token_accounts_by_owner(helius_rpc, SECONDARY_HOLDER),
    }

    secondary_token_account = owner_token_accounts.get(SECONDARY_HOLDER, [{}])[0].get("pubkey") if owner_token_accounts.get(SECONDARY_HOLDER) else None

    owner_histories: dict[str, list[dict[str, Any]]] = {}
    owner_fetch_meta: dict[str, Any] = {}
    for owner in [BUYBACK_WALLET, TREASURY_WALLET, SECONDARY_HOLDER]:
        owner_max_pages = args.max_pages if owner == BUYBACK_WALLET else min(args.max_pages, 10)
        print(f"Fetching owner history: {owner} ...", flush=True)
        txs, meta = fetch_all_history(
            helius_key=helius_key,
            address=owner,
            min_ts=TGE_TS,
            max_pages=owner_max_pages,
            page_limit=args.page_limit,
        )
        owner_histories[owner] = txs
        owner_fetch_meta[owner] = meta
        print(f"  fetched {len(txs)} txs across {meta.get('pages_fetched')} pages", flush=True)

    print("Parsing direct 3VK buyback legs ...", flush=True)
    buy_legs, transfer_legs, direct_summary = fv.parse_buyback_legs(owner_histories[BUYBACK_WALLET])
    direct_buy_by_day = aggregate_amount_by_day(buy_legs, "pump_amount")
    direct_transfer_by_day = aggregate_amount_by_day(transfer_legs, "pump_amount")

    print(f"Fetching treasury token-account history: {TREASURY_TOKEN_ACCOUNT} ...", flush=True)
    treasury_rows = [
        {
            "signature": row["signature"],
            "timestamp": row["timestamp"],
            "datetime_utc": row["datetime_utc"],
            "date": row["date"],
            "helius_source": row["helius_source"],
            "helius_type": row["helius_type"],
            "description": "",
            "token_account": TREASURY_TOKEN_ACCOUNT,
            "owner": TREASURY_WALLET,
            "pump_in": row["pump_amount"],
            "pump_out": 0.0,
            "pump_net": row["pump_amount"],
            "inflow_senders": row.get("senders_to_treasury", []),
            "outflow_receivers": [],
            "classification": "direct_3vk_transfer",
        }
        for row in transfer_legs
    ]

    holder_rows: list[dict[str, Any]] = []
    holder_meta = {}
    secondary_txs: list[dict[str, Any]] = []
    if secondary_token_account:
        print(f"Fetching secondary holder token-account history: {secondary_token_account} ...", flush=True)
        secondary_txs, holder_meta = fetch_all_history(
            helius_key=helius_key,
            address=secondary_token_account,
            min_ts=TGE_TS,
            max_pages=min(args.max_pages, 40),
            page_limit=args.page_limit,
        )
        print(f"  fetched {len(secondary_txs)} txs across {holder_meta.get('pages_fetched')} pages", flush=True)
        holder_rows = parse_token_account_rows(
            txs=secondary_txs,
            token_account=secondary_token_account,
            owner=SECONDARY_HOLDER,
        )
        for row in holder_rows:
            row["classification"] = classify_secondary_holder_row(row)

    owner_summaries = {
        address: summarize_owner_activity(txs)
        for address, txs in owner_histories.items()
    }
    owner_summaries[TREASURY_TOKEN_ACCOUNT] = {
        "tx_count": len(treasury_rows),
        "first_seen_utc": treasury_rows[0]["datetime_utc"] if treasury_rows else "",
        "last_seen_utc": treasury_rows[-1]["datetime_utc"] if treasury_rows else "",
        "source_counts": dict(Counter(str(r["helius_source"]) for r in treasury_rows)),
        "type_counts": dict(Counter(str(r["helius_type"]) for r in treasury_rows)),
        "active_days": len({r["date"] for r in treasury_rows}),
    }
    if secondary_token_account:
        owner_summaries[secondary_token_account] = summarize_owner_activity(secondary_txs)

    holder_sender_totals = top_sender_totals(holder_rows)
    relay_candidates: list[dict[str, Any]] = []
    for sender, amount in holder_sender_totals.most_common(5):
        if not sender or sender in SITE_DISCLOSED_HOLDERS or amount < 1_000_000:
            continue
        print(f"Fetching relay-candidate history: {sender} ...", flush=True)
        relay_txs, relay_meta = fetch_all_history(
            helius_key=helius_key,
            address=sender,
            min_ts=TGE_TS,
            max_pages=min(args.max_pages, 20),
            page_limit=args.page_limit,
        )
        relay_summary = summarize_owner_activity(relay_txs)
        owner_histories[sender] = relay_txs
        owner_fetch_meta[sender] = relay_meta
        owner_summaries[sender] = relay_summary
        owner_token_accounts[sender] = get_pump_token_accounts_by_owner(helius_rpc, sender)
        relay_candidates.append({
            "address": sender,
            "observed_secondary_holder_inflow_pump": round(float(amount), 6),
            "source_counts": list((relay_summary.get("source_counts") or {}).keys()),
            "type_counts": list((relay_summary.get("type_counts") or {}).keys()),
            "token_account": (owner_token_accounts.get(sender) or [{}])[0].get("pubkey"),
        })

    squads_by_owner: dict[str, Counter[str]] = {}
    for owner in [BUYBACK_WALLET, SECONDARY_HOLDER, *[r["address"] for r in relay_candidates]]:
        txs = owner_histories.get(owner) or []
        if txs:
            squads_by_owner[owner] = summarize_squads_accounts(txs, owner)

    shared_squads_tracker: dict[str, dict[str, Any]] = {}
    for owner, counter in squads_by_owner.items():
        for address, count in counter.items():
            if address in {owner, "ComputeBudget111111111111111111111111111111", "11111111111111111111111111111111"}:
                continue
            bucket = shared_squads_tracker.setdefault(address, {"owners": set(), "appearances": 0})
            bucket["owners"].add(owner)
            bucket["appearances"] += int(count)

    shared_squads_accounts: list[dict[str, Any]] = []
    shared_account_meta: dict[str, dict[str, Any]] = {}
    for address, meta in sorted(
        shared_squads_tracker.items(),
        key=lambda kv: (len(kv[1]["owners"]), kv[1]["appearances"]),
        reverse=True,
    ):
        if len(meta["owners"]) < 2:
            continue
        account_meta = fetch_account_meta(helius_rpc, address)
        shared_account_meta[address] = account_meta
        shared_squads_accounts.append({
            "address": address,
            "owners": sorted(meta["owners"]),
            "appearances": meta["appearances"],
            "owner": account_meta.get("owner"),
            "executable": account_meta.get("executable"),
        })

    dynamic_roles = build_dynamic_roles(
        relay_candidates=relay_candidates,
        shared_account_meta=shared_account_meta,
    )

    reconciliation_rows, reconciliation_summary = build_reconciliation(
        official_daily=official_daily,
        direct_buy_by_day=direct_buy_by_day,
        direct_transfer_by_day=direct_transfer_by_day,
        holder_rows=holder_rows,
    )

    if secondary_token_account:
        owner_token_accounts[secondary_token_account] = [{
            "pubkey": secondary_token_account,
            "ui_amount": sum(float(x.get("ui_amount") or 0.0) for x in owner_token_accounts.get(SECONDARY_HOLDER, [])),
        }]
    owner_token_accounts[TREASURY_TOKEN_ACCOUNT] = [{
        "pubkey": TREASURY_TOKEN_ACCOUNT,
        "ui_amount": sum(float(x.get("ui_amount") or 0.0) for x in owner_token_accounts.get(TREASURY_WALLET, [])),
    }]

    candidate_registry = build_candidate_registry(
        owner_summaries=owner_summaries,
        owner_token_accounts=owner_token_accounts,
        treasury_rows=treasury_rows,
        holder_rows=holder_rows,
        secondary_token_account=secondary_token_account,
        dynamic_roles=dynamic_roles,
        shared_account_meta=shared_account_meta,
    )

    derived_registry_path = PUMP_DIR / "derived" / "buyback_candidate_registry.json"
    derived_recon_path = PUMP_DIR / "derived" / "buyback_daily_reconciliation.json"
    raw_ledger_path = PUMP_DIR / "raw" / "buyback_cluster_audit_ledger.json"
    report_path = PUMP_DIR / "reports" / "pump_buyback_gap_audit.md"

    print("Writing outputs ...", flush=True)
    fv.save_json(
        derived_registry_path,
        candidate_registry,
    )
    fv.save_json(
        derived_recon_path,
        {
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "official_last_updated": official.get("lastUpdated"),
            "summary": reconciliation_summary,
            "days": reconciliation_rows,
        },
    )
    fv.save_json(
        raw_ledger_path,
        {
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "official_summary": {
                "totalPumpTokensBought": official.get("totalPumpTokensBought"),
                "totalBuybackUsd": official.get("totalBuybackUsd"),
                "lastUpdated": official.get("lastUpdated"),
            },
            "owner_fetch_meta": owner_fetch_meta,
            "treasury_fetch_meta": {"mode": "derived_from_direct_3vk_transfers"},
            "secondary_holder_fetch_meta": holder_meta,
            "direct_summary": direct_summary,
            "relay_candidates": relay_candidates,
            "shared_squads_accounts": shared_squads_accounts,
            "buy_legs": buy_legs,
            "transfer_legs": transfer_legs,
            "treasury_rows": treasury_rows,
            "secondary_holder_rows": holder_rows,
        },
    )
    write_report(
        path=report_path,
        official=official,
        reconciliation_rows=reconciliation_rows,
        reconciliation_summary=reconciliation_summary,
        candidate_registry=candidate_registry,
        owner_summaries=owner_summaries,
        treasury_rows=treasury_rows,
        holder_rows=holder_rows,
        relay_candidates=relay_candidates,
        shared_squads_accounts=shared_squads_accounts,
    )

    print("Generated:")
    print(f"- {derived_registry_path}")
    print(f"- {derived_recon_path}")
    print(f"- {raw_ledger_path}")
    print(f"- {report_path}")


if __name__ == "__main__":
    main()
