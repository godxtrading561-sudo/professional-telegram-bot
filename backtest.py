
from signal_engine import (
    get_candles,
    validate_candles,
    analyze_market,
)

PAIR = "EURUSD_otc"
MIN_HISTORY = 220
EXPIRIES = (1, 2, 5)
TRAIN_RATIO = 0.70


def simulate(candles, start, end, expiry):
    trades = []
    next_available_entry = start

    for i in range(max(start, MIN_HISTORY - 1), end - expiry):
        entry_index = i + 1
        exit_index = entry_index + expiry - 1

        # Prevent overlapping trades in this expiry test.
        if entry_index < next_available_entry:
            continue

        history = candles[:i + 1]

        try:
            signal = analyze_market(history)
        except (ValueError, RuntimeError, KeyError):
            continue

        direction = signal.get("direction")

        if direction not in ("CALL", "PUT"):
            continue

        entry = candles[entry_index]["open"]
        exit_price = candles[exit_index]["close"]

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
            "time": candles[entry_index]["time"],
            "direction": direction,
            "entry": entry,
            "exit": exit_price,
            "outcome": outcome,
            "expiry": expiry,
            "score": (
                signal.get("bullish_score", 0)
                if direction == "CALL"
                else signal.get("bearish_score", 0)
            ),
        })

        next_available_entry = exit_index + 1

    return trades


def report(trades, title):
    wins = sum(t["outcome"] == "WIN" for t in trades)
    losses = sum(t["outcome"] == "LOSS" for t in trades)
    ties = sum(t["outcome"] == "TIE" for t in trades)

    decided = wins + losses

    calls = [t for t in trades if t["direction"] == "CALL"]
    puts = [t for t in trades if t["direction"] == "PUT"]

    call_wins = sum(t["outcome"] == "WIN" for t in calls)
    call_losses = sum(t["outcome"] == "LOSS" for t in calls)

    put_wins = sum(t["outcome"] == "WIN" for t in puts)
    put_losses = sum(t["outcome"] == "LOSS" for t in puts)

    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    consecutive_losses = 0
    max_consecutive_losses = 0

    for trade in trades:
        if trade["outcome"] == "TIE":
            continue

        if trade["direction"] == "CALL":
            change = trade["exit"] - trade["entry"]
        else:
            change = trade["entry"] - trade["exit"]

        equity += change
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)

        if trade["outcome"] == "LOSS":
            consecutive_losses += 1
            max_consecutive_losses = max(
                max_consecutive_losses,
                consecutive_losses,
            )
        else:
            consecutive_losses = 0

    print(f"\n========== {title} ==========")
    print("TOTAL TRADES:", len(trades))
    print("WINS:", wins)
    print("LOSSES:", losses)
    print("TIES:", ties)

    if decided:
        print("WIN RATE:", round(wins / decided * 100, 2), "%")
    else:
        print("WIN RATE: N/A")

    call_total = call_wins + call_losses
    put_total = put_wins + put_losses

    print(
        "CALL WIN RATE:",
        round(call_wins / call_total * 100, 2) if call_total else "N/A",
    )
    print(
        "PUT WIN RATE:",
        round(put_wins / put_total * 100, 2) if put_total else "N/A",
    )

    print("MAX DRAWDOWN (PRICE UNITS):", round(max_drawdown, 8))
    print("MAX CONSECUTIVE LOSSES:", max_consecutive_losses)
    print("================================")


def main():
    print("Downloading historical candles...")

    candles = validate_candles(get_candles())
    count = len(candles)
    split = int(count * TRAIN_RATIO)

    print("PAIR:", PAIR)
    print("VALID CANDLES:", count)
    print("TRAIN CANDLES:", split)
    print("UNSEEN TEST CANDLES:", count - split)

    if split < MIN_HISTORY + 10:
        raise RuntimeError("Not enough training history")

    if count - split < 10:
        raise RuntimeError("Not enough unseen test history")

    for expiry in EXPIRIES:
        train_trades = simulate(
            candles,
            MIN_HISTORY - 1,
            split,
            expiry,
        )

        test_trades = simulate(
            candles,
            split,
            count,
            expiry,
        )

        print(f"\n######## EXPIRY: {expiry} MINUTE(S) ########")
        report(train_trades, "TRAINING RESULTS")
        report(test_trades, "UNSEEN TEST RESULTS")


if __name__ == "__main__":
    main()
    
