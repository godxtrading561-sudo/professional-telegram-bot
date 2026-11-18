"""
Conservative, research-only signal engine.
Implements a small set of transparent indicator rules rather than pretending
to implement all 50 chart setups exactly.

Expected candle format: list[dict] with open, high, low, close and optional time.
OTCharts endpoint/parameters remain configurable through environment variables.
"""
import os
import requests
from statistics import mean

API_URL = os.getenv("OTCHARTS_URL", "https://otcharts.com/v1/candles")
API_KEY = os.getenv("OTCHARTS_API_KEY", "")
SYMBOL = os.getenv("OTCHARTS_SYMBOL", "EURUSD_otc")
TIMEFRAME = os.getenv("OTCHARTS_TIMEFRAME", "60")
CANDLE_LIMIT = int(os.getenv("OTCHARTS_LIMIT", "1000"))

def fetch_candles():
    if not API_KEY:
        raise RuntimeError("OTCHARTS_API_KEY GitHub Secret is missing.")
    headers = {"Authorization": f"Bearer {API_KEY}", "X-API-KEY": API_KEY}
    params = {"venue": "quotex", "symbol": SYMBOL, "tf": TIMEFRAME, "limit": CANDLE_LIMIT}
    response = requests.get(API_URL, headers=headers, params=params, timeout=25)
    response.raise_for_status()
    payload = response.json()
    rows = payload if isinstance(payload, list) else (
        payload.get("candles") or payload.get("data") or payload.get("result") or []
    )
    candles = validate_candles(rows)
    print(f"OTCharts returned {len(candles)} valid candles (requested {CANDLE_LIMIT}).")
    return candles

def validate_candles(rows):
    result = []
    for row in rows:
        try:
            c = {k: float(row[k]) for k in ("open", "high", "low", "close")}
            if c["high"] < max(c["open"], c["close"], c["low"]): continue
            if c["low"] > min(c["open"], c["close"], c["high"]): continue
            if c["high"] < c["low"]: continue
            c["time"] = row.get("time", row.get("timestamp", len(result)))
            result.append(c)
        except (KeyError, TypeError, ValueError):
            continue
    try:
        result.sort(key=lambda x: float(x["time"]))
    except (TypeError, ValueError):
        pass
    return result

def ema(values, period):
    if len(values) < period: return None
    alpha = 2 / (period + 1)
    current = mean(values[:period])
    for value in values[period:]:
        current = alpha * value + (1-alpha) * current
    return current

def rsi(values, period=14):
    if len(values) < period + 1: return None
    changes = [values[i] - values[i-1] for i in range(1, len(values))]
    gains = [max(x, 0) for x in changes[-period:]]
    losses = [max(-x, 0) for x in changes[-period:]]
    avg_gain, avg_loss = mean(gains), mean(losses)
    if avg_loss == 0: return 100.0
    return 100 - (100 / (1 + avg_gain / avg_loss))

def atr(candles, period=14):
    if len(candles) < period + 1: return None
    trs = []
    for i in range(1, len(candles)):
        p, c = candles[i-1]["close"], candles[i]
        trs.append(max(c["high"]-c["low"], abs(c["high"]-p), abs(c["low"]-p)))
    return mean(trs[-period:])

def analyze_market(candles):
    """Return a CALL/PUT candidate or None. Uses only supplied completed candles."""
    candles = validate_candles(candles)
    if len(candles) < 220:
        return {"direction": None, "reason": "Need at least 220 valid candles."}

    closes = [c["close"] for c in candles]
    last = candles[-1]
    e9, e21, e50, e200 = (ema(closes, p) for p in (9, 21, 50, 200))
    rv, av = rsi(closes), atr(candles)
    if None in (e9, e21, e50, e200, rv, av) or av <= 0:
        return {"direction": None, "reason": "Indicator data unavailable."}

    # Conservative trend filter + momentum confirmation.
    bull_trend = last["close"] > e200 and e50 > e200 and e9 > e21
    bear_trend = last["close"] < e200 and e50 < e200 and e9 < e21

    # Require a meaningful candle body; avoid tiny/doji candles.
    body = abs(last["close"] - last["open"])
    body_ok = body >= 0.15 * av

    # RSI momentum zone avoids buying extreme overbought / selling oversold.
    call_ok = bull_trend and 50 <= rv <= 68 and last["close"] > last["open"] and body_ok
    put_ok = bear_trend and 32 <= rv <= 50 and last["close"] < last["open"] and body_ok

    details = {
        "rsi": round(rv, 2), "ema9": round(e9, 6), "ema21": round(e21, 6),
        "ema50": round(e50, 6), "ema200": round(e200, 6), "atr": round(av, 6),
        "candle_body": round(body, 6)
    }
    if call_ok:
        return {"direction": "CALL", "score": 4, "reason": "EMA trend + RSI momentum + bullish candle", "indicators": details}
    if put_ok:
        return {"direction": "PUT", "score": 4, "reason": "EMA trend + RSI momentum + bearish candle", "indicators": details}
    return {"direction": None, "reason": "No high-confidence rule combination.", "indicators": details}

if __name__ == "__main__":
    data = fetch_candles()
    print(analyze_market(data))
    
