
import os
import math
import requests

API_KEY = os.environ["OTCHARTS_API_KEY"]
API_URL = "https://otcharts.com/v1/candles"

PAIR = "EURUSD_otc"
TIMEFRAME = 60
CANDLE_LIMIT = 1000

MIN_CANDLES = 220
MIN_SCORE = 7


# ---------------- DATA ----------------

def validate_candles(candles):
    cleaned = []
    seen = set()

    for candle in candles:
        try:
            item = {
                "time": candle["time"],
                "open": float(candle["open"]),
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": float(candle["close"]),
            }

            values = [
                item["open"], item["high"],
                item["low"], item["close"]
            ]

            if not all(math.isfinite(v) for v in values):
                continue

            if item["high"] < max(values):
                continue

            if item["low"] > min(values):
                continue

            if item["time"] in seen:
                continue

            seen.add(item["time"])
            cleaned.append(item)

        except (KeyError, TypeError, ValueError):
            continue

    return sorted(cleaned, key=lambda x: x["time"])


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
        raise RuntimeError("Market symbol mismatch")

    candles = validate_candles(data.get("candles", []))

    print("Requested:", CANDLE_LIMIT)
    print("Received valid candles:", len(candles))

    if len(candles) < MIN_CANDLES:
        raise RuntimeError("Not enough valid candles")

    return candles


# ---------------- INDICATORS ----------------

def ema(values, period):
    if len(values) < period:
        raise ValueError("Not enough EMA data")

    multiplier = 2 / (period + 1)
    result = [sum(values[:period]) / period]

    for value in values[period:]:
        result.append(
            value * multiplier
            + result[-1] * (1 - multiplier)
        )

    return result


def rsi(values, period=14):
    changes = [
        values[i] - values[i - 1]
        for i in range(1, len(values))
    ]

    gains = [max(x, 0) for x in changes]
    losses = [max(-x, 0) for x in changes]

    gain = sum(gains[:period]) / period
    loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        gain = (gain * (period - 1) + gains[i]) / period
        loss = (loss * (period - 1) + losses[i]) / period

    if loss == 0:
        return 100.0 if gain else 50.0

    rs = gain / loss
    return 100 - (100 / (1 + rs))


def macd(values, fast=12, slow=26, signal=9):
    fast_line = ema(values, fast)
    slow_line = ema(values, slow)

    fast_line = fast_line[-len(slow_line):]

    line = [
        a - b for a, b in zip(fast_line, slow_line)
    ]

    signal_line = ema(line, signal)

    return line[-1], signal_line[-1]


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
        raise ValueError("Not enough ATR data")

    value = sum(ranges[:period]) / period

    for item in ranges[period:]:
        value = (value * (period - 1) + item) / period

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
        raise ValueError("Not enough ADX data")

    tr = sum(tr_values[:period])
    plus = sum(plus_dm[:period])
    minus = sum(minus_dm[:period])

    dx_values = []

    for i in range(period, len(tr_values)):
        tr += (tr_values[i] - tr) / period
        plus += (plus_dm[i] - plus) / period
        minus += (minus_dm[i] - minus) / period

        pdi = 100 * plus / tr if tr else 0
        mdi = 100 * minus / tr if tr else 0
        total = pdi + mdi

        dx_values.append(
            100 * abs(pdi - mdi) / total if total else 0
        )

    if len(dx_values) < period:
        raise ValueError("Not enough ADX values")

    value = sum(dx_values[:period]) / period

    for item in dx_values[period:]:
        value = (value * (period - 1) + item) / period

    return value


# ---------------- SUPPORT / RESISTANCE ----------------

def find_levels(candles, lookback=100, strength=2):
    sample = candles[-lookback:]
    supports = []
    resistances = []

    for i in range(strength, len(sample) - strength):
        current = sample[i]

        left = sample[i - strength:i]
        right = sample[i + 1:i + strength + 1]

        if all(current["low"] < x["low"] for x in left + right):
            supports.append(current["low"])

        if all(current["high"] > x["high"] for x in left + right):
            resistances.append(current["high"])

    return supports, resistances


def nearest_level(price, levels):
    if not levels:
        return None

    return min(levels, key=lambda level: abs(price - level))


# ---------------- SNR / SUPPLY / DEMAND ----------------

