
from signal_engine import get_candles, ema, rsi

MIN_CANDLES = 30


def backtest(candles):
    candles = sorted(candles, key=lambda c: c["time"])
    closes = [float(c["close"]) for c in candles]

    wins = 0
    losses = 0
    signals = 0
    call_wins = 0
    call_losses = 0
    put_wins = 0
    put_losses = 0

    for i in range(MIN_CANDLES, len(closes) - 1):
        history = closes[:i + 1]

        fast = ema(history, 9)
        slow = ema(history, 21)
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

        entry = closes[i]
        exit_price = closes[i + 1]

        won = (
            exit_price > entry
            if direction == "CALL"
            else exit_price < entry
        )

        signals += 1

        if direction == "CALL":
            if won:
                call_wins += 1
            else:
                call_losses += 1
        else:
            if won:
                put_wins += 1
            else:
                put_losses += 1

        if won:
            wins += 1
            result = "WIN"
        else:
            losses += 1
            result = "LOSS"

        print(
            f"{direction} | Entry: {entry} | "
            f"Next Close: {exit_price} | {result}"
        )

    print("\n========== BACKTEST RESULTS ==========")
    print("PAIR: EURUSD_otc")
    print("CANDLES RECEIVED:", len(candles))
    print("TOTAL SIGNALS:", signals)
    print("CALL SIGNALS:", call_wins + call_losses)
    print("PUT SIGNALS:", put_wins + put_losses)
    print("WINS:", wins)
    print("LOSSES:", losses)

    if signals:
        print(f"OVERALL WIN RATE: {wins / signals * 100:.2f}%")
    else:
        print("OVERALL WIN RATE: No signals")

    call_total = call_wins + call_losses
    put_total = put_wins + put_losses

    if call_total:
        print(f"CALL WIN RATE: {call_wins / call_total * 100:.2f}%")
    else:
        print("CALL WIN RATE: No CALL signals")

    if put_total:
        print(f"PUT WIN RATE: {put_wins / put_total * 100:.2f}%")
    else:
        print("PUT WIN RATE: No PUT signals")

    print("======================================")


if __name__ == "__main__":
    print("Downloading historical candles...")
    historical_candles = get_candles()
    backtest(historical_candles)
    
