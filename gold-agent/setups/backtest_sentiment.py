# GOLD AGENT: day trades in GLD using news and sentiment. Shared rules are in common.py.
#
# Rules (fixed before the first run). Every trade: stop 0.5% from entry, hold to the close.
# Each signal only uses what was public before the entry.
#   Gold volatility index (GVZ) spike: yesterday 10%+ above its 20-day average: buy at the open.
#   Stock fear index (VIX) spike: same rule: buy at the open.
#   Crowded big traders (CFTC non-commercial net long as % of open interest, usable after Friday's
#   release): above the 80th percentile of the prior 3 years: short at the open every day;
#   below the 20th: buy at the open every day.
#   Headline tone, pre-open: headlines containing "gold" since yesterday's close, up words minus
#   down words. Score 2+: buy at the open. -2 or less: short at the open.
#   Headline tone, first hour: same score for 9:30-10:29, trade that way at 10:30.
#   Busy news: 3+ gold headlines before the open: buy if GLD's first hour is up, short if down,
#   at 10:30.
# Pass bar: t-value 3+ and positive in both halves of the period.
import bisect
import csv
import os
import re
import statistics
from datetime import date, timedelta

from common import GOLD_HOME, run, simulate

FOLDER = os.path.join(GOLD_HOME, "sentiment")
STOP = 0.005
NO_TARGET = 1e9
UP = re.compile(r"\b(rise|rises|rising|higher|gain|gains|rally|rallies|surge|surges|jump|jumps|soar|soars|record|climb|climbs)\b", re.I)
DOWN = re.compile(r"\b(fall|falls|falling|lower|drop|drops|slump|slumps|sink|sinks|selloff|tumble|tumbles|retreat|retreats|slide|slides|plunge|plunges)\b", re.I)


def read(name):
    with open(os.path.join(FOLDER, name)) as f:
        return list(csv.DictReader(f))


news = [r for r in read("news_gld.csv") if "gold" in r["headline"].lower()]
news.sort(key=lambda r: r["time_et"])
news_times = [r["time_et"] for r in news]


def headlines(start, end):
    return news[bisect.bisect_left(news_times, start):bisect.bisect_left(news_times, end)]


def tone(rows):
    return sum(bool(UP.search(r["headline"])) - bool(DOWN.search(r["headline"])) for r in rows)


def at_open(bars, side):
    return simulate(bars, 0, side, bars[1]["o"] * (1 - side * STOP), NO_TARGET) if len(bars) > 2 else None


def at_1030(bars, side):
    i = next((j for j, b in enumerate(bars) if b["t"] == "10:30"), None)
    return simulate(bars, i - 1, side, bars[i]["o"] * (1 - side * STOP), NO_TARGET) if i else None


def spike(name):
    rows = [(r["date"], float(r["value"])) for r in read(name)]
    dates = [d for d, _ in rows]
    values = [v for _, v in rows]

    def trade_day(bars, day):
        i = bisect.bisect_left(dates, day)     # last value before today is i - 1
        if i < 21 or values[i - 1] < 1.1 * statistics.mean(values[i - 21:i - 1]):
            return None
        return at_open(bars, 1)
    return trade_day


cftc = [(r["date"], (float(r["long"]) - float(r["short"])) / float(r["open_interest"])) for r in read("cftc_gold.csv")]
usable = [(date.fromisoformat(d) + timedelta(days=3)).isoformat() for d, _ in cftc]   # Tuesday data, out Friday


def crowded(bars, day):
    i = bisect.bisect_left(usable, day)        # released strictly before today
    if i < 157:
        return None
    now = cftc[i - 1][1]
    past = sorted(v for _, v in cftc[i - 157:i - 1])
    if now > past[int(len(past) * 0.8)]:
        return at_open(bars, -1)
    if now < past[int(len(past) * 0.2)]:
        return at_open(bars, 1)
    return None


def with_prev(fn):
    prev = [None]

    def trade_day(bars, day):
        before, prev[0] = prev[0], day
        return fn(bars, day, before) if before else None
    return trade_day


def tone_open(bars, day, before):
    s = tone(headlines(f"{before} 16:00", f"{day} 09:30"))
    return at_open(bars, 1 if s > 0 else -1) if abs(s) >= 2 else None


def tone_hour(bars, day, before):
    s = tone(headlines(f"{day} 09:30", f"{day} 10:30"))
    return at_1030(bars, 1 if s > 0 else -1) if abs(s) >= 2 else None


def busy_news(bars, day, before):
    if len(headlines(f"{before} 16:00", f"{day} 09:30")) < 3 or len(bars) < 61:
        return None
    move = bars[59]["c"] - bars[0]["o"]
    return at_1030(bars, 1 if move > 0 else -1) if move else None


by_year = {}
for r in news:
    by_year[r["time_et"][:4]] = by_year.get(r["time_et"][:4], 0) + 1
print("Gold headlines per year:", by_year)
for name, test in [("Gold volatility spike", spike("GVZCLS.csv")), ("Stock fear spike", spike("VIXCLS.csv")),
                   ("Crowded big traders", crowded), ("Headline tone, pre-open", with_prev(tone_open)),
                   ("Headline tone, first hour", with_prev(tone_hour)), ("Busy news day, follow first hour", with_prev(busy_news))]:
    print(f"\n== {name}")
    run(test)
