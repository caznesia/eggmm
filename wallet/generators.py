

import asyncio
import base58
from eth_account import Account as EthAccount
from solders.keypair import Keypair
from bitcoinrpc.authproxy import AuthServiceProxy

import config
import crypto_utils


from tronpy import Tron
from tronpy.keys import PrivateKey
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey as BtcPrivateKey
import bitcoinutils.constants as btc_constants


from crypto_utils import rpc_async, rpc_btc_async, rpc_doge_async




async def safe_doge_rpc_async(method, *params):
    
    import aiohttp
    url = config.DOGE_RPC_URL
    if not url: return None
    payload = {"method": method, "params": params, "jsonrpc": "2.0", "id": 1}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=5) as resp:
                if resp.status != 200:
                    
                    raise Exception(f"HTTP {resp.status}")
                result = await resp.json()
                return result.get('result')
    except Exception as e:
        
        return None


def ensure_custom_networks():
    
    if "litecoin" not in btc_constants.NETWORK_P2PKH_PREFIXES:
        btc_constants.NETWORK_P2PKH_PREFIXES["litecoin"] = b"\x30"
        btc_constants.NETWORK_WIF_PREFIXES["litecoin"] = b"\xb0"
    
    if "dogecoin" not in btc_constants.NETWORK_P2PKH_PREFIXES:
        btc_constants.NETWORK_P2PKH_PREFIXES["dogecoin"] = b"\x1e"
        btc_constants.NETWORK_WIF_PREFIXES["dogecoin"] = b"\x9e"


def generate_evm_wallet():
    
    account = EthAccount.create()
    return {
        "address": account.address,
        "private_key": account.key.hex()
    }


async def generate_ltc_wallet(deal_id):
    
    label = f"deal_{deal_id}"

    try:
        
        await rpc_async("loadwallet", "rainyday")
    except:
        pass  

    try:
        
        address = await rpc_async("getnewaddress", label)

        
        private_key = await rpc_async("dumpprivkey", address)

        return {
            "address": address,
            "private_key": private_key
        }

    except Exception as e:
        print(f"[LTC-RPC-ERROR] Failed to generate wallet: {e}")
        return None


async def generate_btc_wallet(deal_id):
    
    label = f"deal_{deal_id}"

    try:
        
        await crypto_utils.rpc_btc_async("loadwallet", "rainyday")
        address = await crypto_utils.rpc_btc_async("getnewaddress", label)
        private_key = await crypto_utils.rpc_btc_async("dumpprivkey", address)
        return {"address": address, "private_key": private_key}
    except:
        
        try:
            from bitcoinutils.setup import setup as btc_setup
            from bitcoinutils.keys import PrivateKey as BtcPrivateKey
            btc_setup('mainnet')
            priv = BtcPrivateKey()
            address = priv.get_public_key().get_address().to_string()
            return {"address": address, "private_key": priv.to_wif()}
        except Exception as e:
            print(f"[BTC-GEN-ERROR] {e}")
            return None


def generate_solana_wallet():
    
    kp = Keypair()

    
    secret_key_bytes = bytes(kp)  
    secret_key_b58 = base58.b58encode(secret_key_bytes).decode()

    return {
        "address": str(kp.pubkey()),
        "private_key": secret_key_b58
    }


async def generate_doge_wallet(deal_id):
    
    label = f"deal_{deal_id}"
    print(f"[DOGE-GEN] Starting generation for {label} using RPC: {config.DOGE_RPC_URL}")
    
    try:
        
        address = await safe_doge_rpc_async("getnewaddress", label)
        if address:
            private_key = await safe_doge_rpc_async("dumpprivkey", address)
            if private_key:
                return {"address": address, "private_key": private_key}
        raise Exception("RPC returned no data")
        
    except Exception as e:
        print(f"[DOGE-GEN] RPC Attempt failed: {e}. Falling back to LOCAL generation.")
        
        
        try:
            ensure_custom_networks()
            setup('dogecoin')
            priv = BtcPrivateKey()
            address = priv.get_public_key().get_address().to_string()
            print(f"[DOGE-GEN-LOCAL] Success! Address: {address}")
            return {"address": address, "private_key": priv.to_wif()}
        except Exception as ex:
            print(f"[DOGE-GEN-ERROR] Both RPC and local generation failed: {ex}")
            return None

def generate_tron_wallet():
    
    try:
        priv = PrivateKey.random()
        return {
            "address": priv.public_key.to_base58check_address(),
            "private_key": priv.hex()
        }
    except Exception as e:
        print(f"[TRON-GEN-ERROR] {e}")
        return None

async def generate_wallet_for_currency(deal_id, currency):
    
    c = currency.lower()
    if c == 'ltc':
        return await generate_ltc_wallet(deal_id)
    elif c == 'btc':
        return await generate_btc_wallet(deal_id)
    elif c == 'doge':
        return await generate_doge_wallet(deal_id)
    elif c in [
        'usdt_bep20', 'usdt_polygon', 'ethereum', 'usdt_erc20', 'usdc_erc20', 
        'usdc_bep20', 'usdc_polygon', 'bnb', 'usdc_base', 'usdt_arbitrum', 
        'usdc_arbitrum', 'usdt_optimism', 'usdc_optimism', 'usdt_avalanche', 'usdc_avalanche',
        'shib', 'pepe'
    ]:
        return generate_evm_wallet()
    elif c in ['solana', 'sol', 'usdt_solana', 'usdc_solana', 'wif', 'bonk']:
        return generate_solana_wallet()
    elif c in ['tron', 'usdt_trc20']:
        return generate_tron_wallet()
    else:
        raise ValueError(f"Unsupported currency: {currency}")
