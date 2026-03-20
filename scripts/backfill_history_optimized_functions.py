"""
Optimized functions for batch RPC calls and concurrent processing
"""
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

def batch_rpc_call(rpc_url, method, params_list, max_retries=3):
    """
    Make batch RPC calls to Solana
    
    Args:
        rpc_url: RPC endpoint URL
        method: RPC method name
        params_list: List of parameters for each call
        max_retries: Maximum number of retries
    
    Returns:
        List of results
    """
    batch_request = []
    for i, params in enumerate(params_list):
        batch_request.append({
            "jsonrpc": "2.0",
            "id": i,
            "method": method,
            "params": params
        })
    
    for attempt in range(max_retries):
        try:
            response = requests.post(rpc_url, json=batch_request, timeout=30)
            response.raise_for_status()
            results = response.json()
            
            # Handle both single response and batch response
            if isinstance(results, list):
                return [r.get("result") for r in results]
            else:
                return [results.get("result")]
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait_time = (attempt + 1) * 2
                print(f"    Rate limited, waiting {wait_time}s...", flush=True)
                time.sleep(wait_time)
            else:
                print(f"    HTTP error: {e}", flush=True)
                if attempt == max_retries - 1:
                    return [None] * len(params_list)
        except Exception as e:
            print(f"    RPC batch call error: {e}", flush=True)
            if attempt == max_retries - 1:
                return [None] * len(params_list)
            time.sleep(1)
    
    return [None] * len(params_list)


def parse_solana_transactions_batch(api_key, signatures, batch_size=50):
    """
    Parse multiple Solana transactions in batches
    
    Args:
        api_key: Helius API key
        signatures: List of transaction signatures
        batch_size: Number of transactions per batch
    
    Returns:
        Dictionary mapping signature to parsed transfers
    """
    from backfill_history import HELIUS_RPC
    
    rpc_url = HELIUS_RPC.format(api_key=api_key)
    results = {}
    
    # Process in batches
    for i in range(0, len(signatures), batch_size):
        batch = signatures[i:i + batch_size]
        
        if i % 500 == 0:
            print(f"    Progress: {i}/{len(signatures)}", flush=True)
        
        # Prepare batch parameters
        params_list = [
            [sig, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
            for sig in batch
        ]
        
        # Make batch RPC call
        transactions = batch_rpc_call(rpc_url, "getTransaction", params_list)
        
        # Parse each transaction
        for sig, tx in zip(batch, transactions):
            if not tx or not tx.get("meta"):
                continue
            
            block_time = tx.get("blockTime")
            if not block_time:
                continue
            
            # Parse token transfers
            pre_balances = {b["accountIndex"]: b for b in tx["meta"].get("preTokenBalances", [])}
            post_balances = {b["accountIndex"]: b for b in tx["meta"].get("postTokenBalances", [])}
            
            transfers = []
            for idx, post in post_balances.items():
                pre = pre_balances.get(idx, {})
                pre_amount = int(pre.get("uiTokenAmount", {}).get("amount", 0))
                post_amount = int(post.get("uiTokenAmount", {}).get("amount", 0))
                
                if post_amount != pre_amount:
                    decimals = post.get("uiTokenAmount", {}).get("decimals", 9)
                    amount = abs(post_amount - pre_amount)
                    account = post.get("owner")
                    
                    transfers.append({
                        "account": account,
                        "amount": amount,
                        "decimals": decimals,
                        "blockTime": block_time,
                        "direction": "in" if post_amount > pre_amount else "out"
                    })
            
            if transfers:
                results[sig] = transfers
        
        # Rate limiting between batches
        time.sleep(0.5)
    
    return results
