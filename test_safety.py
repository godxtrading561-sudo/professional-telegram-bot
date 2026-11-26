"""Offline safety regression tests; no API keys or network access required."""
import unittest
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import scheduler
import session_controller
import state
from daily_messages import DAILY_MESSAGES as MESSAGE_TEXTS


class SchedulerSafetyTests(unittest.TestCase):
    def test_latest_due_message_wins_when_catchup_windows_overlap(self):
        now = datetime(2026, 11, 26, 8, 15, tzinfo=ZoneInfo("Asia/Kolkata"))
        with patch.object(scheduler, "send_message", return_value=True) as send:
            self.assertTrue(scheduler.run_daily_messages(now))
        send.assert_called_once_with(MESSAGE_TEXTS["schedule"])


class SessionSafetyTests(unittest.TestCase):
    def test_closed_session_does_not_send_or_find_signals(self):
        with patch.object(session_controller, "start_session",
                          return_value={"active": False, "closed": True, "signals_sent": 0}), \
             patch.object(session_controller, "run_session") as runner:
            # Call the real function with callbacks that must never be reached.
            result = session_controller.run_session(
                "closed-test",
                send_message=lambda message: self.fail("message sent for a closed session"),
                find_signal=lambda: self.fail("signal requested for a closed session"),
            )
        self.assertFalse(result)
        runner.assert_not_called()

    def test_add_trade_refuses_closed_session(self):
        closed = {"active": False, "closed": True, "signals_sent": 0, "trades": []}
        with patch.object(state, "_read_session", return_value=closed), \
             patch.object(state, "_write_session") as save:
            self.assertFalse(state.add_trade("closed-test", {"direction": "CALL"}))
        save.assert_not_called()


if __name__ == "__main__":
    unittest.main()
