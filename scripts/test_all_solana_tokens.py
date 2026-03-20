#!/usr/bin/env python3
"""
全面测试 PUMP/BIRB/SKR 三个代币的交易所匹配
分析最近 100 笔交易，统计匹配到的交易所
"""

import json
import os
from pathlib import Path
from collections import defaultdict
import requests
from dotenv import load_dotenv
import time

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

HELIUS_RPC = "https://mainnet.helius-rpc.com/?api-key={api_key}"

# 三个 Solana 代币配置
TOKENS = {
    "PUMP": {
        "mint": "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn",
        "decimals": 9
    },
    "BIRB": {
        "mint": "G7vQWurMkMMm2dU3iZpXYFTHT9Biio4F4gZCrwFpKNwG",
        "decimals": 9
    },
    "SKR": {
        "mint": "SKRbvo6Gf7GondiT3BbTfuRDPqLWei4j2Qy2NPGZhW3",
        "decimals": 9
    }
}

def load_exchange_lookup():
    """加载交易所地址配置"""
    exchanges_file = BASE_DIR / "data" / "exchange_addresses_normalized.json"
    with open(exchanges_file, 'r') as f:
        exchanges_data = json.load(f)

    sol_lookup = {}
    for exchange_name, chains in exchanges_data.items():
        if 'solana' in chains:
            for addr in chains['solana']:
                sol_lookup[addr] = exchange_name

    return sol_lookup

def analyze_token_transactions(token_name, token_config, sol_lookup, api_key, limit=100):
    """分析指定代币的交易"""
    print(f"\n{'='*60}")
    print(f"分析 {token_name} 代币")
    print(f"{'='*60}")

    mint = token_config["mint"]
    decimals = token_config["decimals"]
    rpc_url = HELIUS_RPC.format(api_key=api_key)

    # 获取最近的签名
    print(f"获取最近 {limit} 笔交易...")
    try:
        response = requests.post(
            rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [mint, {"limit": limit}]
            },
            timeout=15
        )
        response.raise_for_status()
        result = response.json()

        if 'result' not in result or not result['result']:
            print(f"❌ 未找到交易")
            return {}

        signatures = result['result']
        print(f"✓ 找到 {len(signatures)} 笔交易\n")

    except Exception as e:
        print(f"❌ 获取签名失败: {e}")
        return {}

    # 统计数据
    stats = {
        "total_transactions": len(signatures),
        "transactions_with_exchanges": 0,
        "exchange_matches": defaultdict(lambda: {"inflow": 0, "outflow": 0, "count": 0}),
        "old_method_matches": 0,
        "new_method_matches": 0
    }

    # 分析每笔交易
    print(f"分析交易中...")
    for i, sig_info in enumerate(signatures, 1):
        if i % 20 == 0:
            print(f"  进度: {i}/{len(signatures)}")

        sig = sig_info['signature']

        try:
            # 获取交易详情
            tx_response = requests.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTransaction",
                    "params": [
                        sig,
                        {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
                    ]
                },
                timeout=15
            )
            tx_response.raise_for_status()
            tx_result = tx_response.json()

            if 'result' not in tx_result or not tx_result['result']:
                continue

            tx = tx_result['result']

            # 分析 token 余额变化
            pre_balances = {b["accountIndex"]: b for b in tx["meta"].get("preTokenBalances", [])}
            post_balances = {b["accountIndex"]: b for b in tx["meta"].get("postTokenBalances", [])}

            found_exchange = False

            for idx, post in post_balances.items():
                # 只处理目标代币
                if post.get("mint") != mint:
                    continue

                pre = pre_balances.get(idx, {})
                pre_amount = int(pre.get("uiTokenAmount", {}).get("amount", 0))
                post_amount = int(post.get("uiTokenAmount", {}).get("amount", 0))

                if post_amount == pre_amount:
                    continue

                account_owner = post.get("owner", "")

                # 测试旧方法和新方法
                match_old = sol_lookup.get(account_owner.lower())
                match_new = sol_lookup.get(account_owner)

                if match_old:
                    stats["old_method_matches"] += 1

                if match_new:
                    stats["new_method_matches"] += 1
                    found_exchange = True

                    direction = "inflow" if post_amount > pre_amount else "outflow"
                    amount = abs(post_amount - pre_amount) / (10 ** decimals)

                    stats["exchange_matches"][match_new][direction] += amount
                    stats["exchange_matches"][match_new]["count"] += 1

            if found_exchange:
                stats["transactions_with_exchanges"] += 1

            # 避免 API 速率限制
            time.sleep(0.1)

        except Exception as e:
            if "429" in str(e):
                print(f"  ⚠️  速率限制，等待 2 秒...")
                time.sleep(2)
            continue

    return stats

def main():
    print("=" * 60)
    print("Solana 代币交易所匹配全面测试")
    print("=" * 60)

    api_key = os.environ.get("HELIUS_API_KEY")
    if not api_key:
        print("❌ 缺少 HELIUS_API_KEY")
        return

    # 加载交易所配置
    sol_lookup = load_exchange_lookup()
    print(f"\n✓ 加载了 {len(sol_lookup)} 个 Solana 交易所地址")
    print(f"  交易所列表: {', '.join(sorted(set(sol_lookup.values())))}\n")

    # 测试每个代币
    all_results = {}

    for token_name, token_config in TOKENS.items():
        stats = analyze_token_transactions(
            token_name,
            token_config,
            sol_lookup,
            api_key,
            limit=100
        )
        all_results[token_name] = stats

    # 汇总报告
    print(f"\n\n{'='*60}")
    print("测试结果汇总")
    print(f"{'='*60}\n")

    for token_name, stats in all_results.items():
        if not stats:
            continue

        print(f"\n{token_name}:")
        print(f"  总交易数: {stats['total_transactions']}")
        print(f"  涉及交易所的交易: {stats['transactions_with_exchanges']}")
        print(f"  旧方法匹配次数: {stats['old_method_matches']} ❌")
        print(f"  新方法匹配次数: {stats['new_method_matches']} ✅")

        if stats['exchange_matches']:
            print(f"\n  匹配到的交易所 ({len(stats['exchange_matches'])} 个):")
            for exchange, data in sorted(stats['exchange_matches'].items()):
                print(f"    • {exchange}:")
                print(f"        流入: {data['inflow']:,.2f} {token_name}")
                print(f"        流出: {data['outflow']:,.2f} {token_name}")
                print(f"        交易次数: {data['count']}")
        else:
            print(f"  ⚠️  未匹配到任何交易所（可能需要分析更多交易）")

    # 总结
    print(f"\n\n{'='*60}")
    print("结论")
    print(f"{'='*60}\n")

    total_old = sum(s.get('old_method_matches', 0) for s in all_results.values())
    total_new = sum(s.get('new_method_matches', 0) for s in all_results.values())

    print(f"旧方法 (.lower()) 总匹配: {total_old} 次 ❌")
    print(f"新方法 (保持原样) 总匹配: {total_new} 次 ✅")
    print(f"\n修复效果: 从 {total_old} 次提升到 {total_new} 次")

    if total_new > 0:
        print(f"\n✅ 修复方法有效！能够正确识别 Solana 交易所转账")
    else:
        print(f"\n⚠️  未找到交易所转账，可能需要分析更多历史数据")

if __name__ == "__main__":
    main()
