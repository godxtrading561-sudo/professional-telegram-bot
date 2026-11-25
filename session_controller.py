"""Bounded session runner with persistent duplicate/closed-session protection."""
import logging
import time
from datetime import datetime

from config import (
    MAX_SIGNALS_PER_SESSION,
    SIGNAL_INTERVAL_SECONDS,
    RETRY_INTERVAL_SECONDS,
    SESSION_MAX_RUNTIME_SECONDS,
    TIMEZONE,
)
from state import start_session, get_session, add_trade, close_session
from session_messages import session_start_message, signal_message, session_close_message
from session_summary import create_session_summary

log = logging.getLogger("session-controller")


def run_session(session_id, send_message, find_signal):
    session = start_session(session_id)
    if not session or session.get("closed") or not session.get("active"):
        log.info("Session %s is already closed/inactive; refusing to send.", session_id)
        return False

    # Persisted count is authoritative after a restart.
    sent = int(session.get("signals_sent", len(session.get("trades", []))))
    if sent >= MAX_SIGNALS_PER_SESSION:
        close_session(session_id)
        return False

    if not session.get("start_message_sent"):
        if send_message(session_start_message(session_id)):
            session["start_message_sent"] = True
            # add_trade only persists trades; use a dedicated state update.
            from state import update_session
            update_session(session_id, session)
        else:
            log.error("Session start message failed; continuing cautiously.")

    started_at = time.monotonic()
    last_sent_at = 0.0
    close_reason = "Session limit reached"

    try:
        while sent < MAX_SIGNALS_PER_SESSION:
            current = get_session(session_id)
            if not current or current.get("closed") or not current.get("active"):
                close_reason = "Session was externally closed"
                break

            if time.monotonic() - started_at >= SESSION_MAX_RUNTIME_SECONDS:
                close_reason = "Maximum session runtime reached"
                log.warning(close_reason)
                break

            if last_sent_at:
                remaining = SIGNAL_INTERVAL_SECONDS - (time.monotonic() - last_sent_at)
                if remaining > 0:
                    time.sleep(min(remaining, SESSION_MAX_RUNTIME_SECONDS))

            pair, signal = find_signal()
            if not signal:
                log.info("No valid setup; retrying in %s seconds.", RETRY_INTERVAL_SECONDS)
                time.sleep(RETRY_INTERVAL_SECONDS)
                continue

            trade = {
                "pair": pair,
                "direction": signal["direction"],
                "score": signal["score"],
                "time": datetime.now(TIMEZONE).isoformat(),
                "reasons": signal.get("reasons", []),
            }

            if not send_message(signal_message(sent + 1, trade)):
                log.error("Signal delivery failed; will retry without incrementing count.")
                time.sleep(RETRY_INTERVAL_SECONDS)
                continue

            # If persistence fails after delivery, stop immediately to prevent duplicates.
            if not add_trade(session_id, trade):
                log.error("Could not persist delivered signal; stopping to avoid overposting.")
                close_reason = "State persistence failed after delivery"
                break

            sent += 1
            last_sent_at = time.monotonic()
            log.info("Signal %d/%d sent", sent, MAX_SIGNALS_PER_SESSION)

    except KeyboardInterrupt:
        close_reason = "Session interrupted"
        log.warning(close_reason)
    finally:
        close_session(session_id)
        summary = create_session_summary(session_id)
        send_message(session_close_message(sent, summary))
        log.info("Session %s closed: %s", session_id, close_reason)

    return True
