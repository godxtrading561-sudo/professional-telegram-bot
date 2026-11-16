import os
import requests

BOT_TOKEN = os.environ["9239337248:AAEk3gd0csmrosxUVP7EidVmXqbon2ekRIQ"]
CHANNEL_ID = os.environ["-1004478501088"]

URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

def send_message(message):
    response = requests.post(
        URL,
        data={
            "chat_id": CHANNEL_ID,
            "text": message
        },
        timeout=20
    )
    response.raise_for_status()
    print("Message sent successfully!")

if name == "main":
    send_message("🤖 PROFESSIONAL BOT CONNECTED! ✅")
