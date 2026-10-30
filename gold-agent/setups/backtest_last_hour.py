# GOLD AGENT: setup test #5, last-hour follow-through on 1-minute GLD bars.
#
# Rules (fixed before the first run; shared test rules are in common.py):
#   - First 30 minutes = 9:30-9:59 ET. Move = last close before 10:00 vs the 9:30 open.
#   - Big move = at least 0.25% of the open, in either direction.
#   - Trade in that direction at the 15:00 open. Stop 0.5% from entry. Exit at the close.
#   - Half days have no 15:00 bar, so no trade.
#
# Usage: backtest_last_hour.py            -> measuring period only
#        backtest_last_hour.py --unseen   -> also the unseen months (only once a setup has passed)
from common import LAST_ENTRY, run, simulate

BIG = 0.0025
STOP = 0.005
NO_TARGET = 1e9


def trade_day(bars):
    first = [b for b in bars if b["t"] < "10:00"]
    entry = next((i for i, b in enumerate(bars) if b["t"] == LAST_ENTRY), None)
    if not first or not entry:
        return None
    move = (first[-1]["c"] - first[0]["o"]) / first[0]["o"]
    if abs(move) < BIG:
        return None
    side = 1 if move > 0 else -1
    return simulate(bars, entry - 1, side, bars[entry]["o"] * (1 - side * STOP), NO_TARGET)


run(trade_day)
