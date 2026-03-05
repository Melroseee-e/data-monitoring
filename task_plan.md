# Task Plan: 链上交易所流入流出监控系统

## Goal
构建一个自动化的链上数据监控系统，追踪 7 个代币在 38 个主要交易所的流入流出情况，通过 GitHub Pages 展示实时数据。

## Status: ⚠️ IN PROGRESS (Phase 7: 历史数据回填)

---

## Phase 7: 历史数据回填 ⚠️ IN_PROGRESS
**Status:** `in_progress`
**Started:** 2026-03-05 06:00 UTC
**Current Progress:** 4/6 代币完成 (67%)

### 已完成代币 ✅
- GWEI (Ethereum) - commit 063d0b2
- AZTEC (Ethereum) - commit 1bb2c01
- TRIA (Ethereum + BSC) - commit 66cc4c5
- SPACE (Ethereum + BSC) - commit c9fb5ba

### 进行中 ⚠️
- **UAI (BSC)** - 失败，合并冲突
  - 工作流 ID: 22716810918
  - 错误: 与AZTEC数据冲突（2026-02-09 到 2026-03-05所有文件）
  - 原因: JSONL追加模式 + Git rebase无法自动合并

### 待完成 ⏳
- BIRB (Ethereum) - 等待UAI完成

### 跳过 ⏭️
- SKR (Solana) - 需要不同API实现
- BIRB (Solana) - 需要不同API实现

### 当前问题
**合并冲突根本原因:**
多个代币回填时，同一JSONL文件被不同工作流修改，Git无法自动合并JSON Lines格式。

**解决方案: ✅ 已实施**
修改`scripts/backfill_history.py`添加智能合并逻辑（commit 459e2c4）：
1. 读取现有JSONL文件
2. 解析每行JSON
3. 合并新代币数据到现有时间戳记录
4. 写回文件
5. 避免Git冲突

**教训:**
❌ 不要重复运行失败的工作流期待不同结果
✅ 第2次失败后立即停止，深度诊断根因，修改代码

---

## Phase 1: 标签归并 ✅ COMPLETE
**Status:** complete
**Files Created:**
- `scripts/normalize_labels.py`
- `data/exchange_addresses_normalized.json`

**Result:** 121 个原始交易所标签 → 38 个标准化名称

---

## Phase 2: 数据采集器升级 ✅ COMPLETE
**Status:** complete
**Files Modified:**
- `scripts/data_collector.py`

**Changes:**
- Ethereum: Etherscan V2 API (添加 chainid 参数)
- BSC: BSCTrace (NodeReal) JSON-RPC `eth_getLogs`
- Solana: Helius RPC (getTokenAccountsByOwner + getTransaction)
- 添加 `history_summary.json` 生成

**API 成本验证:**
| API | 月使用量 | 免费额度 | 占用率 |
|-----|---------|---------|--------|
| Etherscan | ~2,880 calls | 100k/day | 0.096% |
| BSCTrace | ~118k CU | 10M CU | 1.19% |
| Helius | ~144k credits | 1M credits | 14.4% |

---

## Phase 3: 前端增强 ✅ COMPLETE
**Status:** complete
**Files Modified:**
- `web/index.html`

**Features Added:**
- Sankey 流向图 (Plotly.js)
- 历史趋势图 (Chart.js)
- 异常警报 (净流量 > 1M)
- 交易所排名 (Top 20)
- Tab 导航界面

---

## Phase 4: GitHub Actions 配置 ✅ COMPLETE
**Status:** complete
**Files Modified:**
- `.github/workflows/update-data.yml`
- `.env.example`

**Configuration:**
- 每小时自动运行 (cron: `0 * * * *`)
- 环境变量: ETHERSCAN_API_KEY, BSCTrace_API_KEY, HELIUS_API_KEY

---

## Phase 5: GitHub 部署 ✅ COMPLETE
**Status:** complete
**Actions Taken:**
1. 初始化 git 仓库
2. 创建 GitHub 仓库: https://github.com/Melroseee-e/data-monitoring
3. 配置 GitHub Secrets (3 个 API keys)
4. 启用 GitHub Pages (从 main 分支根目录)
5. 创建根目录 `index.html` 重定向

**Live Site:** https://melroseee-e.github.io/data-monitoring/

---

## Phase 6: 测试与验证 ✅ COMPLETE
**Status:** complete

**Test Results:**
- ✅ 数据采集: 所有链正常 (Ethereum, BSC, Solana)
- ✅ 前端界面: 4 个 Tab 正常显示
- ✅ GitHub Actions: 首次运行成功
- ✅ 历史数据: 已开始累积

**Sample Data:**
```
UAI (BSC): 60 transfers
BIRB (Solana): 2 transfers (26 ATAs)
AZTEC (ETH): 58 transfers
TRIA (ETH+BSC): 37 + 146 transfers
SKR (Solana): 9 transfers (37 ATAs)
GWEI (ETH): 72 transfers
SPACE (ETH+BSC): 38 + 94 transfers
```

---

## 数据存储机制

