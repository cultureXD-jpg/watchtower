# GOLD AGENT: overnight hold test on GLD, compared with simply holding gold.
#
# Rules (fixed before the first run):
#   - Overnight: buy at each day's last 1-minute close, sell at the next day's first 1-minute open.
#     Every night, no stop (the market is closed). Costs $0.02/share per night; also shown at $0.05.
#   - Daytime: buy at each open, sell at that day's close, same costs.
#   - Hold: buy at the first open, sell at the last close, one $0.02 cost.
#   - Measuring period only (Jan 2016 - Jun 2026). Moods use the previous day's label.
#   - Pass: beats Hold on return per unit of risk, t-value 2+, not reliant on one mood, and then
#     still positive on the unseen months. Unseen results are not shown here.
import statistics

from common import MOODS, SPLIT, load_days, moods


def stats(name, rets):
    eq = peak = 1.0
    worst = 0.0
    for r in rets:
        eq *= 1 + r
        peak = max(peak, eq)
        worst = min(worst, eq / peak - 1)
    years = len(rets) / 252
    sd = statistics.stdev(rets)
    t = statistics.mean(rets) / (sd / len(rets) ** 0.5)
    print(f"  {name:22}{eq - 1:>+9.0%}{eq ** (1 / years) - 1:>+9.1%}{worst:>9.0%}"
          f"{sd * 252 ** 0.5:>9.1%}{statistics.mean(rets) * 252 / (sd * 252 ** 0.5):>9.2f}{t:>7.2f}")


mood_by_day = moods()
dates = sorted(mood_by_day)
prev_mood = {d: mood_by_day[dates[i - 1]] for i, d in enumerate(dates) if i}
days = [(d, b[0]["o"], b[-1]["c"]) for d, b in load_days() if d < SPLIT]
print(f"{len(days)} days, {days[0][0]} to {days[-1][0]}\n")

night, night5, daytime, hold, tagged = [], [], [], [], []
for (_, _, pc), (d, o, c) in zip(days, days[1:]):
    night.append((o - 0.02 - pc) / pc)
    night5.append((o - 0.05 - pc) / pc)
    daytime.append((c - 0.02 - o) / o)
    hold.append(c / pc - 1)
    tagged.append((d, prev_mood.get(d), night[-1], hold[-1]))

print(f"  {'':22}{'total':>9}{'a year':>9}{'worst':>9}{'swing':>9}{'ret/risk':>9}{'t':>7}")
stats("Hold gold", hold)
stats("Overnight, $0.02", night)
stats("Overnight, $0.05", night5)
stats("Daytime, $0.02", daytime)

print("\nBy mood (per day, after $0.02):")
for m in MOODS:
    n = [x[2] for x in tagged if x[1] == m]
    h = [x[3] for x in tagged if x[1] == m]
    t = statistics.mean(n) / (statistics.stdev(n) / len(n) ** 0.5)
    print(f"  {m:8}{len(n):>5} nights  overnight {statistics.mean(n):+.3f}% t {t:+.2f}".replace("%", "") .replace(f"{statistics.mean(n):+.3f}", f"{statistics.mean(n) * 100:+.3f}%")
          + f"  hold {statistics.mean(h) * 100:+.3f}%")

print("\nBy year (compounded):")
print(f"  {'year':6}{'overnight':>11}{'hold':>9}")
for y in sorted({x[0][:4] for x in tagged}):
    n = h = 1.0
    for x in tagged:
        if x[0][:4] == y:
            n *= 1 + x[2]
            h *= 1 + x[3]
    print(f"  {y:6}{n - 1:>+11.1%}{h - 1:>+9.1%}")
