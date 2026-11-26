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
    icon = "🟢" if trade["direction"] == "CALL" else "🔴"
    return (
        f"📊 <b>TRADE SIGNAL #{number}</b>\n\n"
        f"PAIR NAME -: <b>{trade['pair']}</b>\n\n"
        "TIME FRAME -: <b>1 Minute</b>\n\n"
        f"DIRECTION -: {icon} <b>{trade['direction']}</b>\n\n"
        "⚠️ <b>Risk carefully; never chase losses.</b>"
    )


def trade_result_message(trade, result):
    labels = {"PROFIT": "🟢 PROFIT", "LOSS": "🔴 LOSS", "TIE": "🟡 TIE"}
    status = str(result.get("status", "PENDING")).upper()
    return (
        "<b>TRADE RESULT UPDATE</b>\n\n"
        f"PAIR: <b>{trade.get('pair', 'N/A')}</b>\n"
        f"DIRECTION: <b>{trade.get('direction', 'N/A')}</b>\n"
        f"RESULT: <b>{labels.get(status, '⏳ RESULT PENDING — NOT VERIFIED')}</b>\n"
        f"ENTRY: <b>{result.get('entry_price', 'N/A')}</b>\n"
        f"EXPIRY: <b>{result.get('exit_price', 'N/A')}</b>"
    )


def session_close_message(sent, summary):
    return (
        "🔴 <b>VIP SESSION CLOSED! 🔚</b>\n\n"
        "🛡️ Session stopped. Do not overtrade.\n\n"
        f"Successfully sent signals: <b>{sent}/12</b>\n\n"
        f"{summary}\n\n"
        "No further signals will be sent in this session."
    )
