# GOLD AGENT: multi-market trend and rotation, compared with simply holding.
#
# Rules (fixed Nov 15, 2026, before the first run):
#   - 10 funds: GLD SPY QQQ IWM EEM XLF XLE TLT SLV GDX. Daily closes adjusted for splits and dividends.
#   - Decided at each month's last close, traded at the next day's close (one day late, so nothing
#     is used before it is known). Cash earns nothing. Costs 0.10% of the value traded.
#   - Trend each: every fund gets 10%, held only while its close is above its 200-day average.
#   - Top 3 momentum: hold the 3 funds with the best 6-month (126-day) return, a third each.
#   - Top 3 momentum, cash filter: same, but a pick with a negative 6-month return is cash instead.
#   - Benchmarks: hold SPY; hold all 10 equally (rebalanced monthly, same costs); hold GLD.
#   - Measuring period only: after a 200-day warm-up, to Jun 30, 2026. Halves split Apr 1, 2021.
#   - Pass: return/risk above both "hold SPY" and "hold all 10" in both halves.
import csv
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import GOLD_HOME, MID, SPLIT

FUNDS = ["GLD", "SPY", "QQQ", "IWM", "EEM", "XLF", "XLE", "TLT", "SLV", "GDX"]
COSTPCT, WARM = 0.001, 200
closes, dates = {}, None
for s in FUNDS:
    with open(os.path.join(GOLD_HOME, "daily", f"{s}.csv")) as f:
        rows = [r for r in csv.DictReader(f) if r["date"] < SPLIT]
    d = [r["date"] for r in rows]
    assert dates is None or d == dates, s
    dates, closes[s] = d, [float(r["c"]) for r in rows]
N = len(dates)


def month_end(i):
    return i + 1 < N and dates[i + 1][:7] != dates[i][:7]


def trend(i):
    return {s: 0.1 for s in FUNDS if closes[s][i] > statistics.mean(closes[s][i - 199:i + 1])}


def top3(cash_filter):
    def pick(i):
        mom = {s: closes[s][i] / closes[s][i - 126] - 1 for s in FUNDS}
        best = sorted(FUNDS, key=lambda s: mom[s], reverse=True)[:3]
        return {s: 1 / 3 for s in best if not cash_filter or mom[s] > 0}
    return pick


RULES = {
    "Hold SPY": lambda i: {"SPY": 1.0},
    "Hold GLD": lambda i: {"GLD": 1.0},
    "Hold all 10 equally": lambda i: {s: 0.1 for s in FUNDS},
    "Trend each (200-day)": trend,
    "Top 3 momentum": top3(False),
    "Top 3 momentum, cash filter": top3(True),
}


def run(rule):
    """Daily returns from day WARM+1 on. Weights decided at month-end close i trade at close i+1."""
    held, rets, decided = {}, [], None
    for i in range(WARM, N - 1):
        if decided is not None:                 # trade at today's close
            moves = {s: held.get(s, 0) for s in FUNDS}
            turnover = sum(abs(decided.get(s, 0) - moves[s]) for s in FUNDS)
            held, decided = decided, None
        else:
            turnover = 0
        if i == WARM or month_end(i):
            decided = rule(i)
        nxt = sum(w * (closes[s][i + 1] / closes[s][i] - 1) for s, w in held.items())
        rets.append(nxt - turnover * COSTPCT)
        # let weights drift with prices until the next trade
        total = 1 + nxt
        held = {s: w * closes[s][i + 1] / closes[s][i] / total for s, w in held.items()}
    return rets


def stats(rets):
    m, sd = statistics.mean(rets), statistics.stdev(rets)
    grow, peak, dd = 1.0, 1.0, 0.0
    for r in rets:
        grow *= 1 + r
        peak = max(peak, grow)
        dd = min(dd, grow / peak - 1)
    return grow ** (252 / len(rets)) - 1, m / sd * 252 ** 0.5, dd


days = dates[WARM + 1:]
half = days.index(next(d for d in days if d >= MID))
print(f"Measuring {days[0]} to {days[-1]}\n")
print(f"{'Rule':30}{'yearly':>8}{'ret/risk':>10}{'half 1':>8}{'half 2':>8}{'worst drop':>12}")
res = {}
for name, rule in RULES.items():
    r = run(rule)
    y, rr, dd = stats(r)
    h1, h2 = stats(r[:half])[1], stats(r[half:])[1]
    res[name] = (h1, h2)
    print(f"{name:30}{y:>+8.1%}{rr:>10.2f}{h1:>8.2f}{h2:>8.2f}{dd:>12.0%}")
print()
for name in list(RULES)[3:]:
    h1, h2 = res[name]
    ok = all(h > max(res["Hold SPY"][k], res["Hold all 10 equally"][k]) for k, h in enumerate((h1, h2)))
    print(f"{name}: {'PASS' if ok else 'no'}")
