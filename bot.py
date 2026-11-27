import logging
import os
import tempfile
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests

from config import BOT_TOKEN, CHANNEL_ID, TIMEZONE, TRADING_PAIRS, SUPABASE_URL, SUPABASE_KEY
from yahoo_data import fetch_yahoo_candles, YahooDataError
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


def send_photo(photo_path, caption):
    if not BOT_TOKEN or not CHANNEL_ID:
        raise RuntimeError("BOT_TOKEN or CHANNEL_ID is missing.")
    try:
        with open(photo_path, "rb") as photo:
            response = requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={"chat_id": CHANNEL_ID, "caption": caption, "parse_mode": "HTML"},
                files={"photo": photo},
                timeout=40,
            )
        data = response.json()
        if response.ok and data.get("ok"):
            return True
        log.error("Telegram sendPhoto error: %s", data)
    except (OSError, requests.RequestException):
        log.exception("Telegram photo delivery failed")
    return False


def make_signal_chart(candles, symbol):
    recent = candles.tail(60)
    fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
    ax.plot(recent.index, recent["close"], linewidth=1.8, label="Close")
    ax.set_title(f"{symbol} FX SPOT — 1 Minute (Yahoo Finance)")
    ax.set_xlabel("UTC")
    ax.set_ylabel("Price")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.autofmt_xdate()
    fig.tight_layout()
    fd, path = tempfile.mkstemp(prefix="fx_signal_", suffix=".png")
    os.close(fd)
    fig.savefig(path, format="png")
    plt.close(fig)
    return path


def find_signal():
    for pair, ticker in TRADING_PAIRS.items():
        try:
            candles = fetch_yahoo_candles(ticker, period="2d", interval="1m")
        except YahooDataError as exc:
            log.warning("Yahoo data unavailable for %s: %s", pair, exc)
            continue
        if candles.empty:
            continue
        signal = analyze_market(candles)
        if signal:
            signal["ticker"] = ticker
            signal["candle_time"] = candles.index[-1].isoformat()
            try:
                signal["chart_path"] = make_signal_chart(candles, pair)
            except Exception:
                log.exception("Could not render FX chart for %s", pair)
            return pair, signal
    return None, None


def preflight_data_and_state():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase credentials are missing; refusing to start without durable state.")
    from supabase_db import get_client
    try:
        client = get_client()
        client.table("bot_state").select("session_id").limit(1).execute()
    except Exception as exc:
        raise RuntimeError("Supabase preflight failed; no session was started.") from exc

    errors = []
    for pair, ticker in TRADING_PAIRS.items():
        try:
            candles = fetch_yahoo_candles(ticker, period="2d", interval="1m")
            if len(candles) >= 60:
                log.info("Yahoo FX preflight passed for %s (%d completed candles).", pair, len(candles))
                return True
        except YahooDataError as exc:
            errors.append(f"{pair}: {exc}")
    raise RuntimeError(
        "Yahoo Finance did not return a usable fresh 1-minute FX dataset. "
        "No session message or signal was sent. " + "; ".join(errors)
    )


def main():
    preflight_data_and_state()
    now = datetime.now(TIMEZONE)
    scheduled_cron = os.getenv("SESSION_SCHEDULE_CRON", "").strip()
    cron_to_ist = {
        "30 3 * * *": (9, 0),
        "30 6 * * *": (12, 0),
        "30 8 * * *": (14, 0),
        "30 12 * * *": (18, 0),
        "30 17 * * *": (23, 0),
    }
    if scheduled_cron in cron_to_ist:
        hour, minute = cron_to_ist[scheduled_cron]
        session_id = now.strftime("%Y-%m-%d-") + f"{hour:02d}-{minute:02d}"
    else:
        session_id = now.strftime("%Y-%m-%d-%H-%M")
    run_session(session_id=session_id, send_message=send_message, find_signal=find_signal, send_photo=send_photo)


if __name__ == "__main__":
    main()
