def session_start_message(session_id):
    return (
        "🚨 <b>TEST SESSION STARTED 🟢</b>\n\n"
        "⚡ <b>Yahoo Finance FX spot data test</b>\n\n"
        "This is ordinary Forex market data, NOT Quotex OTC data.\n\n"
        "⏳ Wait for a confirmed strategy setup.\n"
        "🛡️ No real-money result or OTC accuracy is implied."
    )


def signal_message(number, trade):
    icon = "🟢" if trade["direction"] == "CALL" else "🔴"
    return (
        f"📊 <b>FX SPOT TEST SIGNAL #{number}</b>\n\n"
        f"PAIR NAME -: <b>{trade['pair']}</b>\n\n"
        "TIME FRAME -: <b>1 Minute</b>\n\n"
        f"DIRECTION -: {icon} <b>{trade['direction']}</b>\n\n"
        "DATA SOURCE: <b>Yahoo Finance FX spot (NOT Quotex OTC)</b>\n\n"
        "⚠️ <b>Research/test signal only. No accuracy guarantee.</b>"
    )


def trade_result_message(trade, result):
    labels = {"PROFIT": "🟢 PROFIT", "LOSS": "🔴 LOSS", "TIE": "🟡 TIE"}
    status = str(result.get("status", "PENDING")).upper()
    return (
        "<b>FX SPOT TEST RESULT</b>\n\n"
        f"PAIR: <b>{trade.get('pair', 'N/A')}</b>\n"
        f"DIRECTION: <b>{trade.get('direction', 'N/A')}</b>\n"
        f"RESULT: <b>{labels.get(status, '⏳ RESULT PENDING — NOT VERIFIED')}</b>\n"
        f"ENTRY: <b>{result.get('entry_price', 'N/A')}</b>\n"
        f"EXPIRY: <b>{result.get('exit_price', 'N/A')}</b>\n"
        "SOURCE: Yahoo Finance FX spot — not Quotex OTC"
    )


def session_close_message(sent, summary):
    return (
        "🔴 <b>TEST SESSION CLOSED! 🔚</b>\n\n"
        "🛡️ Session stopped.\n\n"
        f"Successfully sent signals: <b>{sent}/12</b>\n\n"
        f"{summary}\n\n"
        "No further signals will be sent in this session."
    )
