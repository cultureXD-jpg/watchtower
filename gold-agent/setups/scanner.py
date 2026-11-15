# GOLD AGENT: pattern scanner. A model learns which intraday situations came before GLD moving up or
# down over the next hour, from 2016-2020 only, and is then checked on 2021 - Jun 2026.
#
# Rules (fixed Nov 15, 2026, before the first run):
#   - Decision points: every 15 minutes from 10:00 to 14:45 ET. Everything is measured at that minute's close.
#   - What the model sees: return over the last 15 and 60 minutes and since the open; the opening gap;
#     distance from the day's VWAP; where price sits in the day's range so far; the day's range so far
#     and its volume so far, each vs the 20-day average day; the last day's and last 5 days' return;
#     minutes since the open; the previous day's mood.
#   - What it predicts: whether the price 60 minutes later (or at the close, if sooner) is above the
#     next minute's open.
#   - Models: (1) gradient-boosted trees (200 rounds, learning rate 0.05, 15 leaves, at least 200
#     examples per leaf) and (2) logistic regression on standardized inputs.
#   - Learn on Jan 2016 - Dec 2020. Test on Jan 2021 - Jun 2026. Jul - Oct 2026 is never read.
#   - Trading in the test years: buy if the chance of up is 55%+, short if 45% or less; fill at the
#     next minute's open, exit 60 minutes later or at the close. One trade at a time. $0.02/share.
#   - Pass: t-value 3+, positive in both halves of the test years (split Oct 1, 2023), and both the
#     buys and the shorts positive on their own (so gold's uptrend can't carry it).
import os
import statistics
import sys

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import COST, SPLIT, load_days
from mood import MOODS, moods

TRAIN_END, TEST_MID, HOLD = "2021-01-01", "2023-10-01", 60
TIMES = [f"{h:02d}:{m:02d}" for h in range(10, 15) for m in (0, 15, 30, 45)]
NAMES = ["r15", "r60", "since open", "gap", "vs VWAP", "place in range", "range vs avg", "volume vs avg",
         "last day", "last 5 days", "minutes in"] + [f"mood {m}" for m in MOODS]

mood_by_day = moods()
mdays = sorted(mood_by_day)
prev_mood = {d: mood_by_day[mdays[i - 1]] for i, d in enumerate(mdays) if i}
X, y, info = [], [], []
closes, ranges, vols = [], [], []
for day, bars in load_days():
    if day >= SPLIT:
        break
    if len(closes) >= 20:
        c = [b["c"] for b in bars]
        hi = lo = None
        pv = vol = 0.0
        avg_range, avg_vol = statistics.mean(ranges[-20:]), statistics.mean(vols[-20:])
        want = set(TIMES)
        for i, b in enumerate(bars):
            hi = b["h"] if hi is None else max(hi, b["h"])
            lo = b["l"] if lo is None else min(lo, b["l"])
            pv += b["vwap"] * b["v"]
            vol += b["v"]
            t = b["t"][:5]
            if t not in want or i + 1 >= len(bars):
                continue
            j = min(i + HOLD, len(bars) - 1)
            entry, out = bars[i + 1]["o"], c[j]
            m = prev_mood.get(day)
            X.append([c[i] / c[max(0, i - 15)] - 1, c[i] / c[max(0, i - 60)] - 1, c[i] / bars[0]["o"] - 1,
                      bars[0]["o"] / closes[-1] - 1, c[i] / (pv / vol if vol else c[i]) - 1,
                      (c[i] - lo) / (hi - lo) if hi > lo else 0.5, (hi - lo) / avg_range, vol / avg_vol,
                      closes[-1] / closes[-2] - 1, closes[-1] / closes[-6] - 1, i]
                     + [1.0 if m == k else 0.0 for k in MOODS])
            y.append(out > entry)
            info.append((day, i, j, entry, out))
    closes.append(bars[-1]["c"])
    ranges.append(max(b["h"] for b in bars) - min(b["l"] for b in bars))
    vols.append(sum(b["v"] for b in bars))

X, y = np.array(X), np.array(y)
train = np.array([d < TRAIN_END for d, *_ in info])
test = ~train
print(f"Decision points: {train.sum()} to learn from (2016-2020), {test.sum()} to test (2021 - Jun 2026)")
print(f"Share of up hours: learn {y[train].mean():.1%}, test {y[test].mean():.1%}\n")

MODELS = {
    "Boosted trees": HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_leaf_nodes=15,
                                                    min_samples_leaf=200, random_state=0),
    "Logistic regression": make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)),
}
for name, model in MODELS.items():
    model.fit(X[train], y[train])
    p = model.predict_proba(X[test])[:, 1]
    auc = roc_auc_score(y[test], p)
    acc = ((p >= 0.5) == y[test]).mean()
    trades, busy_until = [], (None, -1)
    for k, (prob, (day, i, j, entry, out)) in enumerate(zip(p, [info[n] for n in np.where(test)[0]])):
        if busy_until[0] == day and i < busy_until[1]:
            continue
        side = 1 if prob >= 0.55 else -1 if prob <= 0.45 else 0
        if not side:
            continue
        trades.append({"day": day, "side": side, "pct": (side * (out - entry) - COST) / entry * 100})
        busy_until = (day, j)
    print(f"=== {name} ===")
    print(f"Test years: AUC {auc:.3f} (0.5 = no skill), right direction {acc:.1%}, "
          f"chances given: {p.min():.0%} to {p.max():.0%}")
    if len(trades) < 2:
        print(f"Trades: {len(trades)} (too few)\n")
        continue
    pct = [x["pct"] for x in trades]
    t = statistics.mean(pct) / (statistics.stdev(pct) / len(pct) ** 0.5)
    h1 = statistics.mean([x["pct"] for x in trades if x["day"] < TEST_MID] or [0])
    h2 = statistics.mean([x["pct"] for x in trades if x["day"] >= TEST_MID] or [0])
    longs = [x["pct"] for x in trades if x["side"] == 1]
    shorts = [x["pct"] for x in trades if x["side"] == -1]
    la = statistics.mean(longs) if longs else 0
    sa = statistics.mean(shorts) if shorts else 0
    ok = t >= 3 and h1 > 0 and h2 > 0 and la > 0 and sa > 0
    print(f"Trades: {len(pct)} | win rate {sum(v > 0 for v in pct) / len(pct):.0%} | average {statistics.mean(pct):+.4f}% "
          f"| added up {sum(pct):+.1f}% | t-value {t:.2f}")
    print(f"   halves {h1:+.4f}% / {h2:+.4f}% | buys {len(longs)}: {la:+.4f}% | shorts {len(shorts)}: {sa:+.4f}%")
    print(f"   {'PASS' if ok else 'no pass'}")
    if name == "Boosted trees":
        from sklearn.inspection import permutation_importance
        imp = permutation_importance(model, X[test], y[test], scoring="roc_auc", n_repeats=3, random_state=0)
        top = sorted(zip(imp.importances_mean, NAMES), reverse=True)[:5]
        print("   inputs that mattered most:", ", ".join(f"{n} {v:+.4f}" for v, n in top))
    print()
