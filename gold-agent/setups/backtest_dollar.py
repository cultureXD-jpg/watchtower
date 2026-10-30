# GOLD AGENT: setup test #8, dollar disagreement on 1-minute GLD and UUP bars.
#
# Rules (fixed before the first run; shared test rules are in common.py):
#   - At 10:30 ET compare each fund's move since its 9:30 open.
#   - UUP down 0.2% or more and GLD flat or down -> buy GLD (gold should catch up).
#   - UUP up 0.2% or more and GLD flat or up -> sell GLD short.
#   - Enter at the 10:30 open. Stop 0.5% from entry. No target: hold to the close.
#
# Usage: backtest_dollar.py            -> measuring period only
#        backtest_dollar.py --unseen   -> also the unseen months (only once a setup has passed)
import csv
import os

from common import GOLD_HOME, run, simulate

BIG = 0.002
STOP = 0.005
ENTRY = "10:30"
NO_TARGET = 1e9
day_index = [None]


def uup_move(day):
    path = os.path.join(GOLD_HOME, "uup", f"UUP_{day}.csv")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        rows = [r for r in csv.DictReader(f) if r["t"] < ENTRY]
    return (float(rows[-1]["c"]) - float(rows[0]["o"])) / float(rows[0]["o"]) if rows else None


def trade_day(bars, day):
    i = next((j for j, b in enumerate(bars) if b["t"] == ENTRY), None)
    dollar = uup_move(day)
    if not i or dollar is None or abs(dollar) < BIG:
        return None
    gold = bars[i - 1]["c"] - bars[0]["o"]
    side = 1 if dollar < 0 else -1
    if gold * side > 0:        # gold has already moved the expected way
        return None
    return simulate(bars, i - 1, side, bars[i]["o"] * (1 - side * STOP), NO_TARGET)


run(trade_day)
