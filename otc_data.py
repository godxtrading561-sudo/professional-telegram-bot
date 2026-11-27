"""Read-only Quotex OTC candles from OTCharts.

Requires OTCHARTS_API_KEY in the environment. This is an independent data
provider, not an official Quotex API. Never falls back to FX spot data.
"""
import os
from datetime import datetime, timezone

import pandas as pd
import requests

BASE_URL = "https://otcharts.com"
VENUE = "quotex"
TIMEFRAME_SECONDS = 60
DEFAULT_SYMBOL = "EURUSD_otc"


class QuotexOTCDataError(RuntimeError):
    pass


def fetch_quotex_otc_candles(symbol=DEFAULT_SYMBOL, limit=120):
    key = os.getenv("OTCHARTS_API_KEY", "").strip()
    if not key:
        raise QuotexOTCDataError("OTCHARTS_API_KEY secret is missing.")

    try:
        response = requests.get(
            f"{BASE_URL}/v1/candles",
            headers={
                "Authorization": f"Bearer {key}",
                "Accept": "application/json",
                "User-Agent": "ProfessionalTelegramBot/1.0",
            },
            params={
                "venue": VENUE,
                "symbol": symbol,
                "tf": TIMEFRAME_SECONDS,
                "limit": min(max(int(limit), 60), 500),
            },
            timeout=25,
        )
    except requests.RequestException as exc:
        raise QuotexOTCDataError(f"OTCharts connection failed: {exc}") from exc

    try:
        payload = response.json()
    except ValueError as exc:
        raise QuotexOTCDataError(
            f"OTCharts returned non-JSON HTTP {response.status_code}."
        ) from exc

    if response.status_code != 200:
        detail = payload.get("error", payload) if isinstance(payload, dict) else payload
        raise QuotexOTCDataError(
            f"OTCharts HTTP {response.status_code}: {detail}. "
            "Check key, Quotex book access, free-tier instrument access and quota."
        )

    if payload.get("symbol") != symbol:
        raise QuotexOTCDataError("OTCharts response symbol does not match request.")
    if payload.get("open") is False:
        raise QuotexOTCDataError(f"{symbol} is closed for trading on Quotex.")
    gaps = payload.get("gaps") or {}
    if int(gaps.get("missingBars", 0) or 0) > 0:
        raise QuotexOTCDataError(
            f"OTC candle feed has {gaps['missingBars']} missing 1-minute bars; refusing unsafe data."
        )

    rows = payload.get("candles") or []
    if len(rows) < 60:
        raise QuotexOTCDataError(
            f"Only {len(rows)} OTC candles returned; at least 60 are required."
        )

    df = pd.DataFrame(rows)
    required = ["time", "open", "high", "low", "close"]
    if not all(column in df.columns for column in required):
        raise QuotexOTCDataError("OTCharts candle response is missing OHLC/time fields.")

    df = df[required].copy()
    df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True, errors="coerce")
    for column in ["open", "high", "low", "close"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna().set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]

    # Exclude any still-forming minute and reject stale feed data.
    now = pd.Timestamp.now(tz="UTC")
    df = df[df.index < now.floor("min")]
    if len(df) < 60:
        raise QuotexOTCDataError("Fewer than 60 completed OTC candles are available.")
    age = (now - df.index[-1]).total_seconds()
    if age > 180:
        raise QuotexOTCDataError(f"Quotex OTC feed is stale ({int(age)} seconds).")

    valid = (
        (df["high"] >= df[["open", "close"]].max(axis=1))
        & (df["low"] <= df[["open", "close"]].min(axis=1))
    )
    df = df.loc[valid]
    if len(df) < 60:
        raise QuotexOTCDataError("Fewer than 60 valid completed OTC candles remain.")
    df.index.name = "timestamp"
    return df.tail(180).copy()


if __name__ == "__main__":
    candles = fetch_quotex_otc_candles()
    print(
        f"PASS: {len(candles)} completed 1-minute Quotex OTC candles "
        f"for {DEFAULT_SYMBOL}; latest={candles.index[-1].isoformat()}"
    )
