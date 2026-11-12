# GOLD AGENT setup test: "break and lower high" (idea from @tradesbysci), on 4-hour bars.
#
# Rules (fixed Nov 11, 2026, before the first run):
#   - 4-hour bars from regular-hours minutes: 09:30-13:29 and 13:30-16:00 ET (two a day, one on half days).
#   - Swing low = a 4h bar whose low is below the lows of the 2 bars before and the 2 after
#     (known once the 2nd bar after it closes). Swing high is the mirror.
#   - Short: the latest swing low is "support". A 4h bar closes below it (and the latest swing high
#     is above it). Then wait for the bounce: a 4h bar whose high is above the bars on each side
#     (1 each side), after the break, below that earlier swing high (= lower high), with no 4h close
#     back above support. Bounce low = lowest low from the break bar up to the lower high.
#   - Entry: a 1-minute close below the bounce low; fill at the next minute's open.
#     Stop = lower high + $0.02. Target = 2R.
#   - The setup is cancelled if price trades above the lower high, a 4h bar closes back above support,
#     no lower high forms within 10 4h bars of the break, no entry within 10 4h bars of the lower
#     high, or the trigger comes while a trade is already open (or the day's trade is used).
#   - Long is the exact mirror (break above resistance, higher low, buy above the bounce high).
#   - Trades risking under $0.10/share are skipped (costs would be over 0.2R).
#   - Day version: entry signals before 15:00 only, one trade a day, closed at that day's close.
#     Swing version: one trade at a time, held to stop, target, or the close of the 5th trading day
#     (entry day = day 1). A gap past the stop or target fills at that minute's open.
#   - Same-minute stop and target counts as the stop. Costs $0.02/share. Measuring period only
#     (Jan 2016 - Jun 2026); unseen days are never loaded.
#   - Pass: t-value 3+ and profitable in both halves.
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import COST, SPLIT, load_days, summary
from mood import moods

MIN_RISK, TARGET_R, PAD, WAIT, SWING_DAYS = 0.10, 2, 0.02, 10, 5


class Side:
    """Tracks short setups on prices multiplied by sign (sign=-1 turns the long setup into a short one)."""

    def __init__(self, sign):
        self.sign = sign
        self.h, self.l, self.c = [], [], []
        self.level = self.ph = None
        self.phase = "watch"
        self.found = 0

    def bar4(self, o, h, l, c):
        s = self.sign
        h, l = (h, l) if s == 1 else (-l, -h)
        self.h.append(h)
        self.l.append(l)
        self.c.append(c * s)
        n = len(self.c) - 1
        H, L, C = self.h, self.l, self.c
        if n >= 4:
            k = n - 2
            if L[k] < min(L[k - 2], L[k - 1], L[k + 1], L[k + 2]):
                self.level = L[k]
            if H[k] > max(H[k - 2], H[k - 1], H[k + 1], H[k + 2]):
                self.ph = H[k]
        if self.phase == "watch":
            if self.level is not None and self.ph is not None and self.ph > self.level and C[n] < self.level:
                self.phase, self.b, self.brk, self.top = "broken", n, self.level, self.ph
                self.level = None
        elif C[n] > self.brk:
            self.phase = "watch"
        elif self.phase == "broken":
            k = n - 1
            if k > self.b and H[k] > H[k - 1] and H[k] > H[n]:
                bl = min(L[self.b:k])
                if H[k] < self.top and H[k] > bl:
                    self.phase, self.lh, self.bl, self.until = "armed", H[k], bl, n + WAIT
                    self.found += 1
                else:
                    self.phase = "watch"
            elif n - self.b >= WAIT:
                self.phase = "watch"
        elif n >= self.until:
            self.phase = "watch"

    def minute(self, b):
        """Returns True when this minute's close triggers an entry."""
        if self.phase != "armed":
            return False
        hi = b["h"] if self.sign == 1 else -b["l"]
        if hi > self.lh:
            self.phase = "watch"
            return False
        if b["c"] * self.sign < self.bl:
            self.phase = "watch"
            return True
        return False


def backtest(swing):
    mood_by_day = moods()
    days = sorted(mood_by_day)
    prev = {d: mood_by_day[days[i - 1]] for i, d in enumerate(days) if i}
    sides = [Side(-1), Side(1)]      # sign -1 tracks longs, +1 shorts
    trades, pos, signal = [], None, None
    for day, bars in load_days():
        if day >= SPLIT:
            break
        traded_today = False
        for i, b in enumerate(bars):
            t, last = b["t"][:5], i == len(bars) - 1
            if signal:                                   # fill at this minute's open
                side, stop = signal
                entry = b["o"]
                risk = (entry - stop) * side
                signal = None
                if risk >= MIN_RISK:
                    pos = {"side": side, "entry": entry, "stop": stop, "risk": risk, "day": day,
                           "target": entry + side * TARGET_R * risk, "days": 1}
                    traded_today = True
            if pos:
                s = pos["side"]
                exit_px = why = None
                if i == 0 and pos["day"] != day:         # overnight gap
                    if (b["o"] - pos["stop"]) * s <= 0:
                        exit_px, why = b["o"], "stop"
                    elif (b["o"] - pos["target"]) * s >= 0:
                        exit_px, why = b["o"], "target"
                if why is None:
                    if (b["l"] <= pos["stop"]) if s == 1 else (b["h"] >= pos["stop"]):
                        exit_px, why = pos["stop"], "stop"
                    elif (b["h"] >= pos["target"]) if s == 1 else (b["l"] <= pos["target"]):
                        exit_px, why = pos["target"], "target"
                    elif last and (not swing or pos["days"] >= SWING_DAYS):
                        exit_px, why = b["c"], "close"
                if why:
                    r = ((exit_px - pos["entry"]) * s - COST) / pos["risk"]
                    trades.append({"side": "long" if s == 1 else "short", "risk": pos["risk"],
                                   "r": r, "why": why, "day": pos["day"], "mood": prev.get(pos["day"])})
                    pos = None
                elif last:
                    pos["days"] += 1
            for sd in sides:
                if sd.minute(b):
                    can = (not pos and not signal and not last and
                           (swing or (t < "15:00" and not traded_today)))
                    if can:
                        signal = (-sd.sign, (sd.lh + PAD) * sd.sign)
            if last or (t < "13:30" and bars[i + 1]["t"][:5] >= "13:30"):
                j = i
                while j > 0 and (bars[j - 1]["t"][:5] < "13:30") == (t < "13:30"):
                    j -= 1
                chunk = bars[j:i + 1]
                for sd in sides:
                    sd.bar4(chunk[0]["o"], max(x["h"] for x in chunk), min(x["l"] for x in chunk), b["c"])
    print(f"Setups found: {sides[1].found} short, {sides[0].found} long")
    return trades


for name, swing in (("Day trade (closed by the close)", False), ("Swing (up to 5 days)", True)):
    print(f"\n=== {name} ===")
    summary("Measuring period (Jan 2016 - Jun 2026)", backtest(swing))
