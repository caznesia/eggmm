

import time
import asyncio
import aiohttp


price_cache = {}
CACHE_DURATION = 60  
GLOBAL_SESSION = None

async def get_session():
    
    global GLOBAL_SESSION
    if GLOBAL_SESSION is None or GLOBAL_SESSION.closed:
        GLOBAL_SESSION = aiohttp.ClientSession()
    return GLOBAL_SESSION

async def get_coingecko_price(currency_key, vs_currency="usd"):
    
    mapping = {
        'ltc': 'litecoin',
        'solana': 'solana',
        'ethereum': 'ethereum',
        'usdt_bep20': 'tether',
        'usdt_polygon': 'tether',
        'usdt_erc20': 'tether',
        'usdt_solana': 'tether',
        'usdt_arbitrum': 'tether',
        'usdt_optimism': 'tether',
        'usdt_avalanche': 'tether',
        'usdt_trc20': 'tether',
        'usdt': 'tether',
        'usdc_bep20': 'usd-coin',
        'usdc_polygon': 'usd-coin',
        'usdc_erc20': 'usd-coin',
        'usdc_solana': 'usd-coin',
        'usdc_base': 'usd-coin',
        'usdc_avalanche': 'usd-coin',
        'usdc_optimism': 'usd-coin',
        'usdc_arbitrum': 'usd-coin',
        'usdc': 'usd-coin',
        'usc_bep20': 'usd-coin', 
        'usdt_arbitum': 'tether', 
        'usdc_arbitum': 'usd-coin', 
        'bnb': 'binancecoin',
        'matic': 'matic-network',
        'btc': 'bitcoin',
        'bitcoin': 'bitcoin',
        'avax': 'avalanche-2',
        'avalanche': 'avalanche-2',
        'doge': 'dogecoin',
        'tron': 'tron',
        'trx': 'tron',
        'shib': 'shiba-inu',
        'shiba inu': 'shiba-inu',
        'pepe': 'pepe',
    }
    
    cg_id = mapping.get(currency_key.lower(), currency_key.lower())
    
    
    low_key = currency_key.lower()
    if any(x in low_key for x in ['usdt', 'tether']):
        cg_id = 'tether'
    elif any(x in low_key for x in ['usdc', 'usd-coin']):
        cg_id = 'usd-coin'

    vs_curr = vs_currency.lower()
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies={vs_curr}"
    
    session = await get_session()
    try:
        async with session.get(url, timeout=5) as r:
            if r.status == 200:
                data = await r.json()
                if cg_id in data:
                    return float(data[cg_id][vs_curr])
            elif r.status == 429:
                return "RATE_LIMIT"
    except: pass
    return None

async def get_ltc_price(vs_currency="usd"):
    
    vs_curr = vs_currency.lower()
    if vs_curr != "usd":
        return await get_coingecko_price('ltc', vs_curr)

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
                elif r.status == 429:
                    return "RATE_LIMIT"
        except: pass
        return None

    tasks = [asyncio.create_task(fetch(u)) for u in apis]
    for task in asyncio.as_completed(tasks):
        res = await task
        if res:
            if res == "RATE_LIMIT": continue
            for t in tasks: t.cancel()
            return res
    return 0.0

async def get_solana_price(vs_currency="usd"):
    
    vs_curr = vs_currency.lower()
    if vs_curr != "usd":
        return await get_coingecko_price('solana', vs_curr)

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
                elif r.status == 429:
                    return "RATE_LIMIT"
        except: pass
        return None

    tasks = [asyncio.create_task(fetch(u)) for u in apis]
    for task in asyncio.as_completed(tasks):
        res = await task
        if res:
            if res == "RATE_LIMIT": continue
            for t in tasks: t.cancel()
            return res
    return 0.0

async def get_bnb_price(vs_currency="usd"):
    
    vs_curr = vs_currency.lower()
    if vs_curr != "usd":
        return await get_coingecko_price('binancecoin', vs_curr)

    apis = [
        "https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT",
        "https://api.coingecko.com/api/v3/simple/price?ids=binancecoin&vs_currencies=usd",
        "https://min-api.cryptocompare.com/data/price?fsym=BNB&tsyms=USD",
    ]
    session = await get_session()
    
    async def fetch(url):
        try:
            async with session.get(url, timeout=3) as r:
                if r.status == 200:
                    d = await r.json()
                    if "price" in d: return float(d["price"])
                    if "binancecoin" in d: return float(d["binancecoin"]["usd"])
                    if "USD" in d: return float(d["USD"])
                elif r.status == 429:
                    return "RATE_LIMIT"
        except: pass
        return None

    tasks = [asyncio.create_task(fetch(u)) for u in apis]
    for task in asyncio.as_completed(tasks):
        res = await task
        if res:
            if res == "RATE_LIMIT": continue
            for t in tasks: t.cancel()
            return res
    return 0.0

