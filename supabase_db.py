"""Supabase persistence helpers for bot session state and scheduler locks."""
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


def claim_daily_message(message_key, scheduled_at):
    """Atomically claim one scheduled message using bot_state.session_id's primary key."""
    client = get_client()
    if client is None:
        raise RuntimeError("Supabase is required for daily-message deduplication.")
    try:
        client.table("bot_state").insert({
            "session_id": f"daily-message:{message_key}",
            "state": {"kind": "daily_message", "scheduled_at": scheduled_at},
        }).execute()
        return True
    except Exception as exc:
        # A unique-key conflict means another run already claimed/sent this item.
        existing = client.table("bot_state").select("session_id").eq(
            "session_id", f"daily-message:{message_key}"
        ).limit(1).execute()
        if existing.data:
            return False
        raise RuntimeError("Could not claim daily message in Supabase.") from exc


def release_daily_message(message_key):
    """Release a claim only when Telegram explicitly reports delivery failure."""
    client = get_client()
    if client is None:
        return False
    client.table("bot_state").delete().eq(
        "session_id", f"daily-message:{message_key}"
    ).execute()
    return True
