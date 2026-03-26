"""
Configuration loader for onchain-analysis scripts.

API key search order: ENV vars > local .env > data-monitoring project .env
Config file search order: explicit path > data-monitoring project data/
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Try to import dotenv; gracefully skip if not installed
try:
    from dotenv import load_dotenv
    _HAS_DOTENV = True
except ImportError:
    _HAS_DOTENV = False

# Known location of the data-monitoring project
_DATA_MONITORING_DIR = Path(__file__).resolve().parents[5]

# Chain name aliases
_CHAIN_ALIASES = {
    "eth": "ethereum", "ETH": "ethereum", "Ethereum": "ethereum",
    "sol": "solana", "SOL": "solana", "Solana": "solana",
    "bnb": "bsc", "BNB": "bsc", "BSC": "bsc",
}

# ERC-20 Transfer event topic (same for ETH and BSC)
TRANSFER_EVENT_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# API endpoints
ETHERSCAN_API = "https://api.etherscan.io/v2/api"
BSCTRACE_RPC_TEMPLATE = "https://bsc-mainnet.nodereal.io/v1/{api_key}"
HELIUS_RPC_TEMPLATE = "https://mainnet.helius-rpc.com/?api-key={api_key}"
HELIUS_ENHANCED_TEMPLATE = "https://api.helius.xyz/v0/addresses/{address}/transactions"
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
COINGECKO_OHLC_URL = "https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
COINGECKO_MARKET_URL = "https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"


def _load_dotenv_files() -> None:
    """Load .env files in priority order: cwd > script dir > data-monitoring dir."""
    if not _HAS_DOTENV:
        return
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[2] / ".env",
        _DATA_MONITORING_DIR / ".env",
    ]
    for path in candidates:
        if path.exists():
            load_dotenv(path, override=False)


_load_dotenv_files()


def load_api_keys() -> dict[str, str]:
    """
    Load API keys from environment.
    Returns dict with keys: 'ethereum', 'bsc', 'solana' (empty string if not set).
    For Solana, returns the first available key from HELIUS_API_KEY, HELIUS_API_KEY_2, etc.
    """
    # Solana: try multiple keys, return first non-empty
    solana_key = ""
    for i in range(1, 10):
        suffix = "" if i == 1 else f"_{i}"
        k = os.environ.get(f"HELIUS_API_KEY{suffix}", "")
        if k:
            solana_key = k
            break

    return {
        "ethereum": os.environ.get("ETHERSCAN_API_KEY", ""),
        "bsc": os.environ.get("BSCTrace_API_KEY", ""),
        "solana": solana_key,
    }


def get_all_solana_keys() -> list[str]:
    """Return all available Helius API keys (for rotation on rate limit)."""
    keys = []
    for i in range(1, 10):
        suffix = "" if i == 1 else f"_{i}"
        k = os.environ.get(f"HELIUS_API_KEY{suffix}", "")
        if k:
            keys.append(k)
    return keys


def require_api_key(chain: str) -> str:
    """Get API key for chain, exit with error if missing."""
    keys = load_api_keys()
    chain = resolve_chain(chain)
    key = keys.get(chain, "")
    if not key:
        env_map = {"ethereum": "ETHERSCAN_API_KEY", "bsc": "BSCTrace_API_KEY", "solana": "HELIUS_API_KEY"}
        print(f"ERROR: {env_map.get(chain, 'API_KEY')} not set in environment", file=sys.stderr)
        sys.exit(1)
    return key


def resolve_chain(chain: str) -> str:
    """Normalize chain name: 'eth' -> 'ethereum', 'sol' -> 'solana', etc."""
    return _CHAIN_ALIASES.get(chain, chain.lower())


def _find_data_file(filename: str, explicit_path: Path | None) -> Path | None:
    """Search for a data file in known locations."""
    if explicit_path and explicit_path.exists():
        return explicit_path
    candidate = _DATA_MONITORING_DIR / "data" / filename
    if candidate.exists():
        return candidate
    return None


def load_tokens_config(path: Path | None = None) -> dict[str, list[dict]]:
    """
    Load tokens.json. Returns {symbol: [{chain, contract}]}.
    Searches: explicit path > data-monitoring/data/tokens.json
    """
    found = _find_data_file("tokens.json", path)
    if not found:
        return {}
    with open(found, encoding="utf-8") as f:
        return json.load(f)


def load_exchange_addresses(path: Path | None = None) -> dict:
    """
    Load exchange_addresses_normalized.json.
    Returns {exchange_name: {chain: [addresses]}}
    """
    found = _find_data_file("exchange_addresses_normalized.json", path)
    if not found:
        return {}
    with open(found, encoding="utf-8") as f:
        return json.load(f)


def resolve_symbol(symbol: str, tokens_config: dict | None = None) -> list[dict]:
    """
    Given a token symbol (e.g. 'PUMP'), return list of {chain, contract} deployments.
    Loads tokens.json automatically if tokens_config not provided.
    """
    if tokens_config is None:
        tokens_config = load_tokens_config()
    return tokens_config.get(symbol.upper(), [])
