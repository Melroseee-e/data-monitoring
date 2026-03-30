# Perle (PRL) 筹码结构研究

- 合约: `0xd20fB09A49a8e75Fef536A2dBc68222900287BAc`
- 链: BSC
- 总供应量: 84,315,132.1586 PRL
- 生成时间: 2026-03-30 08:13 UTC
- BubbleMaps 快照: Top 500 holders
- 已知本地交易所地址数: 40

## 1. 当前筹码结构

- Top10 / Top20 / Top50 持仓占比分别为 97.73% / 98.84% / 99.28%。
- BubbleMaps 显式标签覆盖 14 个地址，合计 11.29% 的总供应。
- BubbleMaps 显式 CEX 仅识别到 1 个地址，当前合计 8.70% 的总供应。这一数值按下限理解。

| Segment | Addr Count | Amount | Supply Share |
| --- | --- | --- | --- |
| unlabeled_whale | 7 | 73,150,614.2551 | 86.76% |
| cex | 1 | 7,331,819.1749 | 8.70% |
| dex | 5 | 1,342,791.3200 | 1.59% |
| labeled | 8 | 848,114.2739 | 1.01% |
| tail_wallet | 467 | 751,442.1224 | 0.89% |
| mid_wallet | 3 | 566,406.4342 | 0.67% |
| contract | 9 | 64,213.3794 | 0.08% |

### Top 20 持仓快照

| Rank | Address | BubbleMaps Label | Segment | Amount | Share |
| --- | --- | --- | --- | --- | --- |
| 1 | 0x0350...adc0 | - | unlabeled_whale | 43,160,000.0000 | 51.19% |
| 2 | 0xc3c7...22d7 | - | unlabeled_whale | 10,000,000.0000 | 11.86% |
| 3 | 0x73d8...46db | Binance Wallet Proxy (EIP-1967 Transparent) | cex | 7,331,819.1749 | 8.70% |
| 4 | 0x5861...e257 | - | unlabeled_whale | 5,000,000.0000 | 5.93% |
| 5 | 0x5a4c...4f50 | - | unlabeled_whale | 5,000,000.0000 | 5.93% |
| 6 | 0xccf4...5b55 | - | unlabeled_whale | 5,000,000.0000 | 5.93% |
| 7 | 0x0c4b...8c61 | - | unlabeled_whale | 4,499,990.0000 | 5.34% |
| 8 | 0x238a...e6c4 | PancakeSwap Vault (0x23...e6c4) | dex | 1,189,799.9302 | 1.41% |
| 9 | 0xc806...e799 | degenrunner.bnb | labeled | 725,989.1899 | 0.86% |
| 10 | 0x1026...4820 | - | unlabeled_whale | 490,624.2551 | 0.58% |
| 11 | 0x3723...c168 | - | mid_wallet | 317,418.9519 | 0.38% |
| 12 | 0x440a...5593 | - | mid_wallet | 148,987.4824 | 0.18% |
| 13 | 0x119e...71e5 | - | mid_wallet | 100,000.0000 | 0.12% |
| 14 | 0xf16b...d019 | wyzq.eth | labeled | 80,598.3421 | 0.10% |
| 15 | 0x8fa4...ee16 | Uniswap (BSC-USD-PRL) | dex | 76,783.5535 | 0.09% |
| 16 | 0x28e2...e9df | Uniswap PoolManager (0x28...e9dF) | dex | 53,805.2553 | 0.06% |
| 17 | 0x35ee...8d83 | - | contract | 45,866.5128 | 0.05% |
| 18 | 0x6cce...bb4a | - | tail_wallet | 40,748.4063 | 0.05% |
| 19 | 0x008a...b557 | - | tail_wallet | 37,141.8990 | 0.04% |
| 20 | 0x4128...deae | - | tail_wallet | 34,943.3847 | 0.04% |

## 2. 持仓年龄与回流/新进

- 该部分仅统计非基础设施地址，即排除 BubbleMaps 标记的 CEX / DEX / contract。
- `new_wallet`: 首次入场 < 30 天。
- `return_wallet`: 首次入场 >= 30 天，近 30 天重新净流入，且 31-60 天窗口未出现同等级增持。

| Age Bucket | Addr Count | Amount | Supply Share |
| --- | --- | --- | --- |
| short_term | 484 | 75,314,750.1806 | 89.33% |

| Cohort | Addr Count | Amount | Supply Share |
| --- | --- | --- | --- |
| new_wallet | 484 | 75,314,750.1806 | 89.33% |

## 3. CEX 相关筹码

- 显式持仓只展示 BubbleMaps 直接标注为 CEX 的地址。
- 交易所方向识别使用本地 exchange registry，只用于判断 `向交易所 / 从交易所` 流向，不用于给无标签地址命名。

### BubbleMaps 显式 CEX 持仓

| Rank | Address | Label | Amount | Share |
| --- | --- | --- | --- | --- |
| 3 | 0x73d8...46db | Binance Wallet Proxy (EIP-1967 Transparent) | 7,331,819.1749 | 8.70% |

### 近 30 天主要向交易所存入

| Address | Label | 30d CEX Deposit | Behavior | Current Share |
| --- | --- | --- | --- | --- |
| 0xcd63...fc37 | - | 4,647.1396 | CEX-Selling | 0.00% |
| 0x0678...6e90 | - | 484.9753 | Inactive | 0.00% |
| 0x5b82...d322 | - | 484.9753 | Inactive | 0.00% |

### 近 30 天主要从交易所提出

