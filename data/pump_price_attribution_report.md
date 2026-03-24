# PUMP Price Attribution Report

- Generated at (UTC): 2026-03-24T03:03:35Z
- Price range: 2025-09-11 to 2026-03-23

## Key Verdict

- Buyback existed and was large in cumulative terms, but price support was diluted by confirmed official token releases into exchanges and market-making / DEX routes, while 59-holder proxy flows did not show a synchronized whale exit in the March 2026 sell windows.
- Claimed cumulative buyback: $328,000,000 holding ~103.963B in treasury.
- Confirmed official CEX pressure: 26.184B PUMP.
- Confirmed official market-maker / DEX pressure: 3.203B PUMP.
- Whale sample proxy flow: buys 99.561B vs sells 73.305B.

## Buyback Baseline

- Observable direct buyback floor: $3,945,646.21 on 0.606B PUMP at ~$0.006508 average.
- Observable transfer-to-treasury floor: 3.070B PUMP, implied $19,978,777.45 using observed average buy price.
- Execution style: twap_like_fragmented (69 direct legs / 5 batches / 4 active days).
- Observability caveat: Directly observable buyback legs are concentrated in July 2025. Later buybacks are likely under-counted in direct execution data and need treasury / Squads-side reconciliation.

## Official Pressure

- PUMP Team/Investor Squads Vault #4 (SELLING → OKX): 3.125B via confirmed_cex; current balance 15.630B.
- PUMP Team/Investor Squads Vault #5 Wallet A (ACTIVE SELLING): 11.859B via confirmed_cex; current balance 6.890B.
- PUMP Investor Wallet #1 (CONFIRMED): 11.200B via confirmed_cex; current balance 8.800B.
- Pump.fun Team Wallet #1 (CONFIRMED): 3.203B via market_maker_and_dex; current balance 0.000B.
- Official Allocation Multisig #2: 0.869B via non_sell_distribution; current balance 19.131B.

## Event Windows

| Window | Official Pressure (B) | Whale Sell (B) | Whale Buy (B) | Buyback USD | T+3 | T+7 | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---|
| Observable Buyback Start (2025-07-15) | 0.000 | 0.000 | 0.000 | 0 | n/a% | n/a% | Window was driven more by holder rebalancing than by confirmed official flow. |
| Vault #4 -> OKX (2025-10-06) | 0.000 | 5.236 | 3.827 | 0 | -10.68% | -29.95% | Window was driven more by holder rebalancing than by confirmed official flow. |
| Team Wallet Distribution Start (2026-02-16) | 0.644 | 1.865 | 0.471 | 0 | -6.67% | -19.16% | Official pressure coincided with weak whale balance support. |
| Investor #1 -> Kraken (2026-02-26) | 11.200 | 1.838 | 7.490 | 0 | 6.60% | 12.25% | Official/official-linked supply hit the market while sampled whales were net accumulating. |
| Weekly Buyback Milestone (2026-03-03) | 1.758 | 2.531 | 8.050 | 115,645,606 | -3.23% | 4.59% | Official/official-linked supply hit the market while sampled whales were net accumulating. |
| Vault #5 -> Bitget Tranche 1 (2026-03-06) | 1.758 | 1.960 | 9.510 | 124,295,312 | 5.22% | 6.52% | Official/official-linked supply hit the market while sampled whales were net accumulating. |
| Vault #5 -> Bitget Tranche 2 (2026-03-10) | 3.961 | 0.351 | 6.754 | 8,649,706 | -1.44% | 4.14% | Official/official-linked supply hit the market while sampled whales were net accumulating. |
| Vault #5 -> Bitget Tranche 3 (2026-03-13) | 5.414 | 0.748 | 4.086 | 0 | 8.95% | -5.51% | Official/official-linked supply hit the market while sampled whales were net accumulating. |
| Vault #5 -> Bitget Tranche 4 (2026-03-16) | 2.953 | 0.982 | 4.540 | 16,420,000 | -14.43% | -18.00% | Official/official-linked supply hit the market while sampled whales were net accumulating. |

## Whale Clusters

- Hyperunit: Hot Wallet: current 10.539B; proxy net -23.888B; entry est. 2025-07-14 @ $n/a.
- Fireblocks Custody: current 0.586B; proxy net -2.436B; entry est. 2025-08-14 @ $n/a.
- Top Whale #7: current 2.300B; proxy net -1.319B; entry est. 2025-07-15 @ $n/a.
- Top Whale #44: current 0.628B; proxy net -0.623B; entry est. 2025-07-14 @ $n/a.
- Fireblocks Custody: current 1.282B; proxy net -0.501B; entry est. 2025-08-14 @ $n/a.
- Top Whale #25: current 0.896B; proxy net -0.150B; entry est. 2025-07-15 @ $n/a.
- Top Whale #52: current 0.600B; proxy net -0.150B; entry est. 2025-07-14 @ $n/a.
- Top Whale #20: current 1.000B; proxy net 0.000B; entry est. 2025-07-14 @ $n/a.

## Cost Anchors

- Current price: $0.001767 on 2026-03-23.
- Versus claimed buyback average $0.003350: -47.25%.
- Versus observable July direct-buy average $0.006508: -72.85%.

## Limits

- Later buybacks are likely under-counted in direct execution data because routing may occur through Squads internals or other program-controlled accounts.
- Whale flows are proxy signals from balance deltas, not direct exchange-transfer proof.
- Current price comparisons do not prove realized PnL; they only frame pressure relative to observed or estimated cost anchors.
- The 59-holder sample captures large-address behavior, not the full free float.
