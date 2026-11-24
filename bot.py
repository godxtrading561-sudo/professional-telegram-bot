import os
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import pandas as pd
import yfinance as yf
import requests

from daily_messages import (
    GOOD_NIGHT_MESSAGE,
    MORNING_MESSAGE,
    SCHEDULE_MESSAGE,
    SESSION_CLOSE_MESSAGE,
    SESSION_START_MESSAGE,
)
from signal_engine import analyze_market

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("bot")

IST = timezone(timedelta(hours=5, minutes=30))

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
SESSION_NAMES = {
    "09:00": "1st Bot Session",
    "12:00": "2nd Bot Session",
    "14:00": "3rd Bot Session",
    "18:00": "4th Bot Session",
    "23:00": "5th Bot Session",
}

MAX_SIGNALS_PER_SESSION = 12
SIGNAL_GAP_SECONDS = 5 * 60
NO_SETUP_RETRY_SECONDS = 30
MAX_RUNTIME_SECONDS = 85 * 60


def send_telegram_message(text: str) -> bool:
    token = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or "").strip()
    chat_id = (os.getenv("TELEGRAM_CHAT_ID") or os.getenv("CHANNEL_ID") or "").strip()
    if not token or not chat_id:
        logger.warning("Telegram credentials missing; skipping message.")
        return False

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
            return False
        return True
    except Exception as exc:
        logger.error("Failed to send Telegram message: %s", exc)
        return False


def send_message(text: str) -> bool:
    return send_telegram_message(text)


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

    return df[["open", "high", "low", "close"]].dropna()


def format_signal_message(pair: str, direction_code: str, now_ist: datetime) -> str:
    direction_text = "🟢 CALL (UP)" if direction_code == "CALL" else "🔴 PUT (DOWN)"
    lines = [
        "📊 TRADE SIGNAL SETUP",
        "",
        f"PAIR NAME -: {pair}",
        "",
        "TIME FRAME -: 1 Minute",
        "",
        f"DIRECTION -: {direction_text}",
        "",
        f"🕒 TIME (IST) -: {now_ist.strftime('%H:%M:%S')}",
        "",
        "⚠️ MONEY MANAGEMENT RULE:",
        "Always use proper risk management (Max 2% to 5% of your total capital per trade). Stick to a disciplined martingale plan only if your strategy requires it, and never chase losses blindly! 🚀💰",
    ]
    return "\n".join(lines)


def format_result_message(outcome_label: str, accuracy_text: str) -> str:
    lines = [
        "📊 TRADE RESULT UPDATE",
        "",
        f"TRADE RESULT -: {outcome_label}",
        "",
        f"TRADE ACCURACY -: {accuracy_text}",
        "",
        "💡 PRO TIP: Market mein losses bhi trading ka part hote hain. Proper money management (2%-5%) aur compound discipline hi long-term success ki key hai! 🚀💰",
    ]
    return "\n".join(lines)


def evaluate_real_outcome(ticker: str, direction_code: str) -> Optional[str]:
    try:
        df = fetch_candles(ticker=ticker, period="1d", interval="1m")
        if df.empty or len(df) < 2:
            return None

        candle_open = float(df["open"].iloc[-1])
        candle_close = float(df["close"].iloc[-1])

        if candle_close > candle_open:
            return "WIN" if direction_code == "CALL" else "LOSS"
        if candle_close < candle_open:
            return "WIN" if direction_code == "PUT" else "LOSS"
        return "TIE"
    except Exception as exc:
        logger.error("Outcome check failed for %s: %s", ticker, exc)
        return None


def send_session_results_summary(session_label: str, records: List[Dict[str, str]]) -> None:
    wins = sum(1 for r in records if r["outcome"] == "WIN")
    losses = sum(1 for r in records if r["outcome"] == "LOSS")
    decisive = wins + losses
    acc_text = f"{(wins / decisive) * 100:.1f}%" if decisive > 0 else "N/A"

    lines = [
        "🔥 VIP BOT SESSION RESULTS 🔥",
        "",
        f"🤖 {session_label} Result -:",
        "",
    ]

    if records:
        for rec in records:
            icon = "📈" if rec["dir_arrow"] == "UP" else "📉"
            if rec["outcome"] == "WIN":
                status_tag = "🟢 WIN (Direct)"
            elif rec["outcome"] == "LOSS":
                status_tag = "🔴 LOSS"
            elif rec["outcome"] == "TIE":
                status_tag = "⚪ TIE"
            else:
                status_tag = "⏳ UNVERIFIED"

            lines.append(f"{icon} {rec['pair']} | {rec['dir_arrow']} ➔ {status_tag}")
            lines.append("")
    else:
        lines.append("No verified signal setups during this session.")
        lines.append("")

    lines.extend([
        "📊 SESSION SUMMARY",
        f"🎯 TOTAL TRADES -: {len(records)}",
        f"🟢 TOTAL WINS -: {wins}",
        f"🔴 TOTAL LOSSES -: {losses}",
        "",
        f"⚡ SESSION ACCURACY -: {acc_text}",
        "",
        "💰 PROFIT ALERT: Target achieved for this session! Strict money management applied. 🚀💸",
    ])
    send_telegram_message("\n".join(lines))


