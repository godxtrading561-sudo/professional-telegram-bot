"""Offline tests for the original EMA 9/21 + RSI 14 signal engine."""
import unittest
import pandas as pd
from signal_engine import analyze_market, prepare_candles


class SignalEngineTests(unittest.TestCase):
    def test_rejects_empty_or_short_data(self):
        self.assertIsNone(analyze_market(pd.DataFrame()))
        self.assertIsNone(analyze_market(pd.DataFrame({
            "open": [1.0] * 20, "high": [1.1] * 20,
            "low": [0.9] * 20, "close": [1.02] * 20,
        })))

    def test_prepare_candles_drops_nan_and_invalid_rows(self):
        frame = pd.DataFrame({
            "open": [1.0, 1.0, 1.0], "high": [1.1, 0.9, 1.1],
            "low": [0.9, 0.95, 0.9], "close": [1.05, 1.02, None],
        })
        cleaned = prepare_candles(frame)
        self.assertEqual(len(cleaned), 1)

    def test_no_random_direction_on_flat_market(self):
        frame = pd.DataFrame({
            "open": [1.0] * 100, "high": [1.001] * 100,
            "low": [0.999] * 100, "close": [1.0] * 100,
        })
        self.assertIsNone(analyze_market(frame))


if __name__ == "__main__":
    unittest.main()
