
import os
import glob
import pandas as pd

from signal_engine import PAIRS, analyze_market, prepare_candles

DATA_FOLDER = "data"
EXPIRY_CANDLES = 1
MIN_CANDLES = 220


def load_data(pair):
    path = os.path.join(DATA_FOLDER, f"{pair}.csv")

    if not os.path.exists(path):
        print(f"Missing data file: {path}")
        return None

    df = pd.read_csv(path)
    df.columns = [c.lower().strip() for c in df.columns]

    if "timestamp" in df.columns:
        df = df.sort_values("timestamp")

    return prepare_candles(df)


def run_backtest(pair, df):
    trades = []

    if len(df) <= MIN_CANDLES + EXPIRY_CANDLES:
        print(f"{pair}: Not enough candles")
        return trades

    # Only use candles available at the signal time.
    for i in range(MIN_CANDLES, len(df) - EXPIRY_CANDLES):
        history = df.iloc[:i + 1]
        result = analyze_market(history)

        direction = result["direction"]

        if direction not in ("CALL", "PUT"):
            continue

        entry = float(df.iloc[i + 1]["open"])
        exit_price = float(
            df.iloc[i + EXPIRY_CANDLES]["close"]
        )

        if direction == "CALL":
            outcome = (
                "WIN" if exit_price > entry
                else "LOSS" if exit_price < entry
                else "TIE"
            )
        else:
            outcome = (
                "WIN" if exit_price < entry
                else "LOSS" if exit_price > entry
                else "TIE"
            )

        trades.append({
            "pair": pair,
            "signal": direction,
            "score": result["score"],
            "entry": entry,
            "exit": exit_price,
            "outcome": outcome,
            "rsi": result.get("rsi"),
            "reasons": ", ".join(result.get("reasons", [])),
        })

    return trades


def show_results(all_trades):
    if not all_trades:
        print("\nNo trades generated.")
        return

    df = pd.DataFrame(all_trades)

    wins = (df["outcome"] == "WIN").sum()
    losses = (df["outcome"] == "LOSS").sum()
    ties = (df["outcome"] == "TIE").sum()

    decided = wins + losses
    accuracy = (wins / decided * 100) if decided else 0

    print("\n========== BACKTEST RESULTS ==========")
    print(f"Total signals : {len(df)}")
    print(f"Wins          : {wins}")
    print(f"Losses        : {losses}")
    print(f"Ties          : {ties}")
    print(f"Accuracy      : {accuracy:.2f}%")
    print("======================================")

    print("\nPAIR-WISE RESULTS")

    for pair, group in df.groupby("pair"):
        pair_wins = (group["outcome"] == "WIN").sum()
        pair_losses = (group["outcome"] == "LOSS").sum()
        pair_decided = pair_wins + pair_losses
        pair_accuracy = (
            pair_wins / pair_decided * 100
            if pair_decided else 0
        )

        print(
            f"{pair}: {pair_wins} wins, "
            f"{pair_losses} losses, "
            f"{pair_accuracy:.2f}% accuracy"
        )

    df.to_csv("backtest_trades.csv", index=False)
    print("\nSaved: backtest_trades.csv")


def main():
    all_trades = []

    for pair in PAIRS:
        print(f"\nTesting {pair}...")

        df = load_data(pair)

        if df is None:
            continue

        trades = run_backtest(pair, df)
        all_trades.extend(trades)

        print(f"Signals generated: {len(trades)}")

    show_results(all_trades)


if __name__ == "__main__":
    main()
