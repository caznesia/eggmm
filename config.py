import os
from dotenv import load_dotenv

load_dotenv()


TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_IDS = [int(x) for x in os.getenv("OWNER_IDS", "0").split(",") if x.strip().isdigit()]
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()



CHANNEL_ID = int(os.getenv("CHANNEL_ID", "1456658196247744543"))
CATEGORY_ID_1 = int(os.getenv("CATEGORY_ID_1", "1456657580674912256"))
CATEGORY_ID_2 = int(os.getenv("CATEGORY_ID_2", "0"))
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL_ID", "1456661028841721939"))
HISTORY_CHANNEL = int(os.getenv("HISTORY_CHANNEL_ID", "1456661028841721939"))
SUPPORT_CHANNEL_ID = int(os.getenv("SUPPORT_CHANNEL_ID", "1456661028841721939")) 
CONTACT_MOD_LOG_CHANNEL_ID = int(os.getenv("CONTACT_MOD_LOG_CHANNEL_ID", "0"))
PUBLIC_LOG_CHANNEL_ID = os.getenv("PUBLIC_LOG_CHANNEL_ID")


EXECUTIVE_ROLE_ID = int(os.getenv("EXECUTIVE_ROLE_ID", "0"))


MIN_DEAL_USD = float(os.getenv("MIN_DEAL_USD", "0.1"))
MAX_DEAL_USD = float(os.getenv("MAX_DEAL_USD", "100000"))
APPEAL_LINK = os.getenv("APPEAL_LINK", "https://discord.com/channels/1428193038588579880")
BANNER_BG_COLOR = os.getenv("BANNER_BG_COLOR", "#2B2D31") 
BANNER_THEME_COLOR = os.getenv("BANNER_THEME_COLOR", "#22C55E") 


BOT_LOGO_URL = os.getenv("BOT_LOGO_URL", "https://cdn.discordapp.com/attachments/1383487913186169032/1384932699717898300/Untitled-2.png")
COLOR_MAIN = int(os.getenv("BOT_COLOR_HEX", "0000ff").replace("#", ""), 16)
BOT_STATUS_TEXT = os.getenv("BOT_STATUS_TEXT", "Secure Middleman Services")
BOT_STATUS_TYPE = os.getenv("BOT_STATUS_TYPE", "watching").lower() 


PROXY = None


