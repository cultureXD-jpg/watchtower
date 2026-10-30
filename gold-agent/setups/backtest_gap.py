# GOLD AGENT: setup test #7, overnight gap on 1-minute GLD bars.
#
# Rules (fixed before the first run; shared test rules are in common.py):
#   - Gap = the 9:30 open vs yesterday's last close. Big gap = at least 0.5%, either direction.
#   - Wait 15 minutes (9:30-9:44 ET). Trade in the direction of that 15-minute move, whichever
#     way the gap went, at the next open.
#   - Stop = the far end of those 15 minutes. No target: hold to the close.
#
# Usage: backtest_gap.py            -> measuring period only
#        backtest_gap.py --unseen   -> also the unseen months (only once a setup has passed)
from common import run, simulate

BIG = 0.005
WAIT = 15
NO_TARGET = 1e9
last_close = [None]


def trade_day(bars):
    prev, last_close[0] = last_close[0], bars[-1]["c"]
    if prev is None or len(bars) <= WAIT + 1 or abs(bars[0]["o"] - prev) / prev < BIG:
        return None
    first = bars[:WAIT]
    move = first[-1]["c"] - first[0]["o"]
    if move == 0:
        return None
    side = 1 if move > 0 else -1
    stop = min(b["l"] for b in first) if side == 1 else max(b["h"] for b in first)
    return simulate(bars, WAIT - 1, side, stop, NO_TARGET)


run(trade_day)
