
import os
import requests

API_KEY = os.environ["OTCHARTS_API_KEY"]

API_URL = "https://otcharts.com/v1/candles"

PAIR = "EURUSD_otc"
TIMEFRAME = 60
CANDLE_LIMIT = 1000


def get_candles():
    print("Connecting to OTCharts...")

    response = requests.get(
        API_URL,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Accept": "application/json",
        },
        params={
            "venue": "quotex",
            "symbol": PAIR,
            "tf": TIMEFRAME,
            "limit": CANDLE_LIMIT,
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()
    candles = data.get("candles", [])

    if data.get("symbol") != PAIR:
        raise RuntimeError("Returned pair does not match requested pair")

    if len(candles) < 30:
        raise RuntimeError(
            f"Not enough candles received: {len(candles)}"
        )

    print("Requested candles:", CANDLE_LIMIT)
    print("Actually received:", len(candles))

    return candles


def ema(values, period):
    multiplier = 2 / (period + 1)
    result = [sum(values[:period]) / period]

    for price in values[period:]:
        result.append(
            price * multiplier
            + result[-1] * (1 - multiplier)
        )

    return result


def rsi(values, period=14):
    changes = [
        values[i] - values[i - 1]
        for i in range(1, len(values))
    ]

    gains = [max(change, 0) for change in changes]
    losses = [max(-change, 0) for change in changes]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (
            avg_gain * (period - 1) + gains[i]
        ) / period

        avg_loss = (
            avg_loss * (period - 1) + losses[i]
        ) / period

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0

    relative_strength = avg_gain / avg_loss

    return 100 - (100 / (1 + relative_strength))


def analyze_market(candles):
    candles = sorted(candles, key=lambda candle: candle["time"])

    closes = [
        float(candle["close"])
        for candle in candles
    ]

    fast_ema = ema(closes, 9)
    slow_ema = ema(closes, 21)

    # Align EMA9 and EMA21 to identical candle positions.
    fast_aligned = fast_ema[-len(slow_ema):]

    fast_previous = fast_aligned[-2]
    fast_now = fast_aligned[-1]

    slow_previous = slow_ema[-2]
    slow_now = slow_ema[-1]

    current_rsi = rsi(closes, 14)

    direction = "NO SIGNAL"
    reason = "Conditions not matched"

    if (
        fast_previous <= slow_previous
        and fast_now > slow_now
        and 50 < current_rsi < 70
    ):
        direction = "CALL"
        reason = "Bullish EMA crossover with RSI confirmation"

    elif (
        fast_previous >= slow_previous
        and fast_now < slow_now
        and 30 < current_rsi < 50
    ):
        direction = "PUT"
        reason = "Bearish EMA crossover with RSI confirmation"

    return {
        "pair": PAIR,
        "timeframe": "1 Minute",
        "direction": direction,
        "reason": reason,
        "rsi": round(current_rsi, 2),
        "ema9_previous": round(fast_previous, 6),
        "ema9": round(fast_now, 6),
        "ema21_previous": round(slow_previous, 6),
        "ema21": round(slow_now, 6),
        "candle_time": candles[-1]["time"],
    }


if __name__ == "__main__":
    print("Downloading Quotex candles...")

    candles = get_candles()
    result = analyze_market(candles)

    print("\n========== MARKET ANALYSIS ==========")

    for key, value in result.items():
        print(f"{key.upper()}: {value}")

    print("=====================================")
    
