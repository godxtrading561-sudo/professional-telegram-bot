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
SESSION_MAX_RUNTIME_SECONDS = 90 * 60
SCHEDULE_GRACE_MINUTES = 90
RESULT_EXPIRY_SECONDS = 60

DAILY_MESSAGES = {"morning": time(7, 0), "schedule": time(8, 0), "good_night": time(0, 0)}
TRADING_SESSIONS = [time(9, 0), time(12, 0), time(14, 0), time(18, 0), time(23, 0)]

MIN_CANDLES = 60
# Yahoo Finance symbols are ordinary FX market data, NOT Quotex OTC prices.
TRADING_PAIRS = {
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "AUD/CAD": "AUDCAD=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CHF": "USDCHF=X",
    "NZD/USD": "NZDUSD=X",
    "EUR/GBP": "EURGBP=X",
}
DATA_FOLDER = "data"
REPORT_FOLDER = "reports"
