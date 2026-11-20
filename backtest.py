
"""
Professional EUR/USD Backtest
30-day historical data from Dukascopy.
Separate CALL and PUT reports.
Missing-minute protection for indicator history and trades.
Research only. NOT Quotex OTC data.
"""

import csv
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from signal_engine import validate_candles, analyze_market

EXPIRIES = (1, 2, 5)
TRAIN_RATIO = 0.70
MIN_HISTORY = 220

DATA_FILE = Path("eurusd_data.csv")


def download_candles():
    today = datetime.now(timezone.utc).date()
    date_to = today
    date_from = date_to - timedelta(days=30)

    print("Downloading 30-day Dukascopy EUR/USD data...")
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

    if DATA_FILE.exists():
        DATA_FILE.unlink()

    subprocess.run(command, check=True)

    if not DATA_FILE.exists():
        raise RuntimeError("Dukascopy CSV file was not created.")

    raw_candles = []

    with DATA_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise RuntimeError("CSV header is missing.")

        print("CSV columns:", reader.fieldnames)

        for row in reader:
            try:
                timestamp = int(float(row["timestamp"]))

                candle_time = datetime.fromtimestamp(
                    timestamp / 1000,
                    tz=timezone.utc
                ).isoformat()

                raw_candles.append({
                    "time": candle_time,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"])
                })

            except (
                KeyError,
                TypeError,
                ValueError,
                OverflowError
            ):
                continue

    if not raw_candles:
        raise RuntimeError("No candles found in downloaded CSV.")

    # Remove duplicate times and sort.
    unique = {
        candle["time"]: candle
        for candle in raw_candles
    }

    sorted_candles = sorted(
        unique.values(),
        key=lambda candle: candle["time"]
    )

    candles = validate_candles(sorted_candles)

    # Restore Unix timestamp after validation.
    for candle in candles:
        candle["timestamp"] = int(
            datetime.fromisoformat(
                candle["time"]
            ).timestamp()
        )

    if len(candles) < MIN_HISTORY + 100:
        raise RuntimeError(
            f"Not enough valid candles: {len(candles)}"
        )

    bullish = sum(
        candle["close"] > candle["open"]
        for candle in candles
    )

    bearish = sum(
        candle["close"] < candle["open"]
        for candle in candles
    )

    doji = sum(
        candle["close"] == candle["open"]
        for candle in candles
    )

    gaps = sum(
        candles[i]["timestamp"]
        - candles[i - 1]["timestamp"] != 60
        for i in range(1, len(candles))
    )

    print("\n========== DATA QUALITY ==========")
    print("Valid candles:", len(candles))
    print("Bullish:", bullish)
    print("Bearish:", bearish)
    print("Doji:", doji)
    print("Missing-minute gaps:", gaps)
    print("First candle:", candles[0]["time"])
    print("Last candle:", candles[-1]["time"])

    return candles


def build_contiguous_starts(candles):
    """
    For every candle index, store the beginning
    of its current uninterrupted 1-minute segment.
    """
    starts = [0] * len(candles)

    for i in range(1, len(candles)):
        difference = (
            candles[i]["timestamp"]
            - candles[i - 1]["timestamp"]
        )

        if difference == 60:
            starts[i] = starts[i - 1]
        else:
            starts[i] = i

    return starts


def has_contiguous_minutes(candles, start, end):
    for index in range(start, end):
        difference = (
            candles[index + 1]["timestamp"]
            - candles[index]["timestamp"]
        )

        if difference != 60:
            return False

    return True


