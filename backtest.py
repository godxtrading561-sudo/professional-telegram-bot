
"""
EUR/USD historical backtest using Yahoo Finance.
Research only: not Quotex OTC data and not live trading.
Yahoo Finance 1-minute history is limited (typically 7 days).
"""
import csv
from datetime import datetime, timezone
import yfinance as yf

from signal_engine import validate_candles, analyze_market

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

    # Handle both normal and MultiIndex column formats.
    if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
        df.columns = df.columns.get_level_values(0)

    required = ["Open", "High", "Low", "Close"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise RuntimeError(f"Missing Yahoo columns: {missing}")

    candles = []
    for timestamp, row in df.iterrows():
        try:
            candles.append({
                "time": timestamp.isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"])
            })
        except (TypeError, ValueError):
            continue

    candles = validate_candles(candles)
    print(f"Downloaded {len(candles)} valid candles.")
    return candles


def simulate(candles, start, end, expiry):
    wins = losses = ties = 0
    trades = []
    i = max(start, MIN_HISTORY - 1)

    while i + expiry < end:
        # Engine receives only candles available at signal time.
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
    return {
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "trades": len(trades),
        "win_rate": round(100 * wins / decided, 2) if decided else 0.0,
        "log": trades
    }


def save_csv(filename, trades):
    fields = [
        "signal_time", "entry_time", "direction",
        "entry", "exit", "result", "reason"
    ]
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(trades)
    print(f"Saved: {filename} ({len(trades)} trades)")


def main():
    candles = fetch_free_candles()

    if len(candles) < MIN_HISTORY + 40:
        raise RuntimeError(
            f"Only {len(candles)} candles received. "
            "Not enough data for a meaningful test."
        )

    split = int(len(candles) * TRAIN_RATIO)
    print(
        f"Valid candles: {len(candles)} | "
        f"Training: {split} | Unseen: {len(candles) - split}"
    )

    for expiry in EXPIRIES:
        train = simulate(candles, MIN_HISTORY - 1, split, expiry)
        unseen = simulate(candles, max(split, MIN_HISTORY - 1), len(candles), expiry)

        print(f"\n{expiry}-minute expiry")
        for label, stats in (("TRAIN", train), ("UNSEEN", unseen)):
            print(
                f"{label}: trades={stats['trades']} "
                f"wins={stats['wins']} losses={stats['losses']} "
                f"ties={stats['ties']} win_rate={stats['win_rate']}%"
            )

        save_csv(f"trades_{expiry}m_unseen.csv", unseen["log"])

    print(
        "\nResearch only. Results do not guarantee future performance. "
        "Payout, spread, slippage and execution delay are not included."
    )


if __name__ == "__main__":
    main()
