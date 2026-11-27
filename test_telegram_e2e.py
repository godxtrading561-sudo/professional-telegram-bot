"""Safe Telegram delivery test: sample chart photo, demo result, and close message.
Does not create a trading session or write to Supabase.
"""
import os
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
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


def main():
    if not BOT_TOKEN or not CHANNEL_ID:
        raise RuntimeError("BOT_TOKEN or CHANNEL_ID secret is missing.")

    fig, ax = plt.subplots(figsize=(9, 4), dpi=120)
    ax.plot([1, 2, 3, 4, 5, 6], [1.0, 1.2, 1.1, 1.35, 1.3, 1.5], marker="o")
    ax.set_title("PROFESSIONAL BOT — SAMPLE TEST CHART")
    ax.set_xlabel("Sample candle")
    ax.set_ylabel("Illustrative price")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp:
            path = temp.name
        fig.savefig(path, format="png")
    finally:
        plt.close(fig)

    try:
        with open(path, "rb") as photo:
            telegram(
                "sendPhoto",
                data={
                    "chat_id": CHANNEL_ID,
                    "caption": (
                        "🧪 <b>END-TO-END TEST — SAMPLE SIGNAL</b>\n\n"
                        "PAIR: EURUSD (illustrative only)\n"
                        "TIMEFRAME: 1 Minute\n"
                        "DIRECTION: 🟢 CALL\n\n"
                        "⚠️ Demo only — not a live trading signal."
                    ),
                    "parse_mode": "HTML",
                },
                files={"photo": photo},
            )
        print("PASS: Telegram sample signal photo delivered.")

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
