from state import get_session


def create_session_summary(session_id):
    session = get_session(session_id)
    if not session:
        return "No session data available."

    trades = session.get("trades", [])
    calls = sum(1 for trade in trades if trade.get("direction") == "CALL")
    puts = sum(1 for trade in trades if trade.get("direction") == "PUT")
    wins = sum(1 for trade in trades if trade.get("result") == "WIN")
    losses = sum(1 for trade in trades if trade.get("result") == "LOSS")
    ties = sum(1 for trade in trades if trade.get("result") == "TIE")
    total = len(trades)
    completed = wins + losses
    accuracy = f"{wins / completed * 100:.1f}%" if completed else "N/A (no verified results)"

    return (
        "🔥 <b>VIP BOT SESSION RESULTS</b> 🔥\n\n"
        f"📈 CALL Signals: {calls}\n"
        f"📉 PUT Signals: {puts}\n\n"
        f"📊 TOTAL SIGNALS: {total}\n"
        f"🟢 VERIFIED WINS: {wins}\n"
        f"🔴 VERIFIED LOSSES: {losses}\n"
        f"🟡 TIES: {ties}\n\n"
        f"⚡ SESSION ACCURACY: {accuracy}\n"
        f"⏳ RESULTS PENDING: {total - completed - ties}"
    )