def analyze_zones(candles, current_atr):
    supports, resistances = find_levels(candles)

    price = candles[-1]["close"]
    tolerance = max(current_atr * 0.35, price * 0.00005)

    support = nearest_level(price, supports)
    resistance = nearest_level(price, resistances)

    near_support = (
        support is not None
        and abs(price - support) <= tolerance
    )

    near_resistance = (
        resistance is not None
        and abs(price - resistance) <= tolerance
    )

    # Simplified swing-based supply and demand zones.
    demand_zone = None
    supply_zone = None

    recent = candles[-60:]

    for i in range(2, len(recent) - 2):
        candle = recent[i]
        following = recent[i + 1:i + 3]

        upward_move = (
            min(x["close"] for x in following) - candle["high"]
        )

        downward_move = (
            candle["low"] - max(x["close"] for x in following)
        )

        if upward_move > current_atr:
            demand_zone = (candle["low"], candle["high"])

        if downward_move > current_atr:
            supply_zone = (candle["low"], candle["high"])

    in_demand = (
        demand_zone is not None
        and demand_zone[0] - tolerance <= price <= demand_zone[1] + tolerance
    )

    in_supply = (
        supply_zone is not None
        and supply_zone[0] - tolerance <= price <= supply_zone[1] + tolerance
    )

    # SNR flip: price crossing a previous swing level.
    previous = candles[-2]

    support_flip = any(
        previous["close"] < level <= price
        for level in resistances
    )

    resistance_flip = any(
        previous["close"] > level >= price
        for level in supports
    )

    return {
        "support": support,
        "resistance": resistance,
        "near_support": near_support,
        "near_resistance": near_resistance,
        "demand_zone": demand_zone,
        "supply_zone": supply_zone,
        "in_demand": in_demand,
        "in_supply": in_supply,
        "support_flip": support_flip,
        "resistance_flip": resistance_flip,
    }


# ---------------- CANDLESTICK PATTERNS ----------------

def candlestick_analysis(candles):
    current = candles[-1]
    previous = candles[-2]

    body = abs(current["close"] - current["open"])
    candle_range = current["high"] - current["low"]

    if candle_range <= 0:
        return "NONE"

    upper_wick = current["high"] - max(
        current["open"], current["close"]
    )
    lower_wick = min(
        current["open"], current["close"]
    ) - current["low"]

    bullish_engulfing = (
        previous["close"] < previous["open"]
        and current["close"] > current["open"]
        and current["open"] <= previous["close"]
        and current["close"] >= previous["open"]
    )

    bearish_engulfing = (
        previous["close"] > previous["open"]
        and current["close"] < current["open"]
        and current["open"] >= previous["close"]
        and current["close"] <= previous["open"]
    )

    hammer = (
        lower_wick >= body * 2
        and upper_wick <= body
        and current["close"] > current["open"]
    )

    shooting_star = (
        upper_wick >= body * 2
        and lower_wick <= body
        and current["close"] < current["open"]
    )

    if bullish_engulfing:
        return "BULLISH_ENGULFING"

    if bearish_engulfing:
        return "BEARISH_ENGULFING"

    if hammer:
        return "HAMMER"

    if shooting_star:
        return "SHOOTING_STAR"

    return "NONE"


# ---------------- CHART PATTERNS ----------------

def chart_pattern_analysis(candles, current_atr):
    supports, resistances = find_levels(candles, lookback=80)

    if len(candles) < 20:
        return "NONE"

    price = candles[-1]["close"]
    tolerance = current_atr * 0.35

    # Approximate double top / double bottom.
    recent_highs = sorted(
        [x["high"] for x in candles[-30:]],
        reverse=True
    )[:2]

    recent_lows = sorted(
        [x["low"] for x in candles[-30:]]
    )[:2]

    if (
        abs(recent_highs[0] - recent_highs[1]) <= tolerance
        and price < recent_highs[0]
    ):
        return "POSSIBLE_DOUBLE_TOP"

    if (
        abs(recent_lows[0] - recent_lows[1]) <= tolerance
        and price > recent_lows[0]
    ):
        return "POSSIBLE_DOUBLE_BOTTOM"

    if resistances and price > max(resistances):
        return "RESISTANCE_BREAKOUT"

    if supports and price < min(supports):
        return "SUPPORT_BREAKDOWN"

    return "NONE"


# ---------------- CONFLUENCE ENGINE ----------------

