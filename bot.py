
import os
import time
import logging
import requests

# -------- TELEGRAM CONFIGURATION --------

TOKEN = os.environ["BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["CHANNEL_ID"]

TELEGRAM_URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("PROFESSIONAL_BOT")


# -------- SEND TELEGRAM MESSAGE --------

def send_telegram_message(message):

    if not isinstance(message, str) or not message.strip():
        logger.error("Message cannot be empty")
        return False

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    for attempt in range(3):
        try:
            response = requests.post(
                TELEGRAM_URL,
                json=payload,
                timeout=(10, 20)
            )

            data = response.json()

            if response.status_code == 200 and data.get("ok"):
                logger.info("Telegram message sent successfully")
                return True

            logger.error("Telegram API error: %s", data)

            if response.status_code == 429:
                wait_time = data.get(
                    "parameters", {}
                ).get("retry_after", 5)

                time.sleep(min(int(wait_time), 60))
                continue

        except (requests.RequestException, ValueError) as error:
            logger.error("Telegram connection error: %s", error)

        if attempt < 2:
            time.sleep(2 ** attempt)

    logger.error("Telegram message delivery failed")
    return False


# -------- TELEGRAM CONNECTION TEST --------

if __name__ == "__main__":

    logger.info("Testing Telegram connection...")

    success = send_telegram_message(
        "✅ <b>PROFESSIONAL BOT CONNECTED!</b>\n\n"
        "🤖 Telegram connection test successful."
    )

    if success:
        logger.info("Telegram test completed successfully")
    else:
        logger.error("Telegram test failed")
