# Shiny Escrow Bot

A production-ready Discord bot for cryptocurrency escrow services, supporting multiple blockchains including Litecoin, Bitcoin, Ethereum, Solana, and various stablecoins.

## Features

- **Multi-Currency Support**: LTC, BTC, ETH, SOL, BNB, MATIC, and stablecoins (USDT, USDC) across multiple networks.
- **Automated Payment Detection**: Monitors wallets and confirms transactions automatically.
- **Gamification**: User profiles with XP, streaks, achievements, and leaderboards.
- **Localization**: Multi-language support.

## Prerequisites

- Python 3.10+
- PostgreSQL (recommended) or SQLite
- Access to cryptocurrency RPC nodes (LTC, BTC, EVM chains)

## Setup

### 1. Clone the repository
```bash
git clone <repository_url>
cd eggmm
```

### 2. Create a virtual environment and install dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy the example environment file and fill in your credentials:
```bash
cp .env.example .env
```

**Required Variables:**
- `DISCORD_BOT_TOKEN`: Your Discord bot token.
- `DATABASE_URL`: PostgreSQL connection string (e.g., `postgresql://user:pass@host:5432/dbname`).
- `RPC_URL`: Litecoin RPC URL (e.g., `http://user:pass@host:port`).

**Optional Variables:**
- `LIQUIDITY_REPORT_WEBHOOK`: Discord webhook URL for hourly liquidity reports.
- `BTC_RPC_URL`, `SOLANA_RPC_URLS`, `ETH_RPC_URLS`, `BEP20_RPC_URLS`, `POLYGON_RPC_URLS`.

### 4. Run the Bot
```bash
python main.py
```

## Project Structure

```
/eggmm
├── main.py                 # Bot entry point
├── config.py               # Configuration loader
├── database.py             # Database access layer
├── crypto_utils.py         # Blockchain utilities
├── cogs/                   # Discord.py cogs (modular bot commands)
├── services/               # Business logic services
│   ├── price_service.py    # Cryptocurrency price fetching
│   ├── embed_service.py    # Discord embed generation
│   ├── fee_service.py      # Fee calculation logic
│   └── ...
```

## Security Best Practices

> [!CAUTION]
> **Private Keys**: While this bot handles cryptocurrency private keys, they are currently stored in plaintext. For production, consider implementing encryption at rest using Fernet or a Hardware Security Module (HSM).

- **Never commit your `.env` file** to version control.
- Run the bot on a secure, isolated server with limited access.

## License

Proprietary. All rights reserved.
