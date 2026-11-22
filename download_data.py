
import os
import subprocess
import pandas as pd

os.makedirs("data", exist_ok=True)

subprocess.run([
    "npx", "--yes", "dukascopy-node",
    "-i", "eurusd",
    "-from", "2026-10-01",
    "-to", "2026-11-21",
    "-tf", "m1",
    "-f", "csv",
    "-dir", "data"
], check=True)

files = [
    f for f in os.listdir("data")
    if f.lower().endswith(".csv")
]

if not files:
    raise RuntimeError("Dukascopy did not create a CSV file")

source = os.path.join("data", files[0])
df = pd.read_csv(source)
df.columns = [c.lower().strip() for c in df.columns]

df = df.rename(columns={
    "timestamp": "timestamp",
    "date": "timestamp",
    "datetime": "timestamp",
    "volume": "volume"
})

required = ["timestamp", "open", "high", "low", "close"]
missing = [c for c in required if c not in df.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}. Found: {list(df.columns)}")

df = df[required].dropna()
df.to_csv("data/EURUSD_otc.csv", index=False)

print(f"Saved {len(df)} candles")
