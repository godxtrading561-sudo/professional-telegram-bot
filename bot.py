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
    for ticker, label in PAIRS:
        try:
            candles = fetch_closed_candles(ticker)
            if candles is None:
                continue
            setup = analyze_market(candles)
            if setup:
                return label, setup
        except Exception:
            log.exception("Analysis failed for %s", ticker)
    return None, None


def seconds_until_pre_alert():
    now = datetime.now(TZ)
    target = now.replace(second=45, microsecond=0)
    if now >= target:
        target += timedelta(minutes=1)
    return max(0, (target - now).total_seconds())


def wait_for_pre_alert_slot():
    delay = seconds_until_pre_alert()
    if delay:
        time.sleep(delay)


def run_session(session_label):
    sent_count = 0
    last_signal_slot = None

    log.info("Session %s started (only trade signals).", session_label)

    while sent_count < MAX_SIGNALS:
        wait_for_pre_alert_slot()
        slot = datetime.now(TZ).strftime("%Y-%m-%d %H:%M")
        if slot == last_signal_slot:
            time.sleep(1)
            continue

        label, setup = best_signal()
        if not setup:
            log.info("No valid setup in pre-alert slot %s.", slot)
            time.sleep(RECHECK_SECONDS)
            continue

        next_candle_time = (
            datetime.now(TZ).replace(second=0, microsecond=0)
            + timedelta(minutes=1)
        )
        message = (
            f"⏳ <b>PRE-ALERT — TRADE #{sent_count + 1}/{MAX_SIGNALS}</b>\n"
            f"Asset: <b>{label}</b>\n"
            f"Timeframe: <b>1 Minute</b>\n"
            f"Direction: <b>{setup['direction']}</b>\n"
            f"Confluence: <b>{setup['score']}/6</b>\n"
            f"Reasons: {' + '.join(setup['reasons'])}\n"
            f"Planned entry candle: "
            f"<b>{next_candle_time.strftime('%H:%M:%S')} IST</b>"
        )

        if telegram(message):
            sent_count += 1
            last_signal_slot = slot
            log.info("Trade %d/%d sent for %s.", sent_count, MAX_SIGNALS, label)
            if sent_count >= MAX_SIGNALS:
                break
            time.sleep(SIGNAL_GAP_SECONDS)
        else:
            log.warning("Telegram send failed; retrying next pre-alert slot.")
            time.sleep(RECHECK_SECONDS)

    log.info("Session %s finished after %d signals.", session_label, sent_count)


def main():
    if not BOT_TOKEN or not CHANNEL_ID:
        raise RuntimeError("Missing BOT_TOKEN or CHANNEL_ID secrets.")

    now = datetime.now(TZ)
    current = now.strftime("%H:%M")

    if FORCE_SESSION:
        run_session(f"MANUAL ({current} IST)")
        return

    if current not in SESSION_TIMES:
        log.info("Not a configured session start (%s IST); exiting.", current)
        return

    run_session(f"{current} IST")


if __name__ == "__main__":
    main()
