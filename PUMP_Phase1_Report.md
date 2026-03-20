# PUMP Token — Phase 1 链上地址发现与追踪报告

**报告日期**: 2026-03-19
**数据截止**: 2026-03-19
**链**: Solana
**合约**: `pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn`
**TGE**: 2025-07-12
**分析工具**: Helius RPC (getTokenLargestAccounts, getAccountInfo jsonParsed, Enhanced API /v0/addresses/{addr}/transactions)

---

## 执行摘要

Phase 1 对 PUMP 代币 Top 20 持仓地址进行了完整的链上追踪与分类。核心结论：

- **真实流通量远低于官方公布的 634B**。大量"流通"代币实际静止于官方 Squads 金库、内部人员钱包。
- **5 个 Squads 金库中有 2 个（V4、V5）已确认提前向 CEX 出售**，合计约 15B PUMP，早于 2026-07-12 的正式 Cliff 解锁。
- **"Aug21 投资者三件套"被重新分类为联创人内部人员持仓**：三个钱包共 70B PUMP，均由同一资金方控制，社区研究指向 Pump.fun 联创人 @a1lon9 (Alon)。
- **Investor Wallet #1（9Ucygiam）已向 Kraken 售出 11.2B PUMP**（$21.2M），是唯一确认大规模 CEX 抛售的外部投资者。
- **协议回购力度显著**：回购金库已累积 103.96B PUMP（$310M+），有力对冲卖压。

---

## 一、代币总供应与分布结构

| 类别 | 数量 (B) | 占总供应 | 状态 |
|---|---|---|---|
| **主锁仓库（Token Custodian）** | 365.46 | 36.5% | 🔒 待解锁 |
| **回购金库（Buyback Treasury）** | 103.96 | 10.4% | 🏦 协议持有 |
| **社区储备（Community Reserve）** | 80.00 | 8.0% | 🔒 协议持有 |
| **团队 Squads 金库 ×5（当前余额）** | 107.52 | 10.8% | ⚠ 部分已售出 |
| **联创人内部人员集群（Aug21 trio）** | 70.00 | 7.0% | 🔒 当前锁定 |
| **Investor Wallet #1（9Ucygiam）** | 8.80 | 0.9% | ⚠ 已部分抛售 |
| **Official Multisig #2** | 19.13 | 1.9% | ✅ 生态奖励分发 |
| **运营金库（Operational Vault）** | 24.00 | 2.4% | 🔒 未动 |
| **运营钱包（Operational Wallet）** | 10.00 | 1.0% | 🔒 未动 |
| **CEX 热钱包（链上）** | 51.26 | 5.1% | 交易所托管 |
| **ICO 分发合约（PDA，已清空）** | 0 | — | ✅ 已完成 |

> **真实自由流通估算**: 约 220B PUMP（22%）
> 官方报告流通量 634B 包含大量静止于协议内部、金库或锁仓钱包的代币。

---

## 二、关键地址逐一分析

### 2.1 Token Custodian（主锁仓库）

| 字段 | 值 |
|---|---|
| 地址 | `Cfq1ts1iFr1eUWWBm8eFxUzm5R3YA3UvMZznwiShbgZt` |
| 当前余额 | **365.46B PUMP**（36.5% 总供应） |
| 收到时间 | 2025-07-10（TGE 前 2 天）全量 1000B |
| 已分发 | 634.54B，分配至所有子金库 |
| 验证来源 | Solscan、BubbleMaps、Helius RPC |

**分析**：所有代币解锁均源自该地址。当前余额 365.46B 对应尚未分配至子金库的 Team（约 74B）+ Investor（约 40B）+ Community 线性解锁余量。

---

### 2.2 回购钱包（Buyback Wallet）

| 字段 | 值 |
|---|---|
| 地址 | `3vkpy5YHqnqJTnA5doWTpcgKyZiYsaXYzYM9wm8s3WTi` |
| Solscan 标签 | "Pump.fun: Pump Buy Back"（公开标注） |
| 首次回购 | 2025-07-16（TGE 后第 4 天） |
| 累计回购 | **$310M+**（截至 2026-03） |
| 当前余额 | ~62B PUMP（临时持仓，定期转入金库） |
| 目标金库 | `G8CcfRffqZWHSAQJXLDfwbAkGE95SddUqVXnTrL4kqjm` |

