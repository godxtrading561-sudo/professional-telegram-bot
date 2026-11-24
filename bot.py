import logging
from datetime import datetime

import pandas as pd
import requests
import yfinance as yf

from config import (
    BOT_TOKEN,
    CHANNEL_ID,
    TIMEZONE,
    TRADING_PAIRS,
)
from signal_engine import analyze_market
from session_controller import run_session

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("professional-bot")


def send_message(message):
    if not BOT_TOKEN or not CHANNEL_ID:
        raise RuntimeError("BOT_TOKEN or CHANNEL_ID is missing.")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            json={
                "chat_id": CHANNEL_ID,
                "text": message,
                "parse_mode": "HTML",
            },
            timeout=20,
        )
        data = response.json()

        if response.ok and data.get("ok"):
            return True

        log.error("Telegram error: %s", data)

    except requests.RequestException:
        log.exception("Telegram connection failed")

    return False


def fetch_candles(ticker):
    try:
        df = yf.download(
            ticker,
            period="5d",
            interval="1m",
            progress=False,
            auto_adjust=False,
            threads=False,
        )

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.columns = [str(c).lower() for c in df.columns]

        required = ["open", "high", "low", "close"]
        if not all(c in df.columns for c in required):
            return None

        df = df[required].dropna().copy()
        df.index = pd.to_datetime(df.index, utc=True)

        now = pd.Timestamp.now(tz="UTC")
        df = df[df.index < now.floor("min")]

        if len(df) < 200:
            return None

        if (now - df.index[-1]).total_seconds() > 180:
            return None

        df = df.reset_index()
        df = df.rename(columns={df.columns[0]: "timestamp"})

        return df

    except Exception:
        log.exception("Candle download failed: %s", ticker)
        return None


def find_signal():
    for pair, ticker in TRADING_PAIRS.items():
        candles = fetch_candles(ticker)

        if candles is None:
            continue

        signal = analyze_market(candles)

        if signal:
            return pair, signal

    return None, None


def main():
    now = datetime.now(TIMEZONE)
    session_id = now.strftime("%Y-%m-%d-%H-%M")

    run_session(
        session_id=session_id,
        send_message=send_message,
        find_signal=find_signal,
    )


if __name__ == "__main__":
    main()
