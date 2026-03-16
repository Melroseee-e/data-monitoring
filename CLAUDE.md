# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

On-chain exchange flow monitoring system that tracks token transfers between centralized exchanges and users across Ethereum, BSC, and Solana. Data is collected hourly via GitHub Actions and visualized at https://melroseee-e.github.io/data-monitoring/.

## Core Architecture

### Data Flow
1. **Collection** (`data_collector.py`): Fetches recent transfers from chain APIs
2. **Storage**: Writes to `data/latest_data.json` + `data/history/<date>.jsonl`
3. **Backfill** (`backfill_history.py`): Historical data collection from TGE date
4. **Visualization**: Static HTML frontend reads JSON files

### Multi-Chain Design

**EVM Chains (Ethereum, BSC)**:
- Use contract address as identifier
- Addresses are case-insensitive (stored lowercase)
- Ethereum: Etherscan API (tokentx endpoint)
- BSC: NodeReal BSCTrace (eth_getLogs RPC)

**Solana**:
- Use mint address as identifier
- Addresses are **case-sensitive** (base58 encoding)
- Helius RPC: getSignaturesForAddress → getTransaction (jsonParsed)
- Must find Associated Token Accounts (ATAs) for each exchange first

### Exchange Address Matching

**Critical**: Solana addresses must preserve original case. Never use `.lower()` on Solana addresses.

```python
# Correct lookup table construction
key = addr if chain == "solana" else addr.lower()
lookup[chain][key] = exchange_name
```

## Key Files

### Configuration
- `data/tokens.json`: Monitored tokens (symbol → chain + contract)
- `data/exchange_addresses_normalized.json`: Exchange addresses per chain
- `data/tge_final_config.json`: Token Generation Event dates for backfill
- `.env`: API keys (ETHERSCAN_API_KEY, BSCTrace_API_KEY, HELIUS_API_KEY)

### Data Storage
- `data/latest_data.json`: Most recent hourly snapshot
- `data/history/<YYYY-MM-DD>.jsonl`: Daily aggregated data (one JSON per line)
- `data/history_summary.json`: Aggregated statistics

### Scripts
- `data_collector.py`: Hourly data collection (run by GitHub Actions)
- `backfill_history.py`: Historical backfill from TGE date
- `normalize_labels.py`: Merge exchange address labels

## Common Commands

### Setup
```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python scripts/normalize_labels.py
```

### Data Collection
```bash
# Collect latest data (1 hour lookback)
python scripts/data_collector.py

# Backfill specific token from TGE
python scripts/backfill_history.py --token PUMP

# Backfill all tokens
python scripts/backfill_history.py
```

### Monitoring
```bash
# Check backfill progress
python scripts/monitor_backfill_progress.py

# Verify data integrity
python scripts/verify_backfill.py
```

### Testing
```bash
# Test Solana exchange matching
python scripts/test_solana_exchange_matching.py

# Verify smart skip optimization
python scripts/verify_smart_skip_safety.py
```

## Backfill Architecture

### Smart Skip Optimization

