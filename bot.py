import logging
from datetime import datetime

import requests

from config import BOT_TOKEN, CHANNEL_ID, TIMEZONE, TRADING_PAIRS
from quotex_data import fetch_quotex_candles, CandleFeedError
from signal_engine import analyze_market
from session_controller import run_session

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("professional-bot")


def send_message(message):
    if not BOT_TOKEN or not CHANNEL_ID:
        raise RuntimeError("BOT_TOKEN or CHANNEL_ID is missing.")
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHANNEL_ID, "text": message, "parse_mode": "HTML"},
            timeout=20,
        )
        data = response.json()
        if response.ok and data.get("ok"):
            return True
        log.error("Telegram error: %s", data)
    except requests.RequestException:
        log.exception("Telegram connection failed")
    return False


def fetch_candles(symbol):
    try:
        return fetch_quotex_candles(symbol)
    except CandleFeedError as exc:
        log.error("Quotex OTC feed unavailable for %s: %s", symbol, exc)
        return None


def find_signal():
    for pair, symbol in TRADING_PAIRS.items():
        candles = fetch_candles(symbol)
        if candles is None:
            continue
        signal = analyze_market(candles)
        if signal:
            return pair, signal
    return None, None


def main():
    if not __import__("os").getenv("OTCHARTS_API_KEY", "").strip():
        raise RuntimeError("OTCHARTS_API_KEY is missing; refusing to use non-OTC fallback data.")
    now = datetime.now(TIMEZONE)
    session_id = now.strftime("%Y-%m-%d-%H-%M")
    run_session(session_id=session_id, send_message=send_message, find_signal=find_signal)


if __name__ == "__main__":
    main()
