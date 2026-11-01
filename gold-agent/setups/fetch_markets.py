# GOLD AGENT: download split-adjusted 1-minute bars for other markets since 2016, month by month,
# to GOLD_HOME/markets/SYMBOL_YYYY-MM-DD.csv, in the same format as the GLD files.
# Usage: fetch_markets.py SPY QQQ IWM
import csv
import os
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetCalendarRequest
from config import API_KEY, SECRET_KEY, GOLD_HOME

NY = ZoneInfo("America/New_York")
FOLDER = os.path.join(GOLD_HOME, "markets")
os.makedirs(FOLDER, exist_ok=True)
client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
trading = TradingClient(API_KEY, SECRET_KEY, paper=True)
today = datetime.now(NY).date()

for symbol in sys.argv[1:]:
    y, m, saved = 2016, 1, 0
    while date(y, m, 1) <= today:
        ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
        end = min(date(ny, nm, 1), today)
        cal = trading.get_calendar(GetCalendarRequest(start=date(y, m, 1), end=end))
        bars = client.get_stock_bars(StockBarsRequest(
            symbol_or_symbols=symbol, timeframe=TimeFrame.Minute, feed=DataFeed.SIP, adjustment=Adjustment.SPLIT,
            start=datetime(y, m, 1, tzinfo=NY), end=datetime(end.year, end.month, end.day, tzinfo=NY))).data.get(symbol, [])
        sessions = {c.date: (c.open.replace(tzinfo=NY), c.close.replace(tzinfo=NY)) for c in cal}
        by_day = {}
        for b in bars:
            t = b.timestamp.astimezone(NY)
            s = sessions.get(t.date())
            if s and s[0] <= t < s[1]:
                by_day.setdefault(t.date(), []).append((t, b))
        for d, rows in by_day.items():
            with open(os.path.join(FOLDER, f"{symbol}_{d}.csv"), "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["Time (ET)", "Open", "High", "Low", "Close", "Volume", "Trades", "VWAP"])
                for t, b in rows:
                    w.writerow([t.strftime("%Y-%m-%d %H:%M"), b.open, b.high, b.low, b.close,
                                int(b.volume), int(b.trade_count or 0), round(b.vwap, 4) if b.vwap else ""])
        saved += len(by_day)
        y, m = ny, nm
    print(symbol, saved, "days", flush=True)
