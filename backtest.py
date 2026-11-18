"""
Walk-forward style chronological backtest for signal_engine.py.
Research only: no broker execution, payout, spread, slippage or latency simulation.
Entry = next candle OPEN. Expiry outcome = close of expiry candle.
"""
from collections import defaultdict
from signal_engine import fetch_candles, validate_candles, analyze_market

EXPIRIES = (1, 2, 5)
TRAIN_RATIO = 0.70
MIN_HISTORY = 220

def outcome(candles, signal_index, expiry):
    entry_i = signal_index + 1
    exit_i = entry_i + expiry - 1
    if exit_i >= len(candles):
        return None
    entry = candles[entry_i]["open"]
    exit_price = candles[exit_i]["close"]
    direction = None
    return entry, exit_price

def simulate(candles, start, end, expiry):
    wins = losses = ties = 0
    trades = []
    i = max(start, MIN_HISTORY - 1)
    next_entry = i + 1
    while i < end - expiry:
        # Only candles up to i are passed to the engine.
        signal = analyze_market(candles[:i+1])
        direction = signal.get("direction")
        entry_i = i + 1
        exit_i = entry_i + expiry - 1
        if direction in ("CALL", "PUT") and exit_i < end:
            entry = candles[entry_i]["open"]
            exit_price = candles[exit_i]["close"]
            if exit_price == entry:
                result = "TIE"; ties += 1
            elif (direction == "CALL" and exit_price > entry) or (direction == "PUT" and exit_price < entry):
                result = "WIN"; wins += 1
            else:
                result = "LOSS"; losses += 1
            trades.append({
                "signal_time": candles[i].get("time"),
                "entry_time": candles[entry_i].get("time"),
                "direction": direction, "entry": entry, "exit": exit_price,
                "result": result, "reason": signal.get("reason", "")
            })
            # Non-overlapping trades for this expiry.
            i = exit_i
        else:
            i += 1
    decided = wins + losses
    return {"wins": wins, "losses": losses, "ties": ties,
            "trades": len(trades),
            "win_rate": round(100*wins/decided, 2) if decided else 0.0,
            "log": trades}

def main():
    candles = validate_candles(fetch_candles())
    if len(candles) < 260:
        raise RuntimeError(f"Only {len(candles)} candles. Need at least 260 for this test.")
    split = int(len(candles) * TRAIN_RATIO)
    print(f"Valid candles: {len(candles)} | train: {split} | unseen: {len(candles)-split}")
    for expiry in EXPIRIES:
        train = simulate(candles, MIN_HISTORY-1, split, expiry)
        test = simulate(candles, max(split, MIN_HISTORY-1), len(candles), expiry)
        print(f"\n{expiry}-minute expiry")
        for label, stats in (("TRAIN", train), ("UNSEEN", test)):
            print(f"{label}: trades={stats['trades']} wins={stats['wins']} "
                  f"losses={stats['losses']} ties={stats['ties']} "
                  f"win_rate={stats['win_rate']}%")
        # Save per-trade evidence for later inspection.
        filename = f"trades_{expiry}m_unseen.csv"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("signal_time,entry_time,direction,entry,exit,result,reason\n")
            for t in test["log"]:
                vals = [str(t[k]).replace(",", " ") for k in
                        ("signal_time","entry_time","direction","entry","exit","result","reason")]
                f.write(",".join(vals) + "\n")
        print(f"Saved unseen trade log: {filename}")
    print("\nNOTE: Historical results do not guarantee future performance. "
          "This test does not model payout, spread, slippage or execution delay.")

if __name__ == "__main__":
    main()
    
