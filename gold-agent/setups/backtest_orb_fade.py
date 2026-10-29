# GOLD AGENT: setup test #3, fading the opening range on 1-minute GLD bars.
#
# Rules (fixed before the first run; shared test rules are in common.py):
#   - Opening range = high/low of the first 15 minutes (9:30-9:44 ET). Width = high - low.
#   - From 9:45 ET: a bar that dips into the bottom 10% of the range but closes inside it -> buy.
#     A bar that pokes into the top 10% but closes inside it -> sell short.
#   - If any bar closes outside the range first, the range has broken: no trade that day.
#   - Stop = a quarter of the width beyond the range edge.
#   - Target = the middle of the range (so the target in R varies by trade).
#
# Usage: backtest_orb_fade.py            -> measuring period only
#        backtest_orb_fade.py --unseen   -> also the unseen months (only once a setup has passed)
from common import LAST_ENTRY, run, simulate

OR_MINUTES = 15
NEAR = 0.10
STOP_BEYOND = 0.25


def trade_day(bars):
    if len(bars) <= OR_MINUTES + 1:
        return None
    hi = max(b["h"] for b in bars[:OR_MINUTES])
    lo = min(b["l"] for b in bars[:OR_MINUTES])
    width = hi - lo
    if width <= 0:
        return None
    mid = (hi + lo) / 2
    for i in range(OR_MINUTES, len(bars) - 1):
        b = bars[i]
        if b["t"] > LAST_ENTRY or b["c"] > hi or b["c"] < lo:
            return None
        if b["l"] <= lo + NEAR * width:
            side, stop = 1, lo - STOP_BEYOND * width
        elif b["h"] >= hi - NEAR * width:
            side, stop = -1, hi + STOP_BEYOND * width
        else:
            continue
        entry = bars[i + 1]["o"]
        risk = (entry - stop) * side
        reward = (mid - entry) * side
        if risk <= 0 or reward <= 0:
            return None
        return simulate(bars, i, side, stop, reward / risk)
    return None


run(trade_day)
