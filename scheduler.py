"""One-shot daily-message dispatcher with persistent Supabase deduplication."""
import logging
from datetime import datetime, timedelta

from config import DAILY_MESSAGES, TIMEZONE, SCHEDULE_GRACE_MINUTES
from daily_messages import DAILY_MESSAGES as MESSAGE_TEXTS
from bot import send_message
from supabase_db import claim_daily_message, release_daily_message

log = logging.getLogger("scheduler")


def run_daily_messages(now=None):
    """Send the most recently due message once, even if Actions retries a run."""
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
            due.append((age, name, scheduled))

    if not due:
        log.info("No daily message is due in the grace window at %s", now.isoformat())
        return False

    _, name, scheduled = min(due, key=lambda item: item[0])
    message = MESSAGE_TEXTS.get(name)
    if not message:
        log.error("Daily message template missing: %s", name)
        return False

    message_key = f"{name}:{scheduled.date().isoformat()}"
    try:
        claimed = claim_daily_message(message_key, scheduled.isoformat())
    except Exception:
        log.exception("Could not check/claim daily message; refusing unsafe duplicate send.")
        return False
    if not claimed:
        log.info("Daily message already claimed; skipping duplicate: %s", message_key)
        return False

    try:
        delivered = send_message(message)
    except Exception:
        log.exception("Telegram daily-message send failed.")
        delivered = False
    if not delivered:
        try:
            release_daily_message(message_key)
        except Exception:
            log.exception("Could not release failed daily-message claim.")
        return False
    log.info("Daily message delivered once: %s", message_key)
    return True


def main():
    logging.basicConfig(level=logging.INFO)
    run_daily_messages()


if __name__ == "__main__":
    main()
