# GOLD AGENT: run every day-trading setup on every market, with identical rules (no tuning per market).
# Measuring period only. Pass bar: t-value 3.5+ (this batch has 63 tests, so a stricter bar than 2)
# and positive in both halves of the period.
import csv
import os
import re
import subprocess
import sys

MARKETS = ["SPY", "QQQ", "IWM", "EEM", "XLF", "XLE", "TLT", "SLV", "GDX"]
SETUPS = ["orb", "vwap_pullback", "orb_fade", "trend_day", "last_hour", "quiet_breakout", "gap"]
HOME = os.environ.get("GOLD_HOME", "/var/lib/gold-agent")
here = os.path.dirname(os.path.abspath(__file__))
results = []
for market in MARKETS:
    for setup in SETUPS:
        out = subprocess.run([sys.executable, os.path.join(here, f"backtest_{setup}.py")], capture_output=True, text=True,
                             env=dict(os.environ, GOLD_SYMBOL=market)).stdout
        m = re.search(r"\): (\d+) trades \| win rate (\d+)% \| average ([+-][\d.]+)R .*worst drop (-?[\d.]+)R", out)
        tv = re.search(r"t-value (-?[\d.]+)", out)
        h = re.search(r"halves ([+-][\d.]+)R ([+-][\d.]+)R", out)
        if not (m and tv and h):
            print("NO RESULT", market, setup, flush=True)
            continue
        row = [market, setup, int(m[1]), int(m[2]), float(m[3]), float(m[4]), float(tv[1]), float(h[1]), float(h[2])]
        results.append(row)
        print(*row, flush=True)
with open(os.path.join(HOME, "markets_results.csv"), "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["market", "setup", "trades", "win_pct", "avg_r", "worst_drop_r", "t", "half1_r", "half2_r"])
    w.writerows(results)
print("\nPASSED:", [r[:2] for r in results if r[6] >= 3.5 and r[7] > 0 and r[8] > 0])
print("Positive average:", sum(r[4] > 0 for r in results), "of", len(results))
print("t 2 or more:", [(r[0], r[1], r[6]) for r in results if r[6] >= 2])
print("Top 8 by t:")
for r in sorted(results, key=lambda r: -r[6])[:8]:
    print(" ", *r)
