"""Bounded session runner with persistent closed-session protection."""
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
from state import start_session, get_session, add_trade, close_session, update_session
from session_messages import session_start_message, signal_message, session_close_message
from session_summary import create_session_summary

log = logging.getLogger("session-controller")


def run_session(session_id, send_message, find_signal):
    session = start_session(session_id)
    if not session or session.get("closed") or not session.get("active"):
        log.info("Session %s is already closed/inactive; refusing to send.", session_id)
        return False

    sent = int(session.get("signals_sent", len(session.get("trades", []))))
    if sent >= MAX_SIGNALS_PER_SESSION:
        close_session(session_id)
        return False

    if not session.get("start_message_sent"):
        if not send_message(session_start_message(session_id)):
            log.error("Could not send session start; aborting to avoid confusing channel state.")
            close_session(session_id)
            return False
        session["start_message_sent"] = True
        if not update_session(session_id, session):
            log.error("Could not persist session-start marker; aborting.")
            close_session(session_id)
            return False

    started_at = time.monotonic()
    last_sent_at = 0.0
    close_reason = "Signal limit reached"

    try:
        while sent < MAX_SIGNALS_PER_SESSION:
            current = get_session(session_id)
            if not current or current.get("closed") or not current.get("active"):
                close_reason = "Session was externally closed"
                break

            elapsed = time.monotonic() - started_at
            remaining_runtime = SESSION_MAX_RUNTIME_SECONDS - elapsed
            if remaining_runtime <= 0:
                close_reason = "Maximum session runtime reached"
                break

            if last_sent_at:
                wait_for_signal = SIGNAL_INTERVAL_SECONDS - (time.monotonic() - last_sent_at)
                if wait_for_signal > 0:
                    time.sleep(min(wait_for_signal, remaining_runtime))
                if time.monotonic() - started_at >= SESSION_MAX_RUNTIME_SECONDS:
                    close_reason = "Maximum session runtime reached"
                    break

            pair, signal = find_signal()
            if not signal:
                remaining_runtime = SESSION_MAX_RUNTIME_SECONDS - (time.monotonic() - started_at)
                if remaining_runtime <= 0:
                    close_reason = "Maximum session runtime reached"
                    break
                time.sleep(min(RETRY_INTERVAL_SECONDS, remaining_runtime))
                continue

            if signal.get("direction") not in ("CALL", "PUT"):
                log.warning("Ignoring invalid direction: %r", signal.get("direction"))
                continue

            trade = {
                "pair": pair,
                "direction": signal["direction"],
                "score": signal.get("score"),
                "time": datetime.now(TIMEZONE).isoformat(),
                "reasons": signal.get("reasons", []),
                "result": "PENDING",
            }

            if not send_message(signal_message(sent + 1, trade)):
                log.error("Signal delivery failed; retrying without incrementing count.")
                time.sleep(min(RETRY_INTERVAL_SECONDS, max(0, SESSION_MAX_RUNTIME_SECONDS - (time.monotonic() - started_at))))
                continue

            if not add_trade(session_id, trade):
                log.error("Delivered signal could not be persisted; stopping to prevent overposting.")
                close_reason = "State persistence failed after delivery"
                break

            sent += 1
            last_sent_at = time.monotonic()
            log.info("Signal %d/%d sent", sent, MAX_SIGNALS_PER_SESSION)

    except Exception:
        close_reason = "Unexpected session error"
        log.exception("Session %s failed", session_id)
    finally:
        try:
            close_session(session_id)
            summary = create_session_summary(session_id)
            if not send_message(session_close_message(sent, summary)):
                log.error("Could not deliver session-close message.")
        except Exception:
            log.exception("Failed while closing session %s", session_id)
        log.info("Session %s closed: %s", session_id, close_reason)

    return True
