
def create_session_summary(trades, session_number):
    wins = sum(1 for trade in trades if trade["result"] == "WIN")
    losses = sum(1 for trade in trades if trade["result"] == "LOSS")
    total = wins + losses

    if total != 12:
        return None

    accuracy = (wins / total) * 100

    lines = [
        "🔥 VIP BOT SESSION RESULTS 🔥",
        "",
        f"🤖 {session_number} Bot Session Result -:",
        ""
    ]

    for trade in trades:
        symbol = "📈" if trade["direction"] == "UP" else "📉"
        result = "🟢 WIN" if trade["result"] == "WIN" else "🔴 LOSS"

        lines.append(
            f"{symbol} {trade['pair']} | "
            f"{trade['direction']} ➔ {result} "
            f"({trade.get('type', 'Direct')})"
        )

    lines.extend([
        "",
        "📊 SESSION SUMMARY",
        f"🎯 TOTAL TRADES -: {total}",
        f"🟢 TOTAL WINS -: {wins}",
        f"🔴 TOTAL LOSSES -: {losses}",
        "",
        f"⚡ SESSION ACCURACY -: {accuracy:.1f}%"
    ])

    return "\n".join(lines)
