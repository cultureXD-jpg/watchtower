# GOLD AGENT: daily bars (split and dividend adjusted) for the 10 test markets, saved to GOLD_HOME/daily.
import csv
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from config import API_KEY, SECRET_KEY, GOLD_HOME

SYMBOLS = ["GLD", "SPY", "QQQ", "IWM", "EEM", "XLF", "XLE", "TLT", "SLV", "GDX"]
OUT = os.path.join(GOLD_HOME, "daily")
os.makedirs(OUT, exist_ok=True)
client = StockHistoricalDataClient(API_KEY, SECRET_KEY)
data = client.get_stock_bars(StockBarsRequest(
    symbol_or_symbols=SYMBOLS, timeframe=TimeFrame.Day, start=datetime(2016, 1, 1),
    adjustment=Adjustment.ALL, feed=DataFeed.SIP)).data
for sym in SYMBOLS:
    with open(os.path.join(OUT, f"{sym}.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "o", "h", "l", "c"])
        for b in data[sym]:
            w.writerow([b.timestamp.strftime("%Y-%m-%d"), b.open, b.high, b.low, b.close])
    print(sym, len(data[sym]), "days")
