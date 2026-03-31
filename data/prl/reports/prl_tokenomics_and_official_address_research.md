# Perle / PRL 代币经济与官方地址推测研究

生成时间: 2026-03-31  
研究对象:
- Solana 主部署: `PERLEQKUNUp1dgFZ8EvyXHdN9d6ZQqfGxALDvfs6pDs`
- BSC 次级部署/流通面: `0xd20fB09A49a8e75Fef536A2dBc68222900287BAc`

## 1. 结论先行

1. 从官方 docs 的表述看，Perle 公开承认和重点维护的 canonical PRL 是 Solana 上的 `PERLEQK...`，不是 BSC 上的 `0xd20f...`.
2. 官方 tokenomics 明确写的是 `1,000,000,000 PRL` 总量、`Solana`、`Token-2022/SPL`、`2026-03-25 TGE`。BSC 合约链上读到的是 `84,315,132.158643 PRL`，数量级和部署叙事都不同。
3. 因此，BSC 这个合约更像是二级流通面、桥接/映射仓、运营分发面，至少不是官方 docs 里定义的主发行层。
4. 如果目标是找“官方可能控制的地址”，BSC 侧最值得盯的不是 Binance / LP / `degenrunner.bnb`，而是:
   - 合约 owner: `0xb9dd5fba2ec9a5bc53fd62d0a00d5cd766828a6b`
   - 合约 deployer: `0xceaedc06b40f59d64e7a2a84e7942e49c6f4e8af`
   - 分发母仓: `0x0350c44e15ada696992d44b13225e0853277adc0`
   - 与母仓高度一致的分仓簇: `0xc3c74940e878b0e9ac86a12b0125c4df1a8f22d7` `0x5861703aa2c6acd7a3902e5a06f6aedba0eae257` `0x5a4c318d66c0cf8ef381320a5d49f8a329414f50` `0xccf4d99cb373e054cc8dbf31dca37b8528ec5b55` `0x0c4bb5b2a4cff8c035b590da8e0cf650f63f8c61` `0x1026efec22061b9f463b63e75e8b531a76404820`
5. 我的判断是:
   - `0xb9dd...` 和 `0xceaed...` 是 BSC 侧“官方控制/部署基础设施”的高置信候选。
   - `0x0350...` 是“官方或官方协调的分发母仓”的高置信候选。
   - 其余 6 个未标注 Top 地址是“官方或官方协调的受配/分仓地址”的中高置信候选。

## 2. 官方 docs 到底在讲什么

### 2.1 项目本体

Perle Labs 的公开定位不是 memecoin，也不是纯交易型资产，而是一个把专家标注、验证、审校流程链上化的 AI 数据平台。公开 docs 和官网都反复强调几件事:
- 平台面向企业 AI 团队与专家贡献者两边市场。
- 贡献者先赚的是 points、reputation、tier、badges，链上奖励是这些行为的最终结算层。
- 平台强调 provenance / audit trail，也就是每笔任务、验证、报酬都要能追溯。

这意味着 PRL 的经济设计不是“单一治理代币”，而是更接近:
- 企业端支付媒介
- 贡献者端激励与结算资产
- 数据 provenance 的结算凭证

### 2.2 官方 token 设计

官方 docs 里最关键的 token 参数是:
- Token name: `Perle`
- Ticker: `$PRL`
- Blockchain: `Solana`
- Standard: `SPL / Token-2022`
- Total Supply: `1B`
- TGE Date: `2026-03-25`
- Contract Address: `PERLEQKUNUp1dgFZ8EvyXHdN9d6ZQqfGxALDvfs6pDs`

官方 audit 文档还补充了安全参数:
- Mint authority revoked
- Freeze authority null
- Metadata stored on-chain with Token-2022 metadata extension
- Metadata update authority: `6pJjJFA69U4YFvwu1wajkLBrP4BoP2ULncBBjKwidLRG`

这组描述非常明确地把“官方主 token”锚定在 Solana，而不是 BSC。

### 2.3 代币经济

