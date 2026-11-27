"""Connectivity check for the configured Yahoo Finance 1-minute FX symbols."""
from config import TRADING_PAIRS
from yahoo_data import fetch_yahoo_candles, YahooDataError


def main():
    passed = []
    failed = []
    for pair, ticker in TRADING_PAIRS.items():
        try:
            candles = fetch_yahoo_candles(ticker, period="2d", interval="1m")
            if len(candles) < 60:
                failed.append(f"{pair}: only {len(candles)} completed candles")
            else:
                passed.append((pair, len(candles), candles.index[-1].isoformat()))
                print(f"PASS {pair}: {len(candles)} completed 1m candles; latest={candles.index[-1]}")
        except YahooDataError as exc:
            failed.append(f"{pair}: {exc}")
            print(f"FAIL {pair}: {exc}")
    print(f"\nYahoo FX data check: {len(passed)}/{len(TRADING_PAIRS)} pairs passed.")
    print("NOTE: Yahoo FX spot data is not Quotex OTC data.")
    if not passed:
        raise SystemExit("No Yahoo FX pairs returned usable data.")
    if failed:
        print("Some pairs unavailable; bot can scan available pairs only.")


if __name__ == "__main__":
    main()
