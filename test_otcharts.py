"""Safe manual diagnostic for the configured Quotex OTC candle feed."""
import os
import sys

from config import TRADING_PAIRS
from quotex_data import fetch_quotex_candles, CandleFeedError


def main():
    if not os.getenv("OTCHARTS_API_KEY", "").strip():
        print("ERROR: OTCHARTS_API_KEY secret is missing.")
        return 2

    symbol = next(iter(TRADING_PAIRS.values()))
    print(f"Checking OTCharts Quotex OTC feed for {symbol} (1-minute candles)...")
    try:
        candles = fetch_quotex_candles(symbol, limit=120)
    except CandleFeedError as exc:
        print(f"FEED CHECK FAILED: {exc}")
        return 1

    latest = candles.iloc[-1]
    print(f"SUCCESS: received {len(candles)} completed candles.")
    print(f"Latest candle UTC: {latest['timestamp'].isoformat()}")
    print("OHLC schema and freshness checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
