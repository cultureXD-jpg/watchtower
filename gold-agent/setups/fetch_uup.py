# GOLD AGENT: one-off download of 1-minute UUP (dollar fund) bars since 2016, month by month,
# to GOLD_HOME/uup/UUP_YYYY-MM-DD.csv (regular session only). Skips months already saved.
import csv
import os
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from alpaca.data.enums import DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetCalendarRequest
from config import API_KEY, SECRET_KEY, GOLD_HOME

NY = ZoneInfo("America/New_York")
FOLDER = os.path.join(GOLD_HOME, "uup")
os.makedirs(FOLDER, exist_ok=True)
client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
trading = TradingClient(API_KEY, SECRET_KEY, paper=True)
today = datetime.now(NY).date()

y, m = 2016, 1
while date(y, m, 1) <= today:
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    end = min(date(ny, nm, 1), today)
    cal = trading.get_calendar(GetCalendarRequest(start=date(y, m, 1), end=end))
    bars = client.get_stock_bars(StockBarsRequest(
        symbol_or_symbols="UUP", timeframe=TimeFrame.Minute, feed=DataFeed.SIP,
        start=datetime(y, m, 1, tzinfo=NY), end=datetime(end.year, end.month, end.day, tzinfo=NY))).data.get("UUP", [])
    sessions = {c.date: (c.open.replace(tzinfo=NY), c.close.replace(tzinfo=NY)) for c in cal}
    by_day = {}
    for b in bars:
        t = b.timestamp.astimezone(NY)
        s = sessions.get(t.date())
        if s and s[0] <= t < s[1]:
            by_day.setdefault(t.date(), []).append((t.strftime("%H:%M"), b.open, b.close))
    for d, rows in by_day.items():
        with open(os.path.join(FOLDER, f"UUP_{d}.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["t", "o", "c"])
            w.writerows(rows)
    print(y, m, len(by_day), "days", flush=True)
    y, m = ny, nm
