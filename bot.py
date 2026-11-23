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
    direction = str(signal.get("direction", signal.get("side", "BUY"))).upper()
    expiry = signal.get("expiry", "1M")
    confidence = signal.get("confidence", signal.get("score", ""))
    conf_line = f"\n🎯 <b>Filter:</b> {confidence}" if confidence != "" else ""

    return (
        f"⚡ <b>LIVE FOREX SIGNAL</b> ⚡\n\n"
        f"💱 <b>Pair:</b> {pair}\n"
        f"📊 <b>Direction:</b> {direction}\n"
        f"⏳ <b>Expiry:</b> {expiry}"
        f"{conf_line}\n"
        f"🕒 <b>Time (IST):</b> {now_ist.strftime('%H:%M:%S')}"
    )


def run_live_session(mode: str = "SCHEDULED") -> None:
    start_ts = time.time()
    now_ist = datetime.now(IST)
    logger.info(
        "Session %s started at %s IST across %d pairs.",
        mode,
        now_ist.isoformat(),
        len(TOP_10_PAIRS),
    )

    send_telegram_message(
        f"🚀 <b>Session Started ({mode})</b>\n"
        f"🕒 <b>Time:</b> {now_ist.strftime('%d %b %Y, %H:%M IST')}\n"
        f"📈 <b>Pairs:</b> {len(TOP_10_PAIRS)} Major Forex Pairs"
    )

    seen_signals = set()

    while (time.time() - start_ts) < MAX_RUNTIME_SECONDS:
        loop_ist = datetime.now(IST)

        for pair, ticker in TOP_10_PAIRS.items():
            if (time.time() - start_ts) >= MAX_RUNTIME_SECONDS:
                break

            try:
                df = fetch_candles(ticker=ticker, period="2d", interval="1m")
                if df.empty or len(df) < 20:
                    continue

                if "pair" in evaluate_signal.__code__.co_varnames:
                    signal = evaluate_signal(df, pair=pair)
                else:
                    signal = evaluate_signal(df)

                if not signal:
                    continue

                last_idx = str(df.index[-1])
                direction = str(signal.get("direction", signal.get("side", ""))).upper()
                dedup_key = f"{pair}:{last_idx}:{direction}"

                if dedup_key in seen_signals:
                    continue

                seen_signals.add(dedup_key)
                msg = format_signal_message(pair, signal, loop_ist)
                send_telegram_message(msg)
                logger.info("Sent signal for %s (%s) at %s", pair, direction, last_idx)

            except Exception as exc:
                logger.error("Error processing %s (%s): %s", pair, ticker, exc)

        time.sleep(60)

    logger.info("Session %s finished cleanly.", mode)


def main() -> None:
    task = os.getenv("TASK", "").strip().lower()
    force_session = os.getenv("FORCE_SESSION", "").strip()

    if task == "run_session" or force_session == "1":
        run_live_session(mode="MANUAL")
        return

    now_ist = datetime.now(IST)
    current_hhmm = now_ist.strftime("%H:%M")

    if current_hhmm in SESSION_TIMES or task == "scheduled_session":
        run_live_session(mode="SCHEDULED")
    else:
        logger.info("Current IST %s not in SESSION_TIMES %s; exiting cleanly.", current_hhmm, SESSION_TIMES)


if __name__ == "__main__":
    main()
