
from datetime import datetime
from zoneinfo import ZoneInfo

from config import DAILY_MESSAGES, TRADING_SESSIONS
from daily_messages import (
    MORNING_MESSAGE,
    SCHEDULE_MESSAGE,
    GOOD_NIGHT_MESSAGE,
)
from bot import send_message

TZ = ZoneInfo("Asia/Kolkata")

MESSAGES = {
    "morning": MORNING_MESSAGE,
    "schedule": SCHEDULE_MESSAGE,
    "good_night": GOOD_NIGHT_MESSAGE,
}

def check_daily_messages():
    now = datetime.now(TZ)

    for name, scheduled_time in DAILY_MESSAGES.items():
        if now.hour == scheduled_time.hour and now.minute == scheduled_time.minute:
            send_message(MESSAGES[name])

if __name__ == "__main__":
    check_daily_messages()
  
