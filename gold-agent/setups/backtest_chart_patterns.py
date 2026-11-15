# GOLD AGENT: named chart patterns on 5-, 15- and 60-minute GLD bars, traded intraday.
#
# Rules (fixed Nov 15, 2026, before the first run):
#   - Bars are built from regular-hours minutes, counted from 09:30 (the last 60-minute bar is 30 minutes).
#     Bars run on across days, so a pattern can start the day before; entries are same-day only.
#   - ATR = average high-low range of the last 14 bars. A pattern is confirmed at a bar's close;
#     fill at the next minute's open. Stops are $0.02 past the level named. Target 2R.
#   - One trade at a time per pattern (several a day allowed). No entry signals at or after 15:00.
#     Everything closes at the day's close. Same-minute stop and target = stop. Costs $0.02/share.
#     Trades risking under $0.10/share are skipped.
#   - Flag: a 4-bar pole moving 2+ ATR (open of the 1st to close of the 4th), then a 4-bar flag whose
#     range is at most 1 ATR and holds the upper half of the pole. Buy on a close above the flag;
#     stop below the flag's low. Mirror for bear flags.
#   - Double bottom: the last two swing lows (lower than 2 bars each side) are 5+ bars apart and within
#     0.25 ATR of each other; the high between them (neckline) is 1+ ATR above them. Buy the first close
#     above the neckline within 10 bars of the second low; stop below the lower low. Mirror: double top.
#   - Inside bar: a bar inside the bar before it. Buy if the next bar closes above that earlier
#     ("mother") bar's high, short if below its low. Stop at the mother bar's other side.
#   - Failed breakout: a bar closes above the highest high of the 20 bars before it, and the next bar
#     closes back below that level -> short, stop above the higher of the two bars. Mirror for lows.
#   - Measuring period only (Jan 2016 - Jun 2026). Pass: t-value 3+ and positive in both halves.
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import COST, MID, SPLIT, load_days

PAD, MIN_RISK, TARGET_R = 0.02, 0.10, 2


def flag(B, n, atr, st):
    O, H, L, C = B["o"], B["h"], B["l"], B["c"]
    fh, fl = max(H[n - 4:n]), min(L[n - 4:n])
    if fh - fl > atr:
        return None
    mid = (O[n - 8] + C[n - 5]) / 2
    if C[n - 5] - O[n - 8] >= 2 * atr and fl >= mid and C[n] > fh:
        return 1, fl - PAD
    if O[n - 8] - C[n - 5] >= 2 * atr and fh <= mid and C[n] < fl:
        return -1, fh + PAD


def double(B, n, atr, st):
    H, L, C = B["h"], B["l"], B["c"]
    k = n - 2
    if L[k] < min(L[k - 2], L[k - 1], L[k + 1], L[k + 2]):
        st.setdefault("lows", []).append(k)
    if H[k] > max(H[k - 2], H[k - 1], H[k + 1], H[k + 2]):
        st.setdefault("highs", []).append(k)
    for side, key in ((1, "lows"), (-1, "highs")):
        pts = st.get(key, [])
        if len(pts) < 2 or (pts[-2], pts[-1]) == st.get("used" + key):
            continue
        a, b = pts[-2], pts[-1]
        X = L if side == 1 else H
        if b - a < 5 or abs(X[a] - X[b]) > 0.25 * atr or n - b > 10:
            continue
        if side == 1:
            neck, base = max(H[a + 1:b]), min(L[a], L[b])
            ok = neck - base >= atr and C[n] > neck and all(c <= neck for c in C[b + 1:n])
        else:
            neck, base = min(L[a + 1:b]), max(H[a], H[b])
            ok = base - neck >= atr and C[n] < neck and all(c >= neck for c in C[b + 1:n])
        if ok:
            st["used" + key] = (a, b)
            return side, base - side * PAD


def inside(B, n, atr, st):
    H, L, C = B["h"], B["l"], B["c"]
    if H[n - 1] <= H[n - 2] and L[n - 1] >= L[n - 2]:
        if C[n] > H[n - 2]:
            return 1, L[n - 2] - PAD
        if C[n] < L[n - 2]:
            return -1, H[n - 2] + PAD


