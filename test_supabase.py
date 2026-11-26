"""Safe Supabase read/write/delete connectivity test for the bot_state table."""
from datetime import datetime, timezone
from uuid import uuid4

from supabase_db import get_client


def main():
    client = get_client()
    if client is None:
        raise SystemExit("Supabase credentials are missing (SUPABASE_URL / SUPABASE_KEY).")

    probe_id = f"__connection_test__{uuid4().hex}"
    probe_state = {
        "probe": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "temporary connectivity check; safe to delete",
    }
    inserted = False
    try:
        # Verify write permission and the expected session_id/state columns.
        client.table("bot_state").insert(
            {"session_id": probe_id, "state": probe_state}
        ).execute()
        inserted = True

        # Verify that the exact record can be read back.
        result = (
            client.table("bot_state")
            .select("session_id,state")
            .eq("session_id", probe_id)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if len(rows) != 1 or rows[0].get("state") != probe_state:
            raise RuntimeError("Supabase write completed but read-back verification failed.")

        print("PASS: Supabase connection, bot_state write, and read-back verified.")
    except Exception as exc:
        raise SystemExit(
            "Supabase check failed. Ensure bot_state has session_id (text, unique/primary key) "
            "and state (json/jsonb), and that the API key has SELECT, INSERT, and DELETE access. "
            f"Details: {exc}"
        )
    finally:
        if inserted:
            try:
                client.table("bot_state").delete().eq("session_id", probe_id).execute()
                print("Cleanup: temporary test record deleted.")
            except Exception as cleanup_exc:
                print(
                    "WARNING: temporary test row could not be deleted. "
                    f"Delete session_id {probe_id} from bot_state manually. Details: {cleanup_exc}"
                )


if __name__ == "__main__":
    main()
