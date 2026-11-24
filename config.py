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
