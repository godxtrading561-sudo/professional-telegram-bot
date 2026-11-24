import time
import logging
from datetime import datetime

from config import (
    MAX_SIGNALS_PER_SESSION,
    SIGNAL_INTERVAL_SECONDS,
    RETRY_INTERVAL_SECONDS,
)
from state import start_session, add_trade, close_session
from session_messages import (
    session_start_message,
    signal_message,
    session_close_message,
)
from session_summary import create_session_summary

log = logging.getLogger("session-controller")


def run_session(session_id, send_message, find_signal):
    start_session(session_id)

    if not send_message(session_start_message(session_id)):
        log.error("Session start message failed.")

    sent = 0
    last_sent_at = 0

    while sent < MAX_SIGNALS_PER_SESSION:
        if last_sent_at:
            remaining = SIGNAL_INTERVAL_SECONDS - (time.time() - last_sent_at)
            if remaining > 0:
                time.sleep(remaining)

        pair, signal = find_signal()

        if not signal:
            log.info("No valid setup. Retrying.")
            time.sleep(RETRY_INTERVAL_SECONDS)
            continue

        trade = {
            "pair": pair,
            "direction": signal["direction"],
            "score": signal["score"],
            "time": datetime.now().isoformat(),
            "reasons": signal["reasons"],
        }

        message = signal_message(sent + 1, trade)

        if not send_message(message):
            time.sleep(RETRY_INTERVAL_SECONDS)
            continue

        if not add_trade(session_id, trade):
            log.error("State update failed.")
            break

        sent += 1
        last_sent_at = time.time()
        log.info("Signal %d/%d sent", sent, MAX_SIGNALS_PER_SESSION)

    close_session(session_id)

    summary = create_session_summary(session_id)
    send_message(session_close_message(sent, summary))
