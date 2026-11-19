
"""
Professional EUR/USD Backtest with Candle Diagnostics.

Data: Yahoo Finance EUR/USD (EURUSD=X)
Research only: Not Quotex OTC data.
No live trading and no guaranteed accuracy.
"""

import csv
import yfinance as yf

from signal_engine import (
    validate_candles,
    analyze_market,
    reset_diagnostics,
    get_diagnostics
)

EXPIRIES = (1, 2, 5)
TRAIN_RATIO = 0.70
MIN_HISTORY = 220
SYMBOL = "EURUSD=X"


def fetch_free_candles():
    print(f"Downloading {SYMBOL} 1-minute historical data...")

    df = yf.download(
        SYMBOL,
        period="7d",
        interval="1m",
        auto_adjust=False,
        progress=False,
        threads=False
    )

    if df is None or df.empty:
        raise RuntimeError("Yahoo Finance returned no candles.")

    # Handle Yahoo Finance MultiIndex columns safely.
    if getattr(df.columns, "nlevels", 1) > 1:
        if SYMBOL in df.columns.get_level_values(-1):
            df = df.xs(
                SYMBOL,
                axis=1,
                level=-1
            )
        else:
            df.columns = df.columns.get_level_values(0)

    required = ["Open", "High", "Low", "Close"]

    missing = [name for name in required if name not in df.columns]

    if missing:
        raise RuntimeError(f"Missing Yahoo columns: {missing}")

    candles = []

    for timestamp, row in df.iterrows():
        try:
            candle = {
                "time": timestamp.isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"])
            }

            candles.append(candle)

        except (TypeError, ValueError, KeyError):
            continue

    candles = validate_candles(candles)

    print(f"\nDownloaded valid candles: {len(candles)}")

    if not candles:
        raise RuntimeError("No valid OHLC candles received.")

    # Inspect candle body data.
    bullish = sum(
        1 for c in candles if c["close"] > c["open"]
    )

    bearish = sum(
        1 for c in candles if c["close"] < c["open"]
    )

    doji = sum(
        1 for c in candles if c["close"] == c["open"]
    )

    print("\n========== CANDLE DATA CHECK ==========")
    print("Bullish candles:", bullish)
    print("Bearish candles:", bearish)
    print("Doji candles:", doji)

    print("\nFirst 5 candles:")
    for candle in candles[:5]:
        print(candle)

    if bullish + bearish == 0:
        raise RuntimeError(
            "All candles have equal Open and Close. "
            "Cannot run a meaningful candle-based backtest."
        )

    return candles


def print_diagnostics(label):
    print(f"\n========== {label} DIAGNOSTICS ==========")

    stats = get_diagnostics()

    for name, count in stats.items():
        print(f"{name}: {count}")


def simulate(candles, start, end, expiry, label):
    reset_diagnostics()

    wins = 0
    losses = 0
    ties = 0
    trades = []

    i = max(start, MIN_HISTORY - 1)

    while i + expiry < end:

        # Analyze only data available at signal time.
        signal = analyze_market(candles[:i + 1])

        direction = signal.get("direction")

        entry_i = i + 1
        exit_i = entry_i + expiry - 1

        if direction in ("CALL", "PUT") and exit_i < end:

            entry = candles[entry_i]["open"]
            exit_price = candles[exit_i]["close"]

            if exit_price == entry:
                result = "TIE"
                ties += 1

            elif (
                direction == "CALL" and exit_price > entry
            ) or (
                direction == "PUT" and exit_price < entry
            ):
                result = "WIN"
                wins += 1

            else:
                result = "LOSS"
                losses += 1

            trades.append({
                "signal_time": candles[i]["time"],
                "entry_time": candles[entry_i]["time"],
                "direction": direction,
                "entry": entry,
                "exit": exit_price,
                "result": result,
                "reason": signal.get("reason", "")
            })

            # Do not overlap trades.
            i = exit_i

        else:
            i += 1

    decided = wins + losses

    stats = {
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "trades": len(trades),
        "win_rate": (
            round(100 * wins / decided, 2)
            if decided else 0.0
        ),
        "log": trades
    }

    print_diagnostics(label)

    return stats


def print_results(label, stats):
    print(f"\n========== {label} RESULTS ==========")
    print("Trades:", stats["trades"])
    print("Wins:", stats["wins"])
    print("Losses:", stats["losses"])
    print("Ties:", stats["ties"])
    print("Win rate:", str(stats["win_rate"]) + "%")


def save_csv(filename, trades):
    fields = [
        "signal_time",
        "entry_time",
        "direction",
        "entry",
        "exit",
        "result",
        "reason"
    ]

    with open(
        filename,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields
        )

        writer.writeheader()
        writer.writerows(trades)

    print(f"Saved {filename}: {len(trades)} trades")


def main():
    candles = fetch_free_candles()

    if len(candles) < MIN_HISTORY + 40:
        raise RuntimeError(
            f"Only {len(candles)} candles received. "
            "Not enough data for this test."
        )

    split = int(len(candles) * TRAIN_RATIO)

    print("\n========== DATA SUMMARY ==========")
    print("Total candles:", len(candles))
    print("Training candles:", split)
    print("Unseen candles:", len(candles) - split)

    for expiry in EXPIRIES:

        print(
            f"\n\n========== {expiry}-MINUTE EXPIRY =========="
        )

        train = simulate(
            candles,
            MIN_HISTORY - 1,
            split,
            expiry,
            f"TRAIN {expiry}m"
        )

        unseen = simulate(
            candles,
            max(split, MIN_HISTORY - 1),
            len(candles),
            expiry,
            f"UNSEEN {expiry}m"
        )

        print_results("TRAIN", train)
        print_results("UNSEEN", unseen)

        save_csv(
            f"trades_{expiry}m_unseen.csv",
            unseen["log"]
        )

    print("\n========== BACKTEST COMPLETE ==========")
    print(
        "Research only. Historical results do not guarantee "
        "future performance. Payout, spread, slippage and "
        "execution delay are not included."
    )
    print(
        "Yahoo EUR/USD data is not Quotex OTC market data."
    )


if __name__ == "__main__":
    main()
        
