# Ralph Loop Configuration

## Parameters
- **Max Iterations**: 20
- **Completion Promise**: `前端图表已展示所有从TGE开始到现在的net flow`

## Task Goal
根据当前project，把所有代币设计交易所tx全部获取并上传到GitHub，最后将数据更新到前端，需要展示各个代币从TGE开始到现在的交易所net flow，更新好图表。

## Execution Requirements
1. **执行前检查**: 每次执行前或发现问题需要对整个project做inspect
2. **详细计划**: 详细计划debug或优化方案，最后再执行
3. **Debug日志**: 写的脚本最好要有详细的debug log
4. **使用工具**: 多用 Sequential thinking MCP
5. **等待数据**: 数据获取时间可能比较长，等待就行，在loop中等待
6. **前端验证**: 前端网页需要自行打开页面截图验证，是否所有需要信息都包含了

## Trigger Condition
当 PUMP 回填完成后自动启动

## Status
- Created: 2026-03-12T10:34:23Z
- PUMP Backfill: In Progress (1,000 / 271,287 transactions)
- Monitoring: Active (2-hour interval)