async def get_ethereum_price(vs_currency="usd"):
    
    vs_curr = vs_currency.lower()
    if vs_curr != "usd":
        return await get_coingecko_price('ethereum', vs_curr)

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
                elif r.status == 429:
                    return "RATE_LIMIT"
        except: pass
        return None

    tasks = [asyncio.create_task(fetch(u)) for u in apis]
    for task in asyncio.as_completed(tasks):
        res = await task
        if res:
            if res == "RATE_LIMIT": continue
            for t in tasks: t.cancel()
            return res
    return 0.0

async def get_shib_price(vs_currency="usd"):
    
    vs_curr = vs_currency.lower()
    if vs_curr != "usd":
        return await get_coingecko_price('shiba-inu', vs_curr)

    apis = [
        "https://api.binance.com/api/v3/ticker/price?symbol=SHIBUSDT",
        "https://api.coingecko.com/api/v3/simple/price?ids=shiba-inu&vs_currencies=usd",
        "https://min-api.cryptocompare.com/data/price?fsym=SHIB&tsyms=USD",
    ]
    session = await get_session()
    
    async def fetch(url):
        try:
            async with session.get(url, timeout=3) as r:
                if r.status == 200:
                    d = await r.json()
                    if "price" in d: return float(d["price"])
                    if "shiba-inu" in d: return float(d["shiba-inu"]["usd"])
                    if "USD" in d: return float(d["USD"])
                elif r.status == 429:
                    return "RATE_LIMIT"
        except: pass
        return None

    tasks = [asyncio.create_task(fetch(u)) for u in apis]
    for task in asyncio.as_completed(tasks):
        res = await task
        if res:
            if res == "RATE_LIMIT": continue
            for t in tasks: t.cancel()
            return res
    return 0.0

async def get_pepe_price(vs_currency="usd"):
    
    vs_curr = vs_currency.lower()
    if vs_curr != "usd":
        return await get_coingecko_price('pepe', vs_curr)

    apis = [
        "https://api.binance.com/api/v3/ticker/price?symbol=PEPEUSDT",
        "https://api.coingecko.com/api/v3/simple/price?ids=pepe&vs_currencies=usd",
        "https://min-api.cryptocompare.com/data/price?fsym=PEPE&tsyms=USD",
    ]
    session = await get_session()
    
    async def fetch(url):
        try:
            async with session.get(url, timeout=3) as r:
                if r.status == 200:
                    d = await r.json()
                    if "price" in d: return float(d["price"])
                    if "pepe" in d: return float(d["pepe"]["usd"])
                    if "USD" in d: return float(d["USD"])
                elif r.status == 429:
                    return "RATE_LIMIT"
        except: pass
        return None

    tasks = [asyncio.create_task(fetch(u)) for u in apis]
    for task in asyncio.as_completed(tasks):
        res = await task
        if res:
            if res == "RATE_LIMIT": continue
            for t in tasks: t.cancel()
            return res
    return 0.0

