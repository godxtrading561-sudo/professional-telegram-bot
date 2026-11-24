import os
import glob
import pandas as pd

from signal_engine import analyze_market, prepare_candles

DATA_FOLDER = "data"
OUTPUT_FILE = "backtest_trades.csv"


def backtest_file(path):
    df = prepare_candles(pd.read_csv(path))
    trades = []

    for i in range(200, len(df) - 2):
        signal = analyze_market(df.iloc[:i + 1])

        if not signal:
            continue

        entry_candle = df.iloc[i + 2]
        entry = float(entry_candle["open"])
        exit_price = float(entry_candle["close"])

        if exit_price == entry:
            result = "TIE"
        elif signal["direction"] == "CALL":
            result = "WIN" if exit_price > entry else "LOSS"
        else:
            result = "WIN" if exit_price < entry else "LOSS"

        trades.append({
            "pair": os.path.basename(path).replace(".csv", ""),
            "direction": signal["direction"],
            "score": signal["score"],
            "entry": entry,
            "exit": exit_price,
            "result": result,
        })

    return trades


def main():
    files = glob.glob(os.path.join(DATA_FOLDER, "*.csv"))

    if not files:
        raise SystemExit("No candle CSV files found in data/.")

    all_trades = []

    for path in files:
        print("Testing", path)
        all_trades.extend(backtest_file(path))

    if not all_trades:
        print("No signals generated.")
        return

    df = pd.DataFrame(all_trades)
    df.to_csv(OUTPUT_FILE, index=False)

    wins = int((df["result"] == "WIN").sum())
    losses = int((df["result"] == "LOSS").sum())
    ties = int((df["result"] == "TIE").sum())

    decisive = wins + losses
    accuracy = wins / decisive * 100 if decisive else 0

    print("\n========== BACKTEST REPORT ==========")
    print("Total signals:", len(df))
    print("Wins:", wins)
    print("Losses:", losses)
    print("Ties:", ties)
    print(f"Accuracy excluding ties: {accuracy:.2f}%")

    print("\nPAIR-WISE RESULTS")
    for pair, group in df.groupby("pair"):
        w = int((group["result"] == "WIN").sum())
        l = int((group["result"] == "LOSS").sum())
        n = w + l
        acc = w / n * 100 if n else 0
        print(f"{pair}: {acc:.2f}% ({w} wins / {l} losses)")

    print("\nDIRECTION-WISE RESULTS")
    for direction, group in df.groupby("direction"):
        w = int((group["result"] == "WIN").sum())
        l = int((group["result"] == "LOSS").sum())
        n = w + l
        acc = w / n * 100 if n else 0
        print(f"{direction}: {acc:.2f}% ({w} wins / {l} losses)")

    print("Report saved:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
