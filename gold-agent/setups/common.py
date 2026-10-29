# GOLD AGENT: shared pieces for setup tests on 1-minute GLD bars.
#
# Test rules every setup follows (agreed Oct 28, 2026):
#   - Fill at the next bar's open after the signal. One trade per day. No new entries after 15:00 ET.
#   - 1R = entry-to-stop distance. If stop and target are both touched in the same minute, count the stop.
#   - Anything still open is closed at the last bar's close (no overnight holds).
#   - Costs: $0.02/share round trip, taken off every trade.
#   - Measure on Oct 2025 - Jun 2026 only. Jul - Oct 2026 stays unseen until a setup passes.
import csv
import glob
import os
import sys

GOLD_HOME = os.environ.get("GOLD_HOME", "/var/lib/gold-agent")
SPLIT = "2026-07-01"          # first unseen day
COST = 0.02
LAST_ENTRY = "15:00"


def load_days():
    for path in sorted(glob.glob(os.path.join(GOLD_HOME, "intraday", "GLD_*.csv"))):
        with open(path) as f:
            rows = list(csv.DictReader(f))
        bars = [{"t": r["Time (ET)"][11:], "o": float(r["Open"]), "h": float(r["High"]),
                 "l": float(r["Low"]), "c": float(r["Close"]), "v": float(r["Volume"]),
                 "vwap": float(r["VWAP"]) if r["VWAP"] else float(r["Close"])} for r in rows]
        yield os.path.basename(path)[4:14], bars


def simulate(bars, i, side, stop, target_r):
    """Signal on bar i; fill at bar i+1's open. side is 1 (long) or -1 (short)."""
    entry = bars[i + 1]["o"]
    risk = (entry - stop) * side
    if risk <= 0:            # opened past the stop already
        return None
    target = entry + side * target_r * risk
    exit_px, why = bars[-1]["c"], "close"
    for b in bars[i + 1:]:
        hit_stop = b["l"] <= stop if side == 1 else b["h"] >= stop
        hit_tgt = b["h"] >= target if side == 1 else b["l"] <= target
        if hit_stop:
            exit_px, why = stop, "stop"
            break
        if hit_tgt:
            exit_px, why = target, "target"
            break
    pnl = (exit_px - entry) * side - COST
    return {"side": "long" if side == 1 else "short", "entry": entry, "risk": risk,
            "r": pnl / risk, "why": why, "time": bars[i + 1]["t"]}


def summary(name, trades):
    if not trades:
        print(f"{name}: no trades")
        return
    rs = [t["r"] for t in trades]
    wins = sum(r > 0 for r in rs)
    total = sum(rs)
    # worst run of losses, in R, from a running peak
    peak = run = dd = 0.0
    for r in rs:
        run += r
        peak = max(peak, run)
        dd = min(dd, run - peak)
    exits = {k: sum(t["why"] == k for t in trades) for k in ("target", "stop", "close")}
    print(f"{name}: {len(trades)} trades | win rate {wins / len(trades):.0%} | "
          f"average {total / len(trades):+.3f}R | total {total:+.1f}R | worst drop {dd:.1f}R | "
          f"exits: {exits['target']} target, {exits['stop']} stop, {exits['close']} at close")
    for side in ("long", "short"):
        s = [t["r"] for t in trades if t["side"] == side]
        if s:
            print(f"   {side:5}: {len(s)} trades, average {sum(s) / len(s):+.3f}R")
    avg_risk = sum(t["risk"] for t in trades) / len(trades)
    print(f"   average risk per share ${avg_risk:.2f} (costs are ${COST:.2f}, so about "
          f"{COST / avg_risk:.2f}R per trade)")


def run(trade_day):
    """Run a setup's trade_day(bars) over every saved day and print the results."""
    show_unseen = "--unseen" in sys.argv
    measure, unseen = [], []
    for day, bars in load_days():
        t = trade_day(bars)
        if t:
            t["day"] = day
            (measure if day < SPLIT else unseen).append(t)
    summary("Measuring period (Oct 2025 - Jun 2026)", measure)
    if show_unseen:
        summary("Unseen period (Jul - Oct 2026)", unseen)
    else:
        print(f"Unseen period: {len(unseen)} trades, results hidden until the setup passes.")
