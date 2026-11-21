
import os
import time
import random
import logging
from datetime import datetime, date
from zoneinfo import ZoneInfo

import requests

# ---------- SECURE CONFIGURATION ----------

TOKEN = os.environ["BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["CHANNEL_ID"]

IST = ZoneInfo("Asia/Kolkata")

SESSION_TIMES = {"09:00", "14:00", "20:00"}
MAX_TRADES = 12
TRADE_INTERVAL = 300

# ---------- LOGGING ----------

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("professional_bot")

# Never log the bot token.
session_history = set()

# ---------- EXISTING SIGNAL OPTIONS ----------
# Selection logic intentionally preserved.

ASSETS = [
    "EUR/USD (OTC)",
    "GBP/USD (OTC)",
    "USD/JPY (OTC)",
    "AUD/CAD (OTC)",
    "EUR/JPY (OTC)",
    "GBP/JPY (OTC)",
]

SNR_ZONES = [
    "Support Bounce + SBR",
    "Resistance Rejection + RBS",
    "Order Block + Liquidity Sweep",
    "Key Price Level Rejection",
]

CANDLESTICKS = [
    "Bullish Engulfing",
    "Bearish Engulfing",
    "Hammer Pin Bar",
    "Shooting Star Pin Bar",
    "Strong Rejection Wick",
]

INDICATORS = [
    "RSI(14) + EMA(9/21)",
    "Bollinger Bands + MACD",
    "EMA(9/21) Pullback + RSI(14)",
    "MACD + Bollinger Rejection",
]

MOS_RULES = [
    "Wait for pullback to SNR / MOS",
    "Enter with strict MOS & No Martingale",
    "Confirm rejection wick before entry",
]

# ---------- TELEGRAM ----------

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    for attempt in range(3):
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=(10, 20),
            )

            if response.status_code == 429:
                data = response.json()
                wait = data.get("parameters", {}).get("retry_after", 5)
                time.sleep(min(int(wait), 60))
                continue

            response.raise_for_status()
            data = response.json()

            if data.get("ok") is True:
                return True

            logger.error("Telegram rejected the message.")
            return False

        except requests.RequestException:
            logger.exception(
                "Telegram delivery failed on attempt %s",
                attempt + 1,
            )

            if attempt < 2:
                time.sleep(2 ** attempt)

    return False


# ---------- SIGNAL MESSAGE ----------

def build_signal(trade_num, asset):
    # Original selection logic preserved.
    direction = random.choice(["CALL 📈 (UP)", "PUT 📉 (DOWN)"])
    snr = random.choice(SNR_ZONES)
    candle = random.choice(CANDLESTICKS)
    indicator = random.choice(INDICATORS)
    mos = random.choice(MOS_RULES)

    return (
        f"🔔 <b>TRADE #{trade_num} / 12</b>\n"
        f"Asset: <b>{asset}</b>\n"
        f"Timeframe: <b>1 Minute</b>\n"
        f"Direction: <b>{direction}</b>\n"
        f"Confluence: <b>{snr} | {candle} | {indicator}</b>\n"
        f"Accuracy: <b>Not independently verified</b>\n"
        f"MOS Rule: <b>{mos}</b>\n\n"
        "⚠️ Risk management is essential. No guaranteed result."
    )


# ---------- SESSION ----------

def run_trades(session_key):
    logger.info("Starting session %s", session_key)

    asset = random.choice(ASSETS)

    for trade_num in range(1, MAX_TRADES + 1):
        if trade_num > 1:
            time.sleep(TRADE_INTERVAL)

        current_asset = (
            asset if trade_num % 4 != 0
            else random.choice(ASSETS)
        )

        message = build_signal(trade_num, current_asset)

        if not send_telegram_message(message):
            logger.error(
                "Trade %s was not delivered. Stopping session.",
                trade_num,
            )
            break

    logger.info("Session %s finished", session_key)


def main():
    logger.info("Professional Bot started.")

    while True:
        now = datetime.now(IST)
        current_time = now.strftime("%H:%M")
        session_key = f"{now.date()}_{current_time}"

        if current_time in SESSION_TIMES and session_key not in session_history:
            # Mark before starting to prevent duplicate starts
            # during this running process.
            session_history.add(session_key)
            run_trades(session_key)

        time.sleep(5)


if __name__ == "__main__":
    main()
        
