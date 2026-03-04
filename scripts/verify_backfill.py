#!/usr/bin/env python3
"""Verify backfill data integrity."""

import json
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
HISTORY_DIR = BASE_DIR / "data" / "history"

def verify():
    files = sorted(HISTORY_DIR.glob("*.jsonl"))
    print(f"Found {len(files)} JSONL files")

    total_size = sum(f.stat().st_size for f in files)
    print(f"Total size: {total_size / 1024 / 1024:.2f} MB")

    dates = [f.stem for f in files]
    date_objs = [datetime.strptime(d, "%Y-%m-%d") for d in dates]

    if len(date_objs) > 1:
        gaps = []
        for i in range(len(date_objs) - 1):
            diff = (date_objs[i + 1] - date_objs[i]).days
            if diff > 1:
                gaps.append((dates[i], dates[i + 1]))

        if gaps:
            print(f"⚠️  Found {len(gaps)} date gaps:")
            for g in gaps:
                print(f"  {g[0]} -> {g[1]}")
        else:
            print("✓ No date gaps found")

    for f in files[:3]:
        with open(f) as fp:
            lines = fp.read().strip().split('\n')
            print(f"  {f.name}: {len(lines)} snapshots")

    print("\n✓ Verification complete")

if __name__ == "__main__":
    verify()
