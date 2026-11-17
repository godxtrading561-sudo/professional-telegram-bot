
from signal_engine import (
    get_candles,
    validate_candles,
    ema,
    rsi,
    macd,
    atr,
    adx,
)

PAIR = "EURUSD_otc"
MIN_CANDLES = 220


def analyze_history(history):
    closes = [c["close"] for c in history]

    e9 = ema(closes, 9)
    e21 = ema(closes, 21)
    e50 = ema(closes, 50)
    e200 = ema(closes, 200)

    current_rsi = rsi(closes, 14)
    macd_line, macd_signal = macd(closes)
    current_atr = atr(history)
    current_adx = adx(history)

    current = history[-1]

    bullish = (
        e9[-1] > e21[-1] > e50[-1] > e200[-1]
        and current["close"] > e200[-1]
        and macd_line > macd_signal
        and 52 < current_rsi < 68
        and current_adx >= 20
        and current["close"] > current["open"]
    )

    bearish = (
        e9[-1] < e21[-1] < e50[-1] < e200[-1]
        and current["close"] < e200[-1]
        and macd_line < macd_signal
        and 32 < current_rsi < 48
        and current_adx >= 20
        and current["close"] < current["open"]
    )

    candle_range = current["high"] - current["low"]
    volatility_ok = (
        current_atr > 0
        and candle_range <= current_atr * 2
    )

    if bullish and volatility_ok:
        return "CALL"

    if bearish and volatility_ok:
        return "PUT"

    return None


def backtest(candles):
    candles = validate_candles(candles)

    if len(candles) < MIN_CANDLES + 2:
        raise RuntimeError("Not enough candles for backtest")

    wins = 0
    losses = 0
    ties = 0
    call_wins = 0
    call_losses = 0
    put_wins = 0
    put_losses = 0
    signals = 0

    print("Testing advanced EMA + RSI + MACD + ADX strategy")

    for i in range(MIN_CANDLES, len(candles) - 1):
        history = candles[:i + 1]

        direction = analyze_history(history)

        if direction is None:
            continue

        # Entry at next candle open, exit at next candle close.
        next_candle = candles[i + 1]

        entry = next_candle["open"]
        exit_price = next_candle["close"]

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
            f"{direction} | "
            f"Time: {next_candle['time']} | "
            f"Entry: {entry} | Exit: {exit_price} | {result}"
        )

    decided = wins + losses

    print("\n========== ADVANCED BACKTEST ==========")
    print("PAIR:", PAIR)
    print("CANDLES RECEIVED:", len(candles))
    print("TOTAL SIGNALS:", signals)
    print("WINS:", wins)
    print("LOSSES:", losses)
    print("TIES:", ties)

    if decided:
        print(
            f"OVERALL WIN RATE: {wins / decided * 100:.2f}%"
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
        print("CALL WIN RATE: No trades")

    if put_total:
        print(
            f"PUT WIN RATE: "
            f"{put_wins / put_total * 100:.2f}%"
        )
    else:
        print("PUT WIN RATE: No trades")

    print("=======================================")


if __name__ == "__main__":
    print("Downloading historical candles...")
    candles = get_candles()
    backtest(candles)
    
