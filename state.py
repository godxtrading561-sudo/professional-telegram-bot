from supabase_db import load_bot_state, save_bot_state

STATE_ID = "professional_bot_state"


def load_state():
    return load_bot_state(STATE_ID)


def save_state(state):
    save_bot_state(STATE_ID, state)


def start_session(state, session_id):
    state[session_id] = {
        "active": True,
        "closed": False,
        "signals_sent": 0,
        "trades": []
    }
    save_state(state)


def close_session(state, session_id):
    if session_id in state:
        state[session_id]["active"] = False
        state[session_id]["closed"] = True
        save_state(state)