官方 docs 给出的分配是:

| Bucket | Share | TGE Unlock | Cliff | Linear Vesting | Total Unlock |
| --- | --- | --- | --- | --- | --- |
| Team | 17.00% | 0% | 12 months | 36 months | 48 months |
| Investors | 27.66% | 0% | 12 months | 36 months | 48 months |
| Ecosystem | 17.84% | 10% of total supply | None | Remainder over 48 months | 48 months |
| Community | 37.50% | 7.5% of total supply | None | Remainder over 36 months | 36 months |

几个关键点:
- Team + Investors 在 TGE 都是 `0%`，理论上 launch 时不该直接有大量 insider 流通。
- 真正会在 TGE 打到市场面的，主要是 `Community` 和 `Ecosystem`.
- docs 对 `Community` 的叙事非常重，尤其强调 beta 阶段已经分发大量 reputation-weighted points，以后要把早期行为转成长期经济参与。

### 2.4 激励闭环

官方 utility 页给出的闭环是:
- Enterprise clients buy PRL to access annotation / fine-tuning / QA workflows.
- Contributors earn PRL for verified work.

FAQ / Getting Started 页又说明:
- 当前平台上日常行为先体现为 points / reputation / tiers / streak multipliers.
- docs 里写到 points 决定 “future claim eligibility”.
- FAQ 明说 “in future releases, these points will be convertible into onchain rewards distributed through Solana”.

这说明 Perle 的设计是:
- 平台行为层: points / reputation / tiers
- 结算层: PRL
- 主结算链: Solana

## 3. 链上部署情况

### 3.1 Solana 是官方主部署

支持这一点的证据最强:
- Token Overview 明写 `Blockchain: Solana`.
- FAQ 反复写平台 “runs on Solana”.
- Audit 页明确说 PRL 是 “SPL Token-2022 token deployed on Solana”.
- docs 没有把 BSC 当作主发行链来讲。

因此，研究“官方地址”时，Solana 的 mint / metadata authority / reward distribution 才是主权层。

### 3.2 BSC 是什么

BSC 这边链上读到的参数是:
- Name: `Perle`
- Symbol: `PRL`
- Decimals: `8`
- Total supply: `84,315,132.158643`
- Deployer tx: `0xec54cede0fb9eb213cfb1c5d7211eca31f3d7ae0b7b64f5d695ba76896d11a8c`
- Deployer: `0xceaedc06b40f59d64e7a2a84e7942e49c6f4e8af`
- Contract deployment block: `87,746,660`
- `owner()` returns: `0xb9dd5fba2ec9a5bc53fd62d0a00d5cd766828a6b`

额外观察:
- `owner()` 指向的是合约地址，不是普通 EOA。
- 该 owner 合约当前还持有 `0.5 PRL`.
- BSC 合约的第一批事件非常轻量，最早只看到 `1 PRL` mint 到 deployer，再有一次 `0.5 PRL` burn，说明这不是“部署时一次性大铸造”的传统初始分发流程。

### 3.3 Solana 主发行 vs BSC 次级流通面

这个对比很关键:

| 维度 | Solana 主部署 | BSC 部署 |
| --- | --- | --- |
| 官方 docs 承认度 | 高 | 公开 docs 未明确说明 |
| Supply | 1,000,000,000 | 84,315,132.158643 |
| 标准 | Token-2022 / SPL | ERC20 / BEP20 |
| 叙事 | 主网络结算与 provenance | 更像次级流通或映射面 |

我的推断:
- BSC 不是 canonical issuance.
- BSC 更可能是官方为了交易流动性、生态曝光或跨链流通做的运营侧部署/映射面。
- 如果有人只盯 BSC 合约，很容易把“运营流通地址”误当成“主权发行地址”.

## 4. 把 docs 和 BSC top holders 对起来

### 4.1 BSC Top10 结构

BSC 侧当前 Top10:
- Top10 占供应: `97.73%`
- 7 个未标注地址合计: `73,150,614.25512712 PRL`
- 这 7 个未标注地址占 BSC 供给: `86.76%`
- 这 7 个未标注地址占 Solana 1B 总量的映射比例: `7.315%`

