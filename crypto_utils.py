import asyncio
import time
from web3 import Web3
from eth_account import Account
from bitcoinrpc.authproxy import AuthServiceProxy
import config

def dbg(msg):
    # Consider using proper logging later
    print(f"[LTC-DEBUG] {msg}")

async def safe_rpc_call(func, *args, retries=5, delay=1):
    for i in range(retries):
        try:
            # Check if func is awaitable (coroutine) or regular function
            if asyncio.iscoroutinefunction(func):
                return await func(*args)
            else:
                return func(*args)
        except Exception as e:
            print(f"RPC error: {e}, retry {i+1}/{retries}")
            await asyncio.sleep(delay)
    raise Exception("RPC failed after retries")

# --- RPC Helpers ---

def rpc_call(method, *params):
    """Single RPC call to LTC node (blocking)."""
    # Uses RPC_URL from config which contains auth info
    rpc = AuthServiceProxy(config.RPC_URL, timeout=10)
    return getattr(rpc, method)(*params)

async def rpc_async(method, *params):
    """Async wrapper for blocking RPC calls using threads."""
    return await asyncio.to_thread(rpc_call, method, *params)

# --- Balance Checks ---

async def get_gas_balance(address, currency):
    """Return BNB (for BEP20) or MATIC (for Polygon) balance using AsyncWeb3"""
    from web3 import AsyncWeb3, AsyncHTTPProvider
    try:
        rpc_urls = []
        if currency == "usdt_bep20":
            rpc_urls = config.BEP20_RPC_URLS
        elif currency == "usdt_polygon":
            rpc_urls = config.POLYGON_RPC_URLS
        else:
            return 0.0

        for rpc in rpc_urls:
            w3 = None
            try:
                w3 = AsyncWeb3(AsyncHTTPProvider(rpc, request_kwargs={"timeout": 5}))
                if not await w3.is_connected():
                    continue
                bal = await w3.eth.get_balance(Web3.to_checksum_address(address))
                return float(w3.from_wei(bal, 'ether'))
            except:
                continue
            finally:
                if w3 is not None:
                    try: await w3.provider.session.close()
                    except: pass
    except Exception as e:
        print(f"Gas balance error ({currency}): {e}")

    return 0.0

async def get_eth_balance_parallel(address):
    """Get ETH balance from multiple RPCs in parallel (Async)."""
    from web3 import AsyncWeb3, AsyncHTTPProvider
    
    async def fetch_balance(rpc_url):
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url, request_kwargs={"timeout": 5}))
            if not await w3.is_connected():
                return None
            balance_wei = await w3.eth.get_balance(Web3.to_checksum_address(address))
            return float(balance_wei / (10 ** 18))
        except Exception as e:
            return None
        finally:
            if w3 is not None:
                try: await w3.provider.session.close()
                except: pass
            
    tasks = [asyncio.create_task(fetch_balance(url)) for url in config.ETH_RPC_URLS]
    done, pending = await asyncio.wait(tasks, timeout=6, return_when=asyncio.FIRST_COMPLETED)
    
    for t in done:
        res = t.result()
        if res is not None:
            for p in pending: p.cancel()
            return res
            
    return 0.0