def analyze_market(candles):
    candles = validate_candles(candles)

    if len(candles) < MIN_CANDLES:
        raise ValueError(
            f"Need at least {MIN_CANDLES} valid candles"
        )

    closes = [x["close"] for x in candles]

    e9 = ema(closes, 9)
    e21 = ema(closes, 21)
    e50 = ema(closes, 50)
    e200 = ema(closes, 200)

    current_rsi = rsi(closes)
    macd_line, macd_signal = macd(closes)
    current_atr = atr(candles)
    current_adx = adx(candles)

    current = candles[-1]

    zones = analyze_zones(candles, current_atr)
    candle_pattern = candlestick_analysis(candles)
    chart_pattern = chart_pattern_analysis(candles, current_atr)

    bullish_score = 0
    bearish_score = 0
    reasons = []

    # Trend indicators
    if e9[-1] > e21[-1] > e50[-1] > e200[-1]:
        bullish_score += 2
        reasons.append("Bullish EMA alignment")

    if e9[-1] < e21[-1] < e50[-1] < e200[-1]:
        bearish_score += 2
        reasons.append("Bearish EMA alignment")

    # RSI
    if 52 < current_rsi < 68:
        bullish_score += 1

    if 32 < current_rsi < 48:
        bearish_score += 1

    # MACD
    if macd_line > macd_signal:
        bullish_score += 1

    if macd_line < macd_signal:
        bearish_score += 1

    # ADX trend strength
    if current_adx >= 20:
        if e9[-1] > e21[-1]:
            bullish_score += 1
        elif e9[-1] < e21[-1]:
            bearish_score += 1

    # Support and resistance
    if zones["near_support"]:
        bullish_score += 2
        reasons.append("Near support")

    if zones["near_resistance"]:
        bearish_score += 2
        reasons.append("Near resistance")

    # SNR flips
    if zones["support_flip"]:
        bullish_score += 2
        reasons.append("Resistance turned support")

    if zones["resistance_flip"]:
        bearish_score += 2
        reasons.append("Support turned resistance")

    # Supply and demand
    if zones["in_demand"]:
        bullish_score += 2
        reasons.append("Demand zone")

    if zones["in_supply"]:
        bearish_score += 2
        reasons.append("Supply zone")

    # Candlestick confirmation
    if candle_pattern in (
        "BULLISH_ENGULFING", "HAMMER"
    ):
        bullish_score += 2
        reasons.append(candle_pattern)

    if candle_pattern in (
        "BEARISH_ENGULFING", "SHOOTING_STAR"
    ):
        bearish_score += 2
        reasons.append(candle_pattern)

    # Chart pattern confirmation
    if chart_pattern in (
        "POSSIBLE_DOUBLE_BOTTOM", "RESISTANCE_BREAKOUT"
    ):
        bullish_score += 2
        reasons.append(chart_pattern)

    if chart_pattern in (
        "POSSIBLE_DOUBLE_TOP", "SUPPORT_BREAKDOWN"
    ):
        bearish_score += 2
        reasons.append(chart_pattern)

    # Avoid extreme candle volatility.
    candle_range = current["high"] - current["low"]
    volatility_ok = (
        current_atr > 0
        and candle_range <= current_atr * 2
    )

    direction = "NO SIGNAL"

    if (
        bullish_score >= MIN_SCORE
        and bullish_score > bearish_score
        and volatility_ok
    ):
        direction = "CALL"

    elif (
        bearish_score >= MIN_SCORE
        and bearish_score > bullish_score
        and volatility_ok
    ):
        direction = "PUT"

    return {
        "pair": PAIR,
        "timeframe": "1 Minute",
        "direction": direction,
        "bullish_score": bullish_score,
        "bearish_score": bearish_score,
        "minimum_score": MIN_SCORE,
        "reason": ", ".join(reasons) if reasons else "No strong confluence",
        "candlestick_pattern": candle_pattern,
        "chart_pattern": chart_pattern,
        "support": zones["support"],
        "resistance": zones["resistance"],
        "demand_zone": zones["demand_zone"],
        "supply_zone": zones["supply_zone"],
        "near_support": zones["near_support"],
        "near_resistance": zones["near_resistance"],
        "in_demand": zones["in_demand"],
        "in_supply": zones["in_supply"],
        "support_flip": zones["support_flip"],
        "resistance_flip": zones["resistance_flip"],
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
        
