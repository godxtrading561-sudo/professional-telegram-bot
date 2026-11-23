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
    resistance = swing_highs
