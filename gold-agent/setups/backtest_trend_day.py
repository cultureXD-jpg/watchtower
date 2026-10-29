# GOLD AGENT: setup test #4, trend day on 1-minute GLD bars.
#
# Rules (fixed before the first run; shared test rules are in common.py):
#   - First hour = 9:30-10:29 ET. Move = 10:29 close vs the 9:30 open.
#   - Big move = at least 0.5% of the open, in either direction.
#   - Trade in that direction at the 10:30 open. Stop = the first hour's opposite extreme
#     (its low for a buy, its high for a short).
#   - No target: hold to the close unless the stop is hit.
#
# Usage: backtest_trend_day.py            -> measuring period only
#        backtest_trend_day.py --unseen   -> also the unseen months (only once a setup has passed)
from common import run, simulate

FIRST_HOUR = 60
BIG = 0.005
NO_TARGET = 1e9


def trade_day(bars):
    if len(bars) <= FIRST_HOUR + 1:
        return None
    first = bars[:FIRST_HOUR]
    move = (first[-1]["c"] - first[0]["o"]) / first[0]["o"]
    if abs(move) < BIG:
        return None
    side = 1 if move > 0 else -1
    stop = min(b["l"] for b in first) if side == 1 else max(b["h"] for b in first)
    return simulate(bars, FIRST_HOUR - 1, side, stop, NO_TARGET)


run(trade_day)
