"""Original EMA 9/21 + RSI 14 strategy, using completed OHLC candles only."""
from typing import Dict, Optional
import pandas as pd

from config import MIN_CANDLES


def _compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    return (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)


def prepare_candles(data: pd.DataFrame) -> pd.DataFrame:
    if data is None or data.empty:
        return pd.DataFrame()
    df = data.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower().strip() for c in df.columns]
    required = ["open", "high", "low", "close"]
    if not all(c in df.columns for c in required):
        raise ValueError("Candle data must contain OHLC columns.")
    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=required)
    valid = ((df.high >= df[["open", "close", "low"]].max(axis=1)) &
             (df.low <= df[["open", "close", "high"]].min(axis=1)))
    return df.loc[valid].copy()


def analyze_market(df: pd.DataFrame) -> Optional[Dict[str, str]]:
    candles = prepare_candles(df)
    if len(candles) < MIN_CANDLES:
        return None

    close = candles["close"].astype(float)
    open_p = candles["open"].astype(float)
    high_p = candles["high"].astype(float)
    low_p = candles["low"].astype(float)

    ema_fast = close.ewm(span=9, adjust=False).mean()
    ema_slow = close.ewm(span=21, adjust=False).mean()
    rsi = _compute_rsi(close, period=14)

    curr_open, curr_close = float(open_p.iloc[-1]), float(close.iloc[-1])
    curr_high, curr_low = float(high_p.iloc[-1]), float(low_p.iloc[-1])
    prev_close = float(close.iloc[-2])
    curr_fast, curr_slow = float(ema_fast.iloc[-1]), float(ema_slow.iloc[-1])
    prev_fast, prev_slow = float(ema_fast.iloc[-2]), float(ema_slow.iloc[-2])
    curr_rsi, prev_rsi = float(rsi.iloc[-1]), float(rsi.iloc[-2])

    candle_range = curr_high - curr_low
    body_size = abs(curr_close - curr_open)
    if candle_range <= 0 or body_size < candle_range * 0.35:
        return None

    bullish_trend = curr_fast > curr_slow and (prev_fast <= prev_slow or curr_close > prev_close)
    bullish_momentum = 52.0 <= curr_rsi <= 75.0 and curr_rsi > prev_rsi
    if bullish_trend and bullish_momentum and curr_close > curr_open:
        return {"direction": "CALL", "reason": "EMA_9_21_BULLISH_RSI_MOMENTUM"}

    bearish_trend = curr_fast < curr_slow and (prev_fast >= prev_slow or curr_close < prev_close)
    bearish_momentum = 25.0 <= curr_rsi <= 48.0 and curr_rsi < prev_rsi
    if bearish_trend and bearish_momentum and curr_close < curr_open:
        return {"direction": "PUT", "reason": "EMA_9_21_BEARISH_RSI_MOMENTUM"}
    return None
