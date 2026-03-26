"""
Dune Analytics API v1 client for onchain-analysis scripts.

Usage:
    from core.dune import run_query, execute_query, poll_result

API key: set DUNE_API_KEY in .env
Docs: https://docs.dune.com/api-reference/overview/introduction
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any

from .rpc import get_session

DUNE_API_BASE = "https://api.dune.com/api/v1"


def _require_key() -> str:
    """Return first available Dune API key (DUNE_API_KEY, DUNE_API_KEY_2, etc.)"""
    for i in range(1, 10):
        suffix = "" if i == 1 else f"_{i}"
        key = os.environ.get(f"DUNE_API_KEY{suffix}", "")
        if key:
            return key
    print("ERROR: No DUNE_API_KEY found in environment", file=sys.stderr)
    sys.exit(1)


def _get_all_keys() -> list[str]:
    """Return all available Dune API keys for rotation."""
    keys = []
    for i in range(1, 10):
        suffix = "" if i == 1 else f"_{i}"
        key = os.environ.get(f"DUNE_API_KEY{suffix}", "")
        if key:
            keys.append(key)
    return keys


def execute_query(
    query_id: int,
    params: dict[str, Any] | None = None,
    api_key: str | None = None,
) -> str:
    """
    Submit a Dune query for execution.
    Returns execution_id string.

    params: optional dict of query parameters, e.g. {"pump_mint": "pumpCm..."}
    """
    key = api_key or _require_key()
    session = get_session(DUNE_API_BASE)
    url = f"{DUNE_API_BASE}/query/{query_id}/execute"
    body: dict[str, Any] = {}
    if params:
        body["query_parameters"] = {k: {"type": "text", "value": str(v)} for k, v in params.items()}

    resp = session.post(url, json=body, headers={"X-Dune-API-Key": key}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    execution_id = data.get("execution_id")
    if not execution_id:
        raise RuntimeError(f"Dune execute_query: no execution_id in response: {data}")
    return execution_id


def poll_result(
    execution_id: str,
    api_key: str | None = None,
    timeout: int = 600,
    poll_interval: float = 3.0,
) -> dict[str, Any]:
    """
    Poll a Dune execution until complete.
    Tries all available keys if the provided key returns 402.
    Returns {"rows": [...], "metadata": {...}}.
    """
    all_keys = _get_all_keys()
    if api_key and api_key not in all_keys:
        all_keys = [api_key] + all_keys
    if not all_keys:
        all_keys = [_require_key()]

    session = get_session(DUNE_API_BASE)
    url = f"{DUNE_API_BASE}/execution/{execution_id}/results"
    deadline = time.time() + timeout

    while time.time() < deadline:
        last_err = None
        for key in all_keys:
            resp = session.get(url, headers={"X-Dune-API-Key": key}, timeout=30)
            if resp.status_code == 402:
                last_err = "402"
                continue  # try next key
            if resp.status_code == 429:
                time.sleep(poll_interval * 2)
                break
            resp.raise_for_status()
            data = resp.json()
            state = data.get("state", "")
            if state == "QUERY_STATE_COMPLETED":
                result = data.get("result", {})
                return {
                    "rows": result.get("rows", []),
                    "metadata": result.get("metadata", {}),
                }
            if state in ("QUERY_STATE_FAILED", "QUERY_STATE_CANCELLED", "QUERY_STATE_EXPIRED"):
                raise RuntimeError(f"Dune query {execution_id} ended with state: {state}")
            # Still running
            time.sleep(poll_interval)
            break
        else:
            if last_err == "402":
                raise RuntimeError(f"All Dune keys returned 402 for execution {execution_id}")

    raise RuntimeError(f"Dune poll_result: timeout after {timeout}s for execution {execution_id}")


def run_query(
    query_id: int,
    params: dict[str, Any] | None = None,
    api_key: str | None = None,
    timeout: int = 600,
) -> list[dict[str, Any]]:
    """
    Execute a Dune query and wait for results. Returns list of row dicts.

    Example:
        rows = run_query(12345, {"pump_mint": "pumpCm..."})
    """
    key = api_key or _require_key()
    execution_id = execute_query(query_id, params=params, api_key=key)
    print(f"  Dune query {query_id} submitted → execution_id: {execution_id}")
    result = poll_result(execution_id, api_key=key, timeout=timeout)
    rows = result["rows"]
    print(f"  Dune query {query_id} complete: {len(rows)} rows")
    return rows


def run_sql(
    sql: str,
    api_key: str | None = None,
    timeout: int = 600,
    poll_interval: float = 3.0,
) -> list[dict[str, Any]]:
    """
    Execute an ad-hoc SQL query directly without creating a saved query.
    Auto-rotates through DUNE_API_KEY, DUNE_API_KEY_2, etc. on 402 errors.
    """
    keys = [api_key] if api_key else _get_all_keys()
    if not keys:
        raise RuntimeError("No Dune API keys available")

    session = get_session(DUNE_API_BASE)
    url = f"{DUNE_API_BASE}/sql/execute"
    body = {"sql": sql, "performance": "medium"}

    for key_idx, key in enumerate(keys):
        try:
            resp = session.post(url, json=body, headers={"X-Dune-API-Key": key}, timeout=30)
            if resp.status_code == 402:
                print(f"  Dune key {key_idx+1} credit exhausted (402), trying next key...", flush=True)
                continue
            resp.raise_for_status()
            data = resp.json()
            execution_id = data.get("execution_id")
            if not execution_id:
                raise RuntimeError(f"Dune run_sql: no execution_id in response: {data}")

            print(f"  Dune ad-hoc SQL submitted → execution_id: {execution_id} (key {key_idx+1})")
            result = poll_result(execution_id, api_key=key, timeout=timeout, poll_interval=poll_interval)
            rows = result["rows"]
            print(f"  Dune ad-hoc SQL complete: {len(rows)} rows")
            return rows

        except Exception as e:
            if "402" in str(e) and key_idx < len(keys) - 1:
                print(f"  Dune key {key_idx+1} exhausted, rotating to key {key_idx+2}...", flush=True)
                continue
            raise

    raise RuntimeError(f"All {len(keys)} Dune API keys exhausted")


def get_latest_result(
    query_id: int,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch the latest cached result for a query without re-executing.
    Useful for queries that run on a schedule.
    Returns list of row dicts, or [] if no cached result.
    """
    key = api_key or _require_key()
    session = get_session(DUNE_API_BASE)
    url = f"{DUNE_API_BASE}/query/{query_id}/results"
    resp = session.get(url, headers={"X-Dune-API-Key": key}, timeout=30)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    data = resp.json()
    return data.get("result", {}).get("rows", [])
