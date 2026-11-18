
"""
Professional Signal Engine
Research only: EUR/USD Yahoo data.
Not Quotex OTC data. No guaranteed accuracy.
"""

from math import isfinite


MIN_CANDLES = 220


def validate_candles(candles):
    """Validate and clean OHLC candles."""
    clean = []

    for candle in candles:
        try:
            item = {
                "time": str(candle.get("time", "")),
                "open": float(candle["open"]),
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": float(candle["close"]),
            }

            values = [
                item["open"], item["high"],
                item["low"], item["close"]
            ]

            if not all(isfinite(v) and v > 0 for v in values):
                continue

            if item["high"] < max(item["open"], item["close"]):
                continue

            if item["low"] > min(item["open"], item["close"]):
                continue

            if item["high"] < item["low"]:
                continue

            clean.append(item)

        except (KeyError, TypeError, ValueError):
            continue

    return clean


def ema(values, period):
    """Calculate Exponential Moving Average."""
    if len(values) < period:
        return []

    multiplier = 2 / (period + 1)
    result = [sum(values[:period]) / period]

    for value in values[period:]:
        result.append(
            (value - result[-1]) * multiplier + result[-1]
        )

    return [None] * (period - 1) + result


def calculate_rsi(closes, period=14):
    """Calculate RSI."""
    if len(closes) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (
            (avg_gain * (period - 1)) + gains[i]
        ) / period
        avg_loss = (
            (avg_loss * (period - 1)) + losses[i]
        ) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def analyze_market(candles):
    """
    Return CALL, PUT or NO SIGNAL.
    Uses only candles supplied to this function.
    """

    candles = validate_candles(candles)

    if len(candles) < MIN_CANDLES:
        return {
            "direction": None,
            "reason": "Not enough candle history"
        }

    closes = [c["close"] for c in candles]
    opens = [c["open"] for c in candles]

    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)
    ema200 = ema(closes, 200)

    rsi = calculate_rsi(closes, 14)

    if rsi is None:
        return {
            "direction": None,
            "reason": "RSI unavailable"
        }

    last_close = closes[-1]
    last_open = opens[-1]

    e9 = ema9[-1]
    e21 = ema21[-1]
    e50 = ema50[-1]
    e200 = ema200[-1]

    previous_close = closes[-2]

    bullish_trend = (
        last_close > e200 and
        e50 > e200 and
        e9 > e21
    )

    bearish_trend = (
        last_close < e200 and
        e50 < e200 and
        e9 < e21
    )

    bullish_candle = last_close > last_open
    bearish_candle = last_close < last_open

    bullish_momentum = last_close > previous_close
    bearish_momentum = last_close < previous_close

    # Conservative CALL conditions
    if (
        bullish_trend
        and bullish_candle
        and bullish_momentum
        and 50 <= rsi <= 68
    ):
        return {
            "direction": "CALL",
            "reason": (
                "Bullish EMA trend, RSI confirmation "
                "and positive candle momentum"
            ),
            "rsi": round(rsi, 2),
            "ema9": round(e9, 6),
            "ema21": round(e21, 6),
            "ema50": round(e50, 6),
            "ema200": round(e200, 6)
        }

    # Conservative PUT conditions
    if (
        bearish_trend
        and bearish_candle
        and bearish_momentum
        and 32 <= rsi <= 50
    ):
        return {
            "direction": "PUT",
            "reason": (
                "Bearish EMA trend, RSI confirmation "
                "and negative candle momentum"
            ),
            "rsi": round(rsi, 2),
            "ema9": round(e9, 6),
            "ema21": round(e21, 6),
            "ema50": round(e50, 6),
            "ema200": round(e200, 6)
        }

    return {
        "direction": None,
        "reason": "No clear setup",
        "rsi": round(rsi, 2),
        "ema9": round(e9, 6),
        "ema21": round(e21, 6),
        "ema50": round(e50, 6),
        "ema200": round(e200, 6)
            }
        
