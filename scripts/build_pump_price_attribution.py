#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'
REPORT_PATH = DATA_DIR / 'pump_price_attribution_report.md'
FULL_REPORT_PATH = DATA_DIR / 'pump_price_attribution_full_report.md'
OUTPUT_PATH = DATA_DIR / 'pump_price_attribution.json'

BEHAVIOR_PATH = DATA_DIR / 'pump_behavior_chart_data.json'
WHALE_ANALYSIS_PATH = DATA_DIR / 'pump_whale_analysis.json'
WHALE_CHART_PATH = DATA_DIR / 'pump_whale_chart_data.json'
BUYBACK_ANALYSIS_PATH = DATA_DIR / 'pump_buyback_analysis.json'
BUYBACK_RECON_PATH = DATA_DIR / 'pump_buyback_source_reconciliation.json'
ADDRESSES_PATH = DATA_DIR / 'pump_addresses.json'
TEAM_ANALYSIS_PATH = DATA_DIR / 'pump_team_analysis.json'
FORENSIC_REPORT_PATH = DATA_DIR / 'pump_buyback_forensic_report.md'

KEY_WINDOWS = [
    ('2025-07-15', 'Observable Buyback Start', 'buyback_start'),
    ('2025-10-06', 'Vault #4 -> OKX', 'official_cex'),
    ('2026-02-16', 'Team Wallet Distribution Start', 'official_distribution'),
    ('2026-02-26', 'Investor #1 -> Kraken', 'official_cex'),
    ('2026-03-03', 'Weekly Buyback Milestone', 'buyback_milestone'),
    ('2026-03-06', 'Vault #5 -> Bitget Tranche 1', 'official_cex'),
    ('2026-03-10', 'Vault #5 -> Bitget Tranche 2', 'official_cex'),
    ('2026-03-13', 'Vault #5 -> Bitget Tranche 3', 'official_cex'),
    ('2026-03-16', 'Vault #5 -> Bitget Tranche 4', 'official_cex'),
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))



def round_or_none(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)



def pct_change(current: float | None, future: float | None) -> float | None:
    if current in (None, 0) or future is None:
        return None
    return round((future / current - 1) * 100, 2)



def fmt_num(value: float | None, digits: int = 2) -> str:
    if value is None:
        return 'n/a'
    return f'{value:,.{digits}f}'



def fmt_billions(value: float | None) -> str:
    if value is None:
        return 'n/a'
    return f'{value:.3f}B'



def first_balance_date(history: dict[str, Any]) -> str | None:
    for day in sorted(history.keys()):
        if float(history.get(day, 0) or 0) > 0:
            return day
    return None



def build_summary(data: dict[str, Any]) -> dict[str, Any]:
    buyback = data['buyback']
    pressure = data['sell_pressure']
    cost = data['cost_basis']

    official_cex = pressure['official_rollup']['confirmed_cex_pressure_B']
    official_market = pressure['official_rollup']['confirmed_market_maker_or_dex_pressure_B']
    conservative_buyback = buyback['claimed_conservative_bought_B']
    cex_ratio = round((official_cex / conservative_buyback) * 100, 2) if conservative_buyback else None
    total_market_ratio = round(((official_cex + official_market) / conservative_buyback) * 100, 2) if conservative_buyback else None

    answer = (
        'Buyback existed and was large in cumulative terms, but price support was diluted by confirmed official token releases '
        'into exchanges and market-making / DEX routes, while 59-holder proxy flows did not show a synchronized whale exit in the '
        'March 2026 sell windows.'
    )

    return {
        'headline': answer,
        'latest_price_usd': cost['current_price_usd'],
        'buyback_claimed_usd': buyback['claimed_cumulative_usd'],
        'buyback_treasury_hold_B': buyback['treasury_hold_B'],
        'official_cex_pressure_B': official_cex,
        'official_market_pressure_B': official_market,
        'official_cex_pressure_pct_of_claimed_buyback_B': cex_ratio,
        'official_total_market_pressure_pct_of_claimed_buyback_B': total_market_ratio,
        'whale_proxy_sell_B': pressure['whale_proxy_rollup']['total_sell_B'],
        'whale_proxy_buy_B': pressure['whale_proxy_rollup']['total_buy_B'],
        'key_takeaways': [
            f'Confirmed official CEX pressure reached {official_cex:.3f}B PUMP, about {cex_ratio:.2f}% of the conservative claimed buyback token volume.',
            f'Including Wintermute / DEX-style official release, confirmed market-facing official pressure reached {(official_cex + official_market):.3f}B PUMP.',
            'In the major March 2026 sell windows, the 59-holder sample was mostly net accumulating rather than synchronously net distributing.',
            f'Current price is {cost["distance_from_claimed_buyback_avg_pct"]:.2f}% below the claimed cumulative buyback average price and {cost["distance_from_observed_buyback_avg_pct"]:.2f}% below the observable July direct-buy average price.',
        ],
    }



