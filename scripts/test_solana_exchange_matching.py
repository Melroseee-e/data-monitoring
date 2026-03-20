#!/usr/bin/env python3
"""
测试 Solana 地址匹配逻辑
验证修复后能否正确识别交易所转账
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

HELIUS_RPC = "https://mainnet.helius-rpc.com/?api-key={api_key}"

def load_exchange_lookup():
    """加载交易所地址配置"""
    exchanges_file = BASE_DIR / "data" / "exchange_addresses_normalized.json"
    with open(exchanges_file, 'r') as f:
        exchanges_data = json.load(f)

    # 构建 Solana lookup 表
    sol_lookup = {}
    for exchange_name, chains in exchanges_data.items():
        if 'solana' in chains:
            for addr in chains['solana']:
                # 关键：Solana 地址保持原样，不转小写
                sol_lookup[addr] = exchange_name

    return sol_lookup

def test_address_matching():
    """测试地址匹配逻辑"""
    print("=== 测试 1: 地址匹配逻辑 ===\n")

    sol_lookup = load_exchange_lookup()
    print(f"✓ 加载了 {len(sol_lookup)} 个 Solana 交易所地址\n")

    # 测试样例地址
    test_cases = [
        ("GsCY6n5RY7v3qcDAzGYcDShNzthngVs4So4b5nmVuqSN", "BingX"),
        ("43DbAvKxhXh1oSxkJSqGosNw3HpBnmsWiak6tB5wpecN", "Backpack"),
        ("HqqzZC5qsNKtZBrBsYvbXhzxUQaADSzkDaifHWe1GvEH", "Crypto.com"),
    ]

    print("测试用例:")
    for addr, expected_exchange in test_cases:
        # 错误方式（旧代码）
        addr_lower = addr.lower()
        match_old = sol_lookup.get(addr_lower)

        # 正确方式（修复后）
        match_new = sol_lookup.get(addr)

        print(f"\n地址: {addr[:20]}...")
        print(f"  预期交易所: {expected_exchange}")
        print(f"  旧方法 (.lower()): {match_old or '❌ 未匹配'}")
        print(f"  新方法 (保持原样): {match_new or '❌ 未匹配'}")

        if match_new == expected_exchange:
            print(f"  ✅ 修复后匹配成功")
        else:
            print(f"  ❌ 修复后仍未匹配")

def test_real_transaction():
    """测试真实的 PUMP 交易"""
    print("\n\n=== 测试 2: 真实 PUMP 交易 ===\n")

    api_key = os.environ.get("HELIUS_API_KEY")
    if not api_key:
        print("❌ 缺少 HELIUS_API_KEY")
        return

    # PUMP 代币地址
    pump_mint = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"

    # 获取最近的几个签名
    print(f"获取 PUMP 最近的交易签名...")
    rpc_url = HELIUS_RPC.format(api_key=api_key)

    try:
        response = requests.post(
            rpc_url,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [pump_mint, {"limit": 5}]
            },
            timeout=15
        )
        response.raise_for_status()
        result = response.json()

        if 'result' not in result or not result['result']:
            print("❌ 未找到交易")
            return

        signatures = result['result']
        print(f"✓ 找到 {len(signatures)} 个最近的交易\n")

        # 加载交易所 lookup
        sol_lookup = load_exchange_lookup()

        # 分析前 3 个交易
        for i, sig_info in enumerate(signatures[:3], 1):
            sig = sig_info['signature']
            print(f"\n--- 交易 {i}: {sig[:16]}... ---")

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
                print("  ⚠️  交易详情获取失败")
                continue

            tx = tx_result['result']

            # 分析 token 余额变化
            pre_balances = {b["accountIndex"]: b for b in tx["meta"].get("preTokenBalances", [])}
            post_balances = {b["accountIndex"]: b for b in tx["meta"].get("postTokenBalances", [])}

            print(f"  Token 余额变化: {len(post_balances)} 个账户")

            matched_exchanges = []

            for idx, post in post_balances.items():
                pre = pre_balances.get(idx, {})

                # 检查是否是 PUMP 代币
                if post.get("mint") != pump_mint:
                    continue

                pre_amount = int(pre.get("uiTokenAmount", {}).get("amount", 0))
                post_amount = int(post.get("uiTokenAmount", {}).get("amount", 0))

                if post_amount == pre_amount:
                    continue

                # 获取账户 owner
                account_owner = post.get("owner", "")

                # 测试两种方式
                match_old = sol_lookup.get(account_owner.lower())  # 旧方法
                match_new = sol_lookup.get(account_owner)  # 新方法

                if match_new:
                    direction = "流入" if post_amount > pre_amount else "流出"
                    amount = abs(post_amount - pre_amount) / 1e9  # PUMP decimals = 9
                    matched_exchanges.append((match_new, direction, amount))

                    print(f"  ✅ 匹配到交易所: {match_new}")
                    print(f"     方向: {direction}")
                    print(f"     数量: {amount:,.2f} PUMP")
                    print(f"     账户: {account_owner[:20]}...")
                    print(f"     旧方法匹配: {match_old or '❌'}")

            if not matched_exchanges:
                print(f"  ⚠️  未匹配到交易所转账（可能是用户间转账）")

    except Exception as e:
        print(f"❌ 错误: {e}")

def main():
    print("=" * 60)
    print("Solana 交易所地址匹配测试")
    print("=" * 60)
    print()

    # 测试 1: 地址匹配逻辑
    test_address_matching()

    # 测试 2: 真实交易
    test_real_transaction()

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
