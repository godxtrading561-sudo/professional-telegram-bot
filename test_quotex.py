
import os
import requests

API_KEY = os.environ["OTCHARTS_API_KEY"]

URL = "https://otcharts.com/v1/candles"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json",
    "User-Agent": "ProfessionalTelegramBot/1.0",
}

params = {
    "venue": "quotex",
    "symbol": "EURUSD_otc",
    "tf": 60,
    "limit": 3,
}

print("Connecting to OTCharts...")

response = requests.get(
    URL,
    headers=headers,
    params=params,
    timeout=30,
)

if not response.ok:
    print("API TEST FAILED")
    print("HTTP STATUS:", response.status_code)
    print("ERROR:", response.text[:1000])
    response.raise_for_status()

data = response.json()
candles = data.get("candles", [])

if not candles:
    raise RuntimeError("API connected, but no candle data received.")

print("QUOTEX API CONNECTION SUCCESSFUL!")
print("PAIR:", data.get("symbol"))
print("CANDLES RECEIVED:", len(candles))

for candle in candles:
    print(
        "Time:", candle.get("time"),
        "| Open:", candle.get("open"),
        "| High:", candle.get("high"),
        "| Low:", candle.get("low"),
        "| Close:", candle.get("close"),
)
  
