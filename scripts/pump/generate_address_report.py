#!/usr/bin/env python3
"""
生成 PUMP 代币关键地址详细报告
包括：官方地址、回购地址、大户地址
"""

import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parents[2]
ADDRESSES_FILE = BASE_DIR / "data" / "pump" / "core" / "pump_addresses.json"
HOLDERS_FILE = BASE_DIR / "data" / "pump" / "raw" / "pump_top_holders_with_balances.json"

TOTAL_SUPPLY = 1_000_000_000_000  # 1 trillion

def format_balance(balance):
    """格式化余额显示"""
    billions = balance / 1_000_000_000
    percentage = (balance / TOTAL_SUPPLY) * 100
    return f"{balance:>18,.0f} PUMP ({billions:>7.2f}B, {percentage:>5.2f}%)"

def solscan_link(address):
    """生成 Solscan 链接"""
    return f"https://solscan.io/account/{address}"

def main():
    # 加载数据
    with open(ADDRESSES_FILE, 'r') as f:
        addresses_data = json.load(f)

    with open(HOLDERS_FILE, 'r') as f:
        holders_data = json.load(f)

    addresses = addresses_data.get("addresses", {})
    holders = holders_data.get("holders_with_balance", [])

    print("=" * 100)
    print("PUMP 代币关键地址详细报告".center(100))
    print("=" * 100)
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"总供应量: {TOTAL_SUPPLY:,} PUMP (1 万亿)")
    print("=" * 100)

    # 1. 回购地址
    print("\n" + "🔥 回购地址 (Buyback Wallet)".center(100, "="))
    buyback_addr = "3vkpy5YHqnqJTnA5doWTpcgKyZiYsaXYzYM9wm8s3WTi"
    if buyback_addr in addresses:
        info = addresses[buyback_addr]
        print(f"\n地址: {buyback_addr}")
        print(f"标签: {info.get('label', 'N/A')}")
        print(f"余额: {format_balance(info.get('balance', 0))}")
        print(f"状态: {'✅ 已验证' if info.get('verified') else '❌ 未验证'}")
        print(f"来源: {info.get('source', 'N/A')}")
        print(f"说明: {info.get('notes', 'N/A')}")
        print(f"Solscan: {solscan_link(buyback_addr)}")
        print(f"\n💡 关键信息:")
        print(f"   - 累计回购: $310-328M (截至 2026-03)")
        print(f"   - 供应移除: 27-30% 流通供应")
        print(f"   - 当前余额极低，说明代币已转至金库销毁")

    # 2. 官方金库地址
    print("\n" + "🏦 官方金库地址 (Official Treasury Vaults)".center(100, "="))
    treasury_addrs = addresses_data.get("address_groups", {}).get("treasury", [])

    treasury_total = 0
    for i, addr in enumerate(treasury_addrs, 1):
        if addr in addresses:
            info = addresses[addr]
            balance = info.get('balance', 0)
            treasury_total += balance

            print(f"\n【金库 #{i}】")
            print(f"地址: {addr}")
            print(f"标签: {info.get('label', 'N/A')}")
            print(f"余额: {format_balance(balance)}")
            print(f"状态: {'✅ 已验证' if info.get('verified') else '❌ 未验证'}")
            print(f"BubbleMaps 标签: {info.get('bubblemaps_label', 'N/A')}")
            print(f"说明: {info.get('notes', 'N/A')}")
            print(f"Solscan: {solscan_link(addr)}")

    print(f"\n{'─' * 100}")
    print(f"官方金库合计: {format_balance(treasury_total)}")
    print(f"🚨 警告: 官方控制 {(treasury_total/TOTAL_SUPPLY)*100:.1f}% 总供应，远超声称的 20% 团队分配！")

    # 3. 团队/鲸鱼地址
    print("\n" + "🐋 已知团队/鲸鱼地址 (Known Team/Whale Wallets)".center(100, "="))

    # 团队钱包
    team_addrs = addresses_data.get("address_groups", {}).get("team", [])
    for addr in team_addrs:
        if addr in addresses:
            info = addresses[addr]
            print(f"\n【团队钱包】")
            print(f"地址: {addr}")
            print(f"标签: {info.get('label', 'N/A')}")
            print(f"说明: {info.get('notes', 'N/A')}")
            print(f"状态: {'✅ 已验证' if info.get('verified') else '❌ 未验证'}")
            if 'selling_activity' in info:
                print(f"出售记录:")
                for sale in info['selling_activity']:
                    print(f"   - {sale.get('date')}: {sale.get('amount', 0):,.0f} PUMP (${sale.get('value_usd', 0):,.0f})")

    # 鲸鱼钱包
    whale_addrs = addresses_data.get("address_groups", {}).get("whales", [])
    for addr in whale_addrs:
        if addr in addresses:
            info = addresses[addr]
            print(f"\n【鲸鱼/分发钱包】")
            print(f"地址: {addr}")
            print(f"标签: {info.get('label', 'N/A')}")
            print(f"余额: {format_balance(info.get('balance', 0))}")
            print(f"说明: {info.get('notes', 'N/A')}")
            print(f"Solscan: {solscan_link(addr)}")
            if 'major_transfers' in info:
                print(f"主要转账:")
                for transfer in info['major_transfers']:
                    print(f"   - {transfer.get('date')}: {transfer.get('amount', 0):,.0f} PUMP → {transfer.get('destination')}")

    # 4. Top 20 大户地址
    print("\n" + "📊 Top 20 大户地址 (Top 20 Holders by Balance)".center(100, "="))
    print(f"\n{'排名':<6} {'地址':<45} {'余额 (PUMP)':<25} {'标签'}")
    print("─" * 100)

    for i, holder in enumerate(holders[:20], 1):
        addr = holder['address']
        balance = holder['balance']
        label = holder.get('label', 'No label')

        # 检查是否是已知地址
        marker = ""
        if addr in addresses:
            marker = "✅"

        print(f"#{i:<5} {marker} {addr:<43} {format_balance(balance):<25} {label}")

    # 5. 可疑的无标签大户
    print("\n" + "⚠️  可疑的无标签大户 (Suspicious Unlabeled Whales)".center(100, "="))
    print("这些地址持有大量 PUMP 但没有公开标签，可能是隐藏的团队/投资者钱包\n")

    unlabeled_whales = [h for h in holders if not h.get('label') and h['balance'] > 5_000_000_000]

    print(f"{'排名':<6} {'地址':<45} {'余额 (PUMP)':<25} {'风险等级'}")
    print("─" * 100)

    for holder in unlabeled_whales[:15]:
        addr = holder['address']
        balance = holder['balance']
        rank = holder['rank']

        # 风险评级
        if balance > 20_000_000_000:
            risk = "🔴 高风险"
        elif balance > 10_000_000_000:
            risk = "🟡 中风险"
        else:
            risk = "🟢 低风险"

        print(f"#{rank:<5} {addr:<45} {format_balance(balance):<25} {risk}")
        print(f"       Solscan: {solscan_link(addr)}")

    # 6. 统计摘要
    print("\n" + "📈 统计摘要 (Summary Statistics)".center(100, "="))

    total_top20 = sum(h['balance'] for h in holders[:20])
    total_top50 = sum(h['balance'] for h in holders)

    print(f"\n官方控制:")
    print(f"  - 回购钱包: {addresses.get(buyback_addr, {}).get('balance', 0):,.0f} PUMP")
    print(f"  - 金库总计: {treasury_total:,.0f} PUMP ({(treasury_total/TOTAL_SUPPLY)*100:.2f}%)")
    print(f"\n大户分布:")
    print(f"  - Top 20 持有: {total_top20:,.0f} PUMP ({(total_top20/TOTAL_SUPPLY)*100:.2f}%)")
    print(f"  - Top 50 持有: {total_top50:,.0f} PUMP ({(total_top50/TOTAL_SUPPLY)*100:.2f}%)")
    print(f"  - >1B PUMP 持有者: {sum(1 for h in holders if h['balance'] > 1_000_000_000)} 个")
    print(f"\n风险指标:")
    print(f"  - 官方控制比例: {(treasury_total/TOTAL_SUPPLY)*100:.1f}% (声称 20%)")
    print(f"  - 集中度: {'🔴 极高' if (treasury_total/TOTAL_SUPPLY) > 0.5 else '🟡 高'}")
    print(f"  - 无标签大户: {len(unlabeled_whales)} 个")

    print("\n" + "=" * 100)
    print("报告结束".center(100))
    print("=" * 100)

if __name__ == "__main__":
    main()
