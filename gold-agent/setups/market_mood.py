# GOLD AGENT: market cycle check. What "mood" is gold in, and how has it behaved in each?
#
# Daily GLD bars (split/dividend adjusted) from Alpaca, saved to GOLD_HOME/gld_daily.csv.
# Moods (rules fixed before the first run), checked in this order:
#   Hot     = close within 5% of the highest close so far (near a record)
#   Falling = 200-day average down more than 2% over the last 3 months
#   Flat    = 200-day average moved less than 2% either way over the last 3 months
#   Cooling = everything else (uptrend intact, but 5%+ below the record)
#
# Usage: market_mood.py            -> download/update history and print the summary
#        market_mood.py --today    -> just print today's mood
import csv
import os
import statistics
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from config import API_KEY, SECRET_KEY
from common import GOLD_HOME

OUT = os.path.join(GOLD_HOME, "gld_daily.csv")
NEAR_HIGH, SLOPE, LOOKBACK = 0.05, 0.02, 63


def download():
    client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
    bars = client.get_stock_bars(StockBarsRequest(
        symbol_or_symbols="GLD", timeframe=TimeFrame.Day, start=datetime(2004, 1, 1),
        adjustment=Adjustment.ALL, feed=DataFeed.SIP)).data["GLD"]
    rows = [{"date": b.timestamp.strftime("%Y-%m-%d"), "o": b.open, "h": b.high,
             "l": b.low, "c": b.close} for b in bars]
    with open(OUT + ".tmp", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "o", "h", "l", "c"])
        w.writeheader()
        w.writerows(rows)
    os.replace(OUT + ".tmp", OUT)
    return rows


def label(rows):
    peak, closes = 0, []
    for r in rows:
        closes.append(r["c"])
        peak = max(peak, r["c"])
        r["off_high"] = r["c"] / peak - 1
        r["sma"] = statistics.mean(closes[-200:]) if len(closes) >= 200 else None
    for i, r in enumerate(rows):
        old = rows[i - LOOKBACK]["sma"] if i >= LOOKBACK else None
        if r["sma"] is None or old is None:
            r["mood"] = None
            continue
        slope = r["sma"] / old - 1
        r["mood"] = ("Hot" if r["off_high"] >= -NEAR_HIGH else
                     "Falling" if slope < -SLOPE else
                     "Flat" if abs(slope) <= SLOPE else "Cooling")
    return rows


def fwd(rows, i, n):
    return rows[i + n]["c"] / rows[i]["c"] - 1 if i + n < len(rows) else None


rows = label(download())
today = rows[-1]
print(f"Today {today['date']}: {today['mood']}, {today['off_high']:+.1%} from record, "
      f"{today['c'] / today['sma'] - 1:+.1%} vs 200-day average")
if "--today" in sys.argv:
    sys.exit()

print(f"History: {rows[0]['date']} to {today['date']}, {len(rows)} days\n")
print(f"{'Mood':8}{'days':>6}{'share':>7}{'day range':>11}{'big days':>10}"
      f"{'next month':>12}{'up after':>10}{'next 3 mo':>11}")
for mood in ["Hot", "Cooling", "Flat", "Falling"]:
    idx = [i for i, r in enumerate(rows) if r["mood"] == mood]
    rng = [(rows[i]["h"] - rows[i]["l"]) / rows[i]["o"] for i in idx]
    big = [abs(rows[i]["c"] - rows[i]["o"]) / rows[i]["o"] >= 0.01 for i in idx]
    m1 = [x for x in (fwd(rows, i, 21) for i in idx) if x is not None]
    m3 = [x for x in (fwd(rows, i, 63) for i in idx) if x is not None]
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
