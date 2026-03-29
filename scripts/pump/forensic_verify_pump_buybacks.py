#!/usr/bin/env python3
"""
Forensic verification for PUMP buyback activity.

Sources:
1) Source A: Helius Enhanced API (on-chain parsed txs, primary)
2) Source B: Solana RPC getTransaction (independent on-chain verification)
3) Source C: Research milestones from pump_buyback_analysis.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
PUMP_DIR = DATA_DIR / "pump"

BUYBACK_WALLET = "3vkpy5YHqnqJTnA5doWTpcgKyZiYsaXYzYM9wm8s3WTi"
BUYBACK_TOKEN_ACCOUNT = "Cz2xubgPSvqGqdxCL5ri4y9FTtBDLJNXQhhj2muw8kbt"
TREASURY_WALLET = "G8CcfRffqZWHSAQJXLDfwbAkGE95SddUqVXnTrL4kqjm"
TREASURY_TOKEN_ACCOUNT = "HdtUyEC7TeLGrA7ddRRJWM6nUYk5UZsL9pJuWnXAFQ32"
STAKING_DISTRIBUTOR = "99mRw3EzdJZWEUjgp1nrU4WeHsukUBjbh7gYE7pm4F3c"
PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
TGE_TS = int(datetime(2025, 7, 12, tzinfo=timezone.utc).timestamp())

DEX_SOURCES = {"PUMP_AMM", "JUPITER", "RAYDIUM", "ORCA", "OKX"}
DEX_TYPES = {"SWAP", "DEX_TRADE"}
WSOL_MINT = "So11111111111111111111111111111111111111112"


def dt_utc(ts: int | float | None) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def date_utc(ts: int | float | None) -> str:
    if not ts:
        return ""
    return datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%d")


def load_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_price_map() -> dict[str, float]:
    chart_path = PUMP_DIR / "derived" / "pump_behavior_chart_data.json"
    if chart_path.exists():
        d = load_json(chart_path)
        out: dict[str, float] = {}
        for c in (d.get("price", {}) or {}).get("candles", []) or []:
            day = c.get("date")
            close = c.get("close")
            if isinstance(day, str) and isinstance(close, (int, float)):
                out[day] = float(close)
        if out:
            return out
    return {}


def load_sol_price_map_from_binance() -> tuple[dict[str, float], str]:
    """
    Daily SOL close prices for converting observed SOL spend to USD.
    """
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": "SOLUSDT", "interval": "1d", "limit": 1000}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    rows = resp.json()
    out: dict[str, float] = {}
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, list) or len(row) < 5:
                continue
            ts_ms = int(row[0])
            day = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            out[day] = float(row[4])
    return out, "Binance SOLUSDT 1d close"


def http_get(url: str, *, params: dict[str, Any] | None = None, timeout: int = 40, retries: int = 4) -> Any:
    backoff = 1.0
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
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


def rpc_call(helius_rpc: str, method: str, params: list[Any], retries: int = 4) -> Any:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    backoff = 1.0
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(helius_rpc, json=payload, timeout=40)
            if resp.status_code == 429:
                time.sleep(backoff)
                backoff = min(backoff * 2, 8.0)
                continue
            resp.raise_for_status()
            d = resp.json()
            if "error" in d:
                raise RuntimeError(str(d["error"]))
            return d.get("result")
        except Exception:
            if attempt == retries:
                raise
            time.sleep(backoff)
            backoff = min(backoff * 2, 8.0)
    raise RuntimeError("unreachable")


def fetch_all_enhanced_txs(
    *,
    helius_key: str,
    address: str,
    min_ts: int,
    max_pages: int = 500,
    page_limit: int = 100,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    url = f"https://api.helius.xyz/v0/addresses/{address}/transactions"
    before: str | None = None
    out: list[dict[str, Any]] = []
    reached_min_ts = False
    oldest_seen_ts = None
    pages_fetched = 0
    for page in range(1, max_pages + 1):
        pages_fetched = page
        params: dict[str, Any] = {"api-key": helius_key, "limit": page_limit}
        if before:
            params["before"] = before
        items = http_get(url, params=params)
        if not items:
            break
        out.extend(items)
        oldest_ts = min(int(tx.get("timestamp", 0) or 0) for tx in items)
        oldest_seen_ts = oldest_ts if oldest_seen_ts is None else min(oldest_seen_ts, oldest_ts)
        if oldest_ts and oldest_ts < min_ts:
            reached_min_ts = True
            break
        before = items[-1].get("signature")
        if not before:
            break
        time.sleep(0.06)
    filtered = [tx for tx in out if int(tx.get("timestamp", 0) or 0) >= min_ts]
    meta = {
        "pages_fetched": pages_fetched,
        "oldest_seen_ts": oldest_seen_ts,
        "oldest_seen_date": date_utc(oldest_seen_ts),
        "reached_min_ts": reached_min_ts,
        "max_pages_hit": pages_fetched >= max_pages and not reached_min_ts,
    }
    return filtered, meta


def parse_buyback_legs(txs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """
    Extract:
    - buy_legs: PUMP inflow into buyback token account from DEX-like swaps.
    - transfer_legs: PUMP moved from buyback token account to treasury token account.
    """
    buy_legs: list[dict[str, Any]] = []
    transfer_legs: list[dict[str, Any]] = []

    source_counter: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    monthly_counter: Counter[str] = Counter()

    for tx in txs:
        sig = str(tx.get("signature") or "")
        ts = int(tx.get("timestamp", 0) or 0)
        day = date_utc(ts)
        source = str(tx.get("source") or "")
        tx_type = str(tx.get("type") or "")

        pump_to_buyback = 0.0
        pump_to_treasury = 0.0
        pump_buyback_to_treasury = 0.0
        wsol_out_from_buyback = 0.0

        by_sender_buyback: dict[str, float] = defaultdict(float)
        by_sender_treasury: dict[str, float] = defaultdict(float)

        for tt in tx.get("tokenTransfers", []) or []:
            amount = float(tt.get("tokenAmount", 0.0) or 0.0)
            if amount <= 0:
                continue

            mint = str(tt.get("mint") or "")
            from_user = str(tt.get("fromUserAccount") or "")
            to_user = str(tt.get("toUserAccount") or "")
            from_token_account = str(tt.get("fromTokenAccount") or "")
            to_token_account = str(tt.get("toTokenAccount") or "")

            if mint == WSOL_MINT and from_user == BUYBACK_WALLET:
                wsol_out_from_buyback += amount

            if mint != PUMP_MINT:
                continue

            if to_token_account == BUYBACK_TOKEN_ACCOUNT or to_user == BUYBACK_WALLET:
                pump_to_buyback += amount
                by_sender_buyback[from_user] += amount

            if to_token_account == TREASURY_TOKEN_ACCOUNT:
                pump_to_treasury += amount
                by_sender_treasury[from_user] += amount

            if (
                (from_token_account == BUYBACK_TOKEN_ACCOUNT or from_user == BUYBACK_WALLET)
                and to_token_account == TREASURY_TOKEN_ACCOUNT
            ):
                pump_buyback_to_treasury += amount

        native_out_sol = sum(
            float(nt.get("amount", 0) or 0) / 1e9
            for nt in (tx.get("nativeTransfers", []) or [])
            if str(nt.get("fromUserAccount") or "") == BUYBACK_WALLET
        )
        # Prefer WSOL token out as quote spend; fallback to native SOL out when WSOL is unavailable.
        sol_spent = wsol_out_from_buyback if wsol_out_from_buyback > 0 else native_out_sol

        is_dex_buy_leg = pump_to_buyback > 0 and (tx_type in DEX_TYPES or source in DEX_SOURCES)
        if is_dex_buy_leg:
            source_counter[source or "UNKNOWN"] += 1
            type_counter[tx_type or "UNKNOWN"] += 1
            monthly_counter[day[:7]] += 1
            buy_legs.append({
                "signature": sig,
                "timestamp": ts,
                "datetime_utc": dt_utc(ts),
                "date": day,
                "pump_amount": round(pump_to_buyback, 6),
                "helius_source": source,
                "helius_type": tx_type,
                "sol_spent": round(sol_spent, 9),
                "wsol_out_from_buyback": round(wsol_out_from_buyback, 9),
                "native_out_from_buyback_sol": round(native_out_sol, 9),
                "senders": [
                    {"address": k, "pump_amount": round(v, 6)}
                    for k, v in sorted(by_sender_buyback.items(), key=lambda kv: kv[1], reverse=True)
                ],
            })

        if pump_buyback_to_treasury > 0:
            transfer_legs.append({
                "signature": sig,
                "timestamp": ts,
                "datetime_utc": dt_utc(ts),
                "date": day,
                "pump_amount": round(pump_buyback_to_treasury, 6),
                "pump_to_treasury_total_in_tx": round(pump_to_treasury, 6),
                "helius_source": source,
                "helius_type": tx_type,
                "senders_to_treasury": [
                    {"address": k, "pump_amount": round(v, 6)}
                    for k, v in sorted(by_sender_treasury.items(), key=lambda kv: kv[1], reverse=True)
                ],
                "classification": "buyback_wallet_to_treasury",
            })

    buy_legs.sort(key=lambda r: (r["timestamp"], r["signature"]))
    transfer_legs.sort(key=lambda r: (r["timestamp"], r["signature"]))

    summary = {
        "buy_leg_source_counts": dict(source_counter),
        "buy_leg_type_counts": dict(type_counter),
        "buy_leg_monthly_counts": dict(monthly_counter),
    }
    return buy_legs, transfer_legs, summary


def group_batches(rows: list[dict[str, Any]], *, window_seconds: int, batch_prefix: str) -> list[dict[str, Any]]:
    if not rows:
        return []

    items = sorted(rows, key=lambda r: (r["timestamp"], r["signature"]))
    groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = [items[0]]

    for row in items[1:]:
        if row["timestamp"] - current[-1]["timestamp"] <= window_seconds:
            current.append(row)
        else:
            groups.append(current)
            current = [row]
    groups.append(current)

    out: list[dict[str, Any]] = []
    for idx, g in enumerate(groups, start=1):
        first_ts = g[0]["timestamp"]
        last_ts = g[-1]["timestamp"]
        sigs = sorted({r["signature"] for r in g})
        total = sum(float(r["pump_amount"]) for r in g)
        span_minutes = (last_ts - first_ts) / 60.0 if last_ts >= first_ts else 0.0
        out.append({
            "batch_id": f"{batch_prefix}_{idx:04d}",
            "start_ts": first_ts,
            "end_ts": last_ts,
            "start_utc": dt_utc(first_ts),
            "end_utc": dt_utc(last_ts),
            "date": date_utc(first_ts),
            "signature_count": len(sigs),
            "signatures": sigs,
            "pump_amount": round(total, 6),
            "span_minutes": round(span_minutes, 2),
        })
    return out


def estimate_usd(rows: list[dict[str, Any]], price_map: dict[str, float]) -> None:
    for row in rows:
        day = row.get("date")
        p = price_map.get(day) if isinstance(day, str) else None
        row["pump_close_price_usd"] = p
        if isinstance(p, (int, float)):
            row["usd_est_close"] = round(float(row["pump_amount"]) * float(p), 2)
            row["usd_est_method"] = "pump_amount * daily_close_price"
        else:
            row["usd_est_close"] = None
            row["usd_est_method"] = "unavailable_price"


def estimate_buy_leg_cost_via_sol(buy_legs: list[dict[str, Any]], sol_price_map: dict[str, float]) -> None:
    for row in buy_legs:
        sol_spent = float(row.get("sol_spent") or 0.0)
        day = str(row.get("date") or "")
        sol_price = sol_price_map.get(day)
        row["sol_close_price_usd"] = sol_price
        if sol_spent > 0 and isinstance(sol_price, (int, float)):
            usd = sol_spent * float(sol_price)
            row["usd_est_sol_close"] = round(usd, 2)
            pump_amount = float(row.get("pump_amount") or 0.0)
            row["implied_price_usd_per_pump_sol_close"] = round(usd / pump_amount, 10) if pump_amount > 0 else None
            row["usd_est_sol_method"] = "sol_spent * sol_daily_close"
        else:
            row["usd_est_sol_close"] = None
            row["implied_price_usd_per_pump_sol_close"] = None
            row["usd_est_sol_method"] = "unavailable_sol_price_or_spend"


def attach_buy_batch_cost_from_legs(buy_batches: list[dict[str, Any]], buy_legs: list[dict[str, Any]]) -> None:
    leg_by_sig = {str(r.get("signature")): r for r in buy_legs}
    for b in buy_batches:
        sigs = b.get("signatures", []) or []
        sol_spent = 0.0
        usd_sol = 0.0
        usd_sol_known = False
        for sig in sigs:
            leg = leg_by_sig.get(str(sig))
            if not leg:
                continue
            sol_spent += float(leg.get("sol_spent") or 0.0)
            if isinstance(leg.get("usd_est_sol_close"), (int, float)):
                usd_sol += float(leg["usd_est_sol_close"])
                usd_sol_known = True
        b["sol_spent"] = round(sol_spent, 9)
        if usd_sol_known:
            b["usd_est_sol_close"] = round(usd_sol, 2)
            pump_amount = float(b.get("pump_amount") or 0.0)
            b["implied_price_usd_per_pump_sol_close"] = round(usd_sol / pump_amount, 10) if pump_amount > 0 else None
        else:
            b["usd_est_sol_close"] = None
            b["implied_price_usd_per_pump_sol_close"] = None


def estimate_overall_cost(rows: list[dict[str, Any]], *, prefer_sol_cost: bool = False) -> dict[str, Any]:
    total_pump = sum(float(r.get("pump_amount") or 0.0) for r in rows)
    usd_field = "usd_est_sol_close" if prefer_sol_cost else "usd_est_close"
    known_usd = [float(r[usd_field]) for r in rows if isinstance(r.get(usd_field), (int, float))]
    total_usd = sum(known_usd)
    total_pump_with_price = sum(
        float(r.get("pump_amount") or 0.0)
        for r in rows
        if isinstance(r.get(usd_field), (int, float))
    )
    avg_price = (total_usd / total_pump_with_price) if total_pump_with_price > 0 else None
    coverage = (total_pump_with_price / total_pump) if total_pump > 0 else 0.0
    total_sol_spent = sum(float(r.get("sol_spent") or 0.0) for r in rows)
    return {
        "total_pump": round(total_pump, 6),
        "total_sol_spent": round(total_sol_spent, 9),
        "usd_est_close_total": round(total_usd, 2),
        "avg_price_usd_est_close": round(avg_price, 8) if isinstance(avg_price, float) else None,
        "pump_price_coverage_ratio": round(coverage, 6),
        "usd_method": usd_field,
    }


def infer_execution_style(buy_legs: list[dict[str, Any]], buy_batches: list[dict[str, Any]]) -> dict[str, Any]:
    if not buy_legs:
        return {
            "style": "no_observed_direct_buy_legs",
            "reason": "No DEX-like PUMP inflows into buyback token account detected in scope.",
        }

    by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in buy_legs:
        by_day[row["date"]].append(row)

    day_rows = []
    twap_like_amount = 0.0
    total_amount = sum(float(r["pump_amount"]) for r in buy_legs)
    all_intervals = []

    for day, rows in sorted(by_day.items()):
        rows = sorted(rows, key=lambda x: (x["timestamp"], x["signature"]))
        count = len(rows)
        span_minutes = (rows[-1]["timestamp"] - rows[0]["timestamp"]) / 60.0 if count > 1 else 0.0
        day_amount = sum(float(x["pump_amount"]) for x in rows)

        for i in range(1, count):
            all_intervals.append((rows[i]["timestamp"] - rows[i - 1]["timestamp"]) / 60.0)

        # Heuristic:
        # - >=3 trades in a day and spread over >=30min -> TWAP-like slicing
        is_twap_like_day = count >= 3 and span_minutes >= 30.0
        if is_twap_like_day:
            twap_like_amount += day_amount

        day_rows.append({
            "date": day,
            "trade_count": count,
            "span_minutes": round(span_minutes, 2),
            "pump_amount": round(day_amount, 6),
            "twap_like_day": is_twap_like_day,
        })

    twap_amount_ratio = (twap_like_amount / total_amount) if total_amount > 0 else 0.0
    avg_trades_per_active_day = len(buy_legs) / max(len(by_day), 1)
    median_interval = statistics.median(all_intervals) if all_intervals else None

    if twap_amount_ratio >= 0.5 or avg_trades_per_active_day >= 4:
        style = "twap_like_fragmented"
        reason = "Most observed direct buy volume is executed via multi-trade fragmented sessions."
    elif len(buy_legs) <= 3:
        style = "single_or_few_block_trades"
        reason = "Only a small number of direct buy legs observed."
    else:
        style = "mixed_execution"
        reason = "Observed both fragmented and concentrated direct buy sessions."

    return {
        "style": style,
        "reason": reason,
        "buy_leg_count": len(buy_legs),
        "buy_batch_count": len(buy_batches),
        "active_day_count": len(by_day),
        "avg_trades_per_active_day": round(avg_trades_per_active_day, 3),
        "twap_like_amount_ratio": round(twap_amount_ratio, 6),
        "median_intertrade_minutes": round(float(median_interval), 3) if isinstance(median_interval, (int, float)) else None,
        "day_breakdown": day_rows,
    }


def _account_key_string(x: Any) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        return str(x.get("pubkey") or "")
    return ""


def verify_signatures_with_rpc(helius_rpc: str, signatures: list[str]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for i, sig in enumerate(signatures, start=1):
        tx = rpc_call(
            helius_rpc,
            "getTransaction",
            [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
        )
        if not tx:
            out[sig] = {"rpc_found": False}
            continue

        pre: dict[int, dict[str, Any]] = {}
        post: dict[int, dict[str, Any]] = {}
        for b in (tx.get("meta", {}) or {}).get("preTokenBalances", []) or []:
            if b.get("mint") == PUMP_MINT:
                pre[int(b.get("accountIndex", -1))] = b
        for b in (tx.get("meta", {}) or {}).get("postTokenBalances", []) or []:
            if b.get("mint") == PUMP_MINT:
                post[int(b.get("accountIndex", -1))] = b

        keys_raw = (tx.get("transaction", {}) or {}).get("message", {}).get("accountKeys", []) or []
        keys = [_account_key_string(x) for x in keys_raw]

        buyback_delta = 0.0
        treasury_delta = 0.0
        for idx in set(pre.keys()) | set(post.keys()):
            if idx < 0 or idx >= len(keys):
                continue
            key = keys[idx]
            pb = pre.get(idx, {})
            qb = post.get(idx, {})
            p = float((pb.get("uiTokenAmount", {}) or {}).get("uiAmount") or 0.0)
            q = float((qb.get("uiTokenAmount", {}) or {}).get("uiAmount") or 0.0)
            d = q - p
            if key == BUYBACK_TOKEN_ACCOUNT:
                buyback_delta += d
            if key == TREASURY_TOKEN_ACCOUNT:
                treasury_delta += d

        out[sig] = {
            "rpc_found": True,
            "buyback_token_account_delta_pump": round(buyback_delta, 6),
            "treasury_token_account_delta_pump": round(treasury_delta, 6),
        }
        if i % 50 == 0:
            time.sleep(0.1)
    return out


def select_signatures_for_rpc(buy_batches: list[dict[str, Any]], transfer_batches: list[dict[str, Any]], limit: int) -> list[str]:
    all_sigs = sorted({
        sig for b in buy_batches + transfer_batches for sig in (b.get("signatures") or [])
    })
    if limit <= 0 or len(all_sigs) <= limit:
        return all_sigs

    merged = sorted(
        buy_batches + transfer_batches,
        key=lambda x: float(x.get("pump_amount", 0.0)),
        reverse=True,
    )
    out: list[str] = []
    seen: set[str] = set()
    for b in merged:
        for sig in b.get("signatures", []):
            if sig in seen:
                continue
            seen.add(sig)
            out.append(sig)
            if len(out) >= limit:
                return out
    return out


def map_milestones(
    milestones: list[dict[str, Any]],
    buy_batches: list[dict[str, Any]],
    transfer_batches: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    buy_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    transfer_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for b in buy_batches:
        buy_by_date[b["date"]].append(b)
    for b in transfer_batches:
        transfer_by_date[b["date"]].append(b)

    out = []
    for m in milestones:
        day = str(m.get("date") or "")
        buy_same_day = buy_by_date.get(day, [])
        transfer_same_day = transfer_by_date.get(day, [])
        out.append({
            "milestone_date": day,
            "milestone_event": m.get("event"),
            "milestone_cumulative_usd": m.get("cumulative_usd"),
            "same_day_buy_batch_count": len(buy_same_day),
            "same_day_buy_pump_amount": round(sum(float(x["pump_amount"]) for x in buy_same_day), 6),
            "same_day_transfer_batch_count": len(transfer_same_day),
            "same_day_transfer_pump_amount": round(sum(float(x["pump_amount"]) for x in transfer_same_day), 6),
            "same_day_buy_batch_ids": [x["batch_id"] for x in buy_same_day],
            "same_day_transfer_batch_ids": [x["batch_id"] for x in transfer_same_day],
        })
    return out


def write_batches_csv(path: Path, batches: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "batch_id",
            "date",
            "start_utc",
            "end_utc",
            "signature_count",
            "span_minutes",
            "pump_amount",
            "sol_spent",
            "pump_close_price_usd",
            "usd_est_close",
            "usd_est_sol_close",
            "implied_price_usd_per_pump_sol_close",
        ])
        for b in batches:
            w.writerow([
                b.get("batch_id"),
                b.get("date"),
                b.get("start_utc"),
                b.get("end_utc"),
                b.get("signature_count"),
                b.get("span_minutes"),
                b.get("pump_amount"),
                b.get("sol_spent"),
                b.get("pump_close_price_usd"),
                b.get("usd_est_close"),
                b.get("usd_est_sol_close"),
                b.get("implied_price_usd_per_pump_sol_close"),
            ])


def write_report(
    *,
    report_path: Path,
    metadata: dict[str, Any],
    buy_legs: list[dict[str, Any]],
    transfer_legs: list[dict[str, Any]],
    buy_batches: list[dict[str, Any]],
    transfer_batches: list[dict[str, Any]],
    buy_cost: dict[str, Any],
    transfer_cost: dict[str, Any],
    style: dict[str, Any],
    rpc_verify: dict[str, dict[str, Any]],
    milestone_map: list[dict[str, Any]],
) -> None:
    buy_batch_count = len(buy_batches)
    transfer_batch_count = len(transfer_batches)
    verified_rpc = sum(1 for v in rpc_verify.values() if v.get("rpc_found"))

    claim_note = ""
    if buy_batch_count == 6:
        claim_note = "Observed direct buyback batches equal 6 under this definition."
    elif buy_batch_count > 6:
        claim_note = "Observed direct buyback batches exceed 6 under this definition."
    else:
        claim_note = "Observed direct buyback batches are below 6; may indicate partial observability."

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# PUMP Buyback Forensic Verification Report\n\n")
        f.write(f"- Generated at (UTC): {metadata['generated_at_utc']}\n")
        f.write(f"- Scope: {metadata['start_date']} to {metadata['end_date']}\n")
        f.write("- Source A: Helius Enhanced API (buyback wallet execution legs)\n")
        f.write("- Source B: Solana RPC getTransaction (signature-level delta checks)\n")
        f.write("- Source C: pump_buyback_analysis.json milestones/news claims\n\n")

        f.write("## Key Verdict\n\n")
        f.write(f"- Observed direct buy legs (DEX-like): **{len(buy_legs)}**\n")
        f.write(f"- Observed direct buy batches ({metadata['batch_window_minutes']}m): **{buy_batch_count}**\n")
        f.write(f"- Observed buyback->treasury transfer legs: **{len(transfer_legs)}**\n")
        f.write(f"- Observed buyback->treasury transfer batches ({metadata['batch_window_minutes']}m): **{transfer_batch_count}**\n")
        f.write(f"- Buyback execution style (observable): **{style.get('style')}**\n")
        f.write(f"- Style reason: {style.get('reason')}\n")
        f.write(f"- `only 6 buybacks` check: {claim_note}\n\n")

        f.write("## Cost Estimation\n\n")
        f.write(
            f"- Direct buy legs estimated total: **{buy_cost.get('usd_est_close_total'):,.2f} USD** "
            f"on **{buy_cost.get('total_pump'):,.2f} PUMP** "
            f"with **{buy_cost.get('total_sol_spent'):,.4f} SOL** spent "
            f"(avg **{buy_cost.get('avg_price_usd_est_close')} USD/PUMP**, "
            f"coverage {buy_cost.get('pump_price_coverage_ratio'):.2%}, "
            f"method `{buy_cost.get('usd_method')}`)\n"
        )
        f.write(
            f"- Transfer-to-treasury estimated total: **{transfer_cost.get('usd_est_close_total'):,.2f} USD** "
            f"on **{transfer_cost.get('total_pump'):,.2f} PUMP** "
            f"(method `{transfer_cost.get('usd_method')}`)\n\n"
        )
        if isinstance(transfer_cost.get("usd_est_from_buy_avg_price"), (int, float)):
            f.write(
                f"- Transfer-to-treasury implied USD using observed buy avg price: "
                f"**{float(transfer_cost['usd_est_from_buy_avg_price']):,.2f} USD**\n\n"
            )

        f.write("## Source A Summary\n\n")
        f.write(f"- Enhanced tx fetched on buyback wallet: {metadata['fetch_meta']['pages_fetched']} pages\n")
        f.write(f"- Oldest fetched date: {metadata['fetch_meta']['oldest_seen_date']}\n")
        f.write(f"- Buy leg source counts: {metadata['source_a_summary']['buy_leg_source_counts']}\n")
        f.write(f"- Buy leg type counts: {metadata['source_a_summary']['buy_leg_type_counts']}\n")
        f.write(f"- Buy leg monthly counts: {metadata['source_a_summary']['buy_leg_monthly_counts']}\n\n")
        f.write(f"- SOL pricing source: {metadata.get('sol_price_source')}\n")
        f.write(f"- PUMP pricing source: {metadata.get('pump_price_source')}\n\n")

        f.write("## Source B RPC Verification\n\n")
        f.write(f"- Candidate signatures checked: {len(rpc_verify)}\n")
        f.write(f"- RPC responses found: {verified_rpc}\n\n")

        f.write("## Top 15 Direct Buy Batches by PUMP\n\n")
        f.write("| batch_id | date | signatures | span_min | pump_amount | sol_spent | usd_est_sol_close | implied_usd_per_pump |\n")
        f.write("|---|---|---:|---:|---:|---:|---:|---:|\n")
        for b in sorted(buy_batches, key=lambda x: float(x["pump_amount"]), reverse=True)[:15]:
            usd = b.get("usd_est_sol_close")
            usd_s = f"{usd:,.2f}" if isinstance(usd, (int, float)) else "-"
            p = b.get("implied_price_usd_per_pump_sol_close")
            p_s = f"{float(p):.8f}" if isinstance(p, (int, float)) else "-"
            f.write(
                f"| {b['batch_id']} | {b['date']} | {b['signature_count']} | {b['span_minutes']:.2f} | "
                f"{float(b['pump_amount']):,.2f} | {float(b.get('sol_spent') or 0.0):,.4f} | {usd_s} | {p_s} |\n"
            )

        f.write("\n## Source C Milestone Cross-check\n\n")
        f.write("| milestone_date | milestone_event | buy_batches_same_day | buy_pump_same_day | transfer_batches_same_day | transfer_pump_same_day |\n")
        f.write("|---|---|---:|---:|---:|---:|\n")
        for m in milestone_map:
            ev = str(m.get("milestone_event") or "").replace("|", "/")
            f.write(
                f"| {m['milestone_date']} | {ev} | {m['same_day_buy_batch_count']} | "
                f"{float(m['same_day_buy_pump_amount']):,.2f} | {m['same_day_transfer_batch_count']} | "
                f"{float(m['same_day_transfer_pump_amount']):,.2f} |\n"
            )

        f.write("\n## Notes & Limits\n\n")
        f.write(
            "- This report measures *observable direct execution legs* tied to buyback wallet 3VK and token-account movements.\n"
        )
        f.write(
            "- If later buyback routes execute through other program-controlled accounts (e.g., Squads internals) without direct 3VK token-account deltas, they can be under-counted in this method.\n"
        )
        f.write(
            "- For direct buy legs, USD is primarily estimated from observed SOL outflow * SOL daily close.\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Forensic verify PUMP buyback execution.")
    parser.add_argument("--window-minutes", type=int, default=30, help="Batching window size in minutes.")
    parser.add_argument("--max-pages", type=int, default=500, help="Max Helius pages for buyback wallet history.")
    parser.add_argument("--rpc-verify-limit", type=int, default=300, help="Max signatures verified by RPC (0 = all).")
    args = parser.parse_args()

    load_dotenv(BASE_DIR / ".env")
    helius_key = os.environ.get("HELIUS_API_KEY", "").strip()
    if not helius_key:
        raise RuntimeError("HELIUS_API_KEY missing in .env")
    helius_rpc = f"https://mainnet.helius-rpc.com/?api-key={helius_key}"

    print("=" * 72)
    print("PUMP buyback forensic verification", flush=True)
    print("=" * 72)
    print("Source A: fetching buyback wallet enhanced txs ...", flush=True)
    enhanced_buyback, fetch_meta = fetch_all_enhanced_txs(
        helius_key=helius_key,
        address=BUYBACK_WALLET,
        min_ts=TGE_TS,
        max_pages=args.max_pages,
    )
    print(f"Enhanced buyback wallet txs in scope: {len(enhanced_buyback)}", flush=True)
    print(
        f"Fetch status: pages={fetch_meta['pages_fetched']} oldest={fetch_meta['oldest_seen_date']} "
        f"reached_tge={fetch_meta['reached_min_ts']} max_pages_hit={fetch_meta['max_pages_hit']}",
        flush=True,
    )

    buy_legs, transfer_legs, source_a_summary = parse_buyback_legs(enhanced_buyback)
    print(f"Observed direct buy legs: {len(buy_legs)}", flush=True)
    print(f"Observed buyback->treasury transfer legs: {len(transfer_legs)}", flush=True)

    buy_batches = group_batches(buy_legs, window_seconds=args.window_minutes * 60, batch_prefix="buy")
    transfer_batches = group_batches(transfer_legs, window_seconds=args.window_minutes * 60, batch_prefix="transfer")
    print(f"Buy batches ({args.window_minutes}m): {len(buy_batches)}", flush=True)
    print(f"Transfer batches ({args.window_minutes}m): {len(transfer_batches)}", flush=True)

    price_map = load_price_map()
    estimate_usd(buy_legs, price_map)
    estimate_usd(transfer_legs, price_map)
    estimate_usd(buy_batches, price_map)
    estimate_usd(transfer_batches, price_map)

    sol_price_map, sol_price_source = load_sol_price_map_from_binance()
    estimate_buy_leg_cost_via_sol(buy_legs, sol_price_map)
    attach_buy_batch_cost_from_legs(buy_batches, buy_legs)

    buy_cost = estimate_overall_cost(buy_legs, prefer_sol_cost=True)
    transfer_cost = estimate_overall_cost(transfer_legs, prefer_sol_cost=False)
    if isinstance(buy_cost.get("avg_price_usd_est_close"), (int, float)):
        transfer_cost["usd_est_from_buy_avg_price"] = round(
            float(transfer_cost.get("total_pump") or 0.0) * float(buy_cost["avg_price_usd_est_close"]),
            2,
        )
    style = infer_execution_style(buy_legs, buy_batches)

    verify_sigs = select_signatures_for_rpc(buy_batches, transfer_batches, args.rpc_verify_limit)
    print(
        f"Source B: RPC verification for {len(verify_sigs)} signatures "
        f"(limit={args.rpc_verify_limit}) ...",
        flush=True,
    )
    rpc_verify = verify_signatures_with_rpc(helius_rpc, verify_sigs)
    print(f"RPC verified signatures: {len(rpc_verify)}", flush=True)

    claims = load_json(PUMP_DIR / "core" / "pump_buyback_analysis.json")
    milestones = claims.get("milestones", []) or []
    milestone_map = map_milestones(milestones, buy_batches, transfer_batches)

    now = datetime.now(timezone.utc)
    meta = {
        "generated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "start_date": datetime.fromtimestamp(TGE_TS, tz=timezone.utc).strftime("%Y-%m-%d"),
        "end_date": now.strftime("%Y-%m-%d"),
        "batch_window_minutes": args.window_minutes,
        "fetch_meta": fetch_meta,
        "rpc_verify_limit": args.rpc_verify_limit,
        "rpc_verified_signatures": len(rpc_verify),
        "source_a_summary": source_a_summary,
        "sol_price_source": sol_price_source,
        "pump_price_source": "pump_behavior_chart_data.json::price.candles.close",
        "addresses": {
            "buyback_wallet": BUYBACK_WALLET,
            "buyback_token_account": BUYBACK_TOKEN_ACCOUNT,
            "treasury_wallet": TREASURY_WALLET,
            "treasury_token_account": TREASURY_TOKEN_ACCOUNT,
            "staking_distributor": STAKING_DISTRIBUTOR,
        },
    }

    ledger_path = PUMP_DIR / "raw" / "pump_buyback_execution_ledger.json"
    batches_path = PUMP_DIR / "raw" / "pump_buyback_execution_batches.json"
    recon_path = PUMP_DIR / "derived" / "pump_buyback_source_reconciliation.json"
    report_path = PUMP_DIR / "reports" / "pump_buyback_forensic_report.md"
    csv_path = PUMP_DIR / "raw" / "pump_buyback_execution_batches.csv"

    save_json(
        ledger_path,
        {
            "metadata": meta,
            "buy_legs": buy_legs,
            "transfer_legs": transfer_legs,
        },
    )
    save_json(
        batches_path,
        {
            "metadata": meta,
            "buy_batches": buy_batches,
            "transfer_batches": transfer_batches,
            "execution_style": style,
            "buy_cost_estimation": buy_cost,
            "transfer_cost_estimation": transfer_cost,
        },
    )
    save_json(
        recon_path,
        {
            "metadata": meta,
            "source_a_buy_leg_count": len(buy_legs),
            "source_a_transfer_leg_count": len(transfer_legs),
            "source_b_rpc_checked": len(rpc_verify),
            "source_c_milestones": milestones,
            "milestone_mapping": milestone_map,
            "rpc_verification": rpc_verify,
            "execution_style": style,
            "buy_cost_estimation": buy_cost,
            "transfer_cost_estimation": transfer_cost,
        },
    )
    write_batches_csv(csv_path, buy_batches)
    write_report(
        report_path=report_path,
        metadata=meta,
        buy_legs=buy_legs,
        transfer_legs=transfer_legs,
        buy_batches=buy_batches,
        transfer_batches=transfer_batches,
        buy_cost=buy_cost,
        transfer_cost=transfer_cost,
        style=style,
        rpc_verify=rpc_verify,
        milestone_map=milestone_map,
    )

    print("\nGenerated artifacts:")
    print(f"- {ledger_path}")
    print(f"- {batches_path}")
    print(f"- {csv_path}")
    print(f"- {recon_path}")
    print(f"- {report_path}")
    print("=" * 72)


if __name__ == "__main__":
    main()
