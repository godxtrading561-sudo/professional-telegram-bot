
import os
import time
import logging
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
SEND_MESSAGE_URL = f"{TELEGRAM_API}/sendMessage"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("professional_bot")


class TelegramError(Exception):
    pass


def send_message(
    message,
    parse_mode="HTML",
    disable_notification=False,
):
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Message cannot be empty")

    payload = {
        "chat_id": CHANNEL_ID,
        "text": message,
        "disable_notification": disable_notification,
    }

    if parse_mode:
        payload["parse_mode"] = parse_mode

    for attempt in range(3):
        try:
            response = requests.post(
                SEND_MESSAGE_URL,
                json=payload,
                timeout=(10, 25),
            )

            if response.status_code == 429:
                data = response.json()
                wait_time = data.get(
                    "parameters", {}
                ).get("retry_after", 5)

                logger.warning(
                    "Telegram rate limit. Waiting %s seconds",
                    wait_time,
                )
                time.sleep(min(int(wait_time), 60))
                continue

            response.raise_for_status()
            data = response.json()

            if not data.get("ok"):
                raise TelegramError(
                    data.get("description", "Telegram API error")
                )

            message_id = data["result"]["message_id"]

            logger.info(
                "Telegram message sent. Message ID: %s",
                message_id,
            )

            return message_id

        except (requests.RequestException, ValueError, TelegramError):
            logger.exception(
                "Telegram send attempt %s failed",
                attempt + 1,
            )

            if attempt == 2:
                raise

            time.sleep(2 ** attempt)

    raise TelegramError("Message delivery failed")


def send_signal(
    pair,
    timeframe,
    direction,
    entry_time,
    reason,
):
    if direction not in ("CALL", "PUT"):
        raise ValueError("Only CALL or PUT signals are allowed")

    message = (
        "🔔 <b>PROFESSIONAL BOT — LIVE SIGNAL</b>\n\n"
        f"📊 Pair: <b>{pair}</b>\n"
        f"⏱ Timeframe: <b>{timeframe}</b>\n"
        f"🎯 Direction: <b>{direction}</b>\n"
        f"🕒 Entry time: <b>{entry_time}</b>\n"
        f"🔍 Reason: {reason}\n\n"
        "⚠️ Risk management is essential. No guaranteed result."
    )

    return send_message(message)


def send_session_start(session_name):
    message = (
        "🚀 <b>PROFESSIONAL BOT</b>\n\n"
        f"✅ <b>{session_name} SESSION STARTED</b>\n"
        "📊 Market analysis is active.\n"
        "⚠️ Only verified signals will be published."
    )

    return send_message(message)


def send_session_summary(
    session_name,
    wins,
    losses,
    ties=0,
):
    total = wins + losses
    accuracy = wins / total * 100 if total else 0

    message = (
        f"📊 <b>{session_name} SESSION COMPLETED</b>\n\n"
        f"✅ Wins: <b>{wins}</b>\n"
        f"❌ Losses: <b>{losses}</b>\n"
        f"➖ Ties: <b>{ties}</b>\n"
        f"🎯 Decided trades: <b>{total}</b>\n"
        f"📈 Actual win rate: <b>{accuracy:.2f}%</b>\n\n"
        "Results are based only on recorded trades."
    )

    return send_message(message)


if __name__ == "__main__":
    logger.info("Testing Telegram connection...")
    send_message(
        "✅ <b>PROFESSIONAL BOT CONNECTED!</b>\n"
        "Telegram message delivery test successful."
    )
    
