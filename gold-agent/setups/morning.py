# GOLD AGENT: morning study (9:30-11:30 ET), the part of the day with the most movement.
# Measuring period only (Jan 2016 - Jun 2026), full days. Two questions:
#   A. Can anything known by then predict the DIRECTION of the rest of the morning?
#      Every signal follows its direction to the 11:30 exit. Moves are before costs ($0.02/share
#      is about 0.012%). Each is also split into two halves of the period: a real pattern should
#      show up in both. With this many rows, ask for |t| of 3+ and the same sign in both halves.
#   B. Can anything known before the open predict the SIZE of the morning?
import os
import statistics
import sys

import requests

from common import MOODS, SPLIT, load_days, moods

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from config import FRED_KEY

MID = "2021-04-01"
EXIT = "11:30"


def t(xs):
    return statistics.mean(xs) / (statistics.stdev(xs) / len(xs) ** 0.5) if len(xs) > 2 else 0


def px_at(bars, when):
    """Open of the first bar at or after `when`."""
    return next((b["o"] for b in bars if b["t"] >= when), None)


def release_dates(rid):
    r = requests.get("https://api.stlouisfed.org/fred/release/dates", timeout=30, params={
        "release_id": rid, "api_key": FRED_KEY, "file_type": "json", "realtime_start": "2016-01-01",
        "sort_order": "asc", "limit": 1000})
    r.raise_for_status()
    return {d["date"] for d in r.json()["release_dates"]}


signals = {}


def add(name, day, value):
    signals.setdefault(name, []).append((day, value))


mood_by_day = moods()
dates = sorted(mood_by_day)
prev_mood = {d: mood_by_day[dates[i - 1]] for i, d in enumerate(dates) if i}
cpi, jobs = release_dates(10), release_dates(50)
size = []
prev = None
past_ranges = []
for day, bars in load_days():
    full = len(bars) >= 380
    y, prev = prev, bars
    if day >= SPLIT or not full or y is None or len(y) < 380:
        continue
    o = bars[0]["o"]
    end = px_at(bars, EXIT)
    morning = [b for b in bars if b["t"] < EXIT]
    mrange = (max(b["h"] for b in morning) - min(b["l"] for b in morning)) / o * 100
    gap = (o - y[-1]["c"]) / y[-1]["c"] * 100
    yrange = (max(b["h"] for b in y) - min(b["l"] for b in y)) / y[0]["o"] * 100
    if len(past_ranges) >= 5:
        size.append({"range": mrange, "gap": abs(gap), "yrange": yrange, "avg5": statistics.mean(past_ranges[-5:]),
                     "mood": prev_mood.get(day), "cpi": day in cpi, "jobs": day in jobs})
    past_ranges.append(mrange)

    def follow(name, start, move):
        """Follow the sign of `move` from the open of `start` to the 11:30 exit."""
        p = px_at(bars, start)
        if p and end and move:
            add(name, day, (end - p) / p * 100 * (1 if move > 0 else -1))

    moved = {}
    for label, start in (("5 min", "09:35"), ("15 min", "09:45"), ("30 min", "10:00"), ("60 min", "10:30")):
        p = px_at(bars, start)
        moved[label] = (p - o) / o * 100
        follow(f"Follow first {label}", start, moved[label])
        big = {"5 min": 0.15, "15 min": 0.25, "30 min": 0.35, "60 min": 0.5}[label]
        if abs(moved[label]) >= big:
            follow(f"Follow first {label}, big ({big}%+)", start, moved[label])
    if abs(gap) >= 0.25:
        same = gap * moved["15 min"] > 0
        follow("Gap 0.25%+, first 15 min agrees: follow" if same else "Gap 0.25%+, first 15 min disagrees: follow 15 min", "09:45", moved["15 min"])
    follow("Follow the gap from the open", "09:30", gap)
    follow("Follow yesterday (open to close)", "09:30", y[-1]["c"] - y[0]["o"])
    at10 = [b for b in bars if b["t"] < "10:00"]
    vol = sum(b["v"] for b in at10)
    if at10 and vol:
        follow("Side of VWAP at 10:00: follow", "10:00", at10[-1]["c"] - sum(b["vwap"] * b["v"] for b in at10) / vol)
    hi15, lo15 = max(b["h"] for b in bars[:15]), min(b["l"] for b in bars[:15])
    p10 = px_at(bars, "10:00")
    if p10 and (p10 > hi15 or p10 < lo15):
        follow("Outside 15-min range at 10:00: follow", "10:00", p10 - hi15 if p10 > hi15 else p10 - lo15)
    elif p10:
        follow("Inside 15-min range at 10:00: toward the far side", "10:00", (hi15 + lo15) / 2 - p10)

print("A. Direction: follow the signal to 11:30, before costs (about 0.012%)")
print(f"  {'':52}{'days':>6}{'wins':>6}{'avg':>9}{'t':>7}{'2016-21':>9}{'2021-26':>9}")
for name, rows in signals.items():
    v = [x for _, x in rows]
    a = [x for d, x in rows if d < MID]
    b = [x for d, x in rows if d >= MID]
    print(f"  {name:52}{len(v):>6}{sum(x > 0 for x in v) / len(v):>6.0%}{statistics.mean(v):>+8.3f}%"
          f"{t(v):>7.2f}{statistics.mean(a):>+8.3f}%{statistics.mean(b):>+8.3f}%")

print(f"\nB. Size: morning range (high - low), {len(size)} days, average {statistics.mean(s['range'] for s in size):.2f}%")
print(f"  correlation with: overnight gap size {statistics.correlation([s['gap'] for s in size], [s['range'] for s in size]):+.2f}, "
      f"yesterday's range {statistics.correlation([s['yrange'] for s in size], [s['range'] for s in size]):+.2f}, "
      f"last 5 mornings {statistics.correlation([s['avg5'] for s in size], [s['range'] for s in size]):+.2f}")
for key, name in (("avg5", "last 5 mornings"), ("gap", "overnight gap")):
    ordered = sorted(size, key=lambda s: s[key])
    n = len(ordered) // 3
    parts = [ordered[:n], ordered[n:2 * n], ordered[2 * n:]]
    print(f"  By {name}: quietest third {statistics.mean(s['range'] for s in parts[0]):.2f}%, "
          f"middle {statistics.mean(s['range'] for s in parts[1]):.2f}%, busiest third {statistics.mean(s['range'] for s in parts[2]):.2f}%")
for m in MOODS:
    r = [s["range"] for s in size if s["mood"] == m]
    print(f"  {m:8}{len(r):>5} days  {statistics.mean(r):.2f}%")
for k, name in (("cpi", "CPI days"), ("jobs", "Jobs days")):
    r = [s["range"] for s in size if s[k]]
    print(f"  {name:9}{len(r):>5} days  {statistics.mean(r):.2f}%")
