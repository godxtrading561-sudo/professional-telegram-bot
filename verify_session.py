"""Verify the newest persisted trading session and its saved expiry results."""
import re
from supabase_db import get_client

SESSION_ID = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}$")
VALID_RESULTS = {"PROFIT", "LOSS", "TIE"}

def main():
    client = get_client()
    if client is None:
        raise SystemExit("Supabase credentials are missing.")
    response = client.table("bot_state").select("session_id,state").execute()
    sessions = [
        row for row in (response.data or [])
        if SESSION_ID.match(str(row.get("session_id", "")))
        and isinstance(row.get("state"), dict)
    ]
    if not sessions:
        raise SystemExit("FAIL: No persisted trading sessions found in bot_state.")
    latest = max(sessions, key=lambda row: row["session_id"])
    session_id, state = latest["session_id"], latest["state"]
    trades = state.get("trades", [])
    saved_count = int(state.get("signals_sent", len(trades)))
    results = [trade.get("result", "PENDING") for trade in trades]
    completed = sum(result in VALID_RESULTS for result in results)
    pending = len(trades) - completed
    print(f"Latest session: {session_id}")
    print(f"Closed: {state.get('closed')}; Active: {state.get('active')}")
    print(f"Signals recorded: {saved_count}; trade rows: {len(trades)}")
    print(f"Verified outcomes: PROFIT={results.count('PROFIT')}, LOSS={results.count('LOSS')}, TIE={results.count('TIE')}")
    print(f"Pending/unrecognized outcomes: {pending}")
    for index, trade in enumerate(trades, start=1):
        print(f"Trade {index}: {trade.get('pair')} {trade.get('direction')} => {trade.get('result', 'PENDING')} (expiry={trade.get('expiry_time', 'not saved')})")
    if not state.get("closed") or state.get("active"):
        raise SystemExit("FAIL: Latest session is not closed/inactive.")
    if saved_count != len(trades) or not trades:
        raise SystemExit("FAIL: Persisted signal count does not match non-empty trade rows.")
    if pending:
        raise SystemExit("FAIL: Some trade results are pending or unrecognized.")
    print("PASS: Latest session is closed and every saved signal has a stored outcome.")

if __name__ == "__main__":
    main()
