
"""
EUR/USD historical backtest using Dukascopy free data.
1-minute candles, chronological train/unseen testing.

Research only. NOT Quotex OTC data.
"""

import csv
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from signal_engine import (
    validate_candles,
    analyze_market,
    reset_diagnostics,
    get_diagnostics
)

EXPIRIES = (1, 2, 5)
TRAIN_RATIO = 0.70
MIN_HISTORY = 220

DATA_FILE = Path("eurusd_data.csv")


def download_candles():
    today = datetime.now(timezone.utc).date()

    # End date is exclusive. Avoid requesting the current day.
    date_to = today
    date_from = date_to - timedelta(days=7)

    print("Downloading Dukascopy EUR/USD M1 data")
    print("From:", date_from)
    print("To:", date_to)

    command = [
        "npx",
        "--yes",
        "dukascopy-node",
        "-i", "eurusd",
        "-from", date_from.isoformat(),
        "-to", date_to.isoformat(),
        "-t", "m1",
        "-p", "bid",
        "-f", "csv",
        "-dir", ".",
        "-fn", "eurusd_data",
        "-r", "3",
        "-rp", "1000",
        "-fr"
    ]

    # Remove an old file so stale data is never reused.
    if DATA_FILE.exists():
        DATA_FILE.unlink()

    subprocess.run(command, check=True)

    if not DATA_FILE.exists():
        raise RuntimeError(
            "Dukascopy did not create eurusd_data.csv"
        )

    candles = []

    with DATA_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise RuntimeError("Dukascopy CSV has no header.")

        print("CSV columns:", reader.fieldnames)

        for row in reader:
            try:
                timestamp = int(float(row["timestamp"]))

                candle_time = datetime.fromtimestamp(
                    timestamp / 1000,
                    tz=timezone.utc
                ).isoformat()

                candles.append({
                    "time": candle_time,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"])
                })

            except (KeyError, TypeError, ValueError, OverflowError):
                continue

    candles = validate_candles(candles)

    # Remove duplicate timestamps and sort chronologically.
    unique = {
        candle["time"]: candle
        for candle in candles
    }

    candles = sorted(
        unique.values(),
        key=lambda candle: candle["time"]
    )

    if not candles:
        raise RuntimeError(
            "No valid OHLC candles downloaded. "
            "Check Dukascopy availability or CSV columns."
        )

    bullish = sum(
        c["close"] > c["open"] for c in candles
    )
    bearish = sum(
        c["close"] < c["open"] for c in candles
    )
    doji = sum(
        c["close"] == c["open"] for c in candles
    )

    print("\n========== DATA QUALITY ==========")
    print("Total valid candles:", len(candles))
    print("Bullish:", bullish)
    print("Bearish:", bearish)
    print("Doji:", doji)
    print("First candle:", candles[0])
    print("Last candle:", candles[-1])

    if bullish + bearish == 0:
        raise RuntimeError("All candles are flat.")

    return candles


def print_diagnostics(label):
    print(f"\n========== {label} DIAGNOSTICS ==========")

    for name, count in get_diagnostics().items():
        print(f"{name}: {count}")


def simulate(candles, start, end, expiry, label):
    reset_diagnostics()

    wins = 0
    losses = 0
    ties = 0
    trades = []

    i = max(start, MIN_HISTORY - 1)

    while i + expiry < end:
        # Only information available at signal time.
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

            # Avoid overlapping trades.
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


def show_results(label, stats):
    print(f"\n========== {label} ==========")
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
    candles = download_candles()

    if len(candles) < MIN_HISTORY + 40:
        raise RuntimeError(
            f"Only {len(candles)} candles received. "
            "Not enough data for testing."
        )

    split = int(len(candles) * TRAIN_RATIO)

    print("\n========== DATA SUMMARY ==========")
    print("Total:", len(candles))
    print("Training:", split)
    print("Unseen:", len(candles) - split)

    for expiry in EXPIRIES:
        print(f"\n========== {expiry}-MINUTE EXPIRY ==========")

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

        show_results("TRAIN RESULTS", train)
        show_results("UNSEEN RESULTS", unseen)

        save_csv(
            f"trades_{expiry}m_unseen.csv",
            unseen["log"]
        )

    print("\n========== BACKTEST COMPLETE ==========")
    print("Research only; no future accuracy is guaranteed.")
    print("Dukascopy EUR/USD is not Quotex OTC data.")
    print("Payout, spread, slippage and execution delay are not modeled.")


if __name__ == "__main__":
    main()
                                
