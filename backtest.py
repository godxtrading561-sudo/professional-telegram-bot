
"""
EUR/USD 1-minute historical backtest using Dukascopy.
Free historical data; no API key required.

Research only. This is NOT Quotex OTC data.
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
    date_to = today - timedelta(days=1)
    date_from = date_to - timedelta(days=30)

    print("Downloading free Dukascopy EUR/USD 1-minute data...")
    print("From:", date_from)
    print("To:", date_to)

    command = [
        "npx", "--yes", "dukascopy-node",
        "-i", "eurusd",
        "-from", date_from.isoformat(),
        "-to", date_to.isoformat(),
        "-t", "m1",
        "-f", "csv",
        "-dir", ".",
        "-fn", DATA_FILE.name,
        "-r", "2",
        "-re"
    ]

    subprocess.run(command, check=True)

    if not DATA_FILE.exists():
        raise RuntimeError("Dukascopy CSV file was not created.")

    candles = []

    with DATA_FILE.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise RuntimeError("CSV has no header.")

        for row in reader:
            normalized = {
                str(k).strip().lower(): v
                for k, v in row.items()
                if k is not None
            }

            time_value = (
                normalized.get("timestamp")
                or normalized.get("time")
                or normalized.get("datetime")
                or normalized.get("date")
            )

            try:
                candles.append({
                    "time": str(time_value or ""),
                    "open": float(normalized["open"]),
                    "high": float(normalized["high"]),
                    "low": float(normalized["low"]),
                    "close": float(normalized["close"])
                })
            except (KeyError, TypeError, ValueError):
                continue

    candles = validate_candles(candles)

    if not candles:
        raise RuntimeError(
            "No valid OHLC candles found. Check Dukascopy CSV format."
        )

    unique = {}
    for candle in candles:
        unique[candle["time"]] = candle

    candles = sorted(
        unique.values(),
        key=lambda c: c["time"]
    )

    bullish = sum(c["close"] > c["open"] for c in candles)
    bearish = sum(c["close"] < c["open"] for c in candles)
    doji = sum(c["close"] == c["open"] for c in candles)

    print("\n========== DATA QUALITY ==========")
    print("Valid candles:", len(candles))
    print("Bullish:", bullish)
    print("Bearish:", bearish)
    print("Doji:", doji)
    print("First candle:", candles[0])
    print("Last candle:", candles[-1])

    if bullish + bearish == 0:
        raise RuntimeError("All candles are flat. Backtest stopped.")

    return candles


def print_diagnostics(label):
    print(f"\n--- {label} DIAGNOSTICS ---")
    for name, count in get_diagnostics().items():
        print(f"{name}: {count}")


def simulate(candles, start, end, expiry, label):
    reset_diagnostics()

    wins = losses = ties = 0
    trades = []
    i = max(start, MIN_HISTORY - 1)

    while i + expiry < end:
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

            i = exit_i
        else:
            i += 1

    decided = wins + losses

    stats = {
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "trades": len(trades),
        "win_rate": round(100 * wins / decided, 2) if decided else 0.0,
        "log": trades
    }

    print_diagnostics(label)
    return stats


def save_csv(filename, trades):
    fields = [
        "signal_time", "entry_time", "direction",
        "entry", "exit", "result", "reason"
    ]

    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(trades)

    print(f"Saved {filename}: {len(trades)} trades")


def show_results(label, stats):
    print(f"\n{label}")
    print("Trades:", stats["trades"])
    print("Wins:", stats["wins"])
    print("Losses:", stats["losses"])
    print("Ties:", stats["ties"])
    print("Win rate:", str(stats["win_rate"]) + "%")


def main():
    candles = download_candles()

    if len(candles) < MIN_HISTORY + 40:
        raise RuntimeError(
            f"Only {len(candles)} candles. More history is required."
        )

    split = int(len(candles) * TRAIN_RATIO)

    print("\nTraining candles:", split)
    print("Unseen candles:", len(candles) - split)

    for expiry in EXPIRIES:
        print(f"\n========== {expiry}-MINUTE EXPIRY ==========")

        train = simulate(
            candles, MIN_HISTORY - 1, split,
            expiry, f"TRAIN {expiry}m"
        )

        unseen = simulate(
            candles, max(split, MIN_HISTORY - 1),
            len(candles), expiry, f"UNSEEN {expiry}m"
        )

        show_results("TRAIN RESULTS", train)
        show_results("UNSEEN RESULTS", unseen)

        save_csv(
            f"trades_{expiry}m_unseen.csv",
            unseen["log"]
        )

    print("\nBacktest complete.")
    print("Research only. No future accuracy is guaranteed.")
    print("Dukascopy EUR/USD is not Quotex OTC data.")
    print("Payout, spread, slippage and execution delay are not modeled.")


if __name__ == "__main__":
    main()
  
