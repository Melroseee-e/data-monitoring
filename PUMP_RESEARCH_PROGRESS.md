# PUMP Token Research - Phase 1 & 7 Progress Report

**Generated**: 2026-03-18 10:06 UTC
**Status**: Phase 1 In Progress, Phase 7 Completed

---

## Executive Summary

Phase 7 (信息验证) 已完成，研究专员通过 Exa Deep Research 和 Web Search 验证了大量关键信息。Phase 1 (地址发现) 正在进行中，已验证多个关键地址。

---

## Phase 7: 信息验证 - 关键发现

### ✅ 已验证的地址

#### 1. 回购钱包 (HIGH Confidence)
- **地址**: `3vkpy5YHqnqJTnA5doWTpcgKyZiYsaXYzYM9wm8s3WTi`
- **用途**: 代币回购和销毁
- **当前余额**: 62.31 PUMP (几乎为空，代币已转出)
- **累计回购**: $310-328M (截至 2026-03)
- **供应移除**: 27.10-29.52% 流通供应
- **验证来源**: Solscan, Dune Analytics, CryptoRank, Tokenomics.com
- **置信度**: 95%

#### 2. 鲸鱼/分发钱包 (HIGH Confidence)
- **地址**: `9UcygiamY92yGntGkUkBKi4SdApxkBMZd9QSo6wMC2dN`
- **用途**: Vesting 分发 (疑似)
- **当前余额**: 88 亿 PUMP (2026-03-18 验证)
- **原始分配**: 200 亿 PUMP (2025-07 来自 Pump.fun Custodian)
- **主要转账**:
  - 2026-02-26: 112 亿 PUMP ($21.22M) → Kraken
- **验证来源**: CryptoAdventure, BitcoinWorld, Binance Square
- **置信度**: 85%

#### 3. 团队钱包 (MEDIUM-HIGH Confidence)
- **地址前缀**: `77DsB...` (完整地址未一致报告)
- **用途**: 团队代币托管
- **原始分配**: 37.5 亿 PUMP (2025-07)
- **出售活动**: 33.76 亿 PUMP (~$7.2M) 在 2026-02-17 至 02-21
  - 2026-02-19: 20.7 亿 PUMP ($4.55M)
  - 2026-02-17: 5.43 亿 PUMP ($1.2M)
  - 2026-02-21: 8.33 亿 PUMP
- **剩余余额**: 3.73 亿 PUMP (~$788K, 截至 2026-02-21)
- **验证来源**: Onchain Lens, Lookonchain, CryptoRank, KuCoin News
- **置信度**: 75%
- **⚠️ 问题**: 在 cliff 解锁日期 (2026-07-12) 之前就有出售活动

#### 4. 金库钱包 (LOW Confidence)
- **地址**: `G8CcfRffqZWHSAQJXLDfwbAkGE95SddUqVXnTrL4kqjm`
- **用途**: 金库 (声称)
- **当前余额**: 1039.6 亿 PUMP (10.4% 总供应)
- **验证来源**: 无可靠来源
- **置信度**: 20%
- **状态**: 需要链上验证

---

## Tokenomics 验证

### ✅ 已确认的分配
- **总供应**: 1 万亿 PUMP (HIGH confidence)
- **TGE 日期**: 2025-07-12 (HIGH confidence)
- **团队分配**: 20% (2000 亿 PUMP) (HIGH confidence)
- **投资者分配**: 13% (1300 亿 PUMP) (HIGH confidence)
- **Vesting 时间表**: 12 个月 cliff + 36 个月线性 (HIGH confidence)
- **Cliff 解锁日期**: 2026-07-12 (HIGH confidence)

### ❌ 未验证的信息
- **Vesting 合约地址**: 未找到公开的智能合约地址
- **Bitget 充值**: 17.57 亿 PUMP (2026-03-05) - 无可靠来源
- **金库钱包**: G8Ccf... - 未通过研究验证

---

## 回购机制验证

### ✅ 已确认
- **机制**: 100% 平台日收入用于回购
- **频率**: 每日自动回购
- **代币处理**: 销毁 (永久移除流通)
- **累计回购**: $310-328M (截至 2026-03)
- **周平均**: $8-9M
- **开始日期**: 2025-07-15
- **新系统**: 2026-03-14 推出 AI 代理回购系统

### 数据来源
- Dune Analytics 实时监控面板
- Solscan 链上交易历史
- 官方 Twitter (@pumpdotfun) 周报

---

## 重大转账事件

### ✅ 已验证
1. **2026-02-26**: 112 亿 PUMP ($21.22M) → Kraken
   - 来源: 9Ucygi... (vesting 分发钱包)
   - 目的: Vesting 分发 (疑似)

