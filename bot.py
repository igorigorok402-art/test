import asyncio
import logging
import os
import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import aiohttp
from aiogram import Bot

TRON_USDT_CONTRACT = "TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj"
TRONGRID_BASE_URL = "https://api.trongrid.io"
DEFAULT_POLL_SECONDS = 10
DB_PATH = "state.db"


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    telegram_chat_id: str
    tron_wallet_address: str
    poll_interval_seconds: int = DEFAULT_POLL_SECONDS


def load_config() -> Config:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    wallet = os.getenv("TRON_WALLET_ADDRESS", "").strip()
    poll_seconds = int(os.getenv("POLL_INTERVAL_SECONDS", DEFAULT_POLL_SECONDS))

    missing = [
        name
        for name, value in {
            "TELEGRAM_BOT_TOKEN": token,
            "TELEGRAM_CHAT_ID": chat_id,
            "TRON_WALLET_ADDRESS": wallet,
        }.items()
        if not value
    ]
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    return Config(
        telegram_bot_token=token,
        telegram_chat_id=chat_id,
        tron_wallet_address=wallet,
        poll_interval_seconds=poll_seconds,
    )


class SeenTransactionsStore:
    def __init__(self, db_path: str = DB_PATH) -> None:
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_transactions (
                tx_id TEXT PRIMARY KEY
            )
            """
        )
        self.conn.commit()

    def is_seen(self, tx_id: str) -> bool:
        row = self.conn.execute(
            "SELECT tx_id FROM seen_transactions WHERE tx_id = ?", (tx_id,)
        ).fetchone()
        return row is not None

    def mark_seen(self, tx_id: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO seen_transactions(tx_id) VALUES (?)", (tx_id,)
        )
        self.conn.commit()


class TronUSDTWatcher:
    def __init__(
        self,
        session: aiohttp.ClientSession,
        wallet_address: str,
        store: SeenTransactionsStore,
    ) -> None:
        self.session = session
        self.wallet_address = wallet_address
        self.store = store

    async def fetch_new_incoming(self) -> list[dict[str, Any]]:
        url = f"{TRONGRID_BASE_URL}/v1/accounts/{self.wallet_address}/transactions/trc20"
        params = {
            "limit": 50,
            "only_to": "true",
            "contract_address": TRON_USDT_CONTRACT,
            "order_by": "block_timestamp,desc",
        }
        async with self.session.get(url, params=params, timeout=30) as response:
            response.raise_for_status()
            payload = await response.json()

        transactions: list[dict[str, Any]] = payload.get("data", [])

        new_items: list[dict[str, Any]] = []
        for tx in reversed(transactions):
            tx_id = tx.get("transaction_id")
            if not tx_id:
                continue
            if self.store.is_seen(tx_id):
                continue
            self.store.mark_seen(tx_id)
            new_items.append(tx)

        return new_items


def format_amount(raw_value: str, decimals: int = 6) -> str:
    amount = Decimal(raw_value) / (Decimal(10) ** decimals)
    return f"{amount:.2f}"


def build_notification(tx: dict[str, Any]) -> str:
    tx_id = tx.get("transaction_id", "unknown")
    from_address = tx.get("from", "unknown")
    to_address = tx.get("to", "unknown")
    raw_value = tx.get("value", "0")
    amount = format_amount(raw_value)
    timestamp_ms = tx.get("block_timestamp")

    lines = [
        "💸 Входящее поступление USDT (TRC-20)",
        f"Сумма: {amount} USDT",
        f"От: <code>{from_address}</code>",
        f"Куда: <code>{to_address}</code>",
        f"TxID: <code>{tx_id}</code>",
    ]
    if timestamp_ms:
        lines.append(f"Время (ms): {timestamp_ms}")

    lines.append(f"Tronscan: https://tronscan.org/#/transaction/{tx_id}")
    return "\n".join(lines)


async def run() -> None:
    config = load_config()

    logging.info("Starting watcher for wallet %s", config.tron_wallet_address)

    store = SeenTransactionsStore()
    bot = Bot(token=config.telegram_bot_token)

    async with aiohttp.ClientSession() as session:
        watcher = TronUSDTWatcher(session, config.tron_wallet_address, store)

        initialized = False

        while True:
            try:
                new_transactions = await watcher.fetch_new_incoming()

                if not initialized:
                    initialized = True
                    if new_transactions:
                        logging.info("Initialized with %s already-known transactions", len(new_transactions))
                    await asyncio.sleep(config.poll_interval_seconds)
                    continue

                for tx in new_transactions:
                    text = build_notification(tx)
                    await bot.send_message(
                        chat_id=config.telegram_chat_id,
                        text=text,
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
                    logging.info("Sent notification for tx %s", tx.get("transaction_id"))
            except Exception:
                logging.exception("Polling error")

            await asyncio.sleep(config.poll_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run())
