
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

from config import DAILY_MESSAGES
from daily_messages import (
    MORNING_MESSAGE,
    SCHEDULE_MESSAGE,
    GOOD_NIGHT_MESSAGE,
)
from bot import send_message

TZ = ZoneInfo("Asia/Kolkata")
STATE_FILE = "bot_state.json"

MESSAGES = {
    "morning": MORNING_MESSAGE,
    "schedule": SCHEDULE_MESSAGE,
    "good_night": GOOD_NIGHT_MESSAGE,
}


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}

    try:
        with open(STATE_FILE, "r") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state):
    temp_file = STATE_FILE + ".tmp"

    with open(temp_file, "w") as file:
        json.dump(state, file, indent=2)

    os.replace(temp_file, STATE_FILE)


def check_daily_messages():
    now = datetime.now(TZ)
    today = now.strftime("%Y-%m-%d")
    state = load_state()

    for name, scheduled_time in DAILY_MESSAGES.items():
        if (now.hour, now.minute) != (
            scheduled_time.hour,
            scheduled_time.minute
        ):
            continue

        key = f"{today}_{name}"

        if state.get(key):
            continue

        send_message(MESSAGES[name])
        state[key] = True
        save_state(state)


if __name__ == "__main__":
    check_daily_messages()

