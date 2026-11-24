import time
import logging
from datetime import datetime, timedelta

from config import TIMEZONE, TRADING_SESSIONS
from bot import run_one_session, send_message
from daily_messages import (
    MORNING_MESSAGE,
    SCHEDULE_MESSAGE,
    GOOD_NIGHT_MESSAGE,
)

log = logging.getLogger("scheduler")


def wait_until(target):
    while True:
        now = datetime.now(TIMEZONE)
        seconds = (target - now).total_seconds()

        if seconds <= 0:
            return

        time.sleep(min(seconds, 30))


def main():
    sent_today = set()
    current_day = datetime.now(TIMEZONE).date()

    while True:
        now = datetime.now(TIMEZONE)

        if now.date() != current_day:
            sent_today.clear()
            current_day = now.date()

        if now.hour == 7 and now.minute == 0 and "morning" not in sent_today:
            send_message(MORNING_MESSAGE)
            sent_today.add("morning")

        if now.hour == 8 and now.minute == 0 and "schedule" not in sent_today:
            send_message(SCHEDULE_MESSAGE)
            sent_today.add("schedule")

        if now.hour == 23 and now.minute == 30 and "goodnight" not in sent_today:
            send_message(GOOD_NIGHT_MESSAGE)
            sent_today.add("goodnight")

        for session_time in TRADING_SESSIONS:
            key = session_time.strftime("%H:%M")

            if (
                now.hour == session_time.hour
                and now.minute == session_time.minute
                and key not in sent_today
            ):
                sent_today.add(key)
                run_one_session(now.strftime("%Y-%m-%d-%H-%M"))

        time.sleep(10)


if __name__ == "__main__":
    main()
