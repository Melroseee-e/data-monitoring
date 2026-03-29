#!/usr/bin/env python3
"""
Build merged dataset for PUMP behavior chart:
1) Daily OHLC + volume (CoinGecko)
2) Whale daily net balance deltas (proxy buy/sell pressure)
3) Team/official wallet -> exchange events (confirmed sell pressure)
4) Buyback milestones / weekly buyback events (official buy pressure)

Output:
  data/pump/derived/pump_behavior_chart_data.json
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
PUMP_DIR = DATA_DIR / "pump"

WHALE_CHART_FILE = PUMP_DIR / "derived" / "pump_whale_chart_data.json"
TEAM_ANALYSIS_FILE = PUMP_DIR / "core" / "pump_team_analysis.json"
BUYBACK_ANALYSIS_FILE = PUMP_DIR / "core" / "pump_buyback_analysis.json"
ADDRESSES_FILE = PUMP_DIR / "core" / "pump_addresses.json"
WHALE_ANALYSIS_FILE = PUMP_DIR / "core" / "pump_whale_analysis.json"
OUTPUT_FILE = PUMP_DIR / "derived" / "pump_behavior_chart_data.json"

COINGECKO_OHLC_URL = "https://api.coingecko.com/api/v3/coins/pump-fun/ohlc"
COINGECKO_VOLUME_URL = "https://api.coingecko.com/api/v3/coins/pump-fun/market_chart"
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"

# Use 365-day window to stay within free API limits.
PRICE_DAYS = 365
WHALE_DELTA_THRESHOLD_B = 0.10  # 100M PUMP/day delta threshold


def load_json(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def utc_date_from_ms(ts_ms: int | float) -> str:
    return datetime.fromtimestamp(float(ts_ms) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")


def short_addr(addr: str | None) -> str:
    if not addr:
        return ""
    return f"{addr[:6]}...{addr[-4:]}"


def fetch_json(url: str, params: dict[str, Any]) -> Any:
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_price_series_from_binance() -> list[dict[str, Any]]:
    rows = fetch_json(
        BINANCE_KLINES_URL,
        {"symbol": "PUMPUSDT", "interval": "1d", "limit": 1000},
    )
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 8:
            continue
        open_ts = int(row[0])
        d = utc_date_from_ms(open_ts)
        out.append({
            "date": d,
            "timestamp_ms": open_ts,
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
            "volume_token": float(row[5]),
            "volume_usd": float(row[7]),
        })
    out.sort(key=lambda x: x["date"])
    return out


def fetch_price_series_from_coingecko() -> list[dict[str, Any]]:
    ohlc_rows = fetch_json(
        COINGECKO_OHLC_URL,
        {"vs_currency": "usd", "days": PRICE_DAYS},
    )
    volume_rows = fetch_json(
        COINGECKO_VOLUME_URL,
        {"vs_currency": "usd", "days": PRICE_DAYS, "interval": "daily"},
    ).get("total_volumes", [])

    volume_map: dict[str, float] = {}
    for ts_ms, vol in volume_rows:
        volume_map[utc_date_from_ms(ts_ms)] = float(vol or 0.0)

    by_date: dict[str, dict[str, Any]] = {}
    for row in ohlc_rows:
        if not isinstance(row, list) or len(row) < 5:
            continue
        ts_ms, op, hi, lo, cl = row[:5]
        d = utc_date_from_ms(ts_ms)
        by_date[d] = {
            "date": d,
            "timestamp_ms": int(ts_ms),
            "open": float(op),
            "high": float(hi),
            "low": float(lo),
            "close": float(cl),
            "volume_usd": float(volume_map.get(d, 0.0)),
        }

    return [by_date[d] for d in sorted(by_date.keys())]


def fetch_price_series() -> tuple[list[dict[str, Any]], str]:
    """
    Prefer Binance daily candles (full daily OHLC with higher marker alignment).
    Fall back to CoinGecko when Binance is unavailable.
    """
    try:
        candles = fetch_price_series_from_binance()
        if candles:
            return candles, "Binance API (PUMPUSDT 1d klines)"
    except Exception:
        pass

    candles = fetch_price_series_from_coingecko()
    return candles, f"CoinGecko API ({PRICE_DAYS} days window)"


def normalize_whale_label(label: str, rank: int) -> str:
    if label and label != "无标签":
        return label
    return f"Top Whale #{rank}"


def build_whale_delta_events(whale_chart: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    whales = whale_chart.get("whales", [])
    whales_sorted = sorted(whales, key=lambda w: float(w.get("amount_B", 0.0) or 0.0), reverse=True)

    events: list[dict[str, Any]] = []
    registry: dict[str, dict[str, Any]] = {}

    for rank, whale in enumerate(whales_sorted, start=1):
        address = str(whale.get("address") or "")
        if not address:
            continue
        label = normalize_whale_label(str(whale.get("label") or ""), rank)
        history = whale.get("history", {}) or {}

        registry[address] = {
            "address": address,
            "short_address": short_addr(address),
            "label": label,
            "primary_category": "whale",
            "categories": ["whale"],
            "rank": rank,
            "current_balance_B": float(whale.get("amount_B", 0.0) or 0.0),
        }

        date_keys = sorted(history.keys())
        if len(date_keys) < 2:
            continue

        prev_val = float(history[date_keys[0]] or 0.0)
        for d in date_keys[1:]:
            cur_val = float(history.get(d, 0.0) or 0.0)
            delta_b = cur_val - prev_val
            prev_val = cur_val
            if abs(delta_b) < WHALE_DELTA_THRESHOLD_B:
                continue

            direction = "buy" if delta_b > 0 else "sell"
            events.append({
                "date": d,
                "direction": direction,
                "amount_B": round(abs(delta_b), 6),
                "amount_signed_B": round(delta_b, 6),
                "address": address,
                "short_address": short_addr(address),
                "label": label,
                "category": "whale_netflow",
                "event_type": "balance_delta",
                "exchange": None,
                "source": "pump_whale_chart_data.json",
                "note": "Proxy by daily balance delta (not strictly exchange-transfer confirmed).",
                "confidence": "proxy",
                "rank": rank,
            })

    return events, registry


def build_team_exchange_events(team_analysis: dict[str, Any], wallet_registry: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    raw_wallets = team_analysis.get("wallets", {}) or {}
    agg: dict[tuple[str, str, str], dict[str, Any]] = {}

    for address, info in raw_wallets.items():
        label = str(info.get("label") or "Team/Investor Wallet")
        existing = wallet_registry.get(address, {})
        categories = set(existing.get("categories", []))
        categories.add("official_wallet")
        wallet_registry[address] = {
            "address": address,
            "short_address": short_addr(address),
            "label": label,
            "primary_category": "official_wallet",
            "categories": sorted(categories),
            "rank": existing.get("rank"),
            "current_balance_B": info.get("current_balance_B"),
        }

        txs = info.get("all_transactions_classified", []) or []
        for tx in txs:
            if not tx.get("to_cex"):
                continue
            pump_out = float(tx.get("pump_out", 0.0) or 0.0)
            amount_b = pump_out / 1e9
            if amount_b <= 0:
                continue

            date = str(tx.get("date") or "")
            exchange = str(tx.get("cex_name") or "Unknown CEX")
            key = (date, address, exchange)
            if key not in agg:
                agg[key] = {
                    "date": date,
                    "direction": "sell",
                    "amount_B": 0.0,
                    "amount_signed_B": 0.0,
                    "address": address,
                    "short_address": short_addr(address),
                    "label": label,
                    "category": "official_exchange",
                    "event_type": "wallet_to_exchange",
                    "exchange": exchange,
                    "source": "pump_team_analysis.json",
                    "note": "Confirmed wallet -> exchange deposit.",
                    "confidence": "confirmed",
                    "count": 0,
                    "signatures": [],
                    "exchange_addresses": set(),
                }
            agg[key]["amount_B"] += amount_b
            agg[key]["amount_signed_B"] -= amount_b
            agg[key]["count"] += 1
            sig = tx.get("signature")
            if sig and len(agg[key]["signatures"]) < 5:
                agg[key]["signatures"].append(sig)
            exch_addr = tx.get("pump_destination")
            if exch_addr:
                agg[key]["exchange_addresses"].add(str(exch_addr))

    events = []
    for item in agg.values():
        item["amount_B"] = round(item["amount_B"], 6)
        item["amount_signed_B"] = round(item["amount_signed_B"], 6)
        item["exchange_addresses"] = sorted(item["exchange_addresses"])
        events.append(item)
    return events


def parse_week_ending(period: str) -> str | None:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", period or "")
    if m:
        return m.group(1)
    return None


def build_buyback_events(buyback: dict[str, Any], wallet_registry: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    key_addresses = buyback.get("key_addresses", {}) or {}
    buyback_wallet = (key_addresses.get("buyback_wallet", {}) or {}).get("address")
    treasury_wallet = (key_addresses.get("buyback_treasury", {}) or {}).get("address")

    if buyback_wallet:
        wallet_registry[buyback_wallet] = {
            "address": buyback_wallet,
            "short_address": short_addr(buyback_wallet),
            "label": "Pump Buyback Wallet",
            "primary_category": "buyback",
            "categories": ["buyback", "official_wallet"],
            "rank": None,
            "current_balance_B": None,
        }
    if treasury_wallet and treasury_wallet not in wallet_registry:
        wallet_registry[treasury_wallet] = {
            "address": treasury_wallet,
            "short_address": short_addr(treasury_wallet),
            "label": "Pump Buyback Treasury",
            "primary_category": "treasury",
            "categories": ["treasury", "official_wallet"],
            "rank": None,
            "current_balance_B": None,
        }

    # Milestone buyback events
    milestones = buyback.get("milestones", []) or []
    prev_cum = None
    for m in milestones:
        date = str(m.get("date") or "")
        if not date:
            continue
        cum_usd = m.get("cumulative_usd")
        inc_usd = None
        if isinstance(cum_usd, (int, float)):
            if prev_cum is None:
                inc_usd = float(cum_usd)
            else:
                inc_usd = max(0.0, float(cum_usd) - prev_cum)
            prev_cum = float(cum_usd)

        amount_b = m.get("pump_tokens_B")
        events.append({
            "date": date,
            "direction": "buy",
            "amount_B": float(amount_b) if isinstance(amount_b, (int, float)) else None,
            "amount_signed_B": float(amount_b) if isinstance(amount_b, (int, float)) else None,
            "amount_usd": inc_usd,
            "address": buyback_wallet,
            "short_address": short_addr(buyback_wallet),
            "label": "Official Buyback Milestone",
            "category": "buyback",
            "event_type": "buyback_milestone",
            "exchange": None,
            "source": "pump_buyback_analysis.json",
            "note": str(m.get("event") or ""),
            "confidence": "research_verified",
        })

    # Weekly buyback stats
    weekly = buyback.get("recent_weekly_buybacks", []) or []
    for w in weekly:
        date = parse_week_ending(str(w.get("period") or ""))
        if not date:
            continue
        usd_amount = w.get("usd_amount")
        if not isinstance(usd_amount, (int, float)):
            usd_amount = w.get("usd_amount_monthly_avg")
        events.append({
            "date": date,
            "direction": "buy",
            "amount_B": None,
            "amount_signed_B": None,
            "amount_usd": float(usd_amount) if isinstance(usd_amount, (int, float)) else None,
            "address": buyback_wallet,
            "short_address": short_addr(buyback_wallet),
            "label": "Official Weekly Buyback",
            "category": "buyback",
            "event_type": "buyback_weekly",
            "exchange": None,
            "source": "pump_buyback_analysis.json",
            "note": str(w.get("source") or ""),
            "confidence": "research_verified",
        })

    return events


def infer_direction_from_text(event: str) -> str:
    text = (event or "").lower()
    if "buyback" in text or "bought" in text:
        return "buy"
    if "deposit" in text or "sold" in text or "sell" in text:
        return "sell"
    return "sell"


def build_official_reported_events(addresses_data: dict[str, Any], wallet_registry: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    addrs = addresses_data.get("addresses", {}) or {}
    news = addresses_data.get("news_reported_events", []) or []
    events: list[dict[str, Any]] = []

    for address, info in addrs.items():
        label = str(info.get("label") or "Official Wallet")
        cat = str(info.get("type") or "official_wallet")
        existing = wallet_registry.get(address, {})
        categories = set(existing.get("categories", []))
        categories.add(cat)
        categories.add("official_wallet")
        wallet_registry[address] = {
            "address": address,
            "short_address": short_addr(address),
            "label": label,
            "primary_category": cat,
            "categories": sorted(categories),
            "rank": existing.get("rank"),
            "current_balance_B": (float(info.get("balance", 0.0)) / 1e9) if isinstance(info.get("balance"), (int, float)) else existing.get("current_balance_B"),
        }

    seen_keys: set[tuple[str, str, float | None, str | None]] = set()
    for item in news:
        date = str(item.get("date") or "")
        wallet = item.get("wallet")
        event_text = str(item.get("event") or "")
        direction = infer_direction_from_text(event_text)
        amount_raw = item.get("amount")
        amount_b = None
        if isinstance(amount_raw, (int, float)):
            amount_b = float(amount_raw) / 1e9
        exchange = item.get("exchange")
        key = (date, str(wallet), round(amount_b, 6) if isinstance(amount_b, float) else None, str(exchange) if exchange else None)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        label = wallet_registry.get(wallet, {}).get("label") if wallet else None
        events.append({
            "date": date,
            "direction": direction,
            "amount_B": round(amount_b, 6) if isinstance(amount_b, float) else None,
            "amount_signed_B": (round(amount_b, 6) if direction == "buy" else round(-amount_b, 6)) if isinstance(amount_b, float) else None,
            "amount_usd": float(item.get("value_usd")) if isinstance(item.get("value_usd"), (int, float)) else None,
            "address": wallet,
            "short_address": short_addr(wallet) if wallet else "",
            "label": label or "Official/Reported Wallet",
            "category": "official_exchange",
            "event_type": "reported_exchange_event",
            "exchange": exchange,
            "source": "pump_addresses.json::news_reported_events",
            "note": event_text,
            "confidence": "research_verified",
        })

    return events


def assign_event_ids(events: list[dict[str, Any]]) -> None:
    for idx, event in enumerate(events, start=1):
        event["id"] = f"evt_{idx:05d}"


def build_daily_summary(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    daily: dict[str, dict[str, Any]] = {}
    for event in events:
        date = event.get("date")
        if not date:
            continue
        row = daily.setdefault(date, {
            "date": date,
            "buy_events": 0,
            "sell_events": 0,
            "buy_amount_B": 0.0,
            "sell_amount_B": 0.0,
            "net_amount_B": 0.0,
            "by_category": Counter(),
        })

        direction = event.get("direction")
        amount_b = event.get("amount_B")
        amount_b_num = float(amount_b) if isinstance(amount_b, (int, float)) else 0.0
        category = str(event.get("category") or "unknown")
        row["by_category"][category] += 1

        if direction == "buy":
            row["buy_events"] += 1
            row["buy_amount_B"] += amount_b_num
            row["net_amount_B"] += amount_b_num
        else:
            row["sell_events"] += 1
            row["sell_amount_B"] += amount_b_num
            row["net_amount_B"] -= amount_b_num

    out = []
    for d in sorted(daily.keys()):
        row = daily[d]
        out.append({
            "date": d,
            "buy_events": row["buy_events"],
            "sell_events": row["sell_events"],
            "buy_amount_B": round(row["buy_amount_B"], 6),
            "sell_amount_B": round(row["sell_amount_B"], 6),
            "net_amount_B": round(row["net_amount_B"], 6),
            "by_category": dict(row["by_category"]),
        })
    return out


def infer_exchange_name(label: str | None, fallback: str | None = None) -> str | None:
    if fallback:
        return fallback
    s = (label or "").strip()
    if not s:
        return None
    if s.lower().startswith("cex:"):
        return s.split(":", 1)[1].strip()
    keys = [
        "Binance", "Bybit", "OKX", "Kraken", "Coinbase", "Bitget", "Gate",
        "KuCoin", "HTX", "MEXC", "Wintermute", "Robinhood", "Fireblocks",
    ]
    for k in keys:
        if k.lower() in s.lower():
            return k
    return None


def profile_sort_key(row: dict[str, Any]) -> tuple[int, int, str]:
    order = {
        "whale": 0,
        "official_wallet": 1,
        "team": 2,
        "investor": 3,
        "treasury": 4,
        "buyback": 5,
        "vesting": 6,
        "exchange_address": 7,
        "unknown": 9,
    }
    t = row.get("main_type") or "unknown"
    rank = row.get("rank")
    rank_v = rank if isinstance(rank, int) else 999999
    return (order.get(t, 8), rank_v, str(row.get("label") or ""))


def build_address_profiles(
    wallet_registry: dict[str, dict[str, Any]],
    addresses_data: dict[str, Any],
    team_analysis: dict[str, Any],
    whale_analysis: dict[str, Any],
    in_range_events: list[dict[str, Any]],
    latest_price_usd: float,
) -> list[dict[str, Any]]:
    profiles: dict[str, dict[str, Any]] = {}

    def upsert(
        address: str | None,
        *,
        label: str | None = None,
        main_type: str | None = None,
        categories: list[str] | None = None,
        exchange_name: str | None = None,
        current_balance_B: float | None = None,
        rank: int | None = None,
        source_tag: str | None = None,
        note: str | None = None,
    ) -> None:
        if not address:
            return
        address = str(address)
        row = profiles.setdefault(address, {
            "address": address,
            "short_address": short_addr(address),
            "label": "",
            "main_type": "unknown",
            "categories": set(),
            "source_tags": set(),
            "exchange_name": None,
            "current_balance_B": None,
            "rank": None,
            "note": None,
            "event_count": 0,
            "buy_amount_B": 0.0,
            "sell_amount_B": 0.0,
            "exchange_inflow_B": 0.0,
        })

        if label and (not row["label"] or row["label"] == "无标签" or str(row["label"]).startswith("Top Whale #")):
            row["label"] = label

        if main_type and (row["main_type"] in ("unknown", "") or main_type == "whale"):
            row["main_type"] = main_type

        if categories:
            row["categories"].update([c for c in categories if c])
            if row["main_type"] == "unknown":
                row["main_type"] = categories[0]

        if exchange_name and not row["exchange_name"]:
            row["exchange_name"] = exchange_name

        if isinstance(current_balance_B, (int, float)):
            v = float(current_balance_B)
            if row["current_balance_B"] is None or abs(v) > abs(float(row["current_balance_B"])):
                row["current_balance_B"] = v

        if isinstance(rank, int) and rank > 0 and (row["rank"] is None or rank < row["rank"]):
            row["rank"] = rank

        if source_tag:
            row["source_tags"].add(source_tag)

        if note and not row["note"]:
            row["note"] = note

    # 1) Registry from chart/event build path
    for addr, info in wallet_registry.items():
        cats = info.get("categories") or []
        ex = infer_exchange_name(info.get("label"))
        upsert(
            addr,
            label=info.get("label"),
            main_type=info.get("primary_category"),
            categories=list(cats),
            exchange_name=ex,
            current_balance_B=info.get("current_balance_B"),
            rank=info.get("rank"),
            source_tag="wallet_registry",
        )

    # 2) Official address book
    for addr, info in (addresses_data.get("addresses") or {}).items():
        t = str(info.get("type") or "official_wallet")
        bal = info.get("balance")
        bal_b = (float(bal) / 1e9) if isinstance(bal, (int, float)) else None
        ex = infer_exchange_name(info.get("label"))
        upsert(
            addr,
            label=info.get("label"),
            main_type=t if t != "official_allocation" else "official_wallet",
            categories=[t, "official_wallet"],
            exchange_name=ex,
            current_balance_B=bal_b,
            source_tag="pump_addresses",
            note=info.get("notes"),
        )

    # 3) Whale analysis top-holders (contains CEX owner addresses in top20)
    for h in (whale_analysis.get("top_holders_classified") or []):
        cat = str(h.get("category") or "unknown")
        lbl = str(h.get("label") or "")
        ex = infer_exchange_name(lbl)
        main_type = "exchange_address" if cat == "cex" else cat
        extra_cats = [cat]
        if cat == "cex":
            extra_cats.append("exchange_address")
        upsert(
            h.get("owner"),
            label=lbl,
            main_type=main_type,
            categories=extra_cats,
            exchange_name=ex,
            current_balance_B=h.get("balance_B"),
            rank=h.get("rank"),
            source_tag="whale_analysis_top_holders",
        )

    # 4) Exchange deposit destination addresses from classified team txs
    exchange_addr_inflow: dict[str, float] = defaultdict(float)
    for _wallet_addr, info in (team_analysis.get("wallets") or {}).items():
        for tx in (info.get("all_transactions_classified") or []):
            if not tx.get("to_cex"):
                continue
            dest = tx.get("pump_destination")
            ex = tx.get("cex_name")
            amt_b = float(tx.get("pump_out", 0.0) or 0.0) / 1e9
            if dest:
                exchange_addr_inflow[str(dest)] += amt_b
                upsert(
                    str(dest),
                    label=f"{ex or 'Unknown'} Deposit Address",
                    main_type="exchange_address",
                    categories=["exchange_address", "exchange"],
                    exchange_name=str(ex) if ex else None,
                    source_tag="team_classified_tx_destination",
                )

    # 5) Reported event explicit exchange addresses
    for item in (addresses_data.get("news_reported_events") or []):
        ex_addr = item.get("bitget_address")
        ex = item.get("exchange")
        amt_b = float(item.get("amount", 0.0) or 0.0) / 1e9 if isinstance(item.get("amount"), (int, float)) else 0.0
        if ex_addr:
            exchange_addr_inflow[str(ex_addr)] += amt_b
            upsert(
                str(ex_addr),
                label=f"{ex or 'Unknown'} Deposit Address",
                main_type="exchange_address",
                categories=["exchange_address", "exchange"],
                exchange_name=str(ex) if ex else None,
                source_tag="reported_event_exchange_address",
            )

    # 6) Event statistics by source wallet
    by_addr_stats: dict[str, dict[str, float]] = defaultdict(lambda: {
        "event_count": 0.0, "buy_amount_B": 0.0, "sell_amount_B": 0.0
    })
    for e in in_range_events:
        addr = e.get("address")
        if not addr:
            continue
        st = by_addr_stats[str(addr)]
        st["event_count"] += 1
        amt = float(e.get("amount_B", 0.0) or 0.0)
        if e.get("direction") == "buy":
            st["buy_amount_B"] += amt
        else:
            st["sell_amount_B"] += amt

    # Finalize
    out = []
    total_supply_B = 1000.0
    for addr, row in profiles.items():
        st = by_addr_stats.get(addr)
        if st:
            row["event_count"] = int(st["event_count"])
            row["buy_amount_B"] = round(st["buy_amount_B"], 6)
            row["sell_amount_B"] = round(st["sell_amount_B"], 6)
        row["exchange_inflow_B"] = round(float(exchange_addr_inflow.get(addr, 0.0)), 6)

        bal_b = row.get("current_balance_B")
        if isinstance(bal_b, (int, float)):
            row["share_total_supply_pct"] = round(float(bal_b) / total_supply_B * 100, 6)
            row["estimated_value_usd"] = round(float(bal_b) * 1e9 * latest_price_usd, 2)
        else:
            row["share_total_supply_pct"] = None
            row["estimated_value_usd"] = None

        if not row.get("exchange_name"):
            row["exchange_name"] = infer_exchange_name(row.get("label"))
        if row.get("exchange_name"):
            row["categories"].add("exchange")
            if row["main_type"] == "unknown":
                row["main_type"] = "exchange_address"

        row["categories"] = sorted(row["categories"])
        row["source_tags"] = sorted(row["source_tags"])
        if not row.get("label"):
            row["label"] = "Unlabeled Address"

        out.append(row)

    out.sort(key=profile_sort_key)
    return out


def main() -> None:
    whale_chart = load_json(WHALE_CHART_FILE)
    team_analysis = load_json(TEAM_ANALYSIS_FILE)
    buyback_analysis = load_json(BUYBACK_ANALYSIS_FILE)
    addresses_data = load_json(ADDRESSES_FILE)
    whale_analysis = load_json(WHALE_ANALYSIS_FILE)

    candles, price_source = fetch_price_series()
    if not candles:
        raise RuntimeError("No price candles fetched from CoinGecko.")
    price_dates = {c["date"] for c in candles}
    latest_price_usd = float(candles[-1]["close"])

    wallet_registry: dict[str, dict[str, Any]] = {}

    whale_events, whale_registry = build_whale_delta_events(whale_chart)
    wallet_registry.update(whale_registry)
    team_events = build_team_exchange_events(team_analysis, wallet_registry)
    buyback_events = build_buyback_events(buyback_analysis, wallet_registry)
    official_reported_events = build_official_reported_events(addresses_data, wallet_registry)

    all_events = whale_events + team_events + buyback_events + official_reported_events
    in_range_events = [e for e in all_events if e.get("date") in price_dates]
    dropped_events = len(all_events) - len(in_range_events)

    in_range_events.sort(
        key=lambda e: (
            e.get("date", ""),
            0 if e.get("direction") == "buy" else 1,
            -(float(e.get("amount_B")) if isinstance(e.get("amount_B"), (int, float)) else 0.0),
        )
    )
    assign_event_ids(in_range_events)

    daily_summary = build_daily_summary(in_range_events)

    wallet_list = sorted(
        wallet_registry.values(),
        key=lambda w: (
            0 if w.get("primary_category") == "whale" else 1,
            w.get("rank") if isinstance(w.get("rank"), int) else 9999,
            w.get("label", ""),
        ),
    )
    address_profiles = build_address_profiles(
        wallet_registry=wallet_registry,
        addresses_data=addresses_data,
        team_analysis=team_analysis,
        whale_analysis=whale_analysis,
        in_range_events=in_range_events,
        latest_price_usd=latest_price_usd,
    )

    by_category = Counter(str(e.get("category")) for e in in_range_events)
    by_direction = Counter(str(e.get("direction")) for e in in_range_events)
    profile_main_type_counts = Counter(p.get("main_type") or "unknown" for p in address_profiles)
    profile_exchange_count = sum(1 for p in address_profiles if p.get("exchange_name"))
    profile_with_balance_count = sum(1 for p in address_profiles if isinstance(p.get("current_balance_B"), (int, float)))

    output = {
        "metadata": {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "token": "PUMP",
            "contract": "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn",
            "price_source": price_source,
            "whale_delta_threshold_B": WHALE_DELTA_THRESHOLD_B,
            "notes": [
                "whale_netflow events are inferred from daily balance delta (proxy).",
                "official_exchange events come from confirmed report data or classified team transfers.",
                "wallet->exchange is treated as sell pressure; buyback milestones/weekly are treated as buy pressure.",
            ],
            "source_files": [
                str(WHALE_CHART_FILE.relative_to(BASE_DIR)),
                str(TEAM_ANALYSIS_FILE.relative_to(BASE_DIR)),
                str(BUYBACK_ANALYSIS_FILE.relative_to(BASE_DIR)),
                str(ADDRESSES_FILE.relative_to(BASE_DIR)),
                str(WHALE_ANALYSIS_FILE.relative_to(BASE_DIR)),
            ],
            "dropped_events_outside_price_range": dropped_events,
        },
        "price": {
            "symbol": "PUMP/USD",
            "candles": candles,
            "start_date": candles[0]["date"],
            "end_date": candles[-1]["date"],
            "count": len(candles),
        },
        "wallets": wallet_list,
        "address_profiles": address_profiles,
        "address_profile_stats": {
            "total_profiles": len(address_profiles),
            "with_exchange_name": profile_exchange_count,
            "with_balance": profile_with_balance_count,
            "by_main_type": dict(profile_main_type_counts),
            "latest_price_usd": latest_price_usd,
        },
        "events": in_range_events,
        "daily_summary": daily_summary,
        "event_stats": {
            "total_events": len(in_range_events),
            "by_direction": dict(by_direction),
            "by_category": dict(by_category),
        },
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("=" * 72)
    print("Built pump behavior chart data")
    print("=" * 72)
    print(f"Output: {OUTPUT_FILE}")
    print(f"Candles: {len(candles)} ({candles[0]['date']} -> {candles[-1]['date']})")
    print(f"Wallets tracked: {len(wallet_list)}")
    print(f"Address profiles: {len(address_profiles)}")
    print(f"Events in range: {len(in_range_events)}")
    print(f"Dropped events (out of range): {dropped_events}")
    print(f"Event categories: {dict(by_category)}")
    print(f"Directions: {dict(by_direction)}")


if __name__ == "__main__":
    main()
