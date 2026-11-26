"""One-shot daily-message dispatcher tolerant of delayed GitHub scheduled starts."""
import logging
from datetime import datetime, timedelta

from config import DAILY_MESSAGES, TIMEZONE, SCHEDULE_GRACE_MINUTES
from daily_messages import DAILY_MESSAGES as MESSAGE_TEXTS
from bot import send_message

log = logging.getLogger("scheduler")


def run_daily_messages(now=None):
    """Send only the most recently due message inside the catch-up window."""
    now = (now or datetime.now(TIMEZONE)).astimezone(TIMEZONE)
    due = []
    for name, scheduled_time in DAILY_MESSAGES.items():
        scheduled = now.replace(
            hour=scheduled_time.hour,
            minute=scheduled_time.minute,
            second=0,
            microsecond=0,
        )
        if scheduled > now:
            scheduled -= timedelta(days=1)
        age = (now - scheduled).total_seconds()
        if 0 <= age <= SCHEDULE_GRACE_MINUTES * 60:
            due.append((age, name))

    if not due:
        log.info("No daily message is due in the grace window at %s", now.isoformat())
        return False

    # When windows overlap (e.g. 07:00 and 08:00), send the latest scheduled item.
    _, name = min(due, key=lambda item: item[0])
    message = MESSAGE_TEXTS.get(name)
    if not message:
        log.error("Daily message template missing: %s", name)
        return False
    return send_message(message)


def main():
    logging.basicConfig(level=logging.INFO)
    run_daily_messages()


if __name__ == "__main__":
    main()
