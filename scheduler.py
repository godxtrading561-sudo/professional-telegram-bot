
import time
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from config import DAILY_MESSAGES
from daily_messages import (
    MORNING_MESSAGE,
    SCHEDULE_MESSAGE,
    GOOD_NIGHT_MESSAGE,
)
from bot import send_message
from state import load_state, save_state
from session_controller import check_session_start

IST = ZoneInfo("Asia/Kolkata")

MESSAGES = {
    "morning": MORNING_MESSAGE,
    "schedule": SCHEDULE_MESSAGE,
    "good_night": GOOD_NIGHT_MESSAGE,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger("scheduler")


def check_daily_messages():
    now = datetime.now(IST)
    today = now.strftime("%Y-%m-%d")
    state = load_state()

    for name, scheduled_time in DAILY_MESSAGES.items():
        if (now.hour, now.minute) != (
            scheduled_time.hour,
            scheduled_time.minute,
        ):
            continue

        key = f"{today}_{name}"

        if state.get(key):
            continue

        send_message(MESSAGES[name])
        state[key] = True
        save_state(state)

        logger.info("Daily message sent: %s", name)


def run_scheduler():
    logger.info("Professional Bot scheduler started (IST)")

    while True:
        try:
            check_daily_messages()
            check_session_start()
        except Exception:
            logger.exception("Scheduler cycle failed")

        time.sleep(10)


if __name__ == "__main__":
    run_scheduler()
