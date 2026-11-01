# GOLD AGENT: longer holds on daily GLD bars, compared with simply holding gold.
#
# Rules (fixed before the first run):
#   - Signals use the day's close. Trades happen at the next open. Position returns run open to open.
#   - Costs $0.02/share per round trip ($0.01 each way). Cash earns nothing, which slightly understates rules that sit in cash.
#   - All rules and Hold start on the same day, after 263 days of warm-up.
#   - Measuring period only (to Jun 2026). Also split into two halves.
#   - Pass: higher return/risk than Hold in both halves and t-value 2+.
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import SPLIT
from mood import label, load

rows = [r for r in label(load()) if r["date"] < SPLIT]
closes = [r["c"] for r in rows]
WARM = 263


def sma(i, n):
    return statistics.mean(closes[i - n + 1:i + 1])


def stateful(step):
    """step(i, position) returns the position to hold from the next open."""
    pos, out = 0, {}
    for i in range(WARM, len(rows)):
        pos = step(i, pos)
        out[i] = pos
    return out


def pullback(i, pos):
    if pos:
        return 0 if closes[i] > sma(i, 5) else 1
    return 1 if closes[i] > sma(i, 200) and closes[i] == min(closes[i - 4:i + 1]) else 0


def donchian(i, pos):
    if pos:
        return 0 if closes[i] <= min(closes[i - 19:i + 1]) else 1
    return 1 if closes[i] >= max(closes[i - 49:i + 1]) else 0


def momentum(i, pos):
    if rows[i]["date"][:7] != rows[i + 1 if i + 1 < len(rows) else i]["date"][:7] or i == WARM:
        return 1 if closes[i] > closes[i - 252] else 0
    return pos


def after_move(sign):
    left = [0]

    def step(i, pos):
        if (closes[i] / closes[i - 1] - 1) * sign >= 0.02:
            left[0] = 5
        elif left[0]:
            left[0] -= 1
        return 1 if left[0] else 0
    return step


RULES = {
    "Hold gold": lambda i, p: 1,
    "Only when Hot": lambda i, p: 1 if rows[i]["mood"] == "Hot" else 0,
    "Except when Flat": lambda i, p: 0 if rows[i]["mood"] == "Flat" else 1,
    "Above 200-day avg": lambda i, p: 1 if closes[i] > sma(i, 200) else 0,
    "50-day above 200-day": lambda i, p: 1 if sma(i, 50) > sma(i, 200) else 0,
    "50-day high, 20-day low exit": donchian,
    "12-month momentum, monthly": momentum,
    "200-day avg, long and short": lambda i, p: 1 if closes[i] > sma(i, 200) else -1,
    "Buy 5-day low in uptrend": pullback,
    "5 days after 2%+ drop": after_move(-1),
    "5 days after 2%+ rise": after_move(1),
}


def evaluate(pos):
    rets, trades = [], 0
    for i in range(WARM, len(rows) - 2):
        p, prior = pos[i], pos.get(i - 1, 0)
        entry, nxt = rows[i + 1]["o"], rows[i + 2]["o"]
        change = abs(p - prior)
        trades += change
        rets.append((rows[i + 1]["date"], p * (nxt / entry - 1) - change * 0.01 / entry, p != 0))
    return rets, trades


def ratio(r):
    return statistics.mean(r) * 252 ** 0.5 / statistics.stdev(r) if statistics.stdev(r) else 0


mid = rows[(WARM + len(rows)) // 2]["date"]
print(f"{rows[WARM + 1]['date']} to {rows[-1]['date']}, halves split at {mid}\n")
print(f"  {'':31}{'total':>8}{'a year':>8}{'worst':>7}{'ret/risk':>9}{'half 1':>8}{'half 2':>8}{'t':>7}{'in mkt':>8}{'sides':>7}")
for name, rule in RULES.items():
    rets, trades = evaluate(stateful(rule))
    r = [x[1] for x in rets]
    eq = peak = 1.0
    worst = 0.0
    for x in r:
        eq *= 1 + x
        peak = max(peak, eq)
        worst = min(worst, eq / peak - 1)
    a = [x[1] for x in rets if x[0] < mid]
    b = [x[1] for x in rets if x[0] >= mid]
    print(f"  {name:31}{eq - 1:>+8.0%}{eq ** (252 / len(r)) - 1:>+8.1%}{worst:>7.0%}{ratio(r):>9.2f}{ratio(a):>8.2f}{ratio(b):>8.2f}"
          f"{statistics.mean(r) / (statistics.stdev(r) / len(r) ** 0.5):>7.2f}{sum(x[2] for x in rets) / len(rets):>8.0%}{trades:>7}")
