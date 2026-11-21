
import os
import requests
import pandas as pd

API_KEY = os.environ["OTCHARTS_API_KEY"]

PAIRS = [
    "EURUSD_otc",
    "GBPUSD_otc",
    "USDJPY_otc",
    "AUDCAD_otc",
    "EURJPY_otc",
    "GBPJPY_otc",
]

BASE_URL = "https://otcharts.com/v1/candles"

for pair in PAIRS:
    print(f"Downloading {pair}...")

    params = {
        "venue": "quotex",
        "symbol": pair,
        "tf": 60,
        "limit": 360,
    }

    response = requests.get(
        BASE_URL,
        headers={"Authorization": f"Bearer {API_KEY}"},
        params=params,
        timeout=30,
    )

    if response.status_code != 200:
        print(f"Failed {pair}: HTTP {response.status_code}")
        continue

    candles = response.json().get("candles", [])

    if not candles:
        print(f"No candles returned for {pair}")
        continue

    df = pd.DataFrame(candles)
    df = df.rename(columns={"time": "timestamp"})
    df = df[["timestamp", "open", "high", "low", "close"]]
    df = df.sort_values("timestamp")

    os.makedirs("data", exist_ok=True)
    df.to_csv(f"data/{pair}.csv", index=False)

    print(f"Saved {len(df)} candles for {pair}")

print("Download completed.")
      
