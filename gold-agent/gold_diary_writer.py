# GOLD AGENT: daily gold diary (same as the Mac version). Data lives in /var/lib/gold-agent.
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetCalendarRequest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import csv
import os
import requests
import sys
import time
from config import API_KEY, SECRET_KEY, FRED_KEY, GOLD_HOME

TZ = ZoneInfo("America/Los_Angeles")
trading = TradingClient(API_KEY, SECRET_KEY, paper=True)
today_date = datetime.now(TZ).date()
calendar = trading.get_calendar(GetCalendarRequest(start=today_date, end=today_date))
if not calendar or calendar[0].date != today_date:
    print("Market closed today (weekend or holiday) - skipping.")
    sys.exit()

client = StockHistoricalDataClient(API_KEY, SECRET_KEY)

request = StockBarsRequest(
    symbol_or_symbols=["GLD", "UUP"],
    timeframe=TimeFrame.Day,
    start=datetime.now(TZ) - timedelta(days=10)
)
bars = client.get_stock_bars(request)

gold = bars["GLD"]
dollar = bars["UUP"]

price = gold[-1].close
change = gold[-1].close - gold[-2].close
direction = "up" if change > 0 else "down"
amount = round(abs(change), 2)

dollar_change = dollar[-1].close - dollar[-2].close
dollar_direction = "up" if dollar_change > 0 else "down"

diary = os.path.join(GOLD_HOME, "gold_diary.csv")

def fred(path, params, tries=3):
    # FRED sometimes answers with an empty or HTML page instead of JSON - retry before giving up
    for attempt in range(1, tries + 1):
        try:
            r = requests.get("https://api.stlouisfed.org/fred/" + path, params=dict(params, api_key=FRED_KEY, file_type="json"), timeout=30)
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            print(f"FRED {path} attempt {attempt}/{tries} failed: {str(e).replace(FRED_KEY, '***')}")
            if attempt < tries:
                time.sleep(20 * attempt)
    return None

def last_cpi():
    # CPI only changes once a month, so the previous diary row is a safe stand-in
    if os.path.exists(diary):
        with open(diary) as f:
            for r in reversed([r for r in csv.reader(f) if r][1:]):
                if len(r) > 5 and r[5]:
                    return r[5]
    return ""

fred_data = fred("series/observations", {"series_id": "CPIAUCSL", "sort_order": "desc", "limit": 1})
if fred_data and fred_data.get("observations"):
    inflation = fred_data["observations"][0]["value"]
else:
    inflation = last_cpi()
    print("FRED CPI unavailable - reusing last diary value:", inflation)

today = datetime.now(TZ).strftime("%Y-%m-%d")
releases = {"CPI": 10, "Jobs": 50}
fed_days = ["2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09"]
happened = []
for name, rid in releases.items():
    r = fred("release/dates", {"release_id": rid, "sort_order": "desc", "limit": 5})
    if r is None:
        happened.append(name + "?")
    elif today in [d["date"] for d in r.get("release_dates", [])]:
        happened.append(name)
if today in fed_days:
    happened.append("Fed decision")
events = ", ".join(happened) if happened else "none"
now = datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S")
os.makedirs(os.path.dirname(diary), exist_ok=True)
header = ["Timestamp", "Gold Price (GLD)", "Gold Direction", "Gold Change ($)", "Dollar Direction", "Inflation (CPI)", "Events"]

rows = []
if os.path.exists(diary):
    with open(diary) as f:
        rows = [r for r in csv.reader(f) if r]
if not rows or rows[0] != header:
    rows.insert(0, header)

new_row = [now, price, direction, amount, dollar_direction, inflation, events]

if rows and rows[-1][0].startswith(today):
    rows[-1] = new_row
else:
    rows.append(new_row)

with open(diary, "w") as f:
    csv.writer(f).writerows(rows)

print("Wrote:", now, "gold", price, direction, amount, "| dollar", dollar_direction, "| inflation", inflation)
