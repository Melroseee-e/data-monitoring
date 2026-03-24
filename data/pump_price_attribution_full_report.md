# PUMP Full Price Attribution Report

- Generated at (UTC): 2026-03-24T03:03:35Z
- Token: PUMP
- Contract: `pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn`
- Price coverage in this report: 2025-09-11 to 2026-03-23

## Executive Summary

- Core answer: Buyback existed and was large in cumulative terms, but price support was diluted by confirmed official token releases into exchanges and market-making / DEX routes, while 59-holder proxy flows did not show a synchronized whale exit in the March 2026 sell windows.
- Claimed cumulative buyback reached $328,000,000, with treasury still holding about 103.963B PUMP.
- Confirmed official exchange deposits alone reached 26.184B PUMP, equal to 26.75% of the conservative claimed buyback token volume.
- Including confirmed Wintermute / DEX-style official release, market-facing official pressure reached 29.387B PUMP, or 30.02% of the conservative claimed buyback token volume.
- The 59-holder sample was net accumulating overall: buys 99.561B vs sells 73.305B.
- Current price $0.001767 is -47.25% below the claimed buyback average cost anchor and -72.85% below the observable July direct-buy average.

## Direct Answer

### Why did price fail to sustain upside despite buybacks?

1. A large part of buyback support was offset by confirmed official and official-linked market supply. The confirmed market-facing official pressure in this report is 29.387B PUMP.
2. The most aggressive official sell windows in March 2026 were not matched by broad whale distribution in the 59-holder sample. That weakens the “whales caused the drop” explanation and strengthens the “official overhang dominated the tape” explanation for those windows.
3. Buyback observability is incomplete after July 2025. The chain-forensic floor is real, but later cumulative buyback size mostly comes from treasury reconciliation and milestone claims, not direct execution traces. That makes the buyback program credible, but it also means the market may have seen the sell side more clearly than the buy side.
4. The current market price sits materially below both buyback cost anchors used here. That implies buybacks did not succeed in lifting the effective market clearing level or eliminating overhead supply.

## Buyback Verification Baseline

- Observable direct buyback floor: $3,945,646.21 on 0.606B PUMP.
- Observable transfer-to-treasury floor: 3.070B PUMP, implied $19,978,777.45 using observable average price.
- Claimed conservative cumulative bought amount: 97.900B PUMP.
- Claimed cumulative average buyback price: $0.003350.
- Execution style observed on-chain: `twap_like_fragmented`.
- Observability caveat: Directly observable buyback legs are concentrated in July 2025. Later buybacks are likely under-counted in direct execution data and need treasury / Squads-side reconciliation.

### Buyback Interpretation

- The forensic layer proves buybacks existed and were mechanically executed.
- The direct execution trace is a lower bound, not the full program total.
- Treasury holdings and third-party cumulative milestones imply buybacks were economically meaningful, but not sufficient to absorb all official overhang.

## Official Market Pressure

| Entity | Type | Pressure Type | Confirmed Pressure (B) | Current Balance (B) | % of Conservative Buyback |
|---|---|---|---:|---:|---:|
| PUMP Team/Investor Squads Vault #4 (SELLING → OKX) | official_vesting_vault | confirmed_cex | 3.125 | 15.630 | 3.19% |
| PUMP Team/Investor Squads Vault #5 Wallet A (ACTIVE SELLING) | official_vesting_vault | confirmed_cex | 11.859 | 6.890 | 12.11% |
| PUMP Investor Wallet #1 (CONFIRMED) | investor_wallet | confirmed_cex | 11.200 | 8.800 | 11.44% |
| Pump.fun Team Wallet #1 (CONFIRMED) | team_wallet | market_maker_and_dex | 3.203 | 0.000 | 3.27% |
| Official Allocation Multisig #2 | official_multisig | non_sell_distribution | 0.869 | 19.131 | 0.89% |

### Official Sell Ledger

