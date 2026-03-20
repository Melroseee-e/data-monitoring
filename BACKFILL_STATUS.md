# Historical Data Backfill Status

**Started**: 2026-03-06 13:57 CST
**Last Updated**: 2026-03-06 14:12 CST
**Status**: IN PROGRESS

## Overview

- **Total Expected Days**: 808 days across 8 tokens
- **Current Completion**: 46/808 (5.7%)
- **Target Completion**: 508/808 (62.9%)
- **Estimated Time**: 5-7 hours
- **Elapsed Time**: ~15 minutes

## Running Backfill Jobs

| Token | PID | Start Date | End Date | Days | Status |
|-------|-----|------------|----------|------|--------|
| AZTEC | 63084 | 2025-07-01 | 2026-01-15 | 199 | ✅ **COMPLETE** (14:01) |
| BIRB | 1583 | 2026-01-28 | 2026-03-06 | 38 | ✅ **COMPLETE** (14:13) |
| TRIA | 60715 | 2026-01-17 | 2026-01-20 | 4 | ⏳ Running (BSC blocks 48.7M) |
| UAI | 60985 | 2025-11-06 | 2026-01-15 | 71 | ⏳ Running (BSC blocks 68.5M, ~33%) |
| PUMP | 61328 | 2025-07-12 | 2026-01-15 | 188 | ⏳ Running (400/165k txs, ~0.2%) |

**Total Days Being Backfilled**: 500 days

## Token Details

### AZTEC (Priority 3)
- **TGE**: 2025-07-01
- **Chain**: Ethereum
- **Missing**: 2025-07-01 to 2026-01-15 (199 days)
- **Estimated Time**: 2-3 hours
- **Current Status**: Processing Ethereum blocks

### PUMP (Priority 4)
- **TGE**: 2025-07-12
- **Chain**: Solana
- **Missing**: 2025-07-12 to 2026-01-15 (188 days)
- **Estimated Time**: 2-3 hours
- **Current Status**: Finding ATAs for 39 exchanges

### UAI (Priority 2)
- **TGE**: 2025-11-06
- **Chain**: BSC
- **Missing**: 2025-11-06 to 2026-01-15 (71 days)
- **Estimated Time**: 30-45 minutes
- **Current Status**: Processing BSC blocks

### TRIA (Priority 1)
- **TGE**: 2026-01-16
- **Chain**: Ethereum + BSC
- **Missing**: 2026-01-17 to 2026-01-20 (4 days)
- **Estimated Time**: 5 minutes
- **Current Status**: Processing Ethereum blocks

### BIRB (In Progress)
- **TGE**: 2026-01-28
- **Chain**: Solana
- **Missing**: 2026-01-28 to 2026-03-06 (38 days)
- **Estimated Time**: 30-45 minutes
- **Current Status**: Running since 09:47

## Already Complete

- **GWEI**: 100% (30/30 days)
- **SKR**: 100% (45/45 days)
- **SPACE**: 100% (37/37 days)

## Monitoring Commands

```bash
# Check running processes
ps aux | grep backfill_history.py | grep -v grep

# Check progress
ls data/history/*.jsonl | wc -l

# View logs
tail -f backfill_tria.log
tail -f backfill_uai.log
tail -f backfill_aztec.log
tail -f backfill_pump.log

# Monitor all
watch -n 30 './scripts/monitor_backfill.sh'
```

## Progress Updates

### 14:13 - BIRB Complete ✅
- BIRB backfill completed successfully
- 38 days of data merged into existing files
- Verified: BIRB data now in 2026-01-28, 2026-02-05, 2026-03-01
- Directory size: 2.1M → 2.5M

### 14:12 - AZTEC Complete ✅
- AZTEC backfill completed successfully
- 199 days of data merged into existing files (2026-01-16 to 2026-03-06)
- Verified: AZTEC data now present in files like 2026-03-01.jsonl
- Other 4 tokens still running

## Next Steps

1. ✅ Started all backfill jobs (BIRB, TRIA, UAI, AZTEC, PUMP)
2. ⏳ Wait for completion (~5-7 hours total, ~15 min elapsed)
3. ⏳ Verify data completeness
4. ⏳ Upload to GitHub
5. ⏳ Delete local temporary files

## Expected Final State

After all backfills complete:
- **Total Files**: 508 JSONL files
- **Date Range**: 2025-07-01 to 2026-03-06
- **Completion**: 62.9% (508/808 days)
- **Missing**: Only pre-TGE dates for each token

## Notes

- All backfills running in parallel for maximum speed
- Using smart merge logic to avoid conflicts
- Data will be committed to GitHub after verification
- Local temporary files will be cleaned up after upload
