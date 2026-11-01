# GOLD AGENT: download GLD headlines (Alpaca), fear gauges (FRED) and big-trader positioning (CFTC)
# to GOLD_HOME/sentiment/.
import csv
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from config import API_KEY, SECRET_KEY, FRED_KEY, GOLD_HOME

FOLDER = os.path.join(GOLD_HOME, "sentiment")
os.makedirs(FOLDER, exist_ok=True)
NY = ZoneInfo("America/New_York")


def save(name, header, rows):
    with open(os.path.join(FOLDER, name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(name, len(rows), "rows", rows[0][0], "to", rows[-1][0], flush=True)


rows, token = [], None
while True:
    params = {"symbols": "GLD", "sort": "asc", "limit": 50, "start": "2015-06-01T00:00:00Z"}
    if token:
        params["page_token"] = token
    r = requests.get("https://data.alpaca.markets/v1beta1/news", timeout=60, params=params,
                     headers={"APCA-API-KEY-ID": API_KEY, "APCA-API-SECRET-KEY": SECRET_KEY})
    r.raise_for_status()
    body = r.json()
    for n in body["news"]:
        t = datetime.fromisoformat(n["created_at"].replace("Z", "+00:00")).astimezone(NY)
        rows.append((t.strftime("%Y-%m-%d %H:%M"), n["headline"]))
    token = body.get("next_page_token")
    if not token:
        break
save("news_gld.csv", ["time_et", "headline"], rows)

for series in ("GVZCLS", "VIXCLS"):
    obs = requests.get("https://api.stlouisfed.org/fred/series/observations", timeout=60, params={
        "series_id": series, "api_key": FRED_KEY, "file_type": "json", "observation_start": "2015-01-01"}).json()["observations"]
    save(f"{series}.csv", ["date", "value"], [(o["date"], o["value"]) for o in obs if o["value"] != "."])

cftc = requests.get("https://publicreporting.cftc.gov/resource/6dca-aqww.json", timeout=60, params={
    "$where": "cftc_contract_market_code='088691' AND report_date_as_yyyy_mm_dd >= '2012-01-01'",
    "$order": "report_date_as_yyyy_mm_dd asc", "$limit": 5000,
    "$select": "report_date_as_yyyy_mm_dd,noncomm_positions_long_all,noncomm_positions_short_all,open_interest_all"}).json()
save("cftc_gold.csv", ["date", "long", "short", "open_interest"],
     [(c["report_date_as_yyyy_mm_dd"][:10], c["noncomm_positions_long_all"], c["noncomm_positions_short_all"], c["open_interest_all"]) for c in cftc])
