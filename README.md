# PROFESSIONAL TELEGRAM BOT

Automated Telegram channel messenger and signal publisher. All times use **Asia/Kolkata (IST)**.

## Data source and strategy

- Quotex OTC M1 candle provider priority: QUANTEX (`QUANTEX_API_KEY`) first, then OTCharts (`OTCHARTS_API_KEY`). Both are independent read-only providers, not official Quotex APIs. If neither provides verified candles, the bot safely skips signals; it never substitutes Yahoo FX spot data for OTC.

- Yahoo Finance yfinance 1-minute candles, requested with period=2d and interval=1m.
- Ten ordinary FX symbols: EUR/USD, GBP/USD, USD/JPY, AUD/CAD, EUR/JPY, GBP/JPY, AUD/USD, USD/CHF, NZD/USD, EUR/GBP.
- Original EMA 9 / EMA 21 + RSI 14 + candle-body confirmation strategy.
- Only completed candles are used; forming candles and stale/invalid data are rejected.
- Yahoo Finance FX quotes and HistData historical candles are ordinary FX spot data, NOT Quotex OTC candles. Results are Yahoo FX candle outcomes and must never be represented as verified Quotex OTC outcomes.

## Required GitHub Actions secrets

- BOT_TOKEN — Telegram bot token
- CHANNEL_ID — target private channel ID
- SUPABASE_URL — Supabase project URL
- SUPABASE_KEY — Supabase server-side service_role key; keep private
- QUANTEX_API_KEY — optional QUANTEX key with `candles:read` access (preferred OTC source)
- OTCHARTS_API_KEY — optional OTCharts key (fallback OTC source)

Never commit tokens or keys.

## Supabase table

Run supabase_schema.sql once in Supabase SQL Editor. The test_supabase task performs temporary insert, read-back, and delete verification. Supabase is required for sessions; local runner storage is not accepted as durable state.

## GitHub Actions tasks

Open Actions → Professional Telegram Bot → Run workflow:

1. telegram_test — sends a Telegram connectivity test.
2. test_supabase — checks durable state storage.
3. test_yahoo_data — checks fresh Yahoo Finance 1-minute FX candles.
4. full_validation — checks live Yahoo Finance 1-minute FX data and verifies Supabase. It does **not** run a backtest.
5. download_data — optional HistData 1-minute regular FX spot download only.
6. daily_messages — manually sends a due daily message.

Trading sessions remain disabled until the live data and persistence checks have passed.

## IST schedule

- 07:00 — Morning briefing
- 08:00 — Daily session schedule
- 09:00, 12:00, 14:00, 18:00, 23:00 — planned session starts
- 00:00 — Good-night message

GitHub Actions cron is best-effort and may start late.

## Safeguards

- Maximum 12 delivered signals per session and at least 5 minutes between signals.
- Session runtime is bounded to 90 minutes.
- Closed session IDs cannot be restarted; closed sessions do not send more signals.
- Supabase is mandatory before a session.
- Missing, malformed, or stale candle data produces no signal/result.
- Unverified results remain pending; no invented WIN/LOSS results.

## Performance limitations

No 80–85% win rate is promised. No backtest is part of the current workflow. Yahoo Finance 1-minute availability and quote timing can vary, and regular FX spot data differs from Quotex OTC prices, payout rules, and execution. Do not use these results as proof of OTC performance or as a guarantee of profit.
