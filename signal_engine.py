
"""
Professional Signal Engine v2
Research only: EUR/USD historical data.
Not Quotex OTC data. No guaranteed accuracy.
"""

from math import isfinite

MIN_CANDLES = 220

DIAGNOSTICS = {
    "total_checks": 0,
    "insufficient_history": 0,
    "call_trend_pass": 0,
    "put_trend_pass": 0,
    "call_candle_pass": 0,
    "put_candle_pass": 0,
    "call_momentum_pass": 0,
    "put_momentum_pass": 0,
    "call_rsi_pass": 0,
    "put_rsi_pass": 0,
    "call_signals": 0,
    "put_signals": 0,
    "no_signal": 0,
}


def reset_diagnostics():
    for key in DIAGNOSTICS:
        DIAGNOSTICS[key] = 0


def get_diagnostics():
    return DIAGNOSTICS.copy()


def validate_candles(candles):
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

            o, h, l, c = (
                item["open"], item["high"],
                item["low"], item["close"]
            )

            if not all(isfinite(v) and v > 0 for v in (o, h, l, c)):
                continue

            if h < max(o, c) or l > min(o, c) or h < l:
                continue

            clean.append(item)

        except (KeyError, TypeError, ValueError):
            continue

    return clean


def ema(values, period):
    if len(values) < period:
        return []

    multiplier = 2 / (period + 1)
    result = [None] * (period - 1)
    current = sum(values[:period]) / period
    result.append(current)

    for value in values[period:]:
        current = (value - current) * multiplier + current
        result.append(current)

    return result


def calculate_rsi(closes, period=14):
    if len(closes) <= period:
        return None

    changes = [
        closes[i] - closes[i - 1]
        for i in range(1, len(closes))
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

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_atr(candles, period=14):
    if len(candles) <= period:
        return None

    true_ranges = []

    for i in range(1, len(candles)):
        current = candles[i]
        previous_close = candles[i - 1]["close"]

        true_range = max(
            current["high"] - current["low"],
            abs(current["high"] - previous_close),
            abs(current["low"] - previous_close),
        )
        true_ranges.append(true_range)

    atr = sum(true_ranges[:period]) / period

    for value in true_ranges[period:]:
        atr = ((atr * (period - 1)) + value) / period

    return atr


def analyze_market(candles):
    DIAGNOSTICS["total_checks"] += 1

    candles = validate_candles(candles)

    if len(candles) < MIN_CANDLES:
        DIAGNOSTICS["insufficient_history"] += 1
        return {
            "direction": None,
            "reason": "Not enough candle history",
        }

    closes = [c["close"] for c in candles]
    opens = [c["open"] for c in candles]

    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema50 = ema(closes, 50)
    ema200 = ema(closes, 200)

    rsi = calculate_rsi(closes, 14)
    atr = calculate_atr(candles, 14)

    if rsi is None or atr is None or atr <= 0:
        return {
            "direction": None,
            "reason": "Indicator calculation unavailable",
        }

    last = candles[-1]
    previous = candles[-2]

    last_close = last["close"]
    last_open = last["open"]
    previous_close = previous["close"]

    e9 = ema9[-1]
    e21 = ema21[-1]
    e50 = ema50[-1]
    e200 = ema200[-1]

    previous_e9 = ema9[-2]
    previous_e21 = ema21[-2]
    previous_e50 = ema50[-2]

    candle_range = last["high"] - last["low"]
    body = abs(last_close - last_open)

    if candle_range <= 0:
        DIAGNOSTICS["no_signal"] += 1
        return {
            "direction": None,
            "reason": "Invalid candle range",
        }

    body_strength = body / candle_range

    # Trend direction and EMA slope
    bullish_trend = (
        last_close > e200
        and e50 > e200
        and e9 > e21
        and e21 > previous_e21
        and e50 >= previous_e50
    )

    bearish_trend = (
        last_close < e200
        and e50 < e200
        and e9 < e21
        and e21 < previous_e21
        and e50 <= previous_e50
    )

    bullish_candle = (
        last_close > last_open
        and body_strength >= 0.55
    )

    bearish_candle = (
        last_close < last_open
        and body_strength >= 0.55
    )

    bullish_momentum = (
        last_close > previous_close
        and e9 > previous_e9
    )

    bearish_momentum = (
        last_close < previous_close
        and e9 < previous_e9
    )

    # Avoid extreme RSI entries and very small candle ranges
    call_rsi = 52 <= rsi <= 66
    put_rsi = 34 <= rsi <= 48

    volatility_ok = candle_range >= atr * 0.35

    if bullish_trend:
        DIAGNOSTICS["call_trend_pass"] += 1

    if bearish_trend:
        DIAGNOSTICS["put_trend_pass"] += 1

    if bullish_candle:
        DIAGNOSTICS["call_candle_pass"] += 1

    if bearish_candle:
        DIAGNOSTICS["put_candle_pass"] += 1

    if bullish_momentum:
        DIAGNOSTICS["call_momentum_pass"] += 1

    if bearish_momentum:
        DIAGNOSTICS["put_momentum_pass"] += 1

    if call_rsi:
        DIAGNOSTICS["call_rsi_pass"] += 1

    if put_rsi:
        DIAGNOSTICS["put_rsi_pass"] += 1

    common = {
        "rsi": round(rsi, 2),
        "ema9": round(e9, 6),
        "ema21": round(e21, 6),
        "ema50": round(e50, 6),
        "ema200": round(e200, 6),
    }

    if (
        bullish_trend
        and bullish_candle
        and bullish_momentum
        and call_rsi
        and volatility_ok
    ):
        DIAGNOSTICS["call_signals"] += 1
        return {
            "direction": "CALL",
            "reason": "Bullish trend, EMA slope, strong candle, momentum and RSI confirmed",
            **common,
        }

    if (
        bearish_trend
        and bearish_candle
        and bearish_momentum
        and put_rsi
        and volatility_ok
    ):
        DIAGNOSTICS["put_signals"] += 1
        return {
            "direction": "PUT",
            "reason": "Bearish trend, EMA slope, strong candle, momentum and RSI confirmed",
            **common,
        }

    DIAGNOSTICS["no_signal"] += 1

    return {
        "direction": None,
        "reason": "No clear setup or volatility filter failed",
        **common,
    }

