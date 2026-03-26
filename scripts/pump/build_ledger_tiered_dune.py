#!/usr/bin/env python3
"""
PUMP Address Ledger via Dune — Tiered Aggregation Strategy
===========================================================
Uses small-result queries to stay within Dune free tier read limits.

Query plan (small result sets only):
  Q1: Size tier distribution (5 rows)
  Q2: Daily CEX netflow (260 rows)
  Q3: Top 500 sellers by CEX deposit (500 rows)
  Q4: Top 500 buyers by CEX withdraw (500 rows)
  Q5: Per-exchange CEX flow summary (20 rows)
  Q6: CEX inflow total validation vs Helius (1 row)

Total rows returned: ~1,300 — very low read credit cost.

Usage:
  python scripts/pump/build_ledger_tiered_dune.py
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
TGE_DATE  = "2025-07-12"

DATA_DIR    = BASE_DIR / "data" / "pump"
OUTPUT_DIR  = DATA_DIR / "derived"


def build_cex_values() -> tuple[str, dict[str, str]]:
    exchanges_data = load_exchange_addresses()
    sol_addrs: list[tuple[str, str]] = []
    for ex_name, chains in exchanges_data.items():
        if isinstance(chains, dict) and "solana" in chains:
            for addr in chains["solana"]:
                sol_addrs.append((addr, ex_name.replace("'", "''")))
    values = ",\n    ".join(f"('{a}', '{n}')" for a, n in sol_addrs)
    lookup = {a: n for a, n in sol_addrs}
    print(f"  CEX lookup: {len(sol_addrs)} addresses")
    return values, lookup


def q1_size_tier_distribution(cex_values: str) -> list[dict]:
    """5 rows — size tier breakdown of all senders."""
    sql = f"""
WITH cex_addrs AS (
  SELECT address FROM (VALUES {cex_values}) AS t(address, exchange_name)
),
sender_totals AS (
  SELECT
    from_owner AS address,
    SUM(amount_display / 1e9) AS sent_B
  FROM tokens_solana.transfers
  WHERE token_mint_address = '{PUMP_MINT}'
    AND block_time >= TIMESTAMP '{TGE_DATE}'
    AND from_owner IS NOT NULL
    AND from_owner NOT IN (SELECT address FROM cex_addrs)
    AND amount > 0
  GROUP BY from_owner
),
tiered AS (
  SELECT
    CASE
      WHEN sent_B >= 20   THEN 'Mega (>=20B)'
      WHEN sent_B >= 2    THEN 'Large (2-20B)'
      WHEN sent_B >= 0.2  THEN 'Medium (0.2-2B)'
      WHEN sent_B >= 0.02 THEN 'Small (0.02-0.2B)'
      ELSE                     'Micro (<0.02B)'
    END AS size_tier,
    COUNT(*) AS address_count,
    SUM(sent_B) AS total_sent_B,
    AVG(sent_B) AS avg_sent_B
  FROM sender_totals
  GROUP BY 1
)
SELECT * FROM tiered ORDER BY total_sent_B DESC
"""
    print("Q1: Size tier distribution...")
    return run_sql(sql, timeout=600)


def q2_daily_cex_netflow(cex_values: str) -> list[dict]:
    """~260 rows — daily CEX inflow + outflow."""
    sql = f"""
WITH cex_addrs AS (
  SELECT address, exchange_name
  FROM (VALUES {cex_values}) AS t(address, exchange_name)
)
SELECT
  DATE(block_time) AS date,
  SUM(CASE WHEN c_to.address IS NOT NULL AND c_from.address IS NULL
      THEN amount_display / 1e9 ELSE 0 END) AS cex_inflow_B,
  COUNT(CASE WHEN c_to.address IS NOT NULL AND c_from.address IS NULL THEN 1 END) AS cex_inflow_txs,
  SUM(CASE WHEN c_from.address IS NOT NULL AND c_to.address IS NULL
      THEN amount_display / 1e9 ELSE 0 END) AS cex_outflow_B,
  COUNT(CASE WHEN c_from.address IS NOT NULL AND c_to.address IS NULL THEN 1 END) AS cex_outflow_txs,
  COUNT(DISTINCT from_owner) AS unique_senders
