import os
import glob
import pandas as pd

from signal_engine import analyze_market, prepare_candles

DATA_DIR = "data"


def backtest_file(path):
    df = prepare_candles(pd.read_csv(path))
    rows = []

    for i in range(100, len(df) - 2):
        signal = analyze_market(df.iloc[:i + 1].copy())

        if not signal:
            continue

        alert_candle = df.iloc[i + 1]
        entry_candle = df.iloc[i + 2]

        entry = float(entry_candle["open"])
        exit_price = float(entry_candle["close"])

        if exit_price > entry:
            outcome = "WIN" if signal["direction"] == "CALL" else "LOSS"
        elif exit_price < entry:
            outcome = "WIN" if signal["direction"] == "PUT" else "LOSS"
        else:
            outcome = "TIE"

        rows.append({
            "pair": os.path.basename(path).replace(".csv", ""),
            "signal": signal["direction"],
            "score": signal["score"],
            "alert_candle_timestamp": alert_candle.get("timestamp", i + 1),
            "entry_timestamp": entry_candle.get("timestamp", i + 2),
            "entry": entry,
            "exit": exit_price,
            "outcome": outcome,
            "reasons": " | ".join(signal["reasons"])
        })

    return rows


def main():
    paths = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))

    if not paths:
        raise SystemExit(
            "No CSV files in data/. Expected timestamp,open,high,low,close."
        )

    trades = []

    for path in paths:
        print(f"Testing {path}")
        trades.extend(backtest_file(path))

    if not trades:
        print("No signals found.")
        return

    result = pd.DataFrame(trades)
    result.to_csv("backtest_trades.csv", index=False)

    decisive = result[result.outcome != "TIE"]
    wins = int((decisive.outcome == "WIN").sum())
    losses = int((decisive.outcome == "LOSS").sum())
    ties = int((result.outcome == "TIE").sum())

    accuracy = wins / len(decisive) * 100 if len(decisive) else 0

    print("\n===== BACKTEST SUMMARY =====")
    print(f"Total signals: {len(result)}")
    print(f"Wins: {wins} | Losses: {losses} | Ties: {ties}")
    print(f"Accuracy excluding ties: {accuracy:.2f}%")

    for direction, group in result.groupby("signal"):
        g = group[group.outcome != "TIE"]
        w = int((g.outcome == "WIN").sum())
        l = int((g.outcome == "LOSS").sum())
        acc = w / len(g) * 100 if len(g) else 0
        print(f"{direction}: {acc:.2f}% ({w} wins / {l} losses)")


if __name__ == "__main__":
    main()
