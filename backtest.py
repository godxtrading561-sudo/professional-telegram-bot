
from signal_engine import get_candles, ema, rsi

MIN_CANDLES = 30


def backtest(candles):
    candles = sorted(candles, key=lambda c: c["time"])

    wins = 0
    losses = 0
    ties = 0

    call_wins = 0
    call_losses = 0
    put_wins = 0
    put_losses = 0

    signals = 0

    for i in range(MIN_CANDLES, len(candles) - 1):

        history = candles[:i + 1]
        closes = [float(c["close"]) for c in history]

        fast = ema(closes, 9)
        slow = ema(closes, 21)

        fast_aligned = fast[-len(slow):]

        fast_previous = fast_aligned[-2]
        fast_now = fast_aligned[-1]

        slow_previous = slow[-2]
        slow_now = slow[-1]

        current_rsi = rsi(closes, 14)

        direction = None

        # CALL condition
        if (
            fast_previous <= slow_previous
            and fast_now > slow_now
            and 50 < current_rsi < 70
        ):
            direction = "CALL"

        # PUT condition
        elif (
            fast_previous >= slow_previous
            and fast_now < slow_now
            and 30 < current_rsi < 50
        ):
            direction = "PUT"

        if direction is None:
            continue

        # Entry at next candle OPEN.
        # Exit at that candle CLOSE (1-minute test).
        next_candle = candles[i + 1]

        entry = float(next_candle["open"])
        exit_price = float(next_candle["close"])

        signals += 1

        if exit_price == entry:
            ties += 1
            result = "TIE"

        elif direction == "CALL":
            if exit_price > entry:
                wins += 1
                call_wins += 1
                result = "WIN"
            else:
                losses += 1
                call_losses += 1
                result = "LOSS"

        else:
            if exit_price < entry:
                wins += 1
                put_wins += 1
                result = "WIN"
            else:
                losses += 1
                put_losses += 1
                result = "LOSS"

        print(
            f"{direction} | Entry: {entry} | "
            f"Exit: {exit_price} | {result}"
        )

    print("\n========== BACKTEST RESULTS ==========")
    print("PAIR: EURUSD_otc")
    print("CANDLES RECEIVED:", len(candles))
    print("TOTAL SIGNALS:", signals)
    print("WINS:", wins)
    print("LOSSES:", losses)
    print("TIES:", ties)

    decided = wins + losses

    if decided:
        print(
            f"OVERALL WIN RATE: "
            f"{wins / decided * 100:.2f}%"
        )
    else:
        print("OVERALL WIN RATE: No decided trades")

    call_total = call_wins + call_losses
    put_total = put_wins + put_losses

    if call_total:
        print(
            f"CALL WIN RATE: "
            f"{call_wins / call_total * 100:.2f}%"
        )
    else:
        print("CALL WIN RATE: No CALL trades")

    if put_total:
        print(
            f"PUT WIN RATE: "
            f"{put_wins / put_total * 100:.2f}%"
        )
    else:
        print("PUT WIN RATE: No PUT trades")

    print("======================================")


if __name__ == "__main__":
    print("Downloading historical candles...")
    historical_candles = get_candles()
    backtest(historical_candles)
    
