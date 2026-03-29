#!/usr/bin/env python3
"""
PUMP Full Address Ledger via Dune SQL
======================================
Builds complete per-address buy/sell ledger for ALL PUMP holders from TGE.

Strategy: SQL aggregation on Dune tokens_solana.transfers
  - No Helius credits needed
  - CEX tagging done in SQL via inline VALUES table
  - Output: per-address {sent_B, received_B, cex_sent_B, cex_received_B, net_B}

Runs in 3 queries:
  1. Per-address send aggregation (with CEX flag)
  2. Per-address receive aggregation (with CEX flag)
  3. Daily net flow time series (for timeline analysis)

Output:
  data/pump/derived/pump_address_ledger.json
  data/pump/derived/pump_daily_netflow.json

Usage:
  python scripts/pump/build_address_ledger_dune.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SKILLS_DIR = BASE_DIR / ".claude" / "skills" / "onchain-analysis" / "scripts"
sys.path.insert(0, str(SKILLS_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from core.dune import run_sql
from core.config import load_exchange_addresses

PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"
TGE_DATE = "2025-07-12"

DATA_DIR = BASE_DIR / "data" / "pump"
LEDGER_FILE   = DATA_DIR / "derived" / "pump_address_ledger.json"
NETFLOW_FILE  = DATA_DIR / "derived" / "pump_daily_netflow.json"


def build_cex_values_sql() -> tuple[str, dict[str, str]]:
    """Build SQL VALUES clause for CEX address lookup."""
    exchanges_data = load_exchange_addresses()
    sol_addrs: list[tuple[str, str]] = []
    for ex_name, chains in exchanges_data.items():
        if isinstance(chains, dict) and "solana" in chains:
            for addr in chains["solana"]:
                # Escape single quotes in exchange names
                safe_name = ex_name.replace("'", "''")
                sol_addrs.append((addr, safe_name))

    values = ",\n    ".join(f"('{a}', '{n}')" for a, n in sol_addrs)
    lookup = {a: n for a, n in sol_addrs}
    print(f"  Built CEX lookup: {len(sol_addrs)} Solana addresses")
    return values, lookup


def query_send_ledger(cex_values: str) -> list[dict]:
    """Per-address send aggregation with CEX flag."""
    sql = f"""
WITH cex_addrs AS (
  SELECT address, exchange_name
  FROM (VALUES
    {cex_values}
  ) AS t(address, exchange_name)
),
sends AS (
  SELECT
    t.from_owner AS address,
    SUM(t.amount / 1e9) AS sent_B,
    COUNT(*) AS send_tx_count,
    MIN(DATE(t.block_time)) AS first_send_date,
    MAX(DATE(t.block_time)) AS last_send_date,
    -- CEX sends (depositing to exchange = selling)
    SUM(CASE WHEN c.address IS NOT NULL THEN t.amount / 1e9 ELSE 0 END) AS cex_deposit_B,
    COUNT(CASE WHEN c.address IS NOT NULL THEN 1 END) AS cex_deposit_count,
    -- Collect exchange names used
    ARRAY_AGG(DISTINCT c.exchange_name) FILTER (WHERE c.exchange_name IS NOT NULL) AS exchanges_deposited
  FROM tokens_solana.transfers t
  LEFT JOIN cex_addrs c ON t.to_owner = c.address
  WHERE t.token_mint_address = '{PUMP_MINT}'
    AND t.block_time >= TIMESTAMP '{TGE_DATE}'
    AND t.from_owner IS NOT NULL
    AND t.amount > 0
  GROUP BY t.from_owner
)
SELECT * FROM sends
ORDER BY sent_B DESC
"""
    print("Query 1: Per-address send ledger...")
    return run_sql(sql, timeout=900)


def query_receive_ledger(cex_values: str) -> list[dict]:
    """Per-address receive aggregation with CEX flag."""
    sql = f"""
