import logging
from services import get_session

logger = logging.getLogger("RainyBot")

async def get_evm_confirmations(tx_hash, rpc_urls):
    
    if not tx_hash or not rpc_urls: return 0
    from web3 import AsyncWeb3, AsyncHTTPProvider
    
    if isinstance(tx_hash, str) and not tx_hash.startswith("0x"):
        tx_hash = "0x" + tx_hash

    session = await get_session()
    async def fetch_conf(url):
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(url, request_kwargs={"timeout": 6}, session=session))
            
            
            receipt = await w3.eth.get_transaction_receipt(tx_hash)
            tx_block = None
            
            if receipt:
                tx_block = receipt.get('blockNumber')
            else:
                
                tx_data = await w3.eth.get_transaction(tx_hash)
                if tx_data and tx_data.get('blockNumber'):
                    tx_block = tx_data['blockNumber']
            
            if tx_block is not None:
                current_block = await w3.eth.block_number
                return max(0, current_block - tx_block + 1)
            return 0
        except:
            return 0

    tasks = [fetch_conf(url) for url in rpc_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_results = [r for r in results if isinstance(r, int)]
    return max(valid_results) if valid_results else 0

async def get_solana_confirmations(tx_hash, rpc_urls):
    
    if not tx_hash or not rpc_urls: return 0
    session = await get_session()
    async def fetch_sol(url):
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignatureStatuses",
                "params": [[tx_hash], {"searchTransactionHistory": True}]
            }
            async with session.post(url, json=payload, timeout=5) as r:
                if r.status == 200:
                    data = await r.json()
                    val = data.get("result", {}).get("value", [None])[0]
                    if not val: return 0
                    
                    status = val.get("confirmationStatus")
                    if status == "finalized": return 2
                    if status == "confirmed": return 1
                return 0
        except: return 0

    tasks = [fetch_sol(url) for url in rpc_urls]
    results = await asyncio.gather(*tasks)
    return max(results) if results else 0
