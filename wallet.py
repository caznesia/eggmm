import eth_account
from solders.keypair import Keypair
import base58
import crypto_utils
from tronpy import Tron
from tronpy.keys import PrivateKey


def generate_evm_wallet():
    
    account = eth_account.Account.create()
    return {
        "address": account.address,
        "private_key": account.key.hex()
    }

async def generate_ltc_wallet(deal_id):
    
    label = f"deal_{deal_id}"

    try:
        
        
        await crypto_utils.rpc_async("loadwallet", "rainyday")
    except:
        pass  

    try:
        
        address = await crypto_utils.rpc_async("getnewaddress", label)

        
        private_key = await crypto_utils.rpc_async("dumpprivkey", address)

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
    except:
        pass

    try:
        address = await crypto_utils.rpc_btc_async("getnewaddress", label)
        private_key = await crypto_utils.rpc_btc_async("dumpprivkey", address)

        return {
            "address": address,
            "private_key": private_key
        }

    except Exception as e:
        print(f"[BTC-RPC-ERROR] Failed to generate wallet: {e}")
        return None

def generate_solana_wallet():
    kp = Keypair()

    
    secret_key_bytes = bytes(kp) 
    secret_key_b58 = base58.b58encode(secret_key_bytes).decode()

    return {
        "address": str(kp.pubkey()),
        "private_key": secret_key_b58
    }

def generate_tron_wallet():
    
    priv = PrivateKey.random()
    return {
        "address": priv.public_key.to_base58check_address(),
        "private_key": priv.hex()
    }

async def generate_wallet_for_currency(deal_id, currency):
    
    if currency == 'ltc':
        return await generate_ltc_wallet(deal_id)
    elif currency == 'btc':
        return await generate_btc_wallet(deal_id)
    elif currency in ['usdt_bep20', 'usdt_polygon', 'ethereum', 'usdt_erc20', 'usdc_erc20', 'usdc_bep20', 'usdc_polygon', 'bnb']:
        return generate_evm_wallet()
    elif currency in ['solana', 'sol', 'usdt_solana', 'usdc_solana']:
        return generate_solana_wallet()
    elif currency in ['tron', 'trx', 'usdt_trc20']:
        return generate_tron_wallet()
    else:
        
        raise ValueError(f"Unsupported currency: {currency}")
