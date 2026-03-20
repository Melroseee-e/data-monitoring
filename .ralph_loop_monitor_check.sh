#!/bin/bash
# Ralph Loop 监控检查脚本

# 检查 Ralph Loop 是否活跃
if [ -f "/Users/melrose/.claude/ralph-loop.local.md" ]; then
    echo "✅ Ralph Loop is active"
    exit 0
fi

# Ralph Loop 不活跃，检查任务是否完成
# 检查数据完整性
cd "/Users/melrose/Headquarter/Crypto Intel/On-Chain Data/data-monitoring(chen)"

# 统计完整的代币数量
COMPLETE_COUNT=$(python3 << 'PYTHON'
import json
from pathlib import Path

tokens = ['UAI', 'TRIA', 'SKR', 'GWEI', 'SPACE', 'AZTEC', 'BIRB', 'PUMP']
complete = 0

for token in tokens:
    hours = []
    for f in Path('data/history').glob('*.jsonl'):
        with open(f) as fp:
            for line in fp:
                try:
                    d = json.loads(line)
                    if token in d.get('tokens', {}):
                        for dep in d['tokens'][token].get('deployments', []):
                            if dep.get('exchange_flows'):
                                hours.append(d.get('timestamp'))
                except: pass
    
    dates = len(set(h[:10] for h in hours if h))
    if dates >= 30:
        complete += 1

print(complete)
PYTHON
)

echo "Complete tokens: $COMPLETE_COUNT/8"

if [ "$COMPLETE_COUNT" -eq 8 ]; then
    echo "✅ Task complete - all 8 tokens have data"
    exit 0
else
    echo "⚠️  Ralph Loop inactive but task incomplete ($COMPLETE_COUNT/8)"
    echo "🔄 Need to restart Ralph Loop"
    exit 1
fi
