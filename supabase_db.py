
import os
import requests

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

TABLE_URL = f"{SUPABASE_URL}/rest/v1/bot_state"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
}

def save_bot_state(state_id, data):
    response = requests.post(
        TABLE_URL,
        headers={
            **HEADERS,
            "Prefer": "resolution=merge-duplicates,return=minimal",
        },
        json={"id": state_id, "data": data},
        params={"on_conflict": "id"},
        timeout=20,
    )
    response.raise_for_status()

def load_bot_state(state_id):
    response = requests.get(
        TABLE_URL,
        headers=HEADERS,
        params={
            "id": f"eq.{state_id}",
            "select": "data",
        },
        timeout=20,
    )
    response.raise_for_status()
    rows = response.json()
    return rows[0]["data"] if rows else {}
  
