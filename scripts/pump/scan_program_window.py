#!/usr/bin/env python3
"""
Scan a Solana address/program over a time window and surface candidate accounts
from transactions relevant to PUMP buybacks.

Examples:
  python3 scripts/pump/scan_program_window.py SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf --start-ts 1774051200 --end-ts 1774396800
  python3 scripts/pump/scan_program_window.py DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL --start-ts 1774051200 --end-ts 1774396800
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import forensic_verify_pump_buybacks as fv


BASE_DIR = Path(__file__).resolve().parents[2]
PUMP_MINT = fv.PUMP_MINT

KNOWN_ADDRESSES = {
    "8PSmqJy63d4cAKRLKUitJCBLSjuL1cvZxC53vdCyjUey": "holder_8ps",
    "2KEsnhnFiey3iA5zaenFVRSmuAGZdm7RbuG5VuAN69e1": "holder_8ps_ata",
    "G8CcfRffqZWHSAQJXLDfwbAkGE95SddUqVXnTrL4kqjm": "holder_g8",
    "HdtUyEC7TeLGrA7ddRRJWM6nUYk5UZsL9pJuWnXAFQ32": "holder_g8_ata",
    "9jHrTCwpDANHLNQz5cem6XLUBM8KiTWKe766Br6KVCXM": "relay_9jhr",
    "HxT8kiUKxJ7jdvWfDeRZQzQia4wyRCNN2iRBjMUzcimN": "relay_9jhr_ata",
    "3vkpy5YHqnqJTnA5doWTpcgKyZiYsaXYzYM9wm8s3WTi": "legacy_3vk",
    "Cz2xubgPSvqGqdx5fZNeNbJ7hD4d9WfHnQeB1sXyRNUq": "legacy_3vk_ata",
    "SQDS4ep65T869zMMBKyuUq6aD6EgTu8psMjkvj52pCf": "squads_v4_program",
    "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL": "jito_tip_payment_account",
    "DZboAojTvNwYbhW5rCARYLnWSKNumnd4khQG63aCxTfR": "lookup_table_candidate",
    "99mRw3EzdJZWEUjgp1nrU4WeHsukUBjbh7gYE7pm4F3c": "staking_distributor",
    "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb": "token_2022_program",
    "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA": "token_program",
    "11111111111111111111111111111111": "system_program",
    "ComputeBudget111111111111111111111111111111": "compute_budget",
    "AddressLookupTab1e1111111111111111111111111": "address_lookup_table_program",
}


def fetch_signatures(address: str, start_ts: int, end_ts: int, limit_pages: int, page_size: int, helius_rpc: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    before: str | None = None
    for _ in range(limit_pages):
        params: dict[str, Any] = {"limit": page_size}
        if before:
            params["before"] = before
        rows = fv.rpc_call(helius_rpc, "getSignaturesForAddress", [address, params]) or []
        if not rows:
            break
        stop = False
        for row in rows:
            ts = int(row.get("blockTime") or 0)
            if ts <= 0:
                continue
            if ts >= end_ts:
                continue
            if ts < start_ts:
                stop = True
                break
            out.append(row)
        before = rows[-1].get("signature")
        if stop:
            break
    return out


def tx_relevance(tx: dict[str, Any]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    meta = tx.get("meta") or {}
    msg = ((tx.get("transaction") or {}).get("message") or {})
    keys = [k["pubkey"] if isinstance(k, dict) else k for k in (msg.get("accountKeys") or [])]
    if PUMP_MINT in keys:
        reasons.append("pump_mint_in_keys")
    matched_known = [KNOWN_ADDRESSES[k] for k in keys if k in KNOWN_ADDRESSES]
    if matched_known:
        reasons.append("known_key:" + ",".join(sorted(set(matched_known))))
    for balances_key in ("preTokenBalances", "postTokenBalances"):
        for tb in meta.get(balances_key) or []:
            if tb.get("mint") == PUMP_MINT:
                reasons.append("pump_token_balance")
                owner = tb.get("owner")
                if owner in KNOWN_ADDRESSES:
                    reasons.append(f"known_balance_owner:{KNOWN_ADDRESSES[owner]}")
    return (len(reasons) > 0), reasons


def summarize_transactions(signatures: list[dict[str, Any]], helius_rpc: str, max_txs: int) -> dict[str, Any]:
    relevant_rows: list[dict[str, Any]] = []
    account_counter: Counter[str] = Counter()
    pump_balance_owner_counter: Counter[str] = Counter()
    tx_type_counter: Counter[str] = Counter()

    for row in signatures[:max_txs]:
        sig = str(row.get("signature") or "")
        ts = int(row.get("blockTime") or 0)
        tx = fv.rpc_call(
            helius_rpc,
            "getTransaction",
            [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
        )
        if not tx:
            continue
        relevant, reasons = tx_relevance(tx)
        if not relevant:
            continue
        meta = tx.get("meta") or {}
        msg = ((tx.get("transaction") or {}).get("message") or {})
        keys = [k["pubkey"] if isinstance(k, dict) else k for k in (msg.get("accountKeys") or [])]
        for key in keys:
            account_counter[key] += 1
        for balances_key in ("preTokenBalances", "postTokenBalances"):
            for tb in meta.get(balances_key) or []:
                if tb.get("mint") == PUMP_MINT and tb.get("owner"):
                    pump_balance_owner_counter[str(tb["owner"])] += 1
        tx_type_counter["relevant"] += 1
        relevant_rows.append({
            "signature": sig,
            "timestamp": ts,
            "datetime_utc": fv.dt_utc(ts),
            "reasons": reasons,
            "account_keys": keys,
            "pump_balance_owners": [
                str(tb.get("owner"))
                for balances_key in ("preTokenBalances", "postTokenBalances")
                for tb in (meta.get(balances_key) or [])
                if tb.get("mint") == PUMP_MINT and tb.get("owner")
            ],
            "logs_head": (meta.get("logMessages") or [])[:20],
        })

    top_accounts = []
    for address, count in account_counter.most_common(200):
        top_accounts.append({
            "address": address,
            "count": count,
            "known_label": KNOWN_ADDRESSES.get(address),
        })

    top_balance_owners = []
    for address, count in pump_balance_owner_counter.most_common(100):
        top_balance_owners.append({
            "address": address,
            "count": count,
            "known_label": KNOWN_ADDRESSES.get(address),
        })

    return {
        "relevant_tx_count": len(relevant_rows),
        "top_accounts": top_accounts,
        "top_pump_balance_owners": top_balance_owners,
        "rows": relevant_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan a program/account window for PUMP-relevant txs.")
    parser.add_argument("address")
    parser.add_argument("--start-ts", type=int, required=True)
    parser.add_argument("--end-ts", type=int, required=True)
    parser.add_argument("--limit-pages", type=int, default=40)
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--max-txs", type=int, default=500)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    helius_rpc = "https://mainnet.helius-rpc.com/?api-key=6bb10a8e-f7b7-4216-a9ad-54d7cd762b0e"
    sigs = fetch_signatures(
        address=args.address,
        start_ts=args.start_ts,
        end_ts=args.end_ts,
        limit_pages=args.limit_pages,
        page_size=args.page_size,
        helius_rpc=helius_rpc,
    )
    result = {
        "address": args.address,
        "start_ts": args.start_ts,
        "end_ts": args.end_ts,
        "signature_count_in_window": len(sigs),
        "signatures": [
            {
                "signature": str(row.get("signature") or ""),
                "blockTime": int(row.get("blockTime") or 0),
                "datetime_utc": fv.dt_utc(int(row.get("blockTime") or 0)),
            }
            for row in sigs
        ],
        "analysis": summarize_transactions(sigs, helius_rpc=helius_rpc, max_txs=args.max_txs),
    }

    if args.output:
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2))
        print(path)
        return

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
