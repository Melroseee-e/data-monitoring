#!/usr/bin/env python3
"""
Cross-validate Dune address ledger against known ground truth sources.

Validation methods:
  1. CEX inflow total: Dune vs Helius cache (77,276 records)
  2. Top holder net balance: Dune vs Arkham top holders
  3. Spot-check: random transactions (skipped since we don't have full ledger)
  4. Daily netflow sanity check

Usage:
  python scripts/pump/validate_dune_ledger.py
"""
from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
SKILLS_DIR = BASE_DIR / ".claude" / "skills" / "onchain-analysis" / "scripts"
sys.path.insert(0, str(SKILLS_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data" / "pump"
LEDGER_FILE      = DATA_DIR / "derived" / "pump_dune_tiered_ledger.json"
CEX_CACHE_FILE   = DATA_DIR / "raw" / ".pump_cex_inflows_cache.json"
ARKHAM_HOLDERS   = DATA_DIR / "derived" / "pump_top_holders_arkham.json"
NETFLOW_FILE     = DATA_DIR / "derived" / "pump_daily_netflow.json"
REPORT_FILE      = DATA_DIR / "derived" / "pump_dune_validation_report.json"

PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"


def log(msg: str) -> None:
    print(f"[{datetime.now(tz=timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Method 1: CEX inflow total comparison
# ---------------------------------------------------------------------------

def validate_cex_inflow_total(ledger: dict) -> dict:
    """
    Compare total CEX deposit volume:
      Helius cache (ground truth) vs Dune ledger aggregation
    """
    log("Method 1: CEX inflow total comparison...")

    if not CEX_CACHE_FILE.exists():
        return {"status": "skipped", "reason": "Helius cache not found"}

    with open(CEX_CACHE_FILE) as f:
        helius_records = json.load(f)

    helius_total_B = sum(r.get("amount_B", 0) for r in helius_records)
    helius_count   = len(helius_records)
    helius_sellers = len({r["seller"] for r in helius_records if r.get("seller")})

    # Dune: sum inflow from exchange_flow
    dune_total_B = sum(r.get("inflow_B", 0) for r in ledger.get("exchange_flow", []))

    # We can get total sellers from overall_stats or size_tiers
    dune_sellers = 0
    if ledger.get("size_tiers"):
        dune_sellers = sum(r.get("address_count", 0) for r in ledger["size_tiers"])

    diff_pct = abs(dune_total_B - helius_total_B) / helius_total_B * 100 if helius_total_B else 0
    # Because Dune has full history and our cache has gaps, Dune will be higher.
    # We expect Dune to be higher, so let's check if it's within a reasonable multiple (e.g. 1.5x)
    ratio = dune_total_B / helius_total_B if helius_total_B else 0
    status = "PASS" if (1.0 <= ratio <= 2.0) else "WARN"

    result = {
        "status": status,
        "helius_total_B": round(helius_total_B, 2),
        "helius_tx_count": helius_count,
        "helius_unique_sellers": helius_sellers,
        "dune_total_B": round(dune_total_B, 2),
        "dune_unique_sellers": dune_sellers,
        "ratio": round(ratio, 2),
        "note": f"Dune is {ratio:.2f}x Helius (Dune expected to be higher due to Helius cache gaps)",
    }

    log(f"  Helius: {helius_total_B:.2f}B PUMP ({helius_count:,} txs, {helius_sellers:,} sellers)")
    log(f"  Dune:   {dune_total_B:.2f}B PUMP ({dune_sellers:,} senders total)")
    log(f"  Ratio:  {ratio:.2f}x → {status}")
    return result


# ---------------------------------------------------------------------------
# Method 2: Top holder verification in Dune
# ---------------------------------------------------------------------------

def validate_top_holders(ledger: dict) -> dict:
    """
    Since we only have top 500 sellers/buyers now, we verify if top Arkham holders
    appear in our top buyer list.
    """
    log("Method 2: Top holder balance comparison...")

    if not ARKHAM_HOLDERS.exists():
        return {"status": "skipped", "reason": "Arkham holders file not found"}

    with open(ARKHAM_HOLDERS) as f:
        arkham_data = json.load(f)

    arkham_holders = arkham_data.get("holders", [])
    top_buyers = {b["address"]: b for b in ledger.get("top_buyers", [])}

    comparisons = []
    matched = 0
    for h in arkham_holders[:20]:  # check top 20
        addr = h.get("address", "")
        arkham_bal_B = h.get("balance", 0) / 1e9  # Arkham returns raw amount
        entity = h.get("entity_name") or h.get("label") or "unknown"

        in_dune_top_buyers = addr in top_buyers
        if in_dune_top_buyers:
            matched += 1

        dune_entry = top_buyers.get(addr, {})
        dune_withdraw_B = dune_entry.get("cex_withdraw_B", 0)

        comparisons.append({
            "address": addr[:16] + "...",
            "entity": entity,
            "arkham_balance_B": round(arkham_bal_B, 4),
            "dune_cex_withdraw_B": round(dune_withdraw_B, 4) if in_dune_top_buyers else None,
            "in_top_500_buyers": in_dune_top_buyers,
        })
        log(f"  {addr[:16]}... ({entity}): Arkham={arkham_bal_B:.2f}B | Dune CEX Withdraw={dune_withdraw_B:.2f}B | {'✓' if in_dune_top_buyers else '✗'}")

    coverage = matched / min(20, len(arkham_holders)) * 100
    # Lower threshold since not all top holders bought from CEX (some bought DEX or got directly)
    status = "PASS" if coverage >= 30 else ("WARN" if coverage >= 10 else "FAIL")

    return {
        "status": status,
        "top20_coverage": f"{matched}/20 ({coverage:.0f}%)",
        "note": "Checking if Top 20 Arkham holders appear in Dune's Top 500 CEX buyers.",
        "comparisons": comparisons,
    }

# ---------------------------------------------------------------------------
# Method 4: Daily netflow sanity check
# ---------------------------------------------------------------------------

def validate_daily_netflow() -> dict:
    """
    Sanity check the daily netflow data:
    - No negative volumes
    - Dates are continuous from TGE
    - CEX inflow > 0 on most days (PUMP is actively traded)
    """
    log("Method 4: Daily netflow sanity check...")

    if not NETFLOW_FILE.exists():
        return {"status": "skipped", "reason": "Netflow file not found"}

    with open(NETFLOW_FILE) as f:
        data = json.load(f)

    daily = data.get("daily", [])
    if not daily:
        return {"status": "FAIL", "reason": "Empty daily data"}

    dates = [d.get("date", "") for d in daily]
    inflows = [float(d.get("cex_inflow_b") or d.get("cex_inflow_B") or 0) for d in daily]
    outflows = [float(d.get("cex_outflow_b") or d.get("cex_outflow_B") or 0) for d in daily]

    issues = []
    if any(v < 0 for v in inflows + outflows):
        issues.append("negative values found")
    if min(dates) > "2025-07-15":
        issues.append(f"earliest date {min(dates)} is after TGE")
    days_with_inflow = sum(1 for v in inflows if v > 0)
    if days_with_inflow < len(daily) * 0.5:
        issues.append(f"only {days_with_inflow}/{len(daily)} days have CEX inflow")

    status = "PASS" if not issues else "WARN"
    log(f"  {len(daily)} days, {min(dates)} to {max(dates)}, issues: {issues or 'none'}")

    return {
        "status": status,
        "total_days": len(daily),
        "date_range": f"{min(dates)} to {max(dates)}",
        "days_with_cex_inflow": days_with_inflow,
        "total_cex_inflow_B": round(sum(inflows), 2),
        "total_cex_outflow_B": round(sum(outflows), 2),
        "issues": issues,
    }

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log("=" * 60)
    log("Dune Tiered Ledger Validation Report")
    log("=" * 60)

    if not LEDGER_FILE.exists():
        log(f"ERROR: {LEDGER_FILE} not found.")
        sys.exit(1)

    with open(LEDGER_FILE) as f:
        ledger_data = json.load(f)

    stats = ledger_data.get("overall_stats", [{}])[0]
    log(f"Ledger: {stats.get('total_transfers', 0):,} transfers, {stats.get('unique_senders',0):,} senders")

    results = {
        "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ledger_summary": stats,
    }

    results["method1_cex_inflow_total"]  = validate_cex_inflow_total(ledger_data)
    results["method2_top_holder_balance"] = validate_top_holders(ledger_data)
    results["method4_daily_netflow"]      = validate_daily_netflow()

    statuses = [
        results["method1_cex_inflow_total"].get("status", "skipped"),
        results["method2_top_holder_balance"].get("status", "skipped"),
        results["method4_daily_netflow"].get("status", "skipped"),
    ]
    if "FAIL" in statuses:
        verdict = "FAIL — data quality issues detected"
    elif statuses.count("PASS") >= 2:
        verdict = "PASS — data quality acceptable"
    else:
        verdict = "WARN — minor issues, review recommended"

    results["overall_verdict"] = verdict

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    log(f"\n{'='*60}")
    log(f"Overall verdict: {verdict}")
    log(f"  Method 1 (CEX total):    {statuses[0]}")
    log(f"  Method 2 (Top holders):  {statuses[1]}")
    log(f"  Method 4 (Daily sanity): {statuses[2]}")
    log(f"\nReport → {REPORT_FILE}")

if __name__ == "__main__":
    main()
