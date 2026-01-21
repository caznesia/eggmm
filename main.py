import discord
from discord.ext import commands, tasks
import asyncio
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("RainyBot")
import requests
import datetime
from discord import app_commands
from discord.ui import Modal, TextInput, View, Button, Select
import pytz
import json
import uuid
from PIL import Image
import qrcode
import aiohttp
import time
import chat_exporter
import io
import aiofiles
import base64
import random
import string
import secrets
import base58
import eth_account

from bitcoinrpc.authproxy import AuthServiceProxy

# internal modules
import config
from config import *
from database import *
from wallet import *
from crypto_utils import *
from bot_utils import *
from services import *
from services.image_service import generate_handshake_image
from utils.confirmation_utils import get_evm_confirmations, get_solana_confirmations
from handlers import *
from services.audit_service import audit_service
from services.reputation_service import reputation_service
from services.notification_service import notification_service
from services.achievement_service import achievement_service
from services.localization_service import localization_service

# Initialize global RPC for legacy support
rpc = AuthServiceProxy(RPC_URL)

# =====================================================
# GLOBAL VARIABLES
# =====================================================

TICKET_LOCK = asyncio.Lock()
pending_force_actions = {}
bot = commands.AutoShardedBot(command_prefix="!", intents=discord.Intents.all(), help_command=None)

async def global_interaction_check(interaction: discord.Interaction) -> bool:
    if blacklist_service.is_blacklisted(interaction.user.id):
        embed = discord.Embed(title="You are blacklisted from our services!", description="Appeal this in <#1428193038588579880>", color=discord.Color.red())
        try: await interaction.response.send_message(embed=embed, ephemeral=True)
        except: pass
        return False
    return True

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Global error handler for all application commands."""
    if isinstance(error, app_commands.CommandOnCooldown):
        msg = f"⏱️ **Cooldown Active**\nPlease wait `{error.retry_after:.1f}s` before using this command again."
        return await (interaction.response.send_message(msg, ephemeral=True) if not interaction.response.is_done() else interaction.followup.send(msg, ephemeral=True))
    
    if isinstance(error, app_commands.MissingPermissions):
        msg = "🚫 **Permission Denied**\nYou do not have the required permissions to execute this command."
        return await (interaction.response.send_message(msg, ephemeral=True) if not interaction.response.is_done() else interaction.followup.send(msg, ephemeral=True))

    # Log unexpected errors for developers
    logger.error(f"[Interaction Error] {error}")
    
    # Generic failure response
    msg = "⚠️ **System Error**\nAn unexpected error occurred. The development team has been notified. Please try again later."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)
    except: pass

async def setup_hook():
    # 0. One-time Migration from data.json to Database
    try:
        if os.path.exists("data.json"):
            logger.info("[MIGRATION] legacy data.json found. Migrating to database...")
            with open("data.json", "r") as f:
                legacy_data = json.load(f)
            save_all_data(legacy_data) # This now saves to DB via database.py
            os.rename("data.json", "data.json.migrated")
            logger.info("[MIGRATION] Migration complete. data.json moved to data.json.migrated.")
        else:
            # Pre-load Global Data Cache from DB if no migration needed
            load_all_data() 
            logger.info("[INFO] Global deal data cache pre-warmed from DB.")
    except Exception as e:
        logger.error(f"[ERROR] Migration/Pre-load failed: {e}")

    # 1. Pre-warm Blacklist Cache (Database call)
    try:
        blacklist_service._load_cache()
        logger.info("[INFO] Blacklist cache pre-warmed.")
    except Exception as e:
        logger.error(f"[ERROR] Blacklist pre-warm failed: {e}")

    # 2. Pre-warm Deal Counter Cache (File I/O)
    try:
        load_counter()
        logger.info("[INFO] Counter cache pre-warmed.")
    except Exception as e:
        logger.error(f"[ERROR] Counter pre-warm failed: {e}")

    bot.tree.interaction_check = global_interaction_check
    
    # Register Persistent Views for Restart Tolerance
    bot.add_view(StartDealView())
    bot.add_view(SendButton())
    bot.add_view(ConfButtons())
    bot.add_view(AmountConButton())
    bot.add_view(CancelConButton())
    bot.add_view(ReleaseButton())
    bot.add_view(AddyButtons())
    
    logger.info("[INFO] Global interaction check and Persistent Views registered.")

bot.setup_hook = setup_hook
# Global session and pricing functions are now managed in services.price_service
# Optimized I/O functions now served from database.py caching layer
# Redundant load_all_data / save_all_data removed from main.py



# Helper functions load_counter, save_counter, get_deal_by_dealid are now imported from database.py




# Redundant channel/address lookup helpers removed here as they are imported from database.py



async def deal_id_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for deal_id, prioritizing the current channel's deal."""
    choices = []
    
    # Check if we are in a deal channel
    did, _ = get_deal_by_channel(interaction.channel_id)
    if did:
        choices.append(app_commands.Choice(name=f"Current Ticket: {did}", value=did))
    
    # Discord limits to 25 choices
    return choices









# safe_rpc_call is imported from crypto_utils.py (async version)



import time




def dbg(msg):
    logger.debug(f"[LTC-DEBUG] {msg}")

def format_crypto_amount(amount):
    """Formats crypto amount to avoid scientific notation and show relevant decimals."""
    if amount is None: return "0.0"
    try:
        # Avoid scientific notation for small amounts
        return f"{float(amount):.8f}".rstrip('0').rstrip('.') or "0.0"
    except:
        return str(amount)

def get_currency_info(currency):
    """Returns metadata (name, icon) for a given currency."""
    currency_data = {
        'ltc': {
            'name': 'Litecoin (LTC)',
            'icon': 'https://cryptologos.cc/logos/litecoin-ltc-logo.png'
        },
        'usdt_bep20': {
            'name': 'USDT (BEP20)',
            'icon': 'https://cryptologos.cc/logos/tether-usdt-logo.png'
        },
        'usdt_polygon': {
            'name': 'USDT (Polygon)',
            'icon': 'https://cryptologos.cc/logos/tether-usdt-logo.png'
        },
        'usdt': {
            'name': 'USDT',
            'icon': 'https://cryptologos.cc/logos/tether-usdt-logo.png'
        },
        'sol': {
            'name': 'Solana (SOL)',
            'icon': 'https://cryptologos.cc/logos/solana-sol-logo.png'
        },
        'solana': {
            'name': 'Solana (SOL)',
            'icon': 'https://cryptologos.cc/logos/solana-sol-logo.png'
        },
        'eth': {
            'name': 'Ethereum (ETH)',
            'icon': 'https://cryptologos.cc/logos/ethereum-eth-logo.png'
        },
        'ethereum': {
            'name': 'Ethereum (ETH)',
            'icon': 'https://cryptologos.cc/logos/ethereum-eth-logo.png'
        }
    }
    key = str(currency).lower()
    return currency_data.get(key, {'name': currency.upper() if currency else "MM", 'icon': None})



async def get_gas_balance(address, currency):
    """Return BNB (for BEP20) or MATIC (for Polygon) balance using AsyncWeb3"""
    from web3 import AsyncWeb3, AsyncHTTPProvider
    try:
        if currency == "usdt_bep20":
            for rpc in BEP20_RPC_URLS:
                w3 = None
                try:
                    w3 = AsyncWeb3(AsyncHTTPProvider(rpc, request_kwargs={"timeout": 5}))
                    if not await w3.is_connected(): continue
                    bal = await w3.eth.get_balance(address)
                    return float(w3.from_wei(bal, 'ether'))
                except:
                    continue
                finally:
                    if w3 is not None:
                        try: await w3.provider.session.close()
                        except: pass
        elif currency == "usdt_polygon":
            for rpc in POLYGON_RPC_URLS:
                w3 = None
                try:
                    w3 = AsyncWeb3(AsyncHTTPProvider(rpc, request_kwargs={"timeout": 5}))
                    if not await w3.is_connected(): continue
                    bal = await w3.eth.get_balance(address)
                    return float(w3.from_wei(bal, 'ether'))
                except:
                    continue
                finally:
                    if w3 is not None:
                        try: await w3.provider.session.close()
                        except: pass
    except Exception as e:
        logger.error(f"Gas balance error: {e}")

    return 0.0



    return 0.0



async def safe_respond(interaction, *, content=None, embed=None, view=None, ephemeral=False, defer=False, edit_original=False, send_modal=None):

    try:

        if send_modal:

            if not interaction.response.is_done():

                await interaction.response.send_modal(send_modal)

                return True

            return False

        elif defer:

            if not interaction.response.is_done():

                await interaction.response.defer(ephemeral=ephemeral)

            return True

        elif edit_original and interaction.message:

            await interaction.message.edit(content=content, embed=embed, view=view)

            return True

        elif not interaction.response.is_done():

            kwargs = {}

            if content is not None:

                kwargs['content'] = content

            if embed is not None:

                kwargs['embed'] = embed

            if view is not None:

                kwargs['view'] = view

            kwargs['ephemeral'] = ephemeral

            await interaction.response.send_message(**kwargs)

            return True

        else:

            await interaction.followup.send(content=content, embed=embed, view=view, ephemeral=ephemeral)

            return True

    except (discord.InteractionResponded, discord.NotFound, discord.HTTPException) as e:

        try:

            if interaction.message and not edit_original:

                await interaction.followup.send(content=content, embed=embed, view=view, ephemeral=ephemeral)

                return True

        except:

            pass

        return False

# =====================================================

# WALLET GENERATION

# =====================================================



def generate_evm_wallet():

    """Generate new EVM wallet for ETH/USDT transactions"""

    account = eth_account.Account.create()

    return {

        "address": account.address,

        "private_key": account.key.hex()

    }



from bitcoinrpc.authproxy import AuthServiceProxy

import asyncio



def rpc_call(method, *params):

    """Single RPC call with a fresh connection (safe for async)."""

    rpc = AuthServiceProxy(RPC_URL, timeout=10)

    return getattr(rpc, method)(*params)





async def rpc_async(method, *params):

    """Async wrapper using threads."""

    return await asyncio.to_thread(rpc_call, method, *params)





async def generate_ltc_wallet(deal_id):

    """Generate LTC wallet safely using a NEW RPC connection for every call."""

    label = f"deal_{deal_id}"



    try:

        # load wallet ALWAYS with new connection

        await rpc_async("loadwallet", "rainyday")

    except:

        pass  # already loaded



    try:

        # SAFE new address

        address = await rpc_async("getnewaddress", label)



        # SAFE private key dump (optional)

        private_key = await rpc_async("dumpprivkey", address)



        return {

            "address": address,

            "private_key": private_key

        }



    except Exception as e:
        logger.error(f"[LTC-RPC-ERROR] Failed to generate wallet: {e}")

        return None

from solders.keypair import Keypair

import base58



def generate_solana_wallet():

    kp = Keypair()



    # Secret key = 64 bytes (32 private + 32 public)

    secret_key_bytes = bytes(kp)  # THIS RETURNS ALL 64 BYTES

    secret_key_b58 = base58.b58encode(secret_key_bytes).decode()



    return {

        "address": str(kp.pubkey()),

        "private_key": secret_key_b58

    }



async def generate_wallet_for_currency(deal_id, currency):

    """Generate wallet based on selected currency"""

    if currency == 'ltc':

        return await generate_ltc_wallet(deal_id)

    elif currency in ['usdt_bep20', 'usdt_polygon', 'ethereum']:

        return generate_evm_wallet()

    elif currency == 'solana':

        return generate_solana_wallet()

    else:

        raise ValueError(f"Unsupported currency: {currency}")



# =====================================================

# ETHEREUM FUNCTIONS

# =====================================================



async def get_eth_balance_parallel(address):
    """Get ETH balance from multiple RPCs. Returns the HIGHEST balance found (solves RPC lag)."""
    from web3 import AsyncWeb3, AsyncHTTPProvider
    
    async def fetch_balance(rpc_url):
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url, request_kwargs={"timeout": 6}))
            if not await w3.is_connected():
                return 0.0
            
            addr_checksum = AsyncWeb3.to_checksum_address(address)
            # Check both latest and pending. Pending allows detection before mining!
            balance_latest = await w3.eth.get_balance(addr_checksum, 'latest')
            balance_pending = await w3.eth.get_balance(addr_checksum, 'pending')
            
            # Use the maximum to catch unconfirmed incoming funds
            balance_wei = max(balance_latest, balance_pending)
            return float(balance_wei / (10 ** 18))
        except:
            return 0.0
        finally:
            if w3 is not None:
                try: await w3.provider.session.close()
                except: pass
            
    # Run ALL in parallel and take the MAX
    tasks = [fetch_balance(url) for url in ETH_RPC_URLS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_results = [r for r in results if isinstance(r, (float, int))]
    if valid_results:
        return max(valid_results)
    return 0.0


async def get_eth_block_number():
    """Get current ETH block number from multiple RPCs using AsyncWeb3"""
    from web3 import AsyncWeb3, AsyncHTTPProvider
    async def fetch_block(rpc_url):
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url, request_kwargs={"timeout": 5}))
            return await w3.eth.block_number
        except:
            return None
        finally:
            if w3 is not None:
                try: await w3.provider.session.close()
                except: pass
    tasks = [fetch_block(url) for url in ETH_RPC_URLS]
    results = await asyncio.gather(*tasks)
    valid = [r for r in results if r is not None]
    return max(valid) if valid else 0

async def get_solana_slot():
    """Get current Solana slot from multiple RPCs"""
    session = await get_session()
    async def fetch_slot(rpc_url):
        try:
            payload = {"jsonrpc": "2.0", "id": 1, "method": "getSlot"}
            async with session.post(rpc_url, json=payload, timeout=5) as r:
                if r.status == 200:
                    data = await r.json()
                    return data.get("result")
        except:
            return None
    tasks = [fetch_slot(url) for url in SOLANA_RPC_URLS]
    results = await asyncio.gather(*tasks)
    valid = [r for r in results if r is not None]
    return max(valid) if valid else 0


async def get_last_eth_txhash(address):
    """Get last incoming ETH transaction hash using robust parallel RPCs."""
    from web3 import AsyncWeb3, AsyncHTTPProvider
    
    addr_lower = address.lower()
    
    async def fetch_last_tx(rpc_url):
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url, request_kwargs={"timeout": 6}))
            if not await w3.is_connected():
                return None
            
            # Get latest block
            latest_block = await w3.eth.block_number
            
            # Check last 50 blocks (~10 minutes) for reliability
            for block_num in range(latest_block, latest_block - 50, -1):
                if block_num <= 0: break
                try:
                    # BLOCK FETCH MUST BE AWAITED
                    block = await w3.eth.get_block(block_num, full_transactions=True)
                    if not block or not block.transactions: continue
                    
                    for tx in block.transactions:
                        if tx.to and tx.to.lower() == addr_lower:
                            return tx.hash.hex()
                except:
                    continue
        except Exception as e:
            logger.debug(f"[ETH-TX-RPC] Error ({rpc_url}): {e}")
        finally:
            if w3 is not None:
                try: await w3.provider.session.close()
                except: pass
        return None

    tasks = [fetch_last_tx(url) for url in ETH_RPC_URLS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for res in results:
        if res and isinstance(res, str):
            return res
            
    return None



async def check_eth_balance_sufficient(address, amount_eth=None, rpc_urls=None):
    """
    Check if an address has sufficient ETH balance to send a transaction.
    Returns (is_sufficient, balance, required, error_message)
    """
    from web3 import AsyncWeb3, AsyncHTTPProvider
    
    if rpc_urls is None:
        rpc_urls = ETH_RPC_URLS
    
    for rpc in rpc_urls:
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(rpc, request_kwargs={"timeout": 5}))
            if not await w3.is_connected():
                continue
            
            checksum_addr = AsyncWeb3.to_checksum_address(address)
            balance = await w3.eth.get_balance(checksum_addr)
            
            # Estimate gas cost
            gas_limit = 21000
            gas_price = await w3.eth.gas_price
            fast_gas_price = int(gas_price * 1.5)
            gas_cost = gas_limit * fast_gas_price
            
            if amount_eth is None:
                # For sweep operations, just need to cover gas
                required = gas_cost
                send_amount = balance - gas_cost
            else:
                send_amount = int(amount_eth * (10**18))
                required = send_amount + gas_cost
            
            balance_eth = balance / (10**18)
            required_eth = required / (10**18)
            gas_cost_eth = gas_cost / (10**18)
            
            if balance < required:
                error_msg = f"Insufficient ETH: Have {balance_eth:.8f} ETH, Need {required_eth:.8f} ETH (gas: {gas_cost_eth:.8f} ETH)"
                return False, balance_eth, required_eth, error_msg
            
            return True, balance_eth, required_eth, None
            
        except Exception as e:
            continue
        finally:
            if w3 is not None:
                try:
                    await w3.provider.session.close()
                except:
                    pass
    
    return False, 0, 0, "Unable to connect to any ETH RPC"



async def send_eth(private_key, to_address, amount=None, nonce=None):
    """Sends ETH using AsyncWeb3 (Supports manual nonce & Detailed logging)."""
    from eth_account import Account
    from web3 import AsyncWeb3, AsyncHTTPProvider

    acc = Account.from_key(private_key)
    from_address = acc.address
    last_error = "No RPC connected"

    # Map currency to correct RPC list (fallback to ETH_RPC_URLS)
    rpc_urls = ETH_RPC_URLS

    for rpc in rpc_urls:
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(rpc, request_kwargs={"timeout": 10}))
            if not await w3.is_connected():
                continue

            from_checksum = AsyncWeb3.to_checksum_address(from_address)
            to_checksum = AsyncWeb3.to_checksum_address(to_address)

            balance = await w3.eth.get_balance(from_checksum)
            
            # Manually manage nonce if provided to prevent parallel collision
            current_nonce = nonce if nonce is not None else await w3.eth.get_transaction_count(from_address)

            gas_limit = 21000  # Standard ETH transfer
            gas_price = await w3.eth.gas_price
            
            # Increase gas price by 50% for fast inclusion
            fast_gas_price = int(gas_price * 1.5)
            gas_cost = gas_limit * fast_gas_price

            if amount is None:
                # Sweep all
                send_amount = balance - gas_cost
            else:
                send_amount = int(amount * (10**18))

            # Enhanced error messages with ETH conversion
            if send_amount <= 0:
                balance_eth = balance / (10**18)
                gas_cost_eth = gas_cost / (10**18)
                last_error = f"Insufficient ETH balance: {balance} wei ({balance_eth:.8f} ETH) < {gas_cost} wei ({gas_cost_eth:.8f} ETH) gas cost"
                logger.error(f"[ETH] {last_error}")
                continue

            if balance < (send_amount + gas_cost):
                balance_eth = balance / (10**18)
                required = send_amount + gas_cost
                required_eth = required / (10**18)
                send_amount_eth = send_amount / (10**18)
                gas_cost_eth = gas_cost / (10**18)
                last_error = f"Insufficient ETH balance: {balance} < {required} (Balance: {balance_eth:.8f} ETH, Need: {required_eth:.8f} ETH = {send_amount_eth:.8f} amount + {gas_cost_eth:.8f} gas)"
                logger.error(f"[ETH] {last_error}")
                continue

            tx = {
                "nonce": current_nonce,
                "to": to_checksum,
                "value": send_amount,
                "gas": gas_limit,
                "gasPrice": fast_gas_price,
                "chainId": 1 # Ethereum Mainnet
            }

            signed_tx = w3.eth.account.sign_transaction(tx, private_key)
            
            # Handle different versions of signed_tx attribute names
            raw_tx = getattr(signed_tx, "raw_transaction", getattr(signed_tx, "rawTransaction", None))
            if raw_tx is None:
                raise Exception("Unable to get raw TX bytes from signed transaction")

            tx_hash = await w3.eth.send_raw_transaction(raw_tx)
            logger.info(f"[ETH] Success on {rpc}: {tx_hash.hex()}")
            return tx_hash.hex()

        except Exception as e:
            last_error = f"RPC {rpc} general error: {e}"
            logger.error(f"[ETH] {last_error}")
            continue
        finally:
            # Ensure provider session is closed to prevent warnings
            if w3 is not None:
                try:
                    await w3.provider.session.close()
                except:
                    pass

    raise Exception(f"ETH Withdrawal Failed: {last_error}")



# =====================================================

# PRICE FUNCTIONS

# =====================================================

async def estimate_required_gas(contract_address, private_key, to_address, amount, rpc_urls, decimals):
    """Estimate gas using AsyncWeb3."""
    from eth_account import Account
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
                address=AsyncWeb3.to_checksum_address(contract_address),
                abi=USDT_ABI
            )

            nonce = await w3.eth.get_transaction_count(from_addr)

            tx = await contract.functions.transfer(
                AsyncWeb3.to_checksum_address(to_address),
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
            logger.error(f"Gas estimation failed on RPC: {rpc} {e}")
            continue
        finally:
            if w3 is not None:
                try: await w3.provider.session.close()
                except: pass

    return None



async def get_coingecko_price(currency_key):
    """Get price from CoinGecko using internal currency key mapping"""
    mapping = {
        'ltc': 'litecoin',
        'solana': 'solana',
        'ethereum': 'ethereum',
        'usdt_bep20': 'tether',
        'usdt_polygon': 'tether',
        'bnb': 'binancecoin',
        'matic': 'matic-network',
    }
    cg_id = mapping.get(currency_key.lower(), currency_key.lower())
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd"
    session = await get_session()
    try:
        async with session.get(url, timeout=5) as r:
            if r.status == 200:
                data = await r.json()
                if cg_id in data:
                    return float(data[cg_id]['usd'])
    except: pass
    return None

async def get_cached_price(currency):
    """Get cached price or fetch new one using universal CoinGecko fetcher"""
    current_time = time.time()
    cache_key = f"{currency}_price"
    
    if cache_key in price_cache:
        price, timestamp = price_cache[cache_key]
        if current_time - timestamp < CACHE_DURATION:
            return price
            
    # Try CoinGecko first (User priority)
    new_price = await get_coingecko_price(currency)
    
    # Fallback to parallel fetchers if CG fails
    if new_price is None or new_price <= 0:
        if currency == 'ltc':
            new_price = await get_ltc_price()
        elif currency == 'solana':
            new_price = await get_solana_price()
        elif currency == 'ethereum':
            new_price = await get_ethereum_price()
        elif currency in ['usdt_bep20', 'usdt_polygon']:
            new_price = await get_usdt_price()
        else:
            new_price = 1.0 # Unknown coin

    if new_price and new_price > 0:
        price_cache[cache_key] = (new_price, current_time)
        return new_price
    return 1.0



async def get_usdt_price():
    """Get USDT price using the fastest responding API in parallel"""
    apis = [
        "https://api.binance.com/api/v3/ticker/price?symbol=USDTUSDC", # Proxy for stability
        "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=usd",
        "https://min-api.cryptocompare.com/data/price?fsym=USDT&tsyms=USD",
    ]
    session = await get_session()
    
    async def fetch(url):
        try:
            async with session.get(url, timeout=3) as r:
                if r.status == 200:
                    d = await r.json()
                    if "price" in d: return float(d["price"])
                    if "tether" in d: return float(d["tether"]["usd"])
                    if "USD" in d: return float(d["USD"])
        except: pass
        return None

    tasks = [asyncio.create_task(fetch(u)) for u in apis]
    for task in asyncio.as_completed(tasks):
        res = await task
        if res:
            for t in tasks: t.cancel()
            return res
    return 1.0



async def get_ltc_price():
    """Get LTC price using the fastest responding API in parallel"""
    apis = [
        "https://api.binance.com/api/v3/ticker/price?symbol=LTCUSDT",
        "https://api.coingecko.com/api/v3/simple/price?ids=litecoin&vs_currencies=usd",
        "https://min-api.cryptocompare.com/data/price?fsym=LTC&tsyms=USD",
    ]
    session = await get_session()
    
    async def fetch(url):
        try:
            async with session.get(url, timeout=3) as r:
                if r.status == 200:
                    d = await r.json()
                    if "price" in d: return float(d["price"])
                    if "litecoin" in d: return float(d["litecoin"]["usd"])
                    if "USD" in d: return float(d["USD"])
        except: pass
        return None

    tasks = [asyncio.create_task(fetch(u)) for u in apis]
    for task in asyncio.as_completed(tasks):
        res = await task
        if res:
            for t in tasks: t.cancel()
            return res
    return 80.0



async def get_solana_price():
    """Get SOL price using the fastest responding API in parallel"""
    apis = [
        "https://api.binance.com/api/v3/ticker/price?symbol=SOLUSDT",
        "https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd",
        "https://min-api.cryptocompare.com/data/price?fsym=SOL&tsyms=USD",
    ]
    session = await get_session()
    
    async def fetch(url):
        try:
            async with session.get(url, timeout=3) as r:
                if r.status == 200:
                    d = await r.json()
                    if "price" in d: return float(d["price"])
                    if "solana" in d: return float(d["solana"]["usd"])
                    if "USD" in d: return float(d["USD"])
        except: pass
        return None

    tasks = [asyncio.create_task(fetch(u)) for u in apis]
    for task in asyncio.as_completed(tasks):
        res = await task
        if res:
            for t in tasks: t.cancel()
            return res
    return 150.0



async def get_ethereum_price():
    """Get ETH price using the fastest responding API in parallel"""
    apis = [
        "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT",
        "https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies=usd",
        "https://min-api.cryptocompare.com/data/price?fsym=ETH&tsyms=USD",
    ]
    session = await get_session()
    
    async def fetch(url):
        try:
            async with session.get(url, timeout=3) as r:
                if r.status == 200:
                    d = await r.json()
                    if "price" in d: return float(d["price"])
                    if "ethereum" in d: return float(d["ethereum"]["usd"])
                    if "USD" in d: return float(d["USD"])
        except: pass
        return None

    tasks = [asyncio.create_task(fetch(u)) for u in apis]
    for task in asyncio.as_completed(tasks):
        res = await task
        if res:
            for t in tasks: t.cancel()
            return res
    return 2500.0



async def usd_to_currency_amount(amount_usd, currency):

    """Convert USD to crypto amount using cached prices"""

    rate = await get_cached_price(currency)

    if rate and rate > 0:

        result = amount_usd / rate

        return round(result, 8)

    

    fallback_rates = {

        'ltc': 80.0,

        'usdt_bep20': 1.0,

        'usdt_polygon': 1.0,

        'solana': 150.0,

        'ethereum': 3000.0

    }

    fallback_rate = fallback_rates.get(currency, 1.0)

    result = amount_usd / fallback_rate

    result = float(f"{result:.8f}")

    return result



async def currency_to_usd(amount, currency):

    """Convert crypto amount to USD using cached prices"""

    rate = await get_cached_price(currency)

    if rate and rate > 0:

        result = amount * rate

        return round(result, 2)

    return 0.0



# =====================================================

# GAS FUNCTIONS

# =====================================================



def get_required_gas(currency):

    if currency == "usdt_polygon":

        return POLYGON_GAS_REQUIRED, "MATIC"

    elif currency == "usdt_bep20":

        return BEP20_GAS_REQUIRED, "BNB"

    return 0, ""



async def check_gas_paid(currency, address, rpc_urls):
    """Check if address has enough gas for transactions using AsyncWeb3"""
    from web3 import AsyncWeb3, AsyncHTTPProvider
    for url in rpc_urls:
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(url, request_kwargs={"timeout": 5}))
            if not await w3.is_connected():
                continue
            bal_wei = await w3.eth.get_balance(AsyncWeb3.to_checksum_address(address))
            bal = bal_wei / 1e18

            required_gas, _ = get_required_gas(currency)

            if bal >= required_gas:
                return True

        except:
            continue
        finally:
            if w3 is not None:
                try: await w3.provider.session.close()
                except: pass



    return False





# =====================================================

# SENDING FUNCTIONS

# =====================================================

import asyncio

import logging

from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException



# ---------- LOGGER SETUP ----------

logger = logging.getLogger("LTC_SEND")

logger.setLevel(logging.DEBUG)



handler = logging.StreamHandler()

formatter = logging.Formatter(

    "[%(asctime)s] [%(levelname)s] %(message)s"

)

handler.setFormatter(formatter)

logger.addHandler(handler)





def _send_ltc_sync(sendaddy, private_key, to_address, amount):

    rpc = AuthServiceProxy(
        config.RPC_URL,
        timeout=120
    )



    # Import key once (wallet handles segwit metadata)

    try:

        rpc.importprivkey(private_key, "deal_key", False)

    except:

        pass



    utxos = rpc.listunspent(1, 9999999, [sendaddy])

    if not utxos:

        raise Exception("No UTXO found")



    total_balance = sum(u["amount"] for u in utxos)



    if amount is None or amount > total_balance:
        amount = total_balance

    # FIX: Quantize to 8 decimals to prevent "Invalid amount" RPC error
    # Convert to string first to ensure clean truncation/rounding
    amount = float(f"{amount:.8f}")

    inputs = [{"txid": u["txid"], "vout": u["vout"]} for u in utxos]
    outputs = {to_address: amount}



    raw = rpc.createrawtransaction(inputs, outputs)



    funded = rpc.fundrawtransaction(

        raw,

        {

            "subtractFeeFromOutputs": [0],

            "replaceable": False

        }

    )



    # ✅ WALLET SIGNING (FIX)

    signed = rpc.signrawtransactionwithwallet(funded["hex"])



    if not signed.get("complete"):

        raise Exception(f"Sign failed: {signed}")



    return rpc.sendrawtransaction(signed["hex"])





async def send_ltc(sendaddy, private_key, to_address, amount=None):

    loop = asyncio.get_event_loop()

    return await loop.run_in_executor(

        None,

        _send_ltc_sync,

        sendaddy,

        private_key,

        to_address,

        amount

    )



async def send_usdt(contract_address, private_key, to_address, amount, rpc_urls, decimals, chain_id, nonce=None):
    """Sends USDT using AsyncWeb3 (Supports manual nonce & Detailed logging)."""
    from eth_account import Account
    from web3 import AsyncWeb3, AsyncHTTPProvider

    usdt_abi = [
        {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
        {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
    ]

    acc = Account.from_key(private_key)
    from_address = acc.address
    last_error = "No RPC connected"

    for rpc in rpc_urls:
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(rpc, request_kwargs={"timeout": 10}))
            if not await w3.is_connected():
                continue

            to_checksum = AsyncWeb3.to_checksum_address(to_address)
            contract = w3.eth.contract(AsyncWeb3.to_checksum_address(contract_address), abi=usdt_abi)
            from_checksum = AsyncWeb3.to_checksum_address(from_address)

            balance = await contract.functions.balanceOf(from_checksum).call()

            if amount is None:
                send_amount = balance
            else:
                send_amount = int(amount * (10 ** decimals))

            if send_amount <= 0:
                last_error = f"Invalid amount: {send_amount}"
                continue

            if balance < send_amount:
                # Robustness: If balance is slightly lower (rounding), use max balance
                if balance > 0 and (send_amount - balance) < 100: # 100 units is negligible (0.0001 for 6 decimals)
                     logger.info(f"[EVM] Adjusting dust difference: {send_amount} -> {balance}")
                     send_amount = balance
                else:
                    last_error = f"Balance too low on {rpc}: {balance} < {send_amount}"
                    logger.info(f"[EVM] {last_error}")
                    continue

            # Manually manage nonce if provided to prevent parallel collision
            if nonce is None:
                current_nonce = await w3.eth.get_transaction_count(from_address)
            else:
                current_nonce = nonce

            try:
                estimated_gas = await contract.functions.transfer(to_checksum, send_amount).estimate_gas({"from": from_address})
            except Exception as est_e:
                 last_error = f"Gas estimation failed on {rpc}: {est_e}"
                 logger.info(f"[EVM] {last_error}")
                 continue

            # Increase gas price by 20% to ensure fast inclusion
            current_gas_price = await w3.eth.gas_price
            fast_gas_price = int(current_gas_price * 1.5) # Increased to 1.5x for Polygon safety

            tx = await contract.functions.transfer(to_checksum, send_amount).build_transaction({
                "chainId": chain_id,
                "gas": int(estimated_gas * 1.8), # Increased buffer
                "gasPrice": fast_gas_price,
                "nonce": current_nonce
            })

            signed_tx = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = await w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            logger.info(f"[EVM] Success on {rpc}: {tx_hash.hex()}")
            return tx_hash.hex()

        except Exception as e:
            last_error = f"RPC {rpc} general error: {e}"
            logger.info(f"[EVM] {last_error}")
            continue
        finally:
            # Ensure provider session is closed to prevent warnings
            if w3 is not None:
                try:
                    await w3.provider.session.close()
                except:
                    pass

    raise Exception(f"Withdrawal Failed: {last_error}")





async def send_solana(private_key_b58, to_address, amount):

    """

    Fully stable Solana sender:

    - Auto subtracts rent exemption

    - Auto subtracts network fee

    - Auto adjusts amount so sending never fails

    - Works with solana-rpc.publicnode.com

    """



    import base58

    import aiohttp

    from solders.keypair import Keypair

    from solders.pubkey import Pubkey

    from solders.system_program import TransferParams, transfer

    from solders.transaction import Transaction

    from solders.message import Message

    from solders.hash import Hash  # required for blockhash



    RPC = "https://solana-rpc.publicnode.com"



    # ================================

    # DECODE PRIVATE KEY

    # ================================

    secret_bytes = base58.b58decode(private_key_b58)

    if len(secret_bytes) != 64:

        raise Exception(f"Invalid private key length ({len(secret_bytes)}) — expected 64 bytes")



    keypair = Keypair.from_bytes(secret_bytes)

    pubkey = keypair.pubkey()



    # ================================

    # HELPERS

    # ================================

    async def rpc(method, params):

        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}

        async with aiohttp.ClientSession() as session:

            async with session.post(RPC, json=payload) as r:

                return await r.json()



    # ================================

    # FETCH BALANCE

    # ================================

    balance_res = await rpc("getBalance", [str(pubkey)])

    lamports_balance = balance_res["result"]["value"]



    # ================================

    # FETCH RENT EXEMPTION

    # ================================

    rent_res = await rpc("getMinimumBalanceForRentExemption", [0])

    rent_exempt = rent_res["result"]



    # Minimum network fee (fixed)

    network_fee = 5000  # lamports ≈ 0.000005 SOL



    # ================================

    # CALCULATE MAX SENDABLE

    # ================================

    max_sendable = lamports_balance - rent_exempt - network_fee



    if max_sendable <= 0:

        raise Exception(

            "This wallet does not have enough SOL to send anything "

            f"(balance={lamports_balance}, rent={rent_exempt})."

        )



    requested_lamports = int(amount * 1_000_000_000)



    # Auto adjust if user requested too much

    if requested_lamports > max_sendable:

        print(f"⚠ Adjusting amount from {requested_lamports} → {max_sendable} (max safe)")

        requested_lamports = max_sendable



    if requested_lamports <= 0:

        raise Exception("Requested send amount too small after fee + rent deduction.")



    # ================================

    # GET LATEST BLOCKHASH

    # ================================

    blockhash_res = await rpc("getLatestBlockhash", [{"commitment": "finalized"}])

    blockhash_str = blockhash_res["result"]["value"]["blockhash"]

    blockhash = Hash.from_string(blockhash_str)



    # ================================

    # BUILD TRANSFER INSTRUCTION

    # ================================

    ix = transfer(

        TransferParams(

            from_pubkey=pubkey,

            to_pubkey=Pubkey.from_string(to_address),

            lamports=requested_lamports

        )

    )



    # ================================

    # BUILD TRANSACTION

    # ================================

    msg = Message.new_with_blockhash([ix], pubkey, blockhash)

    tx = Transaction.new_unsigned(msg)

    tx.sign([keypair], blockhash)



    # MUST SEND BASE64 (NOT BASE58)

    import base64

    tx_base64 = base64.b64encode(bytes(tx)).decode()



    # ================================

    # SEND TRANSACTION

    # ================================

    send_res = await rpc("sendTransaction", [tx_base64, {"encoding": "base64"}])



    if "result" in send_res:

        return send_res["result"]  # tx signature



    raise Exception(f"SEND ERROR: {send_res}")



async def send_usdt_wallet_with_gas_embed(interaction, deal_id, currency, address):

    """Send panel with USDT + Gas payment instructions"""



    # Load deal

    data = load_all_data()

    deal = data[deal_id]



    # Amount user must send (USDT)

    usdt_amount = deal["amount"]



    # GAS required based on network

    if currency == "usdt_polygon":

        gas_required = POLYGON_GAS_REQUIRED

        gas_name = "MATIC"

    else:

        gas_required = BEP20_GAS_REQUIRED

        gas_name = "BNB"



    # Save required gas to deal

    deal["gas_required"] = gas_required

    deal["gas_paid"] = False

    data[deal_id] = deal

    save_all_data(data)



    embed = discord.Embed(

        title="Payment Required",

        color=0x0000ff,

        description="Please complete the payments below to continue the deal."

    )



    embed.add_field(

        name="USDT Payment",

        value=f"Send **{usdt_amount} USDT** to:\n{address}",

        inline=False

    )



    embed.set_thumbnail(
        url="https://cdn.discordapp.com/attachments/1438896774243942432/1446526617403920537/discotools-xyz-icon_7.png?ex=69344e64&is=6932fce4&hm=b330f1e3fb9fa6327bbcfcd5cf1e81eb3cf70e5671f8cff6e3bc8a2256e60f89&"
    )

    embed.set_footer(text="Waiting for payment...")



    # Send embed

    await interaction.followup.send(embed=embed)



    # Return for next steps

    return True



async def send_funds_based_on_currency(deal_info, to_address, amount=None, status_msg=None, nonce=None):


    """Send funds based on deal currency"""

    currency = deal_info.get('currency', 'ltc')

    send_address = deal_info.get('address')

    private_key = deal_info.get('private_key')
    
    # Redundant ensure_deal_gas removed (handled in caller send_funds_with_fee)

    if currency == 'ltc':

        if amount is None:

            amount = deal_info.get('ltc_amount')

        return await send_ltc(send_address, private_key, to_address, amount)

    

    elif currency == 'usdt_bep20':

        if amount is None:

            amount = deal_info.get('ltc_amount')

        return await send_usdt(

            USDT_BEP20_CONTRACT, 

            private_key, 

            to_address, 

            amount, 

            BEP20_RPC_URLS, 

            USDT_BEP20_DECIMALS,

            chain_id=56,

            nonce=nonce

        )

    

    elif currency == 'usdt_polygon':

        if amount is None:

            amount = deal_info.get('ltc_amount')

        return await send_usdt(

            USDT_POLYGON_CONTRACT,

            private_key,

            to_address,

            amount,

            POLYGON_RPC_URLS,

            USDT_POLYGON_DECIMALS,

            chain_id=137,

            nonce=nonce

        )

    

    elif currency == 'solana':

        if amount is None:

            amount = deal_info.get('ltc_amount')

        return await send_solana(private_key, to_address, amount)

    

    elif currency == 'ethereum':

        # For ETH, if amount is None, we want to sweep all (send_eth will handle gas deduction)
        # Don't set amount to ltc_amount as that doesn't account for gas properly
        if amount is not None:
            # Only use the specified amount if explicitly provided
            pass  # amount is already set
        # If amount is None, keep it None so send_eth sweeps: balance - gas
        
        return await send_eth(private_key, to_address, amount, nonce=nonce)

    

    else:

        raise ValueError(f"Unsupported currency: {currency}")



# =====================================================

# BALANCE CHECKING FUNCTIONS

# =====================================================


async def send_funds_with_fee(deal_info, to_address, amount=None, status_msg=None):
    """
    Send funds with automatic fee deduction.
    
    If fees are enabled and a fee address is configured for the currency:
    1. Calculate the fee amount
    2. Send fee to the configured fee address
    3. Send remaining amount to the destination address
    
    Returns:
        dict with main_tx, fee_tx, fee_amount, sent_amount
    """
    currency = deal_info.get('currency', 'ltc')
    private_key = deal_info.get('private_key')
    deal_id = deal_info.get('deal_id')
    
    is_sweep = amount is None
    if amount is None:
        amount = deal_info.get('ltc_amount', 0)
    
    # Auto-fund gas for USDT chains before ANY transaction attempt
    if currency in ['usdt_bep20', 'usdt_polygon']:
        if status_msg:
            try:
                await status_msg.edit(embed=discord.Embed(
                    title="Withdrawal Processing",
                    description="*Preparing gas fees...*",
                    color=0x0000ff
                ))
            except: pass
        gas_success = await ensure_deal_gas(deal_info, status_msg=status_msg)
        if not gas_success:
            raise Exception("Failed to fund gas for transaction (Timeout or Error)")

    # Check if fees were already deducted for this deal (prevents double fee on restart)
    if deal_info.get('fee_deducted', False):
        logger.info(f"[FEE] Fee already deducted for deal {deal_id}, skipping fee deduction")
        # For ETH sweep, pass None to send_funds_based_on_currency
        final_amount = None if (is_sweep and currency == 'ethereum') else amount
        main_tx = await send_funds_based_on_currency(deal_info, to_address, final_amount, status_msg=status_msg)
        return {
            'main_tx': main_tx,
            'fee_tx': None,
            'fee_amount': 0,
            'sent_amount': amount,
            'fee_already_deducted': True
        }
    
    # Check if we should deduct fees
    if not should_deduct_fee(currency):
        # For ETH sweep, pass None to send_funds_based_on_currency
        final_amount = None if (is_sweep and currency == 'ethereum') else amount
        main_tx = await send_funds_based_on_currency(deal_info, to_address, final_amount, status_msg=status_msg)
        return {
            'main_tx': main_tx,
            'fee_tx': None,
            'fee_amount': 0,
            'sent_amount': amount
        }
    
    # Calculate fee
    fee_amount, remaining_amount = calculate_fee(amount, currency)
    fee_address = get_fee_address(currency)
    
    logger.info(f"[FEE-TRACE] Amount: {amount}, Fee: {fee_amount}, Remaining: {remaining_amount}, Currency: {currency}")
    
    fee_tx = None

    
    
    # Update status: Signing Transaction
    if status_msg:
        try:
            await status_msg.edit(embed=discord.Embed(
                title="Withdrawal Processing",
                description="*Signing transaction...*",
                color=0x0000ff
            ))
        except: pass
    
    # Fetch initial nonce once for centralized management
    if currency in ['usdt_bep20', 'usdt_polygon', 'ethereum']:
        current_nonce = await get_evm_nonce_parallel(deal_info.get('address'), currency)
        logger.info(f"[FEE] Starting nonce for {currency}: {current_nonce}")
    else:
        current_nonce = None

    try:
        if fee_amount > 0 and fee_address:
            logger.info(f"[FEE] Sending fee of {fee_amount:.8f} {currency} to {fee_address}")
            
            if currency == 'ltc':
                fee_tx = await send_ltc(deal_info.get('address'), private_key, fee_address, fee_amount)
            elif currency == 'usdt_bep20':
                fee_tx = await send_usdt_specific_amount(
                    USDT_BEP20_CONTRACT, private_key, fee_address, 
                    fee_amount, BEP20_RPC_URLS, USDT_BEP20_DECIMALS, chain_id=56,
                    nonce=current_nonce
                )
                if current_nonce is not None: current_nonce += 1
            elif currency == 'usdt_polygon':
                fee_tx = await send_usdt_specific_amount(
                    USDT_POLYGON_CONTRACT, private_key, fee_address,
                    fee_amount, POLYGON_RPC_URLS, USDT_POLYGON_DECIMALS, chain_id=137,
                    nonce=current_nonce
                )
                if current_nonce is not None: current_nonce += 1
            elif currency == 'solana':
                fee_tx = await send_solana(private_key, fee_address, fee_amount)
            elif currency == 'ethereum':
                fee_tx = await send_eth(private_key, fee_address, fee_amount, nonce=current_nonce)
            
            logger.info(f"[FEE] Fee transaction sent: {fee_tx}")
            
            # Mark fee as deducted synchronously to prevent double charging on restart
            if deal_id:
                from database import save_deal_field_sync
                save_deal_field_sync(deal_id, 'fee_deducted', True)
                logger.info(f"[FEE] Marked fee_deducted=True for deal {deal_id} (Sync)")
            
            # Update status: Verifying on blockchain
            if status_msg:
                try:
                    await status_msg.edit(embed=discord.Embed(
                        title="Withdrawal Processing",
                        description="*Verifying on blockchain...*",
                        color=0x0000ff
                    ))
                except: pass

            
            # Wait longer for fee transaction to be mined before sending main tx
            print("[FEE] Waiting 10 seconds for fee transaction to confirm...")
            await asyncio.sleep(10)
    
    except Exception as e:
        logger.info(f"[FEE] Error sending fee: {e}")
        # If fee fails, try sending full amount (no fee)
        # Use sweep mode for ETH if it was a full withdrawal
        final_amount = None if (is_sweep and currency == 'ethereum') else amount
        main_tx = await send_funds_based_on_currency(deal_info, to_address, final_amount, status_msg=status_msg)
        return {
            'main_tx': main_tx,
            'fee_tx': None,
            'fee_amount': 0,
            'sent_amount': amount,
            'fee_error': str(e)
        }
    
    # Update status: Sending main transaction
    if status_msg:
        try:
            await status_msg.edit(embed=discord.Embed(
                title="Withdrawal Processing",
                description="*Sending funds to recipient...*",
                color=0x0000ff
            ))
        except: pass
    
    # Send main funds
    print(f"[FEE] Sending remaining amount: {remaining_amount:.8f} {currency}")
    # For ETH sweep, pass None to sweep the remainder (balance - gas)
    final_amount = None if (is_sweep and currency == 'ethereum') else remaining_amount
    main_tx = await send_funds_based_on_currency(deal_info, to_address, final_amount, status_msg=status_msg, nonce=current_nonce)
    
    return {
        'main_tx': main_tx,
        'fee_tx': fee_tx,
        'fee_amount': fee_amount,
        'sent_amount': remaining_amount
    }


async def send_usdt_specific_amount(contract_address, private_key, to_address, amount, rpc_urls, decimals, chain_id, nonce=None):
    """Send a specific amount of USDT using AsyncWeb3 (Supports manual nonce & Robustness)."""
    from eth_account import Account
    from web3 import AsyncWeb3, AsyncHTTPProvider

    usdt_abi = [
        {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
        {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
    ]

    acc = Account.from_key(private_key)
    from_address = acc.address
    send_amount = int(amount * (10 ** decimals))
    last_error = "No RPC connected"

    for rpc in rpc_urls:
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(rpc, request_kwargs={"timeout": 10}))
            if not await w3.is_connected():
                continue

            to_checksum = AsyncWeb3.to_checksum_address(to_address)
            contract = w3.eth.contract(AsyncWeb3.to_checksum_address(contract_address), abi=usdt_abi)
            from_checksum = AsyncWeb3.to_checksum_address(from_address)
            balance = await contract.functions.balanceOf(from_checksum).call()
            
            if balance < send_amount:
                # Robustness Dust check
                if balance > 0 and (send_amount - balance) < 100:
                    logger.info(f"[EVM-FEE] Adjusting dust: {send_amount} -> {balance}")
                    send_amount = balance
                else:
                    last_error = f"Balance too low on {rpc}: {balance} < {send_amount}"
                    logger.info(f"[EVM-FEE] {last_error}")
                    continue

            if nonce is None:
                current_nonce = await w3.eth.get_transaction_count(from_address)
            else:
                current_nonce = nonce

            try:
                estimated_gas = await contract.functions.transfer(to_checksum, send_amount).estimate_gas({"from": from_address})
            except Exception as est_e:
                last_error = f"Gas estimation failed on {rpc}: {est_e}"
                logger.info(f"[EVM-FEE] {last_error}")
                continue

            # Higher gas price and buffer for reliability
            gas_price = await w3.eth.gas_price
            
            tx = await contract.functions.transfer(to_checksum, send_amount).build_transaction({
                "chainId": chain_id,
                "gas": int(estimated_gas * 1.8),
                "gasPrice": int(gas_price * 1.5),
                "nonce": current_nonce
            })

            signed_tx = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = await w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            logger.info(f"[EVM-FEE] Success on {rpc}: {tx_hash.hex()}")
            return tx_hash.hex()

        except Exception as e:
            last_error = f"RPC {rpc} general error: {e}"
            logger.info(f"[EVM-FEE] {last_error}")
            continue
        finally:
            if w3 is not None:
                try: await w3.provider.session.close()
                except: pass

    raise Exception(f"Fee Transaction Failed: {last_error}")








async def get_usdt_balance_parallel(contract_address, wallet, rpc_urls, decimals):
    """Get USDT balance from multiple RPCs. Returns the HIGHEST balance found."""
    from web3 import AsyncWeb3, AsyncHTTPProvider
    
    async def fetch_balance(rpc_url):
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url, request_kwargs={"timeout": 6}))
            if not await w3.is_connected():
                return 0.0
            
            contract = w3.eth.contract(
                address=AsyncWeb3.to_checksum_address(contract_address),
                abi=USDT_ABI
            )
            
            # For USDT, we also check pending if available (supported on some RPCs)
            try:
                 bal = await contract.functions.balanceOf(AsyncWeb3.to_checksum_address(wallet)).call()
                 return float(bal / (10 ** decimals))
            except:
                 return 0.0
        except:
            return 0.0
        finally:
            if w3 is not None:
                try: await w3.provider.session.close()
                except: pass

    tasks = [fetch_balance(url) for url in rpc_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_results = [r for r in results if isinstance(r, (float, int))]
    if valid_results:
        return max(valid_results)
    return 0.0




async def get_solana_balance_parallel(address):
    """Get Solana balance from multiple RPCs. Returns the HIGHEST balance found."""
    import asyncio
    session = await get_session()
    
    async def fetch_balance(rpc_url):
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [address]
            }
            async with session.post(rpc_url, json=payload, timeout=6) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    balance_lamports = data['result']['value']
                    return float(balance_lamports / 1_000_000_000)
        except: return 0.0
        return 0.0

    tasks = [fetch_balance(url) for url in SOLANA_RPC_URLS]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_results = [r for r in results if isinstance(r, (int, float))]
    return max(valid_results) if valid_results else 0.0



async def get_solana_transactions(address):
    """Get recent transactions for Solana address using fast parallel RPCs"""
    session = await get_session()
    async def fetch_transactions(rpc_url):
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [address, {"limit": 10}]
            }
            async with session.post(rpc_url, json=payload, timeout=6) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    res = data.get('result', [])
                    return res if res else None # Return None if empty to keep looking
        except: pass
        return None

    tasks = [asyncio.create_task(fetch_transactions(url)) for url in SOLANA_RPC_URLS]
    
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if result:
                for t in tasks: t.cancel()
                return result
        except:
            continue
            
    return []



async def get_solana_transaction_details(tx_signature):

    """Get detailed transaction information"""

    import aiohttp

    import asyncio

    

    async def fetch_tx_details(rpc_url):

        try:

            async with aiohttp.ClientSession() as session:

                payload = {

                    "jsonrpc": "2.0",

                    "id": 1,

                    "method": "getTransaction",

                    "params": [tx_signature, {"encoding": "json"}]

                }

                async with session.post(rpc_url, json=payload, timeout=5) as resp:

                    if resp.status == 200:

                        data = await resp.json()

                        return data.get('result')

        except Exception:

            pass

        return None

    

    tasks = [fetch_tx_details(url) for url in SOLANA_RPC_URLS]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    

    for result in results:

        if result:

            return result

    

    return None



# =====================================================

# FINAL UPDATED api_get_status() WITH TATUM + MEMPOOL

# =====================================================

from config import PROXY



def build_proxy_url():

    if not PROXY:

        return None

    return f"http://{PROXY}"



TATUM_LTC_RPC = "https://litecoin-mainnet.gateway.tatum.io/"

TATUM_LTC_HEADERS = {

    "Content-Type": "application/json",

    "x-api-key": "t-66af6dd55d631f0041bd40094f0692f9f4d1"

}

BLOCKCYPHER_KEY = "cddb986"



async def tatum_ltc_balance(session, address):

    try:

        payload = {

            "jsonrpc": "2.0",

            "id": 1,

            "method": "getreceivedbyaddress",

            "params": [address, 0]

        }

        async with session.post(

            TATUM_LTC_RPC,

            json=payload,

            headers=TATUM_LTC_HEADERS,

            timeout=3

        ) as r:

            data = await r.json()

            if "result" in data:

                return float(data["result"])

    except:

        return None



async def blockcypher_ltc_balance(session, address):

    try:

        url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}?token={BLOCKCYPHER_KEY}"

        async with session.get(url, timeout=3) as r:

            if r.status == 200:

                data = await r.json()

                return data.get("balance", 0) / 1e8

    except:

        return None



async def litecoinspace_ltc_balance(session, address):

    """LitecoinSpace with rotating proxy (fastest)"""

    try:

        proxy_url = build_proxy_url()

        url = f"https://litecoinspace.org/api/address/{address}"



        async with session.get(url, proxy=proxy_url, timeout=1.5) as r:

            if r.status != 200:

                return None



            d = await r.json()

            funded = d["chain_stats"]["funded_txo_sum"]

            spent = d["chain_stats"]["spent_txo_sum"]

            return (funded - spent) / 1e8



    except:

        return None



async def tatum_ltc_received(address):

    try:

        async with aiohttp.ClientSession() as session:

            payload = {

                "jsonrpc": "2.0",

                "id": 1,

                "method": "getreceivedbyaddress",

                "params": [address, 0]

            }

            async with session.post(LTC_TATUM_RPC, json=payload, headers=LTC_TATUM_HEADERS, timeout=6) as r:

                data = await r.json()

                if "result" in data:

                    return float(data["result"])

    except:

        pass

    return None



async def tatum_ltc(method, params):

    try:

        async with aiohttp.ClientSession() as session:

            async with session.post(

                TATUM_LTC_RPC,

                headers=TATUM_LTC_HEADERS,

                json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},

                timeout=4,

            ) as r:

                return await r.json()

    except:

        return None





async def fetch_mempool_status(session, address):

    """absolute last fallback (never rate limits)"""

    try:

        url = f"https://mempool.space/api/address/{address}"

        async with session.get(url, timeout=4) as r:

            if r.status != 200:

                return None

            

            d = await r.json()



            conf = (

                d["chain_stats"]["funded_txo_sum"]

                - d["chain_stats"]["spent_txo_sum"]

            ) / 1e8



            unconf = (

                d["mempool_stats"]["funded_txo_sum"]

                - d["mempool_stats"]["spent_txo_sum"]

            ) / 1e8



            return {

                "confirmed": conf,

                "unconfirmed": unconf,

                "txids": [],

                "source": "mempool"

            }

    except:

        return None



async def safe_respond(interaction, *, content=None, embed=None, view=None, ephemeral=False, defer=False, edit_original=False):

    try:

        if defer:

            if not interaction.response.is_done():

                await interaction.response.defer(ephemeral=ephemeral)

            return True

        elif edit_original and interaction.message:

            await interaction.message.edit(content=content, embed=embed, view=view)

            return True

        elif not interaction.response.is_done():

            kwargs = {}

            if content is not None:

                kwargs['content'] = content

            if embed is not None:

                kwargs['embed'] = embed

            if view is not None:

                kwargs['view'] = view

            kwargs['ephemeral'] = ephemeral

            await interaction.response.send_message(**kwargs)

            return True

        else:

            await interaction.followup.send(content=content, embed=embed, view=view, ephemeral=ephemeral)

            return True

    except (discord.InteractionResponded, discord.NotFound, discord.HTTPException) as e:

        try:

            if interaction.message and not edit_original:

                await interaction.followup.send(content=content, embed=embed, view=view, ephemeral=ephemeral)

                return True

        except:

            pass

        return False



async def safe_modal(interaction, modal):

    """Safe way to send modals"""

    try:

        if not interaction.response.is_done():

            await interaction.response.send_modal(modal)

            return True

        return False

    except (discord.InteractionResponded, discord.NotFound, discord.HTTPException):

        return False



async def fetch_tatum_status(address):

    """lightweight fallback when all public APIs fail"""

    try:

        bal = await tatum_ltc("getBalance", [address])

        if not bal or "result" not in bal:

            return None

        

        confirmed = float(bal["result"]) / 1e8



        return {

            "confirmed": confirmed,

            "unconfirmed": 0.0,

            "txids": [],

            "source": "tatum"

        }

    except:

        return None





# =====================================================

# UPDATED MAIN STATUS FUNCTION (DROP-IN REPLACEMENT)

# =====================================================
async def get_balance_for_currency(address, currency):
    """Robust unified balance checker for all currencies."""
    try:
        if currency == 'ltc':
            s = await api_get_status(address)
            return float(s['confirmed'] + s['unconfirmed'])
        elif currency == 'usdt_bep20':
            return await get_usdt_balance_parallel(USDT_BEP20_CONTRACT, address, BEP20_RPC_URLS, USDT_BEP20_DECIMALS)
        elif currency == 'usdt_polygon':
            return await get_usdt_balance_parallel(USDT_POLYGON_CONTRACT, address, POLYGON_RPC_URLS, USDT_POLYGON_DECIMALS)
        elif currency == 'solana':
            return await get_solana_balance_parallel(address)
        elif currency == 'ethereum':
            return await get_eth_balance_parallel(address)
    except Exception as e:
        logger.debug(f"[BalanceHelper] Error checking {currency} for {address}: {e}")
    return 0.0


async def api_get_status(address: str):
    """
    ULTRA-ROBUST parallel LTC balance checker.
    Queries all APIs in parallel and returns the HIGHEST balance (solves API lag).
    """
    proxy_url = build_proxy_url()
    session = await get_session()

    async def fetch_node():
        try:
            unspent = await rpc_async("listunspent", 0, 9999999, [address])
            conf_bal = 0.0
            unconf_bal = 0.0
            for tx in unspent:
                amt = float(tx.get('amount', 0))
                if tx.get('confirmations', 0) > 0: conf_bal += amt
                else: unconf_bal += amt
            return {"confirmed": conf_bal, "unconfirmed": unconf_bal, "total": conf_bal + unconf_bal}
        except: return None

    async def fetch_litecoinspace():
        try:
            url = f"https://litecoinspace.org/api/address/{address}"
            async with session.get(url, proxy=proxy_url, timeout=4) as r:
                if r.status == 200:
                    d = await r.json()
                    conf = (d["chain_stats"]["funded_txo_sum"] - d["chain_stats"]["spent_txo_sum"]) / 1e8
                    unconf = (d["mempool_stats"]["funded_txo_sum"] - d["mempool_stats"]["spent_txo_sum"]) / 1e8
                    return {"confirmed": conf, "unconfirmed": unconf, "total": conf + unconf}
        except: return None

    async def fetch_sochain():
        try:
            url = f"https://chain.so/api/v2/address/LTC/{address}"
            async with session.get(url, proxy=proxy_url, timeout=4) as r:
                if r.status == 200:
                    d = await r.json()
                    data = d["data"]
                    conf = float(data["confirmed_balance"])
                    unconf = float(data["unconfirmed_balance"])
                    return {"confirmed": conf, "unconfirmed": unconf, "total": conf + unconf}
        except: return None

    # Run all in parallel
    tasks = [fetch_node(), fetch_litecoinspace(), fetch_sochain()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid = [r for r in results if isinstance(r, dict)]
    if not valid: return {"confirmed": 0.0, "unconfirmed": 0.0}
    
    # Return the one with the HIGHEST total balance (solved lag)
    best = max(valid, key=lambda x: x['total'])
    return {"confirmed": best['confirmed'], "unconfirmed": best['unconfirmed']}



    return {"confirmed": 0.0, "unconfirmed": 0.0}

async def get_ltc_confirmations(tx_hash):
    """
    Robust parallel LTC confirmation checker.
    Queries all sources in parallel and returns the HIGHEST confirmation count.
    """
    if not tx_hash: return 0
    proxy_url = build_proxy_url()
    session = await get_session()
    
    async def fetch_node():
        try:
            tx_data = await rpc_async("getrawtransaction", tx_hash, 1)
            return int(tx_data.get("confirmations", 0)) if tx_data else 0
        except: return 0

    async def fetch_litecoinspace():
        try:
            url = f"https://litecoinspace.org/api/tx/{tx_hash}"
            async with session.get(url, proxy=proxy_url, timeout=4) as r:
                if r.status == 200:
                    data = await r.json()
                    status = data.get("status", {})
                    if status.get("confirmed"):
                        block_height = status.get("block_height")
                        async with session.get("https://litecoinspace.org/api/blocks/tip/height", proxy=proxy_url, timeout=3) as r2:
                            if r2.status == 200:
                                tip = int(await r2.text())
                                return max(1, tip - block_height + 1)
            return 0
        except: return 0

    async def fetch_blockcypher():
        try:
            url = f"https://api.blockcypher.com/v1/ltc/main/txs/{tx_hash}"
            async with session.get(url, timeout=4) as r:
                if r.status == 200:
                    data = await r.json()
                    return int(data.get("confirmations", 0))
            return 0
        except: return 0

    # Parallel audit
    tasks = [fetch_node(), fetch_litecoinspace(), fetch_blockcypher()]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    valid = [r for r in results if isinstance(r, int)]
    return max(valid) if valid else 0



async def fetch_blockcypher_status(session, address: str):

    try:

        url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}"

        async with session.get(url, timeout=4) as resp:

            if resp.status != 200:

                return None



            data = await resp.json()



            confirmed = data.get("balance", 0) / 1e8

            unconfirmed = data.get("unconfirmed_balance", 0) / 1e8



            txids = []

            for t in data.get("txrefs", []) or []:

                if t.get("tx_hash"):

                    txids.append(t["tx_hash"])

            for t in data.get("unconfirmed_txrefs", []) or []:

                if t.get("tx_hash"):

                    txids.append(t["tx_hash"])



            return {

                "confirmed": confirmed,

                "unconfirmed": unconfirmed,

                "txids": txids,

                "source": "blockcypher"

            }

    except:

        return None





async def fetch_sochain_status(session, address: str):

    try:

        url = f"https://sochain.com/api/v2/address/LTC/{address}"

        async with session.get(url, timeout=4) as resp:

            if resp.status != 200:

                return None

            payload = await resp.json()

            if payload.get("status") != "success":

                return None



            data = payload["data"]



            txids = [t["txid"] for t in data.get("txs", []) if t.get("txid")]



            return {

                "confirmed": float(data.get("confirmed_balance", 0)),

                "unconfirmed": float(data.get("unconfirmed_balance", 0)),

                "txids": txids,

                "source": "sochain"

            }

    except:

        return None



async def fetch_blockchair_status(session, address: str):

    try:

        url = f"https://api.blockchair.com/litecoin/dashboards/address/{address}"

        async with session.get(url, timeout=8) as resp:

            if resp.status != 200:

                return None

            data = await resp.json()

            d = data.get("data", {})

            if not d:

                return None



            key = next(iter(d.keys()))

            addr_info = d[key]["address"]

            txs = d[key].get("transactions", [])



            bal_sat = int(addr_info.get("balance", 0))

            unconf_sat = int(addr_info.get("unconfirmed_balance", 0))



            confirmed = bal_sat / 1e8

            unconfirmed = unconf_sat / 1e8



            return {

                "confirmed": float(confirmed),

                "unconfirmed": float(unconfirmed),

                "txids": txs,

                "source": "blockchair",

            }

    except:

        return None



async def fetch_litecoinspace_txid(session, address: str):

    try:

        url = f"https://litecoinspace.org/api/address/{address}/txs"

        async with session.get(url, timeout=3) as r:

            if r.status != 200:

                return None

            data = await r.json()



            if isinstance(data, list) and len(data) > 0:

                return {

                    "txids": [data[0].get("txid")],

                    "source": "litecoinspace"

                }

    except:

        return None



def get_hash(address):

    endpoint = f"https://litecoinspace.org/api/address/{address}/txs"

    response = requests.get(endpoint)



    if response.status_code != 200:

        return None



    data = response.json()



    if isinstance(data, list) and len(data) > 0:

        latest_tx = data[0]

        return latest_tx.get("txid")

    else:

        return None



# =====================================================

# PAYMENT DETECTION SYSTEM

# =====================================================



import aiohttp

import asyncio

import functools



async def get_ltc_confirmed_balance(address: str):

    """

    FAST confirmed balance checker with:

    1. RPC (instant, best)

    2. LitecoinSpace fallback

    3. BlockCypher fallback

    """



    # 1) TRY NODE FIRST (PRUNE MODE OK)

    try:

        # Use rpc_async to avoid blocking the event loop
        utxos = await rpc_async("listunspent", 1, 999999999, [address])

        total = sum(u["amount"] for u in utxos)

        return float(total)

    except Exception:

        pass



    # 2) FALLBACK → LITECOINSPACE

    try:

        url = f"https://litecoinspace.org/api/address/{address}"

        async with aiohttp.ClientSession() as s:

            async with s.get(url, timeout=5) as r:

                if r.status == 200:

                    data = await r.json()

                    confirmed = data["chain_stats"]["funded_txo_sum"] - data["chain_stats"]["spent_txo_sum"]

                    return confirmed / 1e8

    except:

        pass



    # 3) FALLBACK → BLOCKCYPHER (SLOWER, LAST RESORT)

    try:

        url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}"

        async with aiohttp.ClientSession() as s:

            async with s.get(url, timeout=5) as r:

                if r.status == 200:

                    data = await r.json()

                    bal = data.get("balance", 0)

                    return bal / 1e8

    except:

        pass



    return 0.0



async def run_blocking(func, *args):

    loop = asyncio.get_event_loop()

    partial = functools.partial(func, *args)

    return await loop.run_in_executor(None, partial)



async def get_balance_async(address):
    """Safe, fast, fully non-blocking LTC balance checker (ROBUST)."""
    s = await api_get_status(address)
    return float(s.get("confirmed", 0)), float(s.get("unconfirmed", 0))




def get_balance(address):

    """Get LTC balance from multiple APIs"""

    confirmed = 0.0

    unconfirmed = 0.0



    try:

        r = requests.get(f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}")

        data = r.json()

        confirmed = data.get("balance", 0) / 1e8

        unconfirmed = data.get("unconfirmed_balance", 0) / 1e8

        return confirmed, unconfirmed

    except:

        pass



    try:

        r = requests.get(f"https://api.blockchain.info/balance?active={address}")

        data = r.json().get(address, {})

        confirmed = data.get("final_balance", 0) / 1e8

        unconfirmed = data.get("unconfirmed_balance", 0) / 1e8

        return confirmed, unconfirmed

    except:

        pass



    try:

        r = requests.get(f"https://sochain.com/api/v2/address/LTC/{address}")

        data = r.json()["data"]

        confirmed = float(data["confirmed_balance"])

        unconfirmed = float(data["unconfirmed_balance"])

        return confirmed, unconfirmed

    except:

        pass



    return 0.0, 0.0



async def get_ltc_txid_async(address: str):
    """Get LTC TXID using the fastest responding API in parallel"""
    proxy_url = build_proxy_url()
    session = await get_session()
    
    async def fetch_mempool():
        url = f"https://litecoinspace.org/api/address/{address}/txs/mempool"
        try:
            async with session.get(url, proxy=proxy_url, timeout=5.0) as r:
                if r.status == 200:
                    txs = await r.json()
                    if txs: return [t["txid"] for t in txs]
        except: pass
        return []

    async def fetch_confirmed():
        url = f"https://litecoinspace.org/api/address/{address}/txs"
        try:
            async with session.get(url, proxy=proxy_url, timeout=5.0) as r:
                if r.status == 200:
                    txs = await r.json()
                    if txs: return [t["txid"] for t in txs]
        except: pass
        return []

    async def fetch_blockcypher():
        url = f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}?token={BLOCKCYPHER_KEY}"
        try:
            async with session.get(url, proxy=proxy_url, timeout=5.0) as r:
                if r.status == 200:
                    d = await r.json()
                    all_txs = (d.get("unconfirmed_txrefs") or []) + (d.get("txrefs") or []) # Prefer unconfirmed first
                    if all_txs: return [t["tx_hash"] for t in all_txs]
        except: pass
        return []

    async def fetch_sochain():
        url = f"https://chain.so/api/v2/address/LTC/{address}"
        try:
            async with session.get(url, proxy=proxy_url, timeout=5.0) as r:
                d = await r.json()
                if d.get("status") == "success" and d.get("data") and d["data"].get("txs"): 
                    return [t["txid"] for t in d["data"]["txs"]]
        except: pass
        return []

    tasks = [
        asyncio.create_task(fetch_mempool()),
        asyncio.create_task(fetch_confirmed()),
        asyncio.create_task(fetch_blockcypher()),
        asyncio.create_task(fetch_sochain())
    ]
    for task in asyncio.as_completed(tasks):
        res = await task
        if res:
            for t in tasks: t.cancel()
            return res # Returns list
    return None



async def get_dynamic_gas_price(currency):
    """Fetch current gas price in Wei from RPCs (Async)."""
    if currency == 'usdt_bep20':
        rpc_urls = config.BEP20_RPC_URLS
    elif currency == 'usdt_polygon':
        rpc_urls = config.POLYGON_RPC_URLS
    else:
        return 0

    from web3 import AsyncWeb3, AsyncHTTPProvider
    for rpc in rpc_urls:
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(rpc, request_kwargs={"timeout": 5}))
            if await w3.is_connected():
                return await w3.eth.gas_price
        except:
            continue
        finally:
            if w3 is not None:
                try: await w3.provider.session.close()
                except: pass
    return 0


async def gas_needed_for_currency(currency):
    """
    Dynamically estimate gas needed based on network conditions.
    """
    if currency not in ['usdt_bep20', 'usdt_polygon']:
        return 0.0, ""

    symbol = "MATIC" if currency == 'usdt_polygon' else "BNB"
    
    # 1. Get current gas price
    gas_price = await get_dynamic_gas_price(currency)
    
    # 2. Determine if fee deduction is active (requires 2 tx)
    from services.fee_service import should_deduct_fee
    tx_count = 2 if should_deduct_fee(currency) else 1
    
    # ERC20 transfer gas limit (Standard 65k)
    gas_limit = 65000
    
    # BUFFER: Using a 3x multiplier to ensure gas funding covers actual payout costs.
    # Note: Payouts use 1.8x limit and 1.5x price (2.7x total). 3x provides a safe margin.
    total_gas_needed = gas_limit * tx_count * 3.0
    
    if gas_price == 0:
        # Fallback to config if RPC fails
        fallback_val = config.POLYGON_GAS_REQUIRED if currency == 'usdt_polygon' else config.BEP20_GAS_REQUIRED
        return fallback_val, symbol

    # Calculate total native token needed
    needed_wei = total_gas_needed * gas_price
    # Add a generous 80% buffer to match the send functions (1.5x gas and 1.2x price = 1.8x)
    needed_with_buffer = int(needed_wei * 1.8)
    needed_native = needed_with_buffer / 10**18
    
    return needed_native, symbol




POLYGON_TATUM_RPC = "https://polygon-mainnet.gateway.tatum.io/"

POLYGON_TATUM_HEADERS = {

    "Content-Type": "application/json",

    "Accept-Encoding": "identity",

    "x-api-key": "t-66af6dd55d631f002f9f4d1"  # same key works

}



USDT_POLYGON_CONTRACT = "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"



async def polygon_tatum_rpc(method, params):
    session = await get_session()
    async with session.post(
        POLYGON_TATUM_RPC,
        headers=POLYGON_TATUM_HEADERS,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
        timeout=5
    ) as r:
        return await r.json()





async def get_usdt_polygon_txid_tatum(address):
    """Fetch USDT Polygon TXID using parallel RPC calls (fastest response wins)."""
    from web3 import AsyncWeb3, AsyncHTTPProvider
    import asyncio
    
    address_bare = address.lower().replace("0x", "")
    padded_address = "0x" + address_bare.zfill(64)
    
    async def try_rpc(rpc_url):
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url, request_kwargs={"timeout": 6}))
            if not await w3.is_connected():
                return None
            
            latest = await w3.eth.block_number
            start_block = latest - 1000  # Wider search (~30 mins)
            
            logs = await w3.eth.get_logs({
                "fromBlock": start_block,
                "toBlock": latest,
                "address": AsyncWeb3.to_checksum_address(USDT_POLYGON_CONTRACT),
                "topics": [TRANSFER_TOPIC, None, padded_address]
            })
            
            if logs:
                tx_hash = logs[-1]["transactionHash"].hex()
                if not tx_hash.startswith("0x"):
                    tx_hash = "0x" + tx_hash
                return tx_hash
            return None
        except Exception as e:
            # logger.debug(f"[Pol-TXID] RPC {rpc_url} failed: {e}")
            return None
        finally:
            if w3 is not None:
                try: await w3.provider.session.close()
                except: pass

    # Run all RPCs in parallel, return first success
    tasks = [asyncio.create_task(try_rpc(url)) for url in POLYGON_RPC_URLS]
    
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if result:
                for t in tasks: t.cancel()
                return result
        except:
            continue
    
    return None



TATUM_RPC = "https://bsc-mainnet.gateway.tatum.io/"

TATUM_HEADERS = {

    "Content-Type": "application/json",

    "Accept-Encoding": "identity",

    "x-api-key": "t-66af694f0692f9f4d1"  # <- your real key here

}



USDT_BEP20_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"

TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"





async def tatum_rpc(method, params):

    async with aiohttp.ClientSession() as session:

        async with session.post(

            TATUM_RPC,

            headers=TATUM_HEADERS,

            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}

        ) as r:

            return await r.json()





async def tatum_get_latest_block():

    data = await tatum_rpc("eth_blockNumber", [])

    if "result" in data:

        return int(data["result"], 16)

    return None





async def tatum_get_usdt_logs(start_block, end_block, to_address=None):
    padded_to = None
    if to_address:
        padded_to = "0x" + to_address.lower().replace("0x", "").zfill(64)

    params = [{
        "fromBlock": hex(start_block),
        "toBlock": hex(end_block),
        "address": USDT_BEP20_CONTRACT,
        "topics": [TRANSFER_TOPIC, None, padded_to] if padded_to else [TRANSFER_TOPIC]
    }]
    data = await tatum_rpc("eth_getLogs", params)
    return data.get("result", [])





async def get_usdt_bep20_txid_parallel(address):
    """Fetch USDT BEP20 TXID using parallel RPC calls (fastest response wins)."""
    from web3 import AsyncWeb3, AsyncHTTPProvider
    import asyncio
    
    address_bare = address.lower().replace("0x", "")
    padded_address = "0x" + address_bare.zfill(64)
    
    async def try_rpc(rpc_url):
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(rpc_url, request_kwargs={"timeout": 6}))
            if not await w3.is_connected():
                return None
            
            latest = await w3.eth.block_number
            start_block = latest - 1000  # Wider search (~30 mins)
            
            logs = await w3.eth.get_logs({
                "fromBlock": start_block,
                "toBlock": latest,
                "address": AsyncWeb3.to_checksum_address(USDT_BEP20_CONTRACT),
                "topics": [TRANSFER_TOPIC, None, padded_address]
            })
            
            if logs:
                tx_hash = logs[-1]["transactionHash"].hex()
                if not tx_hash.startswith("0x"):
                    tx_hash = "0x" + tx_hash
                return tx_hash
            return None
        except Exception as e:
            # logger.debug(f"[BEP20-TXID] RPC {rpc_url} failed: {e}")
            return None
        finally:
            if w3 is not None:
                try: await w3.provider.session.close()
                except: pass

    # Run all RPCs in parallel, return first success
    tasks = [asyncio.create_task(try_rpc(url)) for url in BEP20_RPC_URLS]
    
    for task in asyncio.as_completed(tasks):
        try:
            result = await task
            if result:
                for t in tasks: t.cancel()
                return result
        except:
            continue
            
    return None




async def fetch_txid_ultimate(address, currency, max_attempts=8):



    for _ in range(max_attempts):



        # ---------------------------

        # USDT BEP20 → USE TATUM RPC

        # ---------------------------

        if currency == "usdt_bep20":

            txid = await get_usdt_bep20_txid_parallel(address)

            if txid:

                return txid




        # ---------------------------

        # USDT POLYGON → KEEP OLD WORKING

        # ---------------------------

        elif currency == "usdt_polygon":

            txid = await get_usdt_polygon_txid_tatum(address)

            if txid:

                return txid



        # ---------------------------

        # OTHER CHAINS (unchanged)

        # ---------------------------

        elif currency == "ltc":
            # RETURNS LIST
            return await get_ltc_txid_async(address)

            # s = await api_get_status(address)

           # if s.get("txids"):

               # return s["txids"][-1]



        elif currency == "solana":

            txs = await get_solana_transactions(address)

            if txs:

                return txs[0].get("signature")



        elif currency == "ethereum":

            return await get_last_eth_txhash(address)



        await asyncio.sleep(2)



    return None




# ========================================
# AUTO GAS FUNDER
# ========================================
async def auto_fund_gas(address, currency, needed_amount):
    """
    Checks if GAS_SOURCE_PRIVATE_KEY is set.
    Determines chain ID and RPCs based on currency.
    Sends needed_amount (plus a tiny buffer?) of native token to 'address'.
    """
    if not config.GAS_SOURCE_PRIVATE_KEY:
        print("[AutoGas] No GAS_SOURCE_PRIVATE_KEY configured.")
        return False

    gas_key = None
    chain_id = None
    rpc_urls = []
    
    if currency == "usdt_bep20":
        chain_id = 56
        rpc_urls = config.BEP20_RPC_URLS
        gas_key = config.GAS_SOURCE_PRIVATE_KEY_BSC
    elif currency == "usdt_polygon":
        chain_id = 137
        rpc_urls = config.POLYGON_RPC_URLS
        gas_key = config.GAS_SOURCE_PRIVATE_KEY
    else:
        return False

    if not gas_key:
         logger.info(f"[AutoGas] No gas key configured for {currency}")
         return False

    try:
        # Import here to ensure we have the latest
        from crypto_utils import send_native_chain_generic
        
        logger.info(f"[AutoGas] Funding {needed_amount} native to {address} for {currency}...")
        # [DEBUG] Log the source address to help client find the right wallet
        from eth_account import Account
        source_acct = Account.from_key(gas_key)
        logger.info(f"[AutoGas] FUNDING SOURCE: {source_acct.address}")
        
        txid = await send_native_chain_generic(
            gas_key,
            address,
            needed_amount,
            rpc_urls,
            chain_id
        )
        logger.info(f"[AutoGas] Funding Sent! TXID: {txid}")
        return True
    except Exception as e:
        logger.info(f"[AutoGas] Failed to fund gas: {e}")
        return False

async def ensure_deal_gas(deal_info, status_msg=None):
    """
    Ensures the deal wallet has sufficient gas for an EVM transaction.
    """
    currency = deal_info.get('currency')
    if currency not in ['usdt_bep20', 'usdt_polygon']:
        return True

    address = deal_info.get('address')
    # Use the new async gas estimation
    needed, symbol = await gas_needed_for_currency(currency)
    gas_bal = await get_gas_balance(address, currency)
    
    if gas_bal < needed:
        logger.info(f"[AutoGas] Insufficient gas for transaction: {gas_bal:.6f} < {needed:.6f} {symbol}")
        # Fund exactly what's needed plus the buffer already in 'needed'
        fund_amount = float(needed) - float(gas_bal)
        if fund_amount < 0: fund_amount = 0
        
        # Add a tiny bit more for safety when funding from source
        fund_amount = fund_amount * 1.05 

        if config.GAS_SOURCE_PRIVATE_KEY:
            if status_msg:
                try:
                    await status_msg.edit(embed=discord.Embed(
                        description=f"⏳ **Autosending gas fees...** Please wait.\n*(Required: {fund_amount:.6f} {symbol})*", 
                        color=0xffff00
                    ))
                except: pass

            logger.info(f"[AutoGas] Funding {fund_amount:.6f} {symbol} for deal wallet...")
            success = await auto_fund_gas(address, currency, fund_amount)
            if success:
                logger.info(f"[AutoGas] Gas funded, polling for balance confirmation...")
                # Dynamic polling instead of static sleep
                for i in range(12): # Max 60 seconds (12 * 5s)
                    await asyncio.sleep(5)
                    new_bal = await get_gas_balance(address, currency)
                    if new_bal >= needed:
                        logger.info(f"[AutoGas] Gas confirmed after {i*5+5}s")
                        return True
                logger.info(f"[AutoGas] Gas funding timed out after 60s.")
                return False
        else:
            logger.info(f"[AutoGas] No GAS_SOURCE_PRIVATE_KEY configured, skipping auto-fund")
    else:
        logger.info(f"[AutoGas] Gas sufficient: {gas_bal:.6f} {symbol} (needed: {needed:.6f})")
    

    return True

async def sweep_dust_fees(deal_id, deal_info=None):
    """
    Sweeps remaining native token dust (unused gas) to the fee address.
    Should be called just before deal channel deletion.
    """
    try:
        from web3 import AsyncWeb3, AsyncHTTPProvider
        if not deal_info:
            deal_info = load_all_data().get(str(deal_id))
            
        if not deal_info:
            return

        address = deal_info.get('address')
        private_key = deal_info.get('private_key')
        currency = deal_info.get('currency')
        
        if not address or not private_key:
            return

        # Determine chain/native symbol
        chain_type = None
        if currency in ['usdt_bep20']: chain_type = 'usdt_bep20' 
        elif currency in ['usdt_polygon']: chain_type = 'usdt_polygon'
        elif currency == 'ethereum': chain_type = 'ethereum'
        elif currency == 'solana': chain_type = 'solana'
        
        if not chain_type:
            return

        logger.info(f"[Sweep] Checking dust for {deal_id} ({chain_type})...")
        
        # Priority: Dust Sweep Address -> Fee Address
        fee_dest = None
        if chain_type == 'usdt_bep20':
            fee_dest = config.DUST_SWEEP_ADDRESS_BSC
        
        if not fee_dest:
            fee_dest = config.DUST_SWEEP_ADDRESS
            
        if not fee_dest:
             from services.fee_service import get_fee_address
             fee_dest = get_fee_address(chain_type)
             
        if not fee_dest:
            logger.info(f"[Sweep] No sweep address configured for {chain_type}")
            return

        # SWEEP LOGIC
        if chain_type == 'solana':
            # Solana Sweep
            bal = await get_solana_balance_parallel(address)
            # Reserve some for fee
            amount = bal - 0.000005
            if amount > 0.0001: 
                logger.info(f"[Sweep] Sweeping {amount} SOL to {fee_dest}")
                await send_solana(private_key, fee_dest, amount)
                
        elif chain_type in ['usdt_bep20', 'usdt_polygon', 'ethereum']:
            # EVM Sweep (BNB/MATIC/ETH)
            rpc_urls = []
            chain_id = 0
            symbol = ""
            
            if chain_type == 'usdt_bep20':
                rpc_urls = BEP20_RPC_URLS
                chain_id = 56
                symbol = "BNB"
            elif chain_type == 'usdt_polygon':
                rpc_urls = POLYGON_RPC_URLS
                chain_id = 137
                symbol = "MATIC"
            elif chain_type == 'ethereum':
                rpc_urls = config.ETH_RPC_URLS
                chain_id = 1
                symbol = "ETH"

            for rpc in rpc_urls:
                try:
                    w3 = AsyncWeb3(AsyncHTTPProvider(rpc, request_kwargs={"timeout": 5}))
                    if not await w3.is_connected(): continue
                    
                    from_addr = AsyncWeb3.to_checksum_address(address)
                    to_addr = AsyncWeb3.to_checksum_address(fee_dest)
                    
                    balance = await w3.eth.get_balance(from_addr)
                    gas_price = await w3.eth.gas_price
                    gas_limit = 21000
                    cost = gas_limit * gas_price
                    
                    amount_wei = balance - cost
                    if amount_wei > 0:
                        amount_eth = float(AsyncWeb3.from_wei(amount_wei, 'ether'))
                        
                        # Thresholds (don't sweep tiny dust that costs more in gas than its worth)
                        if amount_eth < 0.0005 and symbol == "BNB": return 
                        if amount_eth < 0.01 and symbol == "MATIC": return
                        if amount_eth < 0.0001 and symbol == "ETH": return

                        logger.info(f"[Sweep] Sweeping {amount_eth} {symbol} to {fee_dest}...")
                        
                        tx = {
                            'to': to_addr,
                            'value': amount_wei,
                            'gas': gas_limit,
                            'gasPrice': gas_price,
                            'nonce': await w3.eth.get_transaction_count(from_addr),
                            'chainId': chain_id
                        }
                        
                        signed = w3.eth.account.sign_transaction(tx, private_key)
                        tx_hash = await w3.eth.send_raw_transaction(signed.raw_transaction)
                        logger.info(f"[Sweep] Success! TX: {tx_hash.hex()}")
                        return
                    else:
                        break # Balance < gas cost
                except Exception as e:
                    logger.debug(f"[Sweep] RPC {rpc} error: {e}")
                    continue

    except Exception as e:
        logger.error(f"[Sweep] Error: {e}")


# ========================================

# MAIN PAYMENT CHECK FUNCTION

# ========================================

async def check_payment_multicurrency(address, channel, expected_amount, deal_info, msg=None):

    currency = deal_info.get("currency")
    deal_id = deal_info.get("deal_id")
    buyer = deal_info.get("buyer")
    seller = deal_info.get("seller")

    # FRESH DATA RELOAD (Prevent Stale Args)
    try:
        data = load_all_data()
        if deal_id in data:
            deal_info = data[deal_id]
            # Ensure we persist expectations
            if "expected_crypto_amount" not in deal_info:
                deal_info["expected_crypto_amount"] = float(expected_amount)
                data[deal_id]["expected_crypto_amount"] = float(expected_amount)
                save_all_data(data)
    except: pass

    # MONITOR GUARD
    if not hasattr(bot, 'active_monitors'):
        bot.active_monitors = set()
    
    lock_key = address.lower()
    if lock_key in bot.active_monitors:
        logger.debug(f"[MONITOR] Already monitoring address {address}, skipping duplicate call.")
        return
        
    bot.active_monitors.add(lock_key)

    # If deal is already paid/processed, stop monitoring
    if deal_info.get('paid') or deal_info.get('status') in ['completed', 'cancelled', 'awaiting_withdrawal', 'refunded']:
        logger.debug(f"[CheckPayment] Deal {deal_id[:16]} already processed/paid. Stopping monitoring.")
        bot.active_monitors.discard(lock_key)
        return

    monitoring_start_time = time.time()

    deal_creation_time = deal_info.get("start_time", monitoring_start_time)

    payment_timeout = deal_info.get("payment_timeout", 1200)

    absolute_expiry_time = deal_creation_time + 3600



    gas_warning_sent = False

    last_balance = 0

    rescan_message = None



    while True:

        current_time = time.time()

        monitoring_elapsed = current_time - monitoring_start_time



        # ======================
        # DEAL ABSOLUTE EXPIRY
        # ======================
        # Load fresh deal data for last_activity
        try:
            d_tuple = get_deal_by_channel(channel.id)
            if d_tuple:
                _, current_deal = d_tuple
                last_act = current_deal.get('last_activity', deal_creation_time)
                absolute_expiry_time = last_act + 3600
        except: pass

        if current_time >= absolute_expiry_time:
            # Check if wallet has funds before closing - NEVER close if has funds
            try:
                wallet_balance = await get_balance_for_currency(address, currency)
                if wallet_balance > 0:
                    logger.info(f"[EXPIRY] Deal has funds ({wallet_balance}), skipping expiry - will never close with funds")
                    await asyncio.sleep(30)  # Just wait and continue monitoring
                    continue
            except Exception as e:
                logger.info(f"[EXPIRY] Balance check error: {e}")

            if rescan_message:
                try: await rescan_message.delete()
                except: pass

            await channel.send(
                embed=discord.Embed(
                    title="Deal Expired",
                    description=">>> Ticket has been inactive for 1 hour. Closing.",
                    color=0xff0000
                )
            )
            if msg:
                try: await msg.delete()
                except: pass
            
            # Final data cleanup
            data = load_all_data()
            if deal_id in data:
                del data[deal_id]
                save_all_data(data)
            
            await asyncio.sleep(2)
            await channel.delete()
            
            bot.active_monitors.discard(lock_key)
            return



        # ======================

        # TIMEOUT (NO PAYMENT)

        # ======================

        if monitoring_elapsed >= payment_timeout and rescan_message is None:
            try:
                # Use robust helper instead of strict confirmed only
                total_check = await get_balance_for_currency(address, currency)
                
                # CRITICAL: Only show timeout if API definitely says 0.
                if total_check == 0:
                    remaining = absolute_expiry_time - current_time
                    minutes_left = int(remaining // 60)
                    
                    timeout_embed = discord.Embed(
                        title="Payment Timeout",
                        description=f">>> No payment detected within {payment_timeout//60} minutes.\n\nYou still have {minutes_left} minutes to complete the payment.\n\nClick below to extend payment time by 20 minutes.",
                        color=0xffa500
                    )
                    rescan_message = await channel.send(embed=timeout_embed, view=RescanButton())
            except Exception as e:
                logger.debug(f"[CheckPayment] Timeout check error: {e}")
                pass
            
        # [REMOVED PAUSE LOGIC]
        # We NO LONGER pause checks if a timeout message is showing.
        if rescan_message:
            pass # Keep going, do not continue loop

        await asyncio.sleep(1.5)  # Faster detection (1.5s interval)

        # RE-CHECK PAID STATUS (PREVENT OVERLAP)
        deal_tuple = get_deal_by_channel(channel.id)
        if deal_tuple:
            _, current_deal = deal_tuple
            # CRITICAL: Include ALL post-payment states to stop monitoring immediately
            if current_deal and (current_deal.get('paid') or current_deal.get('status') in ['escrowed', 'completed', 'cancelled', 'awaiting_withdrawal', 'awaiting_confirmation', 'releasing']):
                logger.debug(f"[CheckPayment] Deal {deal_id[:16]} verified or progressing during loop. Stopping.")
                bot.active_monitors.discard(lock_key)
                return
        else:
            # If deal is gone, stop monitoring (or log warning)
            logger.debug(f"[CheckPayment] Deal lost for channel {channel.id}. Stopping.")
            bot.active_monitors.discard(lock_key)
            return



        # ======================

        # MAIN BALANCE CHECK

        # ======================

        try:
            # Determine tolerance (max 1% or flat 0.0001)
            tolerance = min(0.0001, expected_amount * 0.01) if expected_amount > 0 else 0.0001

            if currency == "ltc":
                s = await api_get_status(address)
                total = float(s["confirmed"] + s["unconfirmed"])
                is_confirmed = total >= (expected_amount - tolerance)
            elif currency == "usdt_bep20":
                total = await get_usdt_balance_parallel(USDT_BEP20_CONTRACT, address, BEP20_RPC_URLS, USDT_BEP20_DECIMALS)
                is_confirmed = total >= (expected_amount - tolerance) 
            elif currency == "usdt_polygon":
                total = await get_usdt_balance_parallel(USDT_POLYGON_CONTRACT, address, POLYGON_RPC_URLS, USDT_POLYGON_DECIMALS)
                is_confirmed = total >= (expected_amount - tolerance)
            elif currency == "solana":
                total = await get_solana_balance_parallel(address)
                is_confirmed = total >= (expected_amount - tolerance)
            elif currency == "ethereum":
                total = await get_eth_balance_parallel(address)
                is_confirmed = total >= (expected_amount - tolerance)
            else:
                total = 0
                is_confirmed = False
                
            # Log every check for debugging
            if total > 0 or monitoring_elapsed % 30 < 2:
                logger.debug(f"[MONITOR] Deal {deal_id[:8]} | {currency} | Val: {total} | Expected: {expected_amount} | Confirmed: {is_confirmed}")
                
        except Exception as balance_err:
            print(f"[MONITOR_ERR] Balance check failed for {currency}: {balance_err}")
            await asyncio.sleep(2)
            continue

        # DISMISS TIMEOUT/EXPIRY if funds found
        if total > 0 and rescan_message:
            try: 
                await rescan_message.delete()
                rescan_message = None
            except: pass


        # ======================
        # AUTO-SWITCH CHAIN (USDT)
        # ======================
        if total == 0 and currency in ["usdt_bep20", "usdt_polygon"]:
            try:
                alt_currency = "usdt_polygon" if currency == "usdt_bep20" else "usdt_bep20"
                
                # Check alternative
                if alt_currency == "usdt_bep20":
                     alt_total = await get_usdt_balance_parallel(USDT_BEP20_CONTRACT, address, BEP20_RPC_URLS, USDT_BEP20_DECIMALS)
                else:
                     alt_total = await get_usdt_balance_parallel(USDT_POLYGON_CONTRACT, address, POLYGON_RPC_URLS, USDT_POLYGON_DECIMALS)
                
                # If valid payment found on other chain
                if alt_total > 0:
                     print(f"[AutoSwitch] Funds found on {alt_currency} ({alt_total}). Switching from {currency}.")
                     
                     # 1. Update local vars
                     currency = alt_currency
                     total = alt_total
                     is_confirmed = total >= expected_amount
                     
                     # 2. Update Deal Object
                     deal_info['currency'] = alt_currency
                     
                     # 3. Save to DB
                     data = load_all_data()
                     if deal_id in data:
                         data[deal_id]['currency'] = alt_currency
                         save_all_data(data)
                         
                     # 4. Notify
                     try:
                         sw_embed = discord.Embed(
                             title="Payment Chain Detected",
                             description=f"Detected payment on **{alt_currency.upper().replace('_', ' ')}**. \nSwitching deal currency automatically.",
                             color=0x00ff00
                         )
                         await channel.send(embed=sw_embed)
                     except: pass
            except Exception as e:
                print(f"[AutoSwitch] Error: {e}")



        # DEBUG LOGGING (TEMPORARY)
        logger.debug(f"[DEBUG] Coin: {currency} | Address: {address} | Balance: {total} | Expected: {expected_amount}")

        # NOTE: Gas funding moved to release phase (send_funds_with_fee)
        # Sender pays their own gas when depositing to deal wallet


        # PARTIAL
        logger.debug(f"[DEBUG] Payment check: total={total}, last_balance={last_balance}, total>0={total > 0}, total>last_balance={total > last_balance}")
        if total > 0:
            # If new funds came in since last check
            if total > last_balance:
                payment_txid = None
                last_balance = total
                logger.debug(f"[DEBUG] New balance detected: {total}")
                
                # Feedback: Payment Detected - PREMIUM UI
                if msg:
                    try:
                        currency_meta = get_currency_info(currency)
                        
                        # Calculate rough USD for display
                        usd_approx = 0.0
                        try:
                            # We might not have this function imported or available here context-wise, 
                            # but check_payment_multicurrency is in main.py so it should be fine.
                            # We need to await it.
                            # Use cached price for immediate calculation
                            price = await get_cached_price(currency)
                            usd_approx = float(total) * float(price)
                        except:
                            usd_approx = float(total) # Fallback

                        detect_embed = discord.Embed(
                            title="✨ Verifying Transaction",
                            description=f"We've detected payment of **{format_crypto_amount(total)} {currency_meta['name']}**. \nWaiting for on-chain confirmation before proceeding.",
                            color=0xffaa00
                        )
                        
                        if currency_meta['icon']:
                            detect_embed.set_author(name="Payment Detected", icon_url=currency_meta['icon'])
                        else:
                            detect_embed.set_author(name="Payment Detected", icon_url="https://cdn.discordapp.com/emojis/1324706325112164404.gif")

                        detect_embed.add_field(name="💰 Received", value=f"`{format_crypto_amount(total)}` {currency_meta['name']}", inline=True)
                        detect_embed.add_field(name="🎯 Required", value=f"`{format_crypto_amount(expected_amount)}` {currency_meta['name']}", inline=True)
                        detect_embed.add_field(name="💵 USD Value", value=f"`${usd_approx:.2f}`", inline=True)
                        detect_embed.add_field(name="🔄 Confirmations", value="`⏳ 0/2 Confirmations`", inline=False)
                        detect_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1438896774243942432/1446517314433454342/discotools-xyz-icon.png")
                        detect_embed.set_footer(text="RainyDay MM • Securing your transaction...")

                        # 1. Edit immediately to show detection
                        await msg.edit(embed=detect_embed)
                        
                        # 2. Now try to fetch TXID and update with button if found
                        seen_txids = deal_info.get("_seen_txids", [])
                        temp_txids_list = await fetch_txid_ultimate(address, currency)
                        
                        temp_txid = None
                        if temp_txids_list:
                            if isinstance(temp_txids_list, list):
                                # Pick first one not in seen_txids? OR just the first one if it's the first payment.
                                # For first payment, just pick [0]
                                temp_txid = temp_txids_list[0]
                                # Add to seen
                                if temp_txid not in seen_txids:
                                    seen_txids.append(temp_txid)
                                    deal_info["_seen_txids"] = seen_txids
                                    # Update DB (since we need to remember this for next payment)
                                    data = load_all_data()
                                    data[deal_id]["_seen_txids"] = seen_txids
                                    save_all_data(data)
                            else:
                                temp_txid = temp_txids_list # Legacy/String

                        if temp_txid:
                            payment_txid = temp_txid
                            temp_url = get_explorer_url(currency, temp_txid)
                            if temp_url:
                                d_view = discord.ui.View()
                                d_view.add_item(discord.ui.Button(label="View on Blockchain", url=temp_url))
                                try:
                                    await msg.edit(view=d_view)
                                except:
                                    pass
                    except Exception as e:
                        logger.debug(f"[DEBUG] Error updating detection message: {e}")
                
                # Update deal data
                deal_info["ltc_amount"] = float(total) 
                usd_val = await currency_to_usd(float(total), currency)
                deal_info["amount"] = float(usd_val) 
                
                # Save
                data = load_all_data()
                data[deal_id] = deal_info
                save_all_data(data)
                
                # Calculate difference
                difference = float(expected_amount) - total
                
                # TOLERANCE: Increased to 0.01 (1 cent) for USDT/USD-pegged assets to avoid friction with tiny "dust" differences.
                # Previously it was 0.0001 which was too sensitive to network fee deductions or rounding.
                tolerance = 0.01 if "usdt" in currency.lower() else (expected_amount * 0.001)
                
                if difference > tolerance:
                    print(f"[DEBUG-PARTIAL] Total: {total} | Expected: {expected_amount} | Diff: {difference} | LastNotify: {deal_info.get('last_partial_notification_amount')}")
                    # PARTIAL
                    # JIT check: Don't send partial if deal is already verified/processed
                    d_tup = get_deal_by_channel(channel.id)
                    if d_tup:
                        _, cd = d_tup
                        if cd.get('paid') or cd.get('status') in ['completed', 'cancelled', 'escrowed', 'refunded']:
                             logger.debug(f"[MONITOR] Skipping partial notify for {deal_id[:8]} - state is {cd.get('status')}")
                             bot.active_monitors.discard(lock_key)
                             return

                    # Check if already notified for this amount
                    last_notified = deal_info.get("last_partial_notification_amount", -1)
                    if abs(float(total) - float(last_notified)) < 1e-9:
                         # Already notified for this partial amount, skip embed
                        await asyncio.sleep(1)
                        continue

                    # CLEANUP: Delete previous partial message if exists
                    last_partial_id = deal_info.get("last_partial_msg_id")
                    if last_partial_id:
                        try:
                            old_msg = await channel.fetch_message(int(last_partial_id))
                            await old_msg.delete()
                        except: pass

                    remaining = difference
                    currency_display = currency.upper().replace("_", " ")
                    
                    if remaining < 0.0001: remaining_str = f"{remaining:.8f}"
                    elif remaining < 1: remaining_str = f"{remaining:.6f}"
                    else: remaining_str = f"{remaining:.4f}"
                    
                    embed = discord.Embed(
                        title="⚠ Partial Payment Detected",
                        description=f"Received: {format_crypto_amount(total)} {currency_display}\nExpected: {format_crypto_amount(expected_amount)} {currency_display}\n**Remaining:** {remaining_str} {currency_display}\n\nDo you want to continue by paying the rest, or cancel?",
                        color=0xffaa00
                    )
                    
                    view = PartialPaymentView(deal_id, deal_info, remaining, currency, txid=payment_txid)
                    partial_msg = await channel.send(embed=embed, view=view)
                    
                    # Store ID for future cleanup
                    deal_info["last_partial_msg_id"] = partial_msg.id

                    # Update notification state
                    deal_info["last_partial_notification_amount"] = float(total)
                    data = load_all_data()
                    if deal_id in data:
                        data[deal_id]["last_partial_notification_amount"] = float(total)
                        save_all_data(data)

                    continue
                    


                elif total >= (float(expected_amount) - 0.0001):
                    # JUST-IN-TIME CHECK: Final check of DB before sending message
                    updated_deal_tuple = get_deal_by_channel(channel.id)
                    if updated_deal_tuple:
                        _, updated_deal = updated_deal_tuple
                        if updated_deal.get('paid') or updated_deal.get('status') in ['escrowed', 'completed', 'cancelled', 'awaiting_withdrawal']:
                            logger.debug(f"[MONITOR] JIT check: Deal {deal_id[:8]} already processed. Aborting message.")
                            bot.active_monitors.discard(lock_key)
                            return

                    # JUST-IN-TIME CHECK: Final check of DB before sending message
                    updated_deal_tuple = get_deal_by_channel(channel.id)
                    if updated_deal_tuple:
                        _, updated_deal = updated_deal_tuple
                        if updated_deal.get('paid') or updated_deal.get('status') in ['escrowed', 'completed', 'cancelled', 'awaiting_withdrawal']:
                            logger.debug(f"[MONITOR] JIT check: Deal {deal_id[:8]} already processed. Aborting message.")
                            bot.active_monitors.discard(lock_key)
                            return
                            
                    # CLEANUP: Delete previous partial message if exists (since we are now Full)
                    last_partial_id = deal_info.get("last_partial_msg_id")
                    if last_partial_id:
                        try:
                            old_msg = await channel.fetch_message(int(last_partial_id))
                            await old_msg.delete()
                        except: pass

                    # EXACT FULL PAYMENT - IMMEDIATE PREMIUM UI
                    logger.debug(f"[MONITOR] Full payment detected for {deal_id[:8]}. Proceeding to verification.")
                    
                    # FETCH TXID
                    # Expecting LIST for LTC, String for others? 
                    # fetch_txid_ultimate now returns list for LTC.
                    
                    raw_tx_res = await fetch_txid_ultimate(address, currency)
                    txid = None
                    
                    if raw_tx_res:
                        if isinstance(raw_tx_res, list):
                            # Find the NEW one
                            known = deal_info.get("_seen_txids", [])
                            # Candidates are those in raw_tx_res NOT in known
                            candidates = [t for t in raw_tx_res if t not in known]
                            if candidates:
                                txid = candidates[0] # Prefer new
                            else:
                                txid = raw_tx_res[0] # Fallback to latest
                        else:
                            txid = raw_tx_res

                    # Update USD Value
                    
                    # Compute USD Value
                    usd_val = 0.0
                    try:
                        usd_val = float(total) * float(await get_cached_price(currency))
                    except:
                        usd_val = float(total) # Fallback

                    # Prepare Premium "Verifying" Embed
                    currency_meta = get_currency_info(currency)
                    
                    wait_embed = discord.Embed(
                        title="✨ Verifying Transaction",
                        description=f"We've detected payment of **{format_crypto_amount(total)} {currency_meta['name']}**. \nWaiting for on-chain confirmation before proceeding.",
                        color=0xffaa00 # Rain yellow
                    )
                    
                    if currency_meta['icon']:
                        wait_embed.set_author(name="Payment Detected", icon_url=currency_meta['icon'])
                    else:
                        wait_embed.set_author(name="Payment Detected", icon_url="https://cdn.discordapp.com/emojis/1324706325112164404.gif")

                    wait_embed.add_field(name="💰 Received", value=f"`{format_crypto_amount(total)}` {currency_meta['name']}", inline=True)
                    wait_embed.add_field(name="🎯 Required", value=f"`{format_crypto_amount(expected_amount)}` {currency_meta['name']}", inline=True)
                    wait_embed.add_field(name="💵 USD Value", value=f"${usd_val:.2f}", inline=True)
                    wait_embed.add_field(name="🔄 Confirmations", value="⏳ 0/2 Confirmations", inline=False)
                    
                    wait_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1438896774243942432/1446517314433454342/discotools-xyz-icon.png")
                    wait_embed.set_footer(text="RainyDay MM • Securing your transaction...")

                    wait_view = discord.ui.View()
                    if txid:
                        final_url = get_explorer_url(currency, txid)
                        if final_url:
                            wait_view.add_item(discord.ui.Button(label="View on Blockchain", url=final_url))
                    else:
                        wait_view.add_item(discord.ui.Button(label="Indexing...", style=discord.ButtonStyle.grey, disabled=True))

                    # Update existing message if possible, otherwise send new
                    if msg:
                        try:
                            await msg.edit(embed=wait_embed, view=wait_view)
                        except:
                            msg = await channel.send(embed=wait_embed, view=wait_view)
                    else:
                        msg = await channel.send(embed=wait_embed, view=wait_view)

                    await handle_full_payment(channel, deal_info, total, expected_amount, currency, address, msg, txid)
                    bot.active_monitors.discard(lock_key)
                    return



# ========================================

# PARTIAL PAYMENT HANDLER (Original UI + Fast TXID)

# ========================================

async def handle_partial_payment_fast(channel, deal_info, received, expected, currency, msg, tx_hash):

    """

    PARTIAL PAYMENT HANDLER (Option A)

    - LTC → keep NEW UI & behavior (DO NOT TOUCH)

    - All other coins → restore OLD UI & explorer links

    """



    deal_id = deal_info["deal_id"]

    buyer = deal_info["buyer"]          # RECEIVER

    seller = deal_info["seller"]        # SENDER

    address = deal_info.get("address")



    # Convert to USD

    usd_received = await currency_to_usd(received, currency)

    usd_expected = await currency_to_usd(expected, currency)



    # Save updated amounts

    data = load_all_data()

    data[deal_id]["ltc_amount"] = float(received)

    data[deal_id]["amount"] = float(usd_received)

    save_all_data(data)



    # Display names

    cur_name = {

        "ltc": "LTC",

        "usdt_bep20": "USDT (BEP20)",

        "usdt_polygon": "USDT (Polygon)",

        "solana": "SOL",

        "ethereum": "ETH"

    }.get(currency, "Crypto")



    # ============================================================

    # FORCE TXID DETECTION IF NOT PROVIDED

    # ============================================================

    if not tx_hash:
        try:
                # Legacy flow
            tx_res = await fetch_txid_ultimate(address, currency, max_attempts=12)
            tx_hash = tx_res[0] if isinstance(tx_res, list) and tx_res else tx_res
        except Exception as e:
            logger.error(f"[CheckPayment] TXID fetch failed: {e}")
            tx_hash = None



    # ============================================================

    # SPECIAL CASE → LTC USES YOUR NEW LOGIC (DO NOT TOUCH)

    # ============================================================

    if currency == "ltc":

        # Build NEW UI (your preferred design)

        embed = discord.Embed(

            title="Transaction Detected (Partial)",

            color=0x0000ff,

            description="Received **less** than required. Confirm to proceed."

        )



        if tx_hash:

            explorer = f"https://live.blockcypher.com/ltc/tx/{tx_hash}/"

            embed.add_field(

                name="Transaction Hash",

                value=f"[{tx_hash}]({explorer})",

                inline=False

            )

        else:

            embed.add_field(name="Transaction Hash", value="Indexing...", inline=False)



        embed.add_field(name="Received (LTC)", value=f"`{received} | ${usd_received}`")

        embed.add_field(name="Required (LTC)", value=f"`{expected} | ${usd_expected}`")



        embed.set_thumbnail(

            url="https://cdn.discordapp.com/attachments/1438896774243942432/1446526617403920537/discotools-xyz-icon_7.png"

        )



        if msg:
            # try: await msg.delete()
            # except: pass
            pass



        try:

            history = [m async for m in channel.history(limit=1, oldest_first=True)]

            await history[0].edit(view=ToSButtonsAllInOnee())

        except:

            pass



        await channel.send(f"<@{seller}>", embed=embed, view=ProceedButton())

        await channel.send(embed=discord.Embed(

            title="Waiting for confirmation",

            description="-# Don't pay extra before confirming.",

            color=0xfffff0

        ))

        return



    # ============================================================

    # OLD UI RESTORATION FOR USDT / SOL / ETH (Option A)

    # ============================================================



    # GAS CHECK FOR USDT CHAINS

    if currency in ["usdt_bep20", "usdt_polygon"]:

        needed_gas, gas_symbol = await gas_needed_for_currency(currency)

        gas_balance = await get_gas_balance(address, currency)



        if gas_balance < needed_gas:

            gas_embed = discord.Embed(

                title=f"{gas_symbol} Required For Network Fee",

                color=0x0000ff,

                description=(

                    f"USDT received but **insufficient gas**.\n\n"

                    f"**TXID:** `{tx_hash if tx_hash else 'Indexing...'}`\n"

                    f"**USDT Received:** `{received}`\n"

                    f"**Required Gas:** `{needed_gas:.4f} {gas_symbol}`\n"

                    f"**Current Gas:** `{gas_balance:.6f} {gas_symbol}`\n\n"

                    f"**Send {gas_symbol} to:** `{address}`"

                )

            )

            gas_embed.set_thumbnail(

                url="https://cdn.discordapp.com/attachments/1384928504189026466/1385290221607715038/IMG_1328.png"

            )



            if msg:
                try: await msg.delete()
                except: pass



            await channel.send(embed=gas_embed)

            return



    # ============================================================

    # BUILD OLD UI (Restored)

    # ============================================================

    embed = discord.Embed(

        title="Transaction Detected (Partial)",

        color=0x0000ff,

        description="Received **less** than required. Confirm to proceed."

    )



    # Explorer link restored for all coins

    if tx_hash:

        explorer = {

            "usdt_bep20": f"https://bscscan.com/tx/{tx_hash}",

            "usdt_polygon": f"https://polygonscan.com/tx/{tx_hash}",

            "solana": f"https://solscan.io/tx/{tx_hash}",

            "ethereum": f"https://etherscan.io/tx/{tx_hash}",

        }.get(currency)



        embed.add_field(

            name="Transaction Hash",

            value=f"[{tx_hash}]({explorer})" if explorer else tx_hash,

            inline=False

        )

    else:

        embed.add_field(name="Transaction Hash", value="*Blockchain indexing...*", inline=False)



    embed.add_field(name=f"Received ({cur_name})", value=f"`{received} | ${usd_received}`")

    embed.add_field(name=f"Required ({cur_name})", value=f"`{expected} | ${usd_expected}`")



    # OLD UI Thumbnail restored

    embed.set_thumbnail(

        url="https://cdn.discordapp.com/attachments/1384928504189026466/1385290221607715038/IMG_1328.png"

    )



    # Clean old msg

    if msg:
        # try: await msg.delete()
        # except: pass
        pass



    # Restore ToS UI

    try:

        history = [m async for m in channel.history(limit=1, oldest_first=True)]

        await history[0].edit(view=ToSButtonsAllInOnee())

    except:

        pass



    # Send embed (old style)

    await channel.send(f"<@{buyer}>", embed=embed, view=ProceedButton())



    # Waiting UI restored

    await channel.send(embed=discord.Embed(

        title="Waiting for confirmation",

        description="-# Don't pay extra before confirming.",

        color=0xfffff0

    ))

# ========================================

# FULL PAYMENT HANDLER

# ========================================

async def handle_full_payment(
    channel, deal_info, received_amount, expected_amount,
    currency, address, msg=None, tx_hash=None
):
    # CONCURRENCY GUARD
    if not hasattr(bot, 'active_verifications'):
        bot.active_verifications = set()
    
    lock_key = address.lower()
    if lock_key in bot.active_verifications:
        print(f"[VERIFY] Already verifying address {address}, skipping duplicate call.")
        return
        
    bot.active_verifications.add(lock_key)

    try:
        # Pre-check for completion
        deal_id = deal_info.get('deal_id')
        data = load_all_data()
        deal_data = data.get(deal_id, {})
        # If already paid or finished, stop.
        if deal_data.get('status') in ['completed', 'cancelled', 'awaiting_withdrawal', 'refunded'] or deal_data.get('paid'):
            # if msg:
            #     try: await msg.delete()
            #     except: pass
            return

        buyer_id = deal_info['buyer']
        seller_id = deal_info['seller']
        
        # Calculate initial USD Value
        usd_val = await currency_to_usd(float(received_amount), currency)
        
        # Mark as paid in DB
        data[deal_id]["amount"] = float(usd_val)
        data[deal_id]["ltc_amount"] = float(received_amount)
        data[deal_id]["paid"] = True
        save_all_data(data)

        # UI cleanup: (Removed redundant deletion of the message we use for verification)

        # Display formatting
        currency_meta = {
            "ltc": {"name": "LTC", "icon": "https://cdn.discordapp.com/emojis/1457310421446037599.png"},
            "usdt_bep20": {"name": "USDT (BEP20)", "icon": "https://cdn.discordapp.com/emojis/1457310730423505009.png"},
            "usdt_polygon": {"name": "USDT (Polygon)", "icon": "https://cdn.discordapp.com/emojis/1457310679844524117.png"},
            "solana": {"name": "SOL", "icon": "https://cdn.discordapp.com/emojis/1457310634520608793.png"},
            "ethereum": {"name": "ETH", "icon": "https://cdn.discordapp.com/emojis/1252612760970330143.png"},
        }.get(currency, {"name": currency.upper(), "icon": None})

        # Update Stats & Roles
        try:
            update_user_stats(int(buyer_id), float(usd_val), float(received_amount), currency)
            update_user_stats(int(seller_id), float(usd_val), float(received_amount), currency)
            
            # [GAMIFICATION] Check achievements
            try:
                buyer_obj = channel.guild.get_member(int(buyer_id)) or await bot.fetch_user(int(buyer_id))
                seller_obj = channel.guild.get_member(int(seller_id)) or await bot.fetch_user(int(seller_id))
                if buyer_obj:
                    await achievement_service.check_achievements(buyer_id, buyer_obj)
                if seller_obj:
                    await achievement_service.check_achievements(seller_id, seller_obj)
            except Exception as e:
                print(f"[GAMIFICATION] Error checking achievements: {e}")

            role = channel.guild.get_role(CLIENT_ROLE_ID) if CLIENT_ROLE_ID else None
            if role:
                m1, m2 = channel.guild.get_member(int(buyer_id)), channel.guild.get_member(int(seller_id))
                if m1: await m1.add_roles(role)
                if m2: await m2.add_roles(role)
        except: pass

        # PREPARE PREMIUM WAIT EMBED
        v_wait = discord.ui.View(timeout=None)
        button_added = False
        explorer_url = None
        confs = 0
        max_confs_seen = 0
        
        # Multiple Buttons for Multi-Payment Support
        seen_txids = deal_info.get("_seen_txids", [])
        
        # If no seen_txids but we have tx_hash, use that (Legacy/Single)
        if not seen_txids and tx_hash:
            seen_txids = [tx_hash]
            
        # Ensure current recent one is included if not in seen (Edge Case)
        if tx_hash and tx_hash not in seen_txids:
            seen_txids.append(tx_hash)

        if seen_txids:
            for idx, tx in enumerate(seen_txids):
                url = get_explorer_url(currency, tx)
                if url:
                    # If only 1, use generic label. If multiple, use numbered label.
                    label = "View on Blockchain" if len(seen_txids) == 1 else f"View Payment {idx+1}"
                    v_wait.add_item(discord.ui.Button(label=label, url=url))
                    button_added = True

        if msg:
            wait_embed = msg.embeds[0]
            # Immediate swap to remove old buttons
            try: await msg.edit(view=v_wait)
            except: pass
        else:
            # Fallback creation (shouldn't happen with new flow)
            currency_meta = get_currency_info(currency)
            wait_embed = discord.Embed(
                title="Payment Detected",
                description=f"We've detected payment of **{format_crypto_amount(received_amount)} {currency_meta['name']}**. \nWaiting for on-chain confirmation before proceeding.",
                color=0xffaa00
            )
            if currency_meta['icon']:
                wait_embed.set_author(name="✨ Verifying Transaction", icon_url=currency_meta['icon'])
            else:
                wait_embed.set_author(name="✨ Verifying Transaction", icon_url="https://cdn.discordapp.com/emojis/1324706325112164404.gif")

            wait_embed.add_field(name="💰 Amount", value=f"`{format_crypto_amount(received_amount)}` {currency_meta['name']}", inline=True)
            wait_embed.add_field(name="💵 USD Value", value=f"`${usd_val:.2f}`", inline=True)
            wait_embed.add_field(name="🔄 Confirmations", value="`⏳ 0/2 Confirmations`", inline=False)
            wait_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1438896774243942432/1446517314433454342/discotools-xyz-icon.png")
            wait_embed.set_footer(text="RainyDay MM • Securing your transaction...")
            
            msg = await channel.send(embed=wait_embed, view=v_wait)

        # CONFIRMATION & TXID RETRY LOOP
        current_txid = tx_hash
        
        # [FIX] Ensure embed structure is valid for the loop (must have 3 fields for fields[2] access)
        if len(wait_embed.fields) < 3:
            # Recreate the correct embed structure
            wait_embed = discord.Embed(
                title="Payment Detected",
                description=f"We've detected payment of **{format_crypto_amount(received_amount)} {currency_meta['name']}**. \nWaiting for on-chain confirmation before proceeding.",
                color=0xffaa00
            )
            if currency_meta['icon']:
                wait_embed.set_author(name="✨ Verifying Transaction", icon_url=currency_meta['icon'])
            else:
                wait_embed.set_author(name="✨ Verifying Transaction", icon_url="https://cdn.discordapp.com/emojis/1324706325112164404.gif")

            wait_embed.add_field(name="💰 Amount", value=f"`{received_amount}`\n{currency_meta['name']}", inline=True)
            wait_embed.add_field(name="💵 USD Value", value=f"`${usd_val:.2f}`", inline=True)
            wait_embed.add_field(name="🔄 Confirmations", value="`⏳ 0/2 Confirmations`", inline=False)
            wait_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1438896774243942432/1446517314433454342/discotools-xyz-icon.png")
            wait_embed.set_footer(text="RainyDay MM • Securing your transaction...")
            
            # Update the message to reflect the fixed embed
            if msg:
                try: await msg.edit(embed=wait_embed, view=v_wait)
                except: pass
        
        last_ui_confs = -1  # Track last UI update to avoid redundant edits
        for i in range(240): # Max 12 mins (240 * 3s = 720s)
            try:
                # 1. RETRY TXID if missing
                if not current_txid:
                    res_tx = await fetch_txid_ultimate(address, currency, max_attempts=1)
                    if res_tx:
                        current_txid = res_tx[0] if isinstance(res_tx, list) else res_tx
                        # [FIX] Sync tx_hash so it's available for the final ReleaseButton panel
                        tx_hash = current_txid 
                    if current_txid:
                        explorer_url = get_explorer_url(currency, current_txid)
                
                # 2. Add Button once TXID is found
                if current_txid and not explorer_url:
                    explorer_url = get_explorer_url(currency, current_txid)

                if current_txid and explorer_url and not button_added:
                    v_wait.add_item(discord.ui.Button(label="View on Blockchain", url=explorer_url))
                    button_added = True
                    try: await msg.edit(view=v_wait)
                    except: pass

                # 3. CHECK CONFIRMATIONS (Parallel Strategy)
                tick_confs = 0 
                if currency == "ltc":
                    res = await get_ltc_confirmations(current_txid)
                    if res is not None:
                        tick_confs = res
                        max_confs_seen = max(max_confs_seen, tick_confs)
                        logger.info(f"[VERIFY_LOOP] LTC Confs: {tick_confs} | Max: {max_confs_seen}")
                
                elif currency in ["usdt_polygon", "usdt_bep20", "ethereum"]:
                    # DUAL-TRACK: We check BOTH TXID and Balance simultaneously for maximum reliability
                    rpcs = []
                    if currency == "ethereum": rpcs = ETH_RPC_URLS
                    elif currency == "usdt_bep20": rpcs = BEP20_RPC_URLS
                    elif currency == "usdt_polygon": rpcs = POLYGON_RPC_URLS
                    
                    # Track 1: TXID-based confirmations
                    if current_txid:
                        tick_confs = await get_evm_confirmations(current_txid, rpcs)
                        max_confs_seen = max(max_confs_seen, tick_confs)
                        if tick_confs > 0:
                            logger.info(f"[VERIFY_LOOP] EVM {currency} Confs: {tick_confs} | Max: {max_confs_seen}")
                    
                    # Track 2: Balance-based Heartbeat Fallback (Ensures money isn't lost if indexing lags)
                    try:
                        check_bal = 0
                        smart_tol = min(0.0001, float(expected_amount) * 0.01)
                        if currency == "ethereum":
                            check_bal = await get_eth_balance_parallel(address)
                        else:
                            contract = USDT_POLYGON_CONTRACT if currency == "usdt_polygon" else USDT_BEP20_CONTRACT
                            rpcs = POLYGON_RPC_URLS if currency == "usdt_polygon" else BEP20_RPC_URLS
                            decs = USDT_POLYGON_DECIMALS if currency == "usdt_polygon" else USDT_BEP20_DECIMALS
                            check_bal = await get_usdt_balance_parallel(contract, address, rpcs, decs)
                        
                        # Only trigger if balance is POSITIVE and enough (prevents error-return-0 issues)
                        if check_bal > 0 and check_bal >= (float(expected_amount) - smart_tol):
                            # If balance is full but TXID shows < 1, boost to 1 to show progress
                            if max_confs_seen < 1:
                                max_confs_seen = 1
                                logger.info(f"[VERIFY_LOOP] {currency} Balance found ({check_bal}). Boosting confs to 1.")
                            
                            # If balance is full and we've waited a bit, boost to 2
                            if i > 5 and max_confs_seen < 2: 
                                 max_confs_seen = 2
                                 logger.info(f"[VERIFY_LOOP] {currency} Balance persistent. Force verifying (Pulse 2).")
                    except Exception as bal_e:
                        logger.debug(f"[Heartbeat] Balance fallback error: {bal_e}")

                elif currency == "solana":
                    if current_txid:
                        tick_confs = await get_solana_confirmations(current_txid, SOLANA_RPC_URLS)
                        max_confs_seen = max(max_confs_seen, tick_confs)
                    
                    # Solana Heartbeat Fallback
                    try:
                        check_bal = await get_solana_balance_parallel(address)
                        if check_bal >= (float(expected_amount) - 0.0001):
                            max_confs_seen = max(max_confs_seen, 1)
                            if i > 5: max_confs_seen = 2
                    except: pass

                # Sync confs for UI
                confs = max_confs_seen

                # 4. UPDATE UI (Only when confirmations change to avoid Discord rate limits)
                status_icon = "⏳" if confs < 2 else "✅"
                new_conf_text = f"`{status_icon} {confs}/2 Confirmations`"
                
                # Update UI only if confirmations changed
                if confs != last_ui_confs:
                    try:
                        if len(wait_embed.fields) > 2:
                            wait_embed.set_field_at(2, name="🔄 Confirmations", value=new_conf_text, inline=False)
                            await msg.edit(embed=wait_embed, view=v_wait)
                            last_ui_confs = confs
                            logger.info(f"[VERIFY_UI] Updated UI: {new_conf_text}")
                            if confs >= 2:
                                await asyncio.sleep(1.5)
                    except Exception as ui_err:
                        logger.error(f"[VERIFY_UI] UI Update failed: {ui_err}", exc_info=True)

                logger.info(f"[VERIFY_LOOP] Iteration {i+1}/240 | Deal {deal_id[:8]} | {currency} | Confs: {confs}/{max_confs_seen} | TXID: {current_txid}")
                
                if confs >= 2:
                    break
                    
            except Exception as e:
                logger.error(f"[VERIFY_ERR] Loop error: {e}", exc_info=True)
                await asyncio.sleep(2)

                import traceback
                traceback.print_exc()
                
            await asyncio.sleep(3)  # Reduced API pressure while maintaining responsiveness

        # FINAL STEP: SUCCESS TRANSITION
        if confs < 2:
            logger.warning(f"[VERIFY] Timed out waiting for confirmations for {deal_id}. Aborting.")
            try:
                wait_embed.description = f"⚠️ Verification timed out. We detected {received_amount} {currency} but could not confirm it on-chain within 10 minutes.\n**Please contact support.**"
                wait_embed.color = 0xff0000
                wait_embed.set_field_at(2, name="🔄 Confirmations", value="❌ Timed Out", inline=False)
                await msg.edit(embed=wait_embed, view=None)
            except: pass
            return
        
        final_embed = discord.Embed(
            title="Deal Confirmed ✅",
            description=(
                "**The funds have been successfully secured in our escrow wallet.**\n"
                "The transaction has been verified on the blockchain.\n\n"
                f"**Seller (<@{seller_id}>):**\n"
                "You may now proceed with the delivery of the item/service.\n\n"
                f"**Buyer (<@{buyer_id}>):**\n"
                "Do **NOT** release funds until you have fully received and verified the item."
            ),
            color=0x00ff00
        )
        final_embed.set_author(name="Transaction Verified", icon_url=VERIFIED_ICON_URL)
        
        c_info = get_currency_info(currency)
        c_tag = currency.upper().replace("_", " ")
        final_embed.add_field(name="Amount Secured", value=f"`{received_amount}` {c_tag}\n(`≈ ${usd_val:.2f} USD`)", inline=False)
        
        final_embed.set_footer(text="⚠️ WARNING: Do NOT release funds until you have received and verified the item.")

        v_final = ReleaseButton(txid=tx_hash, currency=currency)

        deals = load_all_data()
        if deal_id in deals:
            deals[deal_id]['status'] = 'escrowed'
            if tx_hash:
                deals[deal_id]['txid'] = tx_hash
            save_all_data(deals)

        # Generate Secure Banner
        file_attachment = None
        try:
            from services.image_service import generate_handshake_image
            
            # Get PFP URLs
            buyer_user = bot.get_user(int(buyer_id))
            seller_user = bot.get_user(int(seller_id))
            
            # Fallback if user not in cache (fetch)
            if not buyer_user:
                try: buyer_user = await bot.fetch_user(int(buyer_id))
                except: pass
            if not seller_user:
                try: seller_user = await bot.fetch_user(int(seller_id))
                except: pass

            # URL or default
            buyer_pfp = "https://cdn.discordapp.com/embed/avatars/0.png"
            seller_pfp = "https://cdn.discordapp.com/embed/avatars/0.png"
            
            if buyer_user:
                buyer_pfp = str(buyer_user.display_avatar.url)
            if seller_user:
                seller_pfp = str(seller_user.display_avatar.url)
            
            banner_bytes = await generate_handshake_image(buyer_pfp, seller_pfp)
            file_attachment = discord.File(banner_bytes, filename="secure_deal.png")
            final_embed.set_image(url="attachment://secure_deal.png")
            # Remove thumbnail if banner is present to avoid clutter, or keep it. User asked for banner.
            # We'll remove thumbnail to match refresh_deal style usually, but code above set it.
            # I will ensure thumbnail logic is removed or overwritten if I didn't include it in this block.
            # I didn't include set_thumbnail in this replacement block, so it won't be set (good).
            
        except Exception as e:
            print(f"Banner generation failed in auto-confirm: {e}")
            # Fallback thumbnail if banner fails
            if c_info['icon']:
                final_embed.set_thumbnail(url=c_info['icon'])

        send_kwargs = {
            "content": f"<@{buyer_id}> <@{seller_id}>",
            "embed": final_embed,
            "view": v_final
        }
        if file_attachment:
            send_kwargs["file"] = file_attachment

        try:
            # Attempt to edit the existing "Payment Detected" message to "Deal Confirmed"
            # This avoids the "deleting panel" effect.
            await msg.edit(**send_kwargs)
        except Exception as edit_e:
            print(f"[VERIFY] Edit failed ({edit_e}), falling back to direct send.")
            try:
                await channel.send(**send_kwargs)
            except Exception as send_e:
                print(f"[VERIFY] Failed to send confirmation embed with attachment: {send_e}")
                # Fallback: Remove file and try again
                if "file" in send_kwargs:
                    del send_kwargs["file"]
                    try:
                        final_embed.set_image(url=None)
                        send_kwargs["embed"] = final_embed 
                        await channel.send(**send_kwargs)
                        print(f"[VERIFY] Successfully sent confirmation embed (fallback mode).")
                    except Exception as fallback_e:
                        print(f"[VERIFY] Critical: Failed to send confirmation embed even after fallback: {fallback_e}")
    finally:
        bot.active_verifications.discard(lock_key)

# =====================================================

# UI COMPONENTS - CURRENCY SELECTION

# =====================================================



class CurrencySelectView(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

        self.add_item(CurrencySelectMenu())



class CurrencySelectMenu(discord.ui.Select):

    def __init__(self):

        options = [

            discord.SelectOption(

                label="Litecoin (LTC)",

                value="ltc",

                emoji="<:LiteCoin:1457310421446037599>"

            ),

            discord.SelectOption(

                label="Ethereum (ETH)",

                value="ethereum",

                emoji="<:SA_ETH_Ethereum:1252612760970330143>"

            ),

            discord.SelectOption(

                label="Solana (SOL)",

                value="solana",

                emoji="<:solana:1457310634520608793>"

            ),

            discord.SelectOption(

                label="USDT Binance Smart Chain (BEP20)",

                value="usdt_bep20",

                emoji="<:USDTBSC:1457310730423505009>"

            ),

            discord.SelectOption(

                label="USDT Polygon (Matic)",

                value="usdt_polygon",

                emoji="<:USDTpolygon:1457310679844524117>"

            )

        ]



        super().__init__(

            placeholder="Select The Cryptocurrency",

            min_values=1,

            max_values=1,

            options=options,

            custom_id="currency_select_menu"

        )




    async def callback(self, interaction: discord.Interaction):
        if blacklist_service.is_blacklisted(interaction.user.id):
            embed = discord.Embed(title="You are blacklisted from our services!", description="Appeal this in <#1428193038588579880>", color=discord.Color.red())
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        selected_currency = self.values[0]
        await interaction.response.send_modal(BuyerSellerModal(selected_currency))



class BuyerSellerModal(Modal, title="Fill properly below!"):

    def __init__(self, currency):

        super().__init__()

        self.currency = currency



    user_id = TextInput(

        label="Enter Seller/Buyer User ID",

        placeholder="Enter the Discord User ID...",

        required=True,

        style=discord.TextStyle.short,

        max_length=50

    )




    async def on_submit(self, interaction: discord.Interaction):
        # 1. Defer IMMEDIATELY to avoid timeout
        await interaction.response.defer(ephemeral=True)

        # 2. Check blacklist (cached now)
        if blacklist_service.is_blacklisted(interaction.user.id):
            embed = discord.Embed(title="You are blacklisted from our services!", description="Appeal this in <#1428193038588579880>", color=discord.Color.red())
            return await interaction.followup.send(embed=embed, ephemeral=True)

        guild = interaction.guild

        user = guild.get_member(int(self.user_id.value))

        if not user:

            return await interaction.followup.send("User not found in this server.", ephemeral=True)



        logger.debug(f"[DEBUG] Looking for Category 1 ID: {CATEGORY_ID_1}")
        logger.debug(f"[DEBUG] Looking for Category 2 ID: {CATEGORY_ID_2}")

        category = guild.get_channel(int(CATEGORY_ID_1))
        acategory = guild.get_channel(int(CATEGORY_ID_2))

        if category:
            logger.debug(f"[DEBUG] Found Category 1: {category.name} ({len(category.channels)} channels)")
        else:
            logger.debug(f"[DEBUG] Category 1 NOT FOUND")
            
        if acategory:
            logger.debug(f"[DEBUG] Found Category 2: {acategory.name} ({len(acategory.channels)} channels)")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        main_cat = None
        if category and isinstance(category, discord.CategoryChannel) and len(category.channels) < 50:
            main_cat = category
        elif acategory and isinstance(acategory, discord.CategoryChannel) and len(acategory.channels) < 50:
            main_cat = acategory
        else:
            print("[DEBUG] No suitable category found or both full.")
            return await interaction.followup.send("All deals are full, please try again later!", ephemeral=True)



        try:
            # FIX: Global Lock for Ticket Creation to prevent race conditions
            async with TICKET_LOCK:
                # Get next deal ID
                counter = load_counter()
                new_channel_number = counter + 1
                deal_prefix = f"auto-{new_channel_number}"
                
                # Check for existing channel with this name (Double safety)
                existing_channel = discord.utils.get(guild.text_channels, name=deal_prefix)
                if existing_channel:
                    # If it conflicts, skip ahead
                    new_channel_number += 1
                    deal_prefix = f"auto-{new_channel_number}"

                # Save new counter IMMEDIATELY
                save_counter(new_channel_number)
                
                # Safe create with error handling
                try:
                    channel = await guild.create_text_channel(name=deal_prefix, category=main_cat, overwrites=overwrites)
                except discord.HTTPException as e:
                    if e.code == 429: # Rate Limit
                         await asyncio.sleep(2) # Wait a bit
                         channel = await guild.create_text_channel(name=deal_prefix, category=main_cat, overwrites=overwrites)
                    else:
                        raise e

            # Generate unique deal ID

            deal_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=64))
            
            # Optimization: Create single deal object and use update_deal
            # No need to load all data!
            new_deal = {
                "channel_id": str(channel.id),

                "seller": "None",  # Now represents RECEIVER
                "buyer": "None",  # Now represents SENDER

                "amount": 0.00,
                "status": "started",
                "role_warning_sent": False,

                "start_time": time.time(),
                "last_activity": time.time(),

                "rescan_count": 0,

                "payment_timeout": 20 * 60,

                "creator_id": str(interaction.user.id),

                "other_user_id": str(user.id),

                "deal_id": deal_id,

                "currency": self.currency
            }
            
            # Efficient save
            update_deal(channel.id, new_deal)



            # Create DM embed with both user information and deal ID
            
            # [OPTIMIZATION] Send DMs in background to avoid blocking interaction
            async def send_dms():
                dm_embed = discord.Embed(
                    title="🎯 New Deal successfully created!",
                    description=(
                        f"Hello! A new secure middleman deal has been initiated.\n"
                        f"Please head over to the deal channel to proceed with the transaction.\n\n"
                        f"**🛡️ Security Tip:** Never share your Deal ID with anyone except staff. "
                        f"This ID is used to recover your transaction if needed."
                    ),
                    color=0x0000ff
                )
                dm_embed.add_field(name="🆔 Deal ID", value=f"```\n{deal_id}\n```", inline=False)
                dm_embed.add_field(name="💬 Deal Channel", value=channel.mention, inline=True)
                dm_embed.add_field(name="💰 Currency", value=f"`{self.currency.upper()}`", inline=True)
                
                p1_rich = get_rich_user_display(guild, interaction.user.id)
                p2_rich = get_rich_user_display(guild, user.id)
                dm_embed.add_field(name="👤 Ticket Creator", value=p1_rich, inline=False)
                dm_embed.add_field(name="👤 Other Participant", value=p2_rich, inline=False)
                dm_embed.set_footer(text="RainyDay MM | Trusted Middleman Service")
                dm_embed.timestamp = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))

                for target in [user, interaction.user]:
                    try:
                        await target.send(embed=dm_embed)
                    except:
                        pass
            
            asyncio.create_task(send_dms())

            # Panel: Deal ID (Dedicated Embed for Channel)
            embed_deal_id = discord.Embed(
                title="Deal ID",
                description=f"```\n{deal_id}\n```\n⚠️ **Save this deal id to recover your deals in case of acc termination, account limit, or lost account.**",
                color=0x0000ff
            )

            logo_url = "https://cdn.discordapp.com/attachments/1383487913186169032/1384932699717898300/Untitled-2.png"
            
            # Panel 1: System / Shield (Restored as requested)
            embed_system = discord.Embed(
                title="RainyDay Auto MiddleMan System",
                description=(
                    "### 🛡️ Secure Transaction Protocol\n"
                    "• This channel is monitored by our automated escrow system.\n"
                    "• All funds are held securely until the buyer confirms receipt.\n"
                    "• Always confirm you have received the goods before releasing funds.\n\n"
                    "### 📝 Deal Context\n"
                    "• **Sender:** `None` (Click to set below)\n"
                    "• **Receiver:** `None` (Click to set below)\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━"
                ),
                color=0x0000ff
            )
            embed_system.set_author(name="RainyDay MM Escrow Services", icon_url=logo_url)
            embed_system.set_thumbnail(url=logo_url)
            embed_system.add_field(
                name="⚠️ Important Note",
                value=(
                    "• Make sure funds will not be released until the goods are fully delivered.\n"
                    "• Always retain the Deal ID to safeguard against potential risks.\n"
                    "• If you encounter any issues, promptly notify us for immediate assistance."
                ),
                inline=False
            )
            embed_system.set_footer(text="RainyDay MM | Secure Trading Enforced", icon_url=logo_url)

            # Panel 3: User Selection
            embed_selection = discord.Embed(
                title="User Selection",
                description=(
                    "**Sender**\n`None`\n\n"
                    "**Receiver**\n`None`"
                ),
                color=0x0000ff
            )
            embed_selection.set_author(name="RainyDay MM", icon_url=logo_url)
            embed_selection.set_thumbnail(url="https://cdn.discordapp.com/attachments/1383487913186169032/1384932699717898300/Untitled-2.png") 

            # Panel 4: Security Advisory (Default English)
            embed_caution = discord.Embed(
                title="⚠️ Be Caution!",
                description="If a seller asks you to send money to their address/UPI QR code first or claims that the bot will charge a fee (our mm service is completely free), be cautious it's most likely a scam. **NEVER PAY DIRECTLY TO THE SELLER.** Report it to the admin immediately, and we'll take action.",
                color=discord.Color.red()
            )

            # Send messages in the requested order: Mention -> DealID -> Shield -> Selection -> Caution
            try:
                await channel.send(content=f"{user.mention} {interaction.user.mention}")
                msg_system = await channel.send(embed=embed_system, view=ToSButtonsAllInOne())
                await channel.send(embed=embed_deal_id)
                await channel.send(embed=embed_selection, view=SendButton())
                await channel.send(embed=embed_caution, view=LangButton())
            except Exception as e:
                await channel.send(f"⚠️ Critical Error sending tickets: {e}")
                print(f"CRITICAL ERROR: {e}")
            
            # Store system message ID for syncing
            new_deal = load_all_data().get(deal_id)
            if new_deal:
                new_deal["system_msg_id"] = msg_system.id
                update_deal(channel.id, new_deal)
            
            await interaction.followup.send(f"Deal created: {channel.mention}", ephemeral=True)



        except Exception as e:

            print(f"Error creating channel: {e}")

            await interaction.followup.send("An error occurred while creating the deal channel.", ephemeral=True)



# =====================================================

# EXISTING UI COMPONENTS (ALL PRESERVED)

# =====================================================



class ToSButton(discord.ui.Button):

    def __init__(self):

        super().__init__(label="Product ToS and Warranty", style=discord.ButtonStyle.primary, custom_id="producttos")



    async def callback(self, interaction: discord.Interaction):

        deal_id, deal = get_deal_by_channel(interaction.channel.id)

        if not deal:

            await interaction.response.send_message("Deal not found.", ephemeral=True)

            return

            

        self.seller_id = deal['seller']  # Now represents RECEIVER

        if interaction.user.id == int(self.seller_id):

           modal = ToSModal()

           await interaction.response.send_modal(modal)

        else:

            await interaction.response.send_message("You are not authorized to use this.", ephemeral=True)



class ToSModal(Modal, title="Please tell properly!"):

    product = TextInput(

        label="Product",

        placeholder="Nitro, OwO, C2I, etc.",

        required=True,

        style=discord.TextStyle.short,

        max_length=40

    )

    tos = TextInput(

        label="TOS AND WARRANTY INFORMATION",

        placeholder="ToS: Record Video, etc | Warranty: Lifetime Warranty, etc.",

        required=False,

        style=discord.TextStyle.paragraph,

        max_length=4000

    )



    async def on_submit(self, interaction: discord.Interaction):

        deal_id, deal = get_deal_by_channel(interaction.channel.id)

        if not deal:

            await interaction.response.send_message("Deal not found.", ephemeral=True)

            return

            

        self.buyer_id = deal['buyer']  # Now represents RECEIVER

        self.seller_id = deal['seller']  # Now represents SENDER

        await interaction.response.defer()

        try:

            embed = discord.Embed(title="Product Details", color=0x0000ff)
            embed.add_field(name="Product", value=f"```\n{self.product.value}\n```", inline=False)
            tos_val = self.tos.value if self.tos.value else 'No ToS and Warranty'
            embed.add_field(name="ToS and Warranty", value=f"```\n{tos_val}\n```", inline=False)
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1438896774243942432/1446517343084740688/discotools-xyz-icon__2_-removebg-preview.png?ex=693445c1&is=6932f441&hm=5c3da62aeac41487f233c248bd8f20c108e1a43795335ad57f0db85349b7c99b&")

            # Save Product Details to Data
            deal_id, deal = get_deal_by_channel(interaction.channel.id)
            if deal:
                deal["product_name"] = self.product.value
                deal["product_tos"] = tos_val
                
                data = load_all_data()
                data[deal_id] = deal
                save_all_data(data)

            deal_id, deal = get_deal_by_channel(interaction.channel.id)

            if not deal:

                await interaction.followup.send("Deal not found.", ephemeral=True)

                return

                

            self.seller_id = deal['seller']  # Now represents SENDER

            self.buyer_id = deal['buyer']  # Now represents RECEIVER

            await interaction.message.edit(embed=embed, view=ToSCoButtons(), content=f"<@{self.seller_id}> <@{self.buyer_id}>")

        except Exception as e:

            print(f"Error in ToSModal: {e}")

            await interaction.followup.send("An error occurred while processing your ToS.", ephemeral=True)





class ToSCoButtons(View):

    def __init__(self):
        super().__init__(timeout=None)
        # self.lock = asyncio.Lock()  <-- Lock not strictly needed if we rely on atomic-ish DB writes or just race condition acceptance, but keeping it simple. 
        # Actually, let's keep it simple and rely on single-threaded event loop unless high concurrency. 
        # Removing instance vars.




        agree_button = Button(label="Agree", style=discord.ButtonStyle.green, custom_id="agree")

        agree_button.callback = self.agree

        self.add_item(agree_button)



        cancel_button = Button(label="Cancel", style=discord.ButtonStyle.red, custom_id="cants")

        cancel_button.callback = self.cancel

        self.add_item(cancel_button)



    async def agree(self, interaction: discord.Interaction):
        deal_id, deal = get_deal_by_channel(interaction.channel.id)
        if not deal:
            await interaction.response.send_message("Deal not found.", ephemeral=True)
            return

        self.buyer = deal['buyer']    # SENDER (Buyer)
        self.seller = deal['seller']  # RECEIVER (Seller)
        currency = deal.get("currency", "ltc")

        # Load fresh data to avoid race conditions (simple approach)
        data = load_all_data()
        if deal_id not in data:
             await interaction.response.send_message("Deal data missing.", ephemeral=True)
             return
        
        current_deal = data[deal_id]
        
        # SENDER (BUYER) Agree
        if interaction.user.id == int(self.buyer):
            if current_deal.get("tos_sender_agreed"):
                await interaction.response.send_message("You have already agreed.", ephemeral=True)
                return
            
            current_deal["tos_sender_agreed"] = True
            save_all_data(data)
            await interaction.response.defer()
            await interaction.channel.send(
                embed=discord.Embed(description=f"{interaction.user.mention} (Sender) has agreed.")
            )

        # RECEIVER (SELLER) Agree
        elif interaction.user.id == int(self.seller):
            if current_deal.get("tos_receiver_agreed"):
                await interaction.response.send_message("You have already agreed.", ephemeral=True)
                return
            
            current_deal["tos_receiver_agreed"] = True
            save_all_data(data)
            await interaction.response.defer()
            await interaction.channel.send(
                embed=discord.Embed(description=f"{interaction.user.mention} (Receiver) has agreed.")
            )

        else:
            await interaction.response.send_message("You are not authorized to agree to this.", ephemeral=True)
            return

        # Check if both agreed
        # Reloading not strictly necessary since we just updated current_deal, but good practice
        sender_agreed = current_deal.get("tos_sender_agreed")
        receiver_agreed = current_deal.get("tos_receiver_agreed")
        tos_concluded = current_deal.get("tos_concluded", False)

        if sender_agreed and receiver_agreed and not tos_concluded:
            current_deal["tos_concluded"] = True
            save_all_data(data)
            
            await interaction.message.edit(view=None, content=None)



            # ===========================================

            # SOLANA CUSTOM MINIMUM AMOUNT EMBED

            # ===========================================

            if currency == "solana":

                sol_min_fee = 0.00206

                sol_fee_usd = await currency_to_usd(sol_min_fee, "solana")

                sol_required_usd = round(sol_fee_usd + 0.10, 4)



                embed = discord.Embed(

                    title="Deal Amount (Solana)",

                    description=(

                        "Kindly specify the exact amount we are expected to receive in USD.\n"

                        "(example: 10.5)\n\n"

                        f"> **Solana Minimum Deal Requirement**\n"

                        f"> Wallet rent + gas = **0.00206 SOL** (~`${sol_fee_usd:.4f}` USD)\n"

                        f"> Base bot minimum = **$0.10 USD**\n"

                        f"> **Total Minimum = `${sol_required_usd}` USD**\n"

                        f"> You cannot enter an amount lower than this.\n"

                    ),

                    color=0x0000ff

                )



            # ===========================================

            # NON-SOLANA NORMAL AMOUNT EMBED

            # ===========================================

            else:

                embed = discord.Embed(

                    title="Deal Amount",

                    description=(

                        "Kindly specify the exact amount we are expected to receive in USD\n"

                        "(example: 10.5).\n\n"

                        "-# Note: The minimum amount is 0.1 USD"

                    ),

                    color=0x0000ff

                )



            embed.set_thumbnail(

                url="https://cdn.discordapp.com/attachments/1438896774243942432/1446517334331097118/discotools-xyz-icon__4_-removebg-preview.png?ex=693445bf&is=6932f43f&hm=1b9730b7b0c4b222db4800e55c379936ce86b938bbe65709034a3cc30bd0dfdf&"

            )



            msgq = await interaction.channel.send(embed=embed, content=f"<@{self.buyer}>")



            # WAIT FOR SENDER INPUT (was seller)

            def check(m):

                return (

                    m.channel == interaction.channel and

                    m.author.id == int(self.buyer) and

                    not m.author.bot

                )



            while True:

                try:

                    amount_message = await bot.wait_for('message', check=check)

                    try:

                        amount = float(amount_message.content)



                        # ==============================

                        # SOLANA MINIMUM CHECK

                        # ==============================

                        if currency == "solana":

                            sol_min_fee = 0.00206

                            sol_fee_usd = await currency_to_usd(sol_min_fee, "solana")

                            sol_required_usd = round(sol_fee_usd + 0.10, 4)



                            if amount < sol_required_usd:

                                warn = await interaction.channel.send(

                                    f"**Minimum deal amount for Solana is `${sol_required_usd}` USD**"

                                )

                                await asyncio.sleep(6)

                                await warn.delete()

                                continue



                        # ==============================

                        # OTHER CURRENCIES MINIMUM

                        # ==============================

                        else:

                            if amount < 0.1:

                                warn = await interaction.channel.send(

                                    "Amount must be at least **0.1 USD**."

                                )

                                await asyncio.sleep(6)

                                await warn.delete()

                                continue



                        # SAVE AMOUNT

                        data = load_all_data()

                        if deal_id in data:

                            data[deal_id]["amount"] = amount

                            save_all_data(data)



                        # Confirm Embed

                        confirm_embed = discord.Embed(

                            title="Confirm Amount",

                            description=f">>> Are you certain that we are expected to receive `{amount}`$ "

                                        f"in {currency.upper()}?",

                            color=0x0000ff

                        )



                        confirm_embed.set_thumbnail(

                            url="https://cdn.discordapp.com/attachments/1438896774243942432/1446517354543714406/discotools-xyz-icon_5.png?ex=693445c4&is=6932f444&hm=9404a1004e35b98864b40386da81875c7b275d3d0c1d080d49fb8926c79421f7&"

                        )



                        await msgq.edit(

                            embed=confirm_embed,

                            view=AmountConButton(),

                            content=f"<@{self.seller}> <@{self.buyer}>"

                        )

                        break



                    except ValueError:

                        continue



                except Exception as e:

                    print(f"Error waiting for amount: {e}")

                    await interaction.channel.send("An error occurred. Please try again.")

                    continue



    async def cancel(self, interaction: discord.Interaction):
        deal_id, deal = get_deal_by_channel(interaction.channel.id)
        if not deal:
            await interaction.response.send_message("Deal not found.", ephemeral=True)
            return

        self.seller = deal['seller']  # SENDER
        self.buyer = deal['buyer']    # RECEIVER

        if str(interaction.user.id) not in [str(self.seller), str(self.buyer)]:
             await interaction.response.send_message("You are not authorized to cancel this.", ephemeral=True)
             return

        # Reset database flags
        data = load_all_data()
        if deal_id in data:
            data[deal_id]["tos_sender_agreed"] = False
            data[deal_id]["tos_receiver_agreed"] = False
            save_all_data(data)

        tos_embed = discord.Embed(
            title="Product Details",
            description="- Please discuss ToS & Warranty.\n- Then click below to conclude your deal.",
            color=0x0000ff
        )
        tos_embed.set_thumbnail(
             url="https://cdn.discordapp.com/attachments/1438896774243942432/1446517343084740688/discotools-xyz-icon__2_-removebg-preview.png?ex=6938e301&is=69379181&hm=894ab566fd708a090f2ff2f58ef335ad8c3ce14f108c10f372d74f60d773be84&"
        )

        await interaction.message.edit(
            embed=tos_embed,
            view=TosView(),
            content=f"<@{self.seller}> Please set your ToS and Warranty below."
        )
        await interaction.response.defer()



class LangButton(View):

    def __init__(self, selected_lang="English"):

        super().__init__(timeout=None)

        self.selected_lang = selected_lang

        self.add_language_buttons()



    def add_language_buttons(self):

        languages = ["English", "Hindi", "Hinglish"]

        for lang in languages:

            is_selected = lang == self.selected_lang

            button = Button(

                label=lang,

                style=discord.ButtonStyle.danger if is_selected else discord.ButtonStyle.gray,

                disabled=is_selected,

                custom_id=f"lang_{lang.lower()}"

            )

            button.callback = self.create_callback(lang)

            self.add_item(button)



    def get_embed_for_language(self, lang: str) -> discord.Embed:

        if lang == "English":

            return discord.Embed(

                title="⚠️ Be Caution!",

                description="If a seller asks you to send money to their address/UPI QR code first or claims that the bot will charge a fee (our mm service is completely free), be cautious it's most likely a scam. **NEVER PAY DIRECTLY TO THE SELLER.** Report it to the admin immediately, and we'll take action.",

                color=discord.Color.red()

            )

        elif lang == "Hindi":

            return discord.Embed(

                title="⚠️ Be Caution!",

                description="अगर कोई विक्रेता आपसे पहले उनके Address/UPI QR कोड पर पैसे भेजने के लिए कहता है या दावा करता है कि बॉट फीस लेगा (हमारी मिडलमैन सेवा पूरी तरह से मुफ़्त है), तो सावधान रहें, यह सबसे अधिक संभावना है कि यह एक घोटाला है। **कभी भी सीधे भुगतान न करें।** इसकी सूचना तुरंत एडमिन को दें, हम कार्रवाई करेंगे।",

                color=discord.Color.red()

            )

        elif lang == "Hinglish":

            return discord.Embed(

                title="⚠️ Be Caution!",

                description="Agar koi seller aapse pehle unke Address/UPI QR code par paise bhejne ke liye kahe ya bole ki bot fees lega (hamari middleman service bilkul free hai), toh sambhal ke, yeh scam ho sakta hai. **Kabhi bhi directly payment mat karo Seller ko.** Aise case ki turant admin ko report karo, hum action lenge.",

                color=discord.Color.red()

            )

        else:

            return discord.Embed(title="Unknown Language", description="Please try again.")



    def create_callback(self, lang: str):

        async def callback(interaction: discord.Interaction):

            new_embed = self.get_embed_for_language(lang)

            new_view = LangButton(selected_lang=lang)

            await interaction.response.edit_message(embed=new_embed, view=new_view)

        return callback



class ToSButtonsAllInOne(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

    @discord.ui.button(label="Ownership ToS", emoji="💎", style=discord.ButtonStyle.blurple, custom_id="tos_ownership")

    async def ownership_tos(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(

            title="💎 Ownership ToS",

            description="(Any Deal Related To Ownership Transfer)\n\n"

                        "🧑‍💼 **Sender**: Must record from the time you have paid until you receive ownership.\n"

                        "🧑‍💼 **Receiver**: Even the Receiver must record the process of bringing ownership to another.",

            color=0x0000ff

        )

        await interaction.response.send_message(embed=embed, ephemeral=True)



    @discord.ui.button(label="Nitro ToS", emoji="⚡", style=discord.ButtonStyle.blurple, custom_id="tos_nitro")

    async def nitro_tos(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(

            title="⚡ Nitro ToS",

            description="(Any Deal Related To Discord Nitro, Ex: Nitro Boost, Basic , Promo, Vcc)\n\n"

                        "🧑‍💼 **Sender**: Turn on the screen recorder before the Receiver sends you the Nitro gift link in your DMs. Keep recording until you claim the product.\n"

                        "🧑‍💼 **Receiver**: The Receiver should confirm with the Sender whether they're ready to record their screen. Do not share the code without their confirmation.",

            color=0x0000ff

        )

        await interaction.response.send_message(embed=embed, ephemeral=True)



    @discord.ui.button(label="Account ToS", emoji="🔐", style=discord.ButtonStyle.blurple, custom_id="tos_account")

    async def account_tos(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(

            title="🔐 Account ToS",

            description="(Any Deal Related To Accounts, Ex: FF Account, BGMI account, Minecraft Account, etc...)\n\n"

                        "🧑‍💼 **Sender**: Must record from beginning when the Receiver drops the account credentials and record until the account is secured.\n"

                        "🧑‍💼 **Receiver**: Must confirm before dropping the account and guide the Sender fully.",

            color=0x0000ff

        )

        await interaction.response.send_message(embed=embed, ephemeral=True)



    @discord.ui.button(label="Exchange ToS", emoji="💱", style=discord.ButtonStyle.blurple, custom_id="tos_exchange")

    async def exchange_tos(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(

            title="💱 Exchange ToS",

            description="(Any Deal Related To I2C, C2I, C2C, PP2C, C2PP, etc...)\n\n"

                        "🧑‍💼 **Sender**: Must open their app and check if they received payment.\n"

                        "🧑‍💼 **Receiver**: Must provide payment proof after delivery.",

            color=0x0000ff

        )

        await interaction.response.send_message(embed=embed, ephemeral=True)



    @discord.ui.button(label="Member ToS", emoji="🛡️", style=discord.ButtonStyle.blurple, custom_id="tos_member")

    async def member_tos(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(

            title="🛡️ Member ToS",

            description="(Any Deal Related To Auth Bot, Invites Link, etc...)\n\n"

                        "🧑‍💼 **Sender**: Should keep a screenshot with the Receiver before adding members and check thoroughly before releasing.\n"

                        "🧑‍💼 **Receiver**: Must provide product proof after delivery.",

            color=0x0000ff

        )

        await interaction.response.send_message(embed=embed, ephemeral=True)



class ToSButtonsAllInOnee(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)

    @discord.ui.button(label="Ownership ToS", emoji="💎", style=discord.ButtonStyle.blurple, custom_id="tos_ownership")

    async def ownership_tos(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(

            title="💎 Ownership ToS",

            description="(Any Deal Related To Ownership Transfer)\n\n"

                        "🧑‍💼 **Sender**: Must record from the time you have paid until you receive ownership.\n"

                        "🧑‍💼 **Receiver**: Even the Receiver must record the process of bringing ownership to another.",

            color=0x0000ff

        )

        await interaction.response.send_message(embed=embed, ephemeral=True)



    @discord.ui.button(label="Nitro ToS", emoji="⚡", style=discord.ButtonStyle.blurple, custom_id="tos_nitro")

    async def nitro_tos(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(

            title="⚡ Nitro ToS",

            description="(Any Deal Related To Discord Nitro, Ex: Nitro Boost, Basic , Promo, Vcc)\n\n"

                        "🧑‍💼 **Sender**: Turn on the screen recorder before the Receiver sends you the Nitro gift link in your DMs. Keep recording until you claim the product.\n"

                        "🧑‍💼 **Receiver**: The Receiver should confirm with the Sender whether they're ready to record their screen. Do not share the code without their confirmation.",

            color=0x0000ff

        )

        await interaction.response.send_message(embed=embed, ephemeral=True)



    @discord.ui.button(label="Account ToS", emoji="🔐", style=discord.ButtonStyle.blurple, custom_id="tos_account")

    async def account_tos(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(

            title="🔐 Account ToS",

            description="(Any Deal Related To Accounts, Ex: FF Account, BGMI account, Minecraft Account, etc...)\n\n"

                        "🧑‍💼 **Sender**: Must record from beginning when the Receiver drops the account credentials and record until the account is secured.\n"

                        "🧑‍💼 **Receiver**: Must confirm before dropping the account and guide the Sender fully.",

            color=0x0000ff

        )

        await interaction.response.send_message(embed=embed, ephemeral=True)



    @discord.ui.button(label="Exchange ToS", emoji="💱", style=discord.ButtonStyle.blurple, custom_id="tos_exchange")

    async def exchange_tos(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(

            title="💱 Exchange ToS",

            description="(Any Deal Related To I2C, C2I, C2C, PP2C, C2PP, etc...)\n\n"

                        "🧑‍💼 **Sender**: Must open their app and check if they received payment.\n"

                        "🧑‍💼 **Receiver**: Must provide payment proof after delivery.",

            color=0x0000ff

        )

        await interaction.response.send_message(embed=embed, ephemeral=True)



    @discord.ui.button(label="Member ToS", emoji="🛡️", style=discord.ButtonStyle.blurple, custom_id="tos_member")

    async def member_tos(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(

            title="🛡️ Member ToS",

            description="(Any Deal Related To Auth Bot, Invites Link, etc...)\n\n"

                        "🧑‍💼 **Sender**: Should keep a screenshot with the Receiver before adding members and check thoroughly before releasing.\n"

                        "🧑‍💼 **Receiver**: Must provide product proof after delivery.",

            color=0x0000ff

        )

        await interaction.response.send_message(embed=embed, ephemeral=True)



class ConfButtons(discord.ui.View):

    def __init__(self):
        super().__init__(timeout=None)
        # Stateless refactor: Removed self.buyer_confirmed/seller_confirmed, self.tos_sent




        button = Button(label="Confirm", style=discord.ButtonStyle.green, custom_id="confcon")

        button.callback = self.confirm_callback

        self.add_item(button)

        buttone = Button(label="Cancel", style=discord.ButtonStyle.red, custom_id="confcan")
        buttone.callback = self.cancel_callback
        self.add_item(buttone)

        # [TIMER] Extend Button
        ext_btn = Button(label="Extend Timer (+15m)", style=discord.ButtonStyle.blurple, emoji="⏳", custom_id="extend_timer")
        ext_btn.callback = self.extend_callback
        self.add_item(ext_btn)

    

    async def extend_callback(self, interaction: discord.Interaction):
        deal_id, deal = get_deal_by_channel(interaction.channel.id)
        if not deal:
            return await interaction.response.send_message("Deal not found.", ephemeral=True)
            
        # Check limit
        current_extensions = deal.get("extensions", 0)
        if current_extensions >= 2:
            return await interaction.response.send_message("⏳ Timer extension limit reached (Max 2).", ephemeral=True)
            
        data = load_all_data()
        if deal_id in data:
            data[deal_id]["payment_timeout"] = data[deal_id].get("payment_timeout", 1200) + (15 * 60)
            data[deal_id]["extensions"] = current_extensions + 1
            data[deal_id]["last_activity"] = time.time()  # Prevent idle deletion
            save_all_data(data)
            
        await interaction.response.send_message(f"✅ Payment timer extended by 15 minutes! (Used {current_extensions + 1}/2)", ephemeral=False)

    async def cancel_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        uid = str(interaction.user.id)
        deal_id, deal = get_deal_by_channel(interaction.channel.id)

        if not deal:
            return await interaction.followup.send("Deal not found.", ephemeral=True)

        self.seller = deal['seller']  # SENDER
        self.buyer = deal['buyer']    # RECEIVER

        if uid != str(self.seller) and uid != str(self.buyer):
             # Only participants can cancel
             return await interaction.followup.send("You are not authorized to cancel.", ephemeral=True)

        # Reset Logic
        deal['seller'] = "None"
        deal['buyer'] = "None"
        
        # Reset confirmation flags in DB since we are resetting roles
        deal["conf_sender_confirmed"] = False
        deal["conf_receiver_confirmed"] = False
        deal["conf_tos_sent"] = False
        
        update_deal(interaction.channel.id, deal)

        embedd = discord.Embed(title="User Selection", color=0x0000ff)
        embedd.add_field(name="Sender", value="`None`", inline=False)
        embedd.add_field(name="Receiver", value="`None`", inline=False)
        embedd.set_thumbnail(url="https://cdn.discordapp.com/attachments/1438896774243942432/1446517323069521992/discotools-xyz-icon_1.png?ex=693445bc&is=6932f43c&hm=5dc48048ac28e07a15b124c51e0b07ff9c8b8ef927dccdcf9b002226febd9b77&")
        embedd.set_footer(text="RainyDay MM", icon_url="https://cdn.discordapp.com/attachments/1383487913186169032/1384932699717898300/Untitled-2.png?ex=68543a96&is=6852e916&hm=3f5566d93ca1ba539950f47e4ea4fbcf1c4b2e6873af9d97424656d867830d7a&")

        em = discord.Embed(description=f"Cancelled by {interaction.user.mention}")

        try:
             # Remove view instead of deleting message to preserve history
             await interaction.message.edit(view=None)
        except:
             pass
             
        await interaction.channel.send(embed=em)
        await interaction.channel.send(embed=embedd, view=SendButton())




    async def confirm_callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        deal_id, deal = get_deal_by_channel(interaction.channel.id)
        if not deal:
             return await interaction.followup.send("Deal not found.", ephemeral=True)

        uid = str(interaction.user.id)  # String for comparison with deal data
        
        # Optimization: Fetch ONLY this deal's data if needed, but we already have it from get_deal_by_channel
        # We don't need load_all_data() here anymore!
        current_deal = deal 

        self.seller = current_deal['seller']  # SENDER
        self.buyer = current_deal['buyer']    # RECEIVER

        # Validate User
        if uid != str(self.buyer) and uid != str(self.seller):
             return await interaction.followup.send("You are not authorized to confirm this deal.", ephemeral=True)

        # CHECK DB STATE
        sender_conf = current_deal.get("conf_sender_confirmed", False)
        receiver_conf = current_deal.get("conf_receiver_confirmed", False)
        
        # Check if already confirmed
        if (uid == str(self.buyer) and sender_conf) or (uid == str(self.seller) and receiver_conf):
             return await interaction.followup.send("You have already confirmed.", ephemeral=True)



        # UPDATE DB
        if uid == str(self.buyer): # Buyer = Sender
             current_deal["conf_sender_confirmed"] = True
             sender_conf = True
        elif uid == str(self.seller): # Seller = Receiver
             current_deal["conf_receiver_confirmed"] = True
             receiver_conf = True
        
        # Optimized Save: Only update this specific deal
        update_deal(interaction.channel.id, current_deal)
        
        confirm_embed = discord.Embed(
            description=f"{interaction.user.mention} ({'Sender' if uid == str(self.buyer) else 'Receiver'}) has confirmed.",
            color=0x0000ff
        )
        await interaction.channel.send(embed=confirm_embed)

        # CHECK BOTH for transition
        tos_sent = current_deal.get("conf_tos_sent", False) # New DB flag for "tos_sent"

        if sender_conf and receiver_conf and not tos_sent:
            current_deal["conf_tos_sent"] = True
            update_deal(interaction.channel.id, current_deal)

            embed = discord.Embed(title="User Confirmation", color=0x0000ff)
            embed.add_field(name="Sender", value=get_rich_user_display(interaction.guild, self.buyer), inline=False)
            embed.add_field(name="Receiver", value=get_rich_user_display(interaction.guild, self.seller), inline=False)
            embed.set_footer(text="RainyDay MM", icon_url="https://cdn.discordapp.com/attachments/1383487913186169032/1384932699717898300/Untitled-2.png")
            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1438896774243942432/1446517323069521992/discotools-xyz-icon_1.png?ex=693445bc&is=6932f43c&hm=5dc48048ac28e07a15b124c51e0b07ff9c8b8ef927dccdcf9b002226febd9b77&")

            tos_embed = discord.Embed(
                title="Product Details",
                description="- Please discuss about ToS and Warranty of products you are dealing. And then click the button below to officially conclude your deal.\n- If you skip this process and put nothing in the ToS and Warranty button below, we will not take any responsibility if you have any problem.",
                color=0x0000ff
            )
            tos_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1438896774243942432/1446517343084740688/discotools-xyz-icon__2_-removebg-preview.png?ex=693445c1&is=6932f441&hm=5c3da62aeac41487f233c248bd8f20c108e1a43795335ad57f0db85349b7c99b&")

            await interaction.message.edit(embed=embed, view=None)
            await interaction.channel.send(embed=tos_embed, view=TosView(), content=f"<@{self.seller}> Please set your ToS and Warranty below.")




class TosView(View):

    def __init__(self):

        super().__init__(timeout=None)

        self.add_item(ToSButton())

def get_rich_user_display(guild, user_id_str):
    """
    Returns a formatted string: @Mention [username] (UserID)
    """
    if user_id_str in (None, "None", ""):
        return "None"
    
    try:
        user_id = int(user_id_str)
        member = guild.get_member(user_id)
        if member:
            return f"{member.mention} | **{member.name}**\n(`{member.id}`)"
        else:
            return f"<@{user_id}> | Unknown\n(`{user_id}`)"
    except:
        return "None"

class ExtendButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Extend Time (+15m)", style=discord.ButtonStyle.green, custom_id="extend_time")
    async def extend_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        deal_id, deal = get_deal_by_channel(interaction.channel.id)
        if not deal:
            return await interaction.response.send_message("Deal not found.", ephemeral=True)

        extension_count = deal.get("extension_count", 0)
        
        if extension_count >= 3:
            # Disable button and update view
            button.label = "Max Extensions Reached"
            button.style = discord.ButtonStyle.gray
            button.disabled = True
            await interaction.response.edit_message(view=self)
            return await interaction.followup.send("❌ Maximum extensions reached.", ephemeral=True)

        # Update start time to NEW time (effectively resetting the timer)
        deal["start_time"] = time.time()
        deal["role_warning_sent"] = False
        deal["extension_count"] = extension_count + 1
        update_deal(interaction.channel.id, deal)

        # Update button label
        new_count = deal["extension_count"]
        button.label = f"Extend Time ({new_count}/3)"

        if new_count >= 3:
             button.style = discord.ButtonStyle.gray
             button.disabled = True
        
        await interaction.response.edit_message(view=self)
        try:
             await interaction.followup.send(f"✅ Time extended by 15 minutes! ({new_count}/3 used)", ephemeral=True)
        except:
             pass

class SendButton(discord.ui.View):

    def __init__(self):

        super().__init__(timeout=None)


    # ============================
    #      TIMER EXTENSION
    # ============================
    @discord.ui.button(label="Extend Time (+15m)", style=discord.ButtonStyle.blurple, row=2, custom_id="senextend")
    async def extend_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        deal_id, deal = get_deal_by_channel(interaction.channel.id)
        if not deal:
            return await interaction.response.send_message("Deal not found.", ephemeral=True)
            
        extension_count = deal.get("extension_count", 0)
        
        if extension_count >= 3:
            # Disable button and update view
            button.label = "Max Extensions Reached"
            button.style = discord.ButtonStyle.gray
            button.disabled = True
            await interaction.response.edit_message(view=self)
            return await interaction.followup.send("❌ Maximum extensions reached.", ephemeral=True)
            
        # Update start time
        deal["start_time"] = time.time()
        deal["role_warning_sent"] = False
        deal["extension_count"] = extension_count + 1
        update_deal(interaction.channel.id, deal)
        
        # Update button label
        new_count = deal["extension_count"]
        button.label = f"Extend Time ({new_count}/3)"
        
        if new_count >= 3:
            button.style = discord.ButtonStyle.gray
            button.disabled = True
            
        await interaction.response.edit_message(view=self)
        try:
             await interaction.followup.send(f"✅ Time extended by 15 minutes! ({new_count}/3 used)", ephemeral=True)
        except:
             pass



    # ============================

    #        SENDER BUTTON

    # ============================

    @discord.ui.button(label="Sending", style=discord.ButtonStyle.gray, custom_id="sensend")
    async def set_sender(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Offload logic to background task to prevent blocking/timeout
        asyncio.create_task(self._handle_set_sender(interaction))

    async def _handle_set_sender(self, interaction):
        try:
            channel_id = interaction.channel.id
            user_id = str(interaction.user.id)
            deal_id, deal = get_deal_by_channel(channel_id)

            if not deal:
                return await interaction.followup.send("Deal not found.", ephemeral=True)

            # Prevent selecting role if already taken by OTHER user
            # IF user is already receiver (seller field), cant be sender
            if deal["seller"] == user_id: 
                return await interaction.followup.send("**You can't select both roles.**", ephemeral=True)

            # Check if Sender (buyer field) is already taken
            if deal["buyer"] != "None" and deal["buyer"] != user_id:
                return await interaction.followup.send("Sender role is already taken.", ephemeral=True)

            # Update DB - SENDER = buyer field
            deal["buyer"] = user_id
            update_deal(channel_id, deal)

            # Update Embed
            await self.update_message(interaction, deal)
        except Exception as e:
            print(f"Set Sender Error: {e}")

    # ============================

    #        RECEIVER BUTTON

    # ============================

    @discord.ui.button(label="Receiving", style=discord.ButtonStyle.gray, custom_id="recres")
    async def set_receiver(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        # Offload logic
        asyncio.create_task(self._handle_set_receiver(interaction))

    async def _handle_set_receiver(self, interaction):
        try:
            channel_id = interaction.channel.id
            user_id = str(interaction.user.id)
            deal_id, deal = get_deal_by_channel(channel_id)

            if not deal:
                return await interaction.followup.send("Deal not found.", ephemeral=True)

            # IF user is already sender (buyer field), cant be receiver
            if deal["buyer"] == user_id:
                return await interaction.followup.send("**You can't select both roles.**", ephemeral=True)

            if deal["seller"] != "None" and deal["seller"] != user_id:
                return await interaction.followup.send("Receiver role is already taken.", ephemeral=True)

            # Update DB - RECEIVER = seller field
            deal["seller"] = user_id
            update_deal(channel_id, deal)

            # Update Embed
            await self.update_embed(interaction, deal)
        except Exception as e:
            print(f"Set Receiver Error: {e}")

    @discord.ui.button(label="Reset", style=discord.ButtonStyle.red, custom_id="reset_roles")
    async def reset_selection(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        asyncio.create_task(self._handle_reset(interaction))

    async def _handle_reset(self, interaction):
        try:
            channel_id = interaction.channel.id
            deal_id, deal = get_deal_by_channel(channel_id)
            if not deal: return

            deal["seller"] = "None"
            deal["buyer"] = "None"
            
            # Fix: Clear confirmation flags to prevent premature progress if roles are swapped
            deal["amt_sender_confirmed"] = False
            deal["amt_receiver_confirmed"] = False
            deal["amount_final_embed_sent"] = False
            
            update_deal(channel_id, deal)
            await self.update_embed(interaction, deal)
        except Exception as e:
            print(f"Reset Error: {e}")

    async def update_message(self, interaction, deal):
        # Re-use update_embed logic but calling it update_message for clarity in this view context
        await self.update_embed(interaction, deal)

    # ============================

    #        UPDATE EMBED

    # ============================

    async def update_embed(self, interaction: discord.Interaction, deal):
        sender = deal["buyer"]
        receiver = deal["seller"]
        deal_id = deal.get("deal_id", "Unknown")
        
        logo_url = "https://cdn.discordapp.com/attachments/1383487913186169032/1384932699717898300/Untitled-2.png"
        
        # 1. Update the current "User Selection" embed
        sender_display = get_rich_user_display(interaction.guild, sender)
        receiver_display = get_rich_user_display(interaction.guild, receiver)

        embed_selection = discord.Embed(
            title="User Selection",
            description=(
                f"**Sender**\n{sender_display}\n\n"
                f"**Receiver**\n{receiver_display}"
            ),
            color=0x0000ff
        )
        embed_selection.set_author(name="RainyDay MM", icon_url=logo_url)
        embed_selection.set_thumbnail(url=logo_url)
        embed_selection.set_footer(text="RainyDay MM", icon_url=logo_url)
        
        await interaction.message.edit(embed=embed_selection, view=self)

        # 2. Sync with the "System / Shield" panel
        system_msg_id = deal.get("system_msg_id")
        msg_system = None
        
        if system_msg_id:
            try:
                msg_system = await interaction.channel.fetch_message(int(system_msg_id))
            except:
                pass
        
        if not msg_system:
            # Fallback: Search recent messages if ID is missing
            async for m in interaction.channel.history(limit=15):
                if m.embeds and "RainyDay Auto MiddleMan System" in (m.embeds[0].title or ""):
                    msg_system = m
                    break
        
        if msg_system and msg_system.embeds:
            old_embed = msg_system.embeds[0]
            
            # Reconstruct the description with updated roles
            sender_display = f"<@{sender}>" if sender != "None" else "`None` (Click to set below)"
            receiver_display = f"<@{receiver}>" if receiver != "None" else "`None` (Click to set below)"
            
            new_description = (
                "**RainyDay MM** is a premier platform specializing in secure intermediary transactions. "
                "We prioritize your safety and ensure an equitable experience for both Senders and Receivers.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "### 🚨 Security Advisory\n"
                "• **Never pay directly to the seller.** Only send funds to the address provided by this bot.\n"
                "• Our middleman service is **completely free**. If someone asks for a 'service fee', report it.\n"
                "• Always confirm you have received the goods before releasing funds.\n\n"
                "### 📝 Deal Context\n"
                f"• **Sender:** {sender_display}\n"
                f"• **Receiver:** {receiver_display}\n"
                f"• **Deal ID:** `{deal_id}`\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
            
            new_embed = discord.Embed(
                title=old_embed.title,
                description=new_description,
                color=old_embed.color
            )
            new_embed.set_author(name=old_embed.author.name, icon_url=old_embed.author.icon_url)
            new_embed.set_thumbnail(url=old_embed.thumbnail.url)
            if old_embed.fields:
                new_embed.add_field(name=old_embed.fields[0].name, value=old_embed.fields[0].value, inline=False)
            new_embed.set_footer(text=old_embed.footer.text, icon_url=old_embed.footer.icon_url)
            
            await msg_system.edit(embed=new_embed)



        # If both roles selected, send confirmation

        if sender != "None" and receiver != "None":

            confirm = discord.Embed(title="User Confirmation", color=0x0000ff)

            confirm.add_field(name="Sender", value=get_rich_user_display(interaction.guild, sender), inline=False)

            confirm.add_field(name="Receiver", value=get_rich_user_display(interaction.guild, receiver), inline=False)



            confirm.set_footer(

                text="RainyDay MM",

                icon_url="https://cdn.discordapp.com/attachments/1383487913186169032/1384932699717898300/Untitled-2.png"

            )

            confirm.set_thumbnail(

                url="https://cdn.discordapp.com/attachments/1438896774243942432/1446517323069521992/discotools-xyz-icon_1.png?ex=693445bc&is=6932f43c&hm=5dc48048ac28e07a15b124c51e0b07ff9c8b8ef927dccdcf9b002226febd9b77&"

            )



            # Remove view instead of deleting message to preserve history
            await interaction.message.edit(view=None)

            await interaction.channel.send(embed=confirm, view=ConfButtons())



class AmountConButton(View):

    def __init__(self):
        super().__init__(timeout=None)
        # Stateless refactor: Removed self.seller_con, self.buyer_con
        # self.final_embed_sent is also problematic if stored in memory, 
        # but logically we can check if we proceed to next step or check DB. 
        # For now, let's rely on DB checks.




        button = Button(label="Confirm", style=discord.ButtonStyle.green, custom_id="amtcon")

        button.callback = self.confirm

        self.add_item(button)



        cancel_button = Button(label="Cancel", style=discord.ButtonStyle.red, custom_id="amtcan")

        cancel_button.callback = self.cancel

        self.add_item(cancel_button)



    async def cancel(self, interaction: discord.Interaction):

        deal_id, deal = get_deal_by_channel(interaction.channel.id)

        if not deal:

            await interaction.response.send_message("Deal not found.", ephemeral=True)

            return



        # deal['buyer'] = SENDER, deal['seller'] = RECEIVER
        self.buyer_id = deal["buyer"]   # SENDER
        self.seller_id = deal["seller"] # RECEIVER

        self.currency = deal.get("currency", "ltc")



        if self.currency == "solana":

            sol_min_fee = 0.00206  # network rent + gas

            sol_fee_usd = await currency_to_usd(sol_min_fee, "solana")



            sol_required_usd = round(sol_fee_usd + 0.10, 4)



            minimum_text = (

                f"> **Solana Minimum Deal Requirement**\n"

                f"> Wallet rent + gas = **0.00206 SOL** (~`${sol_fee_usd:.4f}` USD)\n"

                f"> Base bot minimum = **$0.10 USD**\n"

                f"> **Total Minimum = `${sol_required_usd}` USD**\n"

                f"> You cannot enter an amount lower than this.\n"

            )

        else:

            minimum_text = "-# Note: Minimum deal amount is 0.1 USD"



        embed = discord.Embed(

            title="Deal Amount",

            description=(

                "Kindly specify the exact amount we are expected to receive in USD.\n"

                "(example: 10.5)\n\n"

                f"{minimum_text}"

            ),

            color=0x0000ff

        )

        embed.set_thumbnail(

            url="https://cdn.discordapp.com/attachments/1438896774243942432/1446517354543714406/discotools-xyz-icon_5.png?ex=693445c4&is=6932f444&hm=9404a1004e35b98864b40386da81875c7b275d3d0c1d080d49fb8926c79421f7&"

        )



        await interaction.message.edit(

            embed=embed, view=None, content=f"<@{self.buyer_id}>"

        )

        await interaction.response.defer()



        def check(m):

            return (

                m.channel == interaction.channel and

                m.author.id == int(self.buyer_id) and

                not m.author.bot

            )



        while True:

            try:

                amount_msg = await bot.wait_for("message", check=check)

                try:

                    amount = float(amount_msg.content)



                    # ======================================================

                    # 🔥 ACTUAL VALIDATION CHECK (ENFORCE MINIMUM)

                    # ======================================================

                    if self.currency == "solana":

                        sol_min_fee = 0.00206

                        sol_fee_usd = await currency_to_usd(sol_min_fee, "solana")

                        sol_required_usd = round(sol_fee_usd + 0.10, 4)



                        if amount < sol_required_usd:

                            warn = await interaction.channel.send(

                                f"**Solana minimum is `${sol_required_usd}` USD**\n"

                                f"(Includes **0.00206 SOL fee** + **$0.10 base minimum**)"

                            )

                            await asyncio.sleep(6)

                            await warn.delete()

                            continue



                    else:

                        # Non-solana currencies

                        if amount < 0.1:

                            warn = await interaction.channel.send("Amount must be at least 0.1 USD.")

                            await asyncio.sleep(6)

                            await warn.delete()

                            continue



                    # Save amount

                    data = load_all_data()

                    if deal_id in data:

                        data[deal_id]["amount"] = amount

                        # Fix: Clear previous confirmations when amount changes
                        data[deal_id]["amt_sender_confirmed"] = False
                        data[deal_id]["amt_receiver_confirmed"] = False
                        data[deal_id]["amount_final_embed_sent"] = False

                        save_all_data(data)



                    confirm_embed = discord.Embed(

                        title="Confirm Amount",

                        description=f">>> Are you certain that we are expected to receive `{amount}`$ "

                                    f"in {self.currency.upper()}?",

                        color=0x0000ff

                    )

                    confirm_embed.set_thumbnail(

                        url="https://cdn.discordapp.com/attachments/1438896774243942432/1446517354543714406/discotools-xyz-icon_5.png?ex=693445c4&is=6932f444&hm=9404a1004e35b98864b40386da81875c7b275d3d0c1d080d49fb8926c79421f7&"

                    )



                    await interaction.message.edit(

                        embed=confirm_embed,

                        view=AmountConButton(),

                        content=f"<@{self.buyer_id}> <@{self.seller_id}>"

                    )

                    break



                except ValueError:

                    continue



            except Exception as e:

                print("Amount error:", e)

                await interaction.channel.send("Error occurred. Try again.")

                continue



    async def confirm(self, interaction: discord.Interaction):
        # Fix: Add processing lock to prevent race conditions (double clicks)
        deal_id, deal = get_deal_by_channel(interaction.channel.id)
        if deal:
            if deal.get('_processing_confirm'):
                return await interaction.response.send_message("Processing...", ephemeral=True)
            deal['_processing_confirm'] = True

        try:
            await interaction.response.defer()

            # deal_id, deal = get_deal_by_channel(...) # Already retrieved
            if not deal:
                return await interaction.followup.send("Deal not found.", ephemeral=True)

            data = load_all_data()
            current_deal = data.get(deal_id)
            if not current_deal:
                return await interaction.followup.send("Deal data missing.", ephemeral=True)

            uid = str(interaction.user.id)
            buyer_id = str(current_deal.get("buyer"))  # SENDER
            seller_id = str(current_deal.get("seller")) # RECEIVER

            # 1. Update confirmation state
            if uid == buyer_id: # Buyer = Sender
                if current_deal.get("amt_sender_confirmed"):
                    return await interaction.followup.send("You have already confirmed.", ephemeral=True)
                current_deal["amt_sender_confirmed"] = True
                await interaction.channel.send(embed=discord.Embed(description=f"{interaction.user.mention} (Sender) has confirmed amount."))
            elif uid == seller_id: # Seller = Receiver
                if current_deal.get("amt_receiver_confirmed"):
                    return await interaction.followup.send("You have already confirmed.", ephemeral=True)
                current_deal["amt_receiver_confirmed"] = True
                await interaction.channel.send(embed=discord.Embed(description=f"{interaction.user.mention} (Receiver) has confirmed amount."))
            else:
                return await interaction.followup.send("You are not authorized to confirm.", ephemeral=True)

            save_all_data(data)
        finally:
            if deal:
                deal['_processing_confirm'] = False

        # 2. Check if BOTH confirmed
        if current_deal.get("amt_sender_confirmed") and current_deal.get("amt_receiver_confirmed"):
            if not current_deal.get("amount_final_embed_sent"):
                
                amount_usd = float(current_deal.get("amount", 0))
                currency = current_deal.get("currency", "ltc")

                # Generate payment info FIRST to catch errors
                try:
                    crypto_amount = await usd_to_currency_amount(amount_usd, currency)
                    wallet = await generate_wallet_for_currency(deal_id, currency)
                    
                    if not wallet:
                        raise Exception("Wallet generation returned None")
                        
                    address = wallet['address']
                    private_key = wallet['private_key']
                    
                except Exception as e:
                    print(f"Error generating wallet/crypto amount: {e}")
                    return await interaction.followup.send("Error initializing payment system. Please try confirming again.", ephemeral=True)

                # Store wallet info (BUT DO NOT mark as sent yet, in case sending fails)
                data = load_all_data() 
                if deal_id in data:
                    data[deal_id].update({
                        "address": address,
                        "private_key": private_key,
                        "ltc_amount": crypto_amount,
                        "payment_start_time": time.time(),
                        "last_activity": time.time()
                    })
                    save_all_data(data)

                # Remove buttons from the confirmation message
                try:
                    await interaction.message.edit(view=None)
                except:
                    pass

                # Format display
                currency_display = {
                    'ltc': 'Litecoin',
                    'usdt_bep20': 'USDT (BEP20)',
                    'usdt_polygon': 'USDT (Polygon)',
                    'solana': 'Solana',
                    'ethereum': 'Ethereum'
                }.get(currency, 'Crypto')

                embed = discord.Embed(
                    title="RainyDay MM",
                    description=(
                        f"- <@{buyer_id}> Please proceed by transferring the agreed-upon funds\n"
                        f"- COPY & PASTE the EXACT AMOUNT to avoid errors.\n\n"
                    ),
                    color=0x0000ff
                )
                embed.add_field(name=f"{currency_display} Address", value=f"{address}", inline=False)
                embed.add_field(name=f"{currency_display} Amount", value=f"{crypto_amount:.8f}", inline=True)
                embed.add_field(name="USD Amount", value=f"{amount_usd}$", inline=True)
                embed.set_footer(text="➤ RainyDay MM | Transaction Confirmed")

                # Send Invoice
                await interaction.channel.send(content=f"<@{buyer_id}>", embed=embed, view=AddyButtons())

                # NOW mark as sent, since we successfully sent the message
                current_deal["amount_final_embed_sent"] = True
                
                # Update DB with flag
                if deal_id in data:
                    data[deal_id]["amount_final_embed_sent"] = True
                    save_all_data(data)

                # Payment Timeout Note
                timeout_embed = discord.Embed(
                    description="-# Note - If you don't send the amount within 20 minutes, the deal will be cancelled.",
                    color=0x0000ff
                )
                await interaction.channel.send(embed=timeout_embed)

                # Special consideration for USDT (Gas warning)
                # if currency in ["usdt_bep20", "usdt_polygon"]:
                #     await send_usdt_wallet_with_gas_embed(interaction, deal_id, currency, address)


                # Send "Waiting" message and start checker
                em_wait = discord.Embed(description="*Waiting for transaction...*")
                em_wait.set_author(name="Payment Status", icon_url="https://cdn.discordapp.com/emojis/1324706325112164404.gif")
                msg = await interaction.channel.send(embed=em_wait)

                bot.loop.create_task(
                    check_payment_multicurrency(address, interaction.channel, crypto_amount, data[deal_id], msg)
                )




class AddyButtons(View):

    def __init__(self):

        super().__init__(timeout=None)

        self.copy_used = False

        button = Button(label="Copy", style=discord.ButtonStyle.primary, custom_id="addycopy")

        button.callback = self.copy

        self.add_item(button)

        buttone = Button(label="Scan QR", style=discord.ButtonStyle.primary, custom_id="addyqr")

        buttone.callback = self.qr

        self.add_item(buttone)



    async def copy(self, interaction: discord.Interaction):
        deal_id, deal = get_deal_by_channel(interaction.channel.id)
        if not deal:
            return await interaction.response.send_message("Deal not found.", ephemeral=True)
            
        # Update activity
        try:
            data = load_all_data()
            if deal_id in data:
                data[deal_id]['last_activity'] = time.time()
                save_all_data(data)
        except: pass
            
        seller_id = deal.get('seller', 'None')
        buyer_id = deal.get('buyer', 'None')
        addy = deal.get('address')
        amount = deal.get('expected_crypto_amount', deal.get('ltc_amount', 0))
        
        # Authorization check
        try:
            is_auth = False
            # Only Buyer can copy the address
            if buyer_id != 'None' and interaction.user.id == int(buyer_id): is_auth = True
        except:
            is_auth = False

        if is_auth:
            if not addy:
                return await interaction.response.send_message("Payment address not generated yet.", ephemeral=True)
                
            await interaction.response.send_message(f"{addy}", ephemeral=True)
            try:
                await interaction.followup.send(f"{float(amount):.8f}", ephemeral=True)
            except:
                pass
        else:
            await interaction.response.send_message("You are not authorized to use this.", ephemeral=True)

    async def qr(self, interaction: discord.Interaction):
        deal_id, deal = get_deal_by_channel(interaction.channel.id)
        if not deal:
            return await interaction.response.send_message("Deal not found.", ephemeral=True)
            
        # Update activity
        try:
            data = load_all_data()
            if deal_id in data:
                data[deal_id]['last_activity'] = time.time()
                save_all_data(data)
        except: pass
            
        seller_id = deal.get('seller', 'None')
        buyer_id = deal.get('buyer', 'None')
        addy = deal.get('address')
        amount = deal.get('expected_crypto_amount', deal.get('ltc_amount', 0))
        currency_tag = deal.get('currency', 'ltc')

        # Authorization check
        is_auth = False
        # Only Buyer can scan QR
        try:
            if buyer_id != 'None' and interaction.user.id == int(buyer_id): is_auth = True
        except:
            is_auth = False

        if is_auth:
            if not addy:
                return await interaction.response.send_message("Payment address not generated yet.", ephemeral=True)

            await interaction.response.defer(ephemeral=True)
            
            # [MOBILE] Use BIP21 URI for auto-fill
            uri = addy
            try:
                f_amount = float(amount)
                if currency_tag == 'ltc':
                    uri = f"litecoin:{addy}?amount={f_amount:.8f}"
                elif currency_tag == 'ethereum' or currency_tag.startswith('usdt'):
                    uri = f"ethereum:{addy}"
                elif currency_tag == 'solana' or currency_tag == 'sol':
                    uri = f"solana:{addy}?amount={f_amount:.8f}"
            except:
                pass
            
            qr_bytes = await generate_qr_bytes(uri)

            if qr_bytes:
                file = discord.File(io.BytesIO(qr_bytes), filename="qrcode.png")
                
                currency_display = {
                    'ltc': 'Litecoin',
                    'usdt_bep20': 'USDT (BEP20)',
                    'usdt_polygon': 'USDT (Polygon)',
                    'solana': 'Solana (SOL)',
                    'ethereum': 'Ethereum (ETH)'
                }.get(currency_tag, 'Crypto')
                
                embed = discord.Embed(
                    title="Payment QR Code",
                    description="Scan this with your mobile wallet to pay.",
                    color=0x0000FF
                )
                embed.add_field(name="Address", value=f"`{addy}`", inline=False)
                try:
                    embed.add_field(name="Amount", value=f"`{float(amount):.8f} {currency_display}`", inline=False)
                except:
                    embed.add_field(name="Amount", value=f"`{amount} {currency_display}`", inline=False)
                
                embed.set_image(url="attachment://qrcode.png")
                await interaction.followup.send(embed=embed, file=file, ephemeral=True)
            else:
                await interaction.followup.send("Failed to generate QR code. Please try again.", ephemeral=True)
        else:
            await interaction.response.send_message("You are not authorized to use this.", ephemeral=True)



class ProceedButton(View):

    def __init__(self):

        super().__init__(timeout=None)

        button = Button(label="Continue", style=discord.ButtonStyle.green, custom_id="processcon")

        button.callback = self.process

        self.add_item(button)

        buttone = Button(label="Cancel", style=discord.ButtonStyle.red, custom_id="processcan")

        buttone.callback = self.cancel

        self.add_item(buttone)



    async def process(self, interaction: discord.Interaction):

        deal_id, deal = get_deal_by_channel(interaction.channel.id)

        if not deal:

            await interaction.response.send_message("Deal not found.", ephemeral=True)

            return

            

        buyer = deal['buyer']  # Now represents RECEIVER

        seller = deal['seller']  # Now represents SENDER

        currency = deal.get('currency', 'ltc')

        

        if interaction.user.id == int(seller):  # SENDER confirms
           # Fix: Add processing lock
           if deal.get('_processing_process'):
               return await interaction.response.send_message("Processing...", ephemeral=True)
           deal['_processing_process'] = True
           
           try:
               await interaction.response.defer()

               await interaction.message.edit(view=None)

               embed = discord.Embed(description=f"{interaction.user.mention} has confirmed to proceed with the deal.")

               await interaction.channel.send(embed=embed)

               while True:
    
                  await asyncio.sleep(30)
    
                  address = deal['address']
    
                  
    
                  # Check balance based on currency
    
                  if currency == 'ltc':
    
                      bal, _ = await get_balance_async(address)
    
                  elif currency == 'usdt_bep20':
    
                      bal = await get_usdt_balance_parallel(USDT_BEP20_CONTRACT, address, BEP20_RPC_URLS, USDT_BEP20_DECIMALS)
    
                  elif currency == 'usdt_polygon':
    
                      bal = await get_usdt_balance_parallel(USDT_POLYGON_CONTRACT, address, POLYGON_RPC_URLS, USDT_POLYGON_DECIMALS)
    
                  elif currency == 'solana':
    
                      bal = await get_solana_balance_parallel(address)
    
                  elif currency == 'ethereum':
    
                      bal = await get_eth_balance_parallel(address)
    
                  else:
    
                      bal = 0
    
                      
    
                  if bal > 0:
    
                     usbal = await currency_to_usd(bal, currency)
    
                     deal['ltc_amount'] = bal
    
                     update_deal(interaction.channel.id, deal)
    
                     
    
                     currency_display = {
    
                         'ltc': 'LTC',
    
                         'usdt_bep20': 'USDT (BEP20)',
    
                         'usdt_polygon': 'USDT (Polygon)',
    
                         'solana': 'SOL',
    
                         'ethereum': 'ETH'
    
                     }.get(currency, 'Crypto')
    
                     
    
                     confirmed_embed = discord.Embed(title="Deal Confirmation", color=0x0000ff, description=">>> Payment successfully received.")
    
                     confirmed_embed.add_field(name=f"{currency_display} Amount", value=f"{bal}", inline=False)
    
                     confirmed_embed.add_field(name="USD Amount", value=f"{usbal}$", inline=False)
    
                     confirmed_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1438896774243942432/1446517314433454342/discotools-xyz-icon.png?ex=693445ba&is=6932f43a&hm=379aa3c340acbe860daf7e83bea918027868d2b08b73594728a73220cbc340bf&")
    
                     await interaction.channel.send(embed=confirmed_embed, view=ReleaseButton(), content=f"<@{buyer}> <@{seller}>")
    
                     break
           finally:
               deal['_processing_process'] = False

        else:

            await interaction.response.send_message("You are not authorized to use this.", ephemeral=True)



    async def cancel(self, interaction: discord.Interaction):

        deal_id, deal = get_deal_by_channel(interaction.channel.id)

        if not deal:

            await interaction.response.send_message("Deal not found.", ephemeral=True)

            return

            

        seller = deal['seller']  # Now represents SENDER

        currency = deal.get('currency', 'ltc')

        

        if interaction.user.id == int(seller):  # SENDER cancels
            # Fix: Add processing lock
            if deal.get('_processing_cancel'):
                return await interaction.response.send_message("Processing...", ephemeral=True)
            deal['_processing_cancel'] = True

            try:
                await interaction.response.defer()

                await interaction.message.edit(view=None)

                embed = discord.Embed(description=f"{interaction.user.mention} has cancelled the deal.")

                await interaction.channel.send(embed=embed)

                seller_id = int(deal['seller'])  # SENDER ID

                buyer_id = int(deal['buyer'])  # RECEIVER ID

                currency_display = {
                    'ltc': 'LTC',
                    'usdt_bep20': 'USDT (BEP20)',
                    'usdt_polygon': 'USDT (Polygon)',
                    'solana': 'SOL',
                    'ethereum': 'ETH'
                }.get(currency, 'crypto')

                await interaction.channel.send(f"Please send your {currency_display} address to get the funds back. ||<@{buyer_id}>||")

                def check(msg):
                    return msg.author.id == buyer_id and msg.channel == interaction.channel

                while True:
                    msg = await interaction.client.wait_for("message", check=check)
                    address = msg.content.strip()

                    if await is_valid_address(address, currency):
                        try:
                            tx_hash = await send_funds_based_on_currency(deal, address)
                            
                            currency_display_full = {
                                'ltc': 'Litecoin',
                                'usdt_bep20': 'USDT (BEP20)',
                                'usdt_polygon': 'USDT (Polygon)',
                                'solana': 'Solana (SOL)',
                                'ethereum': 'Ethereum (ETH)'
                            }.get(currency, 'Crypto')
                            
                            explorer_url = get_explorer_url(currency, tx_hash)
                            
                            em = discord.Embed(title=f"{currency_display_full} Sent", description=f"Address: `{address}`\nTransaction ID: [{tx_hash}]({explorer_url})", color=0x0000ff)
                            await msg.reply(embed=em)
                            await send_transcript(interaction.channel, seller_id, buyer_id, txid=tx_hash)
                            deals = load_all_data()
                            
                            await asyncio.sleep(100)
                            await interaction.channel.delete()
                        except Exception as e:
                            await msg.reply(f"Failed to send {currency_display}: `{str(e)}`")
                        break
                    else:
                        continue
            finally:
                deal['_processing_cancel'] = False

        else:

            await interaction.response.send_message("You are not authorized to use this.", ephemeral=True)



class RescanButton(View):

    def __init__(self):

        super().__init__(timeout=None)

        button = Button(label="Rescan", style=discord.ButtonStyle.green, custom_id="rescan")

        button.callback = self.rescan

        self.add_item(button)



    async def rescan(self, interaction: discord.Interaction):

        deal_id, deal = get_deal_by_channel(interaction.channel.id)

        if not deal:

            await interaction.response.send_message("Deal not found.", ephemeral=True)

            return

            

        seller_id = int(deal['seller'])  # Now represents SENDER

        buyer_id = int(deal['buyer'])  # Now represents RECEIVER

        

        if interaction.user.id not in (seller_id, buyer_id):

            await interaction.response.send_message("You are not authorized to use this.", ephemeral=True)

            return

            

        rescan_count = deal.get('rescan_count', 0)

        if rescan_count >= 2:

            await interaction.response.send_message("You've already used all rescan attempts.", ephemeral=True)

            return

            

        deal['rescan_count'] = rescan_count + 1

        deal['payment_timeout'] = deal.get('payment_timeout', 1 * 1200) + 1 * 60

        update_deal(interaction.channel.id, deal)

        

        await interaction.response.defer()

        # Remove view instead of deleting message to preserve history
        await interaction.message.edit(view=None)

        

        embed = discord.Embed(

            title="Payment Time Extended",

            color=0x00ff00,

            description=f">>> Payment time has been extended by 20 minutes. You have {2 - deal['rescan_count']} rescan attempts remaining."

        )

        await interaction.channel.send(embed=embed)

        

        address = deal['address']

        crypto_amount = deal['ltc_amount']

        em = discord.Embed()

        em.set_author(name="Waiting for transaction...")

        msg = await interaction.channel.send(embed=em)

        bot.loop.create_task(check_payment_multicurrency(address, interaction.channel, crypto_amount, deal, msg))



class ContactModModal(Modal):
    def __init__(self, deal_id, deal):
        super().__init__(title="Moderator Assistance Request")
        self.deal_id = deal_id
        self.deal = deal
        
        self.issue_input = TextInput(
            label="What is the issue?",
            placeholder="Describe your issue in detail so we can help you faster...",
            style=discord.TextStyle.paragraph,
            required=True,
            min_length=10,
            max_length=1000
        )
        self.add_item(self.issue_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        issue_text = self.issue_input.value.strip()
        
        # 1. Lock the deal
        self.deal['mod_locked'] = True
        update_deal(interaction.channel_id, self.deal)
        
        # 2. Notify in ticket channel
        embed = discord.Embed(
            title="🛑 Moderator Requested",
            description=f"{interaction.user.mention} has requested moderator assistance. The Release and Cancel buttons are now **locked** until a moderator clears this request.",
            color=discord.Color.red()
        )
        await interaction.channel.send(embed=embed)
        
        # 3. Send detailed request to Support/Logs Channel
        target_channel_id = CONTACT_MOD_LOG_CHANNEL_ID if CONTACT_MOD_LOG_CHANNEL_ID else SUPPORT_CHANNEL_ID
        support_chan = bot.get_channel(target_channel_id)
        
        if not support_chan:
            print(f"[ContactStaff] ERROR: Could not find support/log channel ID: {target_channel_id}")
        else:
            try:
                staff_ping = f"<@&{EXECUTIVE_ROLE_ID}> " if EXECUTIVE_ROLE_ID else ""
                
                support_embed = discord.Embed(
                    title="⚠️ Support Request Received",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.now(pytz.utc)
            )
                support_embed.add_field(name="User", value=f"{interaction.user.mention} ({interaction.user})", inline=True)
                support_embed.add_field(name="Ticket", value=interaction.channel.mention, inline=True)
                support_embed.add_field(name="Deal ID", value=f"`{self.deal_id}`", inline=True)
                support_embed.add_field(name="Issue Description", value=f"```\n{issue_text}\n```", inline=False)
                support_embed.set_footer(text=f"User ID: {interaction.user.id}")
                
                # Add jump link to channel
                jump_url = f"https://discord.com/channels/{interaction.guild_id}/{interaction.channel_id}"
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Jump to Ticket", url=jump_url))
                
                
                await support_chan.send(content=staff_ping, embed=support_embed, view=view)
                
            except Exception as e:
                print(f"[ContactStaff] ERROR: Failed to send to contact channel: {e}")
            
        await interaction.followup.send("✅ Your request has been sent to the support team. A moderator will assist you shortly.", ephemeral=True)

class ReleaseButton(View):

    def __init__(self, txid=None, currency=None):

        super().__init__(timeout=None)

        self.release_button = Button(label="Release", style=discord.ButtonStyle.green, custom_id="release")

        self.release_button.callback = self.release

        self.add_item(self.release_button)

        self.cancel_button = Button(label="Cancel", style=discord.ButtonStyle.red, custom_id="canrel")

        self.cancel_button.callback = self.cancel

        self.add_item(self.cancel_button)

        self.seller_con = False  # Now represents SENDER confirmation

        self.buyer_con = False  # Now represents RECEIVER confirmation

        self.lock = asyncio.Lock()

        buttonu = Button(label="More Info", style=discord.ButtonStyle.gray, custom_id="jfo")
        buttonu.callback = self.info
        self.add_item(buttonu)

        self.mod_button = Button(label="Contact Mod", style=discord.ButtonStyle.blurple, custom_id="contact_mod")
        self.mod_button.callback = self.contact_mod
        self.add_item(self.mod_button)

        # Add "View on Blockchain" button if txid is provided
        if txid and currency:
            explorer_url = get_explorer_url(currency, txid)
            if explorer_url:
                self.add_item(Button(label="View on Blockchain", url=explorer_url, style=discord.ButtonStyle.link))



    async def info(self, interaction: discord.Interaction):

        deal_id, deal = get_deal_by_channel(interaction.channel.id)

        if not deal:

            await interaction.response.send_message("Deal not found.", ephemeral=True)

            return

            

        try:
            seller_id = int(deal.get('seller', 0)) if str(deal.get('seller')) != "None" else 0
            buyer_id = int(deal.get('buyer', 0)) if str(deal.get('buyer')) != "None" else 0
        except:
            seller_id, buyer_id = 0, 0

        if (interaction.user.id == seller_id or interaction.user.id == buyer_id) and seller_id != 0:
            embed = discord.Embed(title="Deal Guide", color=0x0000ff, description=f"**After Completing the deal:**\n<@{buyer_id}> must click **Release** and **Confirm** to transfer the funds to <@{seller_id}>.\n**To Cancel this deal:**\n<@{seller_id}> must click **Cancel** and **Confirm** to transfer the funds to <@{buyer_id}>.")

            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1373630302710399039/1387516877139476551/ddg9MWL.png?ex=685da14a&is=685c4fca&hm=7f2145fa614533ed4b84661299cb955e67d54bd4f16962b67e7350cfc593d972&")

            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        else:
            await interaction.response.send_message("You are not authorized to check this.", ephemeral=True)
            return
    async def contact_mod(self, interaction: discord.Interaction):
        deal_id, deal = get_deal_by_channel(interaction.channel.id)
        if not deal:
            await interaction.response.send_message("Deal not found.", ephemeral=True)
            return

        # Open the modal instead of direct action
        await interaction.response.send_modal(ContactModModal(deal_id, deal))



    async def cancel(self, interaction: discord.Interaction):
        deal_id, deal = get_deal_by_channel(interaction.channel.id)
        if not deal:
            await interaction.response.send_message("Deal not found.", ephemeral=True)
            return

        if deal.get('mod_locked'):
            await interaction.response.send_message("⚠️ This deal has been locked by a moderator. Please contact support for assistance.", ephemeral=True)
            return

            

        try:
            seller_id = int(deal.get('seller', 0)) if str(deal.get('seller')) != "None" else 0
            buyer_id = int(deal.get('buyer', 0)) if str(deal.get('buyer')) != "None" else 0
        except:
            seller_id, buyer_id = 0, 0

        ltc_amount = deal['ltc_amount']

        usd_amount = deal['amount']

        currency = deal.get('currency', 'ltc')



        if interaction.user.id == seller_id:  # SENDER cancels

            if getattr(self, "seller_con", False):

                await interaction.response.send_message("You have already confirmed cancellation.", ephemeral=True)

                return

            self.seller_con = True

        elif interaction.user.id == buyer_id:  # RECEIVER cancels

            if getattr(self, "buyer_con", False):

                await interaction.response.send_message("You have already confirmed cancellation.", ephemeral=True)

                return

            self.buyer_con = True

        else:

            await interaction.response.send_message("You are not authorized to cancel the deal.", ephemeral=True)

            return



        await interaction.response.defer()

        embed = discord.Embed(description=f"{interaction.user.mention} has cancelled the deal.")

        await interaction.channel.send(embed=embed)



        if getattr(self, "seller_con", False) and getattr(self, "buyer_con", False):

            self.cancel_button.disabled = True

            self.release_button.disabled = True



            deal["release_message_id"] = interaction.message.id

            update_deal(interaction.channel.id, deal)



            currency_display = {

                'ltc': 'LTC',

                'usdt_bep20': 'USDT (BEP20)',

                'usdt_polygon': 'USDT (Polygon)',

                'solana': 'SOL',

                'ethereum': 'ETH'

            }.get(currency, 'Crypto')



            embed = discord.Embed(

                title="Confirm Cancellation",

                color=discord.Color.red(),

                description=(

                    f"Are you sure you would like to cancel this deal? Funds will be refunded to the **SENDER** (<@{buyer_id}>). "

                    "This means that the deal is now cancelled, and cannot be reverted once cancelled."

                )

            )

            embed.add_field(name="Refunding Amount", value=f"USD: `{usd_amount}$`\n{currency_display}: `{ltc_amount:.8f}`", inline=False)

            embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1373630302710399039/1387685827697442876/3mjo6QL.png")



            await interaction.message.edit(view=self)

            await interaction.channel.send(embed=embed, view=CancelConButton(), content=f"<@{seller_id}>")



    async def release(self, interaction: discord.Interaction):
        deal_id, deal = get_deal_by_channel(interaction.channel.id)
        if not deal:
            await interaction.response.send_message("Deal not found.", ephemeral=True)
            return

        if deal.get('mod_locked'):
            await interaction.response.send_message("⚠️ This deal has been locked by a moderator. Please contact support for assistance.", ephemeral=True)
            return

            

        try:
            seller_id = int(deal.get('seller', 0)) if str(deal.get('seller')) != "None" else 0
            buyer_id = int(deal.get('buyer', 0)) if str(deal.get('buyer')) != "None" else 0
        except:
            seller_id, buyer_id = 0, 0

        currency = deal.get('currency', 'ltc')

        

        if interaction.user.id == buyer_id:  # RECEIVER releases funds to SENDER

            await interaction.response.defer()

            

            currency_display = {

                'ltc': 'LTC',

                'usdt_bep20': 'USDT (BEP20)',

                'usdt_polygon': 'USDT (Polygon)',

                'solana': 'SOL',

                'ethereum': 'ETH'

            }.get(currency, 'crypto')

            

            embed = discord.Embed(title="Release Confirmation", color=0x0000ff, description=f"<@{buyer_id}> Are you sure you want to release the funds to <@{seller_id}>?\n\n**Note:** Once released, the funds cannot be reversed.")

            embed.set_footer(text="Our Staffs will never ask you to release the funds.")

            await interaction.followup.send(embed=embed, view=ReleaseConButton())

            # Remove view instead of deleting message to preserve history
            await interaction.message.edit(view=None)

        else:

            await interaction.response.send_message("You are not authorized to release the funds.", ephemeral=True)

            return



class RefundInitiationView(View):
    def __init__(self, deal_id, deal, currency):
        super().__init__(timeout=None)
        self.deal_id = deal_id
        self.deal = deal
        self.currency = currency

    @discord.ui.button(label="Provide Refund Address", style=discord.ButtonStyle.green, custom_id="refund_provide_addy")
    async def provide_addy(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Restriction: Only SENDER (Buyer / buyer key in code) can provide address
        sender_id = int(self.deal.get('buyer', 0))
        if interaction.user.id != sender_id:
             return await interaction.response.send_message("Only the Buyer (transaction sender) can provide the refund address.", ephemeral=True)
        
        currency_display = self.currency.upper().replace("_", " ")
        await interaction.response.send_modal(RefundModal(self.deal_id, self.deal, currency_display, self.currency))

class PartialPaymentView(View):
    def __init__(self, deal_id, deal, remaining_amount, currency, txid=None):
        super().__init__(timeout=None)
        self.deal_id = deal_id
        self.deal = deal
        self.remaining_amount = remaining_amount
        self.currency = currency
        self.txid = txid
        
    @discord.ui.button(label="Continue", style=discord.ButtonStyle.green, custom_id="partial_continue")
    async def continue_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Restriction: Only RECEIVER (Seller / seller key) can accept a partial payment as full
        receiver_id = int(self.deal.get('seller', 0))
        if interaction.user.id != receiver_id:
            return await interaction.response.send_message("Only the receiver (Seller) can choose to accept a partial payment as full.", ephemeral=True)

        if self.deal.get('mod_locked'):
            return await interaction.response.send_message("⚠️ This deal has been locked by a moderator. Please contact support for assistance.", ephemeral=True)
            
        await interaction.response.defer()

        # ACCEPT PARTIAL AS FULL
        # We process the current 'ltc_amount' (total paid) as the final accepted amount.
        
        # 1. Update Expected Amount to match Paid (so it doesn't look like underpayment anymore)
        current_paid = self.deal.get('ltc_amount', 0)
        self.deal['expected_crypto_amount'] = float(current_paid)
        
        # Save updated expectation
        try:
             d = load_all_data()
             if self.deal_id in d:
                 d[self.deal_id]['expected_crypto_amount'] = float(current_paid)
                 save_all_data(d)
        except: pass

        # 2. Trigger Full Payment Flow
        # This will show 'Verifying Transaction' -> 'Release Panel'
        await handle_full_payment(
            interaction.channel, 
            self.deal, 
            current_paid, 
            current_paid, # Expected = Paid
            self.currency, 
            self.deal.get('address'), 
            msg=interaction.message, 
            tx_hash=self.txid
        )
        
        # Note: handle_full_payment sets 'paid=True' and stops monitor_wallet.
        return

    @discord.ui.button(label="Cancel with Refund", style=discord.ButtonStyle.red, custom_id="partial_cancel")
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Allow both Sender (Buyer) and Receiver (Seller) to initiate
        receiver_id = int(self.deal.get('seller', 0))
        sender_id = int(self.deal.get('buyer', 0))
        
        if interaction.user.id not in [sender_id, receiver_id]:
            return await interaction.response.send_message("Only the parties involved in this deal can request a refund.", ephemeral=True)
            
        await interaction.response.defer()
        
        # 1. Update the original message to remove buttons
        try: await interaction.message.edit(view=None)
        except: pass
        
        # 2. Send the Refund Initiation embed
        embed = discord.Embed(
            title="⚠️ Refund Requested",
            description=(
                f"<@{interaction.user.id}> has requested a refund for this transaction.\n\n"
                f"<@{sender_id}>, please click the button below to provide your refund address."
            ),
            color=0xff0000
        )
        embed.set_footer(text="The transaction will be cancelled once the refund is processed.")
        
        await interaction.channel.send(embed=embed, view=RefundInitiationView(self.deal_id, self.deal, self.currency))

class OverpaymentView(View):
    def __init__(self, channel, deal_info, received, expected, currency, txid, msg):
        super().__init__(timeout=None)
        self.channel = channel
        self.deal_info = deal_info
        self.received = received
        self.expected = expected
        self.currency = currency
        self.txid = txid
        self.msg = msg
        
    @discord.ui.button(label="Accept Excess Amount", style=discord.ButtonStyle.green, custom_id="overpay_accept")
    async def accept_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Restriction: Only Sender (Buyer / buyer key) can accept overpayment (giving it to seller)
        sender_id = int(self.deal_info.get('buyer', 0))
        if interaction.user.id != sender_id:
            return await interaction.response.send_message("Only the sender (Buyer) can decide to accept overpayment.", ephemeral=True)

        await interaction.response.defer()
        
        # Proceed to full payment handler
        # We clean up the view/embed first or let handle_full_payment do it?
        # handle_full_payment sends a new Main Embed. We should probably delete this warning.
        try: 
            # Remove view instead of deleting message to preserve history
            await interaction.message.edit(view=None)
        except: 
            pass
            
        # Call the original full payment handler
        deal_info_updated = self.deal_info
        # Ensure correct amount is recorded? stored in deal_info already by loop
        
        # We need to access handle_full_payment. It's an async global function.
        # We need to recreate the arguments.
        # Note: We might be inside a class method so we need to ensure scope is fine.
        # Ideally, we call it directly.
        
        # Re-fetch deal deal_id just in case? No, pass deal_info
        
        # Since handle_full_payment is async, we await it.
        # Logic:
        address = self.deal_info['address']
        await handle_full_payment(self.channel, self.deal_info, self.received, self.expected, self.currency, address, self.msg, self.txid)


    @discord.ui.button(label="Cancel with Refund", style=discord.ButtonStyle.red, custom_id="overpay_cancel")
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Allow both Sender (Buyer) and Receiver (Seller) to initiate
        receiver_id = int(self.deal_info.get('seller', 0))
        sender_id = int(self.deal_info.get('buyer', 0))
        
        if interaction.user.id not in [sender_id, receiver_id]:
            return await interaction.response.send_message("Only the parties involved in this deal can request a refund.", ephemeral=True)
            
        await interaction.response.defer()
        
        # 1. Update the original message to remove buttons
        try: await interaction.message.edit(view=None)
        except: pass
        
        # deal_id extraction
        deal_id = None
        for k, v in load_all_data().items():
            if v.get('address') == self.deal_info.get('address'):
                deal_id = k
                break

        # 2. Send the Refund Initiation embed
        embed = discord.Embed(
            title="⚠️ Refund Requested (Overpayment)",
            description=(
                f"<@{interaction.user.id}> has requested a refund for this transaction.\n\n"
                f"<@{sender_id}>, please click the button below to provide your refund address."
            ),
            color=0xff0000
        )
        embed.set_footer(text="The transaction will be cancelled once the refund is processed.")
        
        await interaction.channel.send(embed=embed, view=RefundInitiationView(deal_id, self.deal_info, self.currency))

class RefundModal(Modal):
    def __init__(self, deal_id, deal, currency_display, currency):
        super().__init__(title="Refund Partial Payment")
        self.deal_id = deal_id
        self.deal = deal
        self.currency_display = currency_display
        self.currency = currency
        
        self.address_input = TextInput(
            label=f"Sender's {currency_display} Address",
            placeholder=f"Paste the address to refund to...",
            required=True,
            min_length=10,
            max_length=120
        )
        self.add_item(self.address_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        address = self.address_input.value.strip()
        
        if not await is_valid_address(address, self.currency):
            return await interaction.followup.send(f"Invalid {self.currency_display} address.", ephemeral=True)
            
        try:
            # REFUND: Send funds back (MAX - gas)
            # We pass amount=None to send everything
            tx_hash = await send_funds_based_on_currency(self.deal, address, amount=None)
            
            explorer_url = get_explorer_url(self.currency, tx_hash)
            
            # Helper to get user ID safely
            buyer_id = self.deal.get('buyer', 'Unknown')
            
            embed = discord.Embed(
                title="💸 Refund Processed",
                description=(
                    f"**Refunded To:** <@{buyer_id}>\n"
                    f"**Address:** `{address}`\n\n"
                    f"**Transaction ID:** [{tx_hash}]({explorer_url})"
                ),
                color=0xff0000,
                timestamp=datetime.datetime.now()
            )
            
            view = View()
            view.add_item(Button(label="View On Blockchain", url=explorer_url, style=discord.ButtonStyle.link))
            
            await interaction.followup.send(embed=embed, view=view)
            
            # Mark as finalized for 100s close
            deals = load_all_data()
            if self.deal_id in deals:
                deals[self.deal_id]['status'] = 'refunded'
                deals[self.deal_id]['last_activity'] = time.time()
                save_all_data(deals)
            
            await interaction.channel.send("Refund complete. Closing channel in 100s...")
            await asyncio.sleep(100)
            
            # Sweep Dust
            await sweep_dust_fees(self.deal_id, self.deal)
            
            await interaction.channel.delete()

        except Exception as e:
            await interaction.followup.send(f"Failed to process refund: `{str(e)}`", ephemeral=True)

class WithdrawalModal(Modal):
    def __init__(self, deal_id, deal, currency_display, currency):
        super().__init__(title="Withdraw Funds")
        self.deal_id = deal_id
        self.deal = deal
        self.currency_display = currency_display
        self.currency = currency
        
        self.address_input = TextInput(
            label=f"Your {currency_display} Address",
            placeholder=f"Paste your {currency_display} address here...",
            required=True,
            min_length=10,
            max_length=120
        )
        self.add_item(self.address_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        address = self.address_input.value.strip()
        
        if not await is_valid_address(address, self.currency):
            return await interaction.followup.send(f"Invalid {self.currency_display} address.", ephemeral=True)
            
        try:
            seller_id = int(self.deal['seller'])
            buyer_id = int(self.deal['buyer'])
            ltc_amount = self.deal.get('ltc_amount', 0)
            usd_amount = self.deal.get('amount', 0)
            
            # Show "Processing" status
            process_em = discord.Embed(
                title="Withdrawal Processing",
                description="*Preparing transaction...*",
                color=0x0000ff
            )
            status_msg = await interaction.channel.send(embed=process_em)

            # Send funds with fee deduction (passes status_msg for gas funding updates)
            result = await send_funds_with_fee(self.deal, address, status_msg=status_msg)
            
            # Final Status Update
            try: await status_msg.delete()
            except: pass
            
            main_tx = result['main_tx']
            fee_tx = result.get('fee_tx')
            fee_amount = result.get('fee_amount', 0)
            sent_amount = result.get('sent_amount', ltc_amount)
            
            explorer_url = get_explorer_url(self.currency, main_tx)
            
            # Build the embed with transaction details
            description = f"**Recipient:** <@{seller_id}>\n"
            description += f"**Address:** {address}\n\n"
            
            if fee_tx and fee_amount > 0:
                fee_explorer_url = get_explorer_url(self.currency, fee_tx)
                fee_percentage = get_fee_percentage()
                description += f"**Platform Fee ({fee_percentage}%):** `{fee_amount:.8f}` {self.currency_display}\n"
                description += f"**Fee TX:** [{fee_tx[:16]}...]({fee_explorer_url})\n\n"
                description += f"**Amount Sent:** {sent_amount:.8f} {self.currency_display}\n"
            else:
                description += f"**Amount Sent:** {ltc_amount:.8f} {self.currency_display}\n"
            
            description += f"**Transaction:** [{main_tx[:16]}...]({explorer_url})"
            
            em = discord.Embed(
                title=f"✅ {self.currency_display} Sent Successfully",
                description=description,
                color=0x00ff00,
                timestamp=datetime.datetime.now()
            )
            em.set_thumbnail(url="https://cdn.discordapp.com/attachments/1384928504189026466/1385336614699532449/IMG_1336.png")
            
            view = View()
            view.add_item(Button(label="View Transaction", url=explorer_url, style=discord.ButtonStyle.link))
            
            await interaction.channel.send(content=f"<@{seller_id}>", embed=em, view=view)
            
            # Update user stats
            try:
                update_user_stats(str(seller_id), usd_amount)
            except:
                pass
            
            
            # [ENGAGEMENT] Inject Public Log
            await notification_service.post_public_log(interaction.guild, em)

            # [LOGGING]
            audit_service.log_action(
                action="DEAL_WITHDRAWN",
                user_id=seller_id,
                target_id=self.deal_id,
                details=f"Amount: {usd_amount} USD, TX: {main_tx}"
            )

            # [ACHIEVEMENTS] Check if seller unlocked anything
            try:
                seller_user = interaction.guild.get_member(int(seller_id)) or await bot.fetch_user(int(seller_id))
                if seller_user:
                    await achievement_service.check_achievements(seller_id, seller_user)
            except Exception as e:
                print(f"[GAMIFICATION] Error checking achievements (withdrawal): {e}")

            await send_transcript(interaction.channel, seller_id, buyer_id, txid=main_tx)
            
            # Mark as finalized for 100s close
            deals = load_all_data()
            if self.deal_id in deals:
                deals[self.deal_id]['status'] = 'released'
                deals[self.deal_id]['last_activity'] = time.time()
                save_all_data(deals)
            
            await asyncio.sleep(100)
            # Sweep Dust
            await sweep_dust_fees(self.deal_id, self.deal)
            await interaction.channel.delete()

        except Exception as e:
            await interaction.followup.send(f"Failed to send {self.currency_display}: `{str(e)}`", ephemeral=True)


class WithdrawalView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Enter Address to Withdraw", style=discord.ButtonStyle.green, custom_id="withdraw_btn")
    async def withdraw_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        deal_id, deal = get_deal_by_channel(interaction.channel.id)
        if not deal:
            return await interaction.response.send_message("Deal not found.", ephemeral=True)
        
        # Verify user is the Seller (Receiver of funds)
        seller_id = int(deal['seller'])
        if interaction.user.id != seller_id:
             return await interaction.response.send_message("Only the funds receiver can withdraw.", ephemeral=True)

        currency = deal.get('currency', 'ltc')
        currency_display = {
            'ltc': 'LTC',
            'usdt_bep20': 'USDT (BEP20)',
            'usdt_polygon': 'USDT (Polygon)',
            'solana': 'SOL',
            'ethereum': 'ETH'
        }.get(currency, 'Crypto')

        await interaction.response.send_modal(WithdrawalModal(deal_id, deal, currency_display, currency))


class RefundModal(Modal):
    def __init__(self, deal_id, deal, currency_display, currency):
        super().__init__(title="Refund Funds")
        self.deal_id = deal_id
        self.deal = deal
        self.currency_display = currency_display
        self.currency = currency
        
        self.address_input = TextInput(
            label=f"Your {currency_display} Address",
            placeholder=f"Paste your {currency_display} address here...",
            required=True,
            min_length=10,
            max_length=120
        )
        self.add_item(self.address_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        address = self.address_input.value.strip()
        
        if not await is_valid_address(address, self.currency):
            return await interaction.followup.send(f"Invalid {self.currency_display} address.", ephemeral=True)
            
        try:
            seller_id = int(self.deal['seller'])
            buyer_id = int(self.deal['buyer'])
            ltc_amount = self.deal.get('ltc_amount', 0)
            
            # Show "Processing" status
            process_em = discord.Embed(
                title="Refund Processing",
                description="*Preparing transaction...*",
                color=0x0000ff
            )
            status_msg = await interaction.channel.send(embed=process_em)

            # Auto-fund gas for USDT chains
            if self.currency in ['usdt_bep20', 'usdt_polygon']:
                try:
                    await status_msg.edit(embed=discord.Embed(
                        title="Refund Processing",
                        description="*Preparing gas fees...*",
                        color=0x0000ff
                    ))
                except: pass
                
                gas_success = await ensure_deal_gas(self.deal, status_msg=status_msg)
                if not gas_success:
                    await status_msg.delete()
                    return await interaction.followup.send("Failed to fund gas for refund. Please contact support.", ephemeral=True)

            # [LOGGING] Gas funding happens inside send_funds_based_on_currency
            tx_hash = await send_funds_based_on_currency(self.deal, address, status_msg=status_msg)
            
            # Final Status Update
            try: await status_msg.delete()
            except: pass

            currency_display_full = {
                'ltc': 'Litecoin',
                'usdt_bep20': 'USDT (BEP20)',
                'usdt_polygon': 'USDT (Polygon)',
                'solana': 'Solana (SOL)',
                'ethereum': 'Ethereum (ETH)'
            }.get(self.currency, 'Crypto')
            
            explorer_url = get_explorer_url(self.currency, tx_hash)
            
            em = discord.Embed(title=f"✅ {currency_display_full} Refunded", description=f"Address: {address}\nTransaction ID: [{tx_hash}]({explorer_url})", color=0x00ff00)
            await interaction.channel.send(content=f"<@{buyer_id}>", embed=em)

            await send_transcript(interaction.channel, seller_id, buyer_id, txid=tx_hash)
            
            # Mark as finalized for 100s close
            deals = load_all_data()
            if self.deal_id in deals:
                deals[self.deal_id]['status'] = 'refunded'
                deals[self.deal_id]['last_activity'] = time.time()
                save_all_data(deals)
            
            await asyncio.sleep(100)
            # Sweep Dust
            await sweep_dust_fees(self.deal_id, self.deal)
            await interaction.channel.delete()

        except Exception as e:
            await interaction.followup.send(f"Failed to refund {self.currency_display}: `{str(e)}`", ephemeral=True)


class RefundView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Enter Address to Get Funds Back", style=discord.ButtonStyle.green, custom_id="refund_btn")
    async def refund_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        logger.debug(f"[DEBUG] Refund button clicked by {interaction.user.id} in channel {interaction.channel.id}")
        try:
            deal_id, deal = get_deal_by_channel(interaction.channel.id)
            if not deal:
                return await interaction.response.send_message("Deal not found.", ephemeral=True)
            
            # Verify user is the Buyer (Sender of original funds)
            buyer_id = int(deal['buyer'])
            if interaction.user.id != buyer_id:
                 return await interaction.response.send_message("Only the original sender can receive the refund.", ephemeral=True)
            
            currency = deal.get('currency', 'ltc')
            currency_display = {
                'ltc': 'LTC',
                'usdt_bep20': 'USDT (BEP20)',
                'usdt_polygon': 'USDT (Polygon)',
                'solana': 'SOL',
                'ethereum': 'ETH'
            }.get(currency, 'Crypto')
    
            await interaction.response.send_modal(RefundModal(deal_id, deal, currency_display, currency))
        except Exception as e:
            print(f"[RefundBtn] ERROR: {e}")
            import traceback
            traceback.print_exc()
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)

class ReleaseConButton(View):

    def __init__(self):

        super().__init__(timeout=None)

        button = Button(label="Confirm", style=discord.ButtonStyle.green, custom_id="relcon")

        button.callback = self.confirm

        self.add_item(button)

        buttons = Button(label="Cancel", style=discord.ButtonStyle.red, custom_id="relcan")

        buttons.callback = self.cancel

        self.add_item(buttons)



    async def confirm(self, interaction: discord.Interaction):
        deal_id, deal = get_deal_by_channel(interaction.channel.id)
        if not deal:
            await interaction.response.send_message("Deal not found.", ephemeral=True)
            return

        if deal.get('mod_locked'):
            await interaction.response.send_message("⚠️ This deal has been locked by a moderator. Please contact support for assistance.", ephemeral=True)
            return

            

        seller_id = int(deal['seller'])  # Now represents SENDER

        buyer_id = int(deal['buyer'])  # Now represents RECEIVER

        currency = deal.get('currency', 'ltc')



        if interaction.user.id == buyer_id:  # RECEIVER confirms release to SENDER

            await interaction.response.defer()

            await interaction.message.edit(view=None)

            embed = discord.Embed(description=f"{interaction.user.mention} has confirmed to release the funds.")

            await interaction.channel.send(embed=embed)

            

            currency_display = {

                'ltc': 'LTC',

                'usdt_bep20': 'USDT (BEP20)',

                'usdt_polygon': 'USDT (Polygon)',

                'solana': 'SOL',

                'ethereum': 'ETH'

            }.get(currency, 'crypto')

            

            em = discord.Embed(title="Release Funds", color=0x0000ff, description=f"<@{seller_id}> Please click the button below to enter your {currency_display} address and receive funds.")
            
            # Update deal status for persistence
            deals = load_all_data()
            if deal_id in deals:
                deals[deal_id]['status'] = 'awaiting_withdrawal'
                save_all_data(deals)

            await interaction.channel.send(embed=em, view=WithdrawalView())
        
        else:

            await interaction.response.send_message("You are not authorized to use this.", ephemeral=True)



    async def cancel(self, interaction: discord.Interaction):
        deal_id, deal = get_deal_by_channel(interaction.channel.id)
        if not deal:
            await interaction.response.send_message("Deal not found.", ephemeral=True)
            return

        if deal.get('mod_locked'):
            await interaction.response.send_message("⚠️ This deal has been locked by a moderator. Please contact support for assistance.", ephemeral=True)
            return

            

        seller_id = int(deal['seller'])  # Now represents SENDER

        buyer_id = int(deal['buyer'])  # Now represents RECEIVER

        ltcamt = deal['ltc_amount']

        currency = deal.get('currency', 'ltc')



        if interaction.user.id == buyer_id:  # RECEIVER cancels release

            await interaction.response.defer()

            await interaction.message.edit(view=None)

            embed = discord.Embed(description=f"{interaction.user.mention} has cancelled the release.")

            await interaction.channel.send(embed=embed)

            usbal = await currency_to_usd(ltcamt, currency)

            

            currency_display = {

                'ltc': 'LTC',

                'usdt_bep20': 'USDT (BEP20)',

                'usdt_polygon': 'USDT (Polygon)',

                'solana': 'SOL',

                'ethereum': 'ETH'

            }.get(currency, 'Crypto')

            

            confirmed_embed = discord.Embed(title="Deal Confirmation", color=0x0000ff, description=">>> Payment successfully received.")

            confirmed_embed.add_field(name=f"{currency_display} Amount", value=f"{ltcamt:.8f}", inline=False)

            confirmed_embed.add_field(name="USD Amount", value=f"{usbal}$", inline=False)

            confirmed_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1384928504189026466/1385336614699532449/IMG_1336.png?ex=6855b2c3&is=68546143&hm=f3ad66f898ac9a5281b0cbd027111eebcb0f4bebc4cfb1fbe9f53922a45793d7&")

            await interaction.channel.send(embed=confirmed_embed, view=ReleaseButton())

        else:

            await interaction.response.send_message("You are not authorized to use this.", ephemeral=True)



class CancelConButton(View):

    def __init__(self):

        super().__init__(timeout=None)

        button = Button(label="Confirm", style=discord.ButtonStyle.green, custom_id="cancon")

        button.callback = self.confirm

        self.add_item(button)

        buttons = Button(label="Cancel", style=discord.ButtonStyle.red, custom_id="cancan")

        buttons.callback = self.cancel

        self.add_item(buttons)



    async def confirm(self, interaction: discord.Interaction):
        deal_id, deal = get_deal_by_channel(interaction.channel.id)
        if not deal:
            await interaction.response.send_message("Deal not found.", ephemeral=True)
            return

        if deal.get('mod_locked'):
            await interaction.response.send_message("⚠️ This deal has been locked by a moderator. Please contact support for assistance.", ephemeral=True)
            return

            

        seller_id = int(deal['seller'])  # Now represents SENDER

        buyer_id = int(deal['buyer'])  # Now represents RECEIVER

        currency = deal.get('currency', 'ltc')



        if interaction.user.id == seller_id:  # SENDER confirms cancellation
            await interaction.response.defer()
            await interaction.message.edit(view=None)
            embed = discord.Embed(description=f"{interaction.user.mention} has confirmed to cancel the deal.")
            await interaction.channel.send(embed=embed)

            currency_display = {
                'ltc': 'LTC',
                'usdt_bep20': 'USDT (BEP20)',
                'usdt_polygon': 'USDT (Polygon)',
                'solana': 'SOL',
                'ethereum': 'ETH'
            }.get(currency, 'crypto')

            em = discord.Embed(
                title="Cancel Deal", 
                color=0x0000ff, 
                description=f"<@{buyer_id}> Please click the button below to provide your address and get the funds back."
            )
            await interaction.channel.send(embed=em, view=RefundView())

        else:
            await interaction.response.send_message("You are not authorized to use this.", ephemeral=True)


    async def cancel(self, interaction: discord.Interaction):
        deal_id, deal = get_deal_by_channel(interaction.channel.id)
        if not deal:
            await interaction.response.send_message("Deal not found.", ephemeral=True)
            return

        if deal.get('mod_locked'):
            await interaction.response.send_message("⚠️ This deal has been locked by a moderator. Please contact support for assistance.", ephemeral=True)
            return

            

        seller_id = int(deal['seller'])  # Now represents SENDER

        buyer_id = int(deal['buyer'])  # Now represents RECEIVER

        ltcamt = deal['ltc_amount']



        if interaction.user.id == seller_id:  # SENDER cancels (fixing the logic)

            await interaction.response.defer()

            embed = discord.Embed(description=f"{interaction.user.mention} has cancelled the release.")

            await interaction.channel.send(embed=embed)

            release_msg_id = deal['release_message_id']

            msg = await interaction.channel.fetch_message(release_msg_id)

            view = ReleaseButton()

            view.release_button.disabled = False

            view.cancel_button.disabled = False

            await msg.edit(view=view)

        else:

            await interaction.response.send_message("You are not authorized to use this.", ephemeral=True)



# =====================================================

# UTILITY FUNCTIONS

# =====================================================



async def is_valid_address(address: str, currency: str) -> bool:

    """Validate address based on currency"""

    if currency == 'ltc':

        return await is_valid_ltc_address(address)

    elif currency in ['usdt_bep20', 'usdt_polygon', 'ethereum']:

        return Web3.is_address(address)

    elif currency == 'solana':

        try:

            from solders.pubkey import Pubkey

            Pubkey.from_string(address)

            return True

        except:

            return False

    return False



async def is_valid_ltc_address(address: str) -> bool:

    """Validate LTC address"""

    url = f"https://litecoinspace.org/api/address/{address}"

    try:

        async with aiohttp.ClientSession() as session:

            async with session.get(url) as resp:

                return resp.status == 200

    except Exception:

        return False






async def get_evm_nonce_parallel(address, currency):
    """Fetch current nonce from multiple RPCs for robustness."""
    from web3 import AsyncWeb3, AsyncHTTPProvider
    
    # Map currency to correct RPC list
    rpc_urls = []
    if currency == 'usdt_polygon':
        rpc_urls = config.POLYGON_RPC_URLS
    elif currency == 'usdt_bep20':
        rpc_urls = config.BEP20_RPC_URLS
    elif currency == 'ethereum':
        rpc_urls = config.ETH_RPC_URLS
    
    if not rpc_urls:
        return 0
    
    for rpc in rpc_urls:
        w3 = None
        try:
            w3 = AsyncWeb3(AsyncHTTPProvider(rpc, request_kwargs={"timeout": 5}))
            if await w3.is_connected():
                from_addr = AsyncWeb3.to_checksum_address(address)
                return await w3.eth.get_transaction_count(from_addr)
        except:
            continue
        finally:
            if w3 is not None:
                try: await w3.provider.session.close()
                except: pass
    return 0


# REDUNDANT LOCAL DEFINITION REMOVED - NOW USING STANDARDIZED VERSION IN utils.confirmation_utils
# async def get_evm_confirmations(tx_hash, rpc_urls=None):
#    ...



async def get_solana_confirmations(tx_hash, rpc_urls=None):
    """
    Robust parallel Solana confirmation checker.
    Returns 2 if finalized, 1 if confirmed, 0 otherwise. Checks all RPCs in parallel.
    """
    if not tx_hash: return 0
    from solana.rpc.async_api import AsyncClient
    
    if not rpc_urls:
        from config import SOLANA_RPC_URLS
        rpc_urls = SOLANA_RPC_URLS

    async def fetch_conf(url):
        try:
            async with AsyncClient(url) as client:
                resp = await asyncio.wait_for(client.get_signature_statuses([tx_hash]), timeout=8)
                if resp.value and resp.value[0]:
                    status = resp.value[0].confirmation_status
                    if status == "finalized": return 2
                    if status == "confirmed": return 1
            return 0
        except:
            return 0

    tasks = [fetch_conf(url) for url in rpc_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_results = [r for r in results if isinstance(r, int)]
    return max(valid_results) if valid_results else 0

async def generate_qr_bytes(text):

    """Generate QR code bytes"""

    try:

        qr = qrcode.QRCode(

            version=1,

            error_correction=qrcode.constants.ERROR_CORRECT_L,

            box_size=20,

            border=4,

        )

        qr.add_data(text)

        qr.make(fit=True)



        img = qr.make_image(fill_color="black", back_color="white")

        

        with io.BytesIO() as output:

            img.save(output, format="PNG")

            return output.getvalue()

    except Exception as e:

        print(f"Error generating QR code: {e}")

        return None



# =====================================================

# BOT COMMANDS

# =====================================================



@bot.tree.command(name="check_balance", description="Check balance for any currency address")

@app_commands.describe(address="Wallet address", currency="Currency type")

async def check_balance_cmd(interaction: discord.Interaction, address: str, currency: str = "ltc"):

    await interaction.response.defer(ephemeral=True)



    if interaction.user.id not in OWNER_IDS:

        await interaction.followup.send("You are not authorized.", ephemeral=True)

        return



    try:

        if currency == "ltc":

            confirmed, unconfirmed = await get_balance_async(address)

            total = confirmed + unconfirmed

        elif currency == "usdt_bep20":

            total = await get_usdt_balance_parallel(USDT_BEP20_CONTRACT, address, BEP20_RPC_URLS, USDT_BEP20_DECIMALS)

            confirmed = total

            unconfirmed = 0

        elif currency == "usdt_polygon":

            total = await get_usdt_balance_parallel(USDT_POLYGON_CONTRACT, address, POLYGON_RPC_URLS, USDT_POLYGON_DECIMALS)

            confirmed = total

            unconfirmed = 0

        elif currency == "solana":

            total = await get_solana_balance_parallel(address)

            confirmed = total

            unconfirmed = 0

        elif currency == "ethereum":

            total = await get_eth_balance_parallel(address)

            confirmed = total

            unconfirmed = 0

        else:

            await interaction.followup.send("Unsupported currency.", ephemeral=True)

            return



        usd_value = await currency_to_usd(total, currency)

        

        currency_display = {

            'ltc': 'LTC',

            'usdt_bep20': 'USDT (BEP20)',

            'usdt_polygon': 'USDT (Polygon)',

            'solana': 'SOL',

            'ethereum': 'ETH'

        }.get(currency, currency.upper())

        

        embed = discord.Embed(title=f"{currency_display} Balance", color=0x0000ff)

        embed.add_field(name="Address", value=f"`{address}`", inline=False)

        embed.add_field(name="Confirmed", value=f"`{confirmed}`", inline=True)

        embed.add_field(name="Unconfirmed", value=f"`{unconfirmed}`", inline=True)

        embed.add_field(name="Total", value=f"`{total}`", inline=True)

        embed.add_field(name="USD Value", value=f"`${usd_value:.2f}`", inline=True)

        

        await interaction.followup.send(embed=embed, ephemeral=True)

        

    except Exception as e:

        await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)



@bot.tree.command(name="check_txid", description="Check Ethereum transaction details")

@app_commands.describe(tx_signature="Ethereum transaction hash")

async def check_txid_cmd(interaction: discord.Interaction, tx_signature: str):

    await interaction.response.defer(ephemeral=True)



    if interaction.user.id not in OWNER_IDS:

        await interaction.followup.send("You are not authorized.", ephemeral=True)

        return



    try:

        # For ETH transactions, we need to use web3 to get details

        tx_details = None

        for rpc_url in ETH_RPC_URLS:

            try:

                w3 = Web3(Web3.HTTPProvider(rpc_url))

                if w3.is_connected():

                    tx_details = w3.eth.get_transaction(tx_signature)

                    if tx_details:

                        break

            except:

                continue



        if not tx_details:

            await interaction.followup.send("Transaction not found.", ephemeral=True)

            return



        embed = discord.Embed(

            title="Ethereum Transaction Details",

            color=0x0000ff

        )



        # Extract basic info

        block_number = tx_details.blockNumber

        from_addr = tx_details['from']

        to_addr = tx_details['to']

        value_eth = tx_details.value / (10 ** 18)

        gas_used = tx_details.gas

        gas_price = tx_details.gasPrice / (10 ** 9)  # Convert to Gwei



        # Get block timestamp

        block_timestamp = None

        for rpc_url in ETH_RPC_URLS:

            try:

                w3 = Web3(Web3.HTTPProvider(rpc_url))

                if w3.is_connected():

                    block = w3.eth.get_block(block_number)

                    block_timestamp = block.timestamp

                    break

            except:

                continue



        if block_timestamp:

            from datetime import datetime

            timestamp = datetime.fromtimestamp(block_timestamp).strftime('%Y-%m-%d %H:%M:%S')

        else:

            timestamp = 'Unknown'



        embed.add_field(name="Transaction Hash", value=f"`{tx_signature}`", inline=False)

        embed.add_field(name="From", value=f"`{from_addr}`", inline=False)

        embed.add_field(name="To", value=f"`{to_addr}`", inline=False)

        embed.add_field(name="Value", value=f"`{value_eth:.6f} ETH`", inline=True)

        embed.add_field(name="Block", value=f"`{block_number}`", inline=True)

        embed.add_field(name="Gas Used", value=f"`{gas_used}`", inline=True)

        embed.add_field(name="Gas Price", value=f"`{gas_price:.2f} Gwei`", inline=True)

        embed.add_field(name="Timestamp", value=f"`{timestamp}`", inline=True)



        embed.add_field(

            name="Explorer", 

            value=f"[View on Etherscan](https://etherscan.io/tx/0x{tx_signature})", 

            inline=False

        )



        await interaction.followup.send(embed=embed, ephemeral=True)



    except Exception as e:

        await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)



@bot.tree.command(name="list_transactions", description="List recent Ethereum transactions for address")

@app_commands.describe(address="Ethereum address")

async def list_transactions_cmd(interaction: discord.Interaction, address: str):

    await interaction.response.defer(ephemeral=True)



    if interaction.user.id not in OWNER_IDS:

        await interaction.followup.send("You are not authorized.", ephemeral=True)

        return



    try:

        # For ETH, we'll get recent transactions from Etherscan-like API

        # Note: This is a simplified version - you might want to use a proper ETH block explorer API

        embed = discord.Embed(

            title=f"Ethereum Address - {address[:8]}...{address[-8:]}",

            color=0x0000ff

        )



        # Get current balance

        balance = await get_eth_balance_parallel(address)

        usd_value = await currency_to_usd(balance, "ethereum")



        embed.add_field(name="Current Balance", value=f"`{balance:.6f} ETH` (${usd_value:.2f})", inline=False)

        embed.add_field(

            name="Explorer", 

            value=f"[View on Etherscan](https://etherscan.io/address/{address})", 

            inline=False

        )



        embed.add_field(

            name="Note", 

            value="For detailed transaction history, please use Etherscan directly.", 

            inline=False

        )



        await interaction.followup.send(embed=embed, ephemeral=True)



    except Exception as e:

        await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)



@bot.tree.command(name="stats", description="Check deal statistics for yourself or another user.")
@app_commands.describe(user="The user to check (optional, defaults to you)")
async def stats_cmd(interaction: discord.Interaction, user: discord.Member = None):
    await interaction.response.defer() # Not ephemeral, so others can see the flex
    
    target_user = user or interaction.user
    stats = get_single_user_stats(target_user.id)
    
    deals = stats.get("deals", 0)
    volume = stats.get("volume", 0.0)
    
    # "Professional" Look
    embed = discord.Embed(
        description=f"### {target_user.mention}\n\n**Deals completed:**\n{deals}\n\n**Total USD Value:**\n${volume:,.2f}",
        color=0x2ECC71 # Emerald Green
    )
    
    # Avatar on the right (thumbnail)
    if target_user.avatar:
        embed.set_thumbnail(url=target_user.avatar.url)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="force_cancel", description="Force cancel a deal and refund (Owner Only)")
@app_commands.describe(deal_id="The deal ID (optional inside ticket)")
@app_commands.autocomplete(deal_id=deal_id_autocomplete)
async def force_cancel(interaction: discord.Interaction, deal_id: str = None):
    await interaction.response.defer()

    if interaction.user.id not in OWNER_IDS:
        await interaction.followup.send("You are not authorized.", ephemeral=True)
        return

    # Auto-sync deal_id from channel if not provided
    if not deal_id:
        detected_did, detected_deal = get_deal_by_channel(interaction.channel_id)
        if detected_did:
            deal_id = detected_did
            deal = detected_deal
        else:
            await interaction.followup.send("Please provide a `deal_id` or used this command inside a deal channel.", ephemeral=True)
            return
    else:
        deal = get_deal_by_dealid(deal_id)

    if not deal:
        await interaction.followup.send(f"Deal `{deal_id}` not found.", ephemeral=True)
        return

    # Strict Auto-Targeting: Always target the Buyer (Sender) for refund
    buyer_id = int(deal.get("buyer", 0) or 0)
    if buyer_id:
        try:
            user = await bot.fetch_user(buyer_id)
        except:
            await interaction.followup.send(f"Could not find Sender (ID: {buyer_id}). Alerting admin manually is required.", ephemeral=True)
            return
    else:
         await interaction.followup.send("Deal has no Sender recorded. Cannot auto-refund.", ephemeral=True)
         return



    pending_force_actions[user.id] = {

        "deal_id": deal_id,

        "type": "cancel", 

        "deal": deal

    }



    currency_display = {

        'ltc': 'LTC',

        'usdt_bep20': 'USDT (BEP20)',

        'usdt_polygon': 'USDT (Polygon)',

        'solana': 'SOL',

        'ethereum': 'ETH'

    }.get(deal.get('currency', 'ltc'), 'crypto')



    embed = discord.Embed(

        title="Force Cancel Initiated",

        color=0xff0000,

        description=(

            f"<@{user.id}> your deal has been force-cancelled by the admin.\n\n"

            f"Please **send your {currency_display} address here** to receive your refund."

        )

    )

    

    channel_id = deal.get('channel_id')

    if channel_id:

        channel = bot.get_channel(int(channel_id))

        if channel:

            await channel.send(embed=embed, view=RefundView())

    

    await interaction.followup.send("Force cancel started.", ephemeral=True)



@bot.tree.command(name="force_release", description="Force release funds to the seller. (Owner Only)")
@app_commands.describe(deal_id="The deal ID (optional inside ticket)")
@app_commands.autocomplete(deal_id=deal_id_autocomplete)
async def force_release(interaction: discord.Interaction, deal_id: str = None):
    await interaction.response.defer()

    if interaction.user.id not in OWNER_IDS:
        await interaction.followup.send("You are not authorized.", ephemeral=True)
        return

    # Auto-sync deal_id from channel if not provided
    if not deal_id:
        detected_did, detected_deal = get_deal_by_channel(interaction.channel_id)
        if detected_did:
            deal_id = detected_did
            deal = detected_deal
        else:
            await interaction.followup.send("Please provide a `deal_id` or use this command inside a deal channel.", ephemeral=True)
            return
    else:
        deal = get_deal_by_dealid(deal_id)

    if not deal:
        await interaction.followup.send(f"Deal `{deal_id}` not found.", ephemeral=True)
        return

    # Strict Auto-Targeting: Always target the Seller (Receiver) for release
    seller_id = int(deal.get("seller", 0) or 0)
    if seller_id:
        try:
            user = await bot.fetch_user(seller_id)
        except:
            await interaction.followup.send(f"Could not find Receiver (ID: {seller_id}). Alerting admin manually is required.", ephemeral=True)
            return
    else:
            await interaction.followup.send("Deal has no Receiver recorded. Cannot auto-release.", ephemeral=True)
            return



    pending_force_actions[user.id] = {

        "deal_id": deal_id,

        "type": "release",

        "deal": deal

    }



    currency_display = {

        'ltc': 'LTC',

        'usdt_bep20': 'USDT (BEP20)',

        'usdt_polygon': 'USDT (Polygon)',

        'solana': 'SOL',

        'ethereum': 'ETH'

    }.get(deal.get('currency', 'ltc'), 'crypto')



    embed = discord.Embed(

        title="Force Release Initiated",

        color=0x0000ff,

        description=(

            f"<@{user.id}> admin has force-released the deal.\n\n"

            f"Please **send your {currency_display} address** to receive the funds."

        )

    )



    channel_id = deal.get('channel_id')

    if channel_id:

        channel = bot.get_channel(int(channel_id))

        if channel:

            await channel.send(embed=embed, view=WithdrawalView())

    

    await interaction.followup.send("Force release started.", ephemeral=True)




@bot.tree.command(name="mod_lock", description="Lock Release/Cancel buttons for a deal (Owner Only)")
@app_commands.describe(deal_id="The deal ID (optional inside ticket)")
@app_commands.autocomplete(deal_id=deal_id_autocomplete)
async def mod_lock(interaction: discord.Interaction, deal_id: str = None):
    await interaction.response.defer(ephemeral=True)
    if interaction.user.id not in OWNER_IDS:
        await interaction.followup.send("You are not authorized.", ephemeral=True)
        return

    if not deal_id:
        detected_did, detected_deal = get_deal_by_channel(interaction.channel_id)
        if detected_did:
            deal_id = detected_did
            deal = detected_deal
        else:
            await interaction.followup.send("Please provide a `deal_id` or use this command inside a deal channel.", ephemeral=True)
            return
    else:
        deal = get_deal_by_dealid(deal_id)

    if not deal:
        await interaction.followup.send(f"Deal `{deal_id}` not found.", ephemeral=True)
        return

    deal['mod_locked'] = True
    update_deal(interaction.channel_id, deal)
    await interaction.followup.send(f"✅ Deal `{deal_id}` has been locked by a moderator.", ephemeral=True)
    
    embed = discord.Embed(title="⚠️ Deal Locked", description="A moderator has locked the Release and Cancel buttons for this deal.", color=discord.Color.orange())
    await interaction.channel.send(embed=embed)


@bot.tree.command(name="mod_unlock", description="Unlock Release/Cancel buttons for a deal (Owner Only)")
@app_commands.describe(deal_id="The deal ID (optional inside ticket)")
@app_commands.autocomplete(deal_id=deal_id_autocomplete)
async def mod_unlock(interaction: discord.Interaction, deal_id: str = None):
    await interaction.response.defer(ephemeral=True)
    
    # Allow Admins or Executive Role
    is_admin = interaction.user.guild_permissions.administrator
    has_role = False
    if EXECUTIVE_ROLE_ID:
        has_role = interaction.user.get_role(EXECUTIVE_ROLE_ID) is not None
    
    if not (is_admin or has_role or interaction.user.id in OWNER_IDS):
        await interaction.followup.send("You are not authorized.", ephemeral=True)
        return

    if not deal_id:
        detected_did, detected_deal = get_deal_by_channel(interaction.channel_id)
        if detected_did:
            deal_id = detected_did
            deal = detected_deal
        else:
            await interaction.followup.send("Please provide a `deal_id` or use this command inside a deal channel.", ephemeral=True)
            return
    else:
        deal = get_deal_by_dealid(deal_id)

    if not deal:
        await interaction.followup.send(f"Deal `{deal_id}` not found.", ephemeral=True)
        return

    deal['mod_locked'] = False
    update_deal(interaction.channel_id, deal)
    await interaction.followup.send(f"✅ Deal `{deal_id}` has been unlocked.", ephemeral=True)

    embed = discord.Embed(title="🔓 Deal Unlocked", description="A moderator has unlocked the Release and Cancel buttons for this deal.", color=discord.Color.green())
    await interaction.channel.send(embed=embed)



async def update_embeds_on_change(channel, deal):
    """
    Scans the channel for relevant embeds and updates them with new deal participants.
    Targets: "User Selection", "User Confirmation", "RainyDay Auto MiddleMan System"
    """
    try:
        buyer_id = deal.get("buyer")
        seller_id = deal.get("seller")
        
        buyer_display = get_rich_user_display(channel.guild, buyer_id)
        seller_display = get_rich_user_display(channel.guild, seller_id)
        
        async for message in channel.history(limit=50):
            if message.author.id == bot.user.id and message.embeds:
                embed = message.embeds[0]
                
                # 1. Update "User Selection"
                if embed.title == "User Selection":
                    new_desc = (
                        f"**Sender**\n{buyer_display}\n\n"
                        f"**Receiver**\n{seller_display}"
                    )
                    new_embed = discord.Embed(title=embed.title, description=new_desc, color=embed.color)
                    if embed.thumbnail: new_embed.set_thumbnail(url=embed.thumbnail.url)
                    if embed.author: new_embed.set_author(name=embed.author.name, icon_url=embed.author.icon_url)
                    await message.edit(embed=new_embed)
                    
                # 2. Update "User Confirmation"
                elif embed.title == "User Confirmation":
                    new_embed = embed.copy()
                    new_embed.clear_fields()
                    new_embed.add_field(name="Sender", value=buyer_display, inline=False)
                    new_embed.add_field(name="Receiver", value=seller_display, inline=False)
                    await message.edit(embed=new_embed)
                    
                # 3. Update "RainyDay Auto MiddleMan System"
                elif embed.title == "RainyDay Auto MiddleMan System":
                    # Reconstruct description to be safe
                    new_desc = (
                        "### 🛡️ Secure Transaction Protocol\n"
                        "• This channel is monitored by our automated escrow system.\n"
                        "• All funds are held securely until the buyer confirms receipt.\n"
                        "• Always confirm you have received the goods before releasing funds.\n\n"
                        "### 📝 Deal Context\n"
                        f"• **Sender:** {buyer_display}\n"
                        f"• **Receiver:** {seller_display}\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    )
                    new_embed = discord.Embed(title=embed.title, description=new_desc, color=embed.color)
                    if embed.thumbnail: new_embed.set_thumbnail(url=embed.thumbnail.url)
                    if embed.author: new_embed.set_author(name=embed.author.name, icon_url=embed.author.icon_url)
                    if embed.footer: new_embed.set_footer(text=embed.footer.text, icon_url=embed.footer.icon_url)
                    
                    # Add back fields (Warning Note)
                    if embed.fields:
                         for f in embed.fields:
                             new_embed.add_field(name=f.name, value=f.value, inline=f.inline)
                             
                    await message.edit(embed=new_embed)
                    
    except Exception as e:
        print(f"Failed to update embeds: {e}")



@bot.tree.command(name="change-buyer", description="Change the Buyer/Sender of a deal (Owner Only)")
@app_commands.describe(user="The new Buyer/Sender", deal_id="Optional deal ID")
@app_commands.autocomplete(deal_id=deal_id_autocomplete)
async def change_buyer_cmd(interaction: discord.Interaction, user: discord.Member, deal_id: str = None):
    await interaction.response.defer(ephemeral=True)
    
    if interaction.user.id not in OWNER_IDS:
        return await interaction.followup.send("You are not authorized.", ephemeral=True)

    # Resolve Deal
    if not deal_id:
        detected_did, detected_deal = get_deal_by_channel(interaction.channel_id)
        if detected_did:
            deal_id = detected_did
            deal = detected_deal
        else:
            return await interaction.followup.send("Please provide a `deal_id` or use inside a deal channel.", ephemeral=True)
    else:
        deal = get_deal_by_dealid(deal_id)
    
    if not deal:
        return await interaction.followup.send(f"Deal `{deal_id}` not found.", ephemeral=True)

    # 1. Handle Permissions
    channel_id = deal.get("channel_id")
    if channel_id:
        channel = bot.get_channel(int(channel_id))
        if channel:
            # Remove OLD buyer
            old_buyer_id = deal.get("buyer")
            if old_buyer_id and old_buyer_id != "None":
                try:
                    old_member = await bot.fetch_user(int(old_buyer_id))
                    # Note: We can't remove permissions for a User object if they aren't in guild, 
                    # but we try to get Member from guild if possible.
                    guild = interaction.guild
                    member_obj = guild.get_member(int(old_buyer_id))
                    if member_obj:
                         await channel.set_permissions(member_obj, overwrite=None)
                except Exception as e:
                    print(f"Failed to remove permissions for old buyer: {e}")

            # Add NEW buyer
            await channel.set_permissions(user, read_messages=True, send_messages=True)
            await channel.send(f"🔄 **Update:** {user.mention} is now the **Sender (Buyer)**.")

    # 2. Update Database
    deal["buyer"] = str(user.id)
    update_deal(deal.get("channel_id", interaction.channel_id), deal)
    
    # 3. Update Embeds (Visual Sync)
    if channel:
        await update_embeds_on_change(channel, deal)

    await interaction.followup.send(f"✅ Buyer changed to {user.mention} for deal `{deal_id}`.")


@bot.tree.command(name="change-seller", description="Change the Seller/Receiver of a deal (Owner Only)")
@app_commands.describe(user="The new Seller/Receiver", deal_id="Optional deal ID")
@app_commands.autocomplete(deal_id=deal_id_autocomplete)
async def change_seller_cmd(interaction: discord.Interaction, user: discord.Member, deal_id: str = None):
    await interaction.response.defer(ephemeral=True)
    
    if interaction.user.id not in OWNER_IDS:
        return await interaction.followup.send("You are not authorized.", ephemeral=True)

    # Resolve Deal
    if not deal_id:
        detected_did, detected_deal = get_deal_by_channel(interaction.channel_id)
        if detected_did:
            deal_id = detected_did
            deal = detected_deal
        else:
            return await interaction.followup.send("Please provide a `deal_id` or use inside a deal channel.", ephemeral=True)
    else:
        deal = get_deal_by_dealid(deal_id)
    
    if not deal:
        return await interaction.followup.send(f"Deal `{deal_id}` not found.", ephemeral=True)

    # 1. Handle Permissions
    channel_id = deal.get("channel_id")
    if channel_id:
        channel = bot.get_channel(int(channel_id))
        if channel:
            # Remove OLD seller
            old_seller_id = deal.get("seller")
            if old_seller_id and old_seller_id != "None":
                try:
                    guild = interaction.guild
                    member_obj = guild.get_member(int(old_seller_id))
                    if member_obj:
                         await channel.set_permissions(member_obj, overwrite=None)
                except Exception as e:
                    print(f"Failed to remove permissions for old seller: {e}")

            # Add NEW seller
            await channel.set_permissions(user, read_messages=True, send_messages=True)
            await channel.send(f"🔄 **Update:** {user.mention} is now the **Receiver (Seller)**.")

    # 2. Update Database
    deal["seller"] = str(user.id)
    update_deal(deal.get("channel_id", interaction.channel_id), deal)
    
    # 3. Update Embeds (Visual Sync)
    if channel:
        await update_embeds_on_change(channel, deal)

    await interaction.followup.send(f"✅ Seller changed to {user.mention} for deal `{deal_id}`.")


@bot.tree.command(name="add", description="Add a user to this deal channel.")

@app_commands.describe(user="User to add in this channel.")

async def add_user_cmd(interaction: discord.Interaction, user: discord.User):

    if interaction.user.id not in OWNER_IDS:

        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)

        return



    channel = interaction.channel



    if not isinstance(channel, discord.TextChannel):

        await interaction.response.send_message("This command can only be used inside a text channel.", ephemeral=True)

        return



    try:

        await channel.set_permissions(

            user,

            read_messages=True,

            send_messages=True,

            read_message_history=True,

            view_channel=True

        )

    except Exception as e:

        await interaction.response.send_message(f"Failed to add user: {e}", ephemeral=True)

        return



    embed = discord.Embed(

        title="User Added",

        description=f"> **{user.mention}** has been added to this channel.",

        color=0x0000ff

    )



    await interaction.response.send_message(embed=embed)



@bot.tree.command(name="remove", description="Remove a user from this deal channel.")

@app_commands.describe(user="User to remove from this channel.")

async def remove_user_cmd(interaction: discord.Interaction, user: discord.User):

    if interaction.user.id not in OWNER_IDS:

        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)

        return



    channel = interaction.channel



    if not isinstance(channel, discord.TextChannel):

        await interaction.response.send_message("This command can only be used inside a text channel.", ephemeral=True)

        return



    try:

        await channel.set_permissions(user, overwrite=None)

    except Exception as e:

        await interaction.response.send_message(f"Failed to remove user: {e}", ephemeral=True)

        return



    embed = discord.Embed(

        title="User Removed",

        description=f"> **{user.mention}** has been removed from this channel.",

        color=0xff0000

    )



    await interaction.response.send_message(embed=embed)



# =====================================================

# EXISTING COMMANDS (PRESERVED)

# =====================================================



@bot.tree.command(name="transcript", description="Export transcript of a channel")

@app_commands.describe(

    channel_id="The channel ID to export transcript from",

    user="User to DM the transcript to (optional)",

    target_channel="Channel to send transcript to (optional)"

)

async def transcript_cmd(

    interaction: discord.Interaction, 

    channel_id: str,

    user: discord.User = None,

    target_channel: discord.TextChannel = None

):

    await interaction.response.defer(ephemeral=True)



    if interaction.user.id not in OWNER_IDS:

        await interaction.followup.send("You are not authorized to use this command.", ephemeral=True)

        return



    try:

        channel = bot.get_channel(int(channel_id))

        if not channel:

            await interaction.followup.send("Invalid channel ID.", ephemeral=True)

            return



        transcript = await chat_exporter.export(

            channel,

            tz_info="Asia/Kolkata",

            military_time=True,

            fancy_times=True

        )



        if not transcript:

            await interaction.followup.send("Failed to export transcript.", ephemeral=True)

            return



        transcript_bytes = transcript.encode("utf-8")

        file = discord.File(io.BytesIO(transcript_bytes), filename=f"{channel.name}_transcript.html")



        embed = discord.Embed(

            title="Channel Transcript",

            description=f"Transcript for channel: {channel.mention}",

            color=0x0000ff

        )



        if user:

            try:

                await user.send(embed=embed, file=file)

                await interaction.followup.send(f"Transcript sent to {user.mention}", ephemeral=True)

            except Exception as e:

                await interaction.followup.send(f"Failed to DM user: {e}", ephemeral=True)

        

        elif target_channel:

            await target_channel.send(embed=embed, file=file)

            await interaction.followup.send(f"Transcript sent to {target_channel.mention}", ephemeral=True)

        

        else:

            await interaction.followup.send(embed=embed, file=file, ephemeral=True)



    except Exception as e:

        await interaction.followup.send(f"Error: {str(e)}", ephemeral=True)



@bot.tree.command(name="send_funds", description="Send funds from a deal wallet (Owner Only)")

@app_commands.describe(deal_id="The deal ID", address="Address to send to")

async def send_funds_command(interaction: discord.Interaction, deal_id: str, address: str):

    await interaction.response.defer()



    if interaction.user.id not in OWNER_IDS:

        await interaction.followup.send("You are not authorized to use this command.", ephemeral=True)

        return



    deal = get_deal_by_dealid(deal_id)

    if not deal:

        await interaction.followup.send("Deal not found.", ephemeral=True)

        return



    currency = deal.get('currency', 'ltc')

    if not await is_valid_address(address, currency):

        await interaction.followup.send(f"Invalid {currency.upper()} address.", ephemeral=True)

        return



    try:

        tx_hash = await send_funds_based_on_currency(deal, address)

        

        currency_display = {

            'ltc': 'Litecoin',

            'usdt_bep20': 'USDT (BEP20)',

            'usdt_polygon': 'USDT (Polygon)',

            'solana': 'Solana (SOL)',

            'ethereum': 'Ethereum (ETH)'

        }.get(currency, 'Crypto')

        

        explorer_url = get_explorer_url(currency, tx_hash)

        

        em = discord.Embed(

            title=f"{currency_display} Sent (Admin)",

            description=f"Address: `{address}`\nTransaction ID: [{tx_hash}]({explorer_url})",

            color=0x0000ff

        )

        await interaction.followup.send(embed=em)



    except Exception as e:

        await interaction.followup.send(f"Failed to send funds: `{str(e)}`", ephemeral=True)





    except Exception as e:

        await interaction.followup.send(f"Failed to send funds: `{str(e)}`", ephemeral=True)





@bot.tree.command(name="leaderboard", description="Show top users by volume")
async def leaderboard(interaction: discord.Interaction):
    try:
        await interaction.response.defer(ephemeral=False)
        
        top_users = get_top_users(limit=10)
        
        if not top_users:
            return await interaction.followup.send("No stats available yet.", ephemeral=True)
        
        desc = ""
        for idx, (uid, stats) in enumerate(top_users, 1):
            desc += f"**{idx}.** <@{uid}> - `${stats['volume']:.2f}` ({stats['deals']} deals)\n"
            
        embed = discord.Embed(
            title="🏆 RainyDay Leaderboard",
            description=desc,
            color=0xffd700
        )
        embed.set_footer(text="RainyDay MM Stats")
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        print(f"[Leaderboard Error] {e}")
        try:
            await interaction.followup.send(f"Error fetching leaderboard: {e}", ephemeral=True)
        except:
            pass

@bot.tree.command(name="recover", description="Recover a deleted deal channel (Owner Only)")
@app_commands.describe(deal_id="The Deal ID to recover")
async def recover_cmd(interaction: discord.Interaction, deal_id: str):
    await interaction.response.defer(ephemeral=True)
    
    if interaction.user.id not in OWNER_IDS:
        return await interaction.followup.send("Not authorized.", ephemeral=True)
        
    deal_info = get_deal_by_dealid(deal_id)
    if not deal_info:
        return await interaction.followup.send(f"Deal ID `{deal_id}` not found in database.", ephemeral=True)
        
    guild = interaction.guild
    if not guild:
        return await interaction.followup.send("Command must be used in a server.", ephemeral=True)
        
    # Recreate Channel
    category = None
    if CATEGORY_ID_1: category = guild.get_channel(int(CATEGORY_ID_1))
    if not category and CATEGORY_ID_2: category = guild.get_channel(int(CATEGORY_ID_2))
    
    # Permissions
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    
    # Add Buyer/Seller
    buyer_id = int(deal_info.get('buyer', 0))
    seller_id = int(deal_info.get('seller', 0))
    
    buyer_member = guild.get_member(buyer_id)
    seller_member = guild.get_member(seller_id)
    
    if buyer_member: overwrites[buyer_member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    if seller_member: overwrites[seller_member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
    
    try:
        channel_name = f"recovered-{deal_id}"
        new_channel = await guild.create_text_channel(name=channel_name, category=category, overwrites=overwrites)
        
        # Update DB
        deal_info['channel_id'] = new_channel.id
        data = load_all_data()
        data[deal_id] = deal_info
        save_all_data(data)
        
        await interaction.followup.send(f"Recovered channel: {new_channel.mention}", ephemeral=True)
        
        # =====================================================
        # RESTORE CONTEXT (SIMULATED HISTORY)
        # =====================================================
        
        # 1. Consolidated Premium Welcome Embed
        logo_url = "https://cdn.discordapp.com/attachments/1383487913186169032/1384932699717898300/Untitled-2.png"
        
        embed = discord.Embed(
            title="🛡️ RainyDay Auto MiddleMan System [RECOVERED]",
            description=(
                "**RainyDay MM** is a premier platform specializing in secure intermediary transactions. "
                "We prioritize your safety and ensure an equitable experience for both Senders and Receivers.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "### 🚨 Security Advisory\n"
                "• **Never pay directly to the seller.** Only send funds to the address provided by this bot.\n"
                "• Our middleman service is **completely free**. If someone asks for a 'service fee', report it.\n"
                "• Always confirm you have received the goods before releasing funds.\n\n"
                "### 📝 Deal Context\n"
                "• **Sender:** <@" + str(buyer_id) + ">\n"
                "• **Receiver:** <@" + str(seller_id) + ">\n"
                f"• **Deal ID:** `{deal_id}`\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━"
            ),
            color=0x0000ff
        )
        
        embed.set_author(name="RainyDay MM Escrow Services", icon_url=logo_url)
        embed.set_thumbnail(url=logo_url)
        
        embed.add_field(
            name="⚠️ Important Note",
            value=(
                "• Make sure funds will not be released until the goods are fully delivered.\n"
                "• Always retain the Deal ID to safeguard against potential risks.\n"
                "• If you encounter any issues, promptly notify us for immediate assistance."
            ),
            inline=False
        )
        
        embed.set_footer(text="RainyDay MM | Secure Trading Enforced", icon_url=logo_url)

        try: await new_channel.send(content=f"<@{buyer_id}> <@{seller_id}>", embed=embed)
        except: await new_channel.send(embed=embed)

        # 3. Simulate User Confirmation
        confirm_embed = discord.Embed(title="User Confirmation", color=0x00ff00)
        confirm_embed.add_field(name="Sender", value=f"<@{buyer_id}>", inline=True)
        confirm_embed.add_field(name="Receiver", value=f"<@{seller_id}>", inline=True)
        confirm_embed.add_field(name="Status", value="✅ Confirmed by both", inline=False)
        await new_channel.send(embed=confirm_embed)

        # 4. Product Details (RESTORED)
        prod_embed = discord.Embed(title="Product Details", color=0x0000ff)
        
        # Safe get with fallbacks
        p_name = deal_info.get("product_name", "N/A - Legacy Deal")
        p_tos = deal_info.get("product_tos", "N/A - Legacy Deal")

        prod_embed.add_field(name="Product", value=f"```\n{p_name}\n```", inline=False)
        prod_embed.add_field(name="ToS and Warranty", value=f"```\n{p_tos}\n```", inline=False)
        await new_channel.send(embed=prod_embed)

        # =====================================================
        # RESTORE ACTIVE STATE (FULL PAYMENT PANEL)
        # =====================================================
        status = deal_info.get('status', 'started')
        
        if status == 'awaiting_withdrawal':
            em = discord.Embed(title="Restored Session", description="Please continue withdrawal.", color=0x00ff00)
            await new_channel.send(embed=em, view=WithdrawalView(deal_id))
            
        elif status == 'started':
            # Check if we have an address already
            existing_address = deal_info.get('address')
            crypto_amount = deal_info.get('ltc_amount', 0)
            currency = deal_info.get('currency', 'ltc')
            usd_amount = deal_info.get('amount', 0)
            
            # Check if deal is older than 1 hour AND has an address
            deal_start = deal_info.get('payment_start_time', deal_info.get('start_time', 0))
            current_time = time.time()
            deal_age_seconds = current_time - deal_start
            
            # If deal is older than 1 hour, check if address was paid
            need_new_address = False
            if existing_address and deal_age_seconds > 3600:
                # Check if the old address has any balance
                try:
                    if currency == 'ltc':
                        balance = await get_ltc_confirmed_balance(existing_address)
                    elif currency == 'usdt_bep20':
                        balance = await get_usdt_balance_parallel(USDT_BEP20_CONTRACT, existing_address, BEP20_RPC_URLS, USDT_BEP20_DECIMALS)
                    elif currency == 'usdt_polygon':
                        balance = await get_usdt_balance_parallel(USDT_POLYGON_CONTRACT, existing_address, POLYGON_RPC_URLS, USDT_POLYGON_DECIMALS)
                    elif currency == 'solana':
                        balance = await get_solana_balance_parallel(existing_address)
                    elif currency == 'ethereum':
                        balance = await get_eth_balance_parallel(existing_address)
                    else:
                        balance = 0
                        
                    if balance == 0:
                        need_new_address = True
                        await new_channel.send(embed=discord.Embed(
                            title="⚠️ Address Expired",
                            description="Original address was unpaid for over 1 hour. Generating new address...",
                            color=0xffa500
                        ))
                except Exception as e:
                    print(f"[Recovery] Balance check error: {e}")
                    need_new_address = True
            
            # Generate new address if needed
            if need_new_address or not existing_address:
                if crypto_amount > 0:
                    wallet = await generate_wallet_for_currency(deal_id, currency)
                    existing_address = wallet['address']
                    
                    # Update deal with new address
                    deal_info['address'] = existing_address
                    deal_info['private_key'] = wallet['private_key']
                    deal_info['payment_start_time'] = time.time()
                    
                    data = load_all_data()
                    data[deal_id] = deal_info
                    save_all_data(data)
                else:
                    # No amount set, show currency selection
                    await new_channel.send(embed=discord.Embed(title="Restored Session", description="Please select currency."), view=CurrencySelectView())
                    return
            
            # Display payment panel like the original
            currency_display = {
                'ltc': 'Litecoin',
                'usdt_bep20': 'USDT (BEP20)',
                'usdt_polygon': 'USDT (Polygon)',
                'solana': 'Solana',
                'ethereum': 'Ethereum'
            }.get(currency, 'Crypto')

            # Confirmation messages
            await new_channel.send(f"<@{seller_id}> (Seller) has confirmed.")
            await new_channel.send(f"<@{buyer_id}> (Buyer) has confirmed.")

            # Amount confirmation
            confirm_amt = discord.Embed(
                title="Confirm Amount",
                description=f"Are you certain that we are expected to receive `{usd_amount}$` in **{currency_display.upper()}**?",
                color=0x0000ff
            )
            confirm_amt.set_thumbnail(url="https://cdn.discordapp.com/attachments/1438896774243942432/1446517323069521992/discotools-xyz-icon_1.png")
            await new_channel.send(embed=confirm_amt)

            # Payment panel
            embed = discord.Embed(
                title="RainyDay MM",
                description=(
                    f"- <@{buyer_id}> Please proceed by transferring the agreed-upon funds\n"
                    f"- COPY & PASTE the EXACT AMOUNT to avoid errors.\n\n"
                ),
                color=0x0000ff
            )
            embed.add_field(name=f"{currency_display} Address", value=f"```\n{existing_address}\n```", inline=False)
            embed.add_field(name=f"{currency_display} Amount", value=f"`{crypto_amount:.8f}`", inline=True)
            embed.add_field(name="USD Amount", value=f"`{usd_amount}$`", inline=True)
            embed.set_footer(text="➤ RainyDay MM | Transaction Confirmed")

            await new_channel.send(content=f"<@{buyer_id}>", embed=embed, view=AddyButtons())

            # Timer note
            await new_channel.send("# Note - If you don't send the amount within 20 minutes, the deal will be cancelled.")

            # Waiting embed
            em = discord.Embed()
            em.set_author(name="Waiting for transaction...")
            msg = await new_channel.send(embed=em)

            # Start payment monitoring
            bot.loop.create_task(
                check_payment_multicurrency(existing_address, new_channel, crypto_amount, deal_info, msg)
            )
        
        else:
            await new_channel.send(f"Session restored. Status: {status}")
            
    except Exception as e:
        await interaction.followup.send(f"Recovery failed: {e}", ephemeral=True)



class StartDealView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        # Using the existing CurrencySelectMenu for the dropdown
        self.add_item(CurrencySelectMenu())


@bot.command(name="panel")
async def send_panel(ctx):
    if ctx.author.id not in OWNER_IDS:
        return
        
    try:
        await ctx.message.delete()
    except:
        pass
    
    logo_url = "https://cdn.discordapp.com/attachments/1383487913186169032/1384932699717898300/Untitled-2.png"
    
    embed = discord.Embed(
        description=(
            "<a:Rain_swag:1457340866367717509> **__Welcome to RainyDay MiddleMan!__** <a:Rain_swag:1457340866367717509>\n\n"
            "**We provide a secure and automated escrow service for your transactions. Our bot holds the funds until both parties confirm the deal is complete.**\n\n"
            "<:rainy_sparkle:1454004790681010318>  **__Features:__**\n"
            "<a:dot:1457342042375065620>  ** Fully automated escrow system**\n"
            "<a:dot:1457342042375065620>  **Multiple cryptocurrency support**\n"
            "<a:dot:1457342042375065620>  **Secure wallet generation**\n"
            "<a:dot:1457342042375065620>  **Instant payment detection**\n"
            "<a:dot:1457342042375065620>  **Transaction transparency**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<:Rainy_alert:1454152261214404856>  **How it works:\n"
            "<a:dot:1457342042375065620>  Select Asset — Pick a crypto from the menu below.\n"
            "<a:dot:1457342042375065620>  Setup Deal — Enter Partner ID to open workspace.\n"
            "<a:dot:1457342042375065620>  Fund Escrow — Buyer sends funds to the address.\n"
            "<a:dot:1457342042375065620>  Delivery — Seller delivers assets or services.\n"
            "<a:dot:1457342042375065620>  Release — Funds are released once completed.**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "**__Make sure to check out these:__**\n\n"
            "<a:rain_sparkle:1457341149621649542> **Tos : ⁠https://discord.com/channels/1370345367983493120/1370727225673908405\n"
            "<a:rain_sparkle:1457341149621649542> Guidelines : ⁠https://discord.com/channels/1370345367983493120/1454729394185572383\n"
            "<a:rain_sparkle:1457341149621649542>  AutoMM tos : https://discord.com/channels/1370345367983493120/1454729169295376485**\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "<a:rain_alert:1457341607060705290>   **Ready to Start?**\n"
            "<:rain_heart:1457340964908830903>   **Select an asset from the dropdown below to begin**"
        ),
        color=0x0000ff
    )
    
    # Premium Placement: Thumbnail and Footer
    embed.set_thumbnail(url=logo_url)
    embed.set_footer(text="RainyDay MM | Safe & Secure Trading", icon_url=logo_url)
    
    await ctx.send(embed=embed, view=StartDealView())

@tasks.loop(minutes=10)
async def vc_stats_loop():
    """Update multiple stats voice channels"""
    try:
        # Load stats channel IDs
        stats_channels = load_stats_channels()
        if not stats_channels:
            return
            
        data = load_all_data()
        user_stats = load_user_stats()
        
        # Calculate stats
        # Total volume is sum of all user volumes / 2 (since both buyer and seller get credit)
        raw_volume = sum(u.get('volume', 0.0) for u in user_stats.values())
        total_volume = raw_volume / 2
        total_deals = sum(u.get('deals', 0) for u in user_stats.values())
        active_deals = len([d for d in data.values() if d.get('status') in ['started', 'awaiting_withdrawal']])
        total_users = len(user_stats)
        
        # Update each channel
        updates = [
            ('volume_channel', f"💰 Volume: ${total_volume:,.2f}"),
            ('deals_channel', f"📊 Total Deals: {total_deals}"),
            ('active_channel', f"⚡ Active: {active_deals}"),
            ('users_channel', f"👥 Users: {total_users}")
        ]
        
        for key, new_name in updates:
            channel_id = stats_channels.get(key)
            if channel_id:
                try:
                    channel = bot.get_channel(int(channel_id))
                    if channel:
                        await channel.edit(name=new_name)
                except Exception as e:
                    print(f"Failed to update {key}: {e}")
                    
    except Exception as e:
        print(f"VC Stats Loop Error: {e}")

@tasks.loop(seconds=60)
async def check_idle_deals():
    """Unified auto-close logic: 1h inactivity reset on msg/invoice, 100s close on finalize."""
    try:
        data = load_all_data()
        current_time = time.time()
        
        for deal_id, deal in list(data.items()):
            # 1. SKIP if funds are detected/paid (Never auto-close funded deals)
            if deal.get('paid') or deal.get('status') in ['escrowed', 'awaiting_withdrawal', 'awaiting_confirmation']:
                continue

            channel_id = deal.get("channel_id")
            if not channel_id:
                continue
                
            channel = bot.get_channel(int(channel_id))
            if not channel:
                # Channel deleted manually? Clean up data.
                del data[deal_id]
                save_all_data(data)
                continue

            last_act = deal.get("last_activity", deal.get("start_time", current_time))
            elapsed = current_time - last_act
            status = deal.get("status")

            # 2. FINALIZED CLOSE (100 seconds)
            if status in ['released', 'refunded', 'cancelled']:
                if elapsed > 100:
                    try:
                        print(f"[AutoClose] Closing finalized deal {deal_id} (status: {status})")
                        await sweep_dust_fees(deal_id, deal)
                        await channel.delete()
                        del data[deal_id]
                        save_all_data(data)
                    except Exception as e:
                        print(f"[AutoClose] Error closing finalized {deal_id}: {e}")
                continue

            # 3. INACTIVITY CLOSE (1 hour = 3600 seconds)
            # Skip if payment detection is active? User said "if no activity in 1 hour then it will autoclose"
            # "after payment is detected it will never autoclose" -> we already skipped 'paid'/'escrowed' etc.
            
            if elapsed > 3600:
                try:
                    print(f"[AutoClose] Closing idle deal {deal_id} (1h timeout)")
                    embed = discord.Embed(
                        title="❌ Ticket Closed",
                        description="Ticket closed due to inactivity (1 hour timeout).",
                        color=discord.Color.red()
                    )
                    await channel.send(embed=embed)
                    await asyncio.sleep(2)
                    await sweep_dust_fees(deal_id, deal)
                    await channel.delete()
                    del data[deal_id]
                    save_all_data(data)
                except Exception as e:
                    print(f"[AutoClose] Error closing idle {deal_id}: {e}")
            
            # Warning at 50 minutes (3000 seconds)
            elif elapsed > 3000 and not deal.get("idle_warning_sent"):
                try:
                    embed = discord.Embed(
                        title="⏳ Inactivity Warning",
                        description=(
                            "No activity detected in 50 minutes.\n"
                            "**This ticket will close automatically in 10 minutes.**"
                        ),
                        color=discord.Color.orange()
                    )
                    await channel.send(embed=embed)
                    deal["idle_warning_sent"] = True
                    save_all_data(data)
                except:
                    pass

    except Exception as e:
        print(f"Unified Idle Check Error: {e}")

def load_stats_channels():
    """Load stats channel IDs from JSON"""
    try:
        with open('stats_channels.json', 'r') as f:
            return json.load(f)
    except:
        return {}

def save_stats_channels(data):
    """Save stats channel IDs to JSON"""
    with open('stats_channels.json', 'w') as f:
        json.dump(data, f, indent=2)

@bot.tree.command(name="create_stats_channels", description="Create stats voice channels (Owner Only)")
async def create_stats_channels_cmd(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    if interaction.user.id not in OWNER_IDS:
        return await interaction.followup.send("Not authorized.", ephemeral=True)
    
    guild = interaction.guild
    if not guild:
        return await interaction.followup.send("Must be used in a server.", ephemeral=True)
    
    try:
        # Create a category for stats
        category = await guild.create_category("📊 AutoMM Stats")
        
        # Create 4 voice channels
        # Set permissions so no one can join
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(connect=False),
            guild.me: discord.PermissionOverwrite(connect=True, manage_channels=True)
        }
        
        vol_ch = await guild.create_voice_channel("💰 Volume: $0.00", category=category, overwrites=overwrites)
        deals_ch = await guild.create_voice_channel("📊 Total Deals: 0", category=category, overwrites=overwrites)
        active_ch = await guild.create_voice_channel("⚡ Active: 0", category=category, overwrites=overwrites)
        users_ch = await guild.create_voice_channel("👥 Users: 0", category=category, overwrites=overwrites)
        
        # Save channel IDs
        stats_data = {
            'volume_channel': str(vol_ch.id),
            'deals_channel': str(deals_ch.id),
            'active_channel': str(active_ch.id),
            'users_channel': str(users_ch.id),
            'category_id': str(category.id)
        }
        save_stats_channels(stats_data)
        
        await interaction.followup.send(
            f"✅ **Stats Channels Created!**\n\n"
            f"Category: {category.mention}\n"
            f"• {vol_ch.mention}\n"
            f"• {deals_ch.mention}\n"
            f"• {active_ch.mention}\n"
            f"• {users_ch.mention}\n\n"
            f"Stats will update every 10 minutes.",
            ephemeral=True
        )
        
    except Exception as e:
        await interaction.followup.send(f"Error creating channels: {e}", ephemeral=True)


@bot.tree.command(name="find_deal_id", description="Find deal ID by address or channel ID")

@app_commands.describe(

    address="Address to search for (optional)",

    channel_id="Channel ID to search for (optional)"

)

async def find_deal_id_cmd(

    interaction: discord.Interaction, 

    address: str = None, 

    channel_id: str = None

):

    await interaction.response.defer(ephemeral=True)



    if interaction.user.id not in OWNER_IDS:

        await interaction.followup.send("You are not authorized to use this command.", ephemeral=True)

        return



    if not address and not channel_id:

        await interaction.followup.send("Please provide either address or channel ID.", ephemeral=True)

        return



    data = load_all_data()

    found_deals = []



    if address:

        for deal_id, deal in data.items():

            if deal.get("address") == address:

                found_deals.append((deal_id, deal))

    

    if channel_id:

        for deal_id, deal in data.items():

            if str(deal.get("channel_id")) == str(channel_id):

                found_deals.append((deal_id, deal))



    if not found_deals:

        await interaction.followup.send("No deals found matching the criteria.", ephemeral=True)

        return



    embed = discord.Embed(

        title="Found Deals",

        color=0x0000ff

    )



    for deal_id, deal in found_deals:

        channel_info = f"Channel: `{deal.get('channel_id', 'Unknown')}`"

        seller_info = f"Seller: `{deal.get('seller', 'Unknown')}`"

        buyer_info = f"Buyer: `{deal.get('buyer', 'Unknown')}`"

        address_info = f"Address: `{deal.get('address', 'Unknown')}`"

        currency_info = f"Currency: `{deal.get('currency', 'ltc')}`"

        

        embed.add_field(

            name=f"Deal ID: `{deal_id}`",

            value=f"{channel_info}\n{seller_info}\n{buyer_info}\n{address_info}\n{currency_info}",

            inline=False

        )



    await interaction.followup.send(embed=embed, ephemeral=True)



@bot.tree.command(name="refresh_deal", description="Refresh deal UI if stuck (Admin/User)")
async def refresh_deal(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    channel = interaction.channel
    
    deal_id, deal = get_deal_by_channel(channel.id)
    if not deal:
        return await interaction.followup.send("No deal found in this channel.", ephemeral=True)
    
    # Update activity to prevent deletion
    data = load_all_data()
    if deal_id in data:
        data[deal_id]['last_activity'] = time.time()
        save_all_data(data)
        
    status = deal.get("status")
    paid = deal.get("paid")
    
    # CASE 1: Deal is PAID/ESCROWED but UI might be stuck
    if status == 'escrowed' or paid:
        # Cleanup old "Verifying" or existing "Confirmed" embeds to prevent duplicates
        try:
            async for old_msg in channel.history(limit=20):
                if old_msg.author.id == bot.user.id and old_msg.embeds:
                    emp = old_msg.embeds[0]
                    if any(t in str(emp.title) for t in ["Verifying Transaction", "Payment Detected", "Deal Confirmed"]):
                         try: await old_msg.delete()
                         except: pass
        except: pass

        # Re-send Success Embed
        currency = deal.get("currency", "ltc")
        txid = deal.get("txid", "N/A")
        amount = deal.get("amount", 0.0)
        
        # Calculate USD value again for display
        usd_val = 0.0
        try:
            # Try to get price, handling rate limits and fallbacks
            price_resp = await get_cached_price(currency)
            
            if price_resp == "RATE_LIMIT":
                # Fallback for stablecoins if rate limited
                if any(x in currency.lower() for x in ['usdt', 'usdc', 'dai']):
                    price = 1.0
                else:
                    price = 0.0
            else:
                price = float(price_resp)

            # If price is still 0 (API failed) and it's a stablecoin, force 1.0
            if price <= 0 and any(x in currency.lower() for x in ['usdt', 'usdc', 'dai']):
                price = 1.0
                
            usd_val = float(amount) * price
        except Exception as e:
            print(f"Price calc error: {e}")
            # Final safety fallback for stablecoins
            if any(x in currency.lower() for x in ['usdt', 'usdc']):
                 usd_val = float(amount)
            
        final_embed = discord.Embed(
            title="Deal Confirmed ✅",
            description=">>> **Funds Secured & Verified**\nThe funds are now safely locked in escrow on the blockchain. The Seller should now deliver the goods/service to the Buyer.\n\n**Next Steps:**\n1. **Seller:** Deliver the item/service to the Buyer.\n2. **Buyer:** Verify the item, then click **Release** below.",
            color=0x00ff00
        )
        final_embed.set_author(name="Transaction Verified", icon_url=VERIFIED_ICON_URL)
        
        c_info = get_currency_info(currency)
        c_tag = currency.upper().replace("_", " ")
        final_embed.add_field(name="Amount", value=f"`{amount}` {c_tag} (`${usd_val:.2f}` USD)", inline=False)
        
        if c_info['icon']:
            final_embed.set_thumbnail(url=c_info['icon'])
            
        final_embed.set_footer(text="⚠️ WARNING: Do NOT release funds until you have received and verified the item.")

        v_final = ReleaseButton(txid=txid, currency=currency)
        
        buyer_id = deal.get("buyer") # Receiver
        seller_id = deal.get("seller") # Sender

        # Generate Handshake Banner
        file_attachment = None
        try:
            buyer_user = await bot.fetch_user(int(buyer_id))
            seller_user = await bot.fetch_user(int(seller_id))
            
            buyer_pfp = await buyer_user.display_avatar.read()
            seller_pfp = await seller_user.display_avatar.read()
            
            banner_bytes = await generate_handshake_image(buyer_pfp, seller_pfp)
            file_attachment = discord.File(banner_bytes, filename="secure_deal.png")
            final_embed.set_image(url="attachment://secure_deal.png")
        except Exception as e:
            print(f"Banner generation failed: {e}")

        
        await channel.send(
            content=f"<@{buyer_id}> <@{seller_id}>",
            embed=final_embed,
            file=file_attachment,
            view=v_final
        )
        await interaction.followup.send("✅ Deal UI refreshed successfully.", ephemeral=True)
        return

    await interaction.followup.send(f"Deal status is '{status}'. No automatic refresh needed.", ephemeral=True)


@bot.tree.command(name="change_channel_id", description="Change channel ID for a deal")

@app_commands.describe(

    deal_id="The deal ID to update",

    new_channel_id="The new channel ID"

)

async def change_channel_id_cmd(interaction: discord.Interaction, deal_id: str, new_channel_id: str):

    await interaction.response.defer(ephemeral=True)



    if interaction.user.id not in OWNER_IDS:

        await interaction.followup.send("You are not authorized to use this command.", ephemeral=True)

        return



    data = load_all_data()

    if deal_id not in data:

        await interaction.followup.send("Deal not found.", ephemeral=True)

        return



    old_channel_id = data[deal_id].get("channel_id")

    data[deal_id]["channel_id"] = new_channel_id

    save_all_data(data)



    embed = discord.Embed(

        title="Channel ID Updated",

        description=f"Deal `{deal_id}` channel ID updated from `{old_channel_id}` to `{new_channel_id}`",

        color=0x00ff00

    )



    await interaction.followup.send(embed=embed, ephemeral=True)



@bot.tree.command(name="get_deal_info", description="Get full information about a deal")

@app_commands.describe(deal_id="The deal ID to get information for")

async def get_deal_info_cmd(interaction: discord.Interaction, deal_id: str):

    await interaction.response.defer(ephemeral=True)



    if interaction.user.id not in OWNER_IDS:

        await interaction.followup.send("You are not authorized to use this command.", ephemeral=True)

        return



    deal = get_deal_by_dealid(deal_id)

    if not deal:

        await interaction.followup.send("Deal not found.", ephemeral=True)

        return



    embed = discord.Embed(

        title=f"Deal Information - {deal_id}",

        color=0x0000ff

    )



    for key, value in deal.items():

        if key == "private_key":

            if value and len(value) > 20:

                display_value = f"{value[:10]}...{value[-10:]}"

            else:

                display_value = "***"

        else:

            display_value = str(value) if value else "None"

        

        embed.add_field(name=key, value=f"`{display_value}`", inline=False)



    await interaction.followup.send(embed=embed, ephemeral=True)



@bot.tree.command(name="close", description="Close the ticket and save transcript.")

async def close_command(interaction: discord.Interaction):

    try:
        await interaction.response.defer(ephemeral=True)

        # --- EXECUTIVE ROLE CHECK ---
        # Allow Access if: User is OWNER OR User has Executive Role
        has_role = False
        if hasattr(interaction.user, "roles"):
            if EXECUTIVE_ROLE_ID in [role.id for role in interaction.user.roles]:
                has_role = True
        
        if interaction.user.id in OWNER_IDS:
            has_role = True
            
        if not has_role:
            await interaction.followup.send("You are not authorized to use this command.", ephemeral=True)
            return

    except Exception as e:
        print(f"Error initializing close command: {e}")
        # Try to recover if defer failed
        try:
             await interaction.response.send_message("An error occurred starting the close command.", ephemeral=True)
        except:
             pass
        return


    # -----------------------------



    try:

        deal_id, deal = get_deal_by_channel(interaction.channel.id)



        if deal is None:

            await interaction.followup.send("No deal data found for this channel.", ephemeral=True)

            return



        seller_id = None

        buyer_id = None



        if isinstance(deal, dict):

            if deal.get("seller") not in ("None", None, ""):

                try:

                    seller_id = int(deal["seller"])

                except:

                    seller_id = None



            if deal.get("buyer") not in ("None", None, ""):

                try:

                    buyer_id = int(deal["buyer"])

                except:

                    buyer_id = None

        else:

            await interaction.followup.send("Deal data format error.", ephemeral=True)

            return



        # Save transcript

        if seller_id or buyer_id:

            try:

                await send_transcript(interaction.channel, seller_id or 0, buyer_id or 0)

            except Exception as e:

                print("Transcript error:", e)

                await interaction.followup.send("Transcript could not be created, but the ticket will still close.", ephemeral=True)

        else:

            await interaction.followup.send("No valid participants found. Closing ticket without transcript.", ephemeral=True)



        # DELETE CHANNEL (This was missing)

        try:
            # Sweep Dust
            await sweep_dust_fees(deal_id, deal)

            await interaction.channel.delete(reason="Ticket closed by executive.")

        except Exception as e:

            print("Channel delete error:", e)



    except Exception as e:

        print("Close command error:", e)

        await interaction.followup.send("An error occurred while closing the ticket.", ephemeral=True)

# ========== CONFIRMATION BUTTONS ==========

class CloseAllConfirm(discord.ui.View):

    def __init__(self, interaction):

        super().__init__(timeout=60)

        self.interaction = interaction



    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)

    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):



        # Only original user can confirm

        if interaction.user.id != self.interaction.user.id:

            return await interaction.response.send_message("This confirmation is not for you.", ephemeral=True)



        await interaction.response.defer(ephemeral=True)

        await interaction.followup.send("Closing all deal channels… please wait.", ephemeral=True)



        # Load data.json for seller/buyer

        try:

            with open("data.json", "r") as f:

                all_deals = json.load(f)

        except:

            all_deals = {}



        deleted = 0



        # Loop through both categories

        for cat_id in [CATEGORY_ID_1, CATEGORY_ID_2]:



            category = interaction.guild.get_channel(cat_id)

            if not category:

                continue



            for channel in category.channels:

                ch_id = str(channel.id)



                # Use real seller/buyer if exists in data.json

                if ch_id in all_deals:

                    deal = all_deals[ch_id]

                    seller_id = int(deal.get("seller", 0) or 0)

                    buyer_id = int(deal.get("buyer", 0) or 0)

                else:

                    # Not in data.json → transcript only, no logs or seller/buyer

                    seller_id = 0

                    buyer_id = 0



                # Save transcript no matter what

                try:

                    await send_transcript(channel, seller_id, buyer_id)

                except Exception as e:

                    print(f"[Transcript Error] {channel.id} → {e}")



                # Delete channel

                try:

                    await channel.delete(reason="Close-All executed by owner.")

                    deleted += 1

                except Exception as e:

                    print(f"[Delete Error] {channel.id} → {e}")



        await self.interaction.followup.send(

            f"✅ **Close-All Completed**\nAll deal channels deleted.\nTotal deleted: **{deleted}**",

            ephemeral=True

        )



        self.stop()



    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)

    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):



        if interaction.user.id != self.interaction.user.id:

            return await interaction.response.send_message("This is not for you.", ephemeral=True)



        await interaction.response.send_message("❌ Close-all cancelled.", ephemeral=True)

        self.stop()







@bot.command(name="sync")
async def sync_tree(ctx):
    if ctx.author.id not in OWNER_IDS:
        return

    # WIPE guild-specific commands (Removes duplicates)
    if ctx.guild:
        print(f"Clearing guild commands for {ctx.guild.id}...")
        bot.tree.clear_commands(guild=ctx.guild)
        await bot.tree.sync(guild=ctx.guild)
    
    # Sync Global (Ensures only 1 global copy survives)
    print("Syncing globally...")
    await bot.tree.sync()
    
    await ctx.send("✅ Duplicates removed! Global commands synced. (You may need to restart Discord to see changes)")


# ========== MAIN /close_all COMMAND ==========

@bot.tree.command(name="close_all", description="Owner-only: Delete ALL deal channels and save transcripts.")

async def close_all(interaction: discord.Interaction):



    await interaction.response.defer(ephemeral=True)



    # OWNER CHECK

    if interaction.user.id not in OWNER_IDS:

        return await interaction.followup.send("You are not authorized to use this command.", ephemeral=True)



    embed = discord.Embed(

        title="⚠ Confirm Close All",

        description=(

            f"This will **delete every channel** inside:\n"

            f"- <#{CATEGORY_ID_1}>\n"

            f"- <#{CATEGORY_ID_2}>\n\n"

            f"✔ Transcript will be saved for ALL channels\n"

            f"✔ If channel is in `data.json` → real seller/buyer will be used\n"

            f"✔ If not → seller/buyer will be set to 0\n"

            f"✖ No logs will be sent for missing data\n\n"

            f"Are you sure you want to continue?"

        ),

        color=0x0000ff

    )

    embed.set_footer(text="RainyDay MM")



    await interaction.followup.send(

        embed=embed,

        view=CloseAllConfirm(interaction),

        ephemeral=True

    )



# ========== ADMIN RESCAN COMMAND ==========

@bot.tree.command(name="admin_rescan", description="Force restart payment monitoring for a deal (Owner Only)")
@app_commands.describe(deal_id="The deal ID to rescan")
async def admin_rescan(interaction: discord.Interaction, deal_id: str):
    await interaction.response.defer(ephemeral=True)
    
    if interaction.user.id not in OWNER_IDS:
        await interaction.followup.send("You are not authorized.", ephemeral=True)
        return
    
    deal = get_deal_by_dealid(deal_id)
    if not deal:
        await interaction.followup.send("Deal not found.", ephemeral=True)
        return
    
    # Get channel
    channel_id = deal.get('channel_id')
    if not channel_id:
        await interaction.followup.send("Deal has no channel.", ephemeral=True)
        return
    
    channel = bot.get_channel(int(channel_id))
    if not channel:
        await interaction.followup.send("Channel not found.", ephemeral=True)
        return
    
    # Check if deal has address and amount
    address = deal.get('address')
    crypto_amount = deal.get('ltc_amount', 0)
    currency = deal.get('currency', 'ltc')
    
    if not address:
        await interaction.followup.send("Deal has no payment address yet.", ephemeral=True)
        return
    
    if crypto_amount <= 0:
        await interaction.followup.send("Deal has no expected amount.", ephemeral=True)
        return
    
    # Start payment monitoring task silently
    bot.loop.create_task(check_payment_multicurrency(address, channel, crypto_amount, deal, None))
    
    await interaction.followup.send(f"✅ Payment monitoring restarted for deal `{deal_id}`", ephemeral=True)


@bot.tree.command(name="restart", description="Restart the bot (Owner Only)")
async def restart_bot(interaction: discord.Interaction):
    if interaction.user.id not in OWNER_IDS:
        await interaction.response.send_message("You are not authorized.", ephemeral=True)
        return
    
    await interaction.response.send_message("🔄 Restarting bot...", ephemeral=True)
    print(f"[RESTART] Restart initiated by {interaction.user}")
    import sys
    sys.exit(0)


@bot.tree.command(name="sync_history", description="Sync old history messages to the new design (Owner Only)")
@app_commands.describe(limit="Number of messages to check (default 100)")
async def sync_history(interaction: discord.Interaction, limit: int = 100):
    if interaction.user.id not in OWNER_IDS:
        await interaction.response.send_message("You are not authorized.", ephemeral=True)
        return

    from config import HISTORY_CHANNEL
    channel = bot.get_channel(HISTORY_CHANNEL)
    if not channel:
        await interaction.response.send_message("History channel not found.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    
    updated_count = 0
    async for message in channel.history(limit=limit):
        if message.author.id != bot.user.id or not message.embeds:
            continue
            
        embed = message.embeds[0]
        if not embed.title or "Deal Complete" not in str(embed.title):
            continue
            
        # Extract data from existing embed
        title = embed.title
        full_name = title.replace(" Deal Complete", "")
        
        # Get currency key from full name
        curr_map = {
            'Litecoin': 'ltc', 'Tether (BSC)': 'usdt_bep20', 'Tether (Polygon)': 'usdt_polygon',
            'Solana': 'solana', 'Ethereum': 'ethereum'
        }
        raw_curr = 'ltc'
        for name, key in curr_map.items():
            if name in full_name:
                raw_curr = key
                break
        
        c_info = get_currency_info(raw_curr)
        c_tag = raw_curr.upper().replace("_", " ") if "_" in raw_curr else raw_curr.upper()
        
        new_embed = discord.Embed(title=title, color=0x00ff00)
        if c_info['icon']:
            new_embed.set_thumbnail(url=c_info['icon'])
            
        # Parse Fields
        for field in embed.fields:
            if field.name == "Amount":
                val = field.value.replace("`", "") 
                import re
                match = re.search(r"([\d\.]+) (\S+) \(\$([\d\.]+) USD\)", val)
                if match:
                    crypto_amt, tag, usd_amt = match.groups()
                    new_val = f"`{crypto_amt}` {tag} (`${usd_amt}` USD)"
                    new_embed.add_field(name="Amount", value=new_val, inline=False)
                else:
                    new_embed.add_field(name="Amount", value=field.value, inline=False)
                    
            elif field.name in ["Sender", "Receiver"]:
                new_embed.add_field(name=field.name, value="`Anonymous`", inline=True)
                
            elif field.name == "Transaction":
                val = field.value
                import re
                match = re.search(r"(\S+) \(\[View Transaction\]\((https?://\S+)\)\)", val)
                if match:
                    tx_hash, url = match.groups()
                    tx_hash = tx_hash.replace("`", "")
                    new_val = f"`{tx_hash}` ([View Transaction]({url}))"
                    new_embed.add_field(name="Transaction", value=new_val, inline=False)
                elif "(" not in val:
                    tx_hash = val.replace("`", "")
                    new_embed.add_field(name="Transaction", value=f"`{tx_hash}`", inline=False)
                else:
                    new_embed.add_field(name="Transaction", value=field.value, inline=False)
        
        # Update View (Buttons)
        new_view = discord.ui.View()
        if message.components:
            for row in message.components:
                for comp in row.children:
                    if hasattr(comp, 'url') and comp.url:
                        label = comp.label
                        if label and "BlockChair" in label: label = "View on Blockcypher"
                        new_view.add_item(discord.ui.Button(label=label, url=comp.url))
        
        try:
            await message.edit(embed=new_embed, view=new_view)
            updated_count += 1
        except Exception as e:
            print(f"[SYNC] Failed to edit message {message.id}: {e}")

    await interaction.followup.send(f"Successfully updated {updated_count} history messages.", ephemeral=True)


@bot.command(name="syncglobal")
async def sync_global(ctx):
    if ctx.author.id not in OWNER_IDS:
        return
    try:
        synced = await bot.tree.sync()
        await ctx.send(f"Synced {len(synced)} commands globally.")
    except Exception as e:
        await ctx.send(f"Failed to sync: {e}")

@bot.tree.command(name="sync", description="Sync deal channels with database state (Owner Only)")
async def sync(interaction: discord.Interaction):
    if interaction.user.id not in OWNER_IDS:
        await interaction.response.send_message("You are not authorized.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    
    data = load_all_data()
    synced_count = 0
    errors = 0
    
    for deal_id, deal in data.items():
        channel_id = deal.get('channel_id')
        if not channel_id:
            continue
            
        channel = bot.get_channel(int(channel_id))
        if not channel:
            continue
            
        status = deal.get('status', '')
        
        # 1. SKIP logic
        if status == 'cancelled':
             continue
        
        # 2. STATUS-BASED RESTORATION
        try:
            # --- ESCROWED / PAID ---
            if status == 'escrowed' or deal.get('paid'):
                
                has_correct_ui = False
                async for msg in channel.history(limit=10):
                    if msg.author.id == bot.user.id and msg.embeds:
                        emp = msg.embeds[0]
                        if "Deal Confirmed ✅" in str(emp.title):
                            has_correct_ui = True
                            break
                
                if not has_correct_ui:
                    async for msg in channel.history(limit=15):
                        if msg.author.id == bot.user.id and msg.embeds:
                            emp = msg.embeds[0]
                            if any(t in str(emp.title) for t in ["Interaction Restored", "Deal Confirmed ✅"]):
                                try: await msg.delete()
                                except: pass

                    currency = deal.get('currency', 'ltc')
                    c_info = get_currency_info(currency)
                    c_tag = currency.upper().replace("_", " ")
                    received_amount = deal.get('ltc_amount', 0)
                    usd_val = deal.get('amount', 0)
                    
                    final_embed = discord.Embed(
                        title="Deal Confirmed ✅",
                        description=">>> The funds are now secured in escrow and verified on-chain.",
                        color=0x00ff00
                    )
                    final_embed.set_author(name="Transaction Verified", icon_url=VERIFIED_ICON_URL)
                    final_embed.add_field(name="Amount", value=f"`{received_amount}` {c_tag} (`${usd_val:.2f}` USD)", inline=False)
                    
                    if c_info['icon']:
                        final_embed.set_thumbnail(url=c_info['icon'])
                    else:
                        final_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1438896774243942432/1446517314433454342/discotools-xyz-icon.png")
                    final_embed.set_footer(text="Release the funds item is delivered.")

                    await channel.send(
                        content=f"<@{deal.get('buyer')}> <@{deal.get('seller')}>",
                        embed=final_embed,
                        view=ReleaseButton(txid=deal.get('txid'), currency=currency)
                    )
                    synced_count += 1
            
            # --- PENDING ---
            elif status == 'pending':
                 # Resend Payment Instructions if missing or outdated
                 # 1. Check for existing
                 has_payment_ui = False
                 async for msg in channel.history(limit=10):
                    if msg.author.id == bot.user.id and msg.embeds:
                        emp = msg.embeds[0]
                        if "Payment Required" in str(emp.title) or "Waiting for payment" in str(emp.footer.text):
                            has_payment_ui = True
                            # Optional: Delete it to resend fresh? 
                            # User said "update embeds too", so let's delete old and send fresh.
                            try: await msg.delete()
                            except: pass
                            has_payment_ui = False
                            break
                 
                 if not has_payment_ui:
                     # Resend Payment UI
                     currency = deal.get('currency', 'ltc')
                     c_info = get_currency_info(currency)
                     c_name = c_info['name']
                     expected_amount = deal.get('ltc_amount', 0)
                     if expected_amount == 0: continue # Skip invalid
                     
                     address = deal.get('address')
                     
                     embed = discord.Embed(
                         title="Payment Required",
                         color=0x0000ff,
                         description="Please complete the payments below to continue the deal."
                     )
                     embed.add_field(
                         name=f"{c_name} Payment",
                         value=f"Send **{expected_amount} {c_name}** to:\n`{address}`",
                         inline=False
                     )
                     embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1438896774243942432/1446526617403920537/discotools-xyz-icon_7.png")
                     embed.set_footer(text="Waiting for payment...")
                     
                     await channel.send(embed=embed, view=AddyButtons(address))
                     synced_count += 1

        except Exception as e:
            print(f"[Sync] Error syncing channel {channel.name}: {e}")
            errors += 1
            
    await interaction.followup.send(f"✅ Synced **{synced_count}** active deals. ({errors} errors)", ephemeral=True)


# =====================================================

# BOT EVENTS

# =====================================================



@bot.event

async def on_ready():
    print(f"Logged in as {bot.user}")
    await get_session() # Pre-initialize high-speed session

    # Load Cogs
    initial_extensions = []
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            initial_extensions.append(f'cogs.{filename[:-3]}')
    
    for extension in initial_extensions:
        try:
            await bot.load_extension(extension)
            print(f"Loaded extension: {extension}")
        except Exception as e:
            print(f"Failed to load extension {extension}: {e}")

    # Register Persistent Views
    bot.add_view(ReleaseButton())
    bot.add_view(ReleaseConButton())
    bot.add_view(CancelConButton())
    bot.add_view(WithdrawalView())
    bot.add_view(RefundView())
    print("[Startup] Persistent views registered.")

    synced = await bot.tree.sync()
    print(f"[Startup] Global command tree synced ({len(synced)} commands).")
    
    # Start VC Stats Loop
    if not vc_stats_loop.is_running():
        vc_stats_loop.start()
        
    # Start Idle Check Loop (New)
    if not check_idle_deals.is_running():
        check_idle_deals.start()

    # ========== STARTUP RECOVERY: Resume payment monitoring ==========
    print("[Startup Recovery] Checking for pending payment deals...")
    data = load_all_data()
    print(f"[Startup Recovery] Found {len(data)} total deals in database")
    current_time = time.time()
    recovered_count = 0
    
    for deal_id, deal_info in data.items():
        try:
            # Skip deals without address (not in payment phase)
            address = deal_info.get('address')
            if not address:
                continue
            
            # Skip completed deals (those with completed/cancelled status markers can be added)
            # For now, check if deal has payment_start_time and is within 1 hour
            payment_start = deal_info.get('payment_start_time', deal_info.get('start_time', 0))
            deal_age = current_time - payment_start
            
            # Skip if deal is older than 1 hour (expired)
            if deal_age > 3600:
                continue
            
            # Get expected amount
            # FIX: Priority use expected_crypto_amount which is the original target
            crypto_amount = deal_info.get('expected_crypto_amount', deal_info.get('ltc_amount', 0))
            if crypto_amount <= 0:
                continue
            
            # Get channel
            channel_id = deal_info.get('channel_id')
            if not channel_id:
                continue
            
            # Try to get channel
            channel = None
            for guild in bot.guilds:
                channel = guild.get_channel(int(channel_id))
                if channel:
                    break
            
            if not channel:
                continue
            
            # Resume payment monitoring for this deal (Silent, non-blocking)
            if not hasattr(bot, 'active_monitors'): bot.active_monitors = set()
            if address not in bot.active_monitors:
                print(f"[Startup Recovery] Resuming payment monitoring for deal {deal_id[:16]}...")
                bot.loop.create_task(check_payment_multicurrency(address, channel, crypto_amount, deal_info, None))
                recovered_count += 1
                
        except Exception as e:
            print(f"[Startup Recovery] Error processing deal {deal_id[:16]}: {e}")
            continue
    
    print(f"[Startup Recovery] Resumed monitoring for {recovered_count} deals")

    ist = pytz.timezone('Asia/Kolkata')

@bot.event
async def on_member_join(member):
    """
    Restore access to active deals if a user rejoins.
    """
    guild = member.guild
    data = load_all_data()
    
    restored_count = 0
    seen_channels = set()
    
    for deal_id, info in data.items():
        # Check if user is buyer or seller
        buyer_id = str(info.get('buyer', ''))
        seller_id = str(info.get('seller', ''))
        
        if str(member.id) in [buyer_id, seller_id]:
            channel_id = info.get('channel_id')
            if channel_id and channel_id not in seen_channels:
                channel = guild.get_channel(int(channel_id))
                if channel:
                    try:
                        await channel.set_permissions(member, read_messages=True, send_messages=True)
                        await channel.send(f"Welcome back {member.mention}! Access restored.")
                        restored_count += 1
                        seen_channels.add(channel_id)
                    except Exception as e:
                        print(f"Failed to restore access for {member}: {e}")
                        
    if restored_count > 0:
        print(f"Restored {restored_count} channels for returning member {member}")

    ist = pytz.timezone('Asia/Kolkata')
    time_now = datetime.datetime.now(ist)

    date = time_now.strftime('%d/%m/%y')

    embed = discord.Embed(

        description=(

            "## <:emoji_303:1444562870208823377> RainyDay Auto Middleman\n\n"

            "## What is Auto Middleman?\n"

            "An escrow system used during trades. The buyer sends the funds to the escrow wallet, "

            "the seller delivers the product, and once the buyer confirms, the escrow safely releases the funds.\n\n"

            

            "## Why RainyDay MM?\n"

            "- Fully automated 24/7\n"

            "- Protects both buyer & seller\n"

            "- Fast support & instant updates\n"

            "- Zero service fees (only blockchain fees apply)\n"

            "- Secure, reliable and designed for smooth deals.\n\n"

            

        ),

        color=0x0000ff

    )



    # Footer icon = your logo (thumbnail removed)

    embed.set_footer(

        text=f"Always check https://rainyday.one",

        icon_url="https://cdn.discordapp.com/attachments/1383487913186169032/1384932699717898300/Untitled-2.png"

    )



    #embed = discord.Embed(description="# RainyDay Auto Middleman\n\n**What is Auto Middleman?**\nRainyDay Auto Middleman is an automated, secure escrow system designed to hold cryptocurrency on your behalf. It streamlines transactions, saves time, and ensures safer dealings between buyers and sellers.\n\n**Key Features:**\n- Supports LTC, USDT (BEP20), USDT (Polygon), Solana (SOL), and Ethereum (ETH)\n- Fully automated and available 24/7\n- Fast, efficient, and secure\n- Zero fees", color=0x0000ff)
    #embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1383487913186169032/1384932699717898300/Untitled-2.png?ex=68543a96&is=6852e916&hm=3f5566d93ca1ba539950f47e4ea4fbcf1c4b2e6873af9d97424656d867830d7a&")

    #embed.set_footer(text=f"RainyDay MM | {date}, {time}")

    print("Bot is ready!")

    try:

        channel = bot.get_channel(CHANNEL_ID)

        if channel:
            # Disabled auto-purge/resend to prevent deleting the existing Ticket Panel
            # await channel.purge()
            # await channel.send(embed=embed, view=TicketView())
            pass

    except Exception as e:

        print(f"Failed to refresh main channel: {e}")



    # ======================================================
    # 🔄 RESTORE VIEWS FOR PERSISTENCE (Cleaned up)
    # ======================================================
    print("Restoring persistent views...")
    # NOTE: Individual deal view restoration is NO LONGER NEEDED 
    # because all views are now STATELESS and registered globally below.
    # The previous loop causing conflicts has been removed.




    

    # Add all views

    bot.add_view(StartDealView())

    bot.add_view(ToSButtonsAllInOne())

    bot.add_view(ToSButtonsAllInOnee())

    bot.add_view(LangButton())

    bot.add_view(SendButton())

    bot.add_view(ExtendButton())

    bot.add_view(ConfButtons())

    bot.add_view(TosView())

    bot.add_view(ToSCoButtons())

    bot.add_view(AmountConButton())

    bot.add_view(WithdrawalView())

    bot.add_view(AddyButtons())

    bot.add_view(ProceedButton())

    bot.add_view(RescanButton())

    bot.add_view(ReleaseButton())

    bot.add_view(ReleaseConButton())

    bot.add_view(CancelConButton())



@bot.event

async def on_message(message):

    if message.author.bot:
        return

    # Reset auto-close timer on activity
    did, dinfo = get_deal_by_channel(message.channel.id)
    if dinfo:
        dinfo['last_activity'] = time.time()
        update_deal(message.channel.id, dinfo)

    user_id = message.author.id



    if user_id in pending_force_actions:

        action = pending_force_actions[user_id]

        deal_id = action["deal_id"]

        deal = action["deal"]
        
        action_type = action.get("type", "release")

        addr = message.content.strip()

        currency = deal.get('currency', 'ltc')



        if not await is_valid_address(addr, currency):

            #await message.channel.send(f"Invalid {currency.upper()} address. Try again.")

            return



        try:
            # Use fee deduction only for release, not for cancel/refund
            if action_type == "release":
                result = await send_funds_with_fee(deal, addr)
                txid = result['main_tx']
                fee_tx = result.get('fee_tx')
                fee_amount = result.get('fee_amount', 0)
            else:
                # Cancel/refund - no fees
                txid = await send_funds_based_on_currency(deal, addr)
                fee_tx = None
                fee_amount = 0



            currency_display = {

                'ltc': 'Litecoin',

                'usdt_bep20': 'USDT (BEP20)',

                'usdt_polygon': 'USDT (Polygon)',

                'solana': 'Solana (SOL)',

                'ethereum': 'Ethereum (ETH)'

            }.get(currency, 'Crypto')

            

            explorer_url = get_explorer_url(currency, txid)
            
            description = f"Funds successfully sent to `{addr}`.\n\n"
            
            if fee_tx and fee_amount > 0:
                fee_explorer_url = get_explorer_url(currency, fee_tx)
                description += f"**Platform Fee:** `{fee_amount:.8f}` {currency_display}\n"
                description += f"**Fee TX:** [{fee_tx[:16]}...]({fee_explorer_url})\n\n"
            
            description += f"**TXID:** [{txid}]({explorer_url})"

            

            done_embed = discord.Embed(

                title="Funds Sent",

                color=0x00ff00,

                description=description

            )



            await message.channel.send(embed=done_embed)



        except Exception as e:

            await message.channel.send(f"Error sending {currency.upper()}: `{e}`")

            return



        del pending_force_actions[user_id]

        return




    await bot.process_commands(message)

# =====================================================

# EXISTING FUNCTIONS (PRESERVED)

# =====================================================



def get_explorer_url(currency, txid):
    """Generate blockchain explorer link based on currency."""
    if not txid or str(txid).lower() == "none" or str(txid).lower() == "manual":
        return None
        
    c = currency.lower()
    txid_str = str(txid)
    
    # Helper to ensure 0x prefix for EVM
    def ensure_0x(h):
        return f"0x{h}" if not h.startswith("0x") else h

    if "polygon" in c or c == "matic":
        return f"https://polygonscan.com/tx/{ensure_0x(txid_str)}"
    elif "bep20" in c or "binance" in c or c == "bnb":
        return f"https://bscscan.com/tx/{ensure_0x(txid_str)}"
    elif "ltc" in c or "litecoin" in c:
        return f"https://blockchair.com/litecoin/transaction/{txid_str}"
    elif "sol" in c or "solana" in c:
        return f"https://solscan.io/tx/{txid_str}"
    elif "eth" in c:
        return f"https://etherscan.io/tx/{ensure_0x(txid_str)}"
        
    return None

async def send_transcript(channel, seller_id, buyer_id, txid: str | None = None):

    """Existing transcript function"""

    try:

        seller = bot.get_user(seller_id)

        buyer = bot.get_user(buyer_id)

        log_channel = bot.get_channel(LOG_CHANNEL)

        history_channel = bot.get_channel(HISTORY_CHANNEL)



        deal_id = None

        deal = None



        result = get_deal_by_channel(channel.id)

        if result:

            deal_id, deal = result



        deal_id_str = str(deal_id) if deal_id else "Unknown"



        if isinstance(deal, dict):

            creator_raw = deal.get("creator_id", seller_id) or seller_id

            other_raw = deal.get("other_user_id", buyer_id) or buyer_id



            try:

                creator_id = int(creator_raw)

            except Exception:

                creator_id = seller_id



            try:

                other_id = int(other_raw)

            except Exception:

                other_id = buyer_id

        else:

            creator_id = seller_id

            other_id = buyer_id



        transcript = await chat_exporter.export(

            channel,

            tz_info="Asia/Kolkata",

            military_time=True,

            fancy_times=True

        )



        if not transcript:

            print("Transcript empty")

            return



        transcript_bytes = transcript.encode("utf-8")



        def id_only(uid: int | str):

            try:

                return f"{int(uid)}"

            except Exception:

                return str(uid)



        base_desc = (

            f"DEAL ID: `{deal_id_str}`\n"

            f"Channel: {channel.name}\n"

            f"**Deal Participants:**\n"

            f"• Ticket Creator: `{id_only(creator_id)}`\n"

            f"• Other Participant: `{id_only(other_id)}`"

        )



        transcript_embed = discord.Embed(

            title="RainyDay MM - Deal Transcript",

            description=f"{base_desc}\n\nTranscript file attached below.",

            color=0x0000ff

        )

        if txid and str(txid).lower() != "none" and len(str(txid)) > 5:
            transcript_embed.add_field(name="Transaction ID", value=f"`{txid}`", inline=False)

        await channel.send(
            embed=transcript_embed,
            file=discord.File(io.BytesIO(transcript_bytes), filename=f"{channel.name}.html")
        )

        if log_channel:
            # 1. Gather Data (from deal dict if available)
            amount = "Unknown"
            currency = "Unknown"
            if deal and isinstance(deal, dict):
                amount = deal.get("amount", "0.0")
                currency = deal.get("currency", "Unknown")
            
            # 2. Build Explorer Link
            explorer_url = get_explorer_url(currency, txid)
            
            # 3. Create Custom Embed (Matching Image)
            is_completed = txid is not None and str(txid).lower() != "none" and len(str(txid)) > 5
            
            log_title = "Transaction Completed" if is_completed else "Ticket Closed"
            log_color = 0x00ff00 if is_completed else 0xff0000
            
            log_embed = discord.Embed(
                title=log_title,
                color=log_color
            )
            
            c_info = get_currency_info(currency)
            if c_info['icon']:
                log_embed.set_thumbnail(url=c_info['icon'])
            
            # Match Image Fields
            log_embed.add_field(name="Deal ID", value=f"`{deal_id_str}`", inline=False)
            log_embed.add_field(name="Type", value=f"`{c_info['name']}`", inline=False)
            
            # Sender & Receiver (Buyer & Seller) using rich format
            buyer_display = get_rich_user_display(channel.guild, buyer_id)
            seller_display = get_rich_user_display(channel.guild, seller_id)
            
            log_embed.add_field(name="Sender (Buyer)", value=buyer_display, inline=False)
            log_embed.add_field(name="Receiver (Seller)", value=seller_display, inline=False)
            
            status_text = "✅ Successful" if is_completed else "🔒 Closed"
            log_embed.add_field(name="Status", value=status_text, inline=False)
            
            if is_completed:
                amt_crypto = deal.get("ltc_amount", "0.0") if deal else "0.0"
                c_tag = currency.upper().replace("_", " ") if currency else "MM"
                # Formatting: [`amt_crypto`] CURRENCY (`$amount` USD)
                log_embed.add_field(name="Amount", value=f"`{amt_crypto}` {c_tag} (`${amount}` USD)", inline=False)
                log_embed.add_field(name="Transaction ID", value=f"`{txid}`", inline=False)

            # Set Footer with Timestamp
            log_embed.set_footer(text=f"Today at {datetime.datetime.now().strftime('%I:%M %p')}")
            
            # 4. Create View with Button
            view = discord.ui.View()
            if is_completed and explorer_url:
                view.add_item(discord.ui.Button(label="View on Blockchain", url=explorer_url))
            else:
                view.add_item(discord.ui.Button(label="No Link Available", style=discord.ButtonStyle.grey, disabled=True))

            # Send full details to log_channel (with IDs and File)
            await log_channel.send(
                embed=log_embed, 
                view=view,
                file=discord.File(io.BytesIO(transcript_bytes), filename=f"{channel.name}.html")
            )

        if is_completed and history_channel and history_channel.id not in (channel.id, getattr(log_channel, "id", None)):
            # PROOF VERSION FOR HISTORY (Enhanced Anonymous Design)
            currency_icons = {
                'ltc': 'https://cryptologos.cc/logos/litecoin-ltc-logo.png',
                'sol': 'https://cryptologos.cc/logos/solana-sol-logo.png',
                'solana': 'https://cryptologos.cc/logos/solana-sol-logo.png',
                'eth': 'https://cryptologos.cc/logos/ethereum-eth-logo.png',
                'ethereum': 'https://cryptologos.cc/logos/ethereum-eth-logo.png',
                'usdt_bep20': 'https://cryptologos.cc/logos/tether-usdt-logo.png',
                'usdt_polygon': 'https://cryptologos.cc/logos/tether-usdt-logo.png',
                'usdt': 'https://cryptologos.cc/logos/tether-usdt-logo.png'
            }
            
            c_tag = currency.upper() if currency else "Crypto"
            raw_curr = deal.get('currency', 'ltc')
            
            full_name = {
                'ltc': 'Litecoin', 'usdt_bep20': 'Tether (BSC)', 'usdt_polygon': 'Tether (Polygon)',
                'solana': 'Solana', 'ethereum': 'Ethereum'
            }.get(raw_curr, c_tag)
            
            title_text = f"{full_name} Deal Complete"
            
            history_embed = discord.Embed(
                title=title_text,
                color=0x00ff00
            )
            
            # Thumbnail
            raw_curr_key = str(raw_curr).lower()
            icon_url = currency_icons.get(raw_curr_key, "https://cdn.discordapp.com/attachments/1438896774243942432/1446517314433454342/discotools-xyz-icon.png")
            
            if icon_url:
                history_embed.set_thumbnail(url=icon_url)
            
            # Formatted Amount: [`crypto_amount`] `CURRENCY` (`$USD_amount` USD)
            crypto_val = deal.get("ltc_amount", "0.0") if deal else "0.0"
            try:
                amt_str = f"`{float(crypto_val):.8f}` {c_tag} (`${float(amount):.2f}` USD)"
            except:
                amt_str = f"`{crypto_val}` {c_tag} (`${amount}` USD)"
                
            history_embed.add_field(name="Amount", value=amt_str, inline=False)
            
            # Participants (Anonymous)
            history_embed.add_field(name="Sender", value="`Anonymous`", inline=True)
            history_embed.add_field(name="Receiver", value="`Anonymous`", inline=True)
            
            # Transaction: Shortened Hash + Link -> SHORT_HASH ([View Transaction](EXPLORER_LINK))
            if txid:
                s_txid = str(txid)
                short_txid = f"{s_txid[:6]}...{s_txid[-6:]}" if len(s_txid) > 12 else s_txid
                
                if explorer_url:
                    val_str = f"`{short_txid}` ([View Transaction]({explorer_url}))"
                else:
                    val_str = f"`{short_txid}`"
                
                history_embed.add_field(name="Transaction", value=val_str, inline=False)
            
            # View with specific button label
            h_view = discord.ui.View()
            if explorer_url:
                btn_label = "View on Blockchain"
                if "polygon" in str(raw_curr): btn_label = "View on PolygonScan"
                elif "bep20" in str(raw_curr): btn_label = "View on BscScan"
                elif "ltc" in str(raw_curr): btn_label = "View on Blockcypher"
                elif "sol" in str(raw_curr): btn_label = "View on SolScan"
                elif "eth" in str(raw_curr): btn_label = "View on Etherscan"
                
                h_view.add_item(discord.ui.Button(label=btn_label, url=explorer_url))
            
            await history_channel.send(embed=history_embed, view=h_view)



        if seller:
            try:
                dm_embed_seller = discord.Embed(
                    title="✅ Transaction Completed!",
                    description=(
                        f"Your deal has been successfully processed and the transcript is available below.\n\n"
                        f"**Thank you for choosing RainyDay MM.** We look forward to serving you again!"
                    ),
                    color=0x00ff00
                )
                dm_embed_seller.add_field(name="🆔 Deal ID", value=f"`{deal_id_str}`", inline=True)
                dm_embed_seller.add_field(name="💬 Channel", value=f"`{channel.name}`", inline=True)
                
                # Rich displays for roles
                dm_embed_seller.add_field(name="👤 You (Seller)", value=get_rich_user_display(channel.guild, seller_id), inline=False)
                dm_embed_seller.add_field(name="👤 Buyer", value=get_rich_user_display(channel.guild, buyer_id), inline=False)
                
                if txid and str(txid).lower() != "none" and len(str(txid)) > 5:
                    dm_embed_seller.add_field(name="🔗 Transaction ID", value=f"`{txid}`", inline=False)

                # View with Button
                dm_view = discord.ui.View()
                if is_completed and explorer_url:
                    dm_view.add_item(discord.ui.Button(label="View on Blockchain", url=explorer_url))

                await seller.send(
                    embed=dm_embed_seller,
                    view=dm_view,
                    file=discord.File(io.BytesIO(transcript_bytes), filename=f"{channel.name}.html")
                )
            except Exception as e:
                print(f"[DM] Failed to send transcript to seller {seller_id}: {e}")

        if buyer:
            try:
                dm_embed_buyer = discord.Embed(
                    title="✅ Transaction Completed!",
                    description=(
                        f"Your deal has been successfully processed and the transcript is available below.\n\n"
                        f"**Thank you for choosing RainyDay MM.** We look forward to serving you again!"
                    ),
                    color=0x00ff00
                )
                dm_embed_buyer.add_field(name="🆔 Deal ID", value=f"`{deal_id_str}`", inline=True)
                dm_embed_buyer.add_field(name="💬 Channel", value=f"`{channel.name}`", inline=True)
                
                # Rich displays for roles
                dm_embed_buyer.add_field(name="👤 Seller", value=get_rich_user_display(channel.guild, seller_id), inline=False)
                dm_embed_buyer.add_field(name="👤 You (Buyer)", value=get_rich_user_display(channel.guild, buyer_id), inline=False)
                
                if txid and str(txid).lower() != "none" and len(str(txid)) > 5:
                    dm_embed_buyer.add_field(name="🔗 Transaction ID", value=f"`{txid}`", inline=False)

                # View with Button
                dm_view_buyer = discord.ui.View()
                if is_completed and explorer_url:
                    dm_view_buyer.add_item(discord.ui.Button(label="View on Blockchain", url=explorer_url))

                await buyer.send(
                    embed=dm_embed_buyer,
                    view=dm_view_buyer,
                    file=discord.File(io.BytesIO(transcript_bytes), filename=f"{channel.name}.html")
                )
            except Exception as e:
                print(f"[DM] Failed to send transcript to buyer {buyer_id}: {e}")



    except Exception as e:

        print(f"Error sending transcript: {e}")



# =====================================================
# HELP & FAQ COMMANDS
# =====================================================

# LEGACY HELP & FAQ REMOVED (Replaced by cogs/help.py)



# =====================================================

# RUN THE BOT

# =====================================================



bot.run(TOKEN)