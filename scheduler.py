"""One-shot daily-message dispatcher for scheduled GitHub Actions runs."""
import logging
from datetime import datetime

from config import DAILY_MESSAGES, TIMEZONE
from daily_messages import DAILY_MESSAGES as MESSAGE_TEXTS
from bot import send_message

log = logging.getLogger("scheduler")


def run_daily_messages(now=None):
    """Send the daily message due at the supplied/current Asia/Kolkata time."""
    now = now or datetime.now(TIMEZONE)
    now = now.astimezone(TIMEZONE)

    for name, scheduled_time in DAILY_MESSAGES.items():
        if now.hour == scheduled_time.hour and now.minute == scheduled_time.minute:
            message = MESSAGE_TEXTS.get(name)
            if not message:
                log.error("Daily message template missing: %s", name)
                return False
            return send_message(message)

    log.info("No daily message is scheduled for %s", now.strftime("%H:%M"))
    return False


def main():
    logging.basicConfig(level=logging.INFO)
    run_daily_messages()


if __name__ == "__main__":
    main()
