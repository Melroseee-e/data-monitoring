# PRL Solana Top 10 筹码结构报告

- 生成时间: 2026-03-31T06:23:21Z
- 研究对象: `PERLEQKUNUp1dgFZ8EvyXHdN9d6ZQqfGxALDvfs6pDs`
- 官方主链口径: Solana，Total Supply = 1B，TGE = 2026-03-25
- 官方资料: [Token Overview](https://perle.gitbook.io/perle-docs/tokenomics/token-overview) / [Token Vesting](https://perle.gitbook.io/perle-docs/tokenomics/token-vesting) / [Token Utility](https://perle.gitbook.io/perle-docs/tokenomics/prl-token-utility-and-purpose) / [Audit](https://perle.gitbook.io/perle-docs/perle-prl-token-passes-security-audit-with-halborn) / [Funding](https://www.perle.ai/resources/perle-secures-9-million-seed-round-led-by-framework-ventures-to-launch-an-ai-data-training-platform-powered-by-web3)

## 一眼结论

- Top 10 当前合计持有 **97.68%**，而且这一层现在更像**官方配额与分发地图本身**，不是交易所 / DEX / 民间鲸鱼混合层。
- `6pJjJFA69U4YFvwu1wajkLBrP4BoP2ULncBBjKwidLRG` 不只是公开 metadata authority；链上还直接从它向四个主配额方向打出约 **1B PRL**，因此它现在应视为**官方一级分发总控**。
- 最强匹配关系是：`Community -> #1`、`Investors -> #2`、`Ecosystem -> #3`、`Team -> #10 + #4/#6/#8`。
- Top 10 里当前**没有交易所，也没有 DEX 池子**；第一个交易所地址要到第 `12` 名。

## Tokenomics 快照

- TGE 理论已解锁: **175,000,000 PRL**
- TGE 后理论仍锁定 / 待释放: **825,000,000 PRL**

| Bucket | Allocation | Amount | TGE Unlock | Locked After TGE | Vesting | 当前链上候选 |
| --- | --- | --- | --- | --- | --- | --- |
| Community | 37.50% | 375,000,000 | 75,000,000 | 300,000,000 | 36 months | Community 主仓 Gvpm8t...vE4B |
| Investors | 27.66% | 276,600,000 | 0 | 276,600,000 | 36 months | Investors 主锁仓 ELoD6e...XLoS |
| Ecosystem | 17.84% | 178,400,000 | 100,000,000 | 78,400,000 | 48 months | Ecosystem 主仓 Bv3u7G...jZHH / Ecosystem 释放 Vault HfXxnd...4fdh |
| Team | 17.00% | 170,000,000 | 0 | 170,000,000 | 36 months | Team 二级分发中枢 HhU4r2...7X5M / Team 静态分仓 8G68Pu...cbCe / Team 静态分仓 14bc3R...B6GF / Team 静态分仓 Bu9sDT...2SQT |

## 官方分发路径

| 上游 | 下游 | 金额 | Tokenomics Bucket | 推断角色 |
| --- | --- | --- | --- | --- |
| `6pJjJF...dLRG` | `Gvpm8t...vE4B` | 375,000,000.00 | Community | Community 主仓 |
| `6pJjJF...dLRG` | `ELoD6e...XLoS` | 276,619,098.00 | Investors | Investors 主锁仓 |
| `6pJjJF...dLRG` | `Bv3u7G...jZHH` | 178,380,902.00 | Ecosystem | Ecosystem 主仓 |
| `GLHvbT...TB8v` | `HhU4r2...7X5M` | 102,300,000.00 | Team | Team 二级分发中枢 |
| `HhU4r2...7X5M` | `8G68Pu...cbCe` | 92,650,000.00 | Team | Team 静态分仓 |
| `AewXva...Hcdu` | `HfXxnd...4fdh` | 90,000,000.00 | Ecosystem | Ecosystem 释放 Vault |
| `HhU4r2...7X5M` | `14bc3R...B6GF` | 40,000,000.00 | Team | Team 静态分仓 |
| `HhU4r2...7X5M` | `Bu9sDT...2SQT` | 20,000,000.00 | Team | Team 静态分仓 |

## Top 10 角色判断

| Rank | 地址 | 持仓 | 占总量 | 归类 | 配额桶 | 角色 | 释放状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | `Gvpm8t...vE4B` | 317,980,209.13 | 31.80% | 高概率官方 | Community | Community 主仓 | 中度分发 |
| 2 | `ELoD6e...XLoS` | 276,619,098.00 | 27.66% | 高概率官方 | Investors | Investors 主锁仓 | 未见释放 |
| 3 | `Bv3u7G...jZHH` | 94,080,066.00 | 9.41% | 高概率官方 | Ecosystem | Ecosystem 主仓 | 中度分发 |
| 4 | `8G68Pu...cbCe` | 92,650,000.00 | 9.27% | 高概率官方 | Team | Team 静态分仓 | 未见释放 |
| 5 | `HfXxnd...4fdh` | 83,386,620.03 | 8.34% | 高概率官方 | Ecosystem | Ecosystem 释放 Vault | 活跃释放 |
| 6 | `14bc3R...B6GF` | 40,000,000.00 | 4.00% | 高概率官方 | Team | Team 静态分仓 | 未见释放 |
| 7 | `6pJjJF...dLRG` | 22,397,372.98 | 2.24% | 已公开官方 | Master Distributor | 官方一级分发总控 | 中度分发 |
| 8 | `Bu9sDT...2SQT` | 20,000,000.00 | 2.00% | 高概率官方 | Team | Team 静态分仓 | 未见释放 |
| 9 | `5MnWHh...HcQx` | 20,000,000.00 | 2.00% | 高概率官方 | Operations | 官方运营 / ServiceCo Vault | 未见释放 |
| 10 | `HhU4r2...7X5M` | 9,650,000.00 | 0.97% | 高概率官方 | Team | Team 二级分发中枢 | 中度分发 |

## 官方地址与推断地址

### 已公开官方

- `6pJjJFA69U4YFvwu1wajkLBrP4BoP2ULncBBjKwidLRG`: [Audit](https://perle.gitbook.io/perle-docs/perle-prl-token-passes-security-audit-with-halborn) 直接公开为 metadata update authority；链上又实际承担 1B PRL 的一级分发总控。
- `PERLEQKUNUp1dgFZ8EvyXHdN9d6ZQqfGxALDvfs6pDs`: [Token Overview](https://perle.gitbook.io/perle-docs/tokenomics/token-overview) 直接公开为 PRL 的 Solana mint。

### 高概率官方 / 高概率配额钱包

| Rank | 地址 | 层级 | 配额桶 | 占总量 | 理由 |
| --- | --- | --- | --- | --- | --- |
| 1 | `Gvpm8tjTDofEp86Yeb8vLnPSamPssHtBYSuaRqLgvE4B` | 高概率官方 | Community | 31.798% | 从公开官方总控地址单点收到 375M PRL，与 docs 的 Community 配额完全对齐；当前已净分发约 57.02M，剩余约 317.98M。 |
| 2 | `ELoD6eKDQAffL63TMQv1VhARj3w5GPgHsvQPE3PYXLoS` | 高概率官方 | Investors | 27.662% | 从公开官方总控地址直接收到 276.619098M PRL，和 docs 的 Investors 27.66% 几乎一一对应，当前未见继续释放。 |
| 3 | `Bv3u7GRzziLxvojGvDC9Vt1rRwgquLf7KpwobxHEjZHH` | 高概率官方 | Ecosystem | 9.408% | 从公开官方总控地址直接收到 178.380902M PRL，和 docs 的 Ecosystem 17.84% 几乎完全对齐，目前已向外分发约 87.30M。 |
| 4 | `8G68Pu5fy5DmFAZT4wxZ4TBr3oVnemUrwMAYmTitcbCe` | 高概率官方 | Team | 9.265% | 仅从 HhU4r2...7X5M 单跳收到 92,650,000.00 PRL，之后未继续释放，形态符合 Team 分仓停放地址。 |
| 5 | `HfXxndwJekWeExQyPgE32dCLLh2QbVrcU3AtE2bL4fdh` | 高概率官方 | Ecosystem | 8.339% | 程序控制账户，且对外分发活跃，形态更像官方释放 / 再分发 vault，而不是自然大户钱包。 |
| 6 | `14bc3Rse5cVtsnha7iaDPkSaQ62nJiXqaAJ5asDuB6GF` | 高概率官方 | Team | 4.000% | 仅从 HhU4r2...7X5M 单跳收到 40,000,000.00 PRL，之后未继续释放，形态符合 Team 分仓停放地址。 |
| 7 | `6pJjJFA69U4YFvwu1wajkLBrP4BoP2ULncBBjKwidLRG` | 已公开官方 | Master Distributor | 2.240% | Audit 公开的 metadata authority 地址，链上又直接向 Community / Investors / Ecosystem / Team 主分配地址累计打出约 10 亿 PRL。 |
| 8 | `Bu9sDTKTyqS3RF6udyzgHQdxB562yZKhkBxQYqHd2SQT` | 高概率官方 | Team | 2.000% | 仅从 HhU4r2...7X5M 单跳收到 20,000,000.00 PRL，之后未继续释放，形态符合 Team 分仓停放地址。 |
| 9 | `5MnWHhe5Bbuq8X6kwU3PCEfBFqJvb2uequxMtnRBHcQx` | 高概率官方 | Operations | 2.000% | Arkham 直接标注为 Squads Vault / ServiceCo，属于官方运营侧地址而不是市场大户。 |
| 10 | `HhU4r2WHMV4anKFzMHt4yaEaYxw6Ffgn81T1wnUX7X5M` | 高概率官方 | Team | 0.965% | 累计收到 170M PRL，随后拆分到多个静态分仓地址，和 Team 17% 配额完全对齐。 |

## Top 10 逐地址推断

### #1 `Gvpm8tjTDofEp86Yeb8vLnPSamPssHtBYSuaRqLgvE4B`

- 当前角色判断: **Community 主仓**
- 当前持仓: **317,980,209.13 PRL** (31.798%)
- Tokenomics 对位: **Community**
- 释放状态: **中度分发**
- 推断理由: 从公开官方总控地址单点收到 375M PRL，与 docs 的 Community 配额完全对齐；当前已净分发约 57.02M，剩余约 317.98M。
- 主入账: 6pJjJF...dLRG / 375,000,000.00 PRL
- 主出账: w1GJxV...Z6aG / 30,000,000.00 PRL
- 证据摘要: 研究判断：Community 主仓候选。 从公开官方总控地址单点收到 375M PRL，与 docs 的 Community 配额完全对齐；当前已净分发约 57.02M，剩余约 317.98M。 链上形态是普通 system wallet。 主入账来源 6pJjJF...dLRG，累计 375,000,000.00 PRL。 主出账去向 w1GJxV...Z6aG，累计 30,000,000.00 PRL。 释放状态判断：中度分发。 BubbleMaps relation 度数 37，in/out = 26/11。

### #2 `ELoD6eKDQAffL63TMQv1VhARj3w5GPgHsvQPE3PYXLoS`

- 当前角色判断: **Investors 主锁仓**
- 当前持仓: **276,619,098.00 PRL** (27.662%)
- Tokenomics 对位: **Investors**
- 释放状态: **未见释放**
- 推断理由: 从公开官方总控地址直接收到 276.619098M PRL，和 docs 的 Investors 27.66% 几乎一一对应，当前未见继续释放。
- 主入账: 6pJjJF...dLRG / 276,619,098.00 PRL
- 主出账: —
- 证据摘要: 研究判断：Investors 主锁仓候选。 从公开官方总控地址直接收到 276.619098M PRL，和 docs 的 Investors 27.66% 几乎一一对应，当前未见继续释放。 链上形态是普通 system wallet。 主入账来源 6pJjJF...dLRG，累计 276,619,098.00 PRL。 释放状态判断：未见释放。 BubbleMaps relation 度数 24，in/out = 18/6。

### #3 `Bv3u7GRzziLxvojGvDC9Vt1rRwgquLf7KpwobxHEjZHH`

- 当前角色判断: **Ecosystem 主仓**
- 当前持仓: **94,080,066.00 PRL** (9.408%)
- Tokenomics 对位: **Ecosystem**
- 释放状态: **中度分发**
- 推断理由: 从公开官方总控地址直接收到 178.380902M PRL，和 docs 的 Ecosystem 17.84% 几乎完全对齐，目前已向外分发约 87.30M。
- 主入账: 6pJjJF...dLRG / 178,380,902.00 PRL
- 主出账: w1GJxV...Z6aG / 80,000,000.00 PRL
- 证据摘要: 研究判断：Ecosystem 主仓候选。 从公开官方总控地址直接收到 178.380902M PRL，和 docs 的 Ecosystem 17.84% 几乎完全对齐，目前已向外分发约 87.30M。 链上形态是普通 system wallet。 主入账来源 6pJjJF...dLRG，累计 178,380,902.00 PRL。 主出账去向 w1GJxV...Z6aG，累计 80,000,000.00 PRL。 释放状态判断：中度分发。 BubbleMaps relation 度数 75，in/out = 59/16。

### #4 `8G68Pu5fy5DmFAZT4wxZ4TBr3oVnemUrwMAYmTitcbCe`

- 当前角色判断: **Team 静态分仓**
- 当前持仓: **92,650,000.00 PRL** (9.265%)
- Tokenomics 对位: **Team**
- 释放状态: **未见释放**
- 推断理由: 仅从 HhU4r2...7X5M 单跳收到 92,650,000.00 PRL，之后未继续释放，形态符合 Team 分仓停放地址。
- 主入账: HhU4r2...7X5M / 92,650,000.00 PRL
- 主出账: —
- 证据摘要: 研究判断：Team 静态分仓。 仅从 HhU4r2...7X5M 单跳收到 92,650,000.00 PRL，之后未继续释放，形态符合 Team 分仓停放地址。 public_rpc_not_available 主入账来源 HhU4r2...7X5M，累计 92,650,000.00 PRL。 释放状态判断：未见释放。 BubbleMaps relation 度数 1，in/out = 1/0。

### #5 `HfXxndwJekWeExQyPgE32dCLLh2QbVrcU3AtE2bL4fdh`

- 当前角色判断: **Ecosystem 释放 Vault**
- 当前持仓: **83,386,620.03 PRL** (8.339%)
- Tokenomics 对位: **Ecosystem**
- 释放状态: **活跃释放**
- 推断理由: 程序控制账户，且对外分发活跃，形态更像官方释放 / 再分发 vault，而不是自然大户钱包。
- 主入账: AewXva...Hcdu / 90,000,000.00 PRL
- 主出账: Ee7qK1...unM5 / 2,237,232.85 PRL
- 证据摘要: 研究判断：Ecosystem 释放 Vault。 程序控制账户，且对外分发活跃，形态更像官方释放 / 再分发 vault，而不是自然大户钱包。 账户 owner 为 76fxTpnrukUr6i36wK8K4UJsABtAaPJxP9nZytQKTaPU，不是普通 system wallet，偏向程序控制或 vault 型账户。 主入账来源 AewXva...Hcdu，累计 90,000,000.00 PRL。 主出账去向 Ee7qK1...unM5，累计 2,237,232.85 PRL。 释放状态判断：活跃释放。 BubbleMaps relation 度数 857，in/out = 149/708。

### #6 `14bc3Rse5cVtsnha7iaDPkSaQ62nJiXqaAJ5asDuB6GF`

- 当前角色判断: **Team 静态分仓**
- 当前持仓: **40,000,000.00 PRL** (4.000%)
- Tokenomics 对位: **Team**
- 释放状态: **未见释放**
- 推断理由: 仅从 HhU4r2...7X5M 单跳收到 40,000,000.00 PRL，之后未继续释放，形态符合 Team 分仓停放地址。
- 主入账: HhU4r2...7X5M / 40,000,000.00 PRL
- 主出账: —
- 证据摘要: 研究判断：Team 静态分仓。 仅从 HhU4r2...7X5M 单跳收到 40,000,000.00 PRL，之后未继续释放，形态符合 Team 分仓停放地址。 public_rpc_not_available 主入账来源 HhU4r2...7X5M，累计 40,000,000.00 PRL。 释放状态判断：未见释放。 BubbleMaps relation 度数 1，in/out = 1/0。

### #7 `6pJjJFA69U4YFvwu1wajkLBrP4BoP2ULncBBjKwidLRG`

- 当前角色判断: **官方一级分发总控**
- 当前持仓: **22,397,372.98 PRL** (2.240%)
- Tokenomics 对位: **Master Distributor**
- 释放状态: **中度分发**
- 推断理由: Audit 公开的 metadata authority 地址，链上又直接向 Community / Investors / Ecosystem / Team 主分配地址累计打出约 10 亿 PRL。
- 主入账: Gvpm8t...vE4B / 25,000,000.00 PRL
- 主出账: Gvpm8t...vE4B / 375,000,000.00 PRL
- 证据摘要: 研究判断：官方一级分发总控。 Audit 公开的 metadata authority 地址，链上又直接向 Community / Investors / Ecosystem / Team 主分配地址累计打出约 10 亿 PRL。 现有标签：Squads Vault "Lumen Foundation"。 链上形态是普通 system wallet。 主入账来源 Gvpm8t...vE4B，累计 25,000,000.00 PRL。 主出账去向 Gvpm8t...vE4B，累计 375,000,000.00 PRL。 释放状态判断：中度分发。 BubbleMaps relation 度数 8987，in/out = 6/8981。

### #8 `Bu9sDTKTyqS3RF6udyzgHQdxB562yZKhkBxQYqHd2SQT`

- 当前角色判断: **Team 静态分仓**
- 当前持仓: **20,000,000.00 PRL** (2.000%)
- Tokenomics 对位: **Team**
- 释放状态: **未见释放**
- 推断理由: 仅从 HhU4r2...7X5M 单跳收到 20,000,000.00 PRL，之后未继续释放，形态符合 Team 分仓停放地址。
- 主入账: HhU4r2...7X5M / 20,000,000.00 PRL
- 主出账: —
- 证据摘要: 研究判断：Team 静态分仓。 仅从 HhU4r2...7X5M 单跳收到 20,000,000.00 PRL，之后未继续释放，形态符合 Team 分仓停放地址。 public_rpc_not_available 主入账来源 HhU4r2...7X5M，累计 20,000,000.00 PRL。 释放状态判断：未见释放。 BubbleMaps relation 度数 1，in/out = 1/0。

### #9 `5MnWHhe5Bbuq8X6kwU3PCEfBFqJvb2uequxMtnRBHcQx`

- 当前角色判断: **官方运营 / ServiceCo Vault**
- 当前持仓: **20,000,000.00 PRL** (2.000%)
- Tokenomics 对位: **Operations**
- 释放状态: **未见释放**
- 推断理由: Arkham 直接标注为 Squads Vault / ServiceCo，属于官方运营侧地址而不是市场大户。
- 主入账: w1GJxV...Z6aG / 1.00 PRL
- 主出账: —
- 证据摘要: 研究判断：官方运营 / ServiceCo Vault。 Arkham 直接标注为 Squads Vault / ServiceCo，属于官方运营侧地址而不是市场大户。 现有标签：Squads Vault "SGL Marketing Lumen ServiceCo"。 链上形态是普通 system wallet。 主入账来源 w1GJxV...Z6aG，累计 1.00 PRL。 释放状态判断：未见释放。 BubbleMaps relation 度数 5，in/out = 4/1。

### #10 `HhU4r2WHMV4anKFzMHt4yaEaYxw6Ffgn81T1wnUX7X5M`

- 当前角色判断: **Team 二级分发中枢**
- 当前持仓: **9,650,000.00 PRL** (0.965%)
- Tokenomics 对位: **Team**
- 释放状态: **中度分发**
- 推断理由: 累计收到 170M PRL，随后拆分到多个静态分仓地址，和 Team 17% 配额完全对齐。
- 主入账: GLHvbT...TB8v / 102,300,000.00 PRL
- 主出账: 8G68Pu...cbCe / 92,650,000.00 PRL
- 证据摘要: 研究判断：Team 二级分发中枢。 累计收到 170M PRL，随后拆分到多个静态分仓地址，和 Team 17% 配额完全对齐。 链上形态是普通 system wallet。 主入账来源 GLHvbT...TB8v，累计 102,300,000.00 PRL。 主出账去向 8G68Pu...cbCe，累计 92,650,000.00 PRL。 释放状态判断：中度分发。 BubbleMaps relation 度数 23，in/out = 18/5。

## 交易所 / DEX / 大户观察

- 第一个交易所地址只到第 `12` 名，当前 BubbleMaps / Arkham 识别到的交易所下限仓位约 **1.245%**。
- DEX / LP 不在 Top 10，BubbleMaps Top 500 中的 DEX 下限仓位约 **0.006%**。
- 结合 Helius 流水，本轮最重要的更新是：Top 10 已经不该再被默认视作“未标注鲸鱼层”，而应主要视作官方 allocation / treasury / release / shard 层。

## Label Inventory（前 20）

| 来源 | 标签 | 地址数 | 占总量 |
| --- | --- | --- | --- |
| Arkham | Squads Vault "Lumen Foundation" | 1 | 2.240% |
| Arkham | Squads Vault "SGL Marketing Lumen ServiceCo" | 1 | 2.000% |
| Arkham | Hot Wallet | 8 | 1.165% |
| BubbleMaps | Bitget Exchange (A77H...4RiR) | 1 | 0.595% |
| Arkham Entity | Bitget | 1 | 0.595% |
| BubbleMaps | Coinbase Hot Wallet (4NyK...LeFw) | 1 | 0.232% |
| Arkham Entity | Coinbase | 1 | 0.232% |
| BubbleMaps | Gate.io (u6PJ...Xq2w) | 1 | 0.162% |
| Arkham Entity | Gate | 1 | 0.162% |
| BubbleMaps | MEXC (ASTy...iaJZ) | 1 | 0.137% |
| Arkham Entity | MEXC | 1 | 0.137% |
| Arkham | Fireblocks Custody | 2 | 0.054% |
| BubbleMaps | GSR Markets Fireblocks Custody | 1 | 0.049% |
| Arkham Entity | GSR Markets | 1 | 0.049% |
| Arkham | Gate Deposit | 9 | 0.041% |
| BubbleMaps | Gate Deposit | 5 | 0.036% |
| BubbleMaps | Kucoin (BmFd...ymy6) | 1 | 0.033% |
| Arkham Entity | KuCoin | 1 | 0.033% |
| Arkham | Coinbase Prime Custody | 1 | 0.032% |
| BubbleMaps | Raydium Pool | 1 | 0.005% |

## 数据说明

- 当前持仓快照来自 BubbleMaps Top 500。
- 地址实体标签以 Arkham 为主补充，BubbleMaps 负责 CEX / DEX / contract 标记。
- Top 10 的 PRL 交易流水额外来自 Helius Enhanced API，并已单独落盘到 `data/prl/raw/top10_helius_history/`。
- 这版报告最大的变化是把“金额是否对上 docs 配额”和“主入账 / 主出账路径”并入推断逻辑，而不是只看 BubbleMaps 标签。