**回购金库当前持仓**: **103.96B PUMP**
- 来源：100% 市场买入，非 Token Custodian 直接分配
- 用途规划：60% 销毁 + 40% 质押奖励（官方公告）

---

### 2.3 团队 Squads 金库（5 个）

所有金库均于 **2025-07-14** 从 Token Custodian 收到初始分配，通过 **Squads V4 多签** 管理。

#### Squads Vault #1（LOCKED）

| 地址 | `9pkFKCR1mdS31JxjKdtmWg2awZUg6vJUYVY722DAcXzv` |
|---|---|
| 初始收到 | 35.00B |
| 当前余额 | **35.00B（100% 完整）** |
| 状态 | 🔒 **完全锁定，零流出** |

#### Squads Vault #2（LOCKED）

| 地址 | `BBvQteuawKB2UtExfevL8HYLjWWsgmWXsp922vFbvCfT` |
|---|---|
| 初始收到 | 25.00B |
| 当前余额 | **25.00B（100% 完整）** |
| 状态 | 🔒 **完全锁定，零流出** |

#### Squads Vault #3（LOCKED）

| 地址 | `GTeSSwovPiVirpvWJpThUWiLDSLsuApmJw621Yom3MhB` |
|---|---|
| BubbleMaps 标签 | "Squads Vault SOLANA 3" |
| 初始收到 | 25.00B |
| 当前余额 | **25.00B（100% 完整）** |
| 状态 | 🔒 **完全锁定，零流出** |

#### ⚠ Squads Vault #4（SELLING → OKX）

| 地址 | `GhFaBi8sy3M5mgG97YguQ6J3f7XH4JwV5CoW8MbzRgAU` |
|---|---|
| BubbleMaps 标签 | "Squads Vault MF III" |
| 初始收到 | 18.75B |
| 已流出 | **3.125B → OKX** |
| 当前余额 | **15.625B** |
| 状态 | ⚠ **出售中（提前于 Cliff 解锁）** |

**详细流出记录**:

| 日期 | 金额 | 目标 | 路由方式 |
|---|---|---|---|
| 2025-10-06 | 1.5625B | OKX | Vault → `FfGLiWhCDH3F...`（过路钱包）→ OKX 热钱包 |
| 2025-10-06 | 1.5625B | OKX | Vault → `FfGLiWhCDH3F...`（同一过路）→ OKX 热钱包 |

> **执行模式**：标准 Squads V4 执行链路：金库 → 临时过路钱包（SystemProgram owner，同日创建，~0.007 SOL）→ CEX 热钱包，当日完成。

#### ⚠ Squads Vault #5（ACTIVE SELLING → Bitget）

| 地址 | `5v7ZZg1D1si417WhUQF9Br2dRQEnd1sTbCfesscUCVKE` |
|---|---|
| BubbleMaps 标签 | "Squads Vault Wallet A" |
| 初始收到 | 18.75B |
| **已流出合计** | **11.859B → 全部流向 Bitget** |
| 当前余额 | **6.891B** |
| 状态 | ⚠ **持续大规模出售** |

**详细流出记录**:

| 日期 | 金额 | 目标 | 备注 |
|---|---|---|---|
| 2025-09-07 | 4.6875B | Bitget | 经过路钱包 `3K9vhQSaRt...` → `DNuUdE9on7...` → Bitget |
| 2026-03-06 | 1.758B | Bitget | 经过路钱包 `3VfiFskwmV...` → Bitget |
| 2026-03-10 | 2.461B | Bitget | 经过路钱包 `HJoMZJ14Tp...` → Bitget |
| 2026-03-13 | 1.500B | Bitget | 经过路钱包 `7EMWYeNJfd...` → Bitget |
| 2026-03-16 | 1.453B | Bitget | 同上过路钱包（拆分交付） |

