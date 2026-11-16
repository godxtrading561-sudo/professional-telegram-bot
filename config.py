
from datetime import time
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("Asia/Kolkata")

DAILY_MESSAGES = {
    "morning": time(7, 0),
    "schedule": time(8, 0),
    "good_night": time(0, 0),
}

TRADING_SESSIONS = [
    time(9, 0),
    time(12, 0),
    time(14, 0),
    time(18, 0),
    time(23, 0),
]

MAX_SIGNALS_PER_SESSION = 12
SIGNAL_INTERVAL_MINUTES = 5

# Session close ke baad signals stop.
STOP_AFTER_SESSION_CLOSE = True
