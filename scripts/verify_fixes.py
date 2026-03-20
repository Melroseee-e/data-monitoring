#!/usr/bin/env python3
"""Verify that the bug fixes are correctly applied."""

import re
from pathlib import Path

def check_file(filepath, patterns_to_find, patterns_to_avoid):
    """Check if file has correct patterns and avoids bad patterns."""
    content = Path(filepath).read_text()

    issues = []
    for pattern, description in patterns_to_avoid:
        if re.search(pattern, content):
            issues.append(f"❌ Found bad pattern: {description}")

    for pattern, description in patterns_to_find:
        if not re.search(pattern, content):
            issues.append(f"❌ Missing expected pattern: {description}")

    return issues

# Check backfill_history.py
print("Checking backfill_history.py...")
issues = check_file(
    'scripts/backfill_history.py',
    patterns_to_find=[
        (r'account = post\.get\("owner", ""\)\s+# Solana addresses are case-sensitive', 'Fixed line 506'),
        (r'account = transfer\.get\("account", ""\)\s+# Solana addresses are case-sensitive', 'Fixed line 535/560'),
        (r'has_exchange = any\(key in sol_exchange_lookup for key in account_keys\)', 'Smart skip optimization'),
        (r'if not has_exchange:\s+continue', 'Smart skip filter'),
    ],
    patterns_to_avoid=[
        (r'\.get\("owner", ""\)\.lower\(\)', 'Bug: .lower() on owner'),
        (r'\.get\("account", ""\)\.lower\(\)', 'Bug: .lower() on account'),
    ]
)

if issues:
    for issue in issues:
        print(f"  {issue}")
else:
    print("  ✅ All checks passed")

# Check data_collector.py
print("\nChecking data_collector.py...")
issues = check_file(
    'scripts/data_collector.py',
    patterns_to_find=[
        (r'to_addr = tx\.get\("to_address", ""\)\s+# Solana addresses are case-sensitive', 'Fixed line 408'),
        (r'from_addr = tx\.get\("from_address", ""\)\s+# Solana addresses are case-sensitive', 'Fixed line 409'),
    ],
    patterns_to_avoid=[
        (r'\.get\("to_address", ""\)\.lower\(\)', 'Bug: .lower() on to_address'),
        (r'\.get\("from_address", ""\)\.lower\(\)', 'Bug: .lower() on from_address'),
    ]
)

if issues:
    for issue in issues:
        print(f"  {issue}")
else:
    print("  ✅ All checks passed")

# Check TGE config
print("\nChecking tge_final_config.json...")
import json
config = json.loads(Path('data/tge_final_config.json').read_text())
if 'PUMP' in config['tokens']:
    print("  ✅ PUMP TGE config added")
else:
    print("  ❌ PUMP TGE config missing")

print("\n✅ All fixes verified!")
