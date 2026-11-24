def session_start_message(session_id):
    return (
        "🟢 <b>TRADING SESSION STARTED</b>\n\n"
        f"Session: <b>{session_id}</b>\n"
        "Timeframe: <b>1 Minute</b>\n"
        "Maximum signals: <b>12</b>\n"
        "⚠️ Use strict risk management."
    )


def signal_message(number, trade):
    direction = trade["direction"]
    icon = "📈" if direction == "CALL" else "📉"

    reasons = "\n".join(
        f"• {reason}" for reason in trade["reasons"]
    )

    return (
        f"🚨 <b>TRADE SIGNAL {number}/12</b>\n\n"
        f"Asset: <b>{trade['pair']}</b>\n"
        "Timeframe: <b>1 Minute</b>\n"
        f"Direction: {icon} <b>{direction}</b>\n"
        f"Confluence score: <b>{trade['score']}/5</b>\n\n"
        f"<b>Reasons:</b>\n{reasons}\n\n"
        "⚠️ Confirm price and execution on your trading platform."
    )


def session_close_message(sent, summary):
    return (
        "🔒 <b>SESSION CLOSED</b>\n\n"
        f"Successfully sent signals: <b>{sent}/12</b>\n"
        f"{summary}\n\n"
        "No further signals will be sent in this session."
    )
