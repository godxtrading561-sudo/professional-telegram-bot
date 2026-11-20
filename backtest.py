
"""
Improved EUR/USD backtest.
Separate CALL/PUT results.
Missing-minute protection.
Research only; not Quotex OTC data.
"""

import csv
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from signal_engine import validate_candles, analyze_market, reset_diagnostics

EXPIRIES = (1, 2, 5)
TRAIN_RATIO = 0.70
MIN_HISTORY = 220
DATA_FILE = Path("eurusd_data.csv")


def download_candles():
    today = datetime.now(timezone.utc).date()
    date_to = today
    date_from = date_to - timedelta(days=30)

    command = [
        "npx", "--yes", "dukascopy-node",
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

    if DATA_FILE.exists():
        DATA_FILE.unlink()

    print("Downloading 30-day Dukascopy EUR/USD data...")
    subprocess.run(command, check=True)

    if not DATA_FILE.exists():
        raise RuntimeError("Historical data file not found.")

    candles = []

    with DATA_FILE.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            try:
                timestamp = int(float(row["timestamp"]))
                candle_time = datetime.fromtimestamp(
                    timestamp / 1000,
                    tz=timezone.utc
                )

                candles.append({
                    "time": candle_time.isoformat(),
                    "timestamp": int(candle_time.timestamp()),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"])
                })
            except (KeyError, ValueError, TypeError, OverflowError):
                continue

    candles = validate_candles(candles)

    unique = {c["time"]: c for c in candles}
    candles = sorted(
        unique.values(),
        key=lambda c: c["timestamp"]
    )

    if len(candles) < MIN_HISTORY + 100:
        raise RuntimeError("Not enough historical candles.")

    print("Valid candles:", len(candles))
    print("First:", candles[0]["time"])
    print("Last:", candles[-1]["time"])

    return candles


def has_contiguous_minutes(candles, start, end):
    for j in range(start, end):
        difference = (
            candles[j + 1]["timestamp"]
            - candles[j]["timestamp"]
        )

        if difference != 60:
            return False

    return True


def simulate(candles, start, end, expiry):
    reset_diagnostics()

    trades = []
    i = max(start, MIN_HISTORY - 1)

    while i + expiry < end:
        signal = analyze_market(candles[:i + 1])
        direction = signal.get("direction")

        entry_i = i + 1
        exit_i = entry_i + expiry - 1

        if direction not in ("CALL", "PUT"):
            i += 1
            continue

        if exit_i >= end:
            break

        # Reject trades crossing missing minutes.
        if not has_contiguous_minutes(candles, i, exit_i):
            i += 1
            continue

        entry = candles[entry_i]["open"]
        exit_price = candles[exit_i]["close"]

        if abs(exit_price - entry) < 1e-10:
            result = "TIE"
        elif (
            direction == "CALL" and exit_price > entry
        ) or (
            direction == "PUT" and exit_price < entry
        ):
            result = "WIN"
        else:
            result = "LOSS"

        trades.append({
            "signal_time": candles[i]["time"],
            "entry_time": candles[entry_i]["time"],
            "exit_time": candles[exit_i]["time"],
            "direction": direction,
            "expiry_minutes": expiry,
            "entry": entry,
            "exit": exit_price,
            "result": result,
            "reason": signal.get("reason", "")
        })

        i = exit_i

    return trades


def show_stats(label, trades):
    print(f"\n===== {label} =====")

    for direction in ("CALL", "PUT"):
        selected = [
            t for t in trades
            if t["direction"] == direction
        ]

        wins = sum(t["result"] == "WIN" for t in selected)
        losses = sum(t["result"] == "LOSS" for t in selected)
        ties = sum(t["result"] == "TIE" for t in selected)

        decided = wins + losses
        accuracy = 100 * wins / decided if decided else 0

        print(
            f"{direction}: Trades={len(selected)}, "
            f"Wins={wins}, Losses={losses}, Ties={ties}, "
            f"Win rate={accuracy:.2f}%"
        )

    wins = sum(t["result"] == "WIN" for t in trades)
    losses = sum(t["result"] == "LOSS" for t in trades)
    ties = sum(t["result"] == "TIE" for t in trades)

    decided = wins + losses
    accuracy = 100 * wins / decided if decided else 0

    print("TOTAL TRADES:", len(trades))
    print("TOTAL WINS:", wins)
    print("TOTAL LOSSES:", losses)
    print("TOTAL TIES:", ties)
    print(f"OVERALL WIN RATE: {accuracy:.2f}%")


def save_reports(expiry, trades):
    fields = [
        "signal_time",
        "entry_time",
        "exit_time",
        "direction",
        "expiry_minutes",
        "entry",
        "exit",
        "result",
        "reason"
    ]

    for direction in ("CALL", "PUT"):
        selected = [
            t for t in trades
            if t["direction"] == direction
        ]

        filename = f"trades_{expiry}m_{direction.lower()}_unseen.csv"

        with open(
            filename, "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(selected)

        print("Saved:", filename, len(selected))


def main():
    candles = download_candles()

    split = int(len(candles) * TRAIN_RATIO)

    print("\nTOTAL CANDLES:", len(candles))
    print("TRAINING CANDLES:", split)
    print("UNSEEN CANDLES:", len(candles) - split)

    for expiry in EXPIRIES:
        print(f"\n========== {expiry}-MINUTE EXPIRY ==========")

        train = simulate(
            candles, MIN_HISTORY - 1, split, expiry
        )

        unseen = simulate(
            candles, split, len(candles), expiry
        )

        show_stats(f"TRAIN {expiry}m", train)
        show_stats(f"UNSEEN {expiry}m", unseen)

        save_reports(expiry, unseen)

    print("\nBACKTEST COMPLETE")
    print("Research only. No accuracy is guaranteed.")
    print("Dukascopy EUR/USD is not Quotex OTC data.")
    print("Payout, spread and execution delay are not modeled.")


if __name__ == "__main__":
    main()
