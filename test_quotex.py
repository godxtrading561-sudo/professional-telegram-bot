
import os
import sys
import requests

API_KEY = os.getenv("OTCHARTS_API_KEY")

URL = "https://otcharts.com/v1/candles"

if not API_KEY:
    sys.exit("API TEST FAILED: OTCHARTS_API_KEY secret is missing.")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json",
    "User-Agent": "ProfessionalTelegramBot/1.0",
}

params = {
    "venue": "quotex",
    "symbol": "EURUSD_otc",
    "tf": 60,
    "limit": 10,
}

print("Connecting to OTCharts...")
print("Requested symbol: EURUSD_otc")
print("Requested timeframe: 1 minute")

try:
    response = requests.get(
        URL,
        headers=headers,
        params=params,
        timeout=30,
    )

    print("HTTP STATUS:", response.status_code)
    response.raise_for_status()

    data = response.json()

    if not isinstance(data, dict):
        raise ValueError("Unexpected API response format.")

    candles = data.get("candles")

    if not isinstance(candles, list) or not candles:
        raise ValueError(
            "No candles received. Check API response format and symbol."
        )

    valid = []

    for candle in candles:
        try:
            item = {
                "time": candle["time"],
                "open": float(candle["open"]),
                "high": float(candle["high"]),
                "low": float(candle["low"]),
                "close": float(candle["close"]),
            }

            if not all(
                value > 0
                for key, value in item.items()
                if key != "time"
            ):
                continue

            if item["high"] < max(item["open"], item["close"]):
                continue

            if item["low"] > min(item["open"], item["close"]):
                continue

            if item["high"] < item["low"]:
                continue

            valid.append(item)

        except (KeyError, TypeError, ValueError):
            continue

    if not valid:
        raise ValueError("API returned no valid OHLC candles.")

    print("API RESPONSE: SUCCESS")
    print("SYMBOL:", data.get("symbol", "Not provided"))
    print("CANDLES RECEIVED:", len(candles))
    print("VALID CANDLES:", len(valid))
    print("LATEST CANDLE TIME:", valid[-1]["time"])
    print("OTCharts connectivity test passed.")

except requests.RequestException as error:
    print("API TEST FAILED:", str(error))
    sys.exit(1)

except (ValueError, TypeError) as error:
    print("DATA VALIDATION FAILED:", str(error))
    sys.exit(1)
