import discord
from discord.ext import commands, tasks
from discord import app_commands
import config
from crypto_utils import rpc_call, rpc_async
from services.price_service import currency_to_fiat
from services.localization_service import localization_service
from services.transaction_tracking_service import tracking_service
from web3 import Web3, AsyncWeb3, AsyncHTTPProvider
import datetime
import logging
import re
import asyncio

logger = logging.getLogger("ToolsCog")

class Tools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_tracked_transactions.start()

    def cog_unload(self):
        self.check_tracked_transactions.cancel()


    # --- Generic Balance Checker (BTC, LTC, ETH, SOL, USDT, etc.) ---

    async def get_evm_balance(self, address, rpc_urls, token_contract=None, decimals=18):
        """Fetch EVM stats: Balance, TX Count (Nonce)."""
        stats = {
            'balance': 0.0,
            'unconfirmed': 0.0,
            'total_tx': 0,
            'total_received': 0.0,
            'total_sent': 0.0
        }
        for rpc in rpc_urls:
            try:
                w3 = AsyncWeb3(AsyncHTTPProvider(rpc, request_kwargs={"timeout": 5}))
                if not await w3.is_connected():
                    continue

                check_addr = w3.to_checksum_address(address)
                
                # TX Count (Native Nonce)
                stats['total_tx'] = await w3.eth.get_transaction_count(check_addr)

                if token_contract:
                    # Token Balance
                    contract = w3.eth.contract(
                        address=w3.to_checksum_address(token_contract),
                        abi=config.USDT_ABI
                    )
                    balance_raw = await contract.functions.balanceOf(check_addr).call()
                    stats['balance'] = balance_raw / (10 ** decimals)
                else:
                    # Native Balance
                    balance_wei = await w3.eth.get_balance(check_addr)
                    stats['balance'] = float(w3.from_wei(balance_wei, 'ether'))
                
                return stats # Success

            except Exception as e:
                continue
        return None

    async def get_sol_balance(self, address):
        """Fetch SOL stats."""
        stats = {
            'balance': 0.0,
            'unconfirmed': 0.0, 
            'total_tx': 0,
            'total_received': 0.0, 
            'total_sent': 0.0,
            'last_active': None
        }
        import aiohttp
        payload = {"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [address]}
        
        for url in config.SOLANA_RPC_URLS:
            try:
                async with aiohttp.ClientSession() as session:
                    # Balance
                    async with session.post(url, json=payload, timeout=5) as r:
                         if r.status == 200:
                             data = await r.json()
                             if "result" in data:
                                 stats['balance'] = data["result"]["value"] / 1e9
                                 
                                 # Try Last Active
                                 try:
                                     p2 = {
                                         "jsonrpc": "2.0", "id": 2, 
                                         "method": "getSignaturesForAddress", 
                                         "params": [address, {"limit": 1}]
                                     }
                                     async with session.post(url, json=p2, timeout=5) as r2:
                                         if r2.status == 200:
                                             d2 = await r2.json()
                                             if "result" in d2 and len(d2["result"]) > 0:
                                                 stats['last_active'] = d2["result"][0].get('blockTime')
                                 except: pass
                                 
                                 return stats
            except Exception:
                continue
        return None

    async def get_btc_balance_public(self, address):
        """Fetch BTC stats via public API."""
        import aiohttp
        urls = [
            f"https://blockchain.info/rawaddr/{address}?limit=1",
            f"https://api.blockcypher.com/v1/btc/main/addrs/{address}?limit=1"
        ]

        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    async with session.get(url, timeout=5) as r:
                        if r.status == 200:
                            data = await r.json()
                            stats = {
                                'balance': 0.0, 'unconfirmed': 0.0, 
                                'total_tx': 0, 'total_received': 0.0,
                                'last_active': None
                            }

                            # Blockchain.info
                            if "final_balance" in data: 
                                stats['balance'] = data.get('final_balance', 0) / 1e8
                                stats['total_tx'] = data.get('n_tx', 0)
                                stats['total_received'] = data.get('total_received', 0) / 1e8
                                if data.get('txs'):
                                    stats['last_active'] = data['txs'][0].get('time')
                                return stats
                            
                            # Blockcypher
                            if "balance" in data: 
                                stats['balance'] = data.get('balance', 0) / 1e8
                                stats['unconfirmed'] = data.get('unconfirmed_balance', 0) / 1e8
                                stats['total_tx'] = data.get('n_tx', 0)
                                stats['total_received'] = data.get('total_received', 0) / 1e8
                                stats['total_sent'] = data.get('total_sent', 0) / 1e8
                                
                                txs = data.get('unconfirmed_txrefs', []) + data.get('txrefs', [])
                                if txs:
                                    latest = txs[0]
                                    if 'confirmed' in latest:
                                        try:
                                            # format: 2021-08-26T15:24:43Z
                                            dt = datetime.datetime.fromisoformat(latest['confirmed'].replace('Z', '+00:00'))
                                            stats['last_active'] = int(dt.timestamp())
                                        except: pass
                                return stats

                except:
                    continue
        return None

    async def get_ltc_balance_public(self, address):
        """Fetch LTC stats via public API with fallbacks."""
        import aiohttp
        session = await self.bot.get_session() if hasattr(self.bot, "get_session") else aiohttp.ClientSession()
        
        # Sources in priority order
        sources = [
            ("BlockCypher", f"https://api.blockcypher.com/v1/ltc/main/addrs/{address}?limit=1"),
            ("LitecoinSpace", f"https://litecoinspace.org/api/address/{address}")
        ]

        for name, url in sources:
            try:
                async with session.get(url, timeout=5) as r:
                    if r.status == 200:
                        data = await r.json()
                        stats = {
                            'balance': 0.0, 'unconfirmed': 0.0, 
                            'total_tx': 0, 'total_received': 0.0, 
                            'total_sent': 0.0,
                            'last_active': None
                        }
                        
                        if name == "BlockCypher" and "balance" in data:
                            stats['balance'] = data.get('balance', 0) / 1e8
                            stats['unconfirmed'] = data.get('unconfirmed_balance', 0) / 1e8
                            stats['total_tx'] = data.get('n_tx', 0)
                            stats['total_received'] = data.get('total_received', 0) / 1e8
                            stats['total_sent'] = data.get('total_sent', 0) / 1e8
                            
                            txs = data.get('unconfirmed_txrefs', []) + data.get('txrefs', [])
                            if txs:
                                latest = txs[0]
                                if 'confirmed' in latest:
                                      try:
                                          dt = datetime.datetime.fromisoformat(latest['confirmed'].replace('Z', '+00:00'))
                                          stats['last_active'] = int(dt.timestamp())
                                      except: pass
                            return stats

                        elif name == "LitecoinSpace" and "chain_stats" in data:
                            cs = data.get("chain_stats", {})
                            ms = data.get("mempool_stats", {})
                            stats['balance'] = (cs.get("funded_txo_sum", 0) - cs.get("spent_txo_sum", 0)) / 1e8
                            stats['unconfirmed'] = (ms.get("funded_txo_sum", 0) - ms.get("spent_txo_sum", 0)) / 1e8
                            stats['total_tx'] = cs.get("tx_count", 0) + ms.get("tx_count", 0)
                            stats['total_received'] = cs.get("funded_txo_sum", 0) / 1e8
                            stats['total_sent'] = cs.get("spent_txo_sum", 0) / 1e8
                            return stats

            except:
                continue
        return None

    async def currency_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = [
            'btc', 'ltc', 'eth', 'sol', 'bnb', 'matic', 
            'usdt', 'usdtbsc', 'usdtpol', 'usdteth'
        ]
        return [
            app_commands.Choice(name=c.upper(), value=c)
            for c in choices if current.lower() in c.lower()
        ][:25]

    async def fiat_autocomplete(self, interaction: discord.Interaction, current: str):
        choices = ['usd', 'eur', 'gbp', 'inr', 'jpy', 'rub', 'cad', 'aud']
        return [
            app_commands.Choice(name=c.upper(), value=c)
            for c in choices if current.lower() in c.lower()
        ][:25]

    @commands.command(name="usdtbal")
    async def usdtbal_legacy(self, ctx, address: str):
        """Legacy alias for USDT (BSC) balance."""
        await self.handle_balance(ctx, 'usdt_bep20', address)

    @commands.command(name="balance", aliases=["bal", "w", "wallet", "checkbal"])
    async def balance_prefix(self, ctx, currency: str, address: str = None, fiat: str = "usd"):
        """Check Wallet Balance. Usage: ,bal <currency> <address> [fiat]"""
        if address is None:
            await ctx.send("Usage: `,bal <currency> <address> [fiat]`")
            return
        await self.handle_balance(ctx, currency, address, fiat)

    @app_commands.command(name="balance", description="Check Wallet Balance")
    @app_commands.describe(currency="Cryptocurrency (e.g. BTC, LTC, USDT)", address="Wallet Address", fiat="Fiat currency for value (default: USD)")
    @app_commands.autocomplete(currency=currency_autocomplete, fiat=fiat_autocomplete)
    async def balance_slash(self, interaction: discord.Interaction, currency: str, address: str, fiat: str = "usd"):
        await self.handle_balance(interaction, currency, address, fiat)

    async def handle_balance(self, source, currency, address, fiat="usd"):
        reply = source.response.send_message if isinstance(source, discord.Interaction) else source.send
        lang = "en"
        if isinstance(source, discord.Interaction):
            lang = source.locale.value[:2] if source.locale else "en"
            await source.response.defer()
            reply = source.followup.send

        # Normalize
        raw_currency = currency.lower()
        mapping = {
            'usdtbsc': 'usdt_bep20',
            'usdtpol': 'usdt_polygon',
            'usdteth': 'usdt_erc20', 
            'litecoin': 'ltc',
            'ethereum': 'eth',
            'solana': 'sol',
            'bitcoin': 'btc',
            'bnb': 'bnb',
            'matic': 'matic'
        }
        currency = mapping.get(raw_currency, raw_currency)
        fiat = fiat.lower()
        
        # --- LOGIC ---
        balance = None
        symbol = currency.upper()
        chain_name = currency.upper()
        
        try:
            # 1. EVM (Native & Tokens)
            if currency == 'eth':
                balance = await self.get_evm_balance(address, config.ETH_RPC_URLS)
                chain_name = "Ethereum"
                symbol = "ETH"
            elif currency == 'bnb' or currency == 'bsc': # Native BSC
                balance = await self.get_evm_balance(address, config.BEP20_RPC_URLS)
                chain_name = "BSC"
                symbol = "BNB"
            elif currency == 'matic' or currency == 'polygon': # Native Polygon
                balance = await self.get_evm_balance(address, config.POLYGON_RPC_URLS)
                chain_name = "Polygon"
                symbol = "MATIC"
            
            # USDT Variants
            elif currency == 'usdt_bep20':
                balance = await self.get_evm_balance(address, config.BEP20_RPC_URLS, config.USDT_BEP20_CONTRACT, config.USDT_BEP20_DECIMALS)
                chain_name = "BSC"
                symbol = "USDT"
            elif currency == 'usdt_polygon':
                balance = await self.get_evm_balance(address, config.POLYGON_RPC_URLS, config.USDT_POLYGON_CONTRACT, config.USDT_POLYGON_DECIMALS)
                chain_name = "Polygon"
                symbol = "USDT"
            elif currency == 'usdt_erc20' or (currency == 'usdteth'):
                USDT_ETH = "0xdAC17F958D2ee523a2206206994597C13D831ec7"
                balance = await self.get_evm_balance(address, config.ETH_RPC_URLS, USDT_ETH, 6)
                chain_name = "Ethereum"
                symbol = "USDT"
            
            # 2. SOL
            elif currency == 'sol':
                balance = await self.get_sol_balance(address)
                chain_name = "Solana"
                symbol = "SOL"
            
            # 3. BTC
            elif currency == 'btc':
                balance = await self.get_btc_balance_public(address)
                chain_name = "Bitcoin"
                symbol = "BTC"
            
            # 4. LTC
            elif currency == 'ltc':
                balance = await self.get_ltc_balance_public(address)
                chain_name = "Litecoin"
                symbol = "LTC"
            
            else:
                await reply(localization_service.get("unsupported_currency", lang, currency=raw_currency))
                return

            if balance is None:
                await reply(localization_service.get("error_checking_bal", lang, error=chain_name))
                return
            
            stats = balance
            confirmed_bal = stats['balance']
            
            # Value Fiat
            fiat_val = await currency_to_fiat(confirmed_bal + stats.get('unconfirmed', 0), currency, fiat)
            if fiat_val == "RATE_LIMIT":
                await reply(localization_service.get("rate_limit_error", lang))
                return

            # Create Embed
            title = localization_service.get("wallet_overview", lang, symbol=symbol, chain=chain_name)
            embed = discord.Embed(title=title, color=0x00FF00)
            
            colors = {'BTC': 0xF7931A, 'LTC': 0x345D9D, 'ETH': 0x627EEA, 'SOL': 0x14F195, 'BNB': 0xF3BA2F, 'MATIC': 0x8247E5, 'USDT': 0x26A17B}
            embed.color = colors.get(symbol, 0x00FF00)

            icons = {'BTC': "https://cryptologos.cc/logos/bitcoin-btc-logo.png", 'LTC': "https://cryptologos.cc/logos/litecoin-ltc-logo.png", 'ETH': "https://cryptologos.cc/logos/ethereum-eth-logo.png", 'SOL': "https://cryptologos.cc/logos/solana-sol-logo.png", 'USDT': "https://cryptologos.cc/logos/tether-usdt-logo.png", 'BNB': "https://cryptologos.cc/logos/binance-coin-bnb-logo.png", 'MATIC': "https://cryptologos.cc/logos/polygon-matic-logo.png"}
            if symbol in icons: embed.set_thumbnail(url=icons[symbol])

            embed.add_field(name=localization_service.get("from", lang), value=f"`{address}`", inline=False)
            
            unconfirmed = stats.get('unconfirmed', 0)
            total_bal = confirmed_bal + unconfirmed
            
            bal_str = f"**{localization_service.get('confirmed', lang)}:** `{confirmed_bal:,.8f} {symbol}`\n"
            if unconfirmed > 0:
                 bal_str += f"**{localization_service.get('unconfirmed', lang)}:** `{unconfirmed:,.8f} {symbol}`\n"
                 bal_str += f"**{localization_service.get('total', lang)}:** `{total_bal:,.8f} {symbol}`\n"
            
            embed.add_field(name=localization_service.get("balance", lang), value=bal_str, inline=False)
            
            fiat_label = localization_service.get("value_fiat", lang, fiat=fiat.upper())
            embed.add_field(name=fiat_label, value=f"`{fiat_val:,.2f} {fiat.upper()}`", inline=False)
            
            extra_stats = ""
            if stats.get('total_tx'):
                 extra_stats += f"• **{localization_service.get('transactions_count', lang)}:** `{stats['total_tx']}`\n"
            if stats.get('total_received') and stats['total_received'] > 0:
                 extra_stats += f"• **{localization_service.get('total_received', lang)}:** `{stats['total_received']:,.8f} {symbol}`\n"
            if stats.get('total_sent') and stats['total_sent'] > 0:
                  extra_stats += f"• **{localization_service.get('total_sent', lang)}:** `{stats['total_sent']:,.8f} {symbol}`\n"
            if stats.get('last_active'):
                 timestamp = stats.get('last_active')
                 extra_stats += f"• **{localization_service.get('last_active', lang)}:** <t:{timestamp}:R>\n"
            
            if extra_stats:
                embed.add_field(name=localization_service.get("statistics", lang), value=extra_stats, inline=False)

            user_mention = source.user.mention if isinstance(source, discord.Interaction) else source.author.mention
            embed.set_footer(text=localization_service.get("requested_by", lang, user=user_mention).replace(user_mention, str(source.user if isinstance(source, discord.Interaction) else source.author)))
            
            await reply(embed=embed)

        except Exception as e:
            logger.error(f"Balance Check Error: {e}")
            await reply(localization_service.get("error_checking_bal", lang, error=str(e)))



    # --- TX Checker (LTC, ETH, BSC, POLYGON, SOL, BTC) ---

    async def get_ltc_tx(self, txid):
        # Try Local RPC First
        try:
             return await rpc_async("getrawtransaction", txid, 1)
        except Exception as e:
             logger.warning(f"LTC Local RPC Failed: {e}. Switching to Public API.")
        
        # Fallback: Public API
        import aiohttp
        urls = [
            ("LitecoinSpace", f"https://litecoinspace.org/api/tx/{txid}"),
            ("BlockCypher", f"https://api.blockcypher.com/v1/ltc/main/txs/{txid}"),
            ("ChainSo", f"https://chain.so/api/v2/get_tx/LTC/{txid}") 
        ]
        
        async with aiohttp.ClientSession() as session:
            for name, url in urls:
                try:
                    async with session.get(url, timeout=5) as r:
                         if r.status == 200:
                             data = await r.json()
                             # Normalize data to resemble RPC 'getrawtransaction' verbose output
                             
                             if name == "LitecoinSpace":
                                 mapped = {
                                     'txid': data.get('txid', txid),
                                     'confirmations': 0,
                                     'time': data.get('status', {}).get('block_time', 0),
                                     'vout': []
                                 }
                                 # Get confirmations
                                 try:
                                     async with session.get("https://litecoinspace.org/api/blocks/tip/height", timeout=3) as r2:
                                         if r2.status == 200:
                                             tip = int(await r2.text())
                                             mapped['confirmations'] = tip - data['status']['block_height'] + 1
                                 except: pass

                                 for out in data.get('vout', []):
                                     mapped['vout'].append({
                                         'value': out.get('value', 0) / 1e8,
                                         'scriptPubKey': {'addresses': [out.get('scriptpubkey_address')] if out.get('scriptpubkey_address') else []}
                                     })
                                 return mapped

                             elif name == "BlockCypher" and "outputs" in data:
                                 mapped = {
                                     'txid': data.get('hash', txid),
                                     'confirmations': data.get('confirmations', 0),
                                     'time': 0, 
                                     'vout': []
                                 }
                                 
                                 if 'received' in data:
                                     try:
                                         dt = datetime.datetime.fromisoformat(data['received'].replace('Z', '+00:00'))
                                         mapped['time'] = int(dt.timestamp())
                                     except: pass

                                 for out in data.get('outputs', []):
                                     val = out.get('value', 0) / 1e8
                                     addrs = out.get('addresses', [])
                                     
                                     mapped['vout'].append({
                                         'value': val,
                                         'scriptPubKey': {'addresses': addrs}
                                     })
                                 return mapped
                                 
                             elif name == "ChainSo" and "data" in data and "txid" in data["data"]:
                                  d = data["data"]
                                  mapped = {
                                      'txid': d.get('txid'),
                                      'confirmations': d.get('confirmations', 0),
                                      'time': d.get('time', 0),
                                      'vout': []
                                  }
                                  for out in d.get('outputs', []):
                                      val = float(out.get('value', 0))
                                      addr = out.get('address')
                                      mapped['vout'].append({
                                          'value': val,
                                          'scriptPubKey': {'addresses': [addr] if addr else []}
                                      })
                                  return mapped

                except Exception as e:
                    # logger.error(f"LTC Public API Error: {e}")
                    continue
        return None

    async def get_evm_tx(self, txid, rpc_urls):
        """Fetch EVM transaction details with block info using AsyncWeb3."""
        for rpc in rpc_urls:
            try:
                w3 = AsyncWeb3(AsyncHTTPProvider(rpc, request_kwargs={"timeout": 5}))
                
                if not await w3.is_connected():
                    continue
                    
                tx = await w3.eth.get_transaction(txid)
                receipt = await w3.eth.get_transaction_receipt(txid)
                
                # Identify Block Number
                try:
                    b_num = receipt['blockNumber']
                except:
                    try:
                        b_num = tx['blockNumber']
                    except:
                        b_num = None
                
                block = None
                if b_num is not None:
                    # Try to fetch block timestamp quickly
                    try:
                        # Inject POA middleware for block fetching (web3.py v7+)
                        try:
                            from web3.middleware import ExtraDataToPOAMiddleware
                            w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
                        except ImportError:
                            try:
                                from web3.middleware import geth_poa_middleware
                                w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                            except: pass
                        
                        block = await w3.eth.get_block(b_num)
                        return tx, receipt, w3, block
                    except:
                        pass
                
                return tx, receipt, w3, block
            except Exception:
                continue
        return None, None, None, None

    async def get_solana_tx(self, txid):
        """Fetch Solana transaction details."""
        import aiohttp
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getTransaction",
            "params": [
                txid,
                {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}
            ]
        }
        for url in config.SOLANA_RPC_URLS:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, timeout=5) as r:
                         if r.status == 200:
                             data = await r.json()
                             if "result" in data and data["result"]:
                                 return data["result"]
            except Exception:
                continue
        return None

    # Helper for BTC (Using public API as fallback since no RPC config)
    async def get_btc_tx_public(self, txid):
        import aiohttp
        # Trying BlockCypher (free tier limits) or similar
        # Fallback to blockchain.info which is often open
        urls = [
            f"https://blockchain.info/rawtx/{txid}",
            f"https://api.blockcypher.com/v1/btc/main/txs/{txid}"
        ]
        
        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    async with session.get(url, timeout=5) as r:
                        if r.status == 200:
                            return await r.json()
                except:
                    continue
        return None

    @commands.command(name="tx", aliases=["t", "trans", "hash", "checktx"])
    async def tx_prefix(self, ctx, currency: str, txid: str = None, fiat: str = "usd"):
        """Check transaction details. Usage: =tx <currency> <txid> [fiat]"""
        if txid is None:
             await ctx.send("Usage: `=tx <currency> <txid> [fiat]`")
             return
        await self.handle_tx(ctx, currency, txid, fiat)

    @app_commands.command(name="tx", description="Check Transaction Details")
    @app_commands.describe(currency="Cryptocurrency (e.g. BTC, LTC, USDT)", txid="Transaction ID / Hash", fiat="Fiat currency for value (default: USD)")
    @app_commands.autocomplete(currency=currency_autocomplete, fiat=fiat_autocomplete)
    async def tx_slash(self, interaction: discord.Interaction, currency: str, txid: str, fiat: str = "usd"):
        await self.handle_tx(interaction, currency, txid, fiat)

    async def handle_tx(self, source, currency, txid, fiat="usd"):
        reply = source.response.send_message if isinstance(source, discord.Interaction) else source.send
        lang = "en"
        if isinstance(source, discord.Interaction):
            lang = source.locale.value[:2] if source.locale else "en"
            await source.response.defer()
            reply = source.followup.send

        currency = currency.lower()
        fiat = fiat.lower()
        
        # Normalize synonyms
        mapping = {
            'usdtbsc': 'usdt_bep20',
            'usdtpol': 'usdt_polygon',
            'usdteth': 'usdt_erc20', 
            'litecoin': 'ltc',
            'ethereum': 'eth',
            'solana': 'sol',
            'bitcoin': 'btc',
            'bnb': 'bnb',
            'bsc': 'bnb',
            'matic': 'matic',
            'polygon': 'matic'
        }
        currency = mapping.get(currency, currency)

        # "usdt" generic handler defaults to BSC
        if currency == 'usdt':
            currency = 'usdt_bep20'

        try:
            embed = None
            logger.info(f"Checking {currency} TX: {txid}")
            
            # --- LTC ---
            if currency == 'ltc':
                tx_data = await self.get_ltc_tx(txid)
                if not tx_data:
                    await reply(localization_service.get("tx_not_found", lang, chain="Litecoin"))
                    return
                
                total_out = sum(v['value'] for v in tx_data.get('vout', []))
                val_fiat = await currency_to_fiat(total_out, 'ltc', fiat)
                if val_fiat == "RATE_LIMIT":
                    await reply(localization_service.get("rate_limit_error", lang))
                    return

                inf_text = f"• **{localization_service.get('total_amount', lang)}** `{total_out:.8f} LTC`\n"
                inf_text += f"    ◦ {localization_service.get('approximate_value', lang)} `{val_fiat:,.2f} {fiat.upper()}`\n"
                
                # Timestamp
                ts = tx_data.get('time', 0)
                if ts:
                    inf_text += f"• **{localization_service.get('created_at', lang)}** <t:{ts}:R>\n"
                
                confs = tx_data.get('confirmations', 0)
                status_emoji = "✅" if confs >= 1 else "⏳"
                inf_text += f"• **{localization_service.get('confirmed_status', lang)}** {status_emoji}"

                embed = discord.Embed(title=localization_service.get("tx_details", lang, chain="LiteCoin"), color=0x345D9D)
                embed.set_thumbnail(url="https://cryptologos.cc/logos/litecoin-ltc-logo.png")
                
                embed.add_field(name=localization_service.get("information_header", lang), value=inf_text, inline=False)
                
                # Outputs
                vout = tx_data.get('vout', [])
                out_header = localization_service.get("outputs_label", lang, count=len(vout))
                out_text = ""
                for i, out in enumerate(vout[:5]): # Show up to 5
                    val = out.get('value', 0)
                    val_fiat_out = await currency_to_fiat(val, 'ltc', fiat)
                    addrs = out.get('scriptPubKey', {}).get('addresses', [])
                    addr_str = addrs[0] if addrs else "Unknown"
                    out_text += f"• **{addr_str}**\n"
                    out_text += f"    ◦ {localization_service.get('value_received', lang)} `{val:.8f} LTC = {val_fiat_out:,.2f} {fiat.upper()}`\n"
                
                if len(vout) > 5:
                    out_text += f"*... and {len(vout)-5} more*"

                if out_text:
                    embed.add_field(name=out_header, value=out_text, inline=False)
                
                # Immediate reply for LTC
                url = self.get_explorer_link('ltc', txid)
                view = discord.ui.View(timeout=180)
                if url:
                    view.add_item(discord.ui.Button(label=localization_service.get("view_more_details", lang), url=url))
                
                requester = source.user.mention if isinstance(source, discord.Interaction) else source.author.mention
                embed.set_footer(text=localization_service.get("requested_by", lang, user=requester).replace(requester, str(source.user if isinstance(source, discord.Interaction) else source.author)))
                
                await reply(embed=embed, view=view)
                return


            # --- BTC ---
            elif currency == 'btc':
                tx_data = await self.get_btc_tx_public(txid)
                if not tx_data:
                    await reply(localization_service.get("tx_not_found", lang, chain="Bitcoin"))
                    return
                
                # Identify if blockchain.info or blockcypher
                # blockchain.info uses 'out' -> 'value' (satoshis)
                # blockcypher uses 'outputs' -> 'value' (satoshis)
                
                total_sats = 0
                outputs = tx_data.get('out', tx_data.get('outputs', []))
                
                for o in outputs:
                    total_sats += o.get('value', 0)
                
                total_btc = total_sats / 1e8
                val_fiat = await currency_to_fiat(total_btc, 'btc', fiat)
                if val_fiat == "RATE_LIMIT":
                    await reply(localization_service.get("rate_limit_error", lang))
                    return
                
                # Confirmations
                # blockchain.info might not show confs directly in rawtx sometimes? It usually does 'block_height'.
                # blockcypher shows 'confirmations'.
                confs = tx_data.get('confirmations', "Unknown")
                
                inf_text = f"• **{localization_service.get('total_amount', lang)}** `{total_btc:.8f} BTC`\n"
                inf_text += f"    ◦ {localization_service.get('approximate_value', lang)} `{val_fiat:,.2f} {fiat.upper()}`\n"
                
                # Time
                ts = tx_data.get('time', 0)
                if ts:
                    inf_text += f"• **{localization_service.get('created_at', lang)}** <t:{ts}:R>\n"
                
                try: status_emoji = "✅" if int(confs) >= 1 else "⏳"
                except: status_emoji = "⏳"
                inf_text += f"• **{localization_service.get('confirmed_status', lang)}** {status_emoji}"

                embed = discord.Embed(title=localization_service.get("tx_details", lang, chain="Bitcoin"), color=0xF7931A)
                embed.set_thumbnail(url="https://cryptologos.cc/logos/bitcoin-btc-logo.png")
                
                embed.add_field(name=localization_service.get("information_header", lang), value=inf_text, inline=False)

                # Outputs
                outputs = tx_data.get('out', tx_data.get('outputs', []))
                out_header = localization_service.get("outputs_label", lang, count=len(outputs))
                out_text = ""
                for o in outputs[:5]:
                    val = o.get('value', 0) / 1e8
                    val_fiat_out = await currency_to_fiat(val, 'btc', fiat)
                    addr = o.get('addr', o.get('address', 'Unknown'))
                    out_text += f"• **{addr}**\n"
                    out_text += f"    ◦ {localization_service.get('value_received', lang)} `{val:.8f} BTC = {val_fiat_out:,.2f} {fiat.upper()}`\n"
                
                if len(outputs) > 5:
                    out_text += f"*... and {len(outputs)-5} more*"

                if out_text:
                    embed.add_field(name=out_header, value=out_text, inline=False)

                # Immediate reply for BTC
                url = self.get_explorer_link('btc', txid)
                view = discord.ui.View(timeout=180)
                if url:
                    view.add_item(discord.ui.Button(label=localization_service.get("view_more_details", lang), url=url))
                
                requester = source.user.mention if isinstance(source, discord.Interaction) else source.author.mention
                embed.set_footer(text=localization_service.get("requested_by", lang, user=requester).replace(requester, str(source.user if isinstance(source, discord.Interaction) else source.author)))
                
                await reply(embed=embed, view=view)
                return


            # --- EVM (ETH, BSC, Polygon) ---
            elif currency in ['eth', 'usdt_erc20', 'usdt_bep20', 'usdt_polygon', 'bnb', 'matic']:
                
                # Determine Chain
                if currency == 'eth' or currency == 'usdt_erc20':
                    rpc_urls = config.ETH_RPC_URLS
                    native_sym = "ETH"
                    chain_name = "Ethereum"
                    color = 0x627EEA
                    usdt_contract = "0xdAC17F958D2ee523a2206206994597C13D831ec7" 
                    decimals = 6 # USDT ERC20 is 6 decimals
                    
                elif currency in ['usdt_bep20', 'bnb']:
                    rpc_urls = config.BEP20_RPC_URLS
                    native_sym = "BNB"
                    chain_name = "BSC"
                    color = 0xF3BA2F
                    usdt_contract = config.USDT_BEP20_CONTRACT
                    decimals = config.USDT_BEP20_DECIMALS # 18
                    
                elif currency in ['usdt_polygon', 'matic']:
                    rpc_urls = config.POLYGON_RPC_URLS
                    native_sym = "MATIC"
                    chain_name = "Polygon"
                    color = 0x8247E5
                    usdt_contract = config.USDT_POLYGON_CONTRACT
                    decimals = config.USDT_POLYGON_DECIMALS # 6

                logger.info(f"Fetching EVM TX from RPCs for {chain_name}...")
                res = await self.get_evm_tx(txid, rpc_urls)
                if not res or not res[0]:
                    logger.warning(f"TX not found for {chain_name}: {txid}")
                    await reply(localization_service.get("tx_not_found", lang, chain=chain_name))
                    return
                tx, receipt, w3, block = res
                logger.info(f"Found TX. Sender: {tx['from']} Receiver: {tx['to']}")

                # Initial Time Fetch
                time_str = "Unknown"
                if block:
                    try: 
                        ts = block.get('timestamp') or block['timestamp']
                        if hasattr(ts, 'hex'): ts = int(ts.hex(), 16)
                        ts = int(ts)
                        time_str = f"<t:{ts}:f> (<t:{ts}:R>)"
                    except: pass

                # Sender/Receiver
                sender = tx['from']
                receiver = tx['to']
                
                # Check Native Value
                val_native = float(w3.from_wei(tx['value'], 'ether'))
                
                # Check Token Logs (USDT etc)
                token_val = 0.0
                is_token_tx = False
                found_token_sym = "USDT"
                
                for log in receipt['logs']:
                    if str(log['address']).lower() == usdt_contract.lower():
                        topics = log.get('topics', [])
                        if len(topics) > 0:
                            top0 = topics[0].hex() if hasattr(topics[0], 'hex') else str(topics[0])
                            if not top0.startswith('0x'): top0 = '0x' + top0
                            
                            if top0.lower() == '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef':
                                try:
                                    data_val = log.get('data', '0x0')
                                    if hasattr(data_val, 'hex'): data_val = data_val.hex()
                                    if not str(data_val).startswith('0x'): data_val = '0x' + str(data_val)
                                    
                                    val_int = int(data_val, 16)
                                    token_val += val_int / (10 ** decimals)
                                    is_token_tx = True
                                    
                                    if len(topics) > 2:
                                        topic_to = topics[2].hex() if hasattr(topics[2], 'hex') else str(topics[2])
                                        receiver = "0x" + topic_to[-40:]
                                        receiver = w3.to_checksum_address(receiver)
                                except: pass

                if is_token_tx:
                    display_val = f"{token_val:,.4f} {found_token_sym}"
                    val_fiat = await currency_to_fiat(token_val, 'usdt', fiat)
                else:
                    display_val = f"{val_native:,.8f} {native_sym}"
                    val_fiat = await currency_to_fiat(val_native, native_sym.lower(), fiat)

                if val_fiat == "RATE_LIMIT":
                    logger.warning("Fiat conversion rate limited")
                    await reply(localization_service.get("rate_limit_error", lang))
                    return

                logger.info(f"Starting LIVE MONITORING loop for {txid}")
                live_msg = None
                max_retries = 10 # ~1 minute of auto-updates (6s per loop)
                
                for attempt in range(max_retries):
                    # Re-fetch latest block for confirmations
                    confs = 0
                    current_block = 0
                    try:
                        current_block = await w3.eth.block_number
                        if receipt and receipt.get('blockNumber'):
                            confs = max(0, current_block - receipt['blockNumber'] + 1)
                    except: pass

                    # Re-fetch timestamp if unknown
                    if time_str == "Unknown" or not time_str:
                        try:
                            b_num = None
                            try: b_num = receipt['blockNumber']
                            except: b_num = tx.get('blockNumber')
                            
                            if b_num:
                                if hasattr(b_num, 'hex'): b_num = int(b_num.hex(), 16)
                                for rpc_node in rpc_urls:
                                    try:
                                        w_node = AsyncWeb3(AsyncHTTPProvider(rpc_node, request_kwargs={"timeout": 3}))
                                        b_data = await w_node.eth.get_block(b_num)
                                        ts = b_data.get('timestamp') or b_data['timestamp']
                                        if ts:
                                            if hasattr(ts, 'hex'): ts = int(ts.hex(), 16)
                                            ts = int(ts)
                                            time_str = f"<t:{ts}:f> (<t:{ts}:R>)"
                                            break
                                    except: continue
                        except: pass

                    # Prepare Status String
                    if receipt['status'] == 1:
                        target = 6 if currency in ['matic', 'bnb'] else 2
                        if confs >= target:
                            status_val = f"✅ **Confirmed**"
                        else:
                            status_val = f"⏳ **Confirming** ({confs}/{target})"
                    else:
                        status_val = "❌ **Failed**"

                    embed = discord.Embed(title=localization_service.get("tx_details", lang, chain=chain_name), color=color)
                    embed.add_field(name=localization_service.get("amount", lang), value=f"`{display_val}` (`{val_fiat:,.2f} {fiat.upper()}`)", inline=False)
                    embed.add_field(name=localization_service.get("status", lang), value=status_val, inline=False)
                    embed.add_field(name=localization_service.get("time", lang), value=time_str, inline=False)
                    embed.add_field(name=localization_service.get("from", lang), value=f"`{sender}`", inline=False)
                    embed.add_field(name=localization_service.get("to", lang), value=f"`{receiver}`", inline=False)
                    embed.add_field(name=localization_service.get("block", lang), value=f"`{receipt['blockNumber']}`", inline=True)
                    
                    # Common fields
                    requester = source.user.mention if isinstance(source, discord.Interaction) else source.author.mention
                    embed.set_footer(text=localization_service.get("requested_by", lang, user=requester).replace(requester, str(source.user if isinstance(source, discord.Interaction) else source.author)))
                    
                    # Buttons
                    url = self.get_explorer_link(currency, txid)
                    view = discord.ui.View(timeout=180)
                    if url:
                        view.add_item(discord.ui.Button(label=localization_service.get("view_on_blockchain", lang), url=url))
                    
                    # Send or Edit
                    if not live_msg:
                        live_msg = await reply(embed=embed, view=view)
                    else:
                        try: await live_msg.edit(embed=embed, view=view)
                        except: break # Message deleted

                    # If confirmed, stop loop early
                    if receipt['status'] == 0 or (confs >= (6 if currency in ['matic', 'bnb'] else 2)):
                        break
                    
                    await asyncio.sleep(6) # Poll every 6 seconds

                return # End handle_tx

        except Exception as e:
            logger.error(f"TX Check Error: {e}")
            # Try to send final error if msg was never sent
            try: await reply(localization_service.get("error_checking_tx", lang, error=str(e)))
            except: pass

    def get_explorer_link(self, currency, txid):
        """Generate explorer URL."""
        c = currency.lower()
        if c == 'ltc':
            return f"https://live.blockcypher.com/ltc/tx/{txid}/"
        elif c == 'btc':
            return f"https://www.blockchain.com/explorer/transactions/btc/{txid}"
        elif c == 'eth' or c == 'usdt_erc20':
            return f"https://etherscan.io/tx/{txid}"
        elif c == 'bnb' or c == 'usdt_bep20' or c == 'usdtbsc':
            return f"https://bscscan.com/tx/{txid}"
        elif c == 'matic' or c == 'usdt_polygon' or c == 'usdtpol':
            return f"https://polygonscan.com/tx/{txid}"
        elif c in ['sol', 'solana']:
            return f"https://solscan.io/tx/{txid}"
    @app_commands.command(name="track-transaction", description="Track a transaction and get notified on confirmations (Admin Only)")
    @app_commands.describe(
        txid="Transaction Hash/ID",
        currency="Cryptocurrency (BTC, LTC, ETH, etc.)",
        confirmations="Number of confirmations to wait for (default: 1)"
    )
    @app_commands.autocomplete(currency=currency_autocomplete)
    async def track_transaction(self, interaction: discord.Interaction, txid: str, currency: str, confirmations: int = 1):
        """Admin only command to track a transaction."""
        if interaction.user.id not in config.OWNER_IDS:
            await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
            return

        txid = txid.strip()
        currency = currency.lower()
        
        # Normalize
        mapping = {
            'usdtbsc': 'usdt_bep20',
            'usdtpol': 'usdt_polygon',
            'usdteth': 'usdt_erc20', 
            'litecoin': 'ltc',
            'ethereum': 'eth',
            'solana': 'sol',
            'bitcoin': 'btc',
            'bnb': 'bnb',
            'bsc': 'bnb',
            'matic': 'matic',
            'polygon': 'matic'
        }
        currency = mapping.get(currency, currency)
        if currency == 'usdt': currency = 'usdt_bep20'

        tracking_service.add_tracking(interaction.user.id, txid, currency, confirmations)
        
        embed = discord.Embed(
            title="🎯 Transaction Tracking Started",
            description=(
                f"I will notify you when this transaction reaches **{confirmations}** confirmation(s).\n\n"
                f"**TXID:** `{txid}`\n"
                f"**Currency:** {currency.upper()}"
            ),
            color=0x3498db
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @tasks.loop(minutes=1)
    async def check_tracked_transactions(self):
        """Background task to monitor confirmations for tracked transactions."""
        pending = tracking_service.get_all_pending_tracking()
        if not pending:
            return

        for track in pending:
            try:
                txid = track['txid']
                currency = track['currency']
                target = track['target_confs']
                user_id = track['user_id']
                
                confs = 0
                
                # Check based on currency
                if currency == 'ltc':
                    tx_data = await self.get_ltc_tx(txid)
                    confs = tx_data.get('confirmations', 0) if tx_data else 0
                elif currency == 'btc':
                    tx_data = await self.get_btc_tx_public(txid)
                    confs = tx_data.get('confirmations', 0) if tx_data else 0
                elif currency in ['eth', 'usdt_erc20', 'usdt_bep20', 'usdt_polygon', 'bnb', 'matic']:
                    # EVM
                    rpc_urls = []
                    if currency in ['eth', 'usdt_erc20']: rpc_urls = config.ETH_RPC_URLS
                    elif currency in ['usdt_bep20', 'bnb']: rpc_urls = config.BEP20_RPC_URLS
                    elif currency in ['usdt_polygon', 'matic']: rpc_urls = config.POLYGON_RPC_URLS
                    
                    res = await self.get_evm_tx(txid, rpc_urls)
                    if res and res[1]: # receipt
                        receipt = res[1]
                        w3 = res[2]
                        current_block = await w3.eth.block_number
                        confs = max(0, current_block - receipt['blockNumber'] + 1)
                elif currency == 'sol':
                    tx_data = await self.get_solana_tx(txid)
                    if tx_data:
                        # Solana doesn't really have "confirmations" in the same way, but it has 'slot'
                        # For simplicity, if it's found and successful, we'll treat it as confirmed
                        # Or check meta['err'] is None
                        meta = tx_data.get('meta')
                        if meta and meta.get('err') is None:
                            confs = target # Instant confirm for Solana tracking in this context
                
                if confs >= target:
                    # Notify User
                    try:
                        user = await self.bot.fetch_user(int(user_id))
                        if user:
                            embed = discord.Embed(
                                title="✅ Transaction Confirmed!",
                                description=(
                                    f"Your tracked transaction has reached **{confs}** confirmation(s).\n\n"
                                    f"**TXID:** `{txid}`\n"
                                    f"**Currency:** {currency.upper()}"
                                ),
                                color=0x2ecc71
                            )
                            url = self.get_explorer_link(currency, txid)
                            if url:
                                view = discord.ui.View()
                                view.add_item(discord.ui.Button(label="View on Explorer", url=url))
                                await user.send(embed=embed, view=view)
                            else:
                                await user.send(embed=embed)
                    except Exception as e:
                        logger.error(f"Failed to notify user {user_id}: {e}")
                    
                    # Mark as completed
                    tracking_service.update_tracking_status(track['id'], 'completed')
                    
            except Exception as e:
                logger.error(f"Error checking tracking {track['id']}: {e}")

    @app_commands.command(name="search", description="Intelligently search for any address or transaction ID")
    @app_commands.describe(query="The address or TXID search for")
    async def search_slash(self, interaction: discord.Interaction, query: str):
        """Universal search for addresses and TXIDs."""
        query = query.strip()
        
        # Regex patterns
        patterns = {
            'evm_addr': r'^0x[a-fA-F0-9]{40}$',
            'evm_tx': r'^0x[a-fA-F0-9]{64}$',
            'btc_addr': r'^(1|3|bc1)[a-zA-Z0-9]{25,62}$',
            'ltc_addr': r'^(L|M|ltc1)[a-zA-Z0-9]{26,45}$',
            'sol_addr': r'^[1-9A-HJ-NP-Za-km-z]{32,44}$',
            'generic_tx': r'^[a-fA-F0-9]{64}$'
        }

        # Detection logic
        if re.match(patterns['evm_addr'], query):
             await self.handle_balance(interaction, "eth", query)
             return

        if re.match(patterns['evm_tx'], query):
             await self.handle_tx(interaction, "eth", query)
             return

        if re.match(patterns['ltc_addr'], query):
             await self.handle_balance(interaction, "ltc", query)
             return

        if re.match(patterns['btc_addr'], query):
             await self.handle_balance(interaction, "btc", query)
             return

        if re.match(patterns['sol_addr'], query):
             await self.handle_balance(interaction, "sol", query)
             return

        if re.match(patterns['generic_tx'], query):
             await self.handle_tx(interaction, "ltc", query)
             return

        await interaction.response.send_message("❌ Could not automatically detect the chain. Use `/balance` or `/tx` directly.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Tools(bot))
