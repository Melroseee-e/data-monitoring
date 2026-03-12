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
