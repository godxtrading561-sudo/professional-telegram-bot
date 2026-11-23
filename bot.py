import os
import time
import logging
from datetime import datetime, timezone, timedelta
import pandas as pd
import yfinance as yf
import requests

from signal_engine import analyze_market

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("bot")

IST = timezone(timedelta(hours=5, minutes=30))

# Top 10 liquid forex pairs -> yfinance tickers
TOP_10_PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "AUD/CAD": "AUDCAD=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CHF": "USDCHF=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/GBP": "EURGBP=X",
}

SESSION_TIMES = ["09:00", "12:00", "14:00", "18:00", "23:00"]
MAX_RUNTIME_SECONDS = 75 * 60


def send_telegram_message(text: str) -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        logger.warning("Telegram credentials missing; skipping message.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    try:
        resp = requests.post(url, json=payload, timeout=15)
        if not resp.ok:
            logger.error("Telegram API error (%s): %s", resp.status_code, resp.text)
    except Exception as exc:
        logger.error("Failed to send Telegram message: %s", exc)


def fetch_candles(ticker: str, period: str = "2d", interval: str = "1m") -> pd.DataFrame:
    df = yf.download(
        tickers=ticker,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=False,
    )
    if df is None or df.empty:
        return pd.DataFrame()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.rename(columns=str.lower)
    needed = {"open", "high", "low", "close"}
    if not needed.issubset(df.columns):
        return pd.DataFrame()

    df = df[["open", "high", "low", "close"]].dropna()
    return df


def format_signal_message(pair: str, signal: dict, now_ist: datetime) -> str:
    direction = str(signal.get("direction", "BUY")).strip()
    score = signal.get("score", "")
    reasons = signal.get("reasons", [])

    score_line = f"\n🎯 <b>Score:</b> {score}/6" if score != "" else ""
    reasons_text = ", ".join(str(r) for r in reasons) if reasons else ""
    reasons_line = f"\n📌 <b>Confluence:</b>