> Bitget 收款地址 `A77HErqtfN1hLLpvZ9pCtu66FEtM8BveoaKbbMoZ4RiR`，Solscan 公开标注为 "Bitget Exchange"。
> 媒体报道（2026-03-05）首次揭露该地址首批 1.758B 充值事件，已完全吻合链上记录。

**五大金库合计**:

| | V1 | V2 | V3 | V4 | V5 | **合计** |
|---|---|---|---|---|---|---|
| 初始 (B) | 35 | 25 | 25 | 18.75 | 18.75 | **122.5** |
| 已出售 (B) | 0 | 0 | 0 | 3.125 | 11.859 | **14.984** |
| 当前余额 (B) | 35 | 25 | 25 | 15.625 | 6.891 | **107.516** |

---

### 2.4 团队钱包 #1（77DsB9kw）

| 地址 | `77DsB9kw8u8eKesicT44hGirsj5A2SicGdFPQZZEzPXe` |
|---|---|
| 类型 | 团队/Grant 分配钱包 |
| 初始收到 | 3.75B（2025-07-14，与 Squads 金库同批） |
| 当前余额 | **0**（已全部分发） |
| 分发时间 | 2026-02-16 至 02-21（7 个月后） |
| 验证来源 | Lookonchain、Onchain Lens、CryptoRank、链上直接追踪 |

**分发明细**（6 天内完成）:

| 日期 | 金额 | 主要去向 |
|---|---|---|
| 2026-02-16 | 0.543B | Wintermute + 其他钱包 |
| 2026-02-17 | 0.329B | Wintermute + 其他钱包 |
| 2026-02-18 | 1.201B | Wintermute + 其他钱包（最大单日） |
| 2026-02-19 | 0.732B | 多钱包 |
| 2026-02-20 | 0.571B | 多钱包 |
| 2026-02-21 | 0.374B | 多钱包 |

**资金流向分解**:
- Wintermute OTC（做市商）: **0.942B**（25%）
- DEX 及其他钱包: **2.808B**（75%）
- CEX 直接充值: **0**

> 解读：该钱包更符合"Grant Program / 流动性挖矿激励 / 做市商补偿池"性质，而非个人抛售。持有 7 个月后以小额（12-14M/笔）方式分散分发至 10+ 个地址，Wintermute 为最大单一受益方。

---

### 2.5 Official Allocation Multisig #2（8UHpWBnh）

| 地址 | `8UHpWBnhYNeAQURWjAABp8vSrzfYa69o7sfi65vYLC42` |
|---|---|
| 账户类型 | Squads 多签（isOnCurve=False） |
| 初始收到 | 20.00B（2025-07-14，与 V1-V5 同批） |
| 当前余额 | **19.131B** |
| 已分发 | **0.869B** |
| CEX 充值 | **0** |

**分发链路追踪**:

```
8UHpWBnh (多签)
  └─ 7Qao1Sqh1mdKVKskFTuQe7ivy4f7Q3rrwzE4QrzMDJKV  (0.796B)
       └─ HaYTWK3nQuHuGrydBR4Gkc8tRzqDQ7swq8Fnf45DppQi  (奖励分发枢纽, 826 txs)
            └─ ~80+ 小钱包  (0.001–0.033B/个, Oct–Nov 2025)
  └─ 8S3BjPnAygsmbGnxpLUNympLoeEnRJhyqHkpuxY6aMdC  (0.073B + 增量)
       └─ 滚动月度微分发至多个钱包
```

> **结论**：确认为质押/生态奖励分发（非抛售）。分发模式与典型的链上质押奖励完全一致：从多签到中间钱包，再到枢纽合约，最终分散到 80+ 个终端用户地址。

---

### 2.6 ⚠ 联创人内部人员集群（Aug21 三件套）

> **重要发现**：原始分类为"外部 ICO 投资者"，现已重新分类为**内部人员/联创人持仓**。

三个钱包均于 **2025-08-21（TGE+40 天）** 从 Token Custodian 收到 PUMP，且**全部由同一资金方钱包** `3cBqg6k7g9kBH17hLQPwe4KWn89s3qoP5HN5jGng2p3i` 作为上游来源，社区研究将该地址关联至 Pump.fun 联创人 **@a1lon9（Alon）**。

