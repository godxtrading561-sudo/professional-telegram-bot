
def session_start_message(session_id):
    return (
        "🚨 <b>VIP SESSION IS LIVE NOW! 🟢🔥</b>\n\n"
        "⚡ <b>SESSION HAS STARTED!</b>\n\n"
        "\"Keep your focus high and emotions low. Patience pays!\" 🎯📈\n\n"
        "💻 <b>STATUS -:</b> Session In Progress\n\n"
        "⏳ <b>ACTION -:</b> Wait for the Signal!\n\n"
        "🛡️ <b>RULE -:</b> Strict Money Management (2%-5% Capital)\n\n"
        "📢 Keep your terminals open and stay alert! "
        "First trade signal is dropping any second... 🚀💰"
    )


def signal_message(number, trade):
    direction = trade["direction"]
    icon = "🟢" if direction == "CALL" else "🔴"

    return (
        "📊 <b>TRADE SIGNAL SETUP</b>\n\n"
        f"PAIR NAME -: <b>{trade['pair']}</b>\n\n"
        "TIME FRAME -: <b>1 Minute</b>\n\n"
        f"DIRECTION -: {icon} <b>{direction}</b>\n\n"
        "⚠️ <b>MONEY MANAGEMENT RULE:</b>\n"
        "Always use proper risk management "
        "(Max 2% to 5% of your total capital per trade). "
        "Stick to a disciplined martingale plan only if your "
        "strategy requires it, and never chase losses blindly! 🚀💰"
    )


def trade_result_message(result):
    status = result.get("status", "UNKNOWN")
    accuracy = result.get("accuracy", "Not available")
    method = result.get("method", "Not available")

    result_text = "🟢 PROFIT (ITM)" if status == "WIN" else "🔴 LOSS (OTM)"

    return (
        "<b>TRADE RESULT UPDATE</b>\n\n"
        f"TRADE RESULT -: {result_text}\n\n"
        f"TRADE ACCURACY -: {accuracy}\n"
        f"TRADE TYPE -: {method}\n\n"
        "💡 PRO TIP: Market mein losses bhi trading ka part hote hain. "
        "Proper money management (2%-5%) aur compound discipline "
        "hi long-term success ki key hai! 🚀💰"
    )


def session_close_message(sent, summary):
    return (
        "🔴 <b>VIP SESSION CLOSED! 🔚✨</b>\n\n"
        "📊 <b>SESSION COMPLETED</b>\n\n"
        "\"Consistency over intensity. Secure your profit and exit the market!\" 🎯📈\n\n"
        "💼 <b>STATUS -:</b> All Trades Wrapped Up\n\n"
        "🛡️ <b>RULE -:</b> Close your terminal now — Do NOT overtrade!\n\n"
        "🧠 <b>MINDSET -:</b> Respect your daily target and protect your capital.\n\n"
        "🎉 Great job today, team! Take your profits, relax, "
        "and get ready for the next session. See you soon! 🚀💰\n\n"
        f"Successfully sent signals: <b>{sent}/12</b>\n\n"
        f"{summary}\n\n"
        "No further signals will be sent in this session."
    )
