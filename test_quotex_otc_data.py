"""Single-request smoke test for the Quotex OTC M1 candle feed.
This test never substitutes Yahoo/ordinary FX data.
"""
import os

from otc_data import fetch_quotex_otc_candles, DEFAULT_SYMBOL


if __name__ == "__main__":
    if os.getenv("QUANTEX_API_KEY", "").strip():
        source = "QUANTEX (Quotex candle permission required)"
    elif os.getenv("OTCHARTS_API_KEY", "").strip():
        source = "OTCharts (independent Quotex OTC data provider)"
    else:
        raise RuntimeError("Neither QUANTEX_API_KEY nor OTCHARTS_API_KEY is configured in GitHub Secrets.")

    candles = fetch_quotex_otc_candles(DEFAULT_SYMBOL, limit=120)
    print("QUOTEX OTC DATA TEST: PASS")
    print(f"Provider: {source}")
    print(f"Symbol: {DEFAULT_SYMBOL}")
    print("Timeframe: M1 / 60 seconds")
    print(f"Completed valid OHLC candles: {len(candles)}")
    print(f"Latest candle UTC: {candles.index[-1].isoformat()}")
    print("Validation: fresh, completed, ordered, gap-free, positive OHLC.")