### 三层存储结构
1. **latest_data.json** - 最新快照 (每小时覆盖)
2. **history/<date>.jsonl** - 完整历史 (永久保存，追加模式)
3. **history_summary.json** - 7天汇总 (滚动窗口，168小时)

### 数据保留策略
- `latest_data.json`: 不保留历史，每次覆盖
- `history/*.jsonl`: ✅ 永久保存，不自动删除
- `history_summary.json`: 只保留最近 168 小时

### 存储空间估算
- 每条记录: ~3.5 KB
- 每日增长: 84 KB
- 每月增长: 2.52 MB
- 每年增长: 30.66 MB
- GitHub 免费额度: 1 GB (可存储 ~33 年)

---

## 时间窗口说明

### Overview 页面
- **数据范围**: 过去 1 小时 (3600 秒)
- **更新频率**: 每小时
- **数据来源**: `latest_data.json`

### 具体实现
- **Ethereum/BSC**: 通过区块高度计算 (ETH ~300 blocks, BSC ~1200 blocks)
- **Solana**: 通过 blockTime 时间戳过滤

---

## 历史数据回填可行性分析

### 各代币 TGE 以来的总 Transfer 数量

| 代币 | 链 | 总 Transfer 数 |
|------|-----|---------------|
| UAI | BSC | 2,416,518 |
| TRIA | BSC | 1,250,494 |
| SPACE | BSC | 1,735,190 |
| BIRB | Solana | 5,422,446 |
| SKR | Solana | 12,506,401 |
| AZTEC | Ethereum | >10,000 |
| TRIA | Ethereum | >10,000 |
| GWEI | Ethereum | >10,000 |
| SPACE | Ethereum | >10,000 |

**总计: 至少 2300 万+笔 Transfer 事件**

### 免费 API 额度可行性

| 链 | API 调用量 | 免费额度 | 占用率 | 可行？ |
|---|-----------|---------|--------|-------|
| Ethereum | ~200 calls | 100k/day | 0.2% | ✅ 轻松 |
| BSC | ~15,000 CU | 10M CU/月 | 0.15% | ✅ 轻松 |
| Solana | ~50k-200k credits | 1M credits/月 | 5-20% | ✅ 可以 |

**结论**: 免费额度完全足够，可以实现历史数据回填。

---

## 文档

**已创建:**
- `README.md` - 项目说明
- `IMPLEMENTATION_REPORT.md` - 实施报告
- `DEPLOYMENT.md` - 部署文档

---

## Errors Encountered

| Error | Phase | Resolution |
|-------|-------|------------|
| Python 3.9 不支持 `int \| None` 语法 | Phase 2 | 添加 `from __future__ import annotations` |
| Etherscan V1 API 已弃用 | Phase 2 | 升级到 V2 API，添加 chainid 参数 |
| GitHub Pages 只支持 `/` 或 `/docs` 路径 | Phase 5 | 使用根目录 `/`，创建重定向 index.html |
| Git push 被拒绝 (remote ahead) | Phase 5 | git pull --rebase 后重新推送 |

---

## Next Steps (Optional)

### 未来优化建议

**短期 (可选):**
1. 增加更多代币 - 编辑 `data/tokens.json`
2. 调整刷新频率 - 修改 workflow cron 表达式
3. 自定义异常阈值 - 修改 `ANOMALY_THRESHOLD` 常量

**长期 (可选):**
1. 历史数据回填脚本 - 从 TGE 开始回填所有数据
2. 数据库存储 - 替代 JSONL 文件
3. 实时推送 - WebSocket 或 SSE
4. 移动端 App - React Native / Flutter
5. 警报通知 - Telegram / Discord bot

---

## Project Structure

```
data-monitoring(chen)/
├── scripts/
│   ├── normalize_labels.py          # 标签归并
│   ├── data_collector.py            # 数据采集器
│   └── build_exchange_addresses.py  # 原有脚本
├── data/
│   ├── tokens.json                  # 代币配置
│   ├── exchange_addresses.json      # 原始地址
│   ├── exchange_addresses_normalized.json  # 归并后地址
│   ├── latest_data.json             # 最新数据
│   ├── history_summary.json         # 历史汇总
│   └── history/
│       └── 2026-03-03.jsonl         # 每日历史
├── web/
│   └── index.html                   # 前端
├── .github/workflows/
│   └── update-data.yml              # 自动化
├── index.html                       # 根目录重定向
├── README.md
├── IMPLEMENTATION_REPORT.md
├── DEPLOYMENT.md
├── .env
├── .env.example
└── requirements.txt
```

---

## Key Metrics

- **监控代币**: 7 个
- **监控交易所**: 38 个 (归并后)
- **原始交易所地址**: 347 个
- **支持链**: 3 条 (Ethereum, BSC, Solana)
- **数据更新频率**: 每小时
- **历史数据保留**: 永久 (JSONL 文件)
- **前端趋势图**: 最近 7 天
- **API 成本**: $0/月 (完全免费)
- **存储空间**: ~30 MB/年

---

## Status Summary

✅ **系统已完全部署并运行**
- 数据采集: 正常
- 前端展示: 正常
- 自动化: 正常
- 历史记录: 正常累积

**Live Site**: https://melroseee-e.github.io/data-monitoring/
