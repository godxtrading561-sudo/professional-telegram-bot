
import os
import requests
from datetime import datetime, timezone

API_KEY = os.environ["OTCHARTS_API_KEY"]
API_URL = "https://otcharts.com/v1/candles"

PAIR = "EURUSD_otc"
TIMEFRAME = 60
CANDLE_LIMIT = 1000


def get_candles():
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

    if data.get("symbol") != PAIR:
        raise RuntimeError("Wrong symbol returned by API")

    candles = validate_candles(data.get("candles", []))

    print("Requested:", CANDLE_LIMIT)
    print("Valid candles:", len(candles))

    if len(candles) < 220:
        raise RuntimeError("At least 220 valid candles required")

    return candles


def candle_timestamp(candle):
    value = candle["time"]

    if isinstance(value, (int, float)):
        value = float(value)
        return value / 1000 if value > 1e12 else value

    parsed = datetime.fromisoformat(
        str(value).replace("Z", "+00:00")
    )

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.timestamp()


def validate_candles(candles):
    unique = {}

    for candle in candles:
        try:
            timestamp = candle_timestamp(candle)

            o = float(candle["open"])
            h = float(candle["high"])
            low = float(candle["low"])
            c = float(candle["close"])

            if min(o, h, low, c) <= 0:
                continue

            if h < max(o, c, low) or low > min(o, c, h):
                continue

            unique[timestamp] = {
                "time": candle["time"],
                "open": o,
                "high": h,
                "low": low,
                "close": c,
            }

        except (KeyError, TypeError, ValueError):
            continue

    return [
        unique[t]
        for t in sorted(unique)
    ]


def ema(values, period):
    if len(values) < period:
        raise ValueError("Insufficient EMA data")

    multiplier = 2 / (period + 1)
    result = [sum(values[:period]) / period]

    for price in values[period:]:
        result.append(
            price * multiplier + result[-1] * (1 - multiplier)
        )

    return result


def rsi(values, period=14):
    changes = [
        values[i] - values[i - 1]
        for i in range(1, len(values))
    ]

    gains = [max(x, 0) for x in changes]
    losses = [max(-x, 0) for x in changes]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(values):
    fast = ema(values, 12)
    slow = ema(values, 26)

    aligned_fast = fast[-len(slow):]
    line = [
        a - b for a, b in zip(aligned_fast, slow)
    ]

    signal = ema(line, 9)

    return line[-1], signal[-1]


def atr(candles, period=14):
    ranges = []

    for i in range(1, len(candles)):
        current = candles[i]
        previous_close = candles[i - 1]["close"]

        ranges.append(max(
            current["high"] - current["low"],
            abs(current["high"] - previous_close),
            abs(current["low"] - previous_close),
        ))

    if len(ranges) < period:
        raise ValueError("Insufficient ATR data")

    value = sum(ranges[:period]) / period

    for current in ranges[period:]:
        value = (value * (period - 1) + current) / period

    return value


def adx(candles, period=14):
    tr_values = []
    plus_dm = []
    minus_dm = []

    for i in range(1, len(candles)):
        current = candles[i]
        previous = candles[i - 1]

        up = current["high"] - previous["high"]
        down = previous["low"] - current["low"]

        plus_dm.append(up if up > down and up > 0 else 0)
        minus_dm.append(down if down > up and down > 0 else 0)

        tr_values.append(max(
            current["high"] - current["low"],
            abs(current["high"] - previous["close"]),
            abs(current["low"] - previous["close"]),
        ))

    if len(tr_values) < period * 2:
        raise ValueError("Insufficient ADX data")

    tr = sum(tr_values[:period])
    plus = sum(plus_dm[:period])
    minus = sum(minus_dm[:period])

    dx_values = []

    for i in range(period, len(tr_values)):
        tr = tr - tr / period + tr_values[i]
        plus = plus - plus / period + plus_dm[i]
        minus = minus - minus / period + minus_dm[i]

        if tr == 0:
            dx_values.append(0)
            continue

        pdi = 100 * plus / tr
        mdi = 100 * minus / tr

        denominator = pdi + mdi
        dx_values.append(
            100 * abs(pdi - mdi) / denominator
            if denominator else 0
        )

    if len(dx_values) < period:
        raise ValueError("Insufficient ADX values")

    value = sum(dx_values[:period]) / period

    for current in dx_values[period:]:
        value = (value * (period - 1) + current) / period

    return value


def analyze_market(candles):
    candles = validate_candles(candles)

    if len(candles) < 220:
        raise ValueError("At least 220 candles required")

    closes = [c["close"] for c in candles]

    e9 = ema(closes, 9)
    e21 = ema(closes, 21)
    e50 = ema(closes, 50)
    e200 = ema(closes, 200)

    current_rsi = rsi(closes)
    macd_line, macd_signal = macd(closes)
    current_atr = atr(candles)
    current_adx = adx(candles)

    current = candles[-1]
    previous = candles[-2]

    direction = "NO SIGNAL"
    reason = "Insufficient confirmation"

    # Trend and momentum confirmation.
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

    # Avoid unusually large candles.
    candle_range = current["high"] - current["low"]
    volatility_ok = (
        current_atr > 0
        and candle_range <= current_atr * 2
    )

    if bullish and volatility_ok:
        direction = "CALL"
        reason = "Bullish trend, MACD, RSI and ADX confirmed"

    elif bearish and volatility_ok:
        direction = "PUT"
        reason = "Bearish trend, MACD, RSI and ADX confirmed"

    return {
        "pair": PAIR,
        "timeframe": "1 Minute",
        "direction": direction,
        "reason": reason,
        "rsi": round(current_rsi, 2),
        "adx": round(current_adx, 2),
        "atr": round(current_atr, 6),
        "macd": round(macd_line, 6),
        "macd_signal": round(macd_signal, 6),
        "ema9": round(e9[-1], 6),
        "ema21": round(e21[-1], 6),
        "ema50": round(e50[-1], 6),
        "ema200": round(e200[-1], 6),
        "candle_time": current["time"],
        "candles_analyzed": len(candles),
    }


if __name__ == "__main__":
    candles = get_candles()
    result = analyze_market(candles)

    print("\n========== PROFESSIONAL BOT ==========")

    for key, value in result.items():
        print(f"{key.upper()}: {value}")

    print("======================================")
    
