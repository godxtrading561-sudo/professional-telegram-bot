"""Download free HistData 1-minute regular FX spot candles for research.

HistData timestamps are EST (UTC-5) year-round. These are not Quotex OTC prices.
"""
import os
from datetime import datetime, timezone

import pandas as pd
from histdata_fetcher import fetch_data

DATA_DIR = "data"
START_DATE = os.getenv("DATA_START_DATE", "2025-01-01")
PAIRS = [
    "EURUSD", "GBPUSD", "USDJPY", "AUDCAD", "EURJPY",
    "GBPJPY", "AUDUSD", "USDCHF", "NZDUSD", "EURGBP",
]


def download_pair(pair, end_date):
    print(f"Downloading {pair} HistData 1-minute spot candles...")
    result = fetch_data(
        pair=pair,
        start_date=START_DATE,
        end_date=end_date,
        timeframe="1min",
        output_format=None,
        max_workers=2,
    )
    if result.data is None or result.data.empty:
        details = "; ".join(
            f"{x.period_label}: {x.reason}" for x in (result.failed_periods or [])
        )
        raise RuntimeError(f"No HistData candles returned. {details}")

    df = result.data.copy()
    df.columns = [str(col).lower().strip() for col in df.columns]
    if "datetime" not in df.columns:
        raise ValueError(f"{pair}: HistData datetime column missing: {list(df.columns)}")

    # HistData documents timestamps as fixed EST (UTC-5), without DST.
    local = pd.to_datetime(df["datetime"], errors="coerce")
    df["timestamp"] = (
        local.dt.tz_localize("Etc/GMT+5", ambiguous="NaT", nonexistent="NaT")
        .dt.tz_convert("UTC")
    )
    for col in ["open", "high", "low", "close"]:
        if col not in df.columns:
            raise ValueError(f"{pair}: missing {col} column")
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = (
        df[["timestamp", "open", "high", "low", "close"]]
        .dropna()
        .drop_duplicates(subset=["timestamp"])
        .sort_values("timestamp")
    )
    if len(df) < 200:
        raise RuntimeError(f"{pair}: only {len(df)} valid candles; refusing short dataset")

    os.makedirs(DATA_DIR, exist_ok=True)
    output = os.path.join(DATA_DIR, f"{pair}_spot.csv")
    df.to_csv(output, index=False)
    print(f"Saved {pair}: {len(df):,} candles -> {output}")
    if result.failed_periods:
        print(f"WARNING {pair}: some periods unavailable: {len(result.failed_periods)}")


def main():
    end_date = datetime.now(timezone.utc).date().isoformat()
    failures = []
    for pair in PAIRS:
        try:
            download_pair(pair, end_date)
        except Exception as exc:
            failures.append(f"{pair}: {exc}")
            print(f"ERROR {pair}: {exc}")

    if failures:
        raise SystemExit("Historical download incomplete:\n" + "\n".join(failures))
    print("All ten HistData SPOT datasets downloaded. These are NOT OTC market candles.")


if __name__ == "__main__":
    main()