async def get_usdt_price(vs_currency="usd"):
    
    vs_curr = vs_currency.lower()
    if vs_curr != "usd":
        return await get_coingecko_price('usdt', vs_curr)

    apis = [
        "https://api.binance.com/api/v3/ticker/price?symbol=USDTUSDC",
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
                elif r.status == 429:
                    return "RATE_LIMIT"
        except: pass
        return None

    tasks = [asyncio.create_task(fetch(u)) for u in apis]
    for task in asyncio.as_completed(tasks):
        res = await task
        if res:
            if res == "RATE_LIMIT": continue
            for t in tasks: t.cancel()
            return res
    return 1.0

async def get_btc_price(vs_currency="usd"):
    
    vs_curr = vs_currency.lower()
    if vs_curr != "usd":
        return await get_coingecko_price('bitcoin', vs_curr)

    apis = [
        "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT",
        "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
        "https://min-api.cryptocompare.com/data/price?fsym=BTC&tsyms=USD",
    ]
    session = await get_session()
    
    async def fetch(url):
        try:
            async with session.get(url, timeout=3) as r:
                if r.status == 200:
                    d = await r.json()
                    if "price" in d: return float(d["price"])
                    if "bitcoin" in d: return float(d["bitcoin"]["usd"])
                    if "USD" in d: return float(d["USD"])
                elif r.status == 429:
                    return "RATE_LIMIT"
        except: pass
        return None

    tasks = [asyncio.create_task(fetch(u)) for u in apis]
    for task in asyncio.as_completed(tasks):
        res = await task
        if res:
            if res == "RATE_LIMIT": continue
            for t in tasks: t.cancel()
            return res
    return 0.0

async def get_doge_price(vs_currency="usd"):
    
    vs_curr = vs_currency.lower()
    if vs_curr != "usd":
        return await get_coingecko_price('dogecoin', vs_curr)

    apis = [
        "https://api.binance.com/api/v3/ticker/price?symbol=DOGEUSDT",
        "https://api.coingecko.com/api/v3/simple/price?ids=dogecoin&vs_currencies=usd",
        "https://min-api.cryptocompare.com/data/price?fsym=DOGE&tsyms=USD",
    ]
    session = await get_session()
    
    async def fetch(url):
        try:
            async with session.get(url, timeout=3) as r:
                if r.status == 200:
                    d = await r.json()
                    if "price" in d: return float(d["price"])
                    if "dogecoin" in d: return float(d["dogecoin"]["usd"])
                    if "USD" in d: return float(d["USD"])
                elif r.status == 429:
                    return "RATE_LIMIT"
        except: pass
        return None

    tasks = [asyncio.create_task(fetch(u)) for u in apis]
    for task in asyncio.as_completed(tasks):
        res = await task
        if res:
            if res == "RATE_LIMIT": continue
            for t in tasks: t.cancel()
            return res
    return 0.0

async def get_trx_price(vs_currency="usd"):
    
    vs_curr = vs_currency.lower()
    if vs_curr != "usd":
        return await get_coingecko_price('tron', vs_curr)

    apis = [
        "https://api.binance.com/api/v3/ticker/price?symbol=TRXUSDT",
        "https://api.coingecko.com/api/v3/simple/price?ids=tron&vs_currencies=usd",
        "https://min-api.cryptocompare.com/data/price?fsym=TRX&tsyms=USD",
    ]
    session = await get_session()
    
    async def fetch(url):
        try:
            async with session.get(url, timeout=3) as r:
                if r.status == 200:
                    d = await r.json()
                    if "price" in d: return float(d["price"])
                    if "tron" in d: return float(d["tron"]["usd"])
                    if "USD" in d: return float(d["USD"])
                elif r.status == 429:
                    return "RATE_LIMIT"
        except: pass
        return None

    tasks = [asyncio.create_task(fetch(u)) for u in apis]
    for task in asyncio.as_completed(tasks):
        res = await task
        if res:
            if res == "RATE_LIMIT": continue
            for t in tasks: t.cancel()
            return res
    return 0.0

async def get_cached_price(currency, vs_currency="usd"):
    
    current_time = time.time()
    curr = currency.lower()
    vs_curr = vs_currency.lower()
    
    cache_key = f"{curr}_{vs_curr}_price"
    
    if cache_key in price_cache:
        price, timestamp = price_cache[cache_key]
        if current_time - timestamp < CACHE_DURATION:
            return price
            
    
    new_price = await get_coingecko_price(curr, vs_curr)
    
    
    is_invalid = new_price is None or (isinstance(new_price, (int, float)) and new_price <= 0)
    if is_invalid or new_price == "RATE_LIMIT":
        if curr == 'ltc':
            new_price = await get_ltc_price(vs_curr)
        elif curr == 'solana':
            new_price = await get_solana_price(vs_curr)
        elif curr == 'bnb':
            new_price = await get_bnb_price(vs_curr)
        elif curr == 'ethereum':
            new_price = await get_ethereum_price(vs_curr)
        elif curr == 'btc':
            new_price = await get_btc_price(vs_curr)
        elif curr == 'doge':
            new_price = await get_doge_price(vs_curr)
        elif curr in ['tron', 'trx']:
            new_price = await get_trx_price(vs_curr)
        elif curr in ['shib', 'shiba-inu', 'shiba_inu', 'shiba inu']:
            new_price = await get_shib_price(vs_curr)
        elif curr == 'pepe':
            new_price = await get_pepe_price(vs_curr)
        elif 'usdt' in curr:
            new_price = await get_usdt_price(vs_curr)
            if (not new_price or new_price == "RATE_LIMIT") and vs_curr == "usd": new_price = 1.0
        elif 'usdc' in curr or 'usc' in curr:
            
            if vs_curr == "usd": new_price = 1.0
            else: new_price = await get_coingecko_price('usd-coin', vs_curr)
        else:
            
            new_price = await get_coingecko_price(curr, vs_curr)
            if not new_price: new_price = 0.0

    if new_price and new_price != "RATE_LIMIT" and new_price > 0:
        price_cache[cache_key] = (new_price, current_time)
        return new_price
    
    if new_price == "RATE_LIMIT":
        return "RATE_LIMIT"
        
    return 0.0

async def usd_to_currency_amount(amount_usd, currency):
    
    rate = await get_cached_price(currency, "usd")
    if rate == "RATE_LIMIT": return "RATE_LIMIT"
    if rate and rate > 0:
        result = float(amount_usd) / rate
        return round(result, 8)
    return 0.0

async def currency_to_fiat(amount, currency, vs_currency="usd"):
    
    rate = await get_cached_price(currency, vs_currency)
    if rate == "RATE_LIMIT": return "RATE_LIMIT"
    if rate and rate > 0:
        result = float(amount) * rate
        return round(result, 2)
    return 0.0

async def currency_to_usd(amount, currency):
    
    return await currency_to_fiat(amount, currency, "usd")