这个 `7.315%` 非常值得注意，因为它和 docs 里 `Community` 在 TGE 解锁的 `7.5% of total supply` 很接近。

这不能直接证明两者一一对应，但它给出一个很强的结构性线索:
- BSC 上最核心的未标注大户簇，规模上非常像官方可流通初始份额中的一个子集，尤其像 launch / community / MM / distribution 用仓。

### 4.2 哪些 Top 地址更像官方控制层

#### 高置信

`0x0350c44e15ada696992d44b13225e0853277adc0`
- 当前持仓: `43.16M PRL`，占 BSC 供给 `51.19%`
- 全历史累计收到 `90M`，累计转出 `46.84M`
- 对手方数 `5`
- 形态不是单纯囤币地址，而是“大额收币后再分发”的母仓

这类地址最像:
- 官方初始分发母仓
- 官方运营仓
- 官方协调的做市/配售总仓

#### 中高置信

这几类地址都很像从同一母仓拆出去的分仓:
- `0xc3c74940e878b0e9ac86a12b0125c4df1a8f22d7` 持 `10M`
- `0x5861703aa2c6acd7a3902e5a06f6aedba0eae257` 持 `5M`
- `0x5a4c318d66c0cf8ef381320a5d49f8a329414f50` 持 `5M`
- `0xccf4d99cb373e054cc8dbf31dca37b8528ec5b55` 持 `5M`
- `0x0c4bb5b2a4cff8c035b590da8e0cf650f63f8c61` 持 `4.49999M`
- `0x1026efec22061b9f463b63e75e8b531a76404820` 持 `490,624`

共同特征:
- 大多是近一周新形成仓位
- 多数只有 `1` 个对手方
- 基本没有卖出历史，或只有很小的再分发动作
- 持仓规模呈现很整齐的整数分层

这种整齐度非常不像自然市场买出来的仓位，更像预设的运营/分发分仓。

#### 明确不是“官方控盘仓”的

`0x73d8bd54f7cf5fab43fe4ef40a62d390644946db`
- BubbleMaps 标记为 `Binance Wallet Proxy`
- 对手方数 `1214`
- 明显是交易所库存 / 热钱包性质

`0x238a358808379702088667322f80ac48bad5e6c4`
- BubbleMaps 标记为 `PancakeSwap Vault`
- 对手方数 `1770`
- 这是 LP / 交易流动性，不是官方控盘仓

`0xc80633843f6e00bbc63dd4b2383acf3c4586e799`
- BubbleMaps 标记为 `degenrunner.bnb`
- 近 30 天有交易所提出记录
- 更像外部具名大户/交易者，而不是官方仓

## 5. 官方可能是哪些地址

我把“官方可能地址”拆成三个层级。

### A. 协议/合约控制层

最像官方基础设施的地址:
- `0xb9dd5fba2ec9a5bc53fd62d0a00d5cd766828a6b`
  - BSC token `owner()`
  - 是合约，不是 EOA
  - 高置信属于权限控制层
- `0xceaedc06b40f59d64e7a2a84e7942e49c6f4e8af`
  - BSC token deployer
  - 当前余额为 0
  - 更像部署/初始化执行地址

Solana 侧公开能直接看到的权限相关地址:
- `PERLEQKUNUp1dgFZ8EvyXHdN9d6ZQqfGxALDvfs6pDs`
  - 官方 docs 明示 mint 地址
- `6pJjJFA69U4YFvwu1wajkLBrP4BoP2ULncBBjKwidLRG`
  - 官方 docs 明示 metadata update authority

### B. BSC 运营/分发层

