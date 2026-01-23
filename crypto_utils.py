import asyncio
import time
from web3 import Web3
from eth_account import Account
from bitcoinrpc.authproxy import AuthServiceProxy
import config
from services import get_session
import bitcoinutils.constants as btc_constants
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey as BtcPrivateKey, P2pkhAddress
from bitcoinutils.transactions import Transaction, TxInput, TxOutput


def setup_btcutils(network='litecoin'):
    if network == 'litecoin':
        btc_constants.NETWORK_P2PKH_PREFIXES["litecoin"] = b"\x30"
        btc_constants.NETWORK_WIF_PREFIXES["litecoin"] = b"\xb0"
        setup('litecoin')
    elif network == 'dogecoin':
        btc_constants.NETWORK_P2PKH_PREFIXES["dogecoin"] = b"\x1e"
        btc_constants.NETWORK_WIF_PREFIXES["dogecoin"] = b"\x9e"
        setup('dogecoin')
    else:
        setup('mainnet')

def dbg(msg):
    
    print(f"[UTXO-DEBUG] {msg}")

async def sweep_utxo_address(privkey_wif, to_address, network='litecoin'):
    
    import requests
    setup_btcutils(network)
    
    try:
        priv = BtcPrivateKey(privkey_wif)
        from_pub = priv.get_public_key()
        from_addr = from_pub.get_address().to_string()
        
        
        utxos = []
        if network == 'mainnet': 
            url = f"https://mempool.space/api/address/{from_addr}/utxo"
            resp = requests.get(url, timeout=10).json()
            for u in resp:
                if u['status']['confirmed']:
                    utxos.append({'txid': u['txid'], 'vout': u['vout'], 'value': u['value']})
        elif network == 'litecoin':
            url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{from_addr}?unspentOnly=true"
            resp = requests.get(url, timeout=10).json()
            for u in resp.get('txrefs', []):
                if u.get('confirmations', 0) > 0:
                    utxos.append({'txid': u['txid'], 'vout': u['tx_output_n'], 'value': u['value']})
        elif network == 'dogecoin':
            
            url = f"https://api.blockcypher.com/v1/doge/main/addrs/{from_addr}?unspentOnly=true"
            resp = requests.get(url, timeout=10).json()
            for u in resp.get('txrefs', []):
                if u.get('confirmations', 0) > 0:
                    utxos.append({'txid': u['txid'], 'vout': u['tx_output_n'], 'value': u['value']})

        if not utxos:
            return None 
            
        
        inputs = [TxInput(u['txid'], u['vout']) for u in utxos]
        total_in = sum(u['value'] for u in utxos)
        
        
        
        est_vsize = len(inputs) * 148 + 1 * 34 + 10
        fee_rate = 20 
        
        
        if network == 'mainnet':
            try:
                fr = requests.get("https://mempool.space/api/v1/fees/recommended", timeout=5).json()
                fee_rate = fr.get('hourFee', 20)
            except: pass
        
        fee_sats = int(est_vsize * fee_rate)
        if network == 'dogecoin': fee_sats = int(1 * 10**8) 
        
        send_sats = total_in - fee_sats
        if send_sats <= 546: 
            return None
            
        
        outputs = [TxOutput(send_sats, P2pkhAddress(to_address))]
        tx = Transaction(inputs, outputs)
        
        
        script_pub_key = P2pkhAddress(from_addr).to_script_pub_key()
        for i in range(len(inputs)):
            sig = priv.sign_input(tx, i, script_pub_key)
            tx.inputs[i].script_sig = sig
            
        raw_hex = tx.serialize()
        
        
        if network == 'mainnet': return await rpc_btc_async("sendrawtransaction", raw_hex)
        elif network == 'dogecoin': return await rpc_doge_async("sendrawtransaction", raw_hex)
        else: return await rpc_async("sendrawtransaction", raw_hex)
        
    except Exception as e:
        dbg(f"Sweep for {network} failed: {e}")
        return None

async def safe_rpc_call(func, *args, retries=5, delay=1):
    for i in range(retries):
        try:
            
            if asyncio.iscoroutinefunction(func):
                return await func(*args)
            else:
                return func(*args)
        except Exception as e:
            print(f"RPC error: {e}, retry {i+1}/{retries}")
            await asyncio.sleep(delay)
    raise Exception("RPC failed after retries")





