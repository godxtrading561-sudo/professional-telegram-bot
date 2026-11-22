
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


def prepare_candles(candles):
    df = pd.DataFrame(candles).copy()

    required = ["open", "high", "low", "close"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing candle column: {col}")
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=required)

    df = df[
        (df["high"] >= df["low"]) &
        (df["high"] >= df["open"]) &
        (df["high"] >= df["close"]) &
        (df["low"] <= df["open"]) &
        (df["low"] <= df["close"])
    ]

    if "timestamp" in df.columns:
        df = df.sort_values("timestamp")

    return df.reset_index(drop=True)


def calculate_indicators(df):
    df = df.copy()

    close = df["close"]
    high = df["high"]
    low = df["low"]

    for period in [9, 21, 50, 200]:
        df[f"ema{period}"] = close.ewm(
            span=period, adjust=False
        ).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / 14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    df.loc[avg_loss == 0, "rsi"] = 100
    df["rsi"] = df["rsi"].fillna(50)

    middle = close.rolling(20).mean()
    std = close.rolling(20).std()

    df["bb_middle"] = middle
    df["bb_upper"] = middle + 2 * std
    df["bb_lower"] = middle - 2 * std

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()

    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(
        span=9, adjust=False
    ).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    previous_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - previous_close).abs(),
        (low - previous_close).abs()
    ], axis=1).max(axis=1)

    df["atr"] = tr.rolling(14).mean()

    df["support"] = low.rolling(20).min().shift(1)
    df["resistance"] = high.rolling(20).max().shift(1)

    return df


def candle_patterns(df):
    current = df.iloc[-1]
    previous = df.iloc[-2]

    body = abs(current["close"] - current["open"])
    candle_range = current["high"] - current["low"]

    if candle_range <= 0:
        return None

    lower_wick = min(
        current["open"], current["close"]
    ) - current["low"]

    upper_wick = current["high"] - max(
        current["open"], current["close"]
    )

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

    bullish_pin = (
        lower_wick >= max(body * 2, candle_range * 0.35)
        and current["close"] > current["open"]
    )

    bearish_pin = (
        upper_wick >= max(body * 2, candle_range * 0.35)
        and current["close"] < current["open"]
    )

    if bullish_engulfing or bullish_pin:
        return "BULLISH"

    if bearish_engulfing or bearish_pin:
        return "BEARISH"

    return None


def analyze_market(candles):
    df = prepare_candles(candles)

    if len(df) < MIN_CANDLES:
        return {
            "direction": "NO SIGNAL",
            "reason": "Not enough candles",
            "score": 0
        }

    df = calculate_indicators(df)

    current = df.iloc[-1]
    previous = df.iloc[-2]

    required_values = [
        current["ema9"], current["ema21"],
        current["ema50"], current["ema200"],
        current["rsi"], current["macd_hist"],
        current["bb_middle"], current["support"],
        current["resistance"], current["atr"]
    ]

    if any(pd.isna(value) for value in required_values):
        return {
            "direction": "NO SIGNAL",
            "reason": "Indicator data incomplete",
            "score": 0
        }

    pattern = candle_patterns(df)

    close = float(current["close"])
    atr = float(current["atr"])

    if atr <= 0:
        return {
            "direction": "NO SIGNAL",
            "reason": "Invalid volatility",
            "score": 0
        }

    # Strong trend confirmation
    bullish_trend = (
        current["ema9"] > current["ema21"]
        and current["ema21"] > current["ema50"]
        and current["ema50"] > current["ema200"]
        and close > current["ema50"]
    )

    bearish_trend = (
        current["ema9"] < current["ema21"]
        and current["ema21"] < current["ema50"]
        and current["ema50"] < current["ema200"]
        and close < current["ema50"]
    )

    # RSI momentum confirmation
    bullish_rsi = 52 <= current["rsi"] <= 68
    bearish_rsi = 32 <= current["rsi"] <= 48

    # MACD momentum confirmation
    bullish_macd = (
        current["macd_hist"] > 0
        and current["macd_hist"] > previous["macd_hist"]
    )

    bearish_macd = (
        current["macd_hist"] < 0
        and current["macd_hist"] < previous["macd_hist"]
    )

    # Bollinger confirmation
    bullish_bb = close > current["bb_middle"]
    bearish_bb = close < current["bb_middle"]

    # Support/resistance rejection
    near_support = (
        current["low"] <= current["support"] + atr * 0.25
        and close > current["support"]
    )

    near_resistance = (
        current["high"] >= current["resistance"] - atr * 0.25
        and close < current["resistance"]
    )

    # Avoid unusually large candles
    candle_range = current["high"] - current["low"]
    normal_candle = candle_range <= atr * 1.8

    call_score = 0
    put_score = 0
    reasons = []

    if bullish_trend:
        call_score += 1
        reasons.append("Bullish EMA trend")

    if bearish_trend:
        put_score += 1
        reasons.append("Bearish EMA trend")

    if bullish_rsi:
        call_score += 1
        reasons.append("Bullish RSI")

    if bearish_rsi:
        put_score += 1
        reasons.append("Bearish RSI")

    if bullish_macd:
        call_score += 1
        reasons.append("Bullish MACD momentum")

    if bearish_macd:
        put_score += 1
        reasons.append("Bearish MACD momentum")

    if bullish_bb:
        call_score += 1
        reasons.append("Price above BB middle")

    if bearish_bb:
        put_score += 1
        reasons.append("Price below BB middle")

    if pattern == "BULLISH":
        call_score += 1
        reasons.append("Bullish candle pattern")

    if pattern == "BEARISH":
        put_score += 1
        reasons.append("Bearish candle pattern")

    if near_support:
        call_score += 1
        reasons.append("Support rejection")

    if near_resistance:
        put_score += 1
        reasons.append("Resistance rejection")

    # Strict trend lock: opposite-trend signals are blocked.
    if bullish_trend:
        if (
            call_score >= 5
            and bullish_rsi
            and bullish_macd
            and pattern == "BULLISH"
            and normal_candle
        ):
            direction = "CALL"
            score = call_score
        else:
            direction = "NO SIGNAL"
            score = call_score

    elif bearish_trend:
        if (
            put_score >= 5
            and bearish_rsi
            and bearish_macd
            and pattern == "BEARISH"
            and normal_candle
        ):
            direction = "PUT"
            score = put_score
        else:
            direction = "NO SIGNAL"
            score = put_score

    else:
        direction = "NO SIGNAL"
        score = max(call_score, put_score)
        reasons.append("No confirmed EMA trend")

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
        "reasons": reasons
    }
