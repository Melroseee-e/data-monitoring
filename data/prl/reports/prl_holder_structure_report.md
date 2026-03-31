# Perle (PRL) Top 10 筹码结构研究

- BSC 研究合约: `0xd20fB09A49a8e75Fef536A2dBc68222900287BAc`
- Solana 地址: `PERLEQKUNUp1dgFZ8EvyXHdN9d6ZQqfGxALDvfs6pDs`
- 主研究链: BSC
- 总供应量: 84,315,132.1586 PRL
- 生成时间: 2026-03-31 02:23 UTC
- BubbleMaps 快照: Top 500 holders
- 已知本地交易所地址数: 40

## 1. 先看结论

- Top10 已经解释了 97.73% 的总供应，PRL 当前不是“分散持仓”，而是“Top10 决定流通盘”。
- Top10 里有 7 个未标注地址，合计 86.76%；这 7 个地址才是需要重点盯的控盘层。
- Top10 里真正有明确公共标签的只有 3 类仓位: Binance 库存 8.70%、Pancake 流动性 1.41%、`degenrunner.bnb` 0.86%。
- Top11 到 Top50 只剩 1.55%，说明研究重点不该再分散到长尾，而是把 Top10 尤其是那 7 个未标注大户逐个盯住。

## 2. Top 10 分层

| 层级 | 地址数 | Amount | Supply Share | 涉及 Rank | 解读 |
| --- | --- | --- | --- | --- | --- |
| 未标注大户分发簇 | 7 | 73,150,614.2551 | 86.76% | 1, 2, 4, 5, 6, 7, 10 | 未标注大户簇，表现为新钱包集中拿仓。 |
| 交易所库存层 | 1 | 7,331,819.1749 | 8.70% | 3 | BubbleMaps 已识别的交易所库存。 |
| DEX 流动性层 | 1 | 1,189,799.9302 | 1.41% | 8 | BubbleMaps 已识别的 LP / 交易流动性。 |
| 具名地址层 | 1 | 725,989.1899 | 0.86% | 9 | BubbleMaps 已识别的具名地址。 |

| Rank | Address | BubbleMaps Label | 标签层 | 角色判断 | Amount | Share | 30d Netflow |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0x0350...adc0 | - | 无 BubbleMaps 标签 | 主分发母仓 | 43,160,000.0000 | 51.19% | 43,160,000.0000 |
| 2 | 0xc3c7...22d7 | - | 无 BubbleMaps 标签 | 单次受配分仓 | 10,000,000.0000 | 11.86% | 10,000,000.0000 |
| 3 | 0x73d8...46db | Binance Wallet Proxy (EIP-1967 Transparent) | BubbleMaps 显式 CEX | 交易所库存地址 | 7,331,819.1749 | 8.70% | 7,309,682.4185 |
| 4 | 0x5861...e257 | - | 无 BubbleMaps 标签 | 单次受配分仓 | 5,000,000.0000 | 5.93% | 5,000,000.0000 |
| 5 | 0x5a4c...4f50 | - | 无 BubbleMaps 标签 | 单次受配分仓 | 5,000,000.0000 | 5.93% | 5,000,000.0000 |
| 6 | 0xccf4...5b55 | - | 无 BubbleMaps 标签 | 单次受配分仓 | 5,000,000.0000 | 5.93% | 5,000,000.0000 |
| 7 | 0x0c4b...8c61 | - | 无 BubbleMaps 标签 | 二级分发分仓 | 4,499,990.0000 | 5.34% | 4,499,990.0000 |
| 8 | 0x238a...e6c4 | PancakeSwap Vault (0x23...e6c4) | BubbleMaps 显式 DEX / LP | DEX / LP 流动性地址 | 1,189,799.9302 | 1.41% | 1,186,665.1898 |
| 9 | 0xc806...e799 | degenrunner.bnb | 具名个人/团队地址 | 具名增持地址 | 725,989.1899 | 0.86% | 725,989.1899 |
| 10 | 0x1026...4820 | - | 无 BubbleMaps 标签 | 单次受配分仓 | 490,624.2551 | 0.58% | 490,624.2551 |

## 3. Top 10 地址逐个研究

### Rank 1 | 0x0350...adc0