async def unified_rpc_async(url, method, *params):
    
    import aiohttp
    import json
    
    if not url:
        return None
        
    
    if "127.0.0.1" in url or "@" in url:
        try:
             def sync_call():
                 rpc = AuthServiceProxy(url, timeout=15)
                 return getattr(rpc, method)(*params)
             return await asyncio.to_thread(sync_call)
        except Exception as e:
             
             raise e

    
    payload = {
        "jsonrpc": "2.0",
        "id": "rainybot",
        "method": method,
        "params": params
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as resp:
                if resp.status != 200:
                    raise Exception(f"HTTP {resp.status}")
                result = await resp.json()
                if 'error' in result and result['error']:
                    raise Exception(f"RPC Error: {result['error']}")
                return result.get('result')
    except Exception as e:
        raise e

async def rpc_async(method, *params):
    
    return await unified_rpc_async(config.RPC_URL, method, *params)

async def rpc_btc_async(method, *params):
    
    return await unified_rpc_async(config.BTC_RPC_URL, method, *params)

async def rpc_doge_async(method, *params):
    
    return await unified_rpc_async(config.DOGE_RPC_URL, method, *params)

async def get_doge_balance_public(address):
    
    import aiohttp
    
    
    try:
        url = f"https://api.blockcypher.com/v1/doge/main/addrs/{address}/balance"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    return float(data.get('final_balance', 0)) / 1e8
    except Exception as e:
        print(f"[Doge-Public-Err] BlockCypher: {e}")

    
    try:
        url = f"https://dogechain.info/api/v1/address/balance/{address}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get('success') == 1:
                        return float(data.get('balance', 0.0))
    except Exception as e:
        print(f"[Doge-Public-Err] DogeChain: {e}")

    
    try:
        url = f"https://sochain.com/api/v2/get_address_balance/DOGE/{address}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    
                    if data.get('status') == 'success':
                         bal_str = data['data']['confirmed_balance']
                         return float(bal_str)
    except Exception as e:
        print(f"[Doge-Public-Err] SoChain: {e}")

    except Exception as e:
        print(f"[Doge-Public-Err] SoChain: {e}")

    raise Exception("All Doge public APIs failed")



async def get_gas_balance(address, currency):
    
    from web3 import AsyncWeb3, AsyncHTTPProvider
    try:
        rpc_urls = []
        if currency == "usdt_bep20":
            rpc_urls = config.BEP20_RPC_URLS
        elif currency == "usdt_polygon":
            rpc_urls = config.POLYGON_RPC_URLS
        else:
            return 0.0

        session = await get_session()
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

    raise Exception(f"All Gas RPCs failed for {currency}")

async def get_eth_balance_parallel(address):
    
    from web3 import AsyncWeb3, AsyncHTTPProvider
    
    session = await get_session()
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
            
    
    raise Exception("All RPCs failed for ETH balance check")



async def get_last_eth_txhash(address):
    
    from web3 import AsyncWeb3, AsyncHTTPProvider
    address_checksum = Web3.to_checksum_address(address)
    
    session = await get_session()
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



async def send_eth(private_key, to_address, amount_eth=None):
    
    from web3 import AsyncWeb3, AsyncHTTPProvider
    account = Account.from_key(private_key)
    from_address = account.address

    session = await get_session()
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
    
    from web3 import AsyncWeb3, AsyncHTTPProvider
    account = Account.from_key(private_key)
    from_addr = account.address
    amount_wei = int(amount * (10 ** decimals))

    session = await get_session()
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
    
    from web3 import AsyncWeb3, AsyncHTTPProvider
    account = Account.from_key(private_key)
    from_address = account.address

    session = await get_session()
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
            if chain_id == 137: 
                gas_price = int(gas_price * 1.5)
            
            gas_limit = 21000
            gas_cost = gas_limit * gas_price
            
            if amount_native is None:
                amount_to_send_wei = balance - gas_cost
            else:
                amount_to_send_wei = w3.to_wei(amount_native, 'ether')
                if balance < (amount_to_send_wei + gas_cost):
                    amount_to_send_wei = balance - gas_cost

            if amount_to_send_wei <= 0:
                raise Exception("Insufficient balance to cover gas fees")

            tx = {
                "nonce": nonce,
                "to": Web3.to_checksum_address(to_address),
                "value": amount_to_send_wei,
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
