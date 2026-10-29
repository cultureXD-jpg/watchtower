# GOLD AGENT: do event days (CPI, jobs report, Fed decision) behave differently from normal days?
# Uses the measuring period only (Oct 2025 - Jun 2026), so the unseen months stay unseen.
#
# Per day, on 1-minute GLD bars:
#   range      = (high - low) / open                      how far it travels
#   net move   = |close - open| / open                    how far it ends up
#   trendiness = |close - open| / (high - low)            1 = straight line, 0 = round trip
#   carries on = the rest of the day moves the same way as the first hour
#   after 2 PM = |close - 14:00 price| / open              the Fed announces at 2 PM ET
import os
import statistics
import sys
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import SPLIT, load_days
from config import FRED_KEY

START = "2025-10-28"
FED_DAYS = {"2025-10-29", "2025-12-10", "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17"}


def release_dates(rid):
    r = requests.get("https://api.stlouisfed.org/fred/release/dates", timeout=30, params={
        "release_id": rid, "api_key": FRED_KEY, "file_type": "json",
        "realtime_start": START, "sort_order": "asc", "limit": 100})
    r.raise_for_status()
    return {d["date"] for d in r.json()["release_dates"] if START <= d["date"] < SPLIT}


EVENTS = {"CPI": release_dates(10), "Jobs": release_dates(50), "Fed": FED_DAYS}


def day_stats(bars):
    o, c = bars[0]["o"], bars[-1]["c"]
    hi, lo = max(b["h"] for b in bars), min(b["l"] for b in bars)
    first = bars[59]["c"] - o
    rest = c - bars[59]["c"]
    two = next((b["o"] for b in bars if b["t"] == "14:00"), c)
    return {"range": (hi - lo) / o * 100, "net": abs(c - o) / o * 100,
            "trend": abs(c - o) / (hi - lo) if hi > lo else 0,
            "carries": (first > 0) == (rest > 0) and first != 0 and rest != 0,
            "after2": abs(c - two) / o * 100}


groups = {"Normal": []}
groups.update({k: [] for k in EVENTS})
for day, bars in load_days():
    if not (START <= day < SPLIT) or len(bars) < 380:     # skip half days
        continue
    s = day_stats(bars)
    tags = [k for k, dates in EVENTS.items() if day in dates]
    for k in tags or ["Normal"]:
        groups[k].append(s)

print("Dates found:", {k: sorted(v) for k, v in EVENTS.items()})
print()
print(f"{'':8}{'days':>5}{'range':>9}{'net move':>10}{'trendiness':>12}{'carries on':>12}{'after 2 PM':>12}")
for k, rows in groups.items():
    if not rows:
        print(f"{k:8}{0:>5}")
        continue
    avg = lambda f: statistics.mean(r[f] for r in rows)
    print(f"{k:8}{len(rows):>5}{avg('range'):>8.2f}%{avg('net'):>9.2f}%{avg('trend'):>12.2f}"
          f"{sum(r['carries'] for r in rows) / len(rows):>11.0%}{avg('after2'):>11.2f}%")
