import pandas as pd
import numpy as np
import yfinance as yf

MIN_CANDLES = 100
MIN_SCORE = 5


def download_candles(ticker, period="2d", interval="1m"):
    df = yf.download(
        tickers=ticker,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=False,
    )
    return df if df is not None else pd.DataFrame()


def prepare_candles(df):
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower().strip() for c in df.columns]

    required = ["open", "high", "low", "close"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing candle columns: {missing}")

    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(
            df["timestamp"], errors="coerce", utc=True
        )
        df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
        df = df.drop_duplicates(subset=["timestamp"], keep="last")
    else:
        df = df.sort_index()

    for col in required:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df.dropna(subset=required).reset_index(drop=True)


def _find_snr_levels(df, lookback=40):
    sub = df.iloc[-lookback:-1]
    if len(sub) < 10:
        return float(df["low"].iloc[-20:-1].min()), float(df["high"].iloc[-20:-1].max())

    highs = sub["high"].values
    lows = sub["low"].values

    swing_highs = []
    swing_lows = []

    for idx in range(1, len(sub) - 1):
        if highs[idx] >= highs[idx - 1] and highs[idx] >= highs[idx + 1]:
            swing_highs.append(float(highs[idx]))
        if lows[idx] <= lows[idx - 1] and lows[idx] <= lows[idx + 1]:
            swing_lows.append(float(lows[idx]))

    support = swing_lows[-1] if swing_lows else float(sub["low"].min())
    resistance = swing_highs[-1] if swing_highs else float(sub["high"].max())
    return support, resistance


def analyze_market(candles):
    """Analyze completed candles only."""
    df = prepare_candles(candles)

    if len(df) < MIN_CANDLES:
        return None

    close = df["close"]
    high = df["high"]
    low = df["low"]
    opn = df["open"]

    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(
        alpha=1 / 14, adjust=False, min_periods=14
    ).mean()
    loss = (-delta.clip(upper=0)).ewm(
        alpha=1 / 14, adjust=False, min_periods=14
    ).mean()

    rs = gain / loss.replace(0, float("nan"))
    rsi = (100 - 100 / (1 + rs)).fillna(50)

    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std

    macd = (
        close.ewm(span=12, adjust=False).mean()
        - close.ewm(span=26, adjust=False).mean()
    )
    macd_signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - macd_signal

    atr = (high - low).rolling(14).mean()

    i = len(df) - 1
    price = float(close.iloc[i])
    prev_close = float(close.iloc[i - 1])
    prev_open = float(opn.iloc[i - 1])
    o = float(opn.iloc[i])
    h = float(high.iloc[i])
    l = float(low.iloc[i])

    candle_range = max(h - l, 1e-9)
    body = abs(price - o)
    lower_wick = min(o, price) - l
    upper_wick = h - max(o, price)
    cur_atr = float(atr.iloc[i]) if not pd.isna(atr.iloc[i]) else candle_range

    if body < cur_atr * 0.25 or candle_range <= 0:
        return None

    vals = [
        ema9.iloc[i], ema21.iloc[i], rsi.iloc[i],
        bb_mid.iloc[i], bb_upper.iloc[i], bb_
