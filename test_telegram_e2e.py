"""Safe Telegram delivery test: illustrative OHLC candlestick chart, demo result, and close message.
Does not fetch market data, create a trading session, or write to Supabase.
"""
import os
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def telegram(method, **kwargs):
    response = requests.post(f"{API}/{method}", timeout=40, **kwargs)
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {payload}")
    return payload


def make_sample_candlestick_chart():
    # Deliberately synthetic OHLC values for a delivery/layout test only.
    candles = [
        (1.00, 1.04, 0.98, 1.03),
        (1.03, 1.08, 1.01, 1.06),
        (1.06, 1.07, 1.00, 1.02),
        (1.02, 1.12, 1.01, 1.10),
        (1.10, 1.11, 1.05, 1.07),
        (1.07, 1.16, 1.06, 1.14),
    ]
    fig, ax = plt.subplots(figsize=(9, 4.8), dpi=140)
    width = 0.58
    for x, (open_price, high, low, close) in enumerate(candles, start=1):
        color = "#16a34a" if close >= open_price else "#dc2626"
        ax.vlines(x, low, high, color=color, linewidth=1.6, zorder=2)
        bottom = min(open_price, close)
        height = max(abs(close - open_price), 0.002)
        ax.add_patch(Rectangle(
            (x - width / 2, bottom), width, height,
            facecolor=color, edgecolor=color, linewidth=1, zorder=3,
        ))
    ax.set_title("PROFESSIONAL BOT — SAMPLE OHLC CANDLESTICK TEST")
    ax.set_xlabel("Sample candle (not live market time)")
    ax.set_ylabel("Illustrative price")
    ax.set_xticks(range(1, len(candles) + 1))
    ax.grid(True, alpha=0.25, linestyle="--")
    ax.text(
        0.5, 0.97, "DEMO DATA — NOT LIVE QUOTEX OTC",
        transform=ax.transAxes, ha="center", va="top",
        fontsize=9, color="#b91c1c", fontweight="bold",
    )
    fig.tight_layout()
    return fig


def main():
    if not BOT_TOKEN or not CHANNEL_ID:
        raise RuntimeError("BOT_TOKEN or CHANNEL_ID secret is missing.")

    fig = make_sample_candlestick_chart()
    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
            path = temp.name
        fig.savefig(path, format="png", facecolor="white")
    finally:
        plt.close(fig)

    try:
        with open(path, "rb") as photo:
            telegram(
                "sendPhoto",
                data={
                    "chat_id": CHANNEL_ID,
                    "caption": (
                        "🧪 <b>END-TO-END TEST — SAMPLE CANDLESTICK CHART</b>\n\n"
                        "PAIR: EURUSD_otc (illustrative only)\n"
                        "TIMEFRAME: 1 Minute\n"
                        "⚠️ Demo OHLC values only — not live Quotex data or a trading signal."
                    ),
                    "parse_mode": "HTML",
                },
                files={"photo": photo},
            )
        print("PASS: Telegram sample OHLC candlestick photo delivered.")

        telegram(
            "sendMessage",
            json={
                "chat_id": CHANNEL_ID,
                "text": (
                    "🧪 <b>END-TO-END TEST RESULT</b>\n\n"
                    "RESULT: 🟢 PROFIT (DEMO)\n"
                    "⚠️ Illustrative test message only — not a verified trade outcome."
                ),
                "parse_mode": "HTML",
            },
        )
        print("PASS: Telegram demo PROFIT result delivered.")

        telegram(
            "sendMessage",
            json={
                "chat_id": CHANNEL_ID,
                "text": (
                    "🧪 <b>END-TO-END TEST — SESSION CLOSED</b>\n\n"
                    "Test delivery sequence completed.\n"
                    "No live session was started and no trading state was changed."
                ),
                "parse_mode": "HTML",
            },
        )
        print("PASS: Telegram test session-close message delivered.")
    finally:
        if path and os.path.exists(path):
            os.remove(path)


if __name__ == "__main__":
    main()
