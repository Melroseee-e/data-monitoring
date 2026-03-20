#!/usr/bin/env python3
"""
验证智能跳过是否会漏掉数据
对比 accountKeys 预筛选 vs 完整解析
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

def load_exchange_data():
    """加载交易所配置"""
    exchanges_file = BASE_DIR / "data" / "exchange_addresses_normalized.json"
    with open(exchanges_file, 'r') as f:
        exchanges_data = json.load(f)

    # Owner 地址集合
    owner_addresses = set()
    # Owner -> 交易所名称映射
    owner_to_exchange = {}

    for exchange_name, chains in exchanges_data.items():
        if 'solana' in chains:
            for addr in chains['solana']:
                owner_addresses.add(addr)
                owner_to_exchange[addr] = exchange_name

    return owner_addresses, owner_to_exchange

def test_filtering_accuracy(api_key, sample_size=200):
    """测试过滤准确性"""
    print(f"验证智能跳过准确性（样本: {sample_size} 笔）\n")

    rpc_url = HELIUS_RPC.format(api_key=api_key)
    owner_addresses, owner_to_exchange = load_exchange_data()

    print(f"✓ 加载了 {len(owner_addresses)} 个交易所 Owner 地址\n")

    # 获取签名
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
    results = {
        "total": 0,
        "method_a_match": 0,  # accountKeys 匹配
        "method_b_match": 0,  # postTokenBalances 匹配
        "both_match": 0,      # 两种方法都匹配
        "only_a": 0,          # 只有 A 匹配
        "only_b": 0,          # 只有 B 匹配（漏掉的）
        "examples": []
    }

    print("分析交易...")

    for i, sig_info in enumerate(signatures, 1):
        if i % 50 == 0:
            print(f"  进度: {i}/{len(signatures)}")

        sig = sig_info['signature']

        try:
            # 获取完整交易
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
            tx_result = tx_response.json()

            if 'result' not in tx_result or not tx_result['result']:
                continue

            tx = tx_result['result']
            results["total"] += 1

            # 方法 A: 检查 accountKeys
            account_keys = tx['transaction']['message'].get('accountKeys', [])
            # 提取地址（可能是对象或字符串）
            if account_keys and isinstance(account_keys[0], dict):
                account_addrs = [acc['pubkey'] for acc in account_keys]
            else:
                account_addrs = account_keys

            method_a_match = any(addr in owner_addresses for addr in account_addrs)

            # 方法 B: 检查 postTokenBalances
            post_balances = tx["meta"].get("postTokenBalances", [])
            method_b_exchanges = set()

            for post in post_balances:
                if post.get("mint") != PUMP_MINT:
                    continue

                owner = post.get("owner", "")
                if owner in owner_addresses:
                    method_b_exchanges.add(owner_to_exchange[owner])

            method_b_match = len(method_b_exchanges) > 0

            # 统计
            if method_a_match:
                results["method_a_match"] += 1
            if method_b_match:
                results["method_b_match"] += 1

            if method_a_match and method_b_match:
                results["both_match"] += 1
            elif method_a_match and not method_b_match:
                results["only_a"] += 1
            elif not method_a_match and method_b_match:
                results["only_b"] += 1
                # 记录漏掉的案例
                if len(results["examples"]) < 3:
                    results["examples"].append({
                        "sig": sig[:16] + "...",
                        "exchanges": list(method_b_exchanges),
                        "account_keys_count": len(account_addrs)
                    })

            time.sleep(0.05)

        except Exception as e:
            if "429" in str(e):
                time.sleep(2)
            continue

    return results

def main():
    print("=" * 60)
    print("智能跳过准确性验证")
    print("=" * 60)
    print()

    api_key = os.environ.get("HELIUS_API_KEY")
    if not api_key:
        print("❌ 缺少 HELIUS_API_KEY")
        return

    results = test_filtering_accuracy(api_key, sample_size=200)

    # 结果分析
    print(f"\n\n{'='*60}")
    print("验证结果")
    print(f"{'='*60}\n")

    print(f"总交易数: {results['total']}")
    print(f"\n方法 A (accountKeys 预筛选): {results['method_a_match']} 笔")
    print(f"方法 B (postTokenBalances 完整解析): {results['method_b_match']} 笔")
    print(f"\n两种方法都匹配: {results['both_match']} 笔 ✅")
    print(f"只有 A 匹配: {results['only_a']} 笔")
    print(f"只有 B 匹配: {results['only_b']} 笔 ⚠️")

    if results['only_b'] > 0:
        print(f"\n{'='*60}")
        print("⚠️  警告：智能跳过会漏掉数据！")
        print(f"{'='*60}\n")

        print(f"漏掉的交易数: {results['only_b']} / {results['method_b_match']}")
        print(f"漏掉比例: {results['only_b']/results['method_b_match']*100:.1f}%")

        if results['examples']:
            print(f"\n漏掉的案例:")
            for ex in results['examples']:
                print(f"  • 交易: {ex['sig']}")
                print(f"    交易所: {', '.join(ex['exchanges'])}")
                print(f"    accountKeys 数量: {ex['account_keys_count']}")

        print(f"\n❌ 不建议使用智能跳过方案")
        print(f"   原因: accountKeys 不包含 token account 的 owner")

    else:
        print(f"\n{'='*60}")
        print("✅ 智能跳过安全！")
        print(f"{'='*60}\n")

        if results['method_b_match'] > 0:
            print(f"所有 {results['method_b_match']} 笔交易所转账都能被预筛选捕获")
            print(f"\n✅ 可以安全使用智能跳过方案")
            print(f"   预计节省时间: {(1 - results['method_b_match']/results['total'])*100:.1f}%")
        else:
            print(f"样本中没有交易所转账，无法验证")

if __name__ == "__main__":
    main()