FROM tokens_solana.transfers t
LEFT JOIN cex_addrs c_to   ON t.to_owner   = c_to.address
LEFT JOIN cex_addrs c_from ON t.from_owner = c_from.address
WHERE token_mint_address = '{PUMP_MINT}'
  AND block_time >= TIMESTAMP '{TGE_DATE}'
  AND amount > 0
GROUP BY DATE(block_time)
ORDER BY date
"""
    print("Q2: Daily CEX netflow...")
    return run_sql(sql, timeout=600)


def q3_top_sellers(cex_values: str, limit: int = 500) -> list[dict]:
    """Top N sellers by CEX deposit volume."""
    sql = f"""
WITH cex_addrs AS (
  SELECT address, exchange_name
  FROM (VALUES {cex_values}) AS t(address, exchange_name)
)
SELECT
  t.from_owner AS address,
  SUM(t.amount_display / 1e9) AS cex_deposit_B,
  COUNT(*) AS tx_count,
  ARRAY_AGG(DISTINCT c.exchange_name) AS exchanges_used,
  MIN(DATE(t.block_time)) AS first_sell_date,
  MAX(DATE(t.block_time)) AS last_sell_date
FROM tokens_solana.transfers t
JOIN cex_addrs c ON t.to_owner = c.address
WHERE t.token_mint_address = '{PUMP_MINT}'
  AND t.block_time >= TIMESTAMP '{TGE_DATE}'
  AND t.from_owner IS NOT NULL
  AND t.from_owner NOT IN (SELECT address FROM cex_addrs)
  AND t.amount > 0
GROUP BY t.from_owner
ORDER BY cex_deposit_B DESC
LIMIT {limit}
"""
    print(f"Q3: Top {limit} sellers by CEX deposit...")
    return run_sql(sql, timeout=600)


def q4_top_buyers(cex_values: str, limit: int = 500) -> list[dict]:
    """Top N buyers by CEX withdrawal volume."""
    sql = f"""
WITH cex_addrs AS (
  SELECT address, exchange_name
  FROM (VALUES {cex_values}) AS t(address, exchange_name)
)
SELECT
  t.to_owner AS address,
  SUM(t.amount_display / 1e9) AS cex_withdraw_B,
  COUNT(*) AS tx_count,
  ARRAY_AGG(DISTINCT c.exchange_name) AS exchanges_used,
  MIN(DATE(t.block_time)) AS first_buy_date,
  MAX(DATE(t.block_time)) AS last_buy_date
FROM tokens_solana.transfers t
JOIN cex_addrs c ON t.from_owner = c.address
WHERE t.token_mint_address = '{PUMP_MINT}'
  AND t.block_time >= TIMESTAMP '{TGE_DATE}'
  AND t.to_owner IS NOT NULL
  AND t.to_owner NOT IN (SELECT address FROM cex_addrs)
  AND t.amount > 0
GROUP BY t.to_owner
ORDER BY cex_withdraw_B DESC
LIMIT {limit}
"""
    print(f"Q4: Top {limit} buyers by CEX withdrawal...")
    return run_sql(sql, timeout=600)


def q5_per_exchange_flow(cex_values: str) -> list[dict]:
    """~20 rows — per-exchange inflow + outflow totals."""
    sql = f"""
WITH cex_addrs AS (
  SELECT address, exchange_name
  FROM (VALUES {cex_values}) AS t(address, exchange_name)
)
SELECT
  COALESCE(c_to.exchange_name, c_from.exchange_name) AS exchange,
  SUM(CASE WHEN c_to.address IS NOT NULL AND c_from.address IS NULL
      THEN t.amount_display / 1e9 ELSE 0 END) AS inflow_B,
  COUNT(CASE WHEN c_to.address IS NOT NULL AND c_from.address IS NULL THEN 1 END) AS inflow_txs,
  SUM(CASE WHEN c_from.address IS NOT NULL AND c_to.address IS NULL
      THEN t.amount_display / 1e9 ELSE 0 END) AS outflow_B,
  COUNT(CASE WHEN c_from.address IS NOT NULL AND c_to.address IS NULL THEN 1 END) AS outflow_txs,
  COUNT(DISTINCT CASE WHEN c_to.address IS NOT NULL THEN t.from_owner END) AS unique_depositors
