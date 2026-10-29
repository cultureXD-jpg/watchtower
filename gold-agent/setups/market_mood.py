# GOLD AGENT: market cycle check. How has gold behaved in each mood (rules in mood.py)?
#
# Usage: market_mood.py            -> refresh daily history and print the summary
#        market_mood.py --today    -> just print today's mood
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from mood import MOODS, download, label

rows = label(download())
today = rows[-1]
print(f"Today {today['date']}: {today['mood']}, {today['off_high']:+.1%} from record, "
      f"{today['c'] / today['sma'] - 1:+.1%} vs 200-day average")
if "--today" in sys.argv:
    sys.exit()


def fwd(i, n):
    return rows[i + n]["c"] / rows[i]["c"] - 1 if i + n < len(rows) else None


print(f"History: {rows[0]['date']} to {today['date']}, {len(rows)} days\n")
print(f"{'Mood':8}{'days':>6}{'share':>7}{'day range':>11}{'big days':>10}"
      f"{'next month':>12}{'up after':>10}{'next 3 mo':>11}")
for mood in MOODS:
    idx = [i for i, r in enumerate(rows) if r["mood"] == mood]
    rng = [(rows[i]["h"] - rows[i]["l"]) / rows[i]["o"] for i in idx]
    big = [abs(rows[i]["c"] - rows[i]["o"]) / rows[i]["o"] >= 0.01 for i in idx]
    m1 = [x for x in (fwd(i, 21) for i in idx) if x is not None]
    m3 = [x for x in (fwd(i, 63) for i in idx) if x is not None]
    print(f"{mood:8}{len(idx):>6}{len(idx) / sum(r['mood'] is not None for r in rows):>7.0%}"
          f"{statistics.mean(rng):>10.2%}{sum(big) / len(big):>10.0%}"
          f"{statistics.mean(m1):>+11.1%}{sum(x > 0 for x in m1) / len(m1):>10.0%}"
          f"{statistics.mean(m3):>+10.1%}")

# Hot stretches: runs of Hot days (gaps of up to 10 non-Hot days count as the same stretch)
print("\nHot stretches (near-record runs), and what followed:")
runs, start, last = [], None, None
for i, r in enumerate(rows):
    if r["mood"] == "Hot":
        if start is None or i - last > 10:
            if start is not None:
                runs.append((start, last))
            start = i
        last = i
runs.append((start, last))
for s, e in runs:
    if e - s < 40:
        continue
    low = min(rows[j]["c"] for j in range(e, min(e + 252, len(rows))))
    print(f"  {rows[s]['date']} to {rows[e]['date']}  {e - s + 1:>4} days  "
          f"gain {rows[e]['c'] / rows[s]['c'] - 1:+.0%}  "
          f"worst drop in the year after {low / rows[e]['c'] - 1:+.0%}")