def simulate(candles, run_start, run_end, expiry, segment_starts):
    trades = []

    # Signals are evaluated at candle close.
    # Entry is at the next candle open.
    index = max(run_start, MIN_HISTORY - 1)

    while index + expiry < run_end:
        segment_start = segment_starts[index]

        # Do not calculate indicators across a data gap.
        contiguous_history = index - segment_start + 1

        if contiguous_history < MIN_HISTORY:
            index += 1
            continue

        entry_index = index + 1
        exit_index = entry_index + expiry - 1

        if exit_index >= run_end:
            break

        # Ensure signal candle, entry and expiry candles
        # form one uninterrupted minute sequence.
        if not has_contiguous_minutes(
            candles,
            index,
            exit_index
        ):
            index += 1
            continue

        # Only pass the uninterrupted history segment.
        history = candles[segment_start:index + 1]

        signal = analyze_market(history)
        direction = signal.get("direction")

        if direction not in ("CALL", "PUT"):
            index += 1
            continue

        entry_price = candles[entry_index]["open"]
        exit_price = candles[exit_index]["close"]

        if abs(exit_price - entry_price) < 1e-10:
            result = "TIE"

        elif (
            direction == "CALL"
            and exit_price > entry_price
        ) or (
            direction == "PUT"
            and exit_price < entry_price
        ):
            result = "WIN"

        else:
            result = "LOSS"

        trades.append({
            "signal_time": candles[index]["time"],
            "entry_time": candles[entry_index]["time"],
            "exit_time": candles[exit_index]["time"],
            "direction": direction,
            "expiry_minutes": expiry,
            "entry": entry_price,
            "exit": exit_price,
            "result": result,
            "reason": signal.get("reason", "")
        })

        # Next signal may be evaluated at the expiry candle close.
        # Its entry will be the following candle, so trades do not overlap.
        index = exit_index

    return trades


def show_stats(label, trades):
    print(f"\n========== {label} ==========")

    for direction in ("CALL", "PUT"):
        selected = [
            trade for trade in trades
            if trade["direction"] == direction
        ]

        wins = sum(
            trade["result"] == "WIN"
            for trade in selected
        )

        losses = sum(
            trade["result"] == "LOSS"
            for trade in selected
        )

        ties = sum(
            trade["result"] == "TIE"
            for trade in selected
        )

        decided = wins + losses

        accuracy = (
            100 * wins / decided
            if decided else 0
        )

        print(
            f"{direction}: "
            f"Trades={len(selected)}, "
            f"Wins={wins}, "
            f"Losses={losses}, "
            f"Ties={ties}, "
            f"Win rate={accuracy:.2f}%"
        )

    wins = sum(
        trade["result"] == "WIN"
        for trade in trades
    )

    losses = sum(
        trade["result"] == "LOSS"
        for trade in trades
    )

    ties = sum(
        trade["result"] == "TIE"
        for trade in trades
    )

    decided = wins + losses

    accuracy = (
        100 * wins / decided
        if decided else 0
    )

    print("\nTOTAL TRADES:", len(trades))
    print("WINS:", wins)
    print("LOSSES:", losses)
    print("TIES:", ties)
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
            trade for trade in trades
            if trade["direction"] == direction
        ]

        filename = (
            f"trades_{expiry}m_"
            f"{direction.lower()}_unseen.csv"
        )

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
            writer.writerows(selected)

        print(
            f"Saved {filename}: "
            f"{len(selected)} trades"
        )


def main():
    candles = download_candles()

    split = int(len(candles) * TRAIN_RATIO)

    if split <= MIN_HISTORY:
        raise RuntimeError("Training data is too short.")

    segment_starts = build_contiguous_starts(candles)

    print("\n========== DATA SUMMARY ==========")
    print("Total candles:", len(candles))
    print("Training candles:", split)
    print("Unseen candles:", len(candles) - split)

    for expiry in EXPIRIES:
        print(
            f"\n========== {expiry}-MINUTE EXPIRY =========="
        )

        train_trades = simulate(
            candles,
            MIN_HISTORY - 1,
            split,
            expiry,
            segment_starts
        )

        unseen_trades = simulate(
            candles,
            split,
            len(candles),
            expiry,
            segment_starts
        )

        show_stats(
            f"TRAIN {expiry}m",
            train_trades
        )

        show_stats(
            f"UNSEEN {expiry}m",
            unseen_trades
        )

        save_reports(expiry, unseen_trades)

    print("\n========== BACKTEST COMPLETE ==========")
    print("Research only. Accuracy is not guaranteed.")
    print("Dukascopy EUR/USD is NOT Quotex OTC data.")
    print("Payout, spread and execution delay are not modeled.")


if __name__ == "__main__":
    main()
