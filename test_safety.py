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
        with patch.object(scheduler, "claim_daily_message", return_value=True) as claim, patch.object(scheduler, "send_message", return_value=True) as send:
            self.assertTrue(scheduler.run_daily_messages(now))
        claim.assert_called_once()
        send.assert_called_once_with(MESSAGE_TEXTS["schedule"])


class SessionSafetyTests(unittest.TestCase):
    def test_closed_session_does_not_send_or_find_signals(self):
        with patch.object(session_controller, "start_session",
                          return_value={"active": False, "closed": True, "signals_sent": 0}):
            result = session_controller.run_session(
                "closed-test",
                send_message=lambda message: self.fail("message sent for a closed session"),
                find_signal=lambda: self.fail("signal requested for a closed session"),
            )
        self.assertFalse(result)

    def test_add_trade_refuses_closed_session(self):
        closed = {"active": False, "closed": True, "signals_sent": 0, "trades": []}
        with patch.object(state, "_read_session", return_value=closed), \
             patch.object(state, "_write_session") as save:
            self.assertFalse(state.add_trade("closed-test", {"direction": "CALL"}))
        save.assert_not_called()

    def test_add_trade_refuses_thirteenth_signal(self):
        full = {"active": True, "closed": False, "signals_sent": 12,
                "trades": [{"direction": "CALL"} for _ in range(12)]}
        with patch.object(state, "_read_session", return_value=full), patch.object(state, "_write_session") as save:
            self.assertFalse(state.add_trade("full-test", {"direction": "PUT"}))
        save.assert_not_called()

    def test_update_trade_result_does_not_overwrite_verified_result(self):
        session = {"active": True, "closed": False, "signals_sent": 1,
                   "trades": [{"direction": "CALL", "result": "PROFIT"}]}
        with patch.object(state, "_read_session", return_value=session), patch.object(state, "_write_session") as save:
            self.assertTrue(state.update_trade_result("result-test", 0, {"result": "LOSS"}))
        self.assertEqual(session["trades"][0]["result"], "PROFIT")
        save.assert_not_called()

if __name__ == "__main__":
    unittest.main()
