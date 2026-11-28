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


def _fetch_quantex_candles(symbol=DEFAULT_SYMBOL, limit=120):
    """Fetch completed Quotex OTC M1 candles from QUANTEX (requires candles:read plan)."""
    key = os.getenv("QUANTEX_API_KEY", "").strip()
    if not key:
        return None
    try:
        response = requests.get(
            "https://api.quantexbot.pro/v1/candles",
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            params={"broker": "quotex", "pair": symbol, "tf": "M1", "limit": min(max(int(limit), 60), 5000)},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise QuotexOTCDataError(f"QUANTEX connection failed: {exc}") from exc
    try:
        body = response.json()
    except ValueError as exc:
        raise QuotexOTCDataError(f"QUANTEX returned non-JSON HTTP {response.status_code}.") from exc
    if response.status_code != 200 or not isinstance(body, dict) or not body.get("ok"):
        error = body.get("error", {}) if isinstance(body, dict) else {}
        code = error.get("code", f"HTTP_{response.status_code}") if isinstance(error, dict) else f"HTTP_{response.status_code}"
        message = error.get("message", str(error)) if isinstance(error, dict) else str(error)
        if response.status_code in (401, 403) or code in ("permission_denied", "plan_required", "broker_not_in_plan"):
            raise QuotexOTCDataError(
                f"QUANTEX rejected candle access ({code}): {message}. "
                "Its docs list candles:read for Pro/Business/Candle Basic/Candle Data/Full Market Data; "
                "Developer Free is not listed for candle access."
            )
        raise QuotexOTCDataError(f"QUANTEX candle request failed ({code}): {message}")
    data = body.get("data") or {}
    if data.get("broker") != "quotex" or data.get("symbol") != symbol or data.get("timeframe") != "M1":
        raise QuotexOTCDataError("QUANTEX response broker, symbol, or timeframe does not match request.")
    rows = data.get("candles") or []
    if len(rows) < 60:
        raise QuotexOTCDataError(f"QUANTEX returned only {len(rows)} M1 candles; at least 60 are required.")
    df = pd.DataFrame(rows)
    required = ["epoch", "open", "high", "low", "close"]
    if not all(column in df.columns for column in required):
        raise QuotexOTCDataError("QUANTEX candle response is missing epoch/OHLC fields.")
    df = df[required].copy()
    df["timestamp"] = pd.to_datetime(df["epoch"], unit="s", utc=True, errors="coerce")
    for column in ["open", "high", "low", "close"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.dropna().set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    now = pd.Timestamp.now(tz="UTC")
    df = df[df.index < now.floor("min")]
    if len(df) < 60:
        raise QuotexOTCDataError("Fewer than 60 completed QUANTEX M1 candles are available.")
    age = (now - df.index[-1]).total_seconds()
    if age > 180:
        raise QuotexOTCDataError(f"QUANTEX OTC feed is stale ({int(age)} seconds).")
    valid = (
        (df[["open", "high", "low", "close"]] > 0).all(axis=1)
        & (df["high"] >= df[["open", "close"]].max(axis=1))
        & (df["low"] <= df[["open", "close"]].min(axis=1))
        & (df["high"] >= df["low"])
    )
    df = df.loc[valid]
    if len(df) < 60:
        raise QuotexOTCDataError("Fewer than 60 valid completed QUANTEX candles remain.")
    df.index.name = "timestamp"
    return df.tail(180).copy()


def fetch_quotex_otc_candles(symbol=DEFAULT_SYMBOL, limit=120):
    # Prefer QUANTEX when configured; never substitute ordinary FX spot data.
    quantex_candles = _fetch_quantex_candles(symbol, limit)
    if quantex_candles is not None:
        return quantex_candles
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

    if not isinstance(payload, dict):
        raise QuotexOTCDataError("OTCharts returned an unexpected non-object JSON response.")

    if response.status_code != 200:
        error = payload.get("error", {})
        code = error.get("code", "") if isinstance(error, dict) else ""
        message = error.get("message", str(error)) if isinstance(error, dict) else str(error)
        if response.status_code == 401:
            reason = "API key is missing, revoked, unknown, or the account email is unconfirmed."
        elif response.status_code == 402:
            reason = "OTCharts says this account has a plan it cannot serve; provider support must resolve this."
        elif response.status_code == 403:
            reason = "This key does not open the Quotex book or EURUSD_otc is not in its free five instruments."
        elif response.status_code == 429:
            reason = "The account request quota is exhausted; free tier is limited to 200 requests in its first month."
        elif response.status_code == 502:
            reason = "OTCharts reports that the upstream Quotex feed is temporarily unavailable."
        else:
            reason = f"Provider rejected the request (code={code or 'not supplied'})."
        raise QuotexOTCDataError(
            f"OTCharts HTTP {response.status_code}: {reason} Provider detail: {message}"
        )

    if payload.get("symbol") != symbol:
        raise QuotexOTCDataError(
            f"OTCharts response symbol mismatch: requested {symbol}, received {payload.get('symbol')!r}."
        )
    if payload.get("interval") not in (None, "60s"):
        raise QuotexOTCDataError(
            f"OTCharts returned interval {payload.get('interval')!r}, expected '60s'."
        )
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


def evaluate_quotex_otc_result(direction, signal_candle_time, symbol=DEFAULT_SYMBOL):
    """Evaluate the first completed OTC candle after the signal candle using the same feed."""
    candles = fetch_quotex_otc_candles(symbol, limit=180)
    signal_ts = pd.to_datetime(signal_candle_time, utc=True)
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
        "method": "OTCharts Quotex OTC 1-minute candle open-to-close",
    }