| # | 地址 | 收到 (B) | 当前余额 | 状态 |
|---|---|---|---|---|
| 1 | `85WTujfJ9meJq5hfjAeb5gftj7n8Q7QTsZJbRqMD5ERS` | 30B | **30B** | 🔒 零流出 |
| 2 | `96HiV4cGWTJNCjGVff3RTHgPXmpYz7MSrGTAmxNKVWM9` | 23B | **23B** | 🔒 零流出 |
| 3 | `ERRGqu3dh6zYBg7MNAHKL33TyVb7efMmaKxnmdukdNYa` | 17B | **17B** | 🔒 零流出 |
| **合计** | | **70B** | **70B** | **当前完全锁定** |

**资金来源**:
`3cBqg6k7g9kBH17hLQPwe4KWn89s3qoP5HN5jGng2p3i`（集群 funder）
Attribution: **@a1lon9 (Alon, Pump.fun co-founder)** — 社区链上研究，置信度：中等

> **影响**：若归因属实，意味着联创人持有至少 **70B + Squads 金库份额**，实际内部人员持仓远超 Tokenomics 官方公布的 20% Team 分配。
> **注意**：该归因来自社区研究（X/Twitter），尚未经官方确认。需进一步链上取证。

---

### 2.7 Investor Wallet #1（9Ucygiam）

| 地址 | `9UcygiamY92yGntGkUkBKi4SdApxkBMZd9QSo6wMC2dN` |
|---|---|
| 初始收到 | 20.00B（2025-07-14） |
| Kraken 充值 | **11.2B → Kraken（2026-02-26，$21.2M）** |
| 当前余额 | **~8.8B** |
| 卖出率 | 56% |
| 状态 | ⚠ **已大规模 CEX 抛售** |

> 这是目前唯一已确认向 CEX 大规模转账的外部投资者钱包。

---

### 2.8 协议运营地址

| 地址 | 标签 | 收到 (B) | 当前余额 | 状态 |
|---|---|---|---|---|
| `8UhbNoBXmGoxJr2TeWW8wmSMoWmjS2rTT2tVJxzuTogC` | Community Reserve | 80B | **80B** | 🔒 未动 |
| `AvqFxKNrYZNvxsj2oWhLW8det68HzCXBqswshoD2TdT6` | Operational Vault (Token Hot SOL3) | 24B | **24B** | 🔒 未动 |
| `2WHL4XiNGKW9NgSwsJeG7WG2kD35Bi44rZoLrXHEz3dw` | Operational Wallet | 10B | **10B** | 🔒 未动 |

三个地址均只有 **2025-07-14 一笔流入**（来自 Token Custodian），此后零流出，完全符合协议储备定位。

---

### 2.9 ICO 分发合约（PDA）

| 地址 | `5D95TQGUmg71zrM7CJZiTYBVCPxrjCrrahEHegEPL2oj` |
|---|---|
| 账户类型 | PDA（Program Derived Address，isOnCurve=False） |
| 收到时间 | 2025-07-12（TGE 当天） |
| 初始收到 | **112.125B PUMP** |
| 当前余额 | **≈0**（~$51，可忽略） |
| 分发笔数 | ~2000 笔链上 ICO 交割 |

> ICO 公募所有代币均通过该 PDA 合约完成链上交割，完整性已确认。

---

### 2.10 独立鲸鱼（非关联地址）

#### Hyperunit: Hot Wallet

| 地址 | `9SLPTL41SPsYkgdsMzdfJsxymEANKr5bYoBsQzJyKpKS` |
|---|---|
| Solscan 标签 | "Hyperunit: Hot Wallet"（公开） |
| 当前余额 | 10.54B PUMP |
| 总流出 | 0.508B（卖出率 4.82%） |
| 流出方向 | Wintermute 0.231B + Gate.io 0.0002B + 其他钱包 |
| 特征 | 1000+ txs/3 天，持有 218 种代币 + 108M Fartcoin |
| 性质 | **DeFi 协议 / 做市商**，PUMP 为其库存持仓，非抛售目的 |

