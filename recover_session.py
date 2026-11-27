"""Close an interrupted session after its GitHub Actions runner has stopped."""
from supabase_db import get_client
from state import get_session, close_session
from session_summary import create_session_summary
from session_messages import session_close_message
from bot import send_message

def main():
    client = get_client()
    if client is None:
        raise SystemExit("Supabase credentials are missing.")
    rows = client.table("bot_state").select("session_id,state").execute().data or []
    sessions = [
        row for row in rows
        if isinstance(row.get("session_id"), str)
        and len(row["session_id"]) == 16
        and row["session_id"][4] == "-"
        and row["session_id"][7] == "-"
        and row["session_id"][10] == "-"
        and row["session_id"][13] == "-"
        and isinstance(row.get("state"), dict)
        and row["state"].get("active")
        and not row["state"].get("closed")
    ]
    if not sessions:
        print("No active interrupted session found; nothing to recover.")
        return
    row = max(sessions, key=lambda item: item["session_id"])
    session_id = row["session_id"]
    state = get_session(session_id) or {}
    trades = state.get("trades", [])
    sent = int(state.get("signals_sent", len(trades)))
    pending = [i + 1 for i, trade in enumerate(trades) if trade.get("result") not in ("PROFIT", "LOSS", "TIE")]
    if pending:
        raise SystemExit(f"Refusing recovery: unresolved trade results at positions {pending}.")
    summary = create_session_summary(session_id)
    message = session_close_message(sent, summary)
    message = message.replace("TEST SESSION CLOSED!", "TEST SESSION RECOVERED & CLOSED!")
    message += "\n\n⚠️ Runner was interrupted; no additional signals will be sent."
    if not send_message(message):
        raise SystemExit("Telegram close notification failed; session state left active for safe retry.")
    if not close_session(session_id):
        raise SystemExit("Telegram close sent, but Supabase close-state update failed.")
    print(f"PASS: Interrupted session {session_id} closed. Saved signals={sent}; all results were already resolved.")

if __name__ == "__main__":
    main()
