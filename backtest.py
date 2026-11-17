
from signal_engine import get_candles, ema, rsi

MIN_CANDLES = 30


def backtest(candles):
    candles = sorted(candles, key=lambda c: c["time"])
    closes = [float(c["close"]) for c in candles]

    wins = 0
    losses = 0
    signals = 0

    for i in range(MIN_CANDLES, len(closes) - 1):
        history = closes[:i + 1]

        fast = ema(history, 9)
        slow = ema(history, 21)

        # Align both EMA series to the same candles
        fast_aligned = fast[-len(slow):]

        fast_previous = fast_aligned[-2]
        fast_now = fast_aligned[-1]
        slow_previous = slow[-2]
        slow_now = slow[-1]

        current_rsi = rsi(history, 14)

        direction = None

        if (
            fast_previous <= slow_previous
            and fast_now > slow_now
            and 50 < current_rsi < 70
        ):
            direction = "CALL"

        elif (
            fast_previous >= slow_previous
            and fast_now < slow_now
            and 30 < current_rsi < 50
        ):
            direction = "PUT"

        if direction is None:
            continue

        # Entry at current candle close;
        # evaluate using the next candle close.
        entry = closes[i]
        exit_price = closes[i + 1]

        if direction == "CALL":
            won = exit_price > entry
        else:
            won = exit_price < entry

        signals += 1

        if won:
            wins += 1
        else:
            losses += 1

        print(
            f"Signal: {direction} | "
            f"Entry: {entry} | Exit: {exit_price} | "
            f"{'WIN' if won else 'LOSS'}"
        )

    print("\n========== BACKTEST RESULTS ==========")
    print("PAIR: EURUSD_otc")
    print("CANDLES:", len(candles))
    print("TOTAL SIGNALS:", signals)
    print("WINS:", wins)
    print("LOSSES:", losses)

    if signals:
        accuracy = (wins / signals) * 100
        print(f"WIN RATE: {accuracy:.2f}%")
    else:
        print("WIN RATE: Not available - no signals")

    print("======================================")


if __name__ == "__main__":
    print("Downloading historical candles...")
    historical_candles = get_candles()
    backtest(historical_candles)
      
