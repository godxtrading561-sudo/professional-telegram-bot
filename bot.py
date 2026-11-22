import os
import time
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import yfinance as yf

from signal_engine import analyze_market

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("professional-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
FORCE_SESSION = os.getenv("FORCE_SESSION", "0") == "1"
TZ = ZoneInfo("Asia/Kolkata")

SESSION_TIMES = ["09:00", "12:00", "14:00", "18:00", "23:00"]
MAX_SIGNALS = 12
SIGNAL_GAP_SECONDS = 300
RECHECK_SECONDS = 30
MAX_SESSION_MINUTES = 75
MIN_STRONG_SCORE = 5

PAIRS = [
    ("EURUSD=X", "EUR/USD"),
    ("GBPUSD=X", "GBP/USD"),
    ("USDJPY=X", "USD/JPY"),
    ("AUDCAD=X", "AUD/CAD"),
    ("EURJPY=X", "EUR/JPY"),
    ("GBPJPY=X", "GBP/JPY"),
]


def telegram(text):
    if not BOT_TOKEN or not CHANNEL_ID:
        raise RuntimeError("Set BOT_TOKEN and CHANNEL_ID in GitHub Secrets.")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }, timeout=20)
        if r.ok and r.json().get("ok"):
            return True
        log.error("Telegram error %s: %s", r.status_code, r.text[:400])
    except requests.RequestException as e:
        log.error("Telegram request failed: %s", e)
    return False


def fetch_closed_candles(ticker):
    df = yf.download(
        ticker, period="5d", interval="1m",
        progress=False, auto_adjust=False, threads=False
    )
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    cols = ["Open", "High", "Low", "Close"]
    if any(c not in df.columns for c in cols):
        return None
    df = df[cols].dropna().copy()
    df.index = pd.to_datetime(df.index, utc=True)
    now = pd.Timestamp.now(tz="UTC")
    df = df[df.index < now.floor("min")]
    if len(df) < 100 or (now - df.index[-1]).total_seconds() > 180:
        return None
    df.columns = [c.lower() for c in df.columns]
    df = df.reset_index()
    df = df.rename(columns={df.columns[0]: "timestamp"})
    return df


def best_signal():
    best_pair = None
    best_setup = None

    for ticker, label in PAIRS:
        try:
            candles = fetch_closed_candles(ticker)
            if candles is None:
                continue
            setup = analyze_market(candles)
            if not setup:
                continue
            score = int(setup.get("score", 0))
            if score < MIN_STRONG_SCORE:
                continue
            if best_setup is None or score > int(best_setup.get("score", 0)):
                best_pair = label
                best_setup = setup
        except Exception:
            log.exception("Analysis failed for %s", ticker)

    return best_pair, best_setup


def seconds_until_pre_alert():
    now = datetime.now(TZ)
