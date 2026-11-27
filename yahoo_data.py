"""Yahoo Finance 1-minute FX candles. This is ordinary FX spot data, NOT Quotex OTC."""
from datetime import datetime, timezone

import pandas as pd
import yfinance as yf


class YahooDataError(RuntimeError):
    pass


def fetch_yahoo_candles(ticker: str, period: str = "2d", interval: str = "1m") -> pd.DataFrame:
    try:
        raw = yf.download(
            tickers=ticker,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=False,
            threads=False,
        )
    except Exception as exc:
        raise YahooDataError(f"Yahoo Finance download failed for {ticker}: {exc}") from exc

    if raw is None or raw.empty:
        return pd.DataFrame()
    df = raw.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).lower().strip() for c in df.columns]
    required = ["open", "high", "low", "close"]
    if not all(c in df.columns for c in required):
        raise YahooDataError(f"Yahoo Finance OHLC columns missing for {ticker}")

    df = df[required].apply(pd.to_numeric, errors="coerce").dropna()
    index = pd.to_datetime(df.index, utc=True, errors="coerce")
    df.index = index
    df = df.loc[~df.index.isna()].sort_index()
    df = df[~df.index.duplicated(keep="last")]

    # Exclude the currently-forming minute; strategy only sees completed candles.
    now = pd.Timestamp.now(tz="UTC")
    df = df[df.index < now.floor("min")]
    valid = ((df.high >= df[["open", "close"]].max(axis=1)) &
             (df.low <= df[["open", "close"]].min(axis=1)))
    df = df.loc[valid]
    if len(df) < 60:
        return pd.DataFrame()
    age = (now - df.index[-1]).total_seconds()
    if age > 180:
        raise YahooDataError(f"Yahoo data for {ticker} is stale ({int(age)} seconds)")
    df.index.name = "timestamp"
    return df.tail(180).copy()


def evaluate_yahoo_result(direction: str, signal_time: str, ticker: str):
    """Evaluate the first fully completed one-minute candle after signal time."""
    candles = fetch_yahoo_candles(ticker, period="2d", interval="1m")
    if candles.empty:
        return None
    signal_ts = pd.to_datetime(signal_time, utc=True)
    candidates = candles[candles.index > signal_ts]
    if candidates.empty:
        return None
    candle = candidates.iloc[0]
    entry, exit_price = float(candle.open), float(candle.close)
    if exit_price == entry:
        status = "TIE"
    elif (direction == "CALL" and exit_price > entry) or (direction == "PUT" and exit_price < entry):
        status = "PROFIT"
    else:
        status = "LOSS"
    return {
        "status": status,
        "entry_price": entry,
        "exit_price": exit_price,
        "entry_time": candle.name.isoformat(),
        "expiry_time": (candle.name + pd.Timedelta(minutes=1)).isoformat(),
        "method": "Yahoo Finance 1-minute FX candle open-to-close (not Quotex OTC)",
    }
