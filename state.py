
import json
import os

STATE_FILE = "bot_state.json"

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return {}

def save_state(state):
    temp_file = STATE_FILE + ".tmp"
    with open(temp_file, "w") as file:
        json.dump(state, file, indent=2)
    os.replace(temp_file, STATE_FILE)

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
      
