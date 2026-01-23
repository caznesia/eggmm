import asyncio
from web3 import AsyncWeb3
import config

class NonceManager:
    
    def __init__(self):
        self._locks = {}
        self._nonces = {}

    def _get_lock(self, address):
        
        if address not in self._locks:
            self._locks[address] = asyncio.Lock()
        return self._locks[address]

    async def get_next_nonce(self, w3, address):
        
        lock = self._get_lock(address)
        async with lock:
            
            chain_nonce = await w3.eth.get_transaction_count(address)
            
            
            
            if address not in self._nonces or self._nonces[address] < chain_nonce:
                self._nonces[address] = chain_nonce
            
            
            nonce_to_use = self._nonces[address]
            
            
            self._nonces[address] += 1
            
            return nonce_to_use


nonce_manager = NonceManager()