| Address | Label | 30d CEX Withdraw | Behavior | Current Share |
| --- | --- | --- | --- | --- |
| 0xbd97...2866 | - | 2,591,678.7446 | CEX-Withdrawing | 0.01% |
| 0xc806...e799 | degenrunner.bnb | 54,717.0577 | CEX-Withdrawing | 0.86% |
| 0x1c1c...2cf2 | - | 18,012.2538 | CEX-Withdrawing | 0.00% |

## 4. 关键钱包

| Address | Reason | Label | Behavior | 30d Netflow | Current Share |
| --- | --- | --- | --- | --- | --- |
| 0x0350...adc0 | Top unlabeled whale | - | Accumulating | 43,160,000.0000 | 51.19% |
| 0xc3c7...22d7 | Top unlabeled whale | - | Accumulating | 10,000,000.0000 | 11.86% |
| 0x5861...e257 | Top unlabeled whale | - | Accumulating | 5,000,000.0000 | 5.93% |
| 0x5a4c...4f50 | Top unlabeled whale | - | Accumulating | 5,000,000.0000 | 5.93% |
| 0xccf4...5b55 | Top unlabeled whale | - | Accumulating | 5,000,000.0000 | 5.93% |
| 0x0c4b...8c61 | Top unlabeled whale | - | Accumulating | 4,499,990.0000 | 5.34% |
| 0xc806...e799 | BubbleMaps labeled holder | degenrunner.bnb | CEX-Withdrawing | 725,989.1899 | 0.86% |
| 0x1026...4820 | Top unlabeled whale | - | Accumulating | 490,624.2551 | 0.58% |
| 0xf16b...d019 | BubbleMaps labeled holder | wyzq.eth | Accumulating | 80,598.3421 | 0.10% |
| 0x246a...727c | BubbleMaps labeled holder | Bybit Deposit | Accumulating | 16,006.3923 | 0.02% |
| 0xbd97...2866 | Largest 30d exchange withdrawer | - | CEX-Withdrawing | 14,033.3449 | 0.01% |
| 0x6457...baec | BubbleMaps labeled holder | "Jay-V13" on OpenSea | Accumulating | 10,983.9085 | 0.01% |
| 0x28ea...454c | BubbleMaps labeled holder | kepler | Mixed | 5,330.0863 | 0.01% |
| 0x54c8...61d7 | BubbleMaps labeled holder | MEXC Deposit | Mixed | 4,305.0744 | 0.01% |
| 0xa1d2...ea55 | BubbleMaps labeled holder | @ArjayManalo18 "Jaymanalo" on OpenSea | Inactive | 3,074.3753 | 0.00% |
| 0x1c1c...2cf2 | Largest 30d exchange withdrawer | - | CEX-Withdrawing | 8.2812 | 0.00% |
| 0xcd63...fc37 | Largest 30d exchange depositor | - | CEX-Selling | 0.0000 | 0.00% |
| 0x0678...6e90 | Largest 30d exchange depositor | - | Inactive | 0.0000 | 0.00% |
| 0x5b82...d322 | Largest 30d exchange depositor | - | Inactive | 0.0000 | 0.00% |

## 5. 近期活动

- 非基础设施地址 30d 净流量合计: 75,328,826.7603 PRL
- 非基础设施地址 7d 净流量合计: 75,328,826.7603 PRL

### 近 30 天主要增持

| Address | Label | 30d Netflow | 7d Netflow | Cohort | Behavior |
| --- | --- | --- | --- | --- | --- |
| 0x0350...adc0 | - | 43,160,000.0000 | 43,160,000.0000 | new_wallet | Accumulating |
| 0xc3c7...22d7 | - | 10,000,000.0000 | 10,000,000.0000 | new_wallet | Accumulating |
| 0x5861...e257 | - | 5,000,000.0000 | 5,000,000.0000 | new_wallet | Accumulating |
| 0x5a4c...4f50 | - | 5,000,000.0000 | 5,000,000.0000 | new_wallet | Accumulating |
| 0xccf4...5b55 | - | 5,000,000.0000 | 5,000,000.0000 | new_wallet | Accumulating |
| 0x0c4b...8c61 | - | 4,499,990.0000 | 4,499,990.0000 | new_wallet | Accumulating |
| 0xc806...e799 | degenrunner.bnb | 725,989.1899 | 725,989.1899 | new_wallet | CEX-Withdrawing |
| 0x1026...4820 | - | 490,624.2551 | 490,624.2551 | new_wallet | Accumulating |

### 近 30 天主要减持

| Address | Label | 30d Netflow | 7d Netflow | Cohort | Behavior |
| --- | --- | --- | --- | --- | --- |
| - | - | - | - | - | - |

## 6. 综合判断与风险

- Top10 address concentration is very high at 97.73% of total supply.
- BubbleMaps explicit labels cover only 11.29% of supply, so attribution confidence is structurally limited.
- 30d exchange-directed flow is net positive for holders: withdrawals 2,664,408.06 PRL vs deposits 5,617.09 PRL.
- Fresh wallets control more supply than returning wallets (89.33% vs 0.00%), suggesting newer demand is driving the current holder mix.
- BubbleMaps labels are treated as the only explicit entity source. Unlabeled addresses are classified by behavior only.
- BubbleMaps holder balances were sampled against on-chain balanceOf. If the snapshot drifted, the script refreshes all balances from chain and keeps BubbleMaps only as a label source.
- Cost basis and realized PnL are not included in this report because the current environment does not provide a reliable per-trade pricing ledger for PRL.
