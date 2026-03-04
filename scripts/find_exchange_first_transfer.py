#!/usr/bin/env python3
"""
查询代币在交易所的第一笔交易时间
通过查询交易所地址与代币合约的第一次交互来确定真实的流通开始时间
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TOKENS_FILE = BASE_DIR / "data" / "tokens.json"
EXCHANGES_FILE = BASE_DIR / "data" / "exchange_addresses_normalized.json"

ETHERSCAN_API = "https://api.etherscan.io/v2/api"
BSCSCAN_API = "https://api.bscscan.com/api"

def get_env(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        print(f"WARNING: {name} not set", file=sys.stderr)
    return val

def get_first_exchange_transfer_eth(contract: str, exchange_addresses: list, api_key: str):
    """查询交易所地址与代币的第一笔交易（ETH）"""
    earliest = None

    # 只查询前5个交易所地址（避免 API 限速）
    for exchange_addr in exchange_addresses[:5]:
        print(f"    检查交易所地址 {exchange_addr[:10]}...")

        params = {
            "chainid": "1",
            "module": "account",
            "action": "tokentx",
            "contractaddress": contract,
            "address": exchange_addr,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": 1,
            "sort": "asc",
            "apikey": api_key
        }

        try:
            resp = requests.get(ETHERSCAN_API, params=params, timeout=30)
            data = resp.json()

            if data.get("status") == "1" and data.get("result"):
                first_tx = data["result"][0]
                block_num = int(first_tx["blockNumber"])
                timestamp = int(first_tx["timeStamp"])

                if earliest is None or timestamp < earliest["timestamp"]:
                    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                    earliest = {
                        "block": block_num,
                        "timestamp": timestamp,
                        "date": dt.strftime("%Y-%m-%d"),
                        "datetime": dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "tx_hash": first_tx["hash"],
                        "exchange_address": exchange_addr
                    }
                    print(f"      ✓ 找到交易: {dt.strftime('%Y-%m-%d %H:%M:%S')}")

            time.sleep(0.25)  # API 限速

        except Exception as e:
            print(f"      错误: {e}")
            continue

    return earliest

def get_first_exchange_transfer_bsc(contract: str, exchange_addresses: list, api_key: str):
    """查询交易所地址与代币的第一笔交易（BSC）"""
    earliest = None

    # 只查询前5个交易所地址
    for exchange_addr in exchange_addresses[:5]:
        print(f"    检查交易所地址 {exchange_addr[:10]}...")

        params = {
            "module": "account",
            "action": "tokentx",
            "contractaddress": contract,
            "address": exchange_addr,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": 1,
            "sort": "asc",
            "apikey": api_key
        }

        try:
            resp = requests.get(BSCSCAN_API, params=params, timeout=30)
            data = resp.json()

            if data.get("status") == "1" and data.get("result"):
                first_tx = data["result"][0]
                block_num = int(first_tx["blockNumber"])
                timestamp = int(first_tx["timeStamp"])

                if earliest is None or timestamp < earliest["timestamp"]:
                    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
                    earliest = {
                        "block": block_num,
                        "timestamp": timestamp,
                        "date": dt.strftime("%Y-%m-%d"),
                        "datetime": dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "tx_hash": first_tx["hash"],
                        "exchange_address": exchange_addr
                    }
                    print(f"      ✓ 找到交易: {dt.strftime('%Y-%m-%d %H:%M:%S')}")

            time.sleep(0.25)  # API 限速

        except Exception as e:
            print(f"      错误: {e}")
            continue

    return earliest

def main():
    print("=== 查询代币在交易所的第一笔交易时间 ===\n")

    with open(TOKENS_FILE) as f:
        tokens = json.load(f)

    with open(EXCHANGES_FILE) as f:
        exchanges = json.load(f)

    eth_api_key = get_env("ETHERSCAN_API_KEY")
    bsc_api_key = get_env("BSCTrace_API_KEY")

    results = {}

    for token_name, deployments in tokens.items():
        print(f"\n{'='*60}")
        print(f"{token_name}:")
        print(f"{'='*60}")
        results[token_name] = {}

        for deployment in deployments:
            chain = deployment["chain"]
            contract = deployment["contract"]

            print(f"\n  链: {chain.upper()}")
            print(f"  合约: {contract}")

            if chain == "ethereum":
                if not eth_api_key:
                    print(f"  ✗ 跳过 (无 Etherscan API key)")
                    continue

                # 获取该链上所有交易所地址
                exchange_addrs = []
                for ex_name, ex_chains in exchanges.items():
                    if "ethereum" in ex_chains:
                        exchange_addrs.extend(ex_chains["ethereum"])

                print(f"  查询 {len(exchange_addrs)} 个交易所地址...")

                info = get_first_exchange_transfer_eth(contract, exchange_addrs, eth_api_key)
                if info:
                    results[token_name]["ethereum"] = info
                    print(f"\n  ✓ 最早交易:")
                    print(f"    区块: {info['block']}")
                    print(f"    时间: {info['datetime']}")
                    print(f"    交易所: {info['exchange_address'][:10]}...")
                else:
                    print(f"\n  ✗ 未找到交易所交易")

            elif chain == "bsc":
                if not bsc_api_key:
                    print(f"  ✗ 跳过 (无 BSCScan API key)")
                    continue

                # 获取该链上所有交易所地址
                exchange_addrs = []
                for ex_name, ex_chains in exchanges.items():
                    if "bsc" in ex_chains:
                        exchange_addrs.extend(ex_chains["bsc"])

                print(f"  查询 {len(exchange_addrs)} 个交易所地址...")

                info = get_first_exchange_transfer_bsc(contract, exchange_addrs, bsc_api_key)
                if info:
                    results[token_name]["bsc"] = info
                    print(f"\n  ✓ 最早交易:")
                    print(f"    区块: {info['block']}")
                    print(f"    时间: {info['datetime']}")
                    print(f"    交易所: {info['exchange_address'][:10]}...")
                else:
                    print(f"\n  ✗ 未找到交易所交易")

            elif chain == "solana":
                print(f"  ⚠ Solana 链暂不支持自动查询")

    # 保存结果
    output_file = BASE_DIR / "data" / "exchange_first_transfer.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n\n{'='*60}")
    print(f"✓ 查询完成，结果已保存到:")
    print(f"  {output_file}")
    print(f"{'='*60}")

    # 生成 TGE_BLOCKS 配置
    print("\n\n=== 建议的 TGE_BLOCKS 配置（基于交易所第一笔交易）===\n")
    print("TGE_BLOCKS = {")
    for token_name, chains in results.items():
        if chains:
            chain_blocks = {}
            dates = []

            for chain, info in chains.items():
                chain_blocks[chain] = info["block"]
                dates.append(info["date"])

            # 获取最早的日期
            earliest_date = min(dates) if dates else "UNKNOWN"

            print(f'    "{token_name}": {{')
            for chain, block in chain_blocks.items():
                print(f'        "{chain}": {block},')
            print(f'        "date": "{earliest_date}"')
            print(f'    }},')
    print("}")

if __name__ == "__main__":
    main()
