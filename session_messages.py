def session_start_message(session_id):
    return (
        "🚨 <b>VIP SESSION IS LIVE NOW! 🟢🔥</b>\n\n"
        "⚡ <b>SESSION HAS STARTED!</b>\n\n"
        "\"Keep your focus high and emotions low. Patience pays!\" 🎯📈\n\n"
        "💻 <b>STATUS -:</b> Session In Progress\n\n"
        "⏳ <b>ACTION -:</b> Wait for the Signal!\n\n"
        "🛡️ <b>RULE -:</b> Strict Money Management (2%-5% Capital)\n\n"
        "📢 Keep your terminals open and stay alert! 🚀💰"
    )


def signal_message(number, trade):
    direction = trade["direction"]
    icon = "🟢" if direction == "CALL" else "🔴"
    return (
        f"📊 <b>TRADE SIGNAL #{number}</b>\n\n"
        f"PAIR NAME -: <b>{trade['pair']}</b>\n\n"
        "TIME FRAME -: <b>1 Minute</b>\n\n"
        f"DIRECTION -: {icon} <b>{direction}</b>\n\n"
        "⚠️ <b>Risk carefully; never chase losses.</b>"
    )


def trade_result_message(result):
    status = str(result.get("status", "PENDING")).upper()
    accuracy = result.get("accuracy", "Not available")
    method = result.get("method", "Not available")
    labels = {
        "WIN": "🟢 PROFIT (ITM)",
        "LOSS": "🔴 LOSS (OTM)",
        "TIE": "🟡 TIE",
    }
    result_text = labels.get(status, "⏳ RESULT PENDING — not verified")
    return (
        "<b>TRADE RESULT UPDATE</b>\n\n"
        f"TRADE RESULT -: {result_text}\n"
        f"TRADE ACCURACY -: {accuracy}\n"
        f"TRADE TYPE -: {method}"
    )


def session_close_message(sent, summary):
    return (
        "🔴 <b>VIP SESSION CLOSED! 🔚</b>\n\n"
        "🛡️ Session stopped. Do not overtrade.\n\n"
        f"Successfully sent signals: <b>{sent}/12</b>\n\n"
        f"{summary}\n\n"
        "No further signals will be sent in this session."
    )
