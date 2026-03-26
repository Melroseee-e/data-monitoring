"""
Arkham Intelligence API client for onchain-analysis scripts.

Base URL: https://api.arkm.com
API key: set ARKHAM_API_KEY in .env
Docs: https://intel.arkm.com/api/docs

Key endpoints:
  POST /intelligence/address/batch  — 250 credits/call, up to 1000 addresses
  GET  /token/holders/{chain}/{address} — 30 credits/call
  GET  /transfers — 2 credits/row
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any

from .rpc import get_session

ARKHAM_BASE = "https://api.arkm.com"
ARKHAM_BATCH_LIMIT = 1000   # max addresses per batch call


def _require_key() -> str:
    key = os.environ.get("ARKHAM_API_KEY", "")
    if not key:
        print("ERROR: ARKHAM_API_KEY not set in environment", file=sys.stderr)
        sys.exit(1)
    return key


def batch_lookup_addresses(
    addresses: list[str],
    chain: str = "solana",
    api_key: str | None = None,
) -> dict[str, dict]:
    """
    Batch lookup Arkham entity labels for up to 1000 addresses per call.
    Cost: 250 credits per call (regardless of address count).

    Returns {address: {entity_name, entity_type, entity_id, entity_website, label, has_entity}}
    """
    key = api_key or _require_key()
    session = get_session(ARKHAM_BASE)
    headers = {"API-Key": key, "Content-Type": "application/json"}

    result: dict[str, dict] = {}
    total_chunks = (len(addresses) + ARKHAM_BATCH_LIMIT - 1) // ARKHAM_BATCH_LIMIT

    for chunk_i, i in enumerate(range(0, len(addresses), ARKHAM_BATCH_LIMIT)):
        chunk = addresses[i: i + ARKHAM_BATCH_LIMIT]
        backoff = 1.0
        for attempt in range(5):
            try:
                resp = session.post(
                    f"{ARKHAM_BASE}/intelligence/address/batch",
                    headers=headers,
                    params={"chain": chain},
                    json={"addresses": chunk},
                    timeout=30,
                )
                if resp.status_code == 429:
                    wait = min(32, backoff)
                    print(f"  Arkham 429, retry in {wait:.0f}s...", flush=True)
                    time.sleep(wait)
                    backoff *= 2
                    continue
                if resp.status_code == 402:
                    print("  Arkham 402: insufficient credits", flush=True)
                    return result
                resp.raise_for_status()
                data = resp.json()
                for addr, info in data.get("addresses", {}).items():
                    entity = info.get("arkhamEntity") or {}
                    label  = info.get("arkhamLabel") or {}
                    result[addr] = {
                        "entity_name":    entity.get("name"),
                        "entity_type":    entity.get("type"),
                        "entity_id":      entity.get("id"),
                        "entity_website": entity.get("website"),
                        "label":          label.get("name"),
                        "has_entity":     bool(entity.get("name")),
                    }
                if total_chunks > 1:
                    print(f"  Arkham batch {chunk_i+1}/{total_chunks}: {len(result)} labeled so far", flush=True)
                break
            except Exception as e:
                if attempt < 4:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    print(f"  Arkham batch error: {e}", flush=True)
        # Polite delay between chunks
        if i + ARKHAM_BATCH_LIMIT < len(addresses):
            time.sleep(0.5)

    return result


def get_token_holders(
    chain: str,
    token_address: str,
    api_key: str | None = None,
) -> list[dict]:
    """
    Get top token holders with Arkham entity labels.
    Cost: 30 credits per call.

    Returns list of {address, balance, usd, pct_of_cap, entity_name, entity_type, entity_id, label, has_entity}
    """
    key = api_key or _require_key()
    session = get_session(ARKHAM_BASE)
    headers = {"API-Key": key}

    backoff = 1.0
    for attempt in range(5):
        try:
            resp = session.get(
                f"{ARKHAM_BASE}/token/holders/{chain}/{token_address}",
                headers=headers,
                timeout=20,
            )
            if resp.status_code == 429:
                time.sleep(min(32, backoff))
                backoff *= 2
                continue
            resp.raise_for_status()
            data = resp.json()
            holders = []
            for h in data.get("addressTopHolders", {}).get(chain, []):
                addr_info = h.get("address", {})
                entity = addr_info.get("arkhamEntity") or {}
                label  = addr_info.get("arkhamLabel") or {}
                holders.append({
                    "address":        addr_info.get("address", ""),
                    "balance":        h.get("balance", 0),
                    "usd":            h.get("usd", 0),
                    "pct_of_cap":     h.get("pctOfCap", 0),
                    "entity_name":    entity.get("name"),
                    "entity_type":    entity.get("type"),
                    "entity_id":      entity.get("id"),
                    "entity_website": entity.get("website"),
                    "label":          label.get("name"),
                    "has_entity":     bool(entity.get("name")),
                })
            return holders
        except Exception as e:
            if attempt < 4:
                time.sleep(backoff)
                backoff *= 2
            else:
                print(f"  Arkham token holders error: {e}", flush=True)
    return []


def get_address_entity(
    address: str,
    chain: str = "solana",
    api_key: str | None = None,
) -> dict[str, Any] | None:
    """
    Single address entity lookup (1 credit/call).
    Returns raw Arkham response dict or None on error.
    """
    key = api_key or _require_key()
    session = get_session(ARKHAM_BASE)
    url = f"{ARKHAM_BASE}/intelligence/address/{address}"
    for attempt in range(3):
        try:
            resp = session.get(url, headers={"API-Key": key}, params={"chain": chain}, timeout=20)
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt == 2:
                print(f"  Arkham get_address_entity({address[:8]}...): {e}")
                return None
            time.sleep(1)
    return None


def extract_entity_summary(entity_info: dict[str, Any] | None) -> dict[str, Any]:
    """Extract compact summary from raw Arkham address response."""
    if not entity_info:
        return {"name": None, "type": None, "label": None, "has_entity": False}
    entity = entity_info.get("arkhamEntity") or {}
    label  = entity_info.get("arkhamLabel") or {}
    return {
        "name":       entity.get("name") or None,
        "type":       entity.get("type") or None,
        "label":      label.get("name") or None,
        "has_entity": bool(entity.get("name")),
    }


def search_transfers(
    address: str,
    token_address: str | None = None,
    api_key: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Search token transfers for an address (2 credits/row).
    Optionally filter by token_address (mint for Solana).
    """
    key = api_key or _require_key()
    session = get_session(ARKHAM_BASE)
    params: dict[str, Any] = {"base": address, "limit": limit}
    if token_address:
        params["tokenAddress"] = token_address
    for attempt in range(3):
        try:
            resp = session.get(
                f"{ARKHAM_BASE}/transfers",
                params=params,
                headers={"API-Key": key},
                timeout=30,
            )
            if resp.status_code == 429:
                time.sleep(2 ** attempt)
                continue
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            return resp.json().get("transfers", [])
        except Exception as e:
            if attempt == 2:
                print(f"  Arkham search_transfers({address[:8]}...): {e}")
                return []
            time.sleep(1)
    return []


# Legacy alias for backwards compatibility
def batch_get_entities(
    addresses: list[str],
    api_key: str | None = None,
    delay: float = 0.2,
) -> dict[str, dict[str, Any]]:
    """Legacy: use batch_lookup_addresses instead (250 credits vs 1 credit per address)."""
    return batch_lookup_addresses(addresses, api_key=api_key)
