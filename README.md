# PROFESSIONAL TELEGRAM BOT

Automated Telegram channel messenger and signal publisher. All times use **Asia/Kolkata (IST)**.

## GitHub repository setup

Add these repository Actions secrets:

- `BOT_TOKEN` — Telegram bot token
- `CHANNEL_ID` — target private channel ID
- `SUPABASE_URL` — Supabase project URL
- `SUPABASE_KEY` — Supabase service/API key with the required table permissions
- `OTCHARTS_API_KEY` — eligible OTCharts API key for Quotex OTC candles

Never commit tokens or keys to the repository.

## Supabase table requirement

Create a table named `bot_state` with:
- `session_id`: text, unique or primary key
- `state`: jsonb

The Actions task `test_supabase` performs a temporary insert, read-back, and delete check. Do not run trading sessions until this test passes.

## GitHub Actions tasks

Open **Actions → Professional Telegram Bot → Run workflow**:

1. `telegram_test` — sends a Telegram connectivity test message.
2. `test_supabase` — checks durable state storage.
3. `test_otcharts` — checks the configured live Quotex OTC candle feed.
4. `download_data` — downloads historical ordinary Forex/spot candles for research only.
5. `backtest` — evaluates the strategy on downloaded historical data.
6. `daily_messages` — manually sends a due daily message.
7. `run_session` — manually starts a session; do not use until Supabase and OTC preflight both pass.

## IST daily schedule

- 07:00 — Morning briefing
- 08:00 — Daily session schedule
- 09:00, 12:00, 14:00, 18:00, 23:00 — Trading session starts
- 00:00 — Good-night message

GitHub Actions cron uses UTC and may be delayed. Daily messages have a bounded 90-minute catch-up window.

## Session safeguards

- Maximum 12 successfully delivered signals per session.
- At least 5 minutes between signals.
- A session is closed after the signal cap, runtime limit, or an unrecoverable error.
- Closed session IDs cannot be restarted.
- Signals require live Quotex OTC candles; there is no Forex/spot fallback.
- One-minute results are reported only when a complete eligible candle is available. Missing data remains pending.
- Supabase is required before a scheduled session; ephemeral runner storage is not accepted.

## Data and performance limitations

OTCharts is an independent, read-only data provider, not an official Quotex trading API. The bot does not place trades. A working API key and an eligible provider plan are required.

Historical spot Forex candles are **not** Quotex OTC candles and cannot validate OTC signal accuracy. No 80–85% win rate is promised. Backtest results must be checked for sample size, out-of-sample performance, payout, and execution differences before any real-money use.

GitHub scheduled workflows are best-effort and are not guaranteed to start at the exact minute.
