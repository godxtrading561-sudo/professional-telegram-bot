# PROFESSIONAL TELEGRAM BOT

## GitHub Secrets

- BOT_TOKEN
- CHANNEL_ID
- SUPABASE_URL
- SUPABASE_KEY

## Python files

- config.py
- state.py
- signal_engine.py
- session_messages.py
- session_summary.py
- session_controller.py
- bot.py
- download_data.py
- backtest.py
- scheduler.py
- daily_messages.py
- supabase_db.py
- test_supabase.py
- test_quotex.py

## Workflow tasks

1. telegram_test
2. download_data
3. backtest
4. test_supabase
5. run_session

## Trading schedule (IST)

09:00 AM
12:00 PM
02:00 PM
06:00 PM
11:00 PM

## Session rules

- Maximum 12 successfully sent signals.
- 5-minute interval between successful signals.
- Retry when no valid setup is found.
- Close after 12 successful signals.

## Important limitations

Yahoo Finance data is ordinary Forex data, not verified Quotex OTC data.
85% accuracy is not guaranteed.
Backtest results must be independently verified before live trading.
GitHub Actions schedules may be delayed.