- BubbleMaps Label: `None`
- 标签层: 无 BubbleMaps 标签
- 角色判断: 主分发母仓
- 当前持仓: 43,160,000.0000 PRL (51.19%)
- 首次入场: 2026-03-23 14:04 UTC
- 最近转出: 2026-03-24 20:37 UTC
- 全历史累计收/发: 90,000,000.0000 / 46,840,000.0000
- 近 30 天净流量: 43,160,000.0000
- 近 30 天交易所提出 / 存入: 0.0000 / 0.0000
- 对手方数: 5
- 行为分类: Accumulating | 钱包分组: new_wallet
- 研究判断: 该地址没有 BubbleMaps 标签，但当前仍持有 51.19%。它既是最大仓位又承担明显再分发，形态上更像本轮大户簇的主分发母仓。

### Rank 2 | 0xc3c7...22d7

- BubbleMaps Label: `None`
- 标签层: 无 BubbleMaps 标签
- 角色判断: 单次受配分仓
- 当前持仓: 10,000,000.0000 PRL (11.86%)
- 首次入场: 2026-03-25 07:34 UTC
- 最近转出: -
- 全历史累计收/发: 10,000,000.0000 / 0.0000
- 近 30 天净流量: 10,000,000.0000
- 近 30 天交易所提出 / 存入: 0.0000 / 0.0000
- 对手方数: 1
- 行为分类: Accumulating | 钱包分组: new_wallet
- 研究判断: 该地址没有 BubbleMaps 标签，且基本表现为单次收币后静置，当前持仓 11.86%。形态上更像受配分仓或独立保管仓。

### Rank 3 | 0x73d8...46db

- BubbleMaps Label: `Binance Wallet Proxy (EIP-1967 Transparent)`
- 标签层: BubbleMaps 显式 CEX
- 角色判断: 交易所库存地址
- 当前持仓: 7,331,819.1749 PRL (8.70%)
- 首次入场: 2026-03-25 10:00 UTC
- 最近转出: 2026-03-30 08:01 UTC
- 全历史累计收/发: 117,629,568.1381 / 110,319,885.7196
- 近 30 天净流量: 7,309,682.4185
- 近 30 天交易所提出 / 存入: 0.0000 / 0.0000
- 对手方数: 1214
- 行为分类: Accumulating | 钱包分组: new_wallet
- 研究判断: BubbleMaps 直接标记为 Binance Wallet Proxy (EIP-1967 Transparent)。对手方数量高、近 30 天双向流转明显，更像交易所库存而不是单一控盘仓；但它单地址仍占 8.70%，对短期流通面有实质影响。

### Rank 4 | 0x5861...e257

- BubbleMaps Label: `None`
- 标签层: 无 BubbleMaps 标签
- 角色判断: 单次受配分仓
- 当前持仓: 5,000,000.0000 PRL (5.93%)
- 首次入场: 2026-03-25 07:23 UTC
- 最近转出: -
- 全历史累计收/发: 5,000,000.0000 / 0.0000
- 近 30 天净流量: 5,000,000.0000
- 近 30 天交易所提出 / 存入: 0.0000 / 0.0000
- 对手方数: 1
- 行为分类: Accumulating | 钱包分组: new_wallet
- 研究判断: 该地址没有 BubbleMaps 标签，且基本表现为单次收币后静置，当前持仓 5.93%。形态上更像受配分仓或独立保管仓。

### Rank 5 | 0x5a4c...4f50

- BubbleMaps Label: `None`
- 标签层: 无 BubbleMaps 标签
- 角色判断: 单次受配分仓
- 当前持仓: 5,000,000.0000 PRL (5.93%)
- 首次入场: 2026-03-24 11:22 UTC
- 最近转出: -
- 全历史累计收/发: 5,000,000.0000 / 0.0000
- 近 30 天净流量: 5,000,000.0000
- 近 30 天交易所提出 / 存入: 0.0000 / 0.0000
- 对手方数: 1
- 行为分类: Accumulating | 钱包分组: new_wallet
- 研究判断: 该地址没有 BubbleMaps 标签，且基本表现为单次收币后静置，当前持仓 5.93%。形态上更像受配分仓或独立保管仓。

### Rank 6 | 0xccf4...5b55

- BubbleMaps Label: `None`
- 标签层: 无 BubbleMaps 标签
- 角色判断: 单次受配分仓
- 当前持仓: 5,000,000.0000 PRL (5.93%)
- 首次入场: 2026-03-24 11:25 UTC
- 最近转出: -
- 全历史累计收/发: 5,000,000.0000 / 0.0000
- 近 30 天净流量: 5,000,000.0000
- 近 30 天交易所提出 / 存入: 0.0000 / 0.0000
- 对手方数: 1
- 行为分类: Accumulating | 钱包分组: new_wallet
- 研究判断: 该地址没有 BubbleMaps 标签，且基本表现为单次收币后静置，当前持仓 5.93%。形态上更像受配分仓或独立保管仓。

