# GOLD AGENT: swing setups on daily GLD bars, long and short, held days to weeks.
#
# Rules (fixed Nov 15, 2026, before the first run):
#   - Signals use the day's close; entries fill at the next open. One position at a time per setup.
#   - Each day: a gap past the stop or target fills at the open; otherwise stop, then target, are
#     checked against the day's low/high (both touched = stop); then the setup's exit runs at the close.
#   - ATR = average true range over 14 days. Costs $0.02/share round trip. Results in R (1R = entry to stop).
#   - Measuring period only: warm-up of 200 days, then to Jun 30, 2026. Anything still open is closed
#     at the last measuring close. Jul - Oct 2026 is never read.
#   - Pass: t-value 3+ and positive in both halves (split Apr 1, 2021).
#   - Also shown: being fully in the position (long or short, cash when flat, cash earns nothing)
#     vs simply holding GLD over the same days, as yearly return and return/risk.
#
# Setups:
#   1 Pullback in trend: long if close > 200-day avg and 2-day RSI < 10; short if close < 200-day avg
#     and RSI > 90. Stop 2 ATR. Exit when the close crosses the 5-day avg, or after 10 days.
#   2 20-day breakout: long on a close above the prior 20 days' high, short below their low.
#     Stop 2 ATR. Exit on a close beyond the prior 10 days' opposite extreme, or after 20 days.
#   3 Quiet squeeze breakout: 10-day ATR under 0.75x the 60-day ATR (as of the day before); then a close
#     above the prior 10 days' high (long) or below their low (short). Stop at the other side of that
#     10-day box. Target 2R. Max 10 days.
#   4 Fade a big day: close-to-close move over 2 ATR down -> long, up -> short. Stop 1.5 ATR. Target 1R. Max 3 days.
#   5 10/30-day average cross: long when the 10-day crosses above the 30-day, short when below.
#     Stop 3 ATR. Exit on the opposite cross.
#   6 1-month momentum, weekly: at each week's last close, long if the close is above the close 21 days
#     earlier, else short. Stop 3 ATR. Exit at the next week's last close.
#   7 NR7 breakout: yesterday had the narrowest range of the last 7 days; today closes above its high
#     (long) or below its low (short). Stop at the other side of that day. Target 2R. Max 5 days.
#   8 Turn of month (long only): buy the open of the month's last trading day, sell the close of the
#     3rd trading day of the next month. Stop 3 ATR.
import os
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from common import COST, MID, SPLIT
from mood import load

rows = [r for r in load() if r["date"] < SPLIT]
N, WARM = len(rows), 200
O = [r["o"] for r in rows]
H = [r["h"] for r in rows]
L = [r["l"] for r in rows]
C = [r["c"] for r in rows]
D = [r["date"] for r in rows]


def sma(i, n):
    return sum(C[i - n + 1:i + 1]) / n


def atr(i, n=14):
    return sum(max(H[j], C[j - 1]) - min(L[j], C[j - 1]) for j in range(i - n + 1, i + 1)) / n


def rsi2(i):
    ch = [C[j] - C[j - 1] for j in (i - 1, i)]
    up, dn = sum(x for x in ch if x > 0), -sum(x for x in ch if x < 0)
    return 100 if dn == 0 else 100 - 100 / (1 + up / dn)


def week_end(i):
    return i + 1 < N and rows[i + 1]["date"] and _wk(i) != _wk(i + 1)


def _wk(i):
    import datetime
    return datetime.date.fromisoformat(D[i]).isocalendar()[:2]


# Each setup: signal(i) -> None or (side, stop_distance or None, stop_price or None, target_r or None, max_days)
# and exit(j, side, start) -> True to leave at the close of day j.
def s_pullback(i):
    if C[i] > sma(i, 200) and rsi2(i) < 10:
        return 1, 2 * atr(i), None, None, 10
    if C[i] < sma(i, 200) and rsi2(i) > 90:
        return -1, 2 * atr(i), None, None, 10


def x_pullback(j, side, start):
    return (C[j] - sma(j, 5)) * side > 0


def s_breakout(i):
    if C[i] > max(H[i - 20:i]):
        return 1, 2 * atr(i), None, None, 20
    if C[i] < min(L[i - 20:i]):
        return -1, 2 * atr(i), None, None, 20


def x_breakout(j, side, start):
    return C[j] < min(L[j - 10:j]) if side == 1 else C[j] > max(H[j - 10:j])


def s_squeeze(i):
    if atr(i - 1, 10) >= 0.75 * atr(i - 1, 60):
        return None
    hi, lo = max(H[i - 10:i]), min(L[i - 10:i])
    if C[i] > hi:
        return 1, None, lo, 2, 10
    if C[i] < lo:
        return -1, None, hi, 2, 10


def s_fade(i):
    move = C[i] - C[i - 1]
    if move < -2 * atr(i - 1):
        return 1, 1.5 * atr(i), None, 1, 3
    if move > 2 * atr(i - 1):
        return -1, 1.5 * atr(i), None, 1, 3


def s_cross(i):
    a, b = sma(i, 10) - sma(i, 30), sma(i - 1, 10) - sma(i - 1, 30)
    if a > 0 >= b:
        return 1, 3 * atr(i), None, None, 10 ** 6
    if a < 0 <= b:
        return -1, 3 * atr(i), None, None, 10 ** 6


def x_cross(j, side, start):
    return (sma(j, 10) - sma(j, 30)) * side < 0