**Problem**: Processing all Solana transactions is slow (56 hours for PUMP's 165k transactions).

**Solution**: Pre-filter transactions by checking if `accountKeys` contain any exchange addresses before detailed parsing. Only 0.6% of transactions involve exchanges.

```python
# In batch processing loop
account_keys = tx.get("transaction", {}).get("message", {}).get("accountKeys", [])
has_exchange = any(key in sol_exchange_lookup for key in account_keys)
if not has_exchange:
    continue  # Skip 99.4% of transactions
```

**Impact**: Reduces processing time from 56 hours → 0.3 hours (99.4% savings).

### Rate Limiting

All APIs have rate limits. The backfill script handles this with:
- Batch processing (50 transactions per RPC call)
- Sleep intervals (0.5s between batches)
- Exponential backoff on 429 errors
- Fallback to individual calls on batch failures

**Known Issues (2026-03-12)**:
- Fixed batch size and delay don't adapt to API load
- BIRB backfill encountered 137+ rate limit errors in 1 hour
- Current speed: ~5000 tx/hour with frequent rate limiting

**Planned Optimizations**:
1. **Adaptive Batch Size**: Dynamically adjust batch size (10-100) based on success rate
2. **Adaptive Delay**: Adjust sleep time (0.2-5.0s) based on rate limit frequency
3. **Exponential Backoff**: Use exponential backoff with jitter for retries
4. **Rate Limit Monitoring**: Track success rate over sliding window, slow down if < 80%

**Expected Impact**:
- Reduce rate limit errors by 70%
- Increase throughput by 2-3x
- PUMP backfill time: 33h → 10-15h

## Data Format

### History JSONL Structure
```json
{
  "timestamp": "2026-03-11T14:00:00Z",
  "tokens": {
    "PUMP": {
      "deployments": [{
        "chain": "solana",
        "contract": "pumpCm...",
        "exchange_flows": {
          "2026-03-11T14:00:00Z": {
            "Binance": {
              "inflow": 1234.56,
              "outflow": 789.01,
              "net_flow": 445.55,
              "inflow_tx_count": 12,
              "outflow_tx_count": 8
            }
          }
        }
      }]
    }
  }
}
```

## Critical Bugs Fixed

### Bug #1: Solana Address Case Sensitivity (2026-03-12)

**Issue**: All Solana tokens had empty `exchange_flows` due to `.lower()` being called on addresses before matching.

**Fix**: Removed `.lower()` from 5 locations:
- `backfill_history.py`: Lines 506, 535, 560
- `data_collector.py`: Lines 408, 409

**Verification**: Run `python scripts/verify_fixes.py`

## API Usage Limits

| API | Free Tier | Monthly Usage | Notes |
|-----|-----------|---------------|-------|
| Etherscan | 100k calls/day | ~2,880/month | 0.096% usage |
| BSCTrace | 10M CU/month | ~118k/month | 1.19% usage |
| Helius | 1M credits/month | ~144k/month | 14.4% usage |

## Development Notes

- Always test Solana changes with `test_solana_exchange_matching.py` first
- Backfill runs can take hours - use background processes and monitoring
- History files are committed to git - keep them under 50MB per file
- Frontend is static HTML - no build step required

## Backfill Status and Lessons Learned

### Current Status (2026-03-12 12:50)

**Completed Tokens (6/8)**:
- UAI: 127 days (100%)
- TRIA: 56 days (100%)
- SKR: 51 days (100%)
- GWEI: 36 days (100%)
- SPACE: 43 days (100%)
- AZTEC: 33/35 days (94.3%) - No exchange activity before 2026-02-06

**In Progress (2/8)**:
- BIRB: 5000/14250 tx (35%) - ETA 1.9 hours
- PUMP: 0/167000 tx (0%) - ETA 33 hours (needs optimization)

### Lessons Learned

1. **Transaction Volume Varies Widely**:
   - BIRB: 14,250 transactions
   - PUMP: 167,000 transactions (11.7x more)
   - Always check total signatures before estimating time

2. **Rate Limiting is the Bottleneck**:
   - Smart skip reduces processing by 99.4%
   - But rate limits still occur frequently
   - Need adaptive strategies, not fixed delays

3. **Parallel Processing Risks**:
   - Running BIRB + PUMP simultaneously doubles rate limit hits
   - Better to run sequentially for large backfills
   - Consider parallel only for small tokens

4. **Frontend First Approach**:
   - Show complete data immediately
   - Display "Backfill in progress" for incomplete tokens
   - Users can see progress without waiting for 100% completion

5. **Monitoring is Critical**:
   - Log files essential for debugging (e.g., `backfill_BIRB_*.log`)
   - Progress indicators every 500 transactions
   - Rate limit statistics help identify bottlenecks

### Best Practices

1. **Before Starting Backfill**:
   - Check total signatures: `getSignaturesForAddress` with limit=1000
   - Estimate time: transactions / 5000 per hour
   - Verify smart skip is enabled

2. **During Backfill**:
   - Monitor log files: `tail -f backfill_*.log`
   - Check rate limit frequency
   - Don't interrupt if > 30% complete

3. **After Backfill**:
   - Verify data coverage: check date ranges
   - Regenerate TGE chart data: `python scripts/generate_tge_chart_data.py`
   - Push to GitHub and verify frontend

4. **Rate Limit Management**:
   - Start with conservative settings (batch=50, delay=0.5s)
   - Monitor success rate in first 1000 transactions
   - Adjust if rate limit errors > 10%

## Monitoring Long-Running Tasks

### Using /loop for Periodic Monitoring

For long-running backfill tasks, use the `/loop` command to automatically check status at intervals:

```bash
# Check backfill status every 5 minutes
/loop 5m ./check_backfill_status.sh

# Default interval is 10 minutes if not specified
/loop python scripts/monitor_backfill_progress.py
```

The `/loop` command will:
- Run the specified command/script at regular intervals
- Automatically send results back to the session
- Continue until manually cancelled or task completes

**Note**: This is different from cron jobs - `/loop` runs within the current Claude Code session and will stop when the session ends.

### Quick Status Check Script

`check_backfill_status.sh` provides a comprehensive status overview:
- Running backfill processes (PID and token)
- Latest progress from log files
- Data written to disk

Run manually: `./check_backfill_status.sh`
