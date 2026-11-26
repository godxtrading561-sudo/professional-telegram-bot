from state import get_session


def create_session_summary(session_id):
    session = get_session(session_id)
    if not session:
        return "No session data available."
    trades = session.get("trades", [])
    calls = sum(1 for t in trades if t.get("direction") == "CALL")
    puts = sum(1 for t in trades if t.get("direction") == "PUT")
    profits = sum(1 for t in trades if t.get("result") == "PROFIT")
    losses = sum(1 for t in trades if t.get("result") == "LOSS")
    ties = sum(1 for t in trades if t.get("result") == "TIE")
    total = len(trades)
    completed = profits + losses
    accuracy = f"{profits / completed * 100:.1f}%" if completed else "N/A (no verified results)"
    return (
        "🔥 <b>VIP BOT SESSION RESULTS</b> 🔥\n\n"
        f"📈 CALL Signals: {calls}\n📉 PUT Signals: {puts}\n\n"
        f"📊 TOTAL SIGNALS: {total}\n"
        f"🟢 PROFIT: {profits}\n🔴 LOSS: {losses}\n🟡 TIES: {ties}\n\n"
        f"⚡ SESSION ACCURACY: {accuracy}\n"
        f"⏳ RESULTS PENDING: {total - completed - ties}"
    )
