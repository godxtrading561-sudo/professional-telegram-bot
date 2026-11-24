from state import get_session


def create_session_summary(session_id):
    session = get_session(session_id)

    if not session:
        return "No session data available."

    trades = session.get("trades", [])
    calls = sum(1 for t in trades if t["direction"] == "CALL")
    puts = sum(1 for t in trades if t["direction"] == "PUT")

    return (
        f"CALL signals: {calls}\n"
        f"PUT signals: {puts}\n"
        f"Total signals: {len(trades)}"
    )
