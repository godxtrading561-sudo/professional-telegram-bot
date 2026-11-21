
import pandas as pd
import numpy as np

PAIRS = [
    "EURUSD_otc",
    "GBPUSD_otc",
    "USDJPY_otc",
    "AUDCAD_otc",
    "EURJPY_otc",
    "GBPJPY_otc",
]

TIMEFRAME = "1 Minute"
MIN_CANDLES = 220
MIN_SCORE = 4


def prepare_candles(candles):
    df = pd.DataFrame(candles).copy()

    required = ["open", "high", "low", "close"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing candle column: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=required).reset_index(drop=True)

    df = df[
        (df["high"] >= df["low"]) &
        (df["high"] >= df["open"]) &
        (df["high"] >= df["close"]) &
        (df["low"] <= df["open"]) &
        (df["low"] <= df["close"])
    ].copy()

    return df.reset_index(drop=True)


def calculate_indicators(df):
    df = df.copy()

    close = df["close"]
    high = df["high"]
    low = df["low"]

    df["ema9"] = close.ewm(span=9, adjust=False).mean()
    df["ema21"] = close.ewm(span=21, adjust=False).mean()
    df["ema50"] = close.ewm(span=50, adjust=False).mean()
    df["ema200"] = close.ewm(span=200, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    df["rsi"] = df["rsi"].fillna(50)

    middle = close.rolling(20).mean()
    std = close.rolling(20).std()

    df["bb_upper"] = middle + (2 * std)
    df["bb_lower"] = middle - (2 * std)
    df["bb_middle"] = middle

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(
        span=9, adjust=False
    ).mean()

    df["support"] = low.rolling(20).min().shift(1)
    df["resistance"] = high.rolling(20).max().shift(1)

    return df


def candle_patterns(df):
    current = df.iloc[-1]
    previous = df.iloc[-2]

    body = abs(current["close"] - current["open"])
    candle_range = current["high"] - current["low"]

    if candle_range <= 0:
        return None, None

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

    lower_wick = min(current["open"], current["close"]) - current["low"]
    upper_wick = current["high"] - max(
        current["open"], current["close"]
    )

    bullish_pin = (
        lower_wick >= body * 2
        and upper_wick <= max(body, candle_range * 0.1)
        and current["close"] > current["open"]
    )

    bearish_pin = (
        upper_wick >= body * 2
        and lower_wick <= max(body, candle_range * 0.1)
        and current["close"] < current["open"]
    )

    if bullish_engulfing or bullish_pin:
        return "BULLISH", "Bullish candle pattern"

    if bearish_engulfing or bearish_pin:
        return "BEARISH", "Bearish candle pattern"

    return None, None


def analyze_market(candles):
    df = prepare_candles(candles)

    if len(df) < MIN_CANDLES:
        return {
            "direction": "NO SIGNAL",
            "reason": f"Need at least {MIN_CANDLES} candles",
            "score": 0,
        }

    df = calculate_indicators(df)
    current = df.iloc[-1]
    previous = df.iloc[-2]

    values = [
        current["ema9"], current["ema21"],
        current["ema50"], current["ema200"],
        current["rsi"], current["macd"],
        current["macd_signal"], current["support"],
        current["resistance"], current["bb_upper"],
        current["bb_lower"],
    ]

    if any(pd.isna(v) for v in values):
        return {
            "direction": "NO SIGNAL",
            "reason": "Indicator data incomplete",
            "score": 0,
        }

    pattern, pattern_reason = candle_patterns(df)

    call_score = 0
    put_score = 0
    reasons = []

    # EMA trend
    if current["ema9"] > current["ema21"] > current["ema50"] > current["ema200"]:
        call_score += 1
        reasons.append("Bullish EMA trend")
    elif current["ema9"] < current["ema21"] < current["ema50"] < current["ema200"]:
        put_score += 1
        reasons.append("Bearish EMA trend")

    # RSI
    if 50 < current["rsi"] < 70:
        call_score += 1
        reasons.append("RSI bullish")
    elif 30 < current["rsi"] < 50:
        put_score += 1
        reasons.append("RSI bearish")

    # MACD
    if current["macd"] > current["macd_signal"]:
        call_score += 1
        reasons.append("MACD bullish")
    elif current["macd"] < current["macd_signal"]:
        put_score += 1
        reasons.append("MACD bearish")

    # Bollinger Bands
    if current["close"] > current["bb_middle"]:
        call_score += 1
        reasons.append("Price above BB middle")
    elif current["close"] < current["bb_middle"]:
        put_score += 1
        reasons.append("Price below BB middle")

    # Support and resistance
    if current["close"] <= current["support"] * 1.001:
        call_score += 1
        reasons.append("Near support")
    if current["close"] >= current["resistance"] * 0.999:
        put_score += 1
        reasons.append("Near resistance")

    # Candlestick confirmation
    if pattern == "BULLISH":
        call_score += 1
        reasons.append(pattern_reason)
    elif pattern == "BEARISH":
        put_score += 1
        reasons.append(pattern_reason)

    if call_score >= MIN_SCORE and call_score > put_score:
        direction = "CALL"
        score = call_score
    elif put_score >= MIN_SCORE and put_score > call_score:
        direction = "PUT"
        score = put_score
    else:
        direction = "NO SIGNAL"
        score = max(call_score, put_score)

    return {
        "direction": direction,
        "score": score,
        "call_score": call_score,
        "put_score": put_score,
        "rsi": round(float(current["rsi"]), 2),
        "ema9": round(float(current["ema9"]), 6),
        "ema21": round(float(current["ema21"]), 6),
        "ema50": round(float(current["ema50"]), 6),
        "ema200": round(float(current["ema200"]), 6),
        "support": float(current["support"]),
        "resistance": float(current["resistance"]),
        "reasons": reasons,
    }
