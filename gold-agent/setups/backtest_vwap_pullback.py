# GOLD AGENT: setup test #2, VWAP trend pullback on 1-minute GLD bars.
#
# Rules (fixed before the first run; shared test rules are in common.py):
#   - VWAP = the day's running volume-weighted average price from 9:30 ET.
#   - Uptrend: from 10:00 ET on, the last 30 closes are all above VWAP and VWAP is higher
#     than 30 minutes ago. Downtrend is the mirror image.
#   - Pullback: in an uptrend, a bar's low touches VWAP. Signal: the first later bar that
#     closes above VWAP and above the high of the bar that touched. (Mirror for shorts.)
#     If price closes on the wrong side of VWAP first, the pullback is cancelled.
#   - Stop = the lowest low of the pullback (touch bar to signal bar). Target = 2R.
#
# Usage: backtest_vwap_pullback.py            -> measuring period only
#        backtest_vwap_pullback.py --unseen   -> also the unseen months (only once a setup has passed)
from common import LAST_ENTRY, run, simulate

TREND_BARS = 30
START = "10:00"
TARGET_R = 2.0


def trade_day(bars):
    pv = vol = 0.0
    vw = []
    for b in bars:
        pv += b["vwap"] * b["v"]
        vol += b["v"]
        vw.append(pv / vol if vol else b["c"])

    touch = None             # (index, side) of a pullback in progress
    for i in range(TREND_BARS, len(bars) - 1):
        b = bars[i]
        if b["t"] > LAST_ENTRY:
            return None
        if touch:
            j, side = touch
            if (b["c"] - vw[i]) * side < 0:
                touch = None                 # closed on the wrong side: cancelled
            elif (b["c"] - (bars[j]["h"] if side == 1 else bars[j]["l"])) * side > 0:
                if side == 1:
                    stop = min(x["l"] for x in bars[j:i + 1])
                else:
                    stop = max(x["h"] for x in bars[j:i + 1])
                return simulate(bars, i, side, stop, TARGET_R)
            continue
        if b["t"] < START:
            continue
        prior = range(i - TREND_BARS, i)
        up = all(bars[k]["c"] > vw[k] for k in prior) and vw[i - 1] > vw[i - TREND_BARS]
        down = all(bars[k]["c"] < vw[k] for k in prior) and vw[i - 1] < vw[i - TREND_BARS]
        if up and b["l"] <= vw[i]:
            touch = (i, 1)
        elif down and b["h"] >= vw[i]:
            touch = (i, -1)
    return None


run(trade_day)
