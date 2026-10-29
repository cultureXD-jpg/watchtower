# GOLD AGENT: setup test #1, opening-range breakout (ORB) on 1-minute GLD bars.
# Result Oct 28, 2026: break-even (167 trades, +0.005R average). Not kept.
#
# Rules (shared test rules are in common.py):
#   - Opening range = high/low of the first 15 minutes (9:30-9:44 ET).
#   - First 1-minute close above the range high -> buy; below the range low -> sell short.
#   - Stop = the other side of the range. Target = 2R.
#
# Usage: backtest_orb.py            -> measuring period only
#        backtest_orb.py --unseen   -> also the unseen months (only once a setup has passed)
from common import LAST_ENTRY, run, simulate

OR_MINUTES = 15
TARGET_R = 2.0


def trade_day(bars):
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


run(trade_day)