EMOJI_MAPPING = {
    'ltc': os.getenv("EMOJI_LTC", "<:litecoin:1463098611029246013>"),
    'btc': os.getenv("EMOJI_BTC", "<:bitcoin:1463096676352000056>"),
    'bitcoin': os.getenv("EMOJI_BTC", "<:bitcoin:1463096676352000056>"),
    'ethereum': os.getenv("EMOJI_ETH", "<:ethereum:1463096760363782309>"),
    'eth': os.getenv("EMOJI_ETH", "<:ethereum:1463096760363782309>"),
    'bnb': os.getenv("EMOJI_BNB", "<:bnb:1463096963561029808>"),
    'solana': os.getenv("EMOJI_SOL", "<:solana:1463096910423523513>"),
    'sol': os.getenv("EMOJI_SOL", "<:solana:1463096910423523513>"),
    'usdt_erc20': os.getenv("EMOJI_USDT_ERC20", "<:usdt_eth:1463575840313839626>"),
    'usdt_bep20': os.getenv("EMOJI_USDT_BSC", "<:usdt_bnb:1463575883309912156>"),
    'usdt_polygon': os.getenv("EMOJI_USDT_POLYGON", "<:usdt_pol:1463575863235706974>"),
    'usdt_solana': os.getenv("EMOJI_USDT_SOLANA", "<:usdt_sol:1463575816679067751>"),
    'usdc_erc20': os.getenv("EMOJI_USDC_ERC20", "<:usdc_eth:1463575717420732446>"),
    'usdc_bep20': os.getenv("EMOJI_USDC_BSC", "<:usdc_bnb:1463575672046747843>"),
    'usdc_polygon': os.getenv("EMOJI_USDC_POLYGON", "<:usdc_pol:1463575695731982376>"),
    'usdc_solana': os.getenv("EMOJI_USDC_SOLANA", "<:usdcsol:1463575646801367277>"),
    'usdc_base': os.getenv("EMOJI_USDC_BASE", "<:usdc_base:1463575931716374528>"),
    'base': os.getenv("EMOJI_BASE", "<:base:1463105454828945489>"),
    'shib': os.getenv("EMOJI_SHIB", "<:shibainu:1463097215097507996>"),
    'pepe': os.getenv("EMOJI_PEPE", "<:pepe:1463097443024375911>"),
    'wif': os.getenv("EMOJI_WIF", "🎩"),
    'bonk': os.getenv("EMOJI_BONK", "🦴"),
    'doge': os.getenv("EMOJI_DOGE", "<:dogecoin:1463097010138906708>"),
    'xrp': os.getenv("EMOJI_XRP", "✖️"),
    'ada': os.getenv("EMOJI_ADA", "🅰️"),
    'ton': os.getenv("EMOJI_TON", "💎"),
    'xmr': os.getenv("EMOJI_XMR", "🕵️"),
    'tron': os.getenv("EMOJI_TRON", "<:tron:1463097110822916228>"),
    'trx': os.getenv("EMOJI_TRON", "<:tron:1463097110822916228>"),
    'usdt_trc20': os.getenv("EMOJI_USDT_TRC20", os.getenv("EMOJI_USDT", "<:tether:1463096853498302669>")),
    'usdt_arbitrum': os.getenv("EMOJI_USDT_ARB", "<:usdt_arbitrum:1463575903228661966>"),
    'usdc_arbitrum': os.getenv("EMOJI_USDC_ARB", "<:usdcarbitrum:1463575614152904940>"),
    'usdt_optimism': os.getenv("EMOJI_USDT_OP", "<:usdt_op:1463575979330109607>"),
    'usdc_optimism': os.getenv("EMOJI_USDC_OP", "<:usdc_op:1463575767551049963>"),
    'usdt_avalanche': os.getenv("EMOJI_USDT_AVAX", "<:usdt_ava:1463575789672075451>"),
    'usdc_avalanche': os.getenv("EMOJI_USDC_AVAX", "<:usdc_ava:1463575743702499419>"),
    'polygon': os.getenv("EMOJI_POLYGON", "<:polygon:1463098011872788583>"),
    'arbitrum': os.getenv("EMOJI_ARB", "<:arbitrum:1463097520577183823>"),
    'avalanche': os.getenv("EMOJI_AVAX", "<:avalanche:1463097158180798550>"),
    'optimism': os.getenv("EMOJI_OP", "<:optimismethereum:1463097797745180869>"),
}







LTC_RPC_URL = os.getenv("LTC_RPC_URL")
if not LTC_RPC_URL:
    RPC_USER = os.getenv("LTC_RPC_USER", "rainyday")
    RPC_PASSWORD = os.getenv("LTC_RPC_PASSWORD", "")
    RPC_HOST = os.getenv("LTC_RPC_HOST", "127.0.0.1")
    RPC_PORT = int(os.getenv("LTC_RPC_PORT", "9332"))
    RPC_URL = f"http://{RPC_USER}:{RPC_PASSWORD}@{RPC_HOST}:{RPC_PORT}"
else:
    RPC_URL = LTC_RPC_URL


ETH_RPC_URLS = [
    url.strip() for url in os.getenv("ETH_RPC_URLS", "https://eth.drpc.org,https://rpc.ankr.com/eth,https://ethereum-rpc.publicnode.com,https://1rpc.io/eth").split(",")
]
ETH_DECIMALS = 18


BSC_RPC = os.getenv("BSC_RPC", "https://bsc-dataseed.binance.org/")
BEP20_RPC_URLS = [
    url.strip() for url in os.getenv("BSC_RPC_URLS", "https://bsc-dataseed.binance.org,https://bsc.drpc.org,https://bsc-dataseed1.ninicoin.io,https://bsc-dataseed1.defibit.io,https://1rpc.io/bnb").split(",")
]
USDT_BEP20_CONTRACT = os.getenv("USDT_BEP20_CONTRACT", "0x55d398326f99059fF775485246999027B3197955")
USDT_BEP20_DECIMALS = 18
BEP20_GAS_REQUIRED = float(os.getenv("BEP20_GAS_REQUIRED", "0.00003"))