def run_live_session(mode: str = "SCHEDULED") -> None:
    start_ts = time.time()
    now_ist = datetime.now(IST)
    hhmm = now_ist.strftime("%H:%M")
    session_label = SESSION_NAMES.get(hhmm, f"{mode} Session")

    logger.info("Session %s (%s) started at %s IST.", session_label, mode, now_ist.isoformat())
    send_telegram_message(SESSION_START_MESSAGE)

    seen_signals = set()
    records: List[Dict[str, str]] = []
    sent_count = 0

    try:
        while (time.time() - start_ts) < MAX_RUNTIME_SECONDS and sent_count < MAX_SIGNALS_PER_SESSION:
            signal_sent_this_cycle = False

            for pair, ticker in TOP_10_PAIRS.items():
                if (time.time() - start_ts) >= MAX_RUNTIME_SECONDS or sent_count >= MAX_SIGNALS_PER_SESSION:
                    break

                try:
                    df = fetch_candles(ticker=ticker, period="2d", interval="1m")
                    if df.empty or len(df) < 100:
                        continue

                    signal = analyze_market(df)
                    if not signal:
                        continue

                    raw_dir = str(signal.get("direction", "")).strip().upper()
                    if "CALL" in raw_dir or "UP" in raw_dir or "BUY" in raw_dir:
                        dir_code = "CALL"
                        dir_arrow = "UP"
                    elif "PUT" in raw_dir or "DOWN" in raw_dir or "SELL" in raw_dir:
                        dir_code = "PUT"
                        dir_arrow = "DOWN"
                    else:
                        continue

                    last_idx = str(df.index[-1])
                    dedup_key = f"{pair}:{last_idx}:{dir_code}"
                    if dedup_key in seen_signals:
                        continue

                    seen_signals.add(dedup_key)
                    sig_time = datetime.now(IST)
                    msg = format_signal_message(pair, dir_code, sig_time)

                    if send_telegram_message(msg):
                        sent_count += 1
                        signal_sent_this_cycle = True
                        logger.info("Sent signal #%d/%d: %s %s", sent_count, MAX_SIGNALS_PER_SESSION, pair, dir_code)

                        # 1m candle close ke baad real outcome check (60s), phir baaki 5-min gap (240s)
                        time.sleep(60)
                        outcome = evaluate_real_outcome(ticker, dir_code)

                        if outcome in ("WIN", "LOSS"):
                            outcome_label = "🟢 PROFIT (ITM)" if outcome == "WIN" else "🔴 LOSS (OTM)"
                            wins_so_far = sum(1 for r in records if r["outcome"] == "WIN") + (
                                1 if outcome == "WIN" else 0
                            )
                            decisive_so_far = sum(
                                1 for r in records if r["outcome"] in ("WIN", "LOSS")
                            ) + 1
                            acc_pct = f"{(wins_so_far / decisive_so_far) * 100:.1f}%"
                            send_telegram_message(format_result_message(outcome_label, acc_pct))

                        records.append({
                            "pair": pair,
                            "dir_arrow": dir_arrow,
                            "outcome": outcome or "UNVERIFIED",
                        })

                        if sent_count < MAX_SIGNALS_PER_SESSION and (time.time() - start_ts) < MAX_RUNTIME_SECONDS:
                            remaining_gap = max(1, SIGNAL_GAP_SECONDS - 60)
                            time.sleep(remaining_gap)

                        break

                except Exception as exc:
                    logger.error("Error processing %s (%s): %s", pair, ticker, exc)

            if not signal_sent_this_cycle:
                time.sleep(NO_SETUP_RETRY_SECONDS)
    finally:
        send_telegram_message(SESSION_CLOSE_MESSAGE)
        send_session_results_summary(session_label, records)
        logger.info("Session %s completed. Total signals: %d", session_label, sent_count)


def main() -> None:
    task = os.getenv("TASK", "").strip().lower()
    force_session = os.getenv("FORCE_SESSION", "").strip()

    if task == "morning_briefing":
        send_telegram_message(MORNING_MESSAGE)
        return
    if task == "daily_schedule":
        send_telegram_message(SCHEDULE_MESSAGE)
        return
    if task == "good_night":
        send_telegram_message(GOOD_NIGHT_MESSAGE)
        return

    if task == "run_session" or force_session == "1":
        run_live_session(mode="MANUAL")
        return

    now_ist = datetime.now(IST)
    current_hhmm = now_ist.strftime("%H:%M")

    if current_hhmm in SESSION_TIMES or task == "scheduled_session":
        run_live_session(mode="SCHEDULED")
    else:
        logger.info(
            "Current IST %s not in SESSION_TIMES %s; exiting cleanly.",
            current_hhmm,
            SESSION_TIMES,
        )


if __name__ == "__main__":
    main()
