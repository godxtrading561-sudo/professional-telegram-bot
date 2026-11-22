PROFESSIONAL TELEGRAM BOT
=========================

FILES
-----
bot.py
signal_engine.py
backtest.py
requirements.txt
.github/workflows/bot.yml

GITHUB SECRETS
--------------
Open GitHub Repository:
Settings > Secrets and variables > Actions > New repository secret

Add these two secrets:

BOT_TOKEN
CHANNEL_ID

Do not paste your bot token publicly.

INSTALLATION
------------
1. Upload all files to your GitHub repository.
2. Create the .github/workflows folder.
3. Put bot.yml inside that folder.
4. Add BOT_TOKEN and CHANNEL_ID to GitHub Secrets.
5. Open the Actions tab.
6. Select Professional Telegram Bot.

TELEGRAM TEST
-------------
Choose workflow_dispatch.
Select telegram_test.
Click Run workflow.

BACKTEST
--------
Choose workflow_dispatch.
Select backtest.
Click Run workflow.

Download the backtest-report artifact to view results.

LIVE SESSION
------------
Choose workflow_dispatch.
Select run_session.
Click Run workflow.

AUTOMATIC SESSION TIMES (INDIA)
--------------------------------
09:00 AM
12:00 PM
02:00 PM
06:00 PM
11:00 PM

SESSION RULES
-------------
Maximum 12 successfully sent signals per session.
5-minute gap after a successfully sent signal.
No valid setup: retry after 30 seconds.
After 12 successful sends: send SESSION CLOSED.
No more signals after session closure.

IMPORTANT LIMITATIONS
---------------------
1. This version uses Yahoo Finance data for normal Forex.
2. It does NOT receive Quotex OTC candles.
3. A 1-minute OHLC feed cannot guarantee an exact
   10-15 second pre-entry alert.
4. GitHub Actions is not a permanent 24/7 server.
5. Scheduled GitHub Actions runs can be delayed.
6. No strategy can guarantee 80-85% accuracy.
   Check actual backtest results before live use.

TIMEZONE
--------
Asia/Kolkata (IST)
