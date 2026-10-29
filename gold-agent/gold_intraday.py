# GOLD AGENT: intraday recorder. After the close, saves every 1-minute GLD bar of the day
# to /var/lib/gold-agent/intraday/GLD_YYYY-MM-DD.csv (one file per market day).
# Usage: gold_intraday.py              -> today (Pacific time)
#        gold_intraday.py 2026-10-21   -> that day (to fill in past days)
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.data.enums import DataFeed
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetCalendarRequest
from datetime import datetime, date
from zoneinfo import ZoneInfo
import csv
import os
import sys
from config import API_KEY, SECRET_KEY, GOLD_HOME

TZ = ZoneInfo("America/Los_Angeles")
NY = ZoneInfo("America/New_York")
SYMBOL = "GLD"

day = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.now(TZ).date()

trading = TradingClient(API_KEY, SECRET_KEY, paper=True)
calendar = trading.get_calendar(GetCalendarRequest(start=day, end=day))
if not calendar or calendar[0].date != day:
    print(day, "- market closed (weekend or holiday), nothing to record.")
    sys.exit()

# regular session only; the calendar knows the early-close days
opens = calendar[0].open.replace(tzinfo=NY)
closes = calendar[0].close.replace(tzinfo=NY)

# SIP = every US exchange; the free plan allows it once the bars are 15+ minutes old
client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
bars = client.get_stock_bars(StockBarsRequest(
    symbol_or_symbols=SYMBOL, timeframe=TimeFrame.Minute, start=opens, end=closes, feed=DataFeed.SIP
)).data.get(SYMBOL, [])
bars = [b for b in bars if opens <= b.timestamp < closes]
if not bars:
    raise SystemExit(f"{day}: Alpaca returned no {SYMBOL} minute bars - will retry.")

folder = os.path.join(GOLD_HOME, "intraday")
os.makedirs(folder, exist_ok=True)
path = os.path.join(folder, f"{SYMBOL}_{day}.csv")
tmp = path + ".tmp"
with open(tmp, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["Time (ET)", "Open", "High", "Low", "Close", "Volume", "Trades", "VWAP"])
    for b in bars:
        w.writerow([b.timestamp.astimezone(NY).strftime("%Y-%m-%d %H:%M"), b.open, b.high, b.low, b.close,
                    int(b.volume), int(b.trade_count or 0), round(b.vwap, 4) if b.vwap else ""])
os.replace(tmp, path)

expected = int((closes - opens).total_seconds() // 60)
print(f"Wrote {path}: {len(bars)} of {expected} minutes, open {bars[0].open} close {bars[-1].close}")