POLYGON_RPC = os.getenv("POLYGON_RPC", "https://polygon.llamarpc.com")
POLYGON_RPC_URLS = [
    url.strip() for url in os.getenv("POLYGON_RPC_URLS", "https://polygon.drpc.org,https://1rpc.io/matic,https://rpc.ankr.com/polygon,https://polygon-rpc.com").split(",")
]
USDT_POLYGON_CONTRACT = os.getenv("USDT_POLYGON_CONTRACT", "0xc2132D05D31c914a87C6611C10748AEb04B58e8F")
USDT_POLYGON_DECIMALS = 6
POLYGON_GAS_REQUIRED = float(os.getenv("POLYGON_GAS_REQUIRED", "0.7"))  
ETH_GAS_FALLBACK = float(os.getenv("ETH_GAS_FALLBACK", "0.005"))
BASE_GAS_FALLBACK = float(os.getenv("BASE_GAS_FALLBACK", "0.0005"))
ARB_GAS_FALLBACK = float(os.getenv("ARB_GAS_FALLBACK", "0.0005"))
OP_GAS_FALLBACK = float(os.getenv("OP_GAS_FALLBACK", "0.0005"))
AVAX_GAS_FALLBACK = float(os.getenv("AVAX_GAS_FALLBACK", "0.05"))


GAS_LIMIT_ETH = int(os.getenv("GAS_LIMIT_ETH", "21000"))
GAS_LIMIT_TOKEN = int(os.getenv("GAS_LIMIT_TOKEN", "65000"))


GAS_MULTIPLIER_ETH = float(os.getenv("GAS_MULTIPLIER_ETH", "1.5"))
GAS_MULTIPLIER_L2 = float(os.getenv("GAS_MULTIPLIER_L2", "1.8"))


LTC_CONF_TARGET = int(os.getenv("LTC_CONF_TARGET", "2"))
BTC_CONF_TARGET = int(os.getenv("BTC_CONF_TARGET", "2"))
ETH_CONF_TARGET = int(os.getenv("ETH_CONF_TARGET", "2"))
BSC_CONF_TARGET = int(os.getenv("BSC_CONF_TARGET", "2"))
POLYGON_CONF_TARGET = int(os.getenv("POLYGON_CONF_TARGET", "1"))
SOLANA_CONF_TARGET = int(os.getenv("SOLANA_CONF_TARGET", "2"))
DOGE_CONF_TARGET = int(os.getenv("DOGE_CONF_TARGET", "4"))
BASE_CONF_TARGET = int(os.getenv("BASE_CONF_TARGET", "2"))
ARB_CONF_TARGET = int(os.getenv("ARB_CONF_TARGET", "2"))
OP_CONF_TARGET = int(os.getenv("OP_CONF_TARGET", "2"))
AVAX_CONF_TARGET = int(os.getenv("AVAX_CONF_TARGET", "2"))


SOLANA_RPC_URLS = [
    url.strip() for url in os.getenv("SOLANA_RPC_URLS", "https://solana-rpc.publicnode.com,https://api.mainnet-beta.solana.com,https://solana.drpc.org,https://rpc.ankr.com/solana").split(",")
]


BASE_RPC = os.getenv("BASE_RPC", "https://mainnet.base.org")
BASE_RPC_URLS = [
    url.strip() for url in os.getenv("BASE_RPC_URLS", "https://mainnet.base.org,https://1rpc.io/base,https://base.llamarpc.com").split(",")
]


ARBITRUM_RPC = os.getenv("ARBITRUM_RPC", "https://arb1.arbitrum.io/rpc")
ARBITRUM_RPC_URLS = [
    url.strip() for url in os.getenv("ARBITRUM_RPC_URLS", "https://arb1.arbitrum.io/rpc,https://1rpc.io/arb,https://arbitrum.llamarpc.com").split(",")
]


OPTIMISM_RPC = os.getenv("OPTIMISM_RPC", "https://mainnet.optimism.io")
OPTIMISM_RPC_URLS = [
    url.strip() for url in os.getenv("OPTIMISM_RPC_URLS", "https://mainnet.optimism.io,https://1rpc.io/op,https://optimism.llamarpc.com").split(",")
]


AVALANCHE_RPC = os.getenv("AVALANCHE_RPC", "https://api.avax.network/ext/bc/C/rpc")
AVALANCHE_RPC_URLS = [
    url.strip() for url in os.getenv("AVALANCHE_RPC_URLS", "https://api.avax.network/ext/bc/C/rpc,https://1rpc.io/avax/c,https://avalanche.llamarpc.com").split(",")
]


