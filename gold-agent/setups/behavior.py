# GOLD AGENT: how does GLD actually behave through the day? No trades, just measurements.
# Measuring period only (Jan 2016 - Jun 2026); full days only. t-value: about 2+ is unlikely luck,
# but with this many numbers a few will reach 2 by chance. No costs are taken off here.
import statistics
from collections import defaultdict
from datetime import date

from common import MOODS, SPLIT, load_days, moods

BUCKETS = [f"{h:02d}:{m:02d}" for h in range(9, 16) for m in (0, 30)][1:]


def t(xs):
    return statistics.mean(xs) / (statistics.stdev(xs) / len(xs) ** 0.5) if len(xs) > 2 else 0


def corr_row(name, xs, ys):
    same = sum(x * y > 0 for x, y in zip(xs, ys)) / len(xs)
    r = statistics.correlation(xs, ys)
    print(f"  {name:38}{len(xs):>6} days  same way {same:>4.0%}  correlation {r:+.3f}")


days = []
prev_close = None
mood_by_day = moods()
dates = sorted(mood_by_day)
prev_mood = {d: mood_by_day[dates[i - 1]] for i, d in enumerate(dates) if i}
for day, bars in load_days():
    pc, prev_close = prev_close, bars[-1]["c"]
    if day >= SPLIT or len(bars) < 380 or pc is None:
        continue
    seg = {}
    for k, name in enumerate(BUCKETS):
        end = BUCKETS[k + 1] if k + 1 < len(BUCKETS) else "16:00"
        b = [x for x in bars if name <= x["t"] < end]
        if b:
            seg[name] = (b[0]["o"], b[-1]["c"], max(x["h"] for x in b), min(x["l"] for x in b), sum(x["v"] for x in b))
    days.append({"day": day, "pc": pc, "o": bars[0]["o"], "c": bars[-1]["c"], "seg": seg, "mood": prev_mood.get(day)})

print(f"{len(days)} full days, {days[0]['day']} to {days[-1]['day']}\n")

print("1. Time of day (each half hour)")
print(f"  {'start':7}{'avg size':>10}{'avg range':>11}{'volume':>9}{'avg drift':>11}{'t':>7}")
total_v = sum(s[4] for d in days for s in d["seg"].values())
for name in BUCKETS:
    rows = [d["seg"][name] for d in days if name in d["seg"]]
    r = [(s[1] - s[0]) / s[0] * 100 for s in rows]
    print(f"  {name:7}{statistics.mean(abs(x) for x in r):>9.3f}%"
          f"{statistics.mean((s[2] - s[3]) / s[0] * 100 for s in rows):>10.3f}%"
          f"{sum(s[4] for s in rows) / total_v:>9.1%}{statistics.mean(r):>+10.3f}%{t(r):>7.2f}")

print("\n2. Where the return comes from (per day)")
night = [(d["o"] - d["pc"]) / d["pc"] * 100 for d in days]
day_r = [(d["c"] - d["o"]) / d["o"] * 100 for d in days]
for name, r in (("Overnight (close to open)", night), ("Daytime (open to close)", day_r)):
    print(f"  {name:28} avg {statistics.mean(r):+.3f}%  t {t(r):+.2f}  total {sum(r):+.0f}%  size {statistics.mean(abs(x) for x in r):.3f}%")
print("  By mood:")
for m in MOODS:
    n = [x for x, d in zip(night, days) if d["mood"] == m]
    a = [x for x, d in zip(day_r, days) if d["mood"] == m]
    print(f"    {m:8}{len(a):>5} days  overnight {statistics.mean(n):+.3f}% (t {t(n):+.2f})  daytime {statistics.mean(a):+.3f}% (t {t(a):+.2f})")

print("\n3. Does a move carry on or reverse?")
pairs = defaultdict(lambda: ([], []))
for i, d in enumerate(days):
    s = d["seg"]
    def ret(a, b):
        return (s[b][1] - s[a][0]) / s[a][0] * 100 if a in s and b in s else None
    candidates = {
        "Overnight gap -> rest of day": ((d["o"] - d["pc"]) / d["pc"] * 100, (d["c"] - d["o"]) / d["o"] * 100),
        "First 30 min -> rest of day": (ret("09:30", "09:30"), ret("10:00", "15:30")),
        "First hour -> rest of day": (ret("09:30", "10:00"), ret("10:30", "15:30")),
        "Morning -> afternoon (split 12:30)": (ret("09:30", "12:00"), ret("12:30", "15:30")),
        "Open to 15:30 -> last 30 min": (ret("09:30", "15:00"), ret("15:30", "15:30")),
    }
    if i:
        candidates["Yesterday -> today (open to close)"] = ((days[i - 1]["c"] - days[i - 1]["o"]) / days[i - 1]["o"] * 100, (d["c"] - d["o"]) / d["o"] * 100)
    for name, (x, y) in candidates.items():
        if x is not None and y is not None and x != 0 and y != 0:
            pairs[name][0].append(x)
            pairs[name][1].append(y)
for name, (xs, ys) in pairs.items():
    corr_row(name, xs, ys)

print("\n4. After a big half hour (0.5%+ move), the next half hour")
print(f"  {'':12}{'cases':>7}{'carry on':>10}{'avg, in the big move direction':>33}{'t':>7}")
for name, lo, hi in (("Morning", "09:30", "11:30"), ("Midday", "11:30", "14:00"), ("Afternoon", "14:00", "15:30")):
    r = []
    for d in days:
        for k, b in enumerate(BUCKETS[:-1]):
            if lo <= b < hi and b in d["seg"] and BUCKETS[k + 1] in d["seg"]:
                s, n = d["seg"][b], d["seg"][BUCKETS[k + 1]]
                m = (s[1] - s[0]) / s[0]
                if abs(m) >= 0.005:
                    r.append((n[1] - n[0]) / n[0] * 100 * (1 if m > 0 else -1))
    print(f"  {name:12}{len(r):>7}{sum(x > 0 for x in r) / len(r):>10.0%}{statistics.mean(r):>+32.3f}%{t(r):>7.2f}")

print("\n5. Day of the week (open to close)")
for i, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri"]):
    r = [x for x, d in zip(day_r, days) if date.fromisoformat(d["day"]).weekday() == i]
    print(f"  {name}{len(r):>6} days  avg {statistics.mean(r):+.3f}%  t {t(r):+.2f}  size {statistics.mean(abs(x) for x in r):.3f}%")
