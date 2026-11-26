"""Daily Telegram message templates and scheduler-compatible names."""

DAILY_MESSAGES = {
    "morning": """🌅 RISE AND SHINE TRADERS! ☕🔥

🌟 MORNING BRIEFING & FOCUS

\"Consistency is the bridge between goals and wealth.\" 💎📈

🎯 MINDSET -: Calm, Focused & Disciplined
⚠️ REMINDER -: Never chase losses. Protect capital first!

🚀 MISSION -: Follow the signals, execute with precision, and secure the profits.""",

    "schedule": """👑 TODAY BOT SESSION SCHEDULE 👑

⏰ DAILY SESSION TIMINGS

🌅 1st Session -: 09:00 AM

☀️ 2nd Session -: 12:00 PM

🌤️ 3rd Session -: 02:00 PM

🌇 4th Session -: 06:00 PM

🌙 5th Session -: 10:00 PM

⚠️ IMPORTANT NOTE: Be online 5 minutes before the session time! Follow strict money management and protect your capital. 🚀💰""",

    "good_night": """GOOD NIGHT VIP FAMILY! 🌌✨

💤 END OF DAY WRAP-UP

\"Discipline today brings financial freedom tomorrow.\" 💎📈

📊 TODAY'S STATUS -:
Market Closed / Sessions Completed

🧠 MINDSET -: Rest well, recharge, and come back stronger tomorrow.

🛡️ REMINDER -: Protect your peace and your capital. Tomorrow is a new opportunity!

⭐ Sleep tight and get ready for another massive green day ahead! Good night, traders! 🚀""",
}

# Backward-compatible names for any older imports.
MORNING_MESSAGE = DAILY_MESSAGES["morning"]
SCHEDULE_MESSAGE = DAILY_MESSAGES["schedule"]
GOOD_NIGHT_MESSAGE = DAILY_MESSAGES["good_night"]
