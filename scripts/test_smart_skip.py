#!/usr/bin/env python3
"""
测试智能跳过方案的效果
分析 PUMP 交易中有多少比例涉及交易所
"""

import json
import os
from pathlib import Path
import requests
from dotenv import load_dotenv
import time

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

HELIUS_RPC = "https://mainnet.helius-rpc.com/?api-key={api_key}"
PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"

def load_exchange_addresses():
    """加载所有 Solana 交易所地址"""
    exchanges_file = BASE_DIR / "data" / "exchange_addresses_normalized.json"
    with open(exchanges_file, 'r') as f:
        exchanges_data = json.load(f)

    addresses = set()
    for exchange_name, chains in exchanges_data.items():
        if 'solana' in chains:
            addresses.update(chains['solana'])

    return addresses

def test_smart_skip(api_key, sample_size=1000):
    """测试智能跳过方案"""
    print(f"测试智能跳过方案（样本: {sample_size} 笔交易）\n")

    rpc_url = HELIUS_RPC.format(api_key=api_key)
    exchange_addresses = load_exchange_addresses()

    print(f"✓ 加载了 {len(exchange_addresses)} 个交易所地址\n")

    # 获取签名
    print(f"获取 {sample_size} 个签名...")
    response = requests.post(
        rpc_url,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getSignaturesForAddress",
            "params": [PUMP_MINT, {"limit": sample_size}]
        },
        timeout=15
    )
    signatures = response.json()['result']
    print(f"✓ 获取了 {len(signatures)} 个签名\n")

    # 统计
    stats = {
        "total": len(signatures),
        "with_exchange": 0,
        "without_exchange": 0,
        "parse_time_with_check": 0,
        "parse_time_without_check": 0
    }

    print("分析交易...")

    for i, sig_info in enumerate(signatures, 1):
        if i % 100 == 0:
            print(f"  进度: {i}/{len(signatures)}")

        sig = sig_info['signature']

        try:
            # 方法 1: 先获取账户列表（智能跳过）
            start = time.time()

            # 获取交易（只要 accountKeys）
            tx_response = requests.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTransaction",
                    "params": [sig, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
                },
                timeout=15
            )
            tx_result = tx_response.json()

            if 'result' not in tx_result or not tx_result['result']:
                continue

            tx = tx_result['result']
            account_keys = tx['transaction']['message'].get('accountKeys', [])

            # 检查是否涉及交易所
            has_exchange = any(addr in exchange_addresses for addr in account_keys)

            check_time = time.time() - start
            stats["parse_time_with_check"] += check_time

            if has_exchange:
                stats["with_exchange"] += 1
                # 如果涉及交易所，才获取详细数据（jsonParsed）
                # 这里模拟详细解析的时间
                stats["parse_time_without_check"] += check_time + 0.5  # 假设详细解析多 0.5s
            else:
                stats["without_exchange"] += 1
                # 不涉及交易所，跳过详细解析
                stats["parse_time_without_check"] += check_time + 0.5

            time.sleep(0.05)  # 避免 rate limit

        except Exception as e:
            if "429" in str(e):
                time.sleep(2)
            continue

    return stats

def main():
    print("=" * 60)
    print("智能跳过方案效果测试")
    print("=" * 60)
    print()

    api_key = os.environ.get("HELIUS_API_KEY")
    if not api_key:
        print("❌ 缺少 HELIUS_API_KEY")
        return

    # 测试 1000 笔交易
    stats = test_smart_skip(api_key, sample_size=1000)

    # 结果分析
    print(f"\n\n{'='*60}")
    print("测试结果")
    print(f"{'='*60}\n")

    print(f"总交易数: {stats['total']}")
    print(f"涉及交易所: {stats['with_exchange']} ({stats['with_exchange']/stats['total']*100:.1f}%)")
    print(f"不涉及交易所: {stats['without_exchange']} ({stats['without_exchange']/stats['total']*100:.1f}%)")

    # 时间估算
    print(f"\n{'='*60}")
    print("时间估算（PUMP 165,796 笔交易）")
    print(f"{'='*60}\n")

    exchange_ratio = stats['with_exchange'] / stats['total']

    # 当前方法：处理所有交易
    current_time = 56  # 小时

    # 智能跳过：只处理涉及交易所的交易
    optimized_time = current_time * exchange_ratio

    print(f"当前方法（处理所有交易）: {current_time} 小时")
    print(f"智能跳过（只处理 {exchange_ratio*100:.1f}%）: {optimized_time:.1f} 小时")
    print(f"\n⚡ 节省时间: {current_time - optimized_time:.1f} 小时 ({(1-exchange_ratio)*100:.1f}%)")

    # 三个代币总时间
    print(f"\n{'='*60}")
    print("三个代币总时间对比")
    print(f"{'='*60}\n")

    print(f"当前方法:")
    print(f"  PUMP: 56 小时")
    print(f"  BIRB: 18 小时")
    print(f"  SKR: 11 小时")
    print(f"  总计（串行）: 85 小时")
    print(f"  总计（并行）: 56 小时")

    print(f"\n智能跳过 + 并行:")
    print(f"  PUMP: {56 * exchange_ratio:.1f} 小时")
    print(f"  BIRB: {18 * exchange_ratio:.1f} 小时")
    print(f"  SKR: {11 * exchange_ratio:.1f} 小时")
    print(f"  总计（并行）: {56 * exchange_ratio:.1f} 小时")

    print(f"\n✅ 推荐使用智能跳过方案")

if __name__ == "__main__":
    main()