def s_momentum(i):
    if week_end(i):
        return (1 if C[i] > C[i - 21] else -1), 3 * atr(i), None, None, 10 ** 6


def x_momentum(j, side, start):
    return j > start and week_end(j)


def s_nr7(i):
    k = i - 1
    if H[k] - L[k] >= min(H[m] - L[m] for m in range(k - 6, k)):
        return None
    if C[i] > H[k]:
        return 1, None, L[k], 2, 5
    if C[i] < L[k]:
        return -1, None, H[k], 2, 5


def s_month(i):
    if i + 2 < N and D[i + 1][:7] == D[i][:7] and D[i + 2][:7] != D[i][:7]:
        return 1, 3 * atr(i), None, None, 10 ** 6


def x_month(j, side, start):
    return D[j][:7] != D[start][:7] and sum(D[m][:7] == D[j][:7] for m in range(start, j + 1)) >= 3


SETUPS = [
    ("Pullback in trend", s_pullback, x_pullback),
    ("20-day breakout", s_breakout, x_breakout),
    ("Quiet squeeze breakout", s_squeeze, None),
    ("Fade a big day", s_fade, None),
    ("10/30 average cross", s_cross, x_cross),
    ("1-month momentum, weekly", s_momentum, x_momentum),
    ("NR7 breakout", s_nr7, None),
    ("Turn of month (long)", s_month, x_month),
]


def backtest(signal, exit_fn):
    trades, daily, pos, pending = [], [0.0] * N, None, None
    for i in range(WARM, N):
        if pending:
            side, dist, stop, tr, mx = pending
            pending = None
            entry = O[i]
            stop = entry - side * dist if stop is None else stop
            risk = (entry - stop) * side
            if risk > 0:
                pos = {"side": side, "entry": entry, "stop": stop, "risk": risk, "start": i, "mx": mx,
                       "target": None if tr is None else entry + side * tr * risk}
                daily[i] -= COST / entry
        if pos:
            s, st, tg = pos["side"], pos["stop"], pos["target"]
            ref = pos["entry"] if pos["start"] == i else C[i - 1]
            px = None
            if pos["start"] != i and (O[i] - st) * s <= 0:
                px, why = O[i], "stop"
            elif pos["start"] != i and tg is not None and (O[i] - tg) * s >= 0:
                px, why = O[i], "target"
            elif (L[i] <= st) if s == 1 else (H[i] >= st):
                px, why = st, "stop"
            elif tg is not None and ((H[i] >= tg) if s == 1 else (L[i] <= tg)):
                px, why = tg, "target"
            elif ((exit_fn and exit_fn(i, s, pos["start"])) or i - pos["start"] + 1 >= pos["mx"]
                  or i == N - 1):
                px, why = C[i], "close"
            daily[i] += s * ((px if px is not None else C[i]) - ref) / ref
            if px is not None:
                trades.append({"side": s, "day": D[pos["start"]], "why": why,
                               "r": ((px - pos["entry"]) * s - COST) / pos["risk"]})
                pos = None
        if not pos and i < N - 1:
            pending = signal(i)
    return trades, daily[WARM:]


def yearly(rets):
    m, sd = statistics.mean(rets), statistics.stdev(rets)
    grow, peak, dd = 1.0, 1.0, 0.0
    for r in rets:
        grow *= 1 + r
        peak = max(peak, grow)
        dd = min(dd, grow / peak - 1)
    return grow ** (252 / len(rets)) - 1, (m / sd) * 252 ** 0.5 if sd else 0, dd


days = D[WARM:]
half = days.index(next(d for d in days if d >= MID))
hold = [C[i] / C[i - 1] - 1 for i in range(WARM, N)]
hy, hr, hd = yearly(hold)
_, hr1, _ = yearly(hold[:half])
_, hr2, _ = yearly(hold[half:])
print(f"Measuring {days[0]} to {days[-1]}. Hold GLD: {hy:+.1%} a year, return/risk {hr:.2f} "
      f"(halves {hr1:.2f} / {hr2:.2f}), worst drop {hd:.0%}\n")
print(f"{'Setup':26}{'trades':>7}{'avg R':>8}{'t':>7}{'half 1':>8}{'half 2':>8}{'long R':>12}{'short R':>13}"
      f"{'yearly':>8}{'ret/risk':>9}{'halves':>12}{'worst':>7}  pass")
for name, sig, ex in SETUPS:
    trades, daily = backtest(sig, ex)
    rs = [t["r"] for t in trades]
    t = statistics.mean(rs) / (statistics.stdev(rs) / len(rs) ** 0.5)
    h1 = statistics.mean([x["r"] for x in trades if x["day"] < MID])
    h2 = statistics.mean([x["r"] for x in trades if x["day"] >= MID])
    side = {}
    for s in (1, -1):
        v = [x["r"] for x in trades if x["side"] == s]
        side[s] = f"{len(v)}:{statistics.mean(v):+.2f}" if v else "-"
    y, rr, dd = yearly(daily)
    _, r1, _ = yearly(daily[:half])
    _, r2, _ = yearly(daily[half:])
    ok = "PASS" if t >= 3 and h1 > 0 and h2 > 0 else "no"
    print(f"{name:26}{len(rs):>7}{statistics.mean(rs):>+8.3f}{t:>7.2f}{h1:>+8.3f}{h2:>+8.3f}"
          f"{side[1]:>12}{side[-1]:>13}{y:>+8.1%}{rr:>9.2f}{r1:>6.2f}/{r2:<5.2f}{dd:>7.0%}  {ok}")
