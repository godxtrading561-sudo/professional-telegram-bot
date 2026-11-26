"""Read-only Quotex OTC candles from the OTCharts API."""
import logging
import os
from datetime import datetime, timezone

import pandas as pd
import requests

BASE_URL = "https://otcharts.com/v1/candles"
log = logging.getLogger("quotex-data")


class CandleFeedError(RuntimeError):
    pass


def fetch_quotex_candles(symbol, limit=360, timeout=20):
    key = os.getenv("OTCHARTS_API_KEY", "").strip()
    if not key:
        raise CandleFeedError("OTCHARTS_API_KEY is not configured")
    try:
        response = requests.get(
            BASE_URL,
            params={"venue": "quotex", "symbol": symbol, "tf": 60, "limit": limit},
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise CandleFeedError(f"OTCharts connection failed: {exc}") from exc

    if response.status_code in (401, 403):
        raise CandleFeedError("OTCharts rejected the API key (401/403)")
    if response.status_code == 402:
        raise CandleFeedError("OTCharts account requires an eligible plan (402)")
    if response.status_code == 429:
        raise CandleFeedError("OTCharts request quota/rate limit reached (429)")
    if not response.ok:
        raise CandleFeedError(f"OTCharts HTTP error {response.status_code}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise CandleFeedError("OTCharts returned invalid JSON") from exc

    rows = payload.get("candles") if isinstance(payload, dict) else payload
    if isinstance(rows, dict):
        rows = rows.get("data") or rows.get("candles")
    if not isinstance(rows, list) or not rows:
        raise CandleFeedError("OTCharts response contains no candle list")

    df = pd.DataFrame(rows)
    aliases = {"time": "timestamp", "t": "timestamp", "o": "open",
               "h": "high", "l": "low", "c": "close"}
    df = df.rename(columns={k: v for k, v in aliases.items() if k in df.columns})
    required = ["timestamp", "open", "high", "low", "close"]
    if any(c not in df.columns for c in required):
        raise CandleFeedError("OTCharts candle schema is missing timestamp/OHLC fields")

    # Accept ISO timestamps and Unix seconds/milliseconds.
    raw_time = df["timestamp"]
    if pd.api.types.is_numeric_dtype(raw_time):
        numeric = pd.to_numeric(raw_time, errors="coerce")
        unit = "ms" if numeric.dropna().median() > 10**11 else "s"
        df["timestamp"] = pd.to_datetime(numeric, unit=unit, utc=True, errors="coerce")
    else:
        df["timestamp"] = pd.to_datetime(raw_time, utc=True, errors="coerce")

    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=required).sort_values("timestamp").drop_duplicates("timestamp", keep="last")
    valid = ((df.high >= df[["open", "close", "low"]].max(axis=1)) &
             (df.low <= df[["open", "close", "high"]].min(axis=1)))
    df = df.loc[valid].reset_index(drop=True)

    # Exclude the currently forming minute candle and reject stale feeds.
    now = pd.Timestamp.now(tz="UTC")
    df = df[df.timestamp < now.floor("min")].reset_index(drop=True)
    if len(df) < 60:
        raise CandleFeedError(f"Only {len(df)} completed candles returned; need at least 60")
    age = (now - df.timestamp.iloc[-1]).total_seconds()
    if age > 180:
        raise CandleFeedError(f"Latest completed OTC candle is stale ({int(age)} seconds)")
    return df.tail(limit).copy()


def evaluate_one_minute_result(direction, signal_time, candles):
    """Return PROFIT/LOSS/TIE using next candle open and its one-minute close."""
    direction = str(direction).upper()
    if direction not in ("CALL", "PUT"):
        raise ValueError("direction must be CALL or PUT")
    signal_ts = pd.to_datetime(signal_time, utc=True)
    df = candles.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Entry is the first candle opening strictly after signal creation.
    candidates = df[df.timestamp > signal_ts]
    if candidates.empty:
        return None
    entry = candidates.iloc[0]
    # A one-minute contract entered at this candle's open expires at
    # the close of that same one-minute candle (not the following candle).
    entry_price = float(entry.open)
    exit_price = float(entry.close)
    expiry_time = entry.timestamp + pd.Timedelta(minutes=1)
    if exit_price == entry_price:
        status = "TIE"
    elif (direction == "CALL" and exit_price > entry_price) or (direction == "PUT" and exit_price < entry_price):
        status = "PROFIT"
    else:
        status = "LOSS"
    return {"status": status, "entry_price": entry_price, "exit_price": exit_price,
            "entry_time": entry.timestamp.isoformat(), "expiry_time": expiry_time.isoformat(),
            "method": "1-minute candle open-to-close"}