EXPLORER_URLS = {
    'polygon': os.getenv("EXPLORER_POLYGON", "https://polygonscan.com/tx/"),
    'bsc': os.getenv("EXPLORER_BSC", "https://bscscan.com/tx/"),
    'ltc': os.getenv("EXPLORER_LTC", "https://blockchair.com/litecoin/transaction/"),
    'btc': os.getenv("EXPLORER_BTC", "https://blockchair.com/bitcoin/transaction/"),
    'sol': os.getenv("EXPLORER_SOLANA", "https://solscan.io/tx/"),
    'eth': os.getenv("EXPLORER_ETH", "https://etherscan.io/tx/"),
    'base': os.getenv("EXPLORER_BASE", "https://basescan.org/tx/"),
    'arbitrum': os.getenv("EXPLORER_ARBITRUM", "https://arbiscan.io/tx/"),
    'optimism': os.getenv("EXPLORER_OPTIMISM", "https://optimistic.etherscan.io/tx/"),
    'avalanche': os.getenv("EXPLORER_AVAX", "https://snowtrace.io/tx/"),
    'doge': os.getenv("EXPLORER_DOGE", "https://dogechain.info/tx/"),
}


BTC_RPC_USER = os.getenv("BTC_RPC_USER", "rainyday")
BTC_RPC_PASSWORD = os.getenv("BTC_RPC_PASSWORD", "")
BTC_RPC_HOST = os.getenv("BTC_RPC_HOST", "127.0.0.1")
BTC_RPC_PORT = int(os.getenv("BTC_RPC_PORT", "8332"))
_btc_url_env = os.getenv("BTC_RPC_URL")
if _btc_url_env:
    BTC_RPC_URL = _btc_url_env
else:
    BTC_RPC_URL = f"http://{BTC_RPC_USER}:{BTC_RPC_PASSWORD}@{BTC_RPC_HOST}:{BTC_RPC_PORT}"


DOGE_RPC_URL = os.getenv("DOGE_RPC_URL", "https://rpc.coinsdo.net/doge")
DOGE_RPC_USER = os.getenv("DOGE_RPC_USER", "rainyday")
DOGE_RPC_PASSWORD = os.getenv("DOGE_RPC_PASSWORD", "")
DOGE_RPC_HOST = os.getenv("DOGE_RPC_HOST", "127.0.0.1")
DOGE_RPC_PORT = int(os.getenv("DOGE_RPC_PORT", "22555"))
if "127.0.0.1" in DOGE_RPC_URL and DOGE_RPC_PASSWORD:
    
    DOGE_RPC_URL = f"http://{DOGE_RPC_USER}:{DOGE_RPC_PASSWORD}@{DOGE_RPC_HOST}:{DOGE_RPC_PORT}"


