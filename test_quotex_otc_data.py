"""One-request smoke test for the Quotex OTC candle feed."""
from otc_data import fetch_quotex_otc_candles, DEFAULT_SYMBOL

if __name__ == "__main__":
    candles = fetch_quotex_otc_candles(DEFAULT_SYMBOL, limit=120)
    print("QUOTEX OTC DATA TEST: PASS")
    print(f"Symbol: {DEFAULT_SYMBOL}")
    print(f"Completed 1-minute candles: {len(candles)}")
    print(f"Latest candle UTC: {candles.index[-1].isoformat()}")
    print("Source: QUANTEX if configured, otherwise OTCharts Quotex book (never Yahoo FX spot)")
