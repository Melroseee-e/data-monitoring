#!/bin/bash
echo "=== Backfill Process Status ==="
ps aux | grep -E "backfill_history.py.*(PUMP|BIRB|SKR)" | grep -v grep | awk '{print $2, $11, $12, $13}'
echo ""
echo "=== Latest Progress ==="
for token in PUMP BIRB SKR; do
    echo "--- $token ---"
    tail -5 backfill_${token}_*.log 2>/dev/null | tail -3
    echo ""
done
echo "=== Data Written ==="
python3 scripts/monitor_backfill_progress.py
