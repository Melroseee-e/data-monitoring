#!/usr/bin/env python3
"""Clean Solana token exchange_flows data before re-backfill."""

import json
from pathlib import Path

def clean_solana_exchange_flows():
    """Remove exchange_flows for Solana tokens (PUMP, BIRB, SKR)."""
    history_dir = Path('data/history')
    solana_tokens = {'PUMP', 'BIRB', 'SKR'}

    modified_count = 0

    for file in sorted(history_dir.glob('*.jsonl')):
        lines = []
        file_modified = False

        with open(file, 'r') as f:
            for line in f:
                data = json.loads(line)

                # Clean Solana token exchange_flows
                for token in solana_tokens:
                    if token in data.get('tokens', {}):
                        for deployment in data['tokens'][token].get('deployments', []):
                            if deployment.get('chain') == 'solana' and deployment.get('exchange_flows'):
                                deployment['exchange_flows'] = {}
                                file_modified = True

                lines.append(json.dumps(data))

        if file_modified:
            with open(file, 'w') as f:
                f.write('\n'.join(lines) + '\n')
            modified_count += 1
            print(f"✓ Cleaned {file.name}")

    print(f"\n✅ Cleaned {modified_count} files")

if __name__ == '__main__':
    clean_solana_exchange_flows()
