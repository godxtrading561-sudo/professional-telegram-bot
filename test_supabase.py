"""Read-only Supabase connectivity and bot_state schema check."""
from supabase_db import get_client


def main():
    client = get_client()
    if client is None:
        raise SystemExit("Supabase credentials are missing (SUPABASE_URL / SUPABASE_KEY).")

    try:
        result = client.table("bot_state").select("session_id,state").limit(1).execute()
        print("Supabase connection successful.")
        print("bot_state table is readable; returned rows:", len(result.data or []))
        print("Expected columns: session_id (unique/primary key, text), state (json/jsonb).")
    except Exception as exc:
        raise SystemExit(
            "Supabase check failed. Confirm the bot_state table exists with "
            "session_id (unique/primary key) and state (json/jsonb) columns. "
            f"Details: {exc}"
        )


if __name__ == "__main__":
    main()