FROM tokens_solana.transfers t
LEFT JOIN cex_addrs c_to   ON t.to_owner   = c_to.address
LEFT JOIN cex_addrs c_from ON t.from_owner = c_from.address
WHERE t.token_mint_address = '{PUMP_MINT}'
  AND t.block_time >= TIMESTAMP '{TGE_DATE}'
  AND (c_to.address IS NOT NULL OR c_from.address IS NOT NULL)
  AND t.amount > 0
GROUP BY 1
ORDER BY inflow_B DESC
"""
    print("Q5: Per-exchange flow summary...")
    return run_sql(sql, timeout=600)


def q6_validation_vs_helius() -> list[dict]:
    """1 row — total CEX inflow for cross-validation with Helius cache."""
    sql = f"""
SELECT
  COUNT(*) AS total_transfers,
  SUM(amount_display / 1e9) AS total_volume_B,
  COUNT(DISTINCT from_owner) AS unique_senders,
  COUNT(DISTINCT to_owner) AS unique_receivers,
  MIN(DATE(block_time)) AS earliest_date,
  MAX(DATE(block_time)) AS latest_date
FROM tokens_solana.transfers
WHERE token_mint_address = '{PUMP_MINT}'
  AND block_time >= TIMESTAMP '{TGE_DATE}'
  AND amount > 0
"""
    print("Q6: Overall stats for validation...")
    return run_sql(sql, timeout=300)


def main() -> None:
    ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"[{ts[:19]}] Building PUMP tiered ledger via Dune...")

    cex_values, cex_lookup = build_cex_values()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = {}

    # Run all queries
    results["size_tiers"]     = q1_size_tier_distribution(cex_values)
    results["daily_netflow"]  = q2_daily_cex_netflow(cex_values)
    results["top_sellers"]    = q3_top_sellers(cex_values, limit=500)
    results["top_buyers"]     = q4_top_buyers(cex_values, limit=500)
    results["exchange_flow"]  = q5_per_exchange_flow(cex_values)
    results["overall_stats"]  = q6_validation_vs_helius()

    # Print summary
    print(f"\n=== Results ===")
    for k, v in results.items():
        print(f"  {k}: {len(v)} rows")

    if results["overall_stats"]:
        s = results["overall_stats"][0]
        print(f"\nOverall: {s.get('total_transfers',0):,} transfers, "
              f"{float(s.get('total_volume_b') or s.get('total_volume_B') or 0):.2f}B PUMP, "
              f"{s.get('unique_senders',0):,} senders")

    if results["exchange_flow"]:
        print(f"\nTop 5 exchanges by inflow:")
        for r in results["exchange_flow"][:5]:
            ib = float(r.get('inflow_b') or r.get('inflow_B') or 0)
            ob = float(r.get('outflow_b') or r.get('outflow_B') or 0)
            print(f"  {r.get('exchange','?'):20s} in={ib:.2f}B  out={ob:.2f}B")

    if results["size_tiers"]:
        print(f"\nSize tier distribution:")
        for r in results["size_tiers"]:
            print(f"  {r.get('size_tier','?'):25s} {r.get('address_count',0):>8,} addrs  {float(r.get('total_sent_b') or r.get('total_sent_B') or 0):.2f}B")

    # Save all outputs
    out = {
        "generated_at": ts,
        "pump_mint": PUMP_MINT,
        "tge_date": TGE_DATE,
        **results,
    }
    outfile = OUTPUT_DIR / "pump_dune_tiered_ledger.json"
    with open(outfile, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # Also save daily netflow separately for timeline use
    netflow_file = OUTPUT_DIR / "pump_daily_netflow.json"
    with open(netflow_file, "w") as f:
        json.dump({"generated_at": ts, "pump_mint": PUMP_MINT, "daily": results["daily_netflow"]}, f, ensure_ascii=False, indent=2)

    print(f"\nSaved → {outfile}")
    print(f"Saved → {netflow_file}")


if __name__ == "__main__":
    main()