### Rank 7 | 0x0c4b...8c61

- BubbleMaps Label: `None`
- 标签层: 无 BubbleMaps 标签
- 角色判断: 二级分发分仓
- 当前持仓: 4,499,990.0000 PRL (5.34%)
- 首次入场: 2026-03-25 07:40 UTC
- 最近转出: 2026-03-26 09:21 UTC
- 全历史累计收/发: 5,000,000.0000 / 500,010.0000
- 近 30 天净流量: 4,499,990.0000
- 近 30 天交易所提出 / 存入: 0.0000 / 0.0000
- 对手方数: 3
- 行为分类: Accumulating | 钱包分组: new_wallet
- 研究判断: 该地址没有 BubbleMaps 标签，当前持仓 5.34%，有少量再分发动作但没有形成公开实体标签，应视为未标注的大户分支。

### Rank 8 | 0x238a...e6c4

- BubbleMaps Label: `PancakeSwap Vault (0x23...e6c4)`
- 标签层: BubbleMaps 显式 DEX / LP
- 角色判断: DEX / LP 流动性地址
- 当前持仓: 1,189,799.9302 PRL (1.41%)
- 首次入场: 2026-03-25 01:37 UTC
- 最近转出: 2026-03-30 08:02 UTC
- 全历史累计收/发: 852,118,671.0909 / 850,932,005.9011
- 近 30 天净流量: 1,186,665.1898
- 近 30 天交易所提出 / 存入: 0.0000 / 0.0000
- 对手方数: 1770
- 行为分类: Accumulating | 钱包分组: new_wallet
- 研究判断: BubbleMaps 直接标记为 PancakeSwap Vault (0x23...e6c4)。它承接的是交易流动性而不是主观控盘仓，当前占供应 1.41%，属于可交易流动性池库存。

### Rank 9 | 0xc806...e799

- BubbleMaps Label: `degenrunner.bnb`
- 标签层: 具名个人/团队地址
- 角色判断: 具名增持地址
- 当前持仓: 725,989.1899 PRL (0.86%)
- 首次入场: 2026-03-25 10:00 UTC
- 最近转出: -
- 全历史累计收/发: 725,989.1899 / 0.0000
- 近 30 天净流量: 725,989.1899
- 近 30 天交易所提出 / 存入: 54,717.0577 / 0.0000
- 对手方数: 7
- 行为分类: CEX-Withdrawing | 钱包分组: new_wallet
- 研究判断: 这是 BubbleMaps 具名地址，近 30 天有明确的交易所提出记录，当前保留 0.86% 仓位，行为上偏增持而不是派发。

### Rank 10 | 0x1026...4820

- BubbleMaps Label: `None`
- 标签层: 无 BubbleMaps 标签
- 角色判断: 单次受配分仓
- 当前持仓: 490,624.2551 PRL (0.58%)
- 首次入场: 2026-03-25 10:05 UTC
- 最近转出: -
- 全历史累计收/发: 490,624.2551 / 0.0000
- 近 30 天净流量: 490,624.2551
- 近 30 天交易所提出 / 存入: 0.0000 / 0.0000
- 对手方数: 1
- 行为分类: Accumulating | 钱包分组: new_wallet
- 研究判断: 该地址没有 BubbleMaps 标签，且基本表现为单次收币后静置，当前持仓 0.58%。形态上更像受配分仓或独立保管仓。

## 4. BubbleMaps 标签分层

- BubbleMaps 一共给出 14 个已标注地址，对应 13 个去重标签，覆盖 11.29% 的供应量。
- 这部分只能作为显式标签下限。对未标注地址，本报告只做行为归类，不额外创造实体名。

