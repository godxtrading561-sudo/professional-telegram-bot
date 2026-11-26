"""Bounded session runner with verified one-minute OTC result evaluation."""
import logging
import os
import time
from datetime import datetime, timezone

from config import MAX_SIGNALS_PER_SESSION, SIGNAL_INTERVAL_SECONDS, RETRY_INTERVAL_SECONDS, SESSION_MAX_RUNTIME_SECONDS, TIMEZONE
from state import start_session, get_session, add_trade, close_session, update_session, update_trade_result
from session_messages import session_start_message, signal_message, session_close_message, trade_result_message
from session_summary import create_session_summary
from quotex_data import fetch_quotex_candles, evaluate_one_minute_result, CandleFeedError

log = logging.getLogger("session-controller")


def run_session(session_id, send_message, find_signal, send_photo=None):
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
            close_session(session_id)
            return False
        session["start_message_sent"] = True
        if not update_session(session_id, session):
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
            remaining = SESSION_MAX_RUNTIME_SECONDS - (time.monotonic() - started_at)
            if remaining <= 0:
                close_reason = "Maximum session runtime reached"
                break
            if last_sent_at:
                wait = SIGNAL_INTERVAL_SECONDS - (time.monotonic() - last_sent_at)
                if wait > 0:
                    time.sleep(min(wait, remaining))
                if time.monotonic() - started_at >= SESSION_MAX_RUNTIME_SECONDS:
                    close_reason = "Maximum session runtime reached"
                    break

            pair, signal = find_signal()
            if not signal:
                time.sleep(min(RETRY_INTERVAL_SECONDS, max(0, SESSION_MAX_RUNTIME_SECONDS - (time.monotonic() - started_at))))
                continue
            if signal.get("direction") not in ("CALL", "PUT") or not pair:
                log.warning("Ignoring malformed signal: %r %r", pair, signal)
                continue

            signal_time = datetime.now(timezone.utc).isoformat()
            trade = {"pair": pair, "direction": signal["direction"], "score": signal.get("score"),
                     "time": signal_time, "reasons": signal.get("reasons", []), "result": "PENDING"}
            caption = signal_message(sent + 1, trade)
            chart_path = signal.get("chart_path")
            if chart_path and send_photo:
                delivered = send_photo(chart_path, caption)
                try:
                    os.remove(chart_path)
                except OSError:
                    pass
                # Preserve the signal if Telegram rejects the image upload.
                if not delivered:
                    log.warning("Photo delivery failed; falling back to text signal.")
                    delivered = send_message(caption)
            else:
                delivered = send_message(caption)
            if not delivered:
                log.error("Signal delivery failed; not recording it.")
                time.sleep(RETRY_INTERVAL_SECONDS)
                continue
            if not add_trade(session_id, trade):
                log.error("Signal sent but persistence failed; stopping to prevent overposting.")
                close_reason = "State persistence failed after delivery"
                break

            trade_index = sent
            sent += 1
            last_sent_at = time.monotonic()
            log.info("Signal %d/%d sent; waiting for 1-minute expiry", sent, MAX_SIGNALS_PER_SESSION)

            # One expiry check, not a rapid polling loop. If feed lacks the exact
            # expiry candle, retain PENDING rather than inventing a result.
            time.sleep(125)
            try:
                candles = fetch_quotex_candles(pair, limit=360)
                result = evaluate_one_minute_result(trade["direction"], signal_time, candles)
                if result is None:
                    log.warning("No complete entry/expiry candle for %s; result remains pending", pair)
                elif update_trade_result(session_id, trade_index, {"result": result["status"], **result}):
                    if not send_message(trade_result_message(trade, result)):
                        log.error("Verified result saved but Telegram result message failed.")
            except CandleFeedError as exc:
                log.error("Cannot verify trade result from OTC feed: %s", exc)

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
