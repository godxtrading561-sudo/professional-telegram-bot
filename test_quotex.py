from config import TRADING_PAIRS
from bot import fetch_candles


def main():
    print("Checking available market candle feeds...")

    for pair, ticker in TRADING_PAIRS.items():
        print(f"\nChecking {pair}: {ticker}")
        candles = fetch_candles(ticker)

        if candles is None:
            print("No usable candle data.")
        else:
            print("Candles received:", len(candles))
            print(candles.tail(3).to_string(index=False))

    print(
        "\nNote: Yahoo Finance data is ordinary Forex data, "
        "not verified Quotex OTC data."
    )


if __name__ == "__main__":
    main()