高概率官方或官方协调地址:
- `0x0350c44e15ada696992d44b13225e0853277adc0`
- `0xc3c74940e878b0e9ac86a12b0125c4df1a8f22d7`
- `0x5861703aa2c6acd7a3902e5a06f6aedba0eae257`
- `0x5a4c318d66c0cf8ef381320a5d49f8a329414f50`
- `0xccf4d99cb373e054cc8dbf31dca37b8528ec5b55`
- `0x0c4bb5b2a4cff8c035b590da8e0cf650f63f8c61`
- `0x1026efec22061b9f463b63e75e8b531a76404820`

这里最核心的是:
- `0x0350...` 像母仓
- 其余几乎都像分仓

### C. 交易/流动性层

这些地址很重要，但不宜直接归为“官方仓”:
- `0x73d8bd54f7cf5fab43fe4ef40a62d390644946db` Binance
- `0x238a358808379702088667322f80ac48bad5e6c4` PancakeSwap Vault
- `0xc80633843f6e00bbc63dd4b2383acf3c4586e799` degenrunner.bnb

## 6. 我的最终判断

### 高置信判断

1. `PERLEQK...` 才是官方主部署。
2. BSC 的 `0xd20f...` 不是 canonical issuance，而是次级流通/运营面。
3. `0xb9dd...` 是 BSC 合约控制层候选，`0xceaed...` 是部署层候选。
4. `0x0350...` 是 BSC 侧最像官方分发母仓的地址。

### 中高置信判断

1. `0xc3c7...`、`0x5861...`、`0x5a4c...`、`0xccf4...`、`0x0c4b...`、`0x1026...` 很可能不是独立市场用户，而是与官方或官方协调方相关的分仓。
2. 这组未标注大户簇总量与 docs 中 Community TGE 解锁比例非常接近，这种数量级匹配不是随机噪音。

### 我不会下结论的部分

1. 我还不能严格证明这些 BSC 分仓一定由 Perle 团队自持，也可能是团队 + 做市商 + distribution partner 的协调仓。
2. 我没有看到官方 docs 明文写出 BSC 合约地址，所以不能把 BSC 合约直接等同于“官方主 token”.
3. 没有完整 creator -> mother wallet -> sub-wallet 的逐笔链路前，不建议把每个未标注地址都下成“团队钱包”的死结论。

## 7. 下一步最值得继续挖的方向

如果要把“官方地址”再从高概率推到接近确认，下一步我建议按这个顺序挖:

1. 拉 `0xceaed...`、`0xb9dd...`、`0x0350...` 的全历史 token transfer 和 native BNB 交互。
2. 看 `0x0350...` 的首笔大额入账对手方是谁，是否能回接到 deployer / owner 控制面。
3. 看 `0x0350...` 分发给 `0xc3c7... / 0x5861... / 0x5a4c... / 0xccf4... / 0x0c4b... / 0x1026...` 的时间是否集中在同一批 tx / block。
4. 查这些分仓地址有没有共同的 gas sponsor、共同的创建时间模式、共同的 BNB 补 gas 来源。
5. 补 Solana 侧 mint / largest accounts / metadata authority 交互，确认 BSC 这批地址到底是跨链映射出来的，还是单独运营出来的。

## 8. 主要公开来源

官方 docs / 官网:
- Welcome / platform intro: https://perle.gitbook.io/perle-docs
- Token Overview: https://perle.gitbook.io/perle-docs/tokenomics/token-overview
- Perle Tokenomics: https://perle.gitbook.io/perle-docs/tokenomics/perle-tokenomics
- Token Vesting: https://perle.gitbook.io/perle-docs/tokenomics/token-vesting
- PRL utility: https://perle.gitbook.io/perle-docs/tokenomics/prl-token-utility-and-purpose
- VeryAI claim flow: https://perle.gitbook.io/perle-docs/tokenomics/verify-your-humanity-with-veryai
- FAQ: https://perle.gitbook.io/perle-docs/faq
- Official company funding announcement: https://www.perle.ai/resources/perle-secures-9-million-seed-round-led-by-framework-ventures-to-launch-an-ai-data-training-platform-powered-by-web3

本地链上研究产物:
- `data/prl/derived/prl_holder_analysis.json`
- `data/prl/reports/prl_holder_structure_report.md`
