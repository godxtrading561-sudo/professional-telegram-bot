from collections import defaultdict
from signal_engine import get_candles, validate_candles, analyze_market

PAIR = "EURUSD_otc"
MIN_HISTORY = 220
EXPIRIES = (1, 2, 5)
TRAIN_RATIO = 0.70

# These are the 50 setup names emitted by the supplied signal_engine.py.
# The two confluence labels are deliberately excluded: they are not separate setups.
SETUP_NAMES = [
    "01 support pin", "02 resistance star", "03 SBR retest",
    "04 RBS retest", "05 bullish engulf support",
    "06 bearish engulf resistance", "07 morning star",
    "08 evening star", "09 three candle continuation",
    "10 exhaustion reversal", "11 inside bar break",
    "12 double top proxy", "13 double bottom proxy",
    "14 round number rejection", "15 gap fill",
    "16 ascending line bounce", "17 descending line reject",
    "18 trendline breakout proxy", "19 channel bounce",
    "20 triangle breakout proxy", "21 rising wedge breakdown proxy",
    "22 falling wedge breakout proxy", "23 EMA cross",
    "24 EMA20 pullback", "25 SMA50 bounce", "26 EMA200 filter",
    "27 rainbow EMA", "28 SMA5 cross proxy",
    "29 EMA squeeze breakout", "30 SMA100 rejection",
    "31 RSI reversal", "32 RSI divergence proxy", "33 RSI50 bounce",
    "34 stochastic extreme", "35 MACD zero cross",
    "36 MACD histogram flip", "37 CCI extreme", "38 Williams bounce",
    "39 DeMarker reversal", "40 AO momentum",
    "41 Bollinger reversal", "42 Bollinger squeeze breakout",
    "43 BB plus RSI", "44 Keltner squeeze proxy",
    "45 SAR direction proxy", "46 SAR plus MACD",
    "47 Ichimoku cloud proxy", "48 Alligator EMA proxy",
    "49 fractal breakout", "50 Fibonacci pullback",
]


def parse_setup_reasons(reason_text):
    """Read the individual setup votes from analyze_market()['reason']."""
    found = {}
    for part in (reason_text or "").split(","):
        part = part.strip()
        if "=" not in part:
            continue
        name, direction = part.rsplit("=", 1)
        if name in SETUP_NAMES and direction in ("CALL", "PUT"):
            found[name] = direction
    return found


def trade_outcome(candles, entry_index, expiry, direction):
    exit_index = entry_index + expiry - 1
    entry = candles[entry_index]["open"]
    exit_price = candles[exit_index]["close"]
    if exit_price == entry:
        outcome = "TIE"
    elif (direction == "CALL" and exit_price > entry) or (
        direction == "PUT" and exit_price < entry
    ):
        outcome = "WIN"
    else:
        outcome = "LOSS"
    return {
        "time": candles[entry_index]["time"],
        "direction": direction,
        "entry": entry,
        "exit": exit_price,
        "outcome": outcome,
        "expiry": expiry,
    }


def simulate(candles, start, end, expiry):
    """Combined engine result, with non-overlapping trades."""
    trades = []
    next_entry = max(start, MIN_HISTORY - 1)
    for i in range(max(start, MIN_HISTORY - 1), end - expiry):
        entry_index = i + 1
        if entry_index < next_entry:
            continue
        try:
            signal = analyze_market(candles[:i + 1])
        except (ValueError, RuntimeError, KeyError, IndexError, ZeroDivisionError):
            continue
        direction = signal.get("direction")
        if direction not in ("CALL", "PUT"):
            continue
        trades.append(trade_outcome(candles, entry_index, expiry, direction))
        next_entry = entry_index + expiry
    return trades


def simulate_each_setup(candles, start, end, expiry):
    """Each setup gets its own independent, non-overlapping trade stream."""
    trades_by_setup = defaultdict(list)
    next_entry = {name: max(start, MIN_HISTORY - 1) for name in SETUP_NAMES}

    for i in range(max(start, MIN_HISTORY - 1), end - expiry):
        entry_index = i + 1
        try:
            signal = analyze_market(candles[:i + 1])
            active = parse_setup_reasons(signal.get("reason", ""))
        except (ValueError, RuntimeError, KeyError, IndexError, ZeroDivisionError):
            continue

        for name, direction in active.items():
            if entry_index < next_entry[name]:
                continue
            trades_by_setup[name].append(
                trade_outcome(candles, entry_index, expiry, direction)
            )
            next_entry[name] = entry_index + expiry

    return trades_by_setup


def stats(trades):
    wins = sum(t["outcome"] == "WIN" for t in trades)
    losses = sum(t["outcome"] == "LOSS" for t in trades)
    ties = sum(t["outcome"] == "TIE" for t in trades)
    decided = wins + losses
    rate = (wins / decided * 100) if decided else None
    return wins, losses, ties, rate


def print_report(trades, title):
    wins, losses, ties, rate = stats(trades)
    print(f"\n--- {title} ---")
    print(f"Trades: {len(trades)} | Wins: {wins} | Losses: {losses} | Ties: {ties}")
    print("Win rate:", f"{rate:.2f}%" if rate is not None else "N/A")


def print_setup_table(results, title):
    print(f"\n{title}")
    print(f"{'SETUP':38} {'TRADES':>7} {'W':>5} {'L':>5} {'T':>5} {'RATE':>9}")
    print("-" * 74)
    rows = []
    for name in SETUP_NAMES:
        trades = results.get(name, [])
        w, l, t, rate = stats(trades)
        rows.append((name, len(trades), w, l, t, rate))
    # Most-tested setups first; rate is not ranked as meaningful when sample is tiny.
    rows.sort(key=lambda x: (-x[1], x[0]))
    for name, total, w, l, t, rate in rows:
        rate_text = f"{rate:.2f}%" if rate is not None else "N/A"
        print(f"{name:38} {total:7d} {w:5d} {l:5d} {t:5d} {rate_text:>9}")


def main():
    print("Downloading historical candles...")
    candles = validate_candles(get_candles())
    count = len(candles)
    split = int(count * TRAIN_RATIO)

    print("PAIR:", PAIR)
    print("VALID CANDLES:", count)
    print("TRAIN CANDLES:", split)
    print("UNSEEN TEST CANDLES:", count - split)

    if split < MIN_HISTORY + 10:
        raise RuntimeError("Not enough training history")
    if count - split < 10:
        raise RuntimeError("Not enough unseen test candles")

    for expiry in EXPIRIES:
        print(f"\n{'=' * 18} EXPIRY: {expiry} MINUTE(S) {'=' * 18}")

        train_combined = simulate(candles, MIN_HISTORY - 1, split, expiry)
        test_combined = simulate(candles, split, count, expiry)
        print_report(train_combined, "COMBINED TRAINING")
        print_report(test_combined, "COMBINED UNSEEN TEST")

        train_setups = simulate_each_setup(candles, MIN_HISTORY - 1, split, expiry)
        test_setups = simulate_each_setup(candles, split, count, expiry)
        print_setup_table(train_setups, "INDIVIDUAL SETUPS — TRAINING")
        print_setup_table(test_setups, "INDIVIDUAL SETUPS — UNSEEN TEST")

    print("\nIMPORTANT:")
    print("- Individual setup trades overlap across different setups; do not add their totals.")
    print("- A setup with very few trades has an unreliable win-rate estimate.")
    print("- The engine's proxy setups remain proxies; this report does not make them exact indicators.")
    print("- This is a research backtest, not a live-trading recommendation.")


if __name__ == "__main__":
    main()
    