2. **2025-09-11**: 130 亿 PUMP ($74.24M) → Kraken
   - 来源: pump.fun 官方钱包
   - 目的: 流动性添加

3. **2025-08-18**: 25 亿 PUMP ($9.19M) → OKX
   - 来源: pumpdotfun 分发钱包
   - 目的: 交易所流动性

4. **2026-02-17 至 02-21**: 33.76 亿 PUMP ($7.2M) → DEX
   - 来源: 77DsB... (团队钱包)
   - 目的: 团队代币出售

### ❌ 未验证
- **2026-03-05**: 17.57 亿 PUMP → Bitget (无可靠来源)

---

## 关键问题与风险

### 1. 无公开 Vesting 合约 (MEDIUM Severity)
- **问题**: 尽管声称有时间锁定，但未公开智能合约地址
- **影响**: 无法独立验证 vesting 执行
- **建议**: 要求 pump.fun 团队公开 vesting 合约地址

### 2. 团队钱包提前出售 (MEDIUM Severity)
- **问题**: 团队钱包 77DsB 在 cliff 解锁日期前出售 $7.2M
- **影响**: 表明代币可能未完全锁定，或该钱包不受 vesting 约束
- **建议**: 监控该钱包的持续出售活动

### 3. 官方文档有限 (LOW Severity)
- **问题**: 无白皮书、详细 tokenomics 页面或官方钱包地址披露
- **影响**: 依赖第三方分析进行验证
- **建议**: 交叉验证多个来源

### 4. 鲸鱼集中度高 (MEDIUM Risk)
- **发现**: 60% 代币由鲸鱼持有 (前 340 买家)
- **影响**: 高抛售风险
- **建议**: 追踪鲸鱼地址的流动

---

## Phase 1: 地址发现 - 当前状态

### 进行中的工作
1. **团队钱包发现**: 正在通过 CEX 充值事件反查
   - 脚本运行中: `discover_pump_team_wallets.py`
   - 目标: 找到 77DsB 的完整地址

2. **Top 500 持有者分析**: 待获取
   - 需要: 从 Helius 或其他来源获取 Top 500 持有者
   - 目的: 识别鲸鱼、DEX、未标记的 CEX 地址

3. **Vesting 合约搜索**: 待执行
   - 目标: 查找 Streamflow/Bonfida/自定义锁仓合约

---

## 下一步行动

### 立即任务 (Phase 1)
1. ✅ 等待 `discover_pump_team_wallets.py` 完成
2. ⏳ 获取 PUMP Top 500 持有者数据
3. ⏳ 搜索 77DsB 完整地址
4. ⏳ 验证金库钱包 G8Ccf...
5. ⏳ 识别鲸鱼地址 (排除 CEX/官方/DEX)
6. ⏳ 查找 vesting 合约

### 后续阶段
- **Phase 2**: 回购行为分析 (依赖 Phase 1)
- **Phase 3+4**: 团队和鲸鱼追踪 (依赖 Phase 1)
- **Phase 5**: Vesting 和解锁分析 (依赖 Phase 1)
- **Phase 6**: Dashboard 开发

---

## 数据文件

### 已创建
- `data/pump_addresses.json` - 地址标签数据库
- `data/pump_verification_report.json` - Phase 7 验证报告
- `data/pump_official_sources.json` - 官方来源汇总
- `data/phase7_verification_results.json` - 链上验证结果

### 脚本
- `scripts/verify_pump_buyback_wallet.py` - 验证回购和金库钱包
- `scripts/discover_pump_team_wallets.py` - 发现团队钱包 (运行中)
- `scripts/verify_research_findings.py` - 验证研究发现

---

## 置信度评分

| 项目 | 置信度 | 状态 |
|------|--------|------|
| 回购机制 | 95% | ✅ 已验证 |
| 回购钱包地址 | 95% | ✅ 已验证 |
| 团队分配百分比 | 90% | ✅ 已验证 |
| Vesting 时间表 | 85% | ✅ 已验证 |
| 鲸鱼转账事件 | 85% | ✅ 已验证 |
| 团队钱包识别 | 75% | ⚠️ 部分验证 |
| 金库钱包地址 | 20% | ❌ 未验证 |
| Vesting 合约地址 | 10% | ❌ 未找到 |
| **总体验证** | **70%** | ⏳ 进行中 |

---

## 研究方法

### 工具使用
- Exa Deep Research (deep-reasoning 模式)
- Jina Web Search
- Jina URL Reader
- Helius RPC API
- Solscan / Solana Explorer

### 来源分析
- 50+ 来源交叉验证
- 高可信度来源: CryptoRank, Blockchain.news, Nansen
- 中等可信度来源: BitcoinWorld, CryptoAdventure, PANews

---

**报告结束**
