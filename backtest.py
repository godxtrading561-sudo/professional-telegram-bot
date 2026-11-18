
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

    for i in range(max(start, MIN_HISTORY), end - expiry):
        history = candles[:i + 1]

        try:
            signal = analyze_market(history)
        except (ValueError, RuntimeError):
            continue

        direction = signal["direction"]

        if direction not in ("CALL", "PUT"):
            continue

        # Signal is formed at candle i close.
        # Entry is next candle open.
        entry_index = i + 1
        exit_index = entry_index + expiry - 1

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
        })

    return trades


def report(trades, title):
    wins = sum(t["outcome"] == "WIN" for t in trades)
    losses = sum(t["outcome"] == "LOSS" for t in trades)
    ties = sum(t["outcome"] == "TIE" for t in trades)

    decided = wins + losses

    call = [t for t in trades if t["direction"] == "CALL"]
    put = [t for t in trades if t["direction"] == "PUT"]

    call_wins = sum(t["outcome"] == "WIN" for t in call)
    call_losses = sum(t["outcome"] == "LOSS" for t in call)

    put_wins = sum(t["outcome"] == "WIN" for t in put)
    put_losses = sum(t["outcome"] == "LOSS" for t in put)

    gross_profit = 0.0
    gross_loss = 0.0
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0

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

        if change > 0:
            gross_profit += change
        elif change < 0:
            gross_loss += abs(change)

    print(f"\n========== {title} ==========")
    print("TOTAL TRADES:", len(trades))
    print("WINS:", wins)
    print("LOSSES:", losses)
    print("TIES:", ties)

    if decided:
        print("WIN RATE:", round(wins / decided * 100, 2), "%")
    else:
        print("WIN RATE: No decided trades")

    call_total = call_wins + call_losses
    put_total = put_wins + put_losses

    print(
        "CALL WIN RATE:",
        round(call_wins / call_total * 100, 2) if call_total else "N/A"
    )
    print(
        "PUT WIN RATE:",
        round(put_wins / put_total * 100, 2) if put_total else "N/A"
    )

    if gross_loss:
        profit_factor = gross_profit / gross_loss
        print("PRICE-MOVE PROFIT FACTOR:", round(profit_factor, 3))
    elif gross_profit:
        print("PRICE-MOVE PROFIT FACTOR: Infinite (no losing price moves)")
    else:
        print("PRICE-MOVE PROFIT FACTOR: N/A")

    print("MAX DRAWDOWN (PRICE UNITS):", round(max_drawdown, 8))
    print("================================")


def main():
    print("Downloading historical candles...")
    candles = validate_candles(get_candles())

    count = len(candles)
    split = int(count * TRAIN_RATIO)

    print("PAIR:", PAIR)
    print("VALID CANDLES:", count)
    print("TRAIN CANDLES:", split)
    print("TEST CANDLES:", count - split)

    if split < MIN_HISTORY + 10:
        raise RuntimeError(
            "Not enough training data for chronological testing"
        )

    if count - split < 10:
        raise RuntimeError("Not enough unseen test candles")

    for expiry in EXPIRIES:
        train_trades = simulate(
            candles,
            MIN_HISTORY,
            split,
            expiry,
        )

        # Test uses only the later chronological section.
        # Earlier candles are retained as indicator warm-up history.
        test_trades = simulate(
            candles,
            split,
            count,
            expiry,
        )

        print(f"\n\n######## EXPIRY: {expiry} MINUTE(S) ########")

        report(train_trades, "TRAINING RESULTS")
        report(test_trades, "OUT-OF-SAMPLE TEST RESULTS")


if __name__ == "__main__":
    main()
        
