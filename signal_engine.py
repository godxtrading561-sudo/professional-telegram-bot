
import os
import requests
from datetime import datetime, timezone

API_KEY = os.environ["OTCHARTS_API_KEY"]
API_URL = "https://otcharts.com/v1/candles"

PAIR = "EURUSD_otc"
TIMEFRAME = 60
CANDLE_LIMIT = 1000

# Enable only if OTCharts candle time represents candle OPEN time.
# If the API uses candle CLOSE time, keep this False.
EXCLUDE_FORMING_CANDLE = False


def parse_time(value):
    """Convert candle time into UTC timestamp seconds."""
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 1e12:
            timestamp /= 1000
        return timestamp

    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.timestamp()
        except ValueError:
            raise ValueError(f"Invalid candle time: {value}")

    raise ValueError(f"Unsupported candle time: {value}")


def validate_candles(candles):
    """Validate, deduplicate and sort OHLC candles."""
    unique = {}

    for candle in candles:
        try:
            timestamp = parse_time(candle["time"])

            open_price = float(candle["open"])
            high_price = float(candle["high"])
            low_price = float(candle["low"])
            close_price = float(candle["close"])

            prices = [
                open_price, high_price,
                low_price, close_price
            ]

            if any(price <= 0 for price in prices):
                continue

            if high_price < max(open_price, close_price, low_price):
                continue

            if low_price > min(open_price, close_price, high_price):
                continue

            clean = {
                "time": candle["time"],
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
            }

            unique[timestamp] = clean

        except (KeyError, TypeError, ValueError):
            continue

    result = [
        unique[timestamp]
        for timestamp in sorted(unique)
    ]

    if EXCLUDE_FORMING_CANDLE and result:
        now = datetime.now(timezone.utc).timestamp()
        latest_open = parse_time(result[-1]["time"])

        if latest_open + TIMEFRAME > now:
            result.pop()

    if len(result) < 30:
        raise RuntimeError(
            f"Not enough valid candles: {len(result)}"
        )

    return result


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

    if data.get("symbol") != PAIR:
        raise RuntimeError("Returned pair does not match requested pair")

    raw_candles = data.get("candles", [])
    candles = validate_candles(raw_candles)

    print("Requested candles:", CANDLE_LIMIT)
    print("Received candles:", len(raw_candles))
    print("Valid unique candles:", len(candles))

    return candles


def ema(values, period):
    if len(values) < period:
        raise ValueError("Not enough values for EMA")

    multiplier = 2 / (period + 1)
    result = [sum(values[:period]) / period]

    for price in values[period:]:
        result.append(
            price * multiplier
            + result[-1] * (1 - multiplier)
        )

    return result


def rsi(values, period=14):
    if len(values) <= period:
        raise ValueError("Not enough values for RSI")

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

    if avg_gain == 0:
        return 0.0

    relative_strength = avg_gain / avg_loss
    return 100 - (100 / (1 + relative_strength))


def analyze_market(candles):
    candles = validate_candles(candles)

    closes = [candle["close"] for candle in candles]

    fast_ema = ema(closes, 9)
    slow_ema = ema(closes, 21)

    # Align EMA values to the same candle positions.
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
        "candles_analyzed": len(candles),
    }


if __name__ == "__main__":
    print("Downloading Quotex candles...")

    candles = get_candles()
    result = analyze_market(candles)

    print("\n========== MARKET ANALYSIS ==========")

    for key, value in result.items():
        print(f"{key.upper()}: {value}")

    print("=====================================")
            
