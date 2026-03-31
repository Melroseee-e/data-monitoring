# PRL Solana Top 10 筹码结构报告

- 生成时间: 2026-03-31T04:10:33Z
- 研究对象: `PERLEQKUNUp1dgFZ8EvyXHdN9d6ZQqfGxALDvfs6pDs`
- 官方主链口径: Solana，Total Supply = 1B，TGE = 2026-03-25
- 官方资料: [Token Overview](https://perle.gitbook.io/perle-docs/tokenomics/token-overview) / [Token Vesting](https://perle.gitbook.io/perle-docs/tokenomics/token-vesting) / [Token Utility](https://perle.gitbook.io/perle-docs/tokenomics/prl-token-utility-and-purpose) / [Audit](https://perle.gitbook.io/perle-docs/perle-prl-token-passes-security-audit-with-halborn) / [Funding](https://www.perle.ai/resources/perle-secures-9-million-seed-round-led-by-framework-ventures-to-launch-an-ai-data-training-platform-powered-by-web3)

## 一眼结论

- Top 10 当前合计持有 **97.68%**，Top 5 就占 **86.47%**。
- Top 10 里**没有交易所，也没有 DEX 池子**；第一个交易所地址要到第 `12` 名。
- 当前能直接公开确认的官方地址只有 `metadata update authority`：`6pJjJFA69U4YFvwu1wajkLBrP4BoP2ULncBBjKwidLRG`，它本身就是第 7 大持仓。
- Top 10 里有两类需要分开看：一类是 `已公开官方` / `高概率官方`，另一类是没有公开标签的大仓钱包。

## Top 10 分层

| Rank | 地址 | 持仓 | 占总量 | 归类 | 角色 | 标签 |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `Gvpm8t...vE4B` | 317,980,209.13 | 31.80% | 大户 | 未标注大户 | — |
| 2 | `ELoD6e...XLoS` | 276,619,098.00 | 27.66% | 大户 | 未标注大户 | — |
| 3 | `Bv3u7G...jZHH` | 94,080,066.00 | 9.41% | 大户 | 未标注大户 | — |
| 4 | `8G68Pu...cbCe` | 92,650,000.00 | 9.27% | 大户 | 单跳静态大仓 | — |
| 5 | `HfXxnd...4fdh` | 83,386,620.03 | 8.34% | 高概率官方 | 疑似官方基础设施/托管 vault | — |
| 6 | `14bc3R...B6GF` | 40,000,000.00 | 4.00% | 大户 | 单跳静态大仓 | — |
| 7 | `6pJjJF...dLRG` | 22,397,372.98 | 2.24% | 已公开官方 | 公开 metadata authority 钱包 | Squads Vault "Lumen Foundation" |
| 8 | `Bu9sDT...2SQT` | 20,000,000.00 | 2.00% | 大户 | 单跳静态大仓 | — |
| 9 | `5MnWHh...HcQx` | 20,000,000.00 | 2.00% | 高概率官方 | 疑似 Squads 官方运营/服务 vault | Squads Vault "SGL Marketing Lumen ServiceCo" |
| 10 | `HhU4r2...7X5M` | 9,650,000.00 | 0.97% | 大户 | 未标注大户 | — |

## Top 10 结构判断

- 大户: 7 个地址，合计 85.098%
- 高概率官方: 2 个地址，合计 10.339%
- 已公开官方: 1 个地址，合计 2.240%

## 哪些是官方

### 已公开官方

- `6pJjJFA69U4YFvwu1wajkLBrP4BoP2ULncBBjKwidLRG`: [Audit](https://perle.gitbook.io/perle-docs/perle-prl-token-passes-security-audit-with-halborn) 直接公开为 metadata update authority，同时它现在是第 7 大持仓地址，持有 2.240%。
- `PERLEQKUNUp1dgFZ8EvyXHdN9d6ZQqfGxALDvfs6pDs`: [Token Overview](https://perle.gitbook.io/perle-docs/tokenomics/token-overview) 直接公开为 PRL 的 Solana mint。

### 高概率官方

| Rank | 地址 | 层级 | 占总量 | 证据 |
| --- | --- | --- | --- | --- |
| 5 | `HfXxndwJekWeExQyPgE32dCLLh2QbVrcU3AtE2bL4fdh` | 高概率官方 | 8.339% | Top 10 中的程序控制账户，更像官方 vault / 托管层而非自然大户。 |
| 9 | `5MnWHhe5Bbuq8X6kwU3PCEfBFqJvb2uequxMtnRBHcQx` | 高概率官方 | 2.000% | Arkham 直接打到 Squads Vault，且处于 Top 10。 |

## 哪些是大户

- 第 1、2 名两只无标签钱包就合计持有超过 59%，是当前筹码结构的绝对主导层。
- 第 4、6、8、11 名都接近“单跳静态大仓”，BubbleMaps 度数基本为 1，更像分配后停放的钱包，不像交易所或 AMM 基础设施。
- 这意味着 PRL 当前最需要盯的不是交易所流出，而是这些大仓钱包是否开始互转、拆分或向交易所沉淀。

## 哪些是交易所 / DEX 池子

- 交易所最早从第 `12` 名开始出现，当前 BubbleMaps / Arkham 明确识别到的交易所下限持仓约为 **1.245%**。
- 当前 DEX / 流动性池不在 Top 10，且在 BubbleMaps Top 500 中占比也很低，下限约为 **0.006%**。
- 这说明当前 top of cap 基本不是由交易所库存或池子占据，而是由项目侧/大户侧钱包占据。

## Tokenomics 对照

- Docs 把 PRL 定义为 Solana 原生发行，不是多链并表口径。
- Team: 17.00%，0% TGE，12 个月 cliff，36 个月线性释放。
- Investors: 27.66%，0% TGE，12 个月 cliff，36 个月线性释放。
- Ecosystem: 17.84%，TGE 解锁 10% of total supply，其余 48 个月释放。
- Community: 37.50%，TGE 解锁 7.5% of total supply，其余 36 个月释放。
- 结合当前 Top 10，可见市场最集中的并不是交易所，而是更像“项目侧托管 + 大额静态分仓”的结构，这与 TGE 初期的大额分仓持有是相容的。

## Fresh Wallet 簇

| Rank | 地址 | 占总量 | 首次活动 |
| --- | --- | --- | --- |
| 4 | `8G68Pu...cbCe` | 9.265% | 2026-03-10T00:10:57 |
| 6 | `14bc3R...B6GF` | 4.000% | 2026-03-10T00:11:34 |
| 8 | `Bu9sDT...2SQT` | 2.000% | 2026-03-18T22:00:14 |
| 11 | `5TSnK6...zcmN` | 0.650% | 2026-03-10T00:12:08 |
| 16 | `HeM1Uu...JHeC` | 0.120% | 2026-03-10T00:12:39 |

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
- Solscan API key 当前无权限读取付费接口，因此本报告不把 Solscan 当作结构化标签源。
- 由于 Helius key 当前限额，本报告不做全历史大额流水重建，重点是 Top 10 分层与官方识别。
