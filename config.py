import os
from datetime import time
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("Asia/Kolkata")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
OTCHARTS_API_KEY = os.getenv("OTCHARTS_API_KEY", "")

MAX_SIGNALS_PER_SESSION = 12
SIGNAL_INTERVAL_SECONDS = 300
RETRY_INTERVAL_SECONDS = 30
SESSION_MAX_RUNTIME_SECONDS = 90 * 60
SCHEDULE_GRACE_MINUTES = 2
RESULT_EXPIRY_SECONDS = 60

DAILY_MESSAGES = {"morning": time(7, 0), "schedule": time(8, 0), "good_night": time(0, 0)}
TRADING_SESSIONS = [time(9, 0), time(12, 0), time(14, 0), time(18, 0), time(22, 0)]
MIN_CANDLES = 60
MIN_SIGNAL_SCORE = 4

# These are actual Quotex OTC symbols, not Yahoo/regular FX tickers.
TRADING_PAIRS = {
    "EURUSD_otc": "EURUSD_otc",
    "GBPUSD_otc": "GBPUSD_otc",
    "USDJPY_otc": "USDJPY_otc",
    "AUDCAD_otc": "AUDCAD_otc",
    "EURJPY_otc": "EURJPY_otc",
    "GBPJPY_otc": "GBPJPY_otc",
}
DATA_FOLDER = "data"
REPORT_FOLDER = "reports"