#### Coinbase-Connected Whale

| 地址 | `4GZwzZgqSwwTTRVgBoxTDeH3EwDye84dCPb9fALAZFjF` |
|---|---|
| 资金来源 | Coinbase Hot Wallet 4（多笔转入，Jan 2026） |
| 当前余额 | 7.189B PUMP |
| 流出 | **0**（零流出） |
| 性质 | Coinbase 机构托管账户或 OTC 买入的大户，纯持有 |

---

## 三、链上已确认事件时间线

```
2025-07-10   Token Custodian 接收全量 1000B PUMP
2025-07-12   TGE。ICO PDA 收到 112.125B，启动 ~2000 笔 ICO 交割
2025-07-14   批量分配日：Squads 5 大金库 + 团队钱包 + 投资者 + 社区储备
2025-07-16   回购钱包首次买入（TGE+4 天）
2025-08-21   联创人集群（Aug21 trio）收到 70B PUMP（TGE+40 天）
2025-09-07   ⚠ Vault #5 首次向 Bitget 出售：4.6875B（TGE+57 天）
2025-10-06   ⚠ Vault #4 向 OKX 出售：3.125B（TGE+86 天）
2025-10-~11  Official Multisig #2 开始分发质押奖励至 80+ 小钱包
2026-02-16   团队钱包 77DsB9kw 开始分发 3.75B（向 Wintermute 等，非直接 CEX）
2026-02-26   ⚠ Investor #1 向 Kraken 充值 11.2B（$21.2M）
2026-03-06   ⚠ Vault #5 Bitget 第二批（tranche 1/4）：1.758B
2026-03-10   ⚠ Vault #5 Bitget 第二批（tranche 2/4）：2.461B
2026-03-13   ⚠ Vault #5 Bitget 第二批（tranche 3/4）：1.500B
2026-03-16   ⚠ Vault #5 Bitget 第二批（tranche 4/4）：1.453B
```

---

## 四、Squads V4 执行模式说明

本次分析发现 V4、V5 的所有 CEX 出售均采用相同路由模式：

```
Squads Vault（多签）
  → 临时过路钱包（SystemProgram owner，同日新建，余额仅 ~0.007 SOL）
    → CEX 热钱包（A77HErqtfN1h... = Bitget，C68a6RCG... = OKX 等）
```

特征：
- 过路钱包从不在链上保留余额
- 与主 Squads TX 在同一天或次日完成
- 采用多跳路由，增加链上追踪难度
- Bitget Solscan 公开标注地址已确认接收

---

## 五、风险评估

### 当前存量卖压

| 来源 | 剩余量 | 已出售 | 风险等级 |
|---|---|---|---|
| Vault #5 → Bitget | 6.891B | 11.859B | 🔴 持续出售中 |
| Vault #4 → OKX | 15.625B | 3.125B | 🟡 已出售 3.125B，仍有大量存量 |
| Investor #1 → Kraken | 8.8B | 11.2B | 🟡 已大量出售，剩余减少 |
| 联创人集群（Aug21） | 70B | 0 | 🟡 当前零流出，但 2026-07-12 后解锁 |
| Vaults #1-#3 | 85B | 0 | 🟢 完全锁定，Cliff 前无风险 |

### 最大尾部风险：2026-07-12 Cliff 解锁

- **规模**：根据 Tokenomics，2026-07-12 为 Team（200B）+ Investor（130B）的 12 个月 Cliff，届时解锁 **首批各 25%**
- **链上映射**：Squads Vault #1-#5（107.52B）+ 联创人集群（70B）+ Custodian 内剩余 Team/Investor 份额
- **Vault #4/#5 已提前出售的意义**：在 Cliff 前就开始向 CEX 分批出货，说明内部人员并不等待正式解锁，管理成本极低
- **预计解锁量**：约 82-85B PUMP（Team 25%+Investor 25%），约占当前流通量 13%

---

