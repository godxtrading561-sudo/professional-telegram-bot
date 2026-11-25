"""Supabase persistence helpers for bot session state."""
from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY

_client = None


def get_client():
    global _client
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def save_session(session_id, data):
    client = get_client()
    if client is None:
        return False
    response = client.table("bot_state").upsert(
        {"session_id": session_id, "state": data},
        on_conflict="session_id",
    ).execute()
    return response is not None


def get_session(session_id):
    client = get_client()
    if client is None:
        return None
    response = (
        client.table("bot_state")
        .select("state")
        .eq("session_id", session_id)
        .limit(1)
        .execute()
    )
    if response.data:
        return response.data[0].get("state")
    return None
