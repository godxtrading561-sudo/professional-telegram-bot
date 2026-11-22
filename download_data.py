
import os
import glob
import subprocess
import pandas as pd

os.makedirs("data", exist_ok=True)
os.makedirs("dukascopy_download", exist_ok=True)

subprocess.run([
    "npx", "--yes", "dukascopy-node",
    "-i", "eurusd",
    "-from", "2026-10-01",
    "-to", "2026-11-22",
    "-t", "m1",
    "-f", "csv",
    "-dir", "dukascopy_download"
], check=True)

files = glob.glob("dukascopy_download/*.csv")

if not files:
    raise RuntimeError("No CSV downloaded from Dukascopy")

df = pd.concat([pd.read_csv(f) for f in files], ignore_index=True)
df.columns = [c.lower().strip() for c in df.columns]

if "timestamp" not in df.columns:
    for name in ["date", "datetime"]:
        if name in df.columns:
            df = df.rename(columns={name: "timestamp"})
            break

required = ["timestamp", "open", "high", "low", "close"]
missing = [c for c in required if c not in df.columns]

if missing:
    raise ValueError(f"Missing columns: {missing}; found: {list(df.columns)}")

df = df[required].dropna()
df = df.drop_duplicates(subset=["timestamp"])
df = df.sort_values("timestamp")

df.to_csv("data/EURUSD_otc.csv", index=False)

print(f"SUCCESS: Downloaded {len(df)} candles")
