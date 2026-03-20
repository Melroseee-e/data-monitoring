#!/usr/bin/env python3
"""
深度审核 PUMP 回购地址
分析 G8CcfRff 和 3vkpy 的链上交易关系
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
HELIUS_RPC = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
PUMP_MINT = "pumpCmXqMfrsAkQ5r49WcJnRayYRqmXz6ae8H7H9Dfn"

# 待验证的地址
BUYBACK_ADDR = "3vkpy5YHqnqJTnA5doWTpcgKyZiYsaXYzYM9wm8s3WTi"
TREASURY_ADDR = "G8CcfRffqZWHSAQJXLDfwbAkGE95SddUqVXnTrL4kqjm"

def rpc_call(method, params):
    """RPC 调用"""
    response = requests.post(
        HELIUS_RPC,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=30
    )
    return response.json().get("result")

def get_recent_transactions(address, limit=100):
    """获取最近的交易"""
    return rpc_call("getSignaturesForAddress", [address, {"limit": limit}])

def get_transaction_details(signature):
    """获取交易详情"""
    return rpc_call("getTransaction", [
        signature,
        {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
    ])

def analyze_spl_transfers(tx, target_mint=PUMP_MINT):
    """分析 SPL 代币转账"""
    if not tx or not tx.get("meta"):
        return []

    transfers = []
    pre_balances = {
        b["accountIndex"]: b
        for b in tx["meta"].get("preTokenBalances", [])
        if b.get("mint") == target_mint
    }
    post_balances = {
        b["accountIndex"]: b
        for b in tx["meta"].get("postTokenBalances", [])
        if b.get("mint") == target_mint
    }

    account_keys = tx["transaction"]["message"]["accountKeys"]
    all_indices = set(pre_balances.keys()) | set(post_balances.keys())

    for idx in all_indices:
        pre = pre_balances.get(idx, {}).get("uiTokenAmount", {}).get("uiAmount", 0)
        post = post_balances.get(idx, {}).get("uiTokenAmount", {}).get("uiAmount", 0)
        change = post - pre

        if abs(change) > 0:
            owner = (pre_balances.get(idx) or post_balances.get(idx)).get("owner")
            transfers.append({
                "owner": owner,
                "change": change,
                "account": account_keys[idx] if idx < len(account_keys) else None
            })

    return transfers

def main():
    print("=" * 100)
    print("PUMP 回购地址深度审核 - 链上数据分析".center(100))
    print("=" * 100)

    # 1. 分析回购钱包
    print(f"\n【信息源 1: 链上交易分析 - Helius RPC】")
    print(f"\n分析回购钱包: {BUYBACK_ADDR}")
    print("─" * 100)

    buyback_sigs = get_recent_transactions(BUYBACK_ADDR, 50)
    print(f"获取最近 {len(buyback_sigs)} 笔交易")

    # 分析转出目标
    transfer_destinations = {}
    buyback_purchases = 0
    transfers_to_treasury = 0

    for i, sig_info in enumerate(buyback_sigs[:20], 1):  # 分析前 20 笔
        sig = sig_info["signature"]
        tx = get_transaction_details(sig)

        if not tx:
            continue

        transfers = analyze_spl_transfers(tx)

        # 查找从回购钱包转出的交易
        for transfer in transfers:
            if transfer["owner"] == BUYBACK_ADDR and transfer["change"] < 0:
                # 找到接收方
                for t in transfers:
                    if t["change"] > 0:
                        dest = t["owner"]
                        amount = abs(transfer["change"])
                        transfer_destinations[dest] = transfer_destinations.get(dest, 0) + amount

                        if dest == TREASURY_ADDR:
                            transfers_to_treasury += 1
                            print(f"  ✅ 交易 #{i}: 转账 {amount:,.0f} PUMP → 金库 {dest[:8]}...")

            # 检查是否是回购交易（PUMP 增加）
            if transfer["owner"] == BUYBACK_ADDR and transfer["change"] > 0:
                buyback_purchases += 1

    print(f"\n回购钱包行为分析:")
    print(f"  - 回购交易（PUMP 增加）: {buyback_purchases} 笔")
    print(f"  - 转账到金库: {transfers_to_treasury} 笔")
    print(f"\n主要转账目标:")
    for dest, total in sorted(transfer_destinations.items(), key=lambda x: x[1], reverse=True)[:5]:
        is_treasury = "✅ 金库地址" if dest == TREASURY_ADDR else ""
        print(f"  - {dest[:8]}...{dest[-8:]}: {total:,.0f} PUMP {is_treasury}")

    # 2. 分析金库钱包
    print(f"\n\n分析金库钱包: {TREASURY_ADDR}")
    print("─" * 100)

    treasury_sigs = get_recent_transactions(TREASURY_ADDR, 50)
    print(f"获取最近 {len(treasury_sigs)} 笔交易")

    # 分析转入来源
    transfer_sources = {}
    received_from_buyback = 0

    for i, sig_info in enumerate(treasury_sigs[:20], 1):
        sig = sig_info["signature"]
        tx = get_transaction_details(sig)

        if not tx:
            continue

        transfers = analyze_spl_transfers(tx)

        # 查找转入金库的交易
        for transfer in transfers:
            if transfer["owner"] == TREASURY_ADDR and transfer["change"] > 0:
                # 找到发送方
                for t in transfers:
                    if t["change"] < 0:
                        source = t["owner"]
                        amount = transfer["change"]
                        transfer_sources[source] = transfer_sources.get(source, 0) + amount

                        if source == BUYBACK_ADDR:
                            received_from_buyback += 1
                            print(f"  ✅ 交易 #{i}: 接收 {amount:,.0f} PUMP ← 回购钱包 {source[:8]}...")

    print(f"\n金库钱包行为分析:")
    print(f"  - 从回购钱包接收: {received_from_buyback} 笔")
    print(f"\n主要转入来源:")
    for source, total in sorted(transfer_sources.items(), key=lambda x: x[1], reverse=True)[:5]:
        is_buyback = "✅ 回购钱包" if source == BUYBACK_ADDR else ""
        print(f"  - {source[:8]}...{source[-8:]}: {total:,.0f} PUMP {is_buyback}")

    # 3. 结论
    print(f"\n\n{'=' * 100}")
    print("链上数据结论".center(100))
    print("=" * 100)

    print(f"\n✅ 回购钱包: {BUYBACK_ADDR}")
    print(f"   - 功能: 执行回购（从 DEX 购买 PUMP）")
    print(f"   - 行为: 将回购的代币转移到金库")
    print(f"   - 验证: 发现 {transfers_to_treasury} 笔转账到金库")

    print(f"\n✅ 金库钱包: {TREASURY_ADDR}")
    print(f"   - 功能: 接收并存储回购的代币")
    print(f"   - 行为: 从回购钱包接收代币")
    print(f"   - 验证: 发现 {received_from_buyback} 笔来自回购钱包的转账")

    if received_from_buyback > 0 and transfers_to_treasury > 0:
        print(f"\n🎯 结论: G8CcfRff 是【金库地址】，不是回购地址")
        print(f"         3vkpy 是【回购地址】，负责执行回购并转移到金库")
    else:
        print(f"\n⚠️  警告: 未在最近交易中发现明确的转账关系")

    print("\n" + "=" * 100)

if __name__ == "__main__":
    main()
