
from datetime import datetime
from zoneinfo import ZoneInfo

from bot import send_message
from state import load_state, save_state

IST = ZoneInfo("Asia/Kolkata")

SESSIONS = {
    "MORNING": "09:00",
    "MIDDAY": "12:00",
    "AFTERNOON": "14:00",
    "EVENING": "18:00",
    "NIGHT": "23:00",
}

MAX_SIGNALS = 12
SIGNAL_INTERVAL_MINUTES = 5


def check_session_start():
    now = datetime.now(IST)
    today = now.strftime("%Y-%m-%d")
    state = load_state()

    for session_name, session_time in SESSIONS.items():
        if now.strftime("%H:%M") != session_time:
            continue

        key = f"{today}_{session_name}_started"

        if state.get(key):
            continue

        send_message(
            "🚀 <b>PROFESSIONAL BOT</b>\n\n"
            f"✅ <b>{session_name} SESSION STARTED</b>\n"
            f"🕒 Time: <b>{session_time} IST</b>\n"
            f"📊 Maximum signals: <b>{MAX_SIGNALS}</b>\n"
            "⚠️ Only verified market signals will be sent."
        )

        state[key] = True
        state[f"{today}_{session_name}_count"] = 0
        save_state(state)


def get_active_session(now=None):
    now = now or datetime.now(IST)
    today = now.strftime("%Y-%m-%d")

    for session_name, session_time in SESSIONS.items():
        start = datetime.strptime(
            session_time, "%H:%M"
        ).replace(
            year=now.year,
            month=now.month,
            day=now.day,
            tzinfo=IST,
        )

        elapsed = (now - start).total_seconds()

        if 0 <= elapsed < 60 * SIGNAL_INTERVAL_MINUTES * MAX_SIGNALS:
            return session_name, today

    return None, today


def can_send_signal():
    now = datetime.now(IST)
    session_name, today = get_active_session(now)

    if not session_name:
        return False

    state = load_state()
    count_key = f"{today}_{session_name}_count"
    last_key = f"{today}_{session_name}_last_signal"

    count = int(state.get(count_key, 0))

    if count >= MAX_SIGNALS:
        return False

    last_time = state.get(last_key)

    if last_time:
        last_dt = datetime.fromisoformat(last_time)
        elapsed = (now - last_dt).total_seconds()

        if elapsed < SIGNAL_INTERVAL_MINUTES * 60:
            return False

    return True


def record_signal_sent():
    now = datetime.now(IST)
    session_name, today = get_active_session(now)

    if not session_name:
        raise RuntimeError("No active trading session")

    state = load_state()
    count_key = f"{today}_{session_name}_count"
    last_key = f"{today}_{session_name}_last_signal"

    count = int(state.get(count_key, 0))

    if count >= MAX_SIGNALS:
        raise RuntimeError("Session signal limit reached")

    state[count_key] = count + 1
    state[last_key] = now.isoformat()
    save_state(state)

    return count + 1

