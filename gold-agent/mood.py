# GOLD AGENT: the market "mood" for each day, from daily GLD closes (split/dividend adjusted).
# Rules (fixed Oct 28, 2026), checked in this order:
#   Hot     = close within 5% of the highest close so far (near a record)
#   Falling = 200-day average down more than 2% over the last 3 months
#   Flat    = 200-day average moved less than 2% either way over the last 3 months
#   Cooling = everything else (uptrend intact, but 5%+ below the record)
# A day's mood uses that day's close, so it is only known after the close.
import csv
import os
import statistics
from datetime import datetime

from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from config import API_KEY, SECRET_KEY, GOLD_HOME

DAILY = os.path.join(GOLD_HOME, "gld_daily.csv")
NEAR_HIGH, SLOPE, LOOKBACK = 0.05, 0.02, 63
MOODS = ["Hot", "Cooling", "Flat", "Falling"]


def download():
    """Fetch every daily GLD bar since 2016 (Alpaca's earliest) and save gld_daily.csv."""
    client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
    bars = client.get_stock_bars(StockBarsRequest(
        symbol_or_symbols="GLD", timeframe=TimeFrame.Day, start=datetime(2004, 1, 1),
        adjustment=Adjustment.ALL, feed=DataFeed.SIP)).data["GLD"]
    rows = [{"date": b.timestamp.strftime("%Y-%m-%d"), "o": b.open, "h": b.high,
             "l": b.low, "c": b.close} for b in bars]
    with open(DAILY + ".tmp", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["date", "o", "h", "l", "c"])
        w.writeheader()
        w.writerows(rows)
    os.replace(DAILY + ".tmp", DAILY)
    return rows


def load():
    with open(DAILY) as f:
        return [{"date": r["date"], **{k: float(r[k]) for k in "ohlc"}} for r in csv.DictReader(f)]


def label(rows):
    """Add off_high, sma (200-day) and mood to each row, in place."""
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


def moods(refresh=False):
    """{date: mood} for every saved day. refresh=True downloads first."""
    rows = download() if refresh or not os.path.exists(DAILY) else load()
    return {r["date"]: r["mood"] for r in label(rows)}
