import pandas as pd

MIN_CANDLES = 100
MIN_SCORE = 4

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


def analyze_market(candles):
    """Analyze completed candles only. Caller excludes the live candle."""
    df = prepare_candles(candles)

    if len(df) < MIN_CANDLES:
        return None

    close = df.close
    high = df.high
    low = df.low
    opn = df.open

    ema9 = close.ewm(span=9, adjust=False).mean()
    ema21 = close.ewm(span=21, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0).ewm(
        alpha=1/14, adjust=False, min_periods=14
    ).mean()
    loss = (-delta.clip(upper=0)).ewm(
        alpha=1/14, adjust=False, min_periods=14
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

    i = len(df) - 1
    price = float(close.iloc[i])
    o = float(opn.iloc[i])
    h = float(high.iloc[i])
    l = float(low.iloc[i])

    body = abs(price - o)
    lower_wick = min(o, price) - l
    upper_wick = h - max(o, price)

    vals = [
        ema9.iloc[i], ema21.iloc[i], rsi.iloc[i],
        bb_mid.iloc[i], bb_upper.iloc[i], bb_lower.iloc[i],
        hist.iloc[i], hist.iloc[i-1]
    ]

    if any(pd.isna(x) for x in vals):
        return None

    call = 0
    put = 0
    call_reasons = []
    put_reasons = []

    if ema9.iloc[i] > ema21.iloc[i]:
        call += 1
        call_reasons.append("EMA bullish")

    if 50 < rsi.iloc[i] < 68:
        call += 1
        call_reasons.append(f"RSI {rsi.iloc[i]:.1f}")

    if hist.iloc[i] > 0 and hist.iloc[i] > hist.iloc[i-1]:
        call += 1
        call_reasons.append("MACD bullish")

    if price > bb_mid.iloc[i] and price < bb_upper.iloc[i]:
        call += 1
        call_reasons.append("BB bullish zone")

    if price > o and lower_wick > body * 0.5:
        call += 1
        call_reasons.append("Bullish wick")

    if ema9.iloc[i] < ema21.iloc[i]:
        put += 1
        put_reasons.append("EMA bearish")

    if 32 < rsi.iloc[i] < 50:
        put += 1
        put_reasons.append(f"RSI {rsi.iloc[i]:.1f}")

    if hist.iloc[i] < 0 and hist.iloc[i] < hist.iloc[i-1]:
        put += 1
        put_reasons.append("MACD bearish")

    if price < bb_mid.iloc[i] and price > bb_lower.iloc[i]:
        put += 1
        put_reasons.append("BB bearish zone")

    if price < o and upper_wick > body * 0.5:
        put += 1
        put_reasons.append("Bearish wick")

    if call >= MIN_SCORE and call > put:
        return {
            "direction": "CALL",
            "score": call,
            "reasons": call_reasons
        }

    if put >= MIN_SCORE and put > call:
        return {
            "direction": "PUT",
            "score": put,
            "reasons": put_reasons
        }

    return None
