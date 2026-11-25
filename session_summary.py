
from state import get_session


def create_session_summary(session_id):
    session = get_session(session_id)

    if not session:
        return "No session data available."

    trades = session.get("trades", [])

    calls = sum(1 for t in trades if t.get("direction") == "CALL")
    puts = sum(1 for t in trades if t.get("direction") == "PUT")

    wins = sum(1 for t in trades if t.get("result") == "WIN")
    losses = sum(1 for t in trades if t.get("result") == "LOSS")

    total = len(trades)
    completed = wins + losses

    accuracy = (wins / completed * 100) if completed else 0

    return (
        "🔥 <b>VIP BOT SESSION RESULTS</b> 🔥\n\n"
        f"📈 CALL Signals: {calls}\n"
        f"📉 PUT Signals: {puts}\n\n"
        f"📊 TOTAL TRADES: {total}\n"
        f"🟢 TOTAL WINS: {wins}\n"
        f"🔴 TOTAL LOSSES: {losses}\n\n"
        f"⚡ SESSION ACCURACY: {accuracy:.1f}%\n"
        f"⏳ RESULTS PENDING: {total - completed}"
    )
