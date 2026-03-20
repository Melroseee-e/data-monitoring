#!/bin/bash

echo "=== Backfill Progress Monitor ==="
echo "Time: $(date)"
echo ""

# Check running processes
echo "Running Processes:"
ps aux | grep -E "backfill_history.py" | grep -v grep | awk '{print "  PID " $2 ": " $NF}'
echo ""

# Check log files
for token in BIRB TRIA UAI AZTEC PUMP; do
    logfile="backfill_${token,,}.log"
    if [ -f "$logfile" ]; then
        echo "=== $token ==="
        tail -5 "$logfile" | grep -E "(Fetching|Got|Writing|Complete|Error)" | tail -3
        echo ""
    fi
done

# Count history files
echo "=== Data Files ==="
echo "Total history files: $(ls data/history/*.jsonl 2>/dev/null | wc -l)"
echo "Latest file: $(ls -t data/history/*.jsonl 2>/dev/null | head -1 | xargs basename)"
echo ""

# Calculate completion
python3 << 'PYEOF'
import os
from datetime import datetime

existing = len([f for f in os.listdir('data/history') if f.endswith('.jsonl')])
total_expected = 808  # From earlier calculation
print(f"Overall completion: {existing}/{total_expected} = {existing/total_expected*100:.1f}%")
PYEOF