## 六、CEX 链上持仓（截至 2026-03-19）

| 交易所 | 链上持仓 (B) | 排名 |
|---|---|---|
| Binance | 30.14 | #1 |
| Bybit | 13.26 | #2 |
| OKX | 7.87 | #3 |
| **合计** | **51.27** | |

---

## 七、关键结论

1. **官方流通量被高估**：634B 流通量中，实际可交易的自由流通约 220B（22%），其余均静止于金库、锁仓或协议储备。

2. **V4/V5 提前出售是重要信号**：两个 Squads 金库已在 Cliff 前合计出售约 15B PUMP。出售时间（Sep 2025, Oct 2025, Mar 2026）均早于 2026-07-12 正式解锁日，行为模式为分批、多跳路由至 CEX，具有明显的规避痕迹。

3. **联创人持仓集中度超预期**：若 @a1lon9 归因成立，仅已识别的内部人员地址就超过 **177B PUMP**（70B Aug21 + 107B Vaults，若 Vaults 完全为团队所有）。

4. **回购力度实质性**：回购金库 103.96B、单价远低于当前市价的历史买入，对冲了部分卖压。但近期 Vault #5 持续向 Bitget 分批出货，抵消了部分回购效果。

5. **Investor #1 是目前唯一大规模 CEX 抛售的外部投资者**：11.2B PUMP 流入 Kraken 后的价格走势值得持续关注。

---

## 八、已确认地址清单

| 地址（前 10 字符） | 标签 | 类型 | 余额 (B) | 已流出 (B) |
|---|---|---|---|---|
| `Cfq1ts1iFr` | Token Custodian | token_custodian | 365.46 | 634.54 |
| `G8CcfRffqZ` | Buyback Treasury | treasury | 103.96 | — |
| `3vkpy5YHqn` | Buyback Wallet | buyback | ~62 | — |
| `8UhbNoBXmG` | Community Reserve | treasury | 80.00 | 0 |
| `AvqFxKNrYZ` | Operational Vault | treasury | 24.00 | 0 |
| `2WHL4XiNGK` | Operational Wallet | treasury | 10.00 | 0 |
| `9pkFKCR1md` | Squads Vault #1 | vesting | 35.00 | 0 |
| `BBvQteuawK` | Squads Vault #2 | vesting | 25.00 | 0 |
| `GTeSSwovPi` | Squads Vault #3 | vesting | 25.00 | 0 |
| `GhFaBi8sy3` | Squads Vault #4 ⚠ | vesting | 15.63 | **3.125 → OKX** |
| `5v7ZZg1D1s` | Squads Vault #5 ⚠⚠ | vesting | 6.891 | **11.859 → Bitget** |
| `77DsB9kw8u` | Team Wallet #1 | team | 0 | 3.75 → Wintermute/DEX |
| `8UHpWBnhYN` | Official Multisig #2 | official_allocation | 19.13 | 0.869 → Staking rewards |
| `9UcygiamaY` | Investor Wallet #1 ⚠ | investor | 8.8 | **11.2 → Kraken** |
| `85WTujfJ9m` | Insider Cluster #1 (@a1lon9) | insider | 30.00 | 0 |
| `96HiV4cGWT` | Insider Cluster #2 (@a1lon9) | insider | 23.00 | 0 |
| `ERRGqu3dh6` | Insider Cluster #3 (@a1lon9) | insider | 17.00 | 0 |
| `5D95TQGUmg` | ICO Distribution PDA | ico_distribution | 0 | 112.13 → ICO buyers |
| `9SLPTL41SP` | Hyperunit (Market Maker) | whale | 10.54 | 0.508 |
| `4GZwzZgqSw` | Coinbase-Connected Whale | whale | 7.189 | 0 |

---

*报告数据来源：Helius RPC Enhanced API、BubbleMaps、Solscan、CryptoRank、Lookonchain、Onchain Lens、社区研究（X/Twitter）*
*链上验证日期：2026-03-19*
*置信度说明：地址余额与流出记录为链上直接查询（高可信度）；@a1lon9 归因为社区研究（中等可信度，待官方确认）*
