"""Indicator-based signal engine. Signals are calculated from completed candles only."""
import pandas as pd
from config import MIN_CANDLES, MIN_SIGNAL_SCORE


def prepare_candles(data):
    df = data.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower().strip() for c in df.columns]

    required = ["open", "high", "low", "close"]
    if not all(col in df.columns for col in required):
        raise ValueError("Candle data must contain OHLC columns.")

    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
        df = df.drop_duplicates("timestamp", keep="last")

    df = df.dropna(subset=required)
    # Reject malformed candles instead of allowing them to distort indicators.
    valid = (
        (df["high"] >= df[["open", "close", "low"]].max(axis=1))
        & (df["low"] <= df[["open", "close", "high"]].min(axis=1))
    )
    return df.loc[valid].reset_index(drop=True)


def analyze_market(data):
    df = prepare_candles(data)
    if len(df) < MIN_CANDLES:
        return None

    close = df["close"]
    opn, high, low = df["open"], df["high"], df["low"]

    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    # A zero-loss run means RSI 100; a flat run means neutral RSI 50.
    rsi = rsi.mask((loss == 0) & (gain > 0), 100)
    rsi = rsi.mask((loss == 0) & (gain == 0), 50)

    macd = close.ewm(span=12, adjust=False).mean() - close.ewm(span=26, adjust=False).mean()
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    middle = close.rolling(20).mean()
    std = close.rolling(20).std()
    upper, lower = middle + 2 * std, middle - 2 * std

    i = len(df) - 1
    values = [ema9.iloc[i], ema21.iloc[i], ema50.iloc[i], rsi.iloc[i],
              macd.iloc[i], macd_signal.iloc[i], middle.iloc[i], upper.iloc[i], lower.iloc[i]]
    if any(pd.isna(value) for value in values):
        return None

    price, candle_open = float(close.iloc[i]), float(opn.iloc[i])
    candle_high, candle_low = float(high.iloc[i]), float(low.iloc[i])
    body = abs(price - candle_open)
    lower_wick = min(price, candle_open) - candle_low
    upper_wick = candle_high - max(price, candle_open)

    call_score = put_score = 0
    call_reasons, put_reasons = [], []

    if ema9.iloc[i] > ema21.iloc[i] > ema50.iloc[i]:
        call_score += 1; call_reasons.append("EMA trend bullish")
    if ema9.iloc[i] < ema21.iloc[i] < ema50.iloc[i]:
        put_score += 1; put_reasons.append("EMA trend bearish")
    if 50 < rsi.iloc[i] < 68:
        call_score += 1; call_reasons.append("RSI bullish")
    if 32 < rsi.iloc[i] < 50:
        put_score += 1; put_reasons.append("RSI bearish")
    if macd.iloc[i] > macd_signal.iloc[i]:
        call_score += 1; call_reasons.append("MACD bullish")
    if macd.iloc[i] < macd_signal.iloc[i]:
        put_score += 1; put_reasons.append("MACD bearish")
    if price > middle.iloc[i] and price < upper.iloc[i]:
        call_score += 1; call_reasons.append("Bollinger bullish zone")
    if price < middle.iloc[i] and price > lower.iloc[i]:
        put_score += 1; put_reasons.append("Bollinger bearish zone")
    if price > candle_open and lower_wick > body * 0.5:
        call_score += 1; call_reasons.append("Bullish rejection candle")
    if price < candle_open and upper_wick > body * 0.5:
        put_score += 1; put_reasons.append("Bearish rejection candle")

    if call_score >= MIN_SIGNAL_SCORE and call_score > put_score:
        return {"direction": "CALL", "score": call_score, "reasons": call_reasons}
    if put_score >= MIN_SIGNAL_SCORE and put_score > call_score:
        return {"direction": "PUT", "score": put_score, "reasons": put_reasons}
    return None