WITH cex_addrs AS (
  SELECT address, exchange_name
  FROM (VALUES
    {cex_values}
  ) AS t(address, exchange_name)
),
receives AS (
  SELECT
    t.to_owner AS address,
    SUM(t.amount / 1e9) AS received_B,
    COUNT(*) AS receive_tx_count,
    MIN(DATE(t.block_time)) AS first_receive_date,
    MAX(DATE(t.block_time)) AS last_receive_date,
    -- CEX receives (withdrawing from exchange = buying)
    SUM(CASE WHEN c.address IS NOT NULL THEN t.amount / 1e9 ELSE 0 END) AS cex_withdraw_B,
    COUNT(CASE WHEN c.address IS NOT NULL THEN 1 END) AS cex_withdraw_count,
    ARRAY_AGG(DISTINCT c.exchange_name) FILTER (WHERE c.exchange_name IS NOT NULL) AS exchanges_withdrawn
  FROM tokens_solana.transfers t
  LEFT JOIN cex_addrs c ON t.from_owner = c.address
  WHERE t.token_mint_address = '{PUMP_MINT}'
    AND t.block_time >= TIMESTAMP '{TGE_DATE}'
    AND t.to_owner IS NOT NULL
    AND t.amount > 0
  GROUP BY t.to_owner
)
SELECT * FROM receives
ORDER BY received_B DESC
"""
    print("Query 2: Per-address receive ledger...")
    return run_sql(sql, timeout=900)


def query_daily_netflow(cex_values: str) -> list[dict]:
    """Daily CEX inflow/outflow time series."""
    sql = f"""
WITH cex_addrs AS (
  SELECT address, exchange_name
  FROM (VALUES
    {cex_values}
  ) AS t(address, exchange_name)
)
SELECT
  DATE(t.block_time) AS date,
  SUM(CASE WHEN c_to.address IS NOT NULL AND c_from.address IS NULL
      THEN t.amount / 1e9 ELSE 0 END) AS cex_inflow_B,
  COUNT(CASE WHEN c_to.address IS NOT NULL AND c_from.address IS NULL THEN 1 END) AS cex_inflow_count,
  SUM(CASE WHEN c_from.address IS NOT NULL AND c_to.address IS NULL
      THEN t.amount / 1e9 ELSE 0 END) AS cex_outflow_B,
  COUNT(CASE WHEN c_from.address IS NOT NULL AND c_to.address IS NULL THEN 1 END) AS cex_outflow_count,
  SUM(t.amount / 1e9) AS total_volume_B,
  COUNT(*) AS total_tx_count,
  COUNT(DISTINCT t.from_owner) AS unique_senders
FROM tokens_solana.transfers t
LEFT JOIN cex_addrs c_to   ON t.to_owner   = c_to.address
LEFT JOIN cex_addrs c_from ON t.from_owner = c_from.address
WHERE t.token_mint_address = '{PUMP_MINT}'
  AND t.block_time >= TIMESTAMP '{TGE_DATE}'
  AND t.amount > 0
