#!/usr/bin/env python3
"""
验证代币 TGE 时间 - 通过查询链上第一笔交易
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

ETHERSCAN_API = "https://api.etherscan.io/v2/api"
BSCSCAN_API = "https://api.bscscan.com/api"

def get_env(name: str) -> str:
    val = os.environ.get(name, "")
    if not val:
        print(f"WARNING: {name} not set", file=sys.stderr)
    return val

def get_first_transfer_eth(contract: str, api_key: str):
    """获取 Ethereum 合约的第一笔 Transfer 事件"""
    print(f"  查询 ETH 合约 {contract[:10]}... 的第一笔交易")

    # 先获取合约创建信息
    params = {
        "chainid": "1",
        "module": "contract",
        "action": "getcontractcreation",
        "contractaddresses": contract,
        "apikey": api_key
    }

    try:
        resp = requests.get(ETHERSCAN_API, params=params, timeout=15)
        data = resp.json()

        if data.get("status") == "1" and data.get("result"):
            creator_tx = data["result"][0]["txHash"]

            # 获取创建交易的区块号
            params2 = {
                "chainid": "1",
                "module": "proxy",
                "action": "eth_getTransactionByHash",
                "txhash": creator_tx,
                "apikey": api_key
            }

            resp2 = requests.get(ETHERSCAN_API, params=params2, timeout=15)
            tx_data = resp2.json()

            if tx_data.get("result"):
                creation_block = int(tx_data["result"]["blockNumber"], 16)

                # 获取该区块的时间戳
                params3 = {
                    "chainid": "1",
                    "module": "proxy",
                    "action": "eth_getBlockByNumber",
                    "tag": hex(creation_block),
                    "boolean": "false",
                    "apikey": api_key
                }

                resp3 = requests.get(ETHERSCAN_API, params=params3, timeout=15)
                block_data = resp3.json()

                if block_data.get("result"):
                    timestamp = int(block_data["result"]["timestamp"], 16)
                    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)

                    return {
                        "block": creation_block,
                        "timestamp": timestamp,
                        "date": dt.strftime("%Y-%m-%d"),
                        "datetime": dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "tx_hash": creator_tx
                    }

        # 如果获取合约创建失败，尝试获取第一笔 tokentx
        print(f"    尝试通过 tokentx 查询...")
        params_tx = {
            "chainid": "1",
            "module": "account",
            "action": "tokentx",
            "contractaddress": contract,
            "startblock": 0,
            "endblock": 99999999,
            "page": 1,
            "offset": 1,
            "sort": "asc",
            "apikey": api_key
        }

        resp_tx = requests.get(ETHERSCAN_API, params=params_tx, timeout=30)
        tx_data = resp_tx.json()

        if tx_data.get("status") == "1" and tx_data.get("result"):
            first_tx = tx_data["result"][0]
            block_num = int(first_tx["blockNumber"])
            timestamp = int(first_tx["timeStamp"])
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)

            return {
                "block": block_num,
                "timestamp": timestamp,
                "date": dt.strftime("%Y-%m-%d"),
                "datetime": dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "tx_hash": first_tx["hash"]
            }

    except Exception as e:
        print(f"    错误: {e}")
        return None

    return None

def get_first_transfer_bsc(contract: str, api_key: str):
    """获取 BSC 合约的第一笔 Transfer 事件"""
    print(f"  查询 BSC 合约 {contract[:10]}... 的第一笔交易")

    params = {
        "module": "account",
        "action": "tokentx",
        "contractaddress": contract,
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
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)

            return {
                "block": block_num,
                "timestamp": timestamp,
                "date": dt.strftime("%Y-%m-%d"),
                "datetime": dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "tx_hash": first_tx["hash"]
            }
    except Exception as e:
        print(f"    错误: {e}")
        return None

    return None

def main():
    print("=== 验证代币 TGE 时间（链上数据）===\n")

    with open(TOKENS_FILE) as f:
        tokens = json.load(f)

    eth_api_key = get_env("ETHERSCAN_API_KEY")
    bsc_api_key = get_env("BSCTrace_API_KEY")

    results = {}

    for token_name, deployments in tokens.items():
        print(f"\n{token_name}:")
        results[token_name] = {}

        for deployment in deployments:
            chain = deployment["chain"]
            contract = deployment["contract"]

            if chain == "ethereum":
                if not eth_api_key:
                    print(f"  跳过 ETH (无 API key)")
                    continue

                info = get_first_transfer_eth(contract, eth_api_key)
                if info:
                    results[token_name]["ethereum"] = info
                    print(f"    ✓ 区块: {info['block']}")
                    print(f"    ✓ 时间: {info['datetime']}")
                    print(f"    ✓ 日期: {info['date']}")
                else:
                    print(f"    ✗ 无法获取数据")

                time.sleep(0.3)  # API 限速

            elif chain == "bsc":
                if not bsc_api_key:
                    print(f"  跳过 BSC (无 API key)")
                    continue

                info = get_first_transfer_bsc(contract, bsc_api_key)
                if info:
                    results[token_name]["bsc"] = info
                    print(f"    ✓ 区块: {info['block']}")
                    print(f"    ✓ 时间: {info['datetime']}")
                    print(f"    ✓ 日期: {info['date']}")
                else:
                    print(f"    ✗ 无法获取数据")

                time.sleep(0.3)  # API 限速

            elif chain == "solana":
                print(f"  Solana 链暂不支持自动查询")

    # 保存结果
    output_file = BASE_DIR / "data" / "tge_verification.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n\n✓ 验证完成，结果已保存到: {output_file}")

    # 生成 TGE_BLOCKS 格式
    print("\n\n=== 建议的 TGE_BLOCKS 配置 ===\n")
    print("TGE_BLOCKS = {")
    for token_name, chains in results.items():
        if chains:
            chain_data = {}
            for chain, info in chains.items():
                chain_data[chain] = info["block"]

            # 获取最早的日期
            dates = [info["date"] for info in chains.values()]
            earliest_date = min(dates) if dates else "UNKNOWN"

            print(f'    "{token_name}": {json.dumps(chain_data)}, "date": "{earliest_date}"}},')
    print("}")

if __name__ == "__main__":
    main()
