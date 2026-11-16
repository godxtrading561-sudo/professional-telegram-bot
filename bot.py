
import os
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]

URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


def send_message(message):
    response = requests.post(
        URL,
        json={
            "chat_id": CHANNEL_ID,
            "text": message
        },
        timeout=20
    )

    response.raise_for_status()
    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(result)

    print("Message sent successfully!")


if __name__ == "__main__":
    send_message("🤖 PROFESSIONAL BOT CONNECTED! ✅")
    
