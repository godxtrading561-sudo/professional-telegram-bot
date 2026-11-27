import logging
import os
import tempfile
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import requests

from config import BOT_TOKEN, CHANNEL_ID, TIMEZONE, SUPABASE_URL, SUPABASE_KEY
from otc_data import fetch_quotex_otc_candles, QuotexOTCDataError, DEFAULT_SYMBOL
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
    """Render real OHLC candlesticks (not a close-price line) for the OTC feed."""
    from matplotlib.patches import Rectangle
    import matplotlib.dates as mdates

    recent = candles.tail(60).copy()
    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=160)
    x_values = mdates.date2num(recent.index.to_pydatetime())
    candle_width = 0.72 / (24 * 60)  # 0.72 of one minute, in Matplotlib date units

    for x, (_, candle) in zip(x_values, recent.iterrows()):
        open_price = float(candle["open"])
        high_price = float(candle["high"])
        low_price = float(candle["low"])
        close_price = float(candle["close"])
        rising = close_price >= open_price
        candle_color = "#16a34a" if rising else "#dc2626"

        # High-low wick and open-close candle body.
        ax.vlines(x, low_price, high_price, color=candle_color, linewidth=1.0, zorder=2)
        body_bottom = min(open_price, close_price)
        body_height = abs(close_price - open_price)
        if body_height == 0:
            body_height = max((high_price - low_price) * 0.015, 1e-9)
        ax.add_patch(Rectangle(
            (x - candle_width / 2, body_bottom),
            candle_width,
            body_height,
            facecolor=candle_color,
            edgecolor=candle_color,
            linewidth=0.7,
            zorder=3,
        ))

    ax.set_title(f"{symbol} — QUOTEX OTC — 1 MIN CANDLE CHART", pad=12, fontweight="bold")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel("OTC Price")
    ax.xaxis_date()
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M", tz=recent.index.tz))
    ax.grid(True, alpha=0.22, linestyle="--")
    ax.margins(x=0.025)
    fig.autofmt_xdate()
    fig.tight_layout()

    fd, path = tempfile.mkstemp(prefix="otc_signal_", suffix=".png")
    os.close(fd)
    try:
        fig.savefig(path, format="png", facecolor="white")
    finally:
        plt.close(fig)
    return path


def find_signal():
    # Propagate provider failures so the session closes immediately instead of
    # silently waiting/retrying for 90 minutes with no verified OTC feed.
    candles = fetch_quotex_otc_candles(DEFAULT_SYMBOL, limit=180)
    signal = analyze_market(candles)
    if not signal:
        return None, None
    signal["ticker"] = DEFAULT_SYMBOL
    signal["candle_time"] = candles.index[-1].isoformat()
    try:
        signal["chart_path"] = make_signal_chart(candles, DEFAULT_SYMBOL)
    except Exception:
        log.exception("Could not render Quotex OTC chart")
    return DEFAULT_SYMBOL, signal


def preflight_data_and_state():
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Supabase credentials are missing; refusing to start without durable state.")
    from supabase_db import get_client
    try:
        client = get_client()
        client.table("bot_state").select("session_id").limit(1).execute()
    except Exception as exc:
        raise RuntimeError("Supabase preflight failed; no session was started.") from exc

    try:
        candles = fetch_quotex_otc_candles(DEFAULT_SYMBOL, limit=180)
    except QuotexOTCDataError as exc:
        raise RuntimeError(
            "Quotex OTC feed unavailable. Session safely cancelled; no Yahoo FX spot fallback is allowed. "
            + str(exc)
        ) from exc
    log.info("Quotex OTC preflight passed for %s (%d completed candles).", DEFAULT_SYMBOL, len(candles))
    return True


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
