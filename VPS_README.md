# EggMM Bot - VPS Deployment Guide

## Prerequisites

- A VPS running Linux (Ubuntu/Debian recommended).
- Python 3.10 or higher.
- `pip` (Python package manager).
- A Discord Bot Token.
- RPC URLs for the blockchains you intend to support.

## Installation

1.  **Extract the Zip File**:
    ```bash
    unzip eggmiddleman_deploy.zip -d eggmiddleman
    cd eggmiddleman
    ```

2.  **Install Dependencies**:
    It is recommended to use a virtual environment.
    ```bash
    # Update system and install required build tools (Ubuntu/Debian)
    sudo apt update
    sudo apt install -y python3-dev python3-venv python3-pip build-essential libssl-dev libffi-dev

    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Configuration**:
    - Copy `.env.example` to `.env`.
    - Edit `.env` and fill in your secrets (Token, RPC URLs, API Keys).
    ```bash
    cp .env.example .env
    nano .env
    ```
    *Make sure to set `DISCORD_TOKEN` and `DATABASE_URL` if using Postgres, or ensure SQLite path is valid.*

4.  **Database**:
    - If using SQLite (default), the bot will create `eggmm.db` on first run.
    - If using PostgreSQL, ensure the database is created and `DATABASE_URL` is set.

5.  **Running the Bot**:
    - To run interactively:
      ```bash
      python3 bot.py
      ```
    - To run in the background (using systemd is recommended for production, but `nohup` works for quick testing):
      ```bash
      nohup python3 bot.py > bot.log 2>&1 &
      ```

6.  **Keeping it Running**:
    - Consider using `systemd` or `supervisor` to keep the bot running and restart it on failure.
    - Example `systemd` service file is often provided as `eggmm.service` (if included in zip).

## Troubleshooting

- **Missing Modules**: Run `pip install -r requirements.txt` again.
- **Connection Errors**: Check your `.env` for correct RPC URLs and Proxy settings if applicable.
- **Permission Errors**: Ensure the user running the bot has read/write access to the directory.