| Date | Entity | Flow Type | Exchange / Route | Amount (B) | USD |
|---|---|---|---|---:|---:|
| 2025-09-07 | PUMP Team/Investor Squads Vault #5 Wallet A (ACTIVE SELLING) | to_cex | Bitget | 4.6875 | n/a |
| 2025-10-01 | Official Allocation Multisig #2 | to_wallet | n/a | 0.8689 | n/a |
| 2025-10-06 | PUMP Team/Investor Squads Vault #4 (SELLING → OKX) | to_cex | OKX | 1.5625 | n/a |
| 2025-10-06 | PUMP Team/Investor Squads Vault #4 (SELLING → OKX) | to_cex | OKX | 1.5625 | n/a |
| 2026-02-16 | Pump.fun Team Wallet #1 (CONFIRMED) | to_mm | Wintermute | 0.5433 | n/a |
| 2026-02-17 | Pump.fun Team Wallet #1 (CONFIRMED) | to_mm | Wintermute | 0.3291 | n/a |
| 2026-02-18 | Pump.fun Team Wallet #1 (CONFIRMED) | to_mm | Wintermute | 1.2011 | n/a |
| 2026-02-19 | Pump.fun Team Wallet #1 (CONFIRMED) | to_mm | Wintermute | 0.7318 | n/a |
| 2026-02-20 | Pump.fun Team Wallet #1 (CONFIRMED) | to_mm | Wintermute | 0.5712 | n/a |
| 2026-02-21 | Pump.fun Team Wallet #1 (CONFIRMED) | to_mm | Wintermute | 0.3735 | n/a |
| 2026-02-26 | PUMP Investor Wallet #1 (CONFIRMED) | to_cex | Kraken | 11.2000 | 21,220,000.00 |
| 2026-03-06 | PUMP Team/Investor Squads Vault #5 Wallet A (ACTIVE SELLING) | to_cex | Bitget | 1.7580 | n/a |
| 2026-03-10 | PUMP Team/Investor Squads Vault #5 Wallet A (ACTIVE SELLING) | to_cex | Bitget | 2.4610 | n/a |
| 2026-03-13 | PUMP Team/Investor Squads Vault #5 Wallet A (ACTIVE SELLING) | to_cex | Bitget | 1.5000 | n/a |
| 2026-03-16 | PUMP Team/Investor Squads Vault #5 Wallet A (ACTIVE SELLING) | to_cex | Bitget | 1.4530 | n/a |

### Official Pressure Interpretation

- `Vault #5` is the single largest confirmed exchange-pressure source in this dataset.
- `Investor Wallet #1` is the next largest confirmed exchange-pressure source via Kraken.
- `Team Wallet #1` is not a clean CEX deposit story, but it is still market-facing supply through Wintermute and DEX routes.
- `Official Allocation Multisig #2` is explicitly separated as non-sell distribution and should not be conflated with active dumping.

## 59-Holder Whale Sample

- Coverage: 59 whale-class addresses in the behavior profile layer.
- Aggregate proxy flow: buys 99.561B vs sells 73.305B; net 26.256B.

### Top Accumulators

| Label | Current Balance (B) | Proxy Buy (B) | Proxy Sell (B) | Proxy Net (B) |
|---|---:|---:|---:|---:|
| Coinbase-Connected PUMP Holder | 7.189 | 7.051 | 0.000 | 7.051 |
| Top Whale #3 | 4.690 | 5.290 | 0.600 | 4.690 |
| Top Whale #5 | 2.826 | 10.665 | 6.421 | 4.244 |
| Top Whale #9 | 1.912 | 2.985 | 0.000 | 2.985 |
| Top Whale #6 | 2.800 | 2.800 | 0.000 | 2.800 |
| Top Whale #16 | 1.109 | 9.451 | 6.968 | 2.483 |
| Top Whale #8 | 2.050 | 2.050 | 0.000 | 2.050 |
| Top Whale #11 | 1.623 | 2.067 | 0.444 | 1.623 |
| Fireblocks Custody | 1.634 | 2.462 | 0.883 | 1.579 |
| Fireblocks Custody | 1.328 | 2.038 | 0.760 | 1.278 |

### Top Distributors

| Label | Current Balance (B) | Proxy Buy (B) | Proxy Sell (B) | Proxy Net (B) |
|---|---:|---:|---:|---:|
| Hyperunit: Hot Wallet | 10.539 | 17.787 | 41.676 | -23.888 |
| Fireblocks Custody | 0.586 | 0.587 | 3.023 | -2.436 |
| Top Whale #7 | 2.300 | 1.822 | 3.141 | -1.319 |
| Top Whale #44 | 0.628 | 0.000 | 0.623 | -0.623 |
| Fireblocks Custody | 1.282 | 1.282 | 1.783 | -0.501 |
| Top Whale #25 | 0.896 | 0.000 | 0.150 | -0.150 |
| Top Whale #52 | 0.600 | 0.000 | 0.150 | -0.150 |
| Top Whale #20 | 1.000 | 0.000 | 0.000 | 0.000 |
| Top Whale #32 | 0.786 | 0.000 | 0.000 | 0.000 |
| Top Whale #33 | 0.770 | 0.000 | 0.000 | 0.000 |

### Whale Interpretation

- The sample does not support a simple “all whales were dumping into buyback” explanation for March 2026.
- Several large holders were still accumulating or at least not materially distributing during the official sell windows.
- The single biggest proxy distributor is `Hyperunit: Hot Wallet`, but its label and balance pattern are more consistent with a market-making or inventory wallet than a clean directional dump wallet.

## Event Window Analysis

