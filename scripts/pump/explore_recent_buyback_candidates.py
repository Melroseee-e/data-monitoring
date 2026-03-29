#!/usr/bin/env python3
"""
Explore recent PUMP activity for holder owners, token accounts, and shared accounts.

Examples:
  python3 scripts/pump/explore_recent_buyback_candidates.py owner 8PS... --start 2026-03-21 --end 2026-03-24
  python3 scripts/pump/explore_recent_buyback_candidates.py token-owner 8PS... --start 2026-03-21 --end 2026-03-24
  python3 scripts/pump/explore_recent_buyback_candidates.py owner 9jHr... --start 2026-03-21 --end 2026-03-24 --show-accounts
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

import audit_pump_buyback_reconciliation as audit
import forensic_verify_pump_buybacks as fv


def parse_day(day: str) -> datetime:
    return datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def date_span(start: str, end: str) -> list[str]:
    cur = parse_day(start)
    end_dt = parse_day(end)
    out: list[str] = []
    while cur <= end_dt:
        out.append(cur.strftime("%Y-%m-%d"))
        cur += timedelta(days=1)
    return out


def summarize_token_rows(rows: list[dict[str, Any]], days: list[str]) -> None:
    for day in days:
        senders: Counter[str] = Counter()
        receivers: Counter[str] = Counter()
        net = 0.0
        row_count = 0
        for row in rows:
            if row["date"] != day:
                continue
            row_count += 1
            net += float(row["pump_net"])
            for item in row.get("inflow_senders", []) or []:
                senders[str(item.get("address") or "")] += float(item.get("pump_amount") or 0.0)
            for item in row.get("outflow_receivers", []) or []:
                receivers[str(item.get("address") or "")] += float(item.get("pump_amount") or 0.0)
        print(f"\nDAY {day} rows={row_count} net={round(net, 6)}")
        print("  top inflow senders:")
        for address, amount in senders.most_common(12):
            print(f"    {address} {round(amount, 6)}")
        print("  top outflow receivers:")
        for address, amount in receivers.most_common(12):
            print(f"    {address} {round(amount, 6)}")


def summarize_owner_txs(
    txs: list[dict[str, Any]],
    days: list[str],
    *,
    show_accounts: bool,
) -> None:
    day_set = set(days)
    subset = [tx for tx in txs if fv.date_utc(int(tx.get("timestamp", 0) or 0)) in day_set]
    print(f"matching owner tx count: {len(subset)}")
    for tx in subset:
        ts = int(tx.get("timestamp", 0) or 0)
        print(
            f"\n{fv.dt_utc(ts)} source={tx.get('source')} type={tx.get('type')} "
            f"sig={tx.get('signature')}"
        )
        print(f"  description={tx.get('description')}")
        if show_accounts:
            accounts = [str(row.get("account") or "") for row in (tx.get("accountData") or []) if row.get("account")]
            print(f"  accounts={accounts[:40]}")
        transfers = []
        for tt in tx.get("tokenTransfers", []) or []:
            if str(tt.get("mint") or "") != audit.PUMP_MINT:
                continue
            transfers.append(
                (
                    str(tt.get("fromUserAccount") or tt.get("fromTokenAccount") or ""),
                    str(tt.get("toUserAccount") or tt.get("toTokenAccount") or ""),
                    float(tt.get("tokenAmount") or 0.0),
                )
            )
        if transfers:
            print("  pump transfers:")
            for from_addr, to_addr, amount in transfers[:20]:
                print(f"    {from_addr} -> {to_addr} : {round(amount, 6)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Explore recent PUMP candidate activity.")
    parser.add_argument("mode", choices=["owner", "token-owner"])
    parser.add_argument("address")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--max-pages", type=int, default=40)
    parser.add_argument("--page-limit", type=int, default=100)
    parser.add_argument("--show-accounts", action="store_true")
    args = parser.parse_args()

    helius_key, helius_rpc = audit.load_runtime_config()
    days = date_span(args.start, args.end)

    if args.mode == "owner":
        txs, meta = audit.fetch_all_history(
            helius_key=helius_key,
            address=args.address,
            min_ts=audit.TGE_TS,
            max_pages=args.max_pages,
            page_limit=args.page_limit,
        )
        print(f"fetched owner txs={len(txs)} oldest={meta.get('oldest_seen_date')} max_pages_hit={meta.get('max_pages_hit')}")
        summarize_owner_txs(txs, days, show_accounts=args.show_accounts)
        return

    token_accounts = audit.get_pump_token_accounts_by_owner(helius_rpc, args.address)
    print(f"token accounts={token_accounts}")
    if not token_accounts:
        return
    token_account = token_accounts[0]["pubkey"]
    txs, meta = audit.fetch_all_history(
        helius_key=helius_key,
        address=token_account,
        min_ts=audit.TGE_TS,
        max_pages=args.max_pages,
        page_limit=args.page_limit,
    )
    print(f"fetched token-account txs={len(txs)} oldest={meta.get('oldest_seen_date')} max_pages_hit={meta.get('max_pages_hit')}")
    rows = audit.parse_token_account_rows(
        txs=txs,
        token_account=token_account,
        owner=args.address,
    )
    summarize_token_rows(rows, days)


if __name__ == "__main__":
    main()