| Label | 标签层 | Addr Count | Top Rank | Amount | Supply Share |
| --- | --- | --- | --- | --- | --- |
| Binance Wallet Proxy (EIP-1967 Transparent) | BubbleMaps 显式 CEX | 1 | 3 | 7,331,819.1749 | 8.70% |
| PancakeSwap Vault (0x23...e6c4) | BubbleMaps 显式 DEX / LP | 1 | 8 | 1,189,799.9302 | 1.41% |
| degenrunner.bnb | 具名个人/团队地址 | 1 | 9 | 725,989.1899 | 0.86% |
| Uniswap (BSC-USD-PRL) | BubbleMaps 显式 DEX / LP | 2 | 15 | 91,986.0237 | 0.11% |
| wyzq.eth | 具名个人/团队地址 | 1 | 14 | 80,598.3421 | 0.10% |
| Uniswap PoolManager (0x28...e9dF) | BubbleMaps 显式 DEX / LP | 1 | 16 | 53,805.2553 | 0.06% |
| Bybit Deposit | 交易所相关标签 | 1 | 24 | 16,006.3923 | 0.02% |
| "Jay-V13" on OpenSea | 具名个人/团队地址 | 1 | 35 | 10,983.9085 | 0.01% |
| PancakeSwap (BSC-USD-PRL) | BubbleMaps 显式 DEX / LP | 1 | 48 | 7,200.1110 | 0.01% |
| kepler | 具名个人/团队地址 | 1 | 58 | 5,330.0863 | 0.01% |
| MEXC Deposit | 交易所相关标签 | 1 | 66 | 4,305.0744 | 0.01% |
| @ArjayManalo18 "Jaymanalo" on OpenSea | 具名个人/团队地址 | 1 | 78 | 3,074.3753 | 0.00% |
| Proxy | 具名合约 | 1 | 92 | 1,826.9051 | 0.00% |

## 5. Top 10 之外还剩什么

- Top11-Top50 合计 1.55%；Top51-Top500 合计 0.72%。
- 换句话说，Top10 之外所有地址加起来只占 2.27%。

| Segment | Addr Count | Amount | Supply Share |
| --- | --- | --- | --- |
| unlabeled_whale | 7 | 73,150,614.2551 | 86.76% |
| cex | 1 | 7,331,819.1749 | 8.70% |
| dex | 5 | 1,342,791.3200 | 1.59% |
| labeled | 8 | 848,114.2739 | 1.01% |
| tail_wallet | 467 | 751,442.1224 | 0.89% |
| mid_wallet | 3 | 566,406.4342 | 0.67% |
| contract | 9 | 64,213.3794 | 0.08% |

## 6. 交易所与流动性侧

- BubbleMaps 显式 CEX 仓位下限为 8.70%，当前基本都落在 Binance 那个单地址上。
- BubbleMaps 显式 DEX / LP 仓位下限为 1.59%。
- 近 30 天非基础设施地址从交易所净提出 2,664,408.0561 PRL，向交易所净存入 5,617.0902 PRL。

### 近 30 天主要从交易所提出

| Address | Label | 角色判断 | 30d CEX Withdraw | Current Share |
| --- | --- | --- | --- | --- |
| 0xbd97...2866 | - | 普通持仓地址 | 2,591,678.7446 | 0.01% |
| 0xc806...e799 | degenrunner.bnb | 具名增持地址 | 54,717.0577 | 0.86% |
| 0x1c1c...2cf2 | - | 普通持仓地址 | 18,012.2538 | 0.00% |

### 近 30 天主要向交易所存入

| Address | Label | 角色判断 | 30d CEX Deposit | Current Share |
| --- | --- | --- | --- | --- |
| 0xcd63...fc37 | - | 二级分发分仓 | 4,647.1396 | 0.00% |
| 0x0678...6e90 | - | 二级分发分仓 | 484.9753 | 0.00% |
| 0x5b82...d322 | - | 二级分发分仓 | 484.9753 | 0.00% |

## 7. 综合判断

- 真正需要研究的不是“PRL 的 500 个 holder”，而是 Top10 里的 7 个未标注大户簇，它们合计控制 86.76%。
- 这 7 个地址几乎全部在近一周内形成仓位，且多数是单次收币后静置，说明当前流通盘并没有充分打散。
- Binance 和 PancakeSwap 仓位虽然很大，但性质不同于控盘母仓，前者更像交易所库存，后者更像交易流动性。
- `degenrunner.bnb` 是 Top10 里唯一值得继续持续追踪的具名非基础设施地址，因为它既进入了 Top10，又出现了明确的交易所提出行为。
- BubbleMaps labels are treated as the only explicit entity source. Unlabeled addresses are classified by behavior only.
- BubbleMaps holder balances were sampled against on-chain balanceOf. If the snapshot drifted, the script refreshes all balances from chain and keeps BubbleMaps only as a label source.
- Cost basis and realized PnL are not included in this report because the current environment does not provide a reliable per-trade pricing ledger for PRL.