| Window | Official Pressure (B) | Whale Sell (B) | Whale Buy (B) | Whale Net (B) | Buyback USD | T+3 Return | T+7 Return |
|---|---:|---:|---:|---:|---:|---:|---:|
| Observable Buyback Start (2025-07-15) | 0.000 | 0.000 | 0.000 | 0.000 | 0 | n/a% | n/a% |
| Vault #4 -> OKX (2025-10-06) | 0.000 | 5.236 | 3.827 | -1.409 | 0 | -10.68% | -29.95% |
| Team Wallet Distribution Start (2026-02-16) | 0.644 | 1.865 | 0.471 | -1.394 | 0 | -6.67% | -19.16% |
| Investor #1 -> Kraken (2026-02-26) | 11.200 | 1.838 | 7.490 | 5.652 | 0 | 6.60% | 12.25% |
| Weekly Buyback Milestone (2026-03-03) | 1.758 | 2.531 | 8.050 | 5.518 | 115,645,606 | -3.23% | 4.59% |
| Vault #5 -> Bitget Tranche 1 (2026-03-06) | 1.758 | 1.960 | 9.510 | 7.550 | 124,295,312 | 5.22% | 6.52% |
| Vault #5 -> Bitget Tranche 2 (2026-03-10) | 3.961 | 0.351 | 6.754 | 6.403 | 8,649,706 | -1.44% | 4.14% |
| Vault #5 -> Bitget Tranche 3 (2026-03-13) | 5.414 | 0.748 | 4.086 | 3.338 | 0 | 8.95% | -5.51% |
| Vault #5 -> Bitget Tranche 4 (2026-03-16) | 2.953 | 0.982 | 4.540 | 3.558 | 16,420,000 | -14.43% | -18.00% |

### Event Window Readout

- **Observable Buyback Start (2025-07-15)**: Window was driven more by holder rebalancing than by confirmed official flow.
- **Vault #4 -> OKX (2025-10-06)**: Window was driven more by holder rebalancing than by confirmed official flow.
- **Team Wallet Distribution Start (2026-02-16)**: Official pressure coincided with weak whale balance support.
- **Investor #1 -> Kraken (2026-02-26)**: Official/official-linked supply hit the market while sampled whales were net accumulating.
- **Weekly Buyback Milestone (2026-03-03)**: Official/official-linked supply hit the market while sampled whales were net accumulating.
- **Vault #5 -> Bitget Tranche 1 (2026-03-06)**: Official/official-linked supply hit the market while sampled whales were net accumulating.
- **Vault #5 -> Bitget Tranche 2 (2026-03-10)**: Official/official-linked supply hit the market while sampled whales were net accumulating.
- **Vault #5 -> Bitget Tranche 3 (2026-03-13)**: Official/official-linked supply hit the market while sampled whales were net accumulating.
- **Vault #5 -> Bitget Tranche 4 (2026-03-16)**: Official/official-linked supply hit the market while sampled whales were net accumulating.

## Cost Basis & Overhang

- Current price: $0.001767 (2026-03-23).
- Claimed cumulative buyback average: $0.003350.
- Observable July direct-buy average: $0.006508.
- Distance vs claimed buyback average: -47.25%.
- Distance vs observable July direct-buy average: -72.85%.
- Treasury marked value at current price: $183,702,621.00.

### Cost Interpretation

- If buyback averages are even directionally correct, current price being far below them implies buybacks were not sufficient to reprice the market upward.
- This is consistent with a market structure where official overhang and unlock-related fear dominate the perceived support value of buybacks.

## Final Attribution

### What is well supported

- Buybacks were real and non-trivial.
- Official and official-linked market-facing supply was also real and large.
- The largest confirmed sell-side sources were official or official-linked wallets, not unlabeled whales.
- During the major March 2026 windows, the 59-holder sample was more net bid than net offered.

### What remains uncertain

- The full post-July 2025 direct execution footprint of buybacks.
- Realized cost basis for many unlabeled whales and custodial addresses.
- Whether some unlabeled large holders are indirect official affiliates beyond the currently confirmed set.

## Data Quality & Limits

- Coverage: Direct buyback observability is strong in July 2025 and weaker afterward.
- Coverage: Official vault / investor sell events are structured and confirmed for the main pressure addresses.
- Coverage: 59-holder whale history covers balance behavior but not direct exchange attribution.
- Known conflict: Investor Wallet #1 is not marked as to_cex in pump_team_analysis.json but is confirmed as 11.2B -> Kraken in pump_addresses.json, pump_whale_analysis.json, and PUMP_Phase1_Report.md.
- Limitation: Later buybacks are likely under-counted in direct execution data because routing may occur through Squads internals or other program-controlled accounts.
- Limitation: Whale flows are proxy signals from balance deltas, not direct exchange-transfer proof.
- Limitation: Current price comparisons do not prove realized PnL; they only frame pressure relative to observed or estimated cost anchors.
- Limitation: The 59-holder sample captures large-address behavior, not the full free float.

## Source Registry

- `team_analysis`: `data/pump_team_analysis.json` (official_wallet_flows)
- `addresses`: `data/pump_addresses.json` (verified_official_events)
- `whale_analysis`: `data/pump_whale_analysis.json` (holder_labels_and_provenance)
- `whale_chart`: `data/pump_whale_chart_data.json` (59_whale_daily_balances)
- `buyback_recon`: `data/pump_buyback_source_reconciliation.json` (buyback_observable_absorption)
- `phase1_report`: `PUMP_Phase1_Report.md` (confirmed_vault_sell_tables)
