# GOLD AGENT: setup test #6, opening-range breakout after a quiet day, on 1-minute GLD bars.
#
# Rules (fixed before the first run; shared test rules are in common.py):
#   - Only trade if yesterday's range (high - low, as % of its open) was the smallest of the
#     last 7 market days, yesterday included.
#   - Then the same rules as setup #1: 15-minute opening range, first close outside it,
#     stop at the other side, target 2R.
#
# Usage: backtest_quiet_breakout.py            -> measuring period only
#        backtest_quiet_breakout.py --unseen   -> also the unseen months (only once a setup has passed)
from common import LAST_ENTRY, run, simulate

OR_MINUTES = 15
TARGET_R = 2.0
QUIET_DAYS = 7
ranges = []


def breakout(bars):
    if len(bars) <= OR_MINUTES + 1:
        return None
    hi = max(b["h"] for b in bars[:OR_MINUTES])
    lo = min(b["l"] for b in bars[:OR_MINUTES])
    for i in range(OR_MINUTES, len(bars) - 1):
        if bars[i]["t"] > LAST_ENTRY:
            return None
        c = bars[i]["c"]
        if c > hi or c < lo:
            side = 1 if c > hi else -1
            return simulate(bars, i, side, lo if side == 1 else hi, TARGET_R)
    return None


def trade_day(bars):
    recent = ranges[-QUIET_DAYS:]
    quiet = len(recent) == QUIET_DAYS and recent[-1] == min(recent)
    ranges.append((max(b["h"] for b in bars) - min(b["l"] for b in bars)) / bars[0]["o"])
    return breakout(bars) if quiet else None


run(trade_day)