def failed(B, n, atr, st):
    H, L, C = B["h"], B["l"], B["c"]
    p, q = max(H[n - 21:n - 1]), min(L[n - 21:n - 1])
    if C[n - 1] > p and C[n] < p:
        return -1, max(H[n - 1], H[n]) + PAD
    if C[n - 1] < q and C[n] > q:
        return 1, min(L[n - 1], L[n]) - PAD


PATTERNS = [("Flag", flag), ("Double bottom/top", double), ("Inside bar", inside), ("Failed breakout", failed)]


def minutes(t):
    return (int(t[:2]) - 9) * 60 + int(t[3:5]) - 30


def run(tf):
    B = {k: [] for k in "ohlc"}
    acct = [{"name": nm, "fn": fn, "st": {}, "pos": None, "sig": None, "trades": []} for nm, fn in PATTERNS]
    for day, bars in load_days():
        if day >= SPLIT:
            break
        start = 0
        for i, b in enumerate(bars):
            t, last = b["t"][:5], i == len(bars) - 1
            for a in acct:
                if a["sig"]:
                    side, stop = a["sig"]
                    a["sig"] = None
                    risk = (b["o"] - stop) * side
                    if risk >= MIN_RISK:
                        a["pos"] = {"side": side, "entry": b["o"], "stop": stop, "risk": risk,
                                    "target": b["o"] + side * TARGET_R * risk}
                p = a["pos"]
                if p:
                    s, px = p["side"], None
                    if (b["l"] <= p["stop"]) if s == 1 else (b["h"] >= p["stop"]):
                        px, why = p["stop"], "stop"
                    elif (b["h"] >= p["target"]) if s == 1 else (b["l"] <= p["target"]):
                        px, why = p["target"], "target"
                    elif last:
                        px, why = b["c"], "close"
                    if px is not None:
                        a["trades"].append({"side": s, "day": day, "why": why,
                                            "r": ((px - p["entry"]) * s - COST) / p["risk"]})
                        a["pos"] = None
            if last or minutes(bars[i + 1]["t"][:5]) // tf != minutes(t) // tf:
                chunk = bars[start:i + 1]
                start = i + 1
                B["o"].append(chunk[0]["o"])
                B["h"].append(max(x["h"] for x in chunk))
                B["l"].append(min(x["l"] for x in chunk))
                B["c"].append(b["c"])
                n = len(B["c"]) - 1
                if n < 30:
                    continue
                atr = sum(B["h"][j] - B["l"][j] for j in range(n - 13, n + 1)) / 14
                for a in acct:
                    sig = a["fn"](B, n, atr, a["st"])
                    if sig and not a["pos"] and not last and t < "15:00":
                        a["sig"] = sig
    return acct


print(f"{'Pattern':20}{'bars':>5}{'trades':>8}{'avg R':>8}{'t':>7}{'half 1':>8}{'half 2':>8}"
      f"{'long R':>13}{'short R':>13}{'worst':>8}  pass")
for tf in (5, 15, 60):
    for a in run(tf):
        rs = [x["r"] for x in a["trades"]]
        if len(rs) < 2:
            print(f"{a['name']:20}{tf:>5}  too few trades ({len(rs)})")
            continue
        t = statistics.mean(rs) / (statistics.stdev(rs) / len(rs) ** 0.5)
        h1 = statistics.mean([x["r"] for x in a["trades"] if x["day"] < MID] or [0])
        h2 = statistics.mean([x["r"] for x in a["trades"] if x["day"] >= MID] or [0])
        side = {}
        for s in (1, -1):
            v = [x["r"] for x in a["trades"] if x["side"] == s]
            side[s] = f"{len(v)}:{statistics.mean(v):+.3f}" if v else "-"
        peak = run_r = dd = 0.0
        for r in rs:
            run_r += r
            peak = max(peak, run_r)
            dd = min(dd, run_r - peak)
        ok = "PASS" if t >= 3 and h1 > 0 and h2 > 0 else "no"
        print(f"{a['name']:20}{tf:>5}{len(rs):>8}{statistics.mean(rs):>+8.3f}{t:>7.2f}{h1:>+8.3f}{h2:>+8.3f}"
              f"{side[1]:>13}{side[-1]:>13}{dd:>8.1f}  {ok}", flush=True)
