"""Persistent session state backed by Supabase, with local JSON fallback for development."""
import json
import os
from datetime import datetime

from config import MAX_SIGNALS_PER_SESSION, TIMEZONE
from supabase_db import get_session as db_get_session, save_session as db_save_session, get_client

STATE_FILE = "bot_state.json"


def _load_local_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_local_session(session_id, session):
    state = _load_local_state()
    state[session_id] = session
    temp = STATE_FILE + ".tmp"
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
    os.replace(temp, STATE_FILE)


def _read_session(session_id):
    if get_client() is not None:
        return db_get_session(session_id)
    return _load_local_state().get(session_id)


def _write_session(session_id, session):
    if get_client() is not None:
        if not db_save_session(session_id, session):
            raise RuntimeError("Supabase session save failed.")
        return True
    _save_local_session(session_id, session)
    return True


def start_session(session_id):
    existing = _read_session(session_id)
    if existing:
        # Never reopen a previously closed session or reset its signal count.
        return existing

    session = {
        "active": True,
        "closed": False,
        "signals_sent": 0,
        "trades": [],
        "started_at": datetime.now(TIMEZONE).isoformat(),
    }
    _write_session(session_id, session)
    return session


def get_session(session_id):
    return _read_session(session_id)


def add_trade(session_id, trade):
    session = _read_session(session_id)
    if not session or not session.get("active") or session.get("closed"):
        return False

    trades = session.setdefault("trades", [])
    if int(session.get("signals_sent", len(trades))) >= MAX_SIGNALS_PER_SESSION:
        return False

    trades.append(trade)
    session["signals_sent"] = len(trades)
    _write_session(session_id, session)
    return True


def close_session(session_id):
    session = _read_session(session_id)
    if not session:
        return False

    session["active"] = False
    session["closed"] = True
    session["closed_at"] = datetime.now(TIMEZONE).isoformat()
    _write_session(session_id, session)
    return True


def update_session(session_id, session):
    """Persist non-trade session metadata without changing the signal count."""
    current = _read_session(session_id)
    if not current or current.get("closed"):
        return False
    _write_session(session_id, session)
    return True
