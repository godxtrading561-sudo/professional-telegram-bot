"""Download free Dukascopy 1-minute SPOT FX candles for strategy research.

IMPORTANT: Dukascopy data is regular FX spot data, NOT Quotex OTC data.
Files are deliberately named *_spot.csv so they cannot be mistaken for OTC candles.
"""
import glob
import os
import subprocess
from datetime import datetime, timezone

import pandas as pd

DATA_DIR = "data"
DOWNLOAD_DIR = "dukascopy_download"
# A longer sample is needed for a meaningful first-pass research backtest.
START_DATE = os.getenv("DATA_START_DATE", "2025-01-01")
PAIRS = {
    "EURUSD": "eurusd",
    "GBPUSD": "gbpusd",
    "USDJPY": "usdjpy",
    "AUDCAD": "audcad",
    "EURJPY": "eurjpy",
    "GBPJPY": "gbpjpy",
    "AUDUSD": "audusd",
    "USDCHF": "usdchf",
    "NZDUSD": "nzdusd",
    "EURGBP": "eurgbp",
}


def download_pair(pair, instrument, end_date):
    pair_dir = os.path.join(DOWNLOAD_DIR, pair)
    os.makedirs(pair_dir, exist_ok=True)
    command = [
        "npx", "--yes", "dukascopy-node",
        "-i", instrument,
        "-from", START_DATE,
        "-to", end_date,
        "-t", "m1",
        "-f", "csv",
        "-dir", pair_dir,
        "-fn", f"{pair.lower()}-m1",
        "-r", "3",
        "-rp", "1500",
        "-re",
    ]
    print(f"Downloading {pair} spot candles...")
    subprocess.run(command, check=True)

    files = glob.glob(os.path.join(pair_dir, "*.csv"))
    if not files:
        raise RuntimeError(f"No downloaded CSV found for {pair}")

    frames = [pd.read_csv(path) for path in files]
    df = pd.concat(frames, ignore_index=True)
    df.columns = [str(col).lower().strip() for col in df.columns]

    required = ["timestamp", "open", "high", "low", "close"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{pair}: missing {missing}; found {list(df.columns)}")

    ts = pd.to_numeric(df["timestamp"], errors="coerce")
    if ts.notna().all():
        df["timestamp"] = pd.to_datetime(ts, unit="ms", utc=True)
    else:
        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)

    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = (
        df[required]
        .dropna()
        .drop_duplicates(subset=["timestamp"])
        .sort_values("timestamp")
    )
    if len(df) < 200:
        raise RuntimeError(f"{pair}: only {len(df)} valid candles; refusing empty/short dataset")

    output = os.path.join(DATA_DIR, f"{pair}_spot.csv")
    df.to_csv(output, index=False)
    print(f"Saved {pair}: {len(df)} candles -> {output}")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    end_date = datetime.now(timezone.utc).date().isoformat()

    failures = []
    for pair, instrument in PAIRS.items():
        try:
            download_pair(pair, instrument, end_date)
        except Exception as exc:
            failures.append(f"{pair}: {exc}")
            print(f"ERROR {pair}: {exc}")

    if failures:
        raise SystemExit("Some pair downloads failed:\n" + "\n".join(failures))

    print("All ten spot datasets downloaded. These are NOT OTC market candles.")


if __name__ == "__main__":
    main()