async def get_last_eth_txhash(address):
    """Get last incoming ETH transaction hash using AsyncWeb3"""
    from web3 import AsyncWeb3, AsyncHTTPProvider
    address_checksum = Web3.to_checksum_address(address)
    
    async def fetch_last_tx(rpc_url):
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url, request_kwargs={"timeout": 5}))
            if not await w3.is_connected():
                return None
            
            latest_block = await w3.eth.block_number
            start_block = max(0, latest_block - 20)
            
            for block_num in range(latest_block, start_block, -1):
                try:
                    block = await w3.eth.get_block(block_num, full_transactions=True)
                    for tx in block.transactions:
                        if tx.to and tx.to.lower() == address_checksum.lower():
                            return tx.hash.hex()
                except:
                    continue
        except Exception as e:
            pass
        finally:
            if w3 is not None:
                try: await w3.provider.session.close()
                except: pass
        return None
    
    tasks = [fetch_last_tx(url) for url in config.ETH_RPC_URLS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if result and isinstance(result, str):
            return result
    
    return None

# --- Transaction Helpers ---

async def send_eth(private_key, to_address, amount_eth=None):
    """Sends ETH using AsyncWeb3."""
    from web3 import AsyncWeb3, AsyncHTTPProvider
    account = Account.from_key(private_key)
    from_address = account.address

    for rpc_url in config.ETH_RPC_URLS:
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
            if not await w3.is_connected():
                continue

            balance = await w3.eth.get_balance(from_address)
            from services.nonce_manager import nonce_manager
            nonce = await nonce_manager.get_next_nonce(w3, from_address)
            gas_limit = 21000
            gas_price = await w3.eth.gas_price
            gas_cost = gas_limit * gas_price

            if balance <= gas_cost:
                raise Exception("Not enough ETH to cover gas.")

            if amount_eth:
                amount_wei = Web3.to_wei(amount_eth, 'ether')
                if balance < (amount_wei + gas_cost):
                     raise Exception("Insufficient ETH balance for amount + gas")
                amount_to_send = amount_wei
            else:
                amount_to_send = balance - gas_cost

            tx = {
                "nonce": nonce,
                "to": Web3.to_checksum_address(to_address),
                "value": amount_to_send,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "chainId": 1
            }

            signed_tx = w3.eth.account.sign_transaction(tx, private_key)
            raw_tx = getattr(signed_tx, "rawTransaction", getattr(signed_tx, "raw_transaction", None))
            if raw_tx is None:
                raise Exception("Unable to get raw TX bytes")

            tx_hash = await w3.eth.send_raw_transaction(raw_tx)
            return tx_hash.hex()

        except Exception as e:
            print(f"ETH send failed ({rpc_url}): {e}")
            continue
        finally:
            if w3 is not None:
                try: await w3.provider.session.close()
                except: pass

    raise Exception("All ETH RPC endpoints failed")

async def estimate_required_gas(contract_address, private_key, to_address, amount, rpc_urls, decimals):
    """Estimate gas using AsyncWeb3."""
    from web3 import AsyncWeb3, AsyncHTTPProvider
    account = Account.from_key(private_key)
    from_addr = account.address
    amount_wei = int(amount * (10 ** decimals))

    for rpc in rpc_urls:
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(rpc, request_kwargs={"timeout": 5}))
            if not await w3.is_connected():
                continue

            contract = w3.eth.contract(
                address=w3.to_checksum_address(contract_address),
                abi=config.USDT_ABI
            )

            nonce = await w3.eth.get_transaction_count(from_addr)

            tx = await contract.functions.transfer(
                w3.to_checksum_address(to_address),
                amount_wei
            ).build_transaction({
                "from": from_addr,
                "nonce": nonce,
            })

            gas = await w3.eth.estimate_gas(tx)
            gas_price = await w3.eth.gas_price
            total_gas_native = (gas * gas_price) / (10 ** 18)
            return float(total_gas_native)

        except Exception as e:
            print("Gas estimation failed on RPC:", rpc, e)
            continue
        finally:
            if w3 is not None:
                try: await w3.provider.session.close()
                except: pass

    return None

async def send_native_chain_generic(private_key, to_address, amount_native, rpc_urls, chain_id):
    """Sends native token using AsyncWeb3."""
    from web3 import AsyncWeb3, AsyncHTTPProvider
    account = Account.from_key(private_key)
    from_address = account.address

    for rpc_url in rpc_urls:
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
            if not await w3.is_connected():
                continue

            balance = await w3.eth.get_balance(from_address)
            from services.nonce_manager import nonce_manager
            nonce = await nonce_manager.get_next_nonce(w3, from_address)
            
            gas_price = await w3.eth.gas_price
            if chain_id == 137: # Polygon
                gas_price = int(gas_price * 1.5)
            
            gas_limit = 21000
            gas_cost = gas_limit * gas_price
            amount_wei = w3.to_wei(amount_native, 'ether')
            
            if balance < (amount_wei + gas_cost):
                raise Exception(f"Insufficient native balance. Need {amount_wei+gas_cost}, have {balance}")

            tx = {
                "nonce": nonce,
                "to": Web3.to_checksum_address(to_address),
                "value": amount_wei,
                "gas": gas_limit,
                "gasPrice": gas_price,
                "chainId": chain_id
            }

            signed_tx = w3.eth.account.sign_transaction(tx, private_key)
            raw_tx = getattr(signed_tx, "rawTransaction", getattr(signed_tx, "raw_transaction", None))
            if raw_tx is None:
                 raise Exception("Unable to extract raw transaction")

            tx_hash = await w3.eth.send_raw_transaction(raw_tx)
            return tx_hash.hex()

        except Exception as e:
            print(f"Native send failed on {rpc_url}: {e}")
            continue
        finally:
            if w3 is not None:
                try: await w3.provider.session.close()
                except: pass

    raise Exception(f"All RPCs failed for chain {chain_id}")
