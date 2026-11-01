# GOLD AGENT: day trades in GLD using other data, on 1-minute bars. Shared rules are in common.py.
#
# Rules (fixed before the first run). Signals at 10:30 ET use each fund's move since 9:30; enter
# GLD at the 10:30 open, stop 0.5% from entry, hold to the close.
#   GDX/SLV: moved 0.5%+ and GLD has not moved that way: trade GLD in that direction.
#   SPY: down 0.5%+: buy GLD; up 0.5%+: short GLD.
#   TLT: up 0.25%+: buy GLD; down 0.25%+: short GLD.
# Real yields (FRED DFII10, latest value public before the open; 3 basis points or more): falling:
# buy GLD at the open; rising: short GLD at the open. Same stop, hold to the close.
# Busy mornings: setups #1 and #4 only when the last 5 mornings' range is above its median of the
# prior 250 market days.
# Pass bar for this batch: t-value 3+ with the same sign in both halves of the period.
import csv
import os
import statistics
import sys

import requests

from common import GOLD_HOME, LAST_ENTRY, run, simulate

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from config import FRED_KEY

STOP = 0.005
NO_TARGET = 1e9
ENTRY = "10:30"


def fund_move(symbol, day):
    path = os.path.join(GOLD_HOME, "other", f"{symbol}_{day}.csv")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        rows = [r for r in csv.DictReader(f) if r["t"] < ENTRY]
    return (float(rows[-1]["c"]) - float(rows[0]["o"])) / float(rows[0]["o"]) if rows else None


def enter(bars, i, side):
    return simulate(bars, i - 1, side, bars[i]["o"] * (1 - side * STOP), NO_TARGET)


def lead(symbol):
    def trade_day(bars, day):
        i = next((j for j, b in enumerate(bars) if b["t"] == ENTRY), None)
        m = fund_move(symbol, day)
        if not i or m is None or abs(m) < 0.005:
            return None
        side = 1 if m > 0 else -1
        return None if (bars[i - 1]["c"] - bars[0]["o"]) * side > 0 else enter(bars, i, side)
    return trade_day


def macro(symbol, big, side_when_up):
    def trade_day(bars, day):
        i = next((j for j, b in enumerate(bars) if b["t"] == ENTRY), None)
        m = fund_move(symbol, day)
        if not i or m is None or abs(m) < big:
            return None
        return enter(bars, i, side_when_up if m > 0 else -side_when_up)
    return trade_day


obs = requests.get("https://api.stlouisfed.org/fred/series/observations", timeout=30, params={
    "series_id": "DFII10", "api_key": FRED_KEY, "file_type": "json", "observation_start": "2015-12-01"}).json()["observations"]
yields = [(o["date"], float(o["value"])) for o in obs if o["value"] != "."]
seen_days = []


def real_yield(bars, day):
    seen_days.append(day)
    if len(seen_days) < 2 or len(bars) < 2:
        return None
    # DFII10 for a date is published the next afternoon, so before today's open only dates
    # before the previous market day are safely public
    known = [v for d, v in yields if d < seen_days[-2]]
    if len(known) < 2 or abs(known[-1] - known[-2]) < 0.03:
        return None
    side = -1 if known[-1] > known[-2] else 1
    return simulate(bars, 0, side, bars[1]["o"] * (1 - side * STOP), NO_TARGET)


def orb(bars):
    if len(bars) <= 16:
        return None
    hi, lo = max(b["h"] for b in bars[:15]), min(b["l"] for b in bars[:15])
    for i in range(15, len(bars) - 1):
        if bars[i]["t"] > LAST_ENTRY:
            return None
        c = bars[i]["c"]
        if c > hi or c < lo:
            side = 1 if c > hi else -1
            return simulate(bars, i, side, lo if side == 1 else hi, 2.0)
    return None


def trend(bars):
    if len(bars) <= 61:
        return None
    first = bars[:60]
    move = (first[-1]["c"] - first[0]["o"]) / first[0]["o"]
    if abs(move) < 0.005:
        return None
    side = 1 if move > 0 else -1
    stop = min(b["l"] for b in first) if side == 1 else max(b["h"] for b in first)
    return simulate(bars, 59, side, stop, NO_TARGET)


def busy(setup):
    ranges, averages = [], []

    def trade_day(bars):
        go = len(averages) >= 250 and averages[-1] > statistics.median(averages[-250:])
        morning = [b for b in bars if b["t"] < "11:30"]
        ranges.append((max(b["h"] for b in morning) - min(b["l"] for b in morning)) / bars[0]["o"])
        if len(ranges) >= 5:
            averages.append(statistics.mean(ranges[-5:]))
        return setup(bars) if go else None
    return trade_day


TESTS = [("GDX (miners) lead", lead("GDX")), ("SLV (silver) lead", lead("SLV")),
         ("SPY (stocks): opposite", macro("SPY", 0.005, -1)), ("TLT (bonds): same way", macro("TLT", 0.0025, 1)),
         ("Real yields", real_yield), ("Breakout on busy mornings", busy(orb)), ("Trend day on busy mornings", busy(trend))]
for name, test in TESTS:
    print(f"\n== {name}")
    run(test)
