#!/bin/bash
# 持续监控 backfill 进度

while true; do
    clear
    echo "=== Solana Backfill 监控 ==="
    echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""

    # 检查进程状态
    echo "进程状态:"
    for pid in 16292 16349 16433; do
        if ps -p $pid > /dev/null 2>&1; then
            token=$(ps -p $pid -o command= | grep -oE "(PUMP|BIRB|SKR)")
            echo "  ✓ $token (PID: $pid) 运行中"
        fi
    done
    echo ""

    # 显示最新进度
    echo "最新进度:"
    for token in PUMP BIRB SKR; do
        echo "  $token:"
        tail -3 backfill_${token}_*.log 2>/dev/null | sed 's/^/    /'
    done
    echo ""

    # 显示数据统计
    echo "数据写入统计:"
    python3 scripts/monitor_backfill_progress.py | grep -A 3 "PUMP:\|BIRB:\|SKR:" | sed 's/^/  /'

    echo ""
    echo "按 Ctrl+C 退出监控"
    sleep 10
done