TRON_RPC_URL = os.getenv("TRON_RPC_URL", "https://api.trongrid.io")
USDT_TRC20_CONTRACT = os.getenv("USDT_TRC20_CONTRACT", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
TRON_CONF_TARGET = int(os.getenv("TRON_CONF_TARGET", "2"))


XRP_RPC_URL = os.getenv("XRP_RPC_URL", "https://s1.ripple.com:51234")
ADA_RPC_URL = os.getenv("ADA_RPC_URL", "https://rpc.coinsdo.net/ada")
TON_RPC_URL = os.getenv("TON_RPC_URL", "https://rpc.ankr.com/ton_api_v2")
XMR_RPC_URL = os.getenv("XMR_RPC_URL", "http://127.0.0.1:18081") 

XRP_CONF_TARGET = int(os.getenv("XRP_CONF_TARGET", "1"))
ADA_CONF_TARGET = int(os.getenv("ADA_CONF_TARGET", "5"))
TON_CONF_TARGET = int(os.getenv("TON_CONF_TARGET", "2"))
XMR_CONF_TARGET = int(os.getenv("XMR_CONF_TARGET", "10"))


USDT_ETH_CONTRACT = os.getenv("USDT_ETH_CONTRACT", "0xdac17f958d2ee523a2206206994597c13d831ec7")
USDT_ETH_DECIMALS = 6

USDT_SOL_CONTRACT = os.getenv("USDT_SOL_CONTRACT", "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB")
USDT_SOL_DECIMALS = 6

USDC_ETH_CONTRACT = os.getenv("USDC_ETH_CONTRACT", "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48")
USDC_ETH_DECIMALS = 6

USDC_SOL_CONTRACT = os.getenv("USDC_SOL_CONTRACT", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
USDC_SOL_DECIMALS = 6

USDC_BEP20_CONTRACT = os.getenv("USDC_BEP20_CONTRACT", "0x8ac76a51cc950d9822d68b83fe1ad97b32cd580d")
USDC_BEP20_DECIMALS = 18

USDC_POLYGON_DECIMALS = 6
USDC_POLYGON_CONTRACT = os.getenv("USDC_POLYGON_CONTRACT", "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359")

SHIB_CONTRACT = os.getenv("SHIB_CONTRACT", "0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE")
SHIB_DECIMALS = 18

PEPE_CONTRACT = os.getenv("PEPE_CONTRACT", "0x6982508145454ce325ddbe47a25d4ec3d2311933")
PEPE_DECIMALS = 18

WIF_CONTRACT = os.getenv("WIF_CONTRACT", "EKpQGSJtjMFqKZ9KQan958rCPyM4tA0-9G5F1m1Npump")
WIF_DECIMALS = 6

BONK_CONTRACT = os.getenv("BONK_CONTRACT", "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263")
BONK_DECIMALS = 5


USDC_BASE_CONTRACT = os.getenv("USDC_BASE_CONTRACT", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
USDC_BASE_DECIMALS = 6

USDT_ARB_CONTRACT = os.getenv("USDT_ARB_CONTRACT", "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9")
USDT_ARB_DECIMALS = 6
USDC_ARB_CONTRACT = os.getenv("USDC_ARB_CONTRACT", "0xaf88d065e77c8cC2239327C5EDb3A432268e5831")
USDC_ARB_DECIMALS = 6

USDT_OP_CONTRACT = os.getenv("USDT_OP_CONTRACT", "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58")
USDT_OP_DECIMALS = 6
USDC_OP_CONTRACT = os.getenv("USDC_OP_CONTRACT", "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85")
USDC_OP_DECIMALS = 6

USDT_AVAX_CONTRACT = os.getenv("USDT_AVAX_CONTRACT", "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7")
USDT_AVAX_DECIMALS = 6
USDC_AVAX_CONTRACT = os.getenv("USDC_AVAX_CONTRACT", "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E")
USDC_AVAX_DECIMALS = 6


CHAINS = {
    "usdt_bep20": {
        "rpc": BSC_RPC,
        "chain_id": 56,
        "symbol": "BNB",
        "usdt": USDT_BEP20_CONTRACT,
        "decimals": USDT_BEP20_DECIMALS,
        "solana": "So11111111111111111111111111111111111111112"
    },
    "usdt_polygon": {
        "rpc": POLYGON_RPC,
        "chain_id": 137,
        "symbol": "MATIC",
        "usdt": USDT_POLYGON_CONTRACT,
        "decimals": USDT_POLYGON_DECIMALS
    },
    "usdc_base": {
        "rpc": BASE_RPC,
        "chain_id": 8453,
        "symbol": "ETH",
        "usdc": USDC_BASE_CONTRACT,
        "decimals": USDC_BASE_DECIMALS
    },
    "usdt_arbitrum": {
        "rpc": ARBITRUM_RPC,
        "chain_id": 42161,
        "symbol": "ETH",
        "usdt": USDT_ARB_CONTRACT,
        "decimals": USDT_ARB_DECIMALS
    },
    "usdc_arbitrum": {
        "rpc": ARBITRUM_RPC,
        "chain_id": 42161,
        "symbol": "ETH",
        "usdc": USDC_ARB_CONTRACT,
        "decimals": USDC_ARB_DECIMALS
    },
    "usdt_optimism": {
        "rpc": OPTIMISM_RPC,
        "chain_id": 10,
        "symbol": "ETH",
        "usdt": USDT_OP_CONTRACT,
        "decimals": USDT_OP_DECIMALS
    },
    "usdc_optimism": {
        "rpc": OPTIMISM_RPC,
        "chain_id": 10,
        "symbol": "ETH",
        "usdc": USDC_OP_CONTRACT,
        "decimals": USDC_OP_DECIMALS
    },
    "usdt_avalanche": {
        "rpc": AVALANCHE_RPC,
        "chain_id": 43114,
        "symbol": "AVAX",
        "usdt": USDT_AVAX_CONTRACT,
        "decimals": USDT_AVAX_DECIMALS
    },
    "usdc_avalanche": {
        "rpc": AVALANCHE_RPC,
        "chain_id": 43114,
        "symbol": "AVAX",
        "usdc": USDC_AVAX_CONTRACT,
        "decimals": USDC_AVAX_DECIMALS
    },
    "shib": {
        "rpc": "https://ethereum-rpc.publicnode.com",
        "contract": SHIB_CONTRACT,
        "decimals": SHIB_DECIMALS
    },
    "pepe": {
        "rpc": "https://ethereum-rpc.publicnode.com",
        "contract": PEPE_CONTRACT,
        "decimals": PEPE_DECIMALS
    },
    "doge": {
        "rpc": DOGE_RPC_URL,
        "symbol": "DOGE",
        "decimals": 8
    }
}


USDT_ABI = [
    {
        "constant": False,
        "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    }
]


FEE_ADDRESS_USDT = os.getenv('FEE_ADDRESS_USDT')
FEE_ADDRESS_USDC = os.getenv('FEE_ADDRESS_USDC')

FEE_ADDRESSES = {
    'ltc': os.getenv('FEE_ADDRESS_LTC'),
    'btc': os.getenv('FEE_ADDRESS_BTC'),
    'bnb': os.getenv('FEE_ADDRESS_BSC'),
    'usdt_bep20': os.getenv('FEE_ADDRESS_USDT_BSC') or FEE_ADDRESS_USDT or os.getenv('FEE_ADDRESS_BSC'),
    'usdt_polygon': os.getenv('FEE_ADDRESS_USDT_POLYGON') or FEE_ADDRESS_USDT or os.getenv('FEE_ADDRESS_POLYGON'),
    'usdc_bep20': os.getenv('FEE_ADDRESS_USDC_BSC') or FEE_ADDRESS_USDC or os.getenv('FEE_ADDRESS_BSC'),
    'usdc_polygon': os.getenv('FEE_ADDRESS_USDC_POLYGON') or FEE_ADDRESS_USDC or os.getenv('FEE_ADDRESS_POLYGON'),
    'usdc_base': os.getenv('FEE_ADDRESS_USDC_BASE') or FEE_ADDRESS_USDC or os.getenv('FEE_ADDRESS_BASE') or os.getenv('FEE_ADDRESS_ETH'),
    'usdt_arbitrum': os.getenv('FEE_ADDRESS_USDT_ARB') or FEE_ADDRESS_USDT or os.getenv('FEE_ADDRESS_ARBITRUM') or os.getenv('FEE_ADDRESS_ETH'),
    'usdc_arbitrum': os.getenv('FEE_ADDRESS_USDC_ARB') or FEE_ADDRESS_USDC or os.getenv('FEE_ADDRESS_ARBITRUM') or os.getenv('FEE_ADDRESS_ETH'),
    'usdt_optimism': os.getenv('FEE_ADDRESS_USDT_OP') or FEE_ADDRESS_USDT or os.getenv('FEE_ADDRESS_OPTIMISM') or os.getenv('FEE_ADDRESS_ETH'),
    'usdc_optimism': os.getenv('FEE_ADDRESS_USDC_OP') or FEE_ADDRESS_USDC or os.getenv('FEE_ADDRESS_OPTIMISM') or os.getenv('FEE_ADDRESS_ETH'),
    'usdt_avalanche': os.getenv('FEE_ADDRESS_USDT_AVAX') or FEE_ADDRESS_USDT or os.getenv('FEE_ADDRESS_AVAX'),
    'usdc_avalanche': os.getenv('FEE_ADDRESS_USDC_AVAX') or FEE_ADDRESS_USDC or os.getenv('FEE_ADDRESS_AVAX'),
    'solana': os.getenv('FEE_ADDRESS_SOL'),
    'sol': os.getenv('FEE_ADDRESS_SOL'),
    'ethereum': os.getenv('FEE_ADDRESS_ETH'),
    'eth': os.getenv('FEE_ADDRESS_ETH'),
    'usdt_erc20': os.getenv('FEE_ADDRESS_USDT_ERC20') or FEE_ADDRESS_USDT or os.getenv('FEE_ADDRESS_ETH'),
    'usdc_erc20': os.getenv('FEE_ADDRESS_USDC_ERC20') or FEE_ADDRESS_USDC or os.getenv('FEE_ADDRESS_ETH'),
    'usdt_solana': os.getenv('FEE_ADDRESS_USDT_SOLANA') or FEE_ADDRESS_USDT or os.getenv('FEE_ADDRESS_SOL'),
    'usdc_solana': os.getenv('FEE_ADDRESS_USDC_SOLANA') or FEE_ADDRESS_USDC or os.getenv('FEE_ADDRESS_SOL'),
    'shib': os.getenv('FEE_ADDRESS_ETH'),
    'pepe': os.getenv('FEE_ADDRESS_ETH'),
    'wif': os.getenv('FEE_ADDRESS_SOL'),
    'bonk': os.getenv('FEE_ADDRESS_SOL'),
    'doge': os.getenv('FEE_ADDRESS_DOGE'),
    'tron': os.getenv('FEE_ADDRESS_TRON'),
    'trx': os.getenv('FEE_ADDRESS_TRON'),
    'usdt_trc20': os.getenv('FEE_ADDRESS_TRC20') or os.getenv('FEE_ADDRESS_TRON'),
    'xrp': os.getenv('FEE_ADDRESS_XRP'),
    'ada': os.getenv('FEE_ADDRESS_ADA'),
    'ton': os.getenv('FEE_ADDRESS_TON'),
    'xmr': os.getenv('FEE_ADDRESS_XMR'),
}


DUST_SWEEP_ADDRESS = os.getenv('DUST_SWEEP_ADDRESS')
DUST_SWEEP_ADDRESS_ETH = os.getenv('DUST_SWEEP_ADDRESS_ETH', DUST_SWEEP_ADDRESS)
DUST_SWEEP_ADDRESS_BSC = os.getenv('DUST_SWEEP_ADDRESS_BSC', DUST_SWEEP_ADDRESS)
DUST_SWEEP_ADDRESS_POLYGON = os.getenv('DUST_SWEEP_ADDRESS_POLYGON', DUST_SWEEP_ADDRESS)
DUST_SWEEP_ADDRESS_BASE = os.getenv('DUST_SWEEP_ADDRESS_BASE', DUST_SWEEP_ADDRESS)
DUST_SWEEP_ADDRESS_ARBITRUM = os.getenv('DUST_SWEEP_ADDRESS_ARBITRUM', DUST_SWEEP_ADDRESS)
DUST_SWEEP_ADDRESS_OPTIMISM = os.getenv('DUST_SWEEP_ADDRESS_OPTIMISM', DUST_SWEEP_ADDRESS)
DUST_SWEEP_ADDRESS_AVALANCHE = os.getenv('DUST_SWEEP_ADDRESS_AVALANCHE', DUST_SWEEP_ADDRESS)
DUST_SWEEP_ADDRESS_SOLANA = os.getenv('DUST_SWEEP_ADDRESS_SOLANA', DUST_SWEEP_ADDRESS)


GAS_SOURCE_PRIVATE_KEY_ETH = os.getenv('GAS_SOURCE_PRIVATE_KEY_ETH')
GAS_SOURCE_PRIVATE_KEY_BSC = os.getenv('GAS_SOURCE_PRIVATE_KEY_BSC')
GAS_SOURCE_PRIVATE_KEY_POLYGON = os.getenv('GAS_SOURCE_PRIVATE_KEY_POLYGON')
GAS_SOURCE_PRIVATE_KEY_BASE = os.getenv('GAS_SOURCE_PRIVATE_KEY_BASE')
GAS_SOURCE_PRIVATE_KEY_ARBITRUM = os.getenv('GAS_SOURCE_PRIVATE_KEY_ARBITRUM')
GAS_SOURCE_PRIVATE_KEY_OPTIMISM = os.getenv('GAS_SOURCE_PRIVATE_KEY_OPTIMISM')
GAS_SOURCE_PRIVATE_KEY_AVALANCHE = os.getenv('GAS_SOURCE_PRIVATE_KEY_AVALANCHE')


VC_STATS_CHANNEL_ID = os.getenv('VC_STATS_CHANNEL_ID', '1456697637821616384')


CLIENT_ROLE_ID = int(os.getenv('CLIENT_ROLE_ID', '0'))


IDLE_TIMEOUT = int(os.getenv('IDLE_TIMEOUT', '3600')) 
FINALIZED_TIMEOUT = int(os.getenv('FINALIZED_TIMEOUT', '100')) 


AUTO_GAS_BUFFER = float(os.getenv('AUTO_GAS_BUFFER', '1.05')) 



DATABASE_URL_ENV = os.getenv("DATABASE_URL")
DB_TYPE = os.getenv("RAINYDAY_DB_TYPE", "postgres" if DATABASE_URL_ENV and "postgres" in DATABASE_URL_ENV else "sqlite")
DB_PATH = os.getenv("RAINYDAY_DB_PATH", "rainyday.db")


AUTO_SWEEP_ENABLED = True
AUTO_SWEEP_INTERVAL_HOURS = 6.0
AUTO_SWEEP_THRESHOLD_USD = 1000.0
AUTO_SWEEP_WEBHOOK = "https://discord.com/api/webhooks/1464218953629958258/NCPPAxoExz-YDOmprCXGVtV1bzfQ_oGRuP0DLaBSxGDU4JKkMDqAQemKUYzo8Ia23lIp"


TATUM_API_KEY = os.getenv('TATUM_API_KEY')
BLOCKCHAIR_API_KEY = os.getenv('BLOCKCHAIR_API_KEY')


FEES_ENABLED = os.getenv('FEES_ENABLED', 'false').lower() == 'true'
FEES_PERCENTAGE = float(os.getenv('FEES_PERCENTAGE', '0'))


CRYPTO_FEES = {
    'ltc': float(os.getenv('FEE_PERCENT_LTC', FEES_PERCENTAGE)),
    'eth': float(os.getenv('FEE_PERCENT_ETH', FEES_PERCENTAGE)),
    'ethereum': float(os.getenv('FEE_PERCENT_ETH', FEES_PERCENTAGE)),
    'btc': float(os.getenv('FEE_PERCENT_BTC', FEES_PERCENTAGE)),
    'bitcoin': float(os.getenv('FEE_PERCENT_BTC', FEES_PERCENTAGE)),
    'sol': float(os.getenv('FEE_PERCENT_SOL', FEES_PERCENTAGE)),
    'doge': float(os.getenv('FEE_PERCENT_DOGE', FEES_PERCENTAGE)),
    'solana': float(os.getenv('FEE_PERCENT_SOL', FEES_PERCENTAGE)),
    'bnb': float(os.getenv('FEE_PERCENT_BSC', FEES_PERCENTAGE)),
    'usdt_bep20': float(os.getenv('FEE_PERCENT_BSC', FEES_PERCENTAGE)),
    'usdt_polygon': float(os.getenv('FEE_PERCENT_POLYGON', FEES_PERCENTAGE)),
    'usdc_bep20': float(os.getenv('FEE_PERCENT_BSC', FEES_PERCENTAGE)),
    'usdc_polygon': float(os.getenv('FEE_PERCENT_POLYGON', FEES_PERCENTAGE)),
    'usdb': float(os.getenv('FEE_PERCENT_BASE', os.getenv('FEE_PERCENT_ETH', FEES_PERCENTAGE))),
    'tron': float(os.getenv('FEE_PERCENT_TRON', FEES_PERCENTAGE)),
    'usdt_trc20': float(os.getenv('FEE_PERCENT_TRON', FEES_PERCENTAGE)),
    'xrp': float(os.getenv('FEE_PERCENT_XRP', FEES_PERCENTAGE)),
    'ada': float(os.getenv('FEE_PERCENT_ADA', FEES_PERCENTAGE)),
    'ton': float(os.getenv('FEE_PERCENT_TON', FEES_PERCENTAGE)),
    'xmr': float(os.getenv('FEE_PERCENT_XMR', FEES_PERCENTAGE)),
    'usdt_arbitrum': float(os.getenv('FEE_PERCENT_ARBITRUM', os.getenv('FEE_PERCENT_ETH', FEES_PERCENTAGE))),
    'usdc_arbitrum': float(os.getenv('FEE_PERCENT_ARBITRUM', os.getenv('FEE_PERCENT_ETH', FEES_PERCENTAGE))),
    'usdt_optimism': float(os.getenv('FEE_PERCENT_OPTIMISM', os.getenv('FEE_PERCENT_ETH', FEES_PERCENTAGE))),
    'usdc_optimism': float(os.getenv('FEE_PERCENT_OPTIMISM', os.getenv('FEE_PERCENT_ETH', FEES_PERCENTAGE))),
    'usdt_avalanche': float(os.getenv('FEE_PERCENT_AVAX', FEES_PERCENTAGE)),
    'usdc_avalanche': float(os.getenv('FEE_PERCENT_AVAX', FEES_PERCENTAGE)),
    'usdt_erc20': float(os.getenv('FEE_PERCENT_ETH', FEES_PERCENTAGE)),
    'usdc_erc20': float(os.getenv('FEE_PERCENT_ETH', FEES_PERCENTAGE)),
    'usdt_solana': float(os.getenv('FEE_PERCENT_SOL', FEES_PERCENTAGE)),
    'usdc_solana': float(os.getenv('FEE_PERCENT_SOL', FEES_PERCENTAGE)),
}


VERIFIED_ICON_URL = os.getenv("VERIFIED_ICON_URL", "https://cdn.discordapp.com/emojis/1321450257917251706.png?v=1")


USDT_ABI = [
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"},
    {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"}
]
