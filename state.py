import json
import os
from datetime import datetime
from config import TIMEZONE

STATE_FILE = "bot_state.json"


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state):
    temp = STATE_FILE + ".tmp"
    with open(temp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(temp, STATE_FILE)


def start_session(session_id):
    state = load_state()
    if session_id in state:
        return state[session_id]

    state[session_id] = {
        "active": True,
        "closed": False,
        "signals_sent": 0,
        "trades": [],
        "started_at": datetime.now(TIMEZONE).isoformat(),
    }
    save_state(state)
    return state[session_id]


def get_session(session_id):
    return load_state().get(session_id)


def add_trade(session_id, trade):
    state = load_state()
    session = state.get(session_id)

    if not session or not session["active"] or session["closed"]:
        return False

    if session["signals_sent"] >= 12:
        return False

    session["trades"].append(trade)
    session["signals_sent"] += 1
    save_state(state)
    return True


def close_session(session_id):
    state = load_state()
    session = state.get(session_id)

    if not session:
        return False

    session["active"] = False
    session["closed"] = True
    session["closed_at"] = datetime.now(TIMEZONE).isoformat()
    save_state(state)
    return True
