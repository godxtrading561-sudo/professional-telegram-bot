import logging
import os
import tempfile
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import requests

from config import BOT_TOKEN, CHANNEL_ID, TIMEZONE, TRADING_PAIRS, SUPABASE_URL, SUPABASE_KEY
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


def send_photo(photo_path, caption):
    """Send a generated OTC chart image with the signal as its caption."""
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
    """Create a compact chart from the same completed OTC candles used by strategy."""
    recent = candles.tail(60)
    fig, ax = plt.subplots(figsize=(10, 5), dpi=140)
    ax.plot(recent["timestamp"], recent["close"], linewidth=1.8, label="Close")
    ax.set_title(f"{symbol} OTC — 1 Minute")
    ax.set_xlabel("UTC")
    ax.set_ylabel("Price")
    ax.grid(True, alpha=0.25)
    ax.legend(loc="best")
    fig.autofmt_xdate()
    fig.tight_layout()
    fd, path = tempfile.mkstemp(prefix="otc_signal_", suffix=".png")
    os.close(fd)
    fig.savefig(path, format="png")
    plt.close(fig)
    return path


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
            try:
                signal["chart_path"] = make_signal_chart(candles, symbol)
            except Exception:
                log.exception("Could not render OTC chart for %s", symbol)
            return pair, signal
    return None, None


def preflight_otc_feed():
    """Verify live OTC access and durable state storage before a session."""
    if not os.getenv("OTCHARTS_API_KEY", "").strip():
        raise RuntimeError("OTCHARTS_API_KEY is missing; refusing to use non-OTC fallback data.")
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase credentials are missing; refusing to run a session without durable state.")
    from supabase_db import get_client
    try:
        client = get_client()
        client.table("bot_state").select("session_id").limit(1).execute()
    except Exception as exc:
        raise RuntimeError(
            "Supabase preflight failed. Check bot_state table and SELECT permissions; "
            "no session was started."
        ) from exc

    last_error = None
    for pair, symbol in TRADING_PAIRS.items():
        try:
            candles = fetch_quotex_candles(symbol, limit=120)
            if candles is not None and len(candles) >= 60:
                log.info("OTCharts preflight passed for %s (%d candles).", symbol, len(candles))
                return True
        except CandleFeedError as exc:
            last_error = exc
            if "402" in str(exc):
                raise RuntimeError(
                    "Trading session safely blocked: OTCharts returned HTTP 402. "
                    "The configured account plan does not currently provide this OTC feed. "
                    "No session announcement or trading signal was sent."
                ) from exc
            log.warning("OTC preflight unavailable for %s: %s", symbol, exc)
    raise RuntimeError(
        "Trading session safely blocked: no usable Quotex OTC feed was found. "
        f"No session announcement or trading signal was sent. Last error: {last_error}"
    )


def main():
    preflight_otc_feed()
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