GROUP BY DATE(t.block_time)
ORDER BY date
"""
    print("Query 3: Daily CEX netflow time series...")
    return run_sql(sql, timeout=900)


def merge_ledger(sends: list[dict], receives: list[dict], cex_lookup: dict[str, str]) -> dict[str, dict]:
    """Merge send + receive into unified per-address ledger."""
    print("Merging send + receive ledgers...")

    send_map = {r["address"]: r for r in sends if r.get("address")}
    recv_map = {r["address"]: r for r in receives if r.get("address")}
    all_addrs = set(send_map) | set(recv_map)

    ledger: dict[str, dict] = {}
    for addr in all_addrs:
        s = send_map.get(addr, {})
        r = recv_map.get(addr, {})

        sent_B     = float(s.get("sent_b") or s.get("sent_B") or 0)
        received_B = float(r.get("received_b") or r.get("received_B") or 0)
        cex_dep_B  = float(s.get("cex_deposit_b") or s.get("cex_deposit_B") or 0)
        cex_wdw_B  = float(r.get("cex_withdraw_b") or r.get("cex_withdraw_B") or 0)
        net_B      = received_B - sent_B

        # Size tier by total activity
        total_vol = sent_B + received_B
        if total_vol >= 20.0:
            size_tier = "Mega"
        elif total_vol >= 2.0:
            size_tier = "Large"
        elif total_vol >= 0.2:
            size_tier = "Medium"
        elif total_vol >= 0.02:
            size_tier = "Small"
        else:
            size_tier = "Micro"

        is_cex = addr in cex_lookup

        # Dates
        dates = [
            s.get("first_send_date"), s.get("last_send_date"),
            r.get("first_receive_date"), r.get("last_receive_date"),
        ]
        valid_dates = [str(d) for d in dates if d]
        first_date = min(valid_dates) if valid_dates else None
        last_date  = max(valid_dates) if valid_dates else None

        # Exchange lists
        ex_dep = s.get("exchanges_deposited") or []
        ex_wdw = r.get("exchanges_withdrawn") or []
        if isinstance(ex_dep, str):
            ex_dep = [ex_dep]
        if isinstance(ex_wdw, str):
            ex_wdw = [ex_wdw]

        ledger[addr] = {
            "address":            addr,
            "is_cex":             is_cex,
            "cex_name":           cex_lookup.get(addr),
            "size_tier":          size_tier,
            "sent_B":             round(sent_B, 4),
            "received_B":         round(received_B, 4),
            "net_B":              round(net_B, 4),
            "cex_deposit_B":      round(cex_dep_B, 4),   # sent to CEX (sell)
            "cex_withdraw_B":     round(cex_wdw_B, 4),   # received from CEX (buy)
            "net_cex_B":          round(cex_wdw_B - cex_dep_B, 4),
            "send_tx_count":      int(s.get("send_tx_count") or 0),
            "receive_tx_count":   int(r.get("receive_tx_count") or 0),
            "first_activity_date": first_date,
            "last_activity_date":  last_date,
            "exchanges_deposited": sorted(set(ex_dep)),
            "exchanges_withdrawn": sorted(set(ex_wdw)),
        }

    return ledger


def main() -> None:
    print(f"[{datetime.now(tz=timezone.utc).strftime('%H:%M:%S')}] Building PUMP address ledger via Dune...")

    cex_values, cex_lookup = build_cex_values_sql()

    # Run 3 queries
    sends    = query_send_ledger(cex_values)
    receives = query_receive_ledger(cex_values)
    daily    = query_daily_netflow(cex_values)

    print(f"  Sends: {len(sends):,} addresses")
    print(f"  Receives: {len(receives):,} addresses")
    print(f"  Daily: {len(daily)} days")

    # Merge
    ledger = merge_ledger(sends, receives, cex_lookup)

    # Summary stats
    non_cex = {a: d for a, d in ledger.items() if not d["is_cex"]}
    net_sellers = sum(1 for d in non_cex.values() if d["net_B"] < 0)
    net_buyers  = sum(1 for d in non_cex.values() if d["net_B"] > 0)
    cex_sellers = sum(1 for d in non_cex.values() if d["cex_deposit_B"] > 0)
    cex_buyers  = sum(1 for d in non_cex.values() if d["cex_withdraw_B"] > 0)

    size_dist: dict[str, int] = {}
    for d in non_cex.values():
        t = d["size_tier"]
        size_dist[t] = size_dist.get(t, 0) + 1

    total_cex_dep = sum(d["cex_deposit_B"] for d in non_cex.values())
    total_cex_wdw = sum(d["cex_withdraw_B"] for d in non_cex.values())

    summary = {
        "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pump_mint": PUMP_MINT,
        "tge_date": TGE_DATE,
        "source": "dune_tokens_solana_transfers",
        "total_addresses": len(ledger),
        "non_cex_addresses": len(non_cex),
        "net_sellers": net_sellers,
        "net_buyers": net_buyers,
        "ever_sold_to_cex": cex_sellers,
        "ever_bought_from_cex": cex_buyers,
        "size_distribution": size_dist,
        "total_cex_deposit_B": round(total_cex_dep, 2),
        "total_cex_withdraw_B": round(total_cex_wdw, 2),
        "net_cex_flow_B": round(total_cex_wdw - total_cex_dep, 2),
    }

    LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_FILE, "w") as f:
        json.dump({"summary": summary, "addresses": ledger}, f, ensure_ascii=False, indent=2)

    with open(NETFLOW_FILE, "w") as f:
        json.dump({
            "generated_at": summary["generated_at"],
            "pump_mint": PUMP_MINT,
            "daily": daily,
        }, f, ensure_ascii=False, indent=2)

    print(f"\n=== Summary ===")
    print(f"Total addresses:      {len(ledger):,}")
    print(f"Non-CEX addresses:    {len(non_cex):,}")
    print(f"Net sellers:          {net_sellers:,}")
    print(f"Net buyers:           {net_buyers:,}")
    print(f"Ever sold to CEX:     {cex_sellers:,}")
    print(f"Ever bought from CEX: {cex_buyers:,}")
    print(f"Size distribution:    {size_dist}")
    print(f"Total CEX deposit:    {total_cex_dep:.2f}B PUMP")
    print(f"Total CEX withdraw:   {total_cex_wdw:.2f}B PUMP")
    print(f"\nLedger → {LEDGER_FILE}")
    print(f"Daily  → {NETFLOW_FILE}")


if __name__ == "__main__":
    main()