def main() -> None:
    behavior = load_json(BEHAVIOR_PATH)
    whale_analysis = load_json(WHALE_ANALYSIS_PATH)
    whale_chart = load_json(WHALE_CHART_PATH)
    buyback_analysis = load_json(BUYBACK_ANALYSIS_PATH)
    buyback_recon = load_json(BUYBACK_RECON_PATH)
    addresses = load_json(ADDRESSES_PATH)
    team_analysis = load_json(TEAM_ANALYSIS_PATH)

    candles = behavior['price']['candles']
    prices = {c['date']: float(c['close']) for c in candles}
    latest_candle = candles[-1]
    current_price = float(latest_candle['close'])

    address_profiles = {p['address']: p for p in behavior['address_profiles']}
    whale_histories = {w['address']: w.get('history', {}) for w in whale_chart['whales']}

    buy_cost = buyback_recon['buy_cost_estimation']
    transfer_cost = buyback_recon['transfer_cost_estimation']
    execution_style = buyback_recon['execution_style']
    buyback_totals = buyback_analysis['cumulative_buyback_totals']

    buyback = {
        'claimed_cumulative_usd': float(buyback_totals['total_usd_spent']),
        'claimed_conservative_bought_B': float(buyback_totals['estimated_total_pump_bought_B_conservative']),
        'claimed_news_calc_bought_B': float(buyback_totals['estimated_total_pump_bought_B_news_calc']),
        'claimed_avg_price_usd': float(buyback_totals['estimated_avg_buy_price_usd']),
        'treasury_hold_B': float(buyback_totals['treasury_current_hold_B']),
        'observable_direct_buy_usd': float(buy_cost['usd_est_close_total']),
        'observable_direct_buy_pump_B': float(buy_cost['total_pump']) / 1e9,
        'observable_direct_buy_avg_price_usd': float(buy_cost['avg_price_usd_est_close']),
        'observable_transfer_to_treasury_pump_B': float(transfer_cost['total_pump']) / 1e9,
        'observable_transfer_implied_usd': float(transfer_cost['usd_est_from_buy_avg_price']),
        'observable_buy_leg_count': int(execution_style['buy_leg_count']),
        'observable_buy_batch_count': int(execution_style['buy_batch_count']),
        'observable_active_day_count': int(execution_style['active_day_count']),
        'execution_style': execution_style['style'],
        'execution_style_reason': execution_style['reason'],
        'observability_note': (
            'Directly observable buyback legs are concentrated in July 2025. Later buybacks are likely under-counted in direct execution data '
            'and need treasury / Squads-side reconciliation.'
        ),
    }

    addr_map = addresses['addresses']
    official_entities: list[dict[str, Any]] = []
    official_sell_ledger: list[dict[str, Any]] = []

    def add_entity(address: str, label: str, entity_type: str, pressure_type: str, confirmed_pressure_B: float, current_balance_B: float | None, notes: str) -> None:
        profile = address_profiles.get(address, {})
        official_entities.append({
            'address': address,
            'label': label,
            'entity_type': entity_type,
            'pressure_type': pressure_type,
            'confirmed_pressure_B': round(confirmed_pressure_B, 4),
            'current_balance_B': round_or_none(current_balance_B),
            'share_of_conservative_buyback_pct': round((confirmed_pressure_B / buyback['claimed_conservative_bought_B']) * 100, 2) if buyback['claimed_conservative_bought_B'] else None,
            'exchange_name': profile.get('exchange_name'),
            'note': notes,
        })

    def add_ledger_event(
        event_id: str,
        date: str,
        from_address: str,
        label: str,
        amount_B: float,
        flow_type: str,
        *,
        exchange: str | None = None,
        amount_usd: float | None = None,
        confirmed: bool = True,
        source_ids: list[str] | None = None,
        note: str | None = None,
    ) -> None:
        official_sell_ledger.append({
            'event_id': event_id,
            'date': date,
            'from_address': from_address,
            'label': label,
            'exchange': exchange,
            'amount_pump_B': round(amount_B, 4),
            'amount_usd': round_or_none(amount_usd, 2),
            'flow_type': flow_type,
            'confirmed': confirmed,
            'source_ids': source_ids or [],
            'note': note,
        })

    vault4 = addr_map['GhFaBi8sy3M5mgG97YguQ6J3f7XH4JwV5CoW8MbzRgAU']
    vault5 = addr_map['5v7ZZg1D1si417WhUQF9Br2dRQEnd1sTbCfesscUCVKE']
    investor1 = addr_map['9UcygiamY92yGntGkUkBKi4SdApxkBMZd9QSo6wMC2dN']
    team1 = addr_map['77DsB9kw8u8eKesicT44hGirsj5A2SicGdFPQZZEzPXe']

    add_entity(
        'GhFaBi8sy3M5mgG97YguQ6J3f7XH4JwV5CoW8MbzRgAU',
        vault4['label'],
        'official_vesting_vault',
        'confirmed_cex',
        float(vault4['okx_deposits_oct_2025']['total_B']),
        float(vault4['balance']) / 1e9,
        vault4['notes'],
    )
    for idx, event in enumerate(vault4['okx_deposits_oct_2025']['events'], start=1):
        add_ledger_event(
            f'vault4_okx_{idx}',
            event['date'],
            'GhFaBi8sy3M5mgG97YguQ6J3f7XH4JwV5CoW8MbzRgAU',
            vault4['label'],
            float(event['amount_B']),
            'to_cex',
            exchange=event.get('destination'),
            source_ids=['addresses', 'phase1_report'],
            note=vault4['notes'],
        )
    add_entity(
        '5v7ZZg1D1si417WhUQF9Br2dRQEnd1sTbCfesscUCVKE',
        vault5['label'],
        'official_vesting_vault',
        'confirmed_cex',
        float(vault5['bitget_deposits_all']['total_B']),
        float(vault5['balance']) / 1e9,
        vault5['notes'],
    )
    for idx, event in enumerate(vault5['bitget_deposits_all']['events'], start=1):
        add_ledger_event(
            f'vault5_bitget_{idx}',
            event['date'],
            '5v7ZZg1D1si417WhUQF9Br2dRQEnd1sTbCfesscUCVKE',
            vault5['label'],
            float(event['amount_B']),
            'to_cex',
            exchange=event.get('destination'),
            source_ids=['addresses', 'phase1_report'],
            note=vault5['notes'],
        )
    add_entity(
        '9UcygiamY92yGntGkUkBKi4SdApxkBMZd9QSo6wMC2dN',
        investor1['label'],
        'investor_wallet',
        'confirmed_cex',
        float(investor1['major_transfers'][0]['amount']) / 1e9,
        (float(investor1['received_from_custodian']) - float(investor1['major_transfers'][0]['amount'])) / 1e9,
        investor1['notes'],
    )
    add_ledger_event(
        'investor1_kraken_1',
        investor1['major_transfers'][0]['date'],
        '9UcygiamY92yGntGkUkBKi4SdApxkBMZd9QSo6wMC2dN',
        investor1['label'],
        float(investor1['major_transfers'][0]['amount']) / 1e9,
        'to_cex',
        exchange=investor1['major_transfers'][0]['destination'],
        amount_usd=float(investor1['major_transfers'][0]['value_usd']),
        source_ids=['addresses', 'whale_analysis', 'phase1_report'],
        note=investor1['notes'],
    )
    add_entity(
        '77DsB9kw8u8eKesicT44hGirsj5A2SicGdFPQZZEzPXe',
        team1['label'],
        'team_wallet',
        'market_maker_and_dex',
        float(team1['sell_breakdown']['wintermute_otc_B']) + float(team1['sell_breakdown']['dex_swaps_B']),
        float(team1.get('balance', 0)) / 1e9,
        team1['notes'],
    )
    for idx, event in enumerate(team1['selling_activity'], start=1):
        flow_type = 'to_mm' if 'Wintermute' in event['method'] else 'via_dex'
        add_ledger_event(
            f'team1_distribution_{idx}',
            event['date'],
            '77DsB9kw8u8eKesicT44hGirsj5A2SicGdFPQZZEzPXe',
            team1['label'],
            float(event['amount']) / 1e9,
            flow_type,
            exchange='Wintermute' if 'Wintermute' in event['method'] else None,
            source_ids=['addresses', 'team_analysis', 'phase1_report'],
            note=team1['notes'],
        )
    add_entity(
        '8UHpWBnhYNeAQURWjAABp8vSrzfYa69o7sfi65vYLC42',
        'Official Allocation Multisig #2',
        'official_multisig',
        'non_sell_distribution',
        float(whale_analysis['known_investor_summary']['8UHpWBnhYNeAQURWjAABp8vSrzfYa69o7sfi65vYLC42']['total_pump_out_B']),
        float(whale_analysis['known_investor_summary']['8UHpWBnhYNeAQURWjAABp8vSrzfYa69o7sfi65vYLC42']['current_balance_B']),
        whale_analysis['known_investor_summary']['8UHpWBnhYNeAQURWjAABp8vSrzfYa69o7sfi65vYLC42']['notes'],
    )
    add_ledger_event(
        'official_multisig_distribution',
        '2025-10-01',
        '8UHpWBnhYNeAQURWjAABp8vSrzfYa69o7sfi65vYLC42',
        'Official Allocation Multisig #2',
        float(whale_analysis['known_investor_summary']['8UHpWBnhYNeAQURWjAABp8vSrzfYa69o7sfi65vYLC42']['total_pump_out_B']),
        'to_wallet',
        confirmed=True,
        source_ids=['whale_analysis'],
        note='Staking / ecosystem reward distribution, not counted as confirmed sell pressure.',
    )

    official_rollup = {
        'confirmed_cex_pressure_B': round(sum(e['confirmed_pressure_B'] for e in official_entities if e['pressure_type'] == 'confirmed_cex'), 4),
        'confirmed_market_maker_or_dex_pressure_B': round(sum(e['confirmed_pressure_B'] for e in official_entities if e['pressure_type'] == 'market_maker_and_dex'), 4),
        'non_sell_distribution_B': round(sum(e['confirmed_pressure_B'] for e in official_entities if e['pressure_type'] == 'non_sell_distribution'), 4),
        'remaining_balance_B': round(sum((e['current_balance_B'] or 0) for e in official_entities if e['current_balance_B'] is not None), 4),
    }

    whale_profiles = [p for p in behavior['address_profiles'] if p['main_type'] == 'whale']
    whale_profiles.sort(key=lambda p: (p.get('sell_amount_B', 0) - p.get('buy_amount_B', 0), p.get('current_balance_B', 0)), reverse=True)
    whale_clusters: list[dict[str, Any]] = []
    for profile in whale_profiles[:12]:
        history = whale_histories.get(profile['address'], {})
        entry_date = first_balance_date(history)
        entry_price = prices.get(entry_date) if entry_date else None
        whale_clusters.append({
            'address': profile['address'],
            'label': profile['label'],
            'rank': profile.get('rank'),
            'exchange_name': profile.get('exchange_name'),
            'current_balance_B': round_or_none(profile.get('current_balance_B')),
            'proxy_buy_B': round_or_none(profile.get('buy_amount_B')),
            'proxy_sell_B': round_or_none(profile.get('sell_amount_B')),
            'proxy_net_B': round_or_none((profile.get('buy_amount_B', 0) or 0) - (profile.get('sell_amount_B', 0) or 0)),
            'share_total_supply_pct': round_or_none(profile.get('share_total_supply_pct'), 3),
            'entry_date_estimate': entry_date,
            'entry_price_estimate_usd': round_or_none(entry_price, 6),
            'current_vs_entry_pct': pct_change(entry_price, current_price) if entry_price else None,
            'source_tags': profile.get('source_tags', []),
            'note': profile.get('note'),
        })

    whale_proxy_rollup = {
        'total_sell_B': round(sum(p.get('sell_amount_B', 0) or 0 for p in whale_profiles), 4),
        'total_buy_B': round(sum(p.get('buy_amount_B', 0) or 0 for p in whale_profiles), 4),
        'net_B': round(sum((p.get('buy_amount_B', 0) or 0) - (p.get('sell_amount_B', 0) or 0) for p in whale_profiles), 4),
        'coverage_addresses': len(whale_profiles),
        'note': 'Whale flow is proxy-only and derived from daily balance changes among the 59-holder sample. It is not equivalent to confirmed exchange selling.',
    }
    whale_accumulators = sorted(
        [
            {
                'address': p['address'],
                'label': p['label'],
                'current_balance_B': round_or_none(p.get('current_balance_B')),
                'proxy_buy_B': round_or_none(p.get('buy_amount_B')),
                'proxy_sell_B': round_or_none(p.get('sell_amount_B')),
                'proxy_net_B': round_or_none((p.get('buy_amount_B', 0) or 0) - (p.get('sell_amount_B', 0) or 0)),
                'exchange_name': p.get('exchange_name'),
            }
            for p in whale_profiles
        ],
        key=lambda x: (x['proxy_net_B'] or 0),
        reverse=True,
    )
    whale_distributors = sorted(whale_accumulators, key=lambda x: (x['proxy_net_B'] or 0))

    top10_addresses = {w['address'] for w in whale_chart['whales'][:10]}
    top20_addresses = {w['address'] for w in whale_chart['whales'][:20]}
    whale_daily_netflow: list[dict[str, Any]] = []
    by_date = sorted({d for history in whale_histories.values() for d in history.keys()})
    for idx in range(1, len(by_date)):
        day = by_date[idx]
        prev_day = by_date[idx - 1]
        net59 = 0.0
        net10 = 0.0
        net20 = 0.0
        for whale in whale_chart['whales']:
            history = whale.get('history', {})
            delta = float(history.get(day, 0) or 0) - float(history.get(prev_day, 0) or 0)
            net59 += delta
            if whale['address'] in top10_addresses:
                net10 += delta
            if whale['address'] in top20_addresses:
                net20 += delta
        whale_daily_netflow.append({
            'date': day,
            'net_delta_B_59': round(net59, 4),
            'top10_delta_B': round(net10, 4),
            'top20_delta_B': round(net20, 4),
        })

    def window_stats(date_str: str, label: str, window_type: str) -> dict[str, Any]:
        center = datetime.strptime(date_str, '%Y-%m-%d').date()
        dates = [(center + timedelta(days=i)).isoformat() for i in range(-3, 4)]
        events = [e for e in behavior['events'] if e['date'] in dates]
        official_sell = sum((e.get('amount_B') or 0) for e in events if e['category'] == 'official_exchange')
        whale_sell = sum((e.get('amount_B') or 0) for e in events if e['category'] == 'whale_netflow' and e['direction'] == 'sell')
        whale_buy = sum((e.get('amount_B') or 0) for e in events if e['category'] == 'whale_netflow' and e['direction'] == 'buy')
        buyback_usd = sum((e.get('amount_usd') or 0) for e in events if e['category'] == 'buyback')
        price_now = prices.get(date_str)
        p3 = prices.get((center + timedelta(days=3)).isoformat())
        p7 = prices.get((center + timedelta(days=7)).isoformat())
        net_proxy = whale_buy - whale_sell
        if official_sell > 0 and net_proxy > 0:
            interpretation = 'Official/official-linked supply hit the market while sampled whales were net accumulating.'
        elif official_sell > 0 and net_proxy <= 0:
            interpretation = 'Official pressure coincided with weak whale balance support.'
        elif buyback_usd > 0 and net_proxy > 0:
            interpretation = 'Buyback narrative aligned with whale accumulation, but follow-through depended on overhead supply.'
        else:
            interpretation = 'Window was driven more by holder rebalancing than by confirmed official flow.'
        return {
            'date': date_str,
            'label': label,
            'window_type': window_type,
            'price_event_usd': round_or_none(price_now, 6),
            'price_t_plus_3_usd': round_or_none(p3, 6),
            'price_t_plus_7_usd': round_or_none(p7, 6),
            'return_t_plus_3_pct': pct_change(price_now, p3),
            'return_t_plus_7_pct': pct_change(price_now, p7),
            'official_confirmed_pressure_B_window': round(official_sell, 4),
            'whale_proxy_sell_B_window': round(whale_sell, 4),
            'whale_proxy_buy_B_window': round(whale_buy, 4),
            'whale_proxy_net_B_window': round(net_proxy, 4),
            'buyback_usd_window': round(buyback_usd, 2),
            'interpretation': interpretation,
        }

    event_windows = [window_stats(date_str, label, window_type) for date_str, label, window_type in KEY_WINDOWS]

    cost_basis = {
        'current_price_usd': round(current_price, 6),
        'current_price_date': latest_candle['date'],
        'claimed_buyback_avg_price_usd': buyback['claimed_avg_price_usd'],
        'observed_buyback_avg_price_usd': buyback['observable_direct_buy_avg_price_usd'],
        'distance_from_claimed_buyback_avg_pct': round((current_price / buyback['claimed_avg_price_usd'] - 1) * 100, 2),
        'distance_from_observed_buyback_avg_pct': round((current_price / buyback['observable_direct_buy_avg_price_usd'] - 1) * 100, 2),
        'treasury_hold_value_usd_current': round(buyback['treasury_hold_B'] * 1e9 * current_price, 2),
        'note': 'Whale entry prices are estimated from first visible balance appearance in the 59-holder history and daily close prices. They are rough anchors, not realized-cost reconstructions.',
    }

    methodology = {
        'confidence_tiers': [
            'Tier 1: confirmed on-chain official pressure from structured address tracing and signature-level buyback verification.',
            'Tier 2: treasury / milestone reconciliation from prior research outputs.',
            'Tier 3: whale proxy flows from daily balance changes in the 59-holder sample.',
        ],
        'limitations': [
            'Later buybacks are likely under-counted in direct execution data because routing may occur through Squads internals or other program-controlled accounts.',
            'Whale flows are proxy signals from balance deltas, not direct exchange-transfer proof.',
            'Current price comparisons do not prove realized PnL; they only frame pressure relative to observed or estimated cost anchors.',
            'The 59-holder sample captures large-address behavior, not the full free float.',
        ],
        'source_files': [
            str(BEHAVIOR_PATH.relative_to(BASE_DIR)),
            str(WHALE_ANALYSIS_PATH.relative_to(BASE_DIR)),
            str(WHALE_CHART_PATH.relative_to(BASE_DIR)),
            str(BUYBACK_ANALYSIS_PATH.relative_to(BASE_DIR)),
            str(BUYBACK_RECON_PATH.relative_to(BASE_DIR)),
            str(ADDRESSES_PATH.relative_to(BASE_DIR)),
            str(TEAM_ANALYSIS_PATH.relative_to(BASE_DIR)),
            str(FORENSIC_REPORT_PATH.relative_to(BASE_DIR)),
        ],
    }

    payload = {
        'metadata': {
            'generated_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            'token': 'PUMP',
            'contract': behavior['metadata']['contract'],
            'price_range_start': behavior['price']['start_date'],
            'price_range_end': behavior['price']['end_date'],
            'source_files': methodology['source_files'],
        },
        'source_registry': [
            {'id': 'team_analysis', 'path': str(TEAM_ANALYSIS_PATH.relative_to(BASE_DIR)), 'role': 'official_wallet_flows'},
            {'id': 'addresses', 'path': str(ADDRESSES_PATH.relative_to(BASE_DIR)), 'role': 'verified_official_events'},
            {'id': 'whale_analysis', 'path': str(WHALE_ANALYSIS_PATH.relative_to(BASE_DIR)), 'role': 'holder_labels_and_provenance'},
            {'id': 'whale_chart', 'path': str(WHALE_CHART_PATH.relative_to(BASE_DIR)), 'role': '59_whale_daily_balances'},
            {'id': 'buyback_recon', 'path': str(BUYBACK_RECON_PATH.relative_to(BASE_DIR)), 'role': 'buyback_observable_absorption'},
            {'id': 'phase1_report', 'path': str(Path('PUMP_Phase1_Report.md')), 'role': 'confirmed_vault_sell_tables'},
        ],
        'buyback': buyback,
        'sell_pressure': {
            'official_rollup': official_rollup,
            'whale_proxy_rollup': whale_proxy_rollup,
        },
        'cost_basis': cost_basis,
        'event_windows': event_windows,
        'official_entities': official_entities,
        'official_sell_ledger': official_sell_ledger,
        'whale_clusters': whale_clusters,
        'whale_accumulators': whale_accumulators[:10],
        'whale_distributors': whale_distributors[:10],
        'whale_daily_netflow': whale_daily_netflow,
        'methodology': methodology,
        'data_quality': {
            'coverage_flags': [
                'Direct buyback observability is strong in July 2025 and weaker afterward.',
                'Official vault / investor sell events are structured and confirmed for the main pressure addresses.',
                '59-holder whale history covers balance behavior but not direct exchange attribution.',
            ],
            'known_conflicts': [
                'Investor Wallet #1 is not marked as to_cex in pump_team_analysis.json but is confirmed as 11.2B -> Kraken in pump_addresses.json, pump_whale_analysis.json, and PUMP_Phase1_Report.md.',
            ],
            'limitations': methodology['limitations'],
        },
    }
    payload['summary'] = build_summary(payload)

    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [
        '# PUMP Price Attribution Report',
        '',
        f'- Generated at (UTC): {payload["metadata"]["generated_at"]}',
        f'- Price range: {payload["metadata"]["price_range_start"]} to {payload["metadata"]["price_range_end"]}',
        '',
        '## Key Verdict',
        '',
        f'- {payload["summary"]["headline"]}',
        f'- Claimed cumulative buyback: ${fmt_num(buyback["claimed_cumulative_usd"], 0)} holding ~{fmt_billions(buyback["treasury_hold_B"])} in treasury.',
        f'- Confirmed official CEX pressure: {fmt_billions(official_rollup["confirmed_cex_pressure_B"])} PUMP.',
        f'- Confirmed official market-maker / DEX pressure: {fmt_billions(official_rollup["confirmed_market_maker_or_dex_pressure_B"])} PUMP.',
        f'- Whale sample proxy flow: buys {fmt_billions(whale_proxy_rollup["total_buy_B"])} vs sells {fmt_billions(whale_proxy_rollup["total_sell_B"])}.',
        '',
        '## Buyback Baseline',
        '',
        f'- Observable direct buyback floor: ${fmt_num(buyback["observable_direct_buy_usd"], 2)} on {fmt_billions(buyback["observable_direct_buy_pump_B"])} PUMP at ~${fmt_num(buyback["observable_direct_buy_avg_price_usd"], 6)} average.',
        f'- Observable transfer-to-treasury floor: {fmt_billions(buyback["observable_transfer_to_treasury_pump_B"])} PUMP, implied ${fmt_num(buyback["observable_transfer_implied_usd"], 2)} using observed average buy price.',
        f'- Execution style: {buyback["execution_style"]} ({buyback["observable_buy_leg_count"]} direct legs / {buyback["observable_buy_batch_count"]} batches / {buyback["observable_active_day_count"]} active days).',
        f'- Observability caveat: {buyback["observability_note"]}',
        '',
        '## Official Pressure',
        '',
    ]
    for entity in official_entities:
        lines.append(
            f'- {entity["label"]}: {fmt_billions(entity["confirmed_pressure_B"])} via {entity["pressure_type"]}; current balance {fmt_billions(entity["current_balance_B"])}.'
        )
    lines.extend([
        '',
        '## Event Windows',
        '',
        '| Window | Official Pressure (B) | Whale Sell (B) | Whale Buy (B) | Buyback USD | T+3 | T+7 | Interpretation |',
        '|---|---:|---:|---:|---:|---:|---:|---|',
    ])
    for window in event_windows:
        lines.append(
            f'| {window["label"]} ({window["date"]}) | {fmt_num(window["official_confirmed_pressure_B_window"], 3)} | {fmt_num(window["whale_proxy_sell_B_window"], 3)} | {fmt_num(window["whale_proxy_buy_B_window"], 3)} | {fmt_num(window["buyback_usd_window"], 0)} | {fmt_num(window["return_t_plus_3_pct"], 2)}% | {fmt_num(window["return_t_plus_7_pct"], 2)}% | {window["interpretation"]} |'
        )
    lines.extend([
        '',
        '## Whale Clusters',
        '',
    ])
    for whale in whale_clusters[:8]:
        lines.append(
            f'- {whale["label"]}: current {fmt_billions(whale["current_balance_B"])}; proxy net {fmt_billions(whale["proxy_net_B"])}; entry est. {whale["entry_date_estimate"] or "n/a"} @ ${fmt_num(whale["entry_price_estimate_usd"], 6)}.'
        )
    lines.extend([
        '',
        '## Cost Anchors',
        '',
        f'- Current price: ${fmt_num(cost_basis["current_price_usd"], 6)} on {cost_basis["current_price_date"]}.',
        f'- Versus claimed buyback average ${fmt_num(cost_basis["claimed_buyback_avg_price_usd"], 6)}: {fmt_num(cost_basis["distance_from_claimed_buyback_avg_pct"], 2)}%.',
        f'- Versus observable July direct-buy average ${fmt_num(cost_basis["observed_buyback_avg_price_usd"], 6)}: {fmt_num(cost_basis["distance_from_observed_buyback_avg_pct"], 2)}%.',
        '',
        '## Limits',
        '',
    ])
    for item in methodology['limitations']:
        lines.append(f'- {item}')
    lines.append('')

    REPORT_PATH.write_text('\n'.join(lines), encoding='utf-8')

    full_lines = [
        '# PUMP Full Price Attribution Report',
        '',
        f'- Generated at (UTC): {payload["metadata"]["generated_at"]}',
        f'- Token: {payload["metadata"]["token"]}',
        f'- Contract: `{payload["metadata"]["contract"]}`',
        f'- Price coverage in this report: {payload["metadata"]["price_range_start"]} to {payload["metadata"]["price_range_end"]}',
        '',
        '## Executive Summary',
        '',
        f'- Core answer: {payload["summary"]["headline"]}',
        f'- Claimed cumulative buyback reached ${fmt_num(buyback["claimed_cumulative_usd"], 0)}, with treasury still holding about {fmt_billions(buyback["treasury_hold_B"])} PUMP.',
        f'- Confirmed official exchange deposits alone reached {fmt_billions(official_rollup["confirmed_cex_pressure_B"])} PUMP, equal to {fmt_num(payload["summary"]["official_cex_pressure_pct_of_claimed_buyback_B"], 2)}% of the conservative claimed buyback token volume.',
        f'- Including confirmed Wintermute / DEX-style official release, market-facing official pressure reached {fmt_billions(official_rollup["confirmed_cex_pressure_B"] + official_rollup["confirmed_market_maker_or_dex_pressure_B"])} PUMP, or {fmt_num(payload["summary"]["official_total_market_pressure_pct_of_claimed_buyback_B"], 2)}% of the conservative claimed buyback token volume.',
        f'- The 59-holder sample was net accumulating overall: buys {fmt_billions(whale_proxy_rollup["total_buy_B"])} vs sells {fmt_billions(whale_proxy_rollup["total_sell_B"])}.',
        f'- Current price ${fmt_num(cost_basis["current_price_usd"], 6)} is {fmt_num(cost_basis["distance_from_claimed_buyback_avg_pct"], 2)}% below the claimed buyback average cost anchor and {fmt_num(cost_basis["distance_from_observed_buyback_avg_pct"], 2)}% below the observable July direct-buy average.',
        '',
        '## Direct Answer',
        '',
        '### Why did price fail to sustain upside despite buybacks?',
        '',
        f'1. A large part of buyback support was offset by confirmed official and official-linked market supply. The confirmed market-facing official pressure in this report is {fmt_billions(official_rollup["confirmed_cex_pressure_B"] + official_rollup["confirmed_market_maker_or_dex_pressure_B"])} PUMP.',
        '2. The most aggressive official sell windows in March 2026 were not matched by broad whale distribution in the 59-holder sample. That weakens the “whales caused the drop” explanation and strengthens the “official overhang dominated the tape” explanation for those windows.',
        '3. Buyback observability is incomplete after July 2025. The chain-forensic floor is real, but later cumulative buyback size mostly comes from treasury reconciliation and milestone claims, not direct execution traces. That makes the buyback program credible, but it also means the market may have seen the sell side more clearly than the buy side.',
        '4. The current market price sits materially below both buyback cost anchors used here. That implies buybacks did not succeed in lifting the effective market clearing level or eliminating overhead supply.',
        '',
        '## Buyback Verification Baseline',
        '',
        f'- Observable direct buyback floor: ${fmt_num(buyback["observable_direct_buy_usd"], 2)} on {fmt_billions(buyback["observable_direct_buy_pump_B"])} PUMP.',
        f'- Observable transfer-to-treasury floor: {fmt_billions(buyback["observable_transfer_to_treasury_pump_B"])} PUMP, implied ${fmt_num(buyback["observable_transfer_implied_usd"], 2)} using observable average price.',
        f'- Claimed conservative cumulative bought amount: {fmt_billions(buyback["claimed_conservative_bought_B"])} PUMP.',
        f'- Claimed cumulative average buyback price: ${fmt_num(buyback["claimed_avg_price_usd"], 6)}.',
        f'- Execution style observed on-chain: `{buyback["execution_style"]}`.',
        f'- Observability caveat: {buyback["observability_note"]}',
        '',
        '### Buyback Interpretation',
        '',
        '- The forensic layer proves buybacks existed and were mechanically executed.',
        '- The direct execution trace is a lower bound, not the full program total.',
        '- Treasury holdings and third-party cumulative milestones imply buybacks were economically meaningful, but not sufficient to absorb all official overhang.',
        '',
        '## Official Market Pressure',
        '',
        '| Entity | Type | Pressure Type | Confirmed Pressure (B) | Current Balance (B) | % of Conservative Buyback |',
        '|---|---|---|---:|---:|---:|',
    ]
    for entity in official_entities:
        full_lines.append(
            f'| {entity["label"]} | {entity["entity_type"]} | {entity["pressure_type"]} | {fmt_num(entity["confirmed_pressure_B"], 3)} | {fmt_num(entity["current_balance_B"], 3)} | {fmt_num(entity["share_of_conservative_buyback_pct"], 2)}% |'
        )
    full_lines.extend([
        '',
        '### Official Sell Ledger',
        '',
        '| Date | Entity | Flow Type | Exchange / Route | Amount (B) | USD |',
        '|---|---|---|---|---:|---:|',
    ])
    for event in sorted(official_sell_ledger, key=lambda x: (x['date'], x['event_id'])):
        full_lines.append(
            f'| {event["date"]} | {event["label"]} | {event["flow_type"]} | {event["exchange"] or "n/a"} | {fmt_num(event["amount_pump_B"], 4)} | {fmt_num(event["amount_usd"], 2)} |'
        )
    full_lines.extend([
        '',
        '### Official Pressure Interpretation',
        '',
        '- `Vault #5` is the single largest confirmed exchange-pressure source in this dataset.',
        '- `Investor Wallet #1` is the next largest confirmed exchange-pressure source via Kraken.',
        '- `Team Wallet #1` is not a clean CEX deposit story, but it is still market-facing supply through Wintermute and DEX routes.',
        '- `Official Allocation Multisig #2` is explicitly separated as non-sell distribution and should not be conflated with active dumping.',
        '',
        '## 59-Holder Whale Sample',
        '',
        f'- Coverage: {whale_proxy_rollup["coverage_addresses"]} whale-class addresses in the behavior profile layer.',
        f'- Aggregate proxy flow: buys {fmt_billions(whale_proxy_rollup["total_buy_B"])} vs sells {fmt_billions(whale_proxy_rollup["total_sell_B"])}; net {fmt_billions(whale_proxy_rollup["net_B"])}.',
        '',
        '### Top Accumulators',
        '',
        '| Label | Current Balance (B) | Proxy Buy (B) | Proxy Sell (B) | Proxy Net (B) |',
        '|---|---:|---:|---:|---:|',
    ])
    for row in whale_accumulators[:10]:
        full_lines.append(
            f'| {row["label"]} | {fmt_num(row["current_balance_B"], 3)} | {fmt_num(row["proxy_buy_B"], 3)} | {fmt_num(row["proxy_sell_B"], 3)} | {fmt_num(row["proxy_net_B"], 3)} |'
        )
    full_lines.extend([
        '',
        '### Top Distributors',
        '',
        '| Label | Current Balance (B) | Proxy Buy (B) | Proxy Sell (B) | Proxy Net (B) |',
        '|---|---:|---:|---:|---:|',
    ])
    for row in whale_distributors[:10]:
        full_lines.append(
            f'| {row["label"]} | {fmt_num(row["current_balance_B"], 3)} | {fmt_num(row["proxy_buy_B"], 3)} | {fmt_num(row["proxy_sell_B"], 3)} | {fmt_num(row["proxy_net_B"], 3)} |'
        )
    full_lines.extend([
        '',
        '### Whale Interpretation',
        '',
        '- The sample does not support a simple “all whales were dumping into buyback” explanation for March 2026.',
        '- Several large holders were still accumulating or at least not materially distributing during the official sell windows.',
        '- The single biggest proxy distributor is `Hyperunit: Hot Wallet`, but its label and balance pattern are more consistent with a market-making or inventory wallet than a clean directional dump wallet.',
        '',
        '## Event Window Analysis',
        '',
        '| Window | Official Pressure (B) | Whale Sell (B) | Whale Buy (B) | Whale Net (B) | Buyback USD | T+3 Return | T+7 Return |',
        '|---|---:|---:|---:|---:|---:|---:|---:|',
    ])
    for window in event_windows:
        full_lines.append(
            f'| {window["label"]} ({window["date"]}) | {fmt_num(window["official_confirmed_pressure_B_window"], 3)} | {fmt_num(window["whale_proxy_sell_B_window"], 3)} | {fmt_num(window["whale_proxy_buy_B_window"], 3)} | {fmt_num(window["whale_proxy_net_B_window"], 3)} | {fmt_num(window["buyback_usd_window"], 0)} | {fmt_num(window["return_t_plus_3_pct"], 2)}% | {fmt_num(window["return_t_plus_7_pct"], 2)}% |'
        )
    full_lines.extend([
        '',
        '### Event Window Readout',
        '',
    ])
    for window in event_windows:
        full_lines.append(f'- **{window["label"]} ({window["date"]})**: {window["interpretation"]}')
    full_lines.extend([
        '',
        '## Cost Basis & Overhang',
        '',
        f'- Current price: ${fmt_num(cost_basis["current_price_usd"], 6)} ({cost_basis["current_price_date"]}).',
        f'- Claimed cumulative buyback average: ${fmt_num(cost_basis["claimed_buyback_avg_price_usd"], 6)}.',
        f'- Observable July direct-buy average: ${fmt_num(cost_basis["observed_buyback_avg_price_usd"], 6)}.',
        f'- Distance vs claimed buyback average: {fmt_num(cost_basis["distance_from_claimed_buyback_avg_pct"], 2)}%.',
        f'- Distance vs observable July direct-buy average: {fmt_num(cost_basis["distance_from_observed_buyback_avg_pct"], 2)}%.',
        f'- Treasury marked value at current price: ${fmt_num(cost_basis["treasury_hold_value_usd_current"], 2)}.',
        '',
        '### Cost Interpretation',
        '',
        '- If buyback averages are even directionally correct, current price being far below them implies buybacks were not sufficient to reprice the market upward.',
        '- This is consistent with a market structure where official overhang and unlock-related fear dominate the perceived support value of buybacks.',
        '',
        '## Final Attribution',
        '',
        '### What is well supported',
        '',
        '- Buybacks were real and non-trivial.',
        '- Official and official-linked market-facing supply was also real and large.',
        '- The largest confirmed sell-side sources were official or official-linked wallets, not unlabeled whales.',
        '- During the major March 2026 windows, the 59-holder sample was more net bid than net offered.',
        '',
        '### What remains uncertain',
        '',
        '- The full post-July 2025 direct execution footprint of buybacks.',
        '- Realized cost basis for many unlabeled whales and custodial addresses.',
        '- Whether some unlabeled large holders are indirect official affiliates beyond the currently confirmed set.',
        '',
        '## Data Quality & Limits',
        '',
    ])
    for flag in payload['data_quality']['coverage_flags']:
        full_lines.append(f'- Coverage: {flag}')
    for conflict in payload['data_quality']['known_conflicts']:
        full_lines.append(f'- Known conflict: {conflict}')
    for item in methodology['limitations']:
        full_lines.append(f'- Limitation: {item}')
    full_lines.extend([
        '',
        '## Source Registry',
        '',
    ])
    for item in payload['source_registry']:
        full_lines.append(f'- `{item["id"]}`: `{item["path"]}` ({item["role"]})')
    full_lines.append('')

    FULL_REPORT_PATH.write_text('\n'.join(full_lines), encoding='utf-8')
    print(f'Wrote {OUTPUT_PATH.relative_to(BASE_DIR)}')
    print(f'Wrote {REPORT_PATH.relative_to(BASE_DIR)}')
    print(f'Wrote {FULL_REPORT_PATH.relative_to(BASE_DIR)}')


if __name__ == '__main__':
    main()
