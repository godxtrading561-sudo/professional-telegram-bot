"""One-shot daily-message dispatcher tolerant of delayed GitHub scheduled starts."""
import logging
from datetime import datetime, timedelta

from config import DAILY_MESSAGES, TIMEZONE, SCHEDULE_GRACE_MINUTES
from daily_messages import DAILY_MESSAGES as MESSAGE_TEXTS
from bot import send_message

log = logging.getLogger("scheduler")


def run_daily_messages(now=None):
    """Send a message if its scheduled time fell within the recent grace window."""
    now = (now or datetime.now(TIMEZONE)).astimezone(TIMEZONE)
    for name, scheduled_time in DAILY_MESSAGES.items():
        scheduled = now.replace(
            hour=scheduled_time.hour,
            minute=scheduled_time.minute,
            second=0,
            microsecond=0,
        )
        # Midnight belongs to the previous calendar date when checking shortly after midnight.
        if scheduled > now:
            scheduled -= timedelta(days=1)
        age = (now - scheduled).total_seconds()
        if 0 <= age <= SCHEDULE_GRACE_MINUTES * 60:
            message = MESSAGE_TEXTS.get(name)
            if not message:
                log.error("Daily message template missing: %s", name)
                return False
            return send_message(message)
    log.info("No daily message is due in the grace window at %s", now.isoformat())
    return False


def main():
    logging.basicConfig(level=logging.INFO)
    run_daily_messages()


if __name__ == "__main__":
    main()
