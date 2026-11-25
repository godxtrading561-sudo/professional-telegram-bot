
import os
from datetime import time
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("Asia/Kolkata")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

MAX_SIGNALS_PER_SESSION = 12
SIGNAL_INTERVAL_SECONDS = 300
RETRY_INTERVAL_SECONDS = 30
SESSION_MAX_RUNTIME_SECONDS = 90 * 60  # Stop safely if no valid setups appear.
SCHEDULE_GRACE_MINUTES = 20

# Daily automatic messages (Indian Standard Time)
DAILY_MESSAGES = {
    "morning": time(7, 0),
    "schedule": time(8, 0),
    "good_night": time(0, 0),
}

# Trading sessions (Indian Standard Time)
TRADING_SESSIONS = [
    time(9, 0),
    time(12, 0),
    time(14, 0),
    time(18, 0),
    time(23, 0),
]

MIN_CANDLES = 200
MIN_SIGNAL_SCORE = 4

TRADING_PAIRS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "AUDCAD": "AUDCAD=X",
    "EURJPY": "EURJPY=X",
    "GBPJPY": "GBPJPY=X",
}

DATA_FOLDER = "data"
REPORT_FOLDER = "reports"
