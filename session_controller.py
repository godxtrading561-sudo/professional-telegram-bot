
from datetime import datetime
from zoneinfo import ZoneInfo

from config import TRADING_SESSIONS
from session_messages import SESSION_LIVE
from bot import send_message
from state import load_state, save_state

TZ = ZoneInfo("Asia/Kolkata")


def check_session_start():
    now = datetime.now(TZ)
    today = now.strftime("%Y-%m-%d")
    state = load_state()

    for index, session_time in enumerate(TRADING_SESSIONS, start=1):
        if (now.hour, now.minute) != (
            session_time.hour,
            session_time.minute
        ):
            continue

        session_id = f"{today}_session_{index}"

        if state.get(session_id, {}).get("started"):
            continue

        send_message(
            f"👑 SESSION {index} STARTING 👑\n\n{SESSION_LIVE}"
        )

        state[session_id] = {
            "started": True,
            "active": True,
            "closed": False,
            "signals_sent": 0,
            "trades": []
        }

        save_state(state)


if __name__ == "__main__":
    check_session_start()
  
