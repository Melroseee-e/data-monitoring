#!/usr/bin/env python3
"""Monitor backfill progress by checking exchange_flows data."""

import json
from pathlib import Path
from collections import defaultdict

def monitor_progress():
    """Check how many files have exchange data for Solana tokens."""
    history_dir = Path('data/history')
    solana_tokens = {'PUMP', 'BIRB', 'SKR'}

    stats = defaultdict(lambda: {'files_with_data': 0, 'total_exchanges': set(), 'total_hours': 0})

    for file in sorted(history_dir.glob('2026-*.jsonl')):
        with open(file, 'r') as f:
            for line in f:
                data = json.loads(line)

                for token in solana_tokens:
                    if token in data.get('tokens', {}):
                        for deployment in data['tokens'][token].get('deployments', []):
                            if deployment.get('chain') == 'solana':
                                flows = deployment.get('exchange_flows', {})
                                if flows:
                                    stats[token]['files_with_data'] += 1
                                    stats[token]['total_hours'] += len(flows)
                                    for hour_data in flows.values():
                                        stats[token]['total_exchanges'].update(hour_data.keys())

    print("=" * 60)
    print("Solana Token Backfill Progress")
    print("=" * 60)

    for token in ['PUMP', 'BIRB', 'SKR']:
        s = stats[token]
        print(f"\n{token}:")
        print(f"  Files with data: {s['files_with_data']}")
        print(f"  Total hours: {s['total_hours']}")
        print(f"  Exchanges found: {len(s['total_exchanges'])}")
        if s['total_exchanges']:
            print(f"    {', '.join(sorted(s['total_exchanges']))}")

if __name__ == '__main__':
    monitor_progress()
