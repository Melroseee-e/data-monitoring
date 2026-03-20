#!/bin/bash
# 监控 BIRB 完成后自动启动 PUMP

BIRB_PID=67249
LOG_FILE="pump_auto_start.log"

echo "$(date): 开始监控 BIRB 进程 (PID: $BIRB_PID)" | tee -a $LOG_FILE

while true; do
    if ! ps -p $BIRB_PID > /dev/null 2>&1; then
        echo "$(date): BIRB 进程已完成！" | tee -a $LOG_FILE
        
        # 验证 BIRB 数据
        echo "$(date): 验证 BIRB 数据..." | tee -a $LOG_FILE
        python3 << 'PYTHON'
import json
from pathlib import Path

birb_hours = []
for f in sorted(Path('data/history').glob('*.jsonl')):
    with open(f) as fp:
        for line in fp:
            try:
                d = json.loads(line)
                if 'BIRB' in d.get('tokens', {}):
                    for dep in d['tokens']['BIRB'].get('deployments', []):
                        if dep.get('exchange_flows'):
                            birb_hours.append(d.get('timestamp'))
            except: pass

birb_dates = sorted(set(h[:10] for h in birb_hours if h))
print(f"BIRB 数据: {len(birb_hours)} 小时, {len(birb_dates)} 天")
PYTHON
        
        # 启动 PUMP 回填
        echo "$(date): 启动 PUMP 回填..." | tee -a $LOG_FILE
        nohup python3 scripts/backfill_history.py --token PUMP > backfill_PUMP_$(date +%Y%m%d_%H%M%S).log 2>&1 &
        PUMP_PID=$!
        echo "$(date): PUMP 回填已启动 (PID: $PUMP_PID)" | tee -a $LOG_FILE
        
        break
    fi
    
    # 每 5 分钟检查一次
    sleep 300
done

echo "$(date): 监控脚本结束" | tee -a $LOG_FILE
