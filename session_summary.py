
def create_session_summary(trades, session_number):
    wins = sum(1 for trade in trades if trade.get("result") == "WIN")
    losses = sum(1 for trade in trades if trade.get("result") == "LOSS")
    ties = sum(1 for trade in trades if trade.get("result") == "TIE")

    total = wins + losses + ties
    decided = wins + losses

    if total == 0:
        return None

    accuracy = (wins / decided) * 100 if decided else 0

    lines = [
        "🔥 VIP BOT SESSION RESULTS 🔥",
        "",
        f"🤖 {session_number} Bot Session Result:",
        "",
    ]

    for trade in trades:
        direction = trade.get("direction", "UNKNOWN")
        symbol = "📈" if direction in ("UP", "CALL") else "📉" if direction in ("DOWN", "PUT") else "➖"

        result = trade.get("result", "PENDING")
        result_icon = {
            "WIN": "🟢 WIN",
            "LOSS": "🔴 LOSS",
            "TIE": "➖ TIE",
            "PENDING": "⏳ PENDING",
        }.get(result, "❓ UNKNOWN")

        lines.append(
            f"{symbol} {trade.get('pair', 'Unknown')} | "
            f"{direction} ➔ {result_icon} "
            f"({trade.get('type', 'Direct')})"
        )

    lines.extend([
        "",
        "📊 SESSION SUMMARY",
        f"🎯 TOTAL TRADES: {total}",
        f"🟢 TOTAL WINS: {wins}",
        f"🔴 TOTAL LOSSES: {losses}",
        f"➖ TOTAL TIES: {ties}",
        f"📈 DECIDED TRADES: {decided}",
        f"⚡ SESSION ACCURACY: {accuracy:.1f}%",
    ])

    return "\n".join(lines)
