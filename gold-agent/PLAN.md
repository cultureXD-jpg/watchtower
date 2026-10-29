# Gold Agent plan

Source of truth for the Gold Agent. Update it as steps finish. Started Oct 8, 2026 by Daniel Delgado.

**Goal:** an agent that day trades gold on its own (paper money first), then other stocks later. No rush: building it correctly matters more than building it fast.

## Vision

A self-improving, memory-driven agent that learns from experience instead of only running fixed rules. It should:

- observe market conditions on its own
- find and catalog trading setups, including the ones it skips
- keep historical context
- judge how past setups turned out
- learn which setup traits go with wins and losses
- apply those lessons to future decisions

Real money only after a long, proven record on paper money, and only with Daniel's explicit decision.

## How the agent works

A loop of five parts sharing one permanent memory:

1. **Observer:** records price, trend, volatility, the dollar, rates and scheduled events (later: actual vs expected numbers).
2. **Setup catalog:** spots setups and saves each with full context.
3. **Paper trader:** takes setups that pass the current filters on the Alpaca paper account, with a stop, a target and fixed risk.
4. **Evaluator:** reviews closed trades and measures what goes with wins and losses.
5. **Learner:** turns proven findings into updated scores and filters.

**Memory** underneath: every observation, setup, trade, outcome and lesson, plus a changelog of every rule adopted and why.

## Guardrails

- **Paper money only** until there's a long, proven record across different market conditions.
- **Enough evidence:** no lesson is used until it rests on 30+ similar trades (100+ is better).
- **Prove it on unseen trades** before a pattern is promoted.
- **Small, gradual changes** to how much a setup is trusted.
- **Big changes need Daniel's OK:** new rules and risk changes are proposed first.
- **Everything is logged** with the evidence behind it.
- **Fixed risk per trade:** 1% of the account (confirm vs 2.5%).
- **Kill switch:** stop trading and flag for review at about a 15% drop from the peak (10/15/20% still open).
- Most day traders lose money, so these guardrails matter even more.

## Done

- **Phase 1: Observer.** Daily diary on watchtower at 1:15 PM PT: GLD price, direction, change, dollar (UUP), CPI, events (CPI/Jobs/Fed). Retries on FRED errors. Gate passed: 10-day test Oct 12-23.

## Next steps

1. [x] Verify the Oct 23 row and the Oct 28 "Fed decision" event. (Both verified Oct 28.)
2. [ ] Intraday watcher: record GLD every 1-5 min during market hours (Alpaca free minute data). After-close recorder live Oct 28: every 1-min bar (all exchanges) saved daily at 1:45 PM PT to intraday/GLD_YYYY-MM-DD.csv. Backfilled Oct 28 2025 - Oct 28 2026: 252 days, no missing minutes (2 half days). Still open: live recording when the paper trader needs it.
3. [ ] Setup catalog: trends, support/resistance, moving averages, RSI, volume, breakouts. Test each on history; keep only what works.
   - Test rules (agreed Oct 28): measure on Oct 2025-Jun 2026, keep Jul-Oct 2026 unseen; every trade has a stop, target and 4 PM exit; results in R after $0.02/share costs; pass = 30+ trades, positive average R, and still positive on the unseen months.
   - [x] Opening-range breakout (15 min, stop at other side, 2R target): **failed.** 167 trades, 43% wins, +0.005R average (break-even), worst drop -24.5R. Not kept. (setups/backtest_orb.py)
   - [x] VWAP trend pullback (30-min trend vs VWAP, buy the bounce off VWAP, stop at pullback low, 2R target): **failed.** 85 trades, 21% wins, -0.415R average, worst drop -44R. Tight stops (~$0.61) get shaken out by normal noise. Not kept. (setups/backtest_vwap_pullback.py)
   - [x] Opening-range fade (buy in the bottom 10% / sell in the top 10% while the range holds, stop 1/4 width outside, target the middle): **failed.** 121 trades, 46% wins, -0.149R average, worst drop -20R. Longs alone were +0.096R on 49 trades: too few and picked after the fact, so not a pass. Not kept. (setups/backtest_orb_fade.py)
   - [ ] Trend day (first-hour move of 0.5%+, trade that way at 10:30, stop at the first hour's other extreme, hold to close): **technically passes the measuring bar, but weakly.** 47 trades, 49% wins, +0.037R average, worst drop -3.3R. Statistically indistinguishable from zero (t = 0.29). Unseen check pending Daniel's go-ahead. (setups/backtest_trend_day.py)
   - [x] Event days vs normal days (measuring period only, setups/event_days.py): CPI (7 days) and jobs (7 days) look like normal days (146 days), even a bit calmer. **Fed days (6) stand out:** daily range 2.16% vs 1.61%, net move 1.29% vs 0.75%, and after the 2 PM ET announcement GLD moved 1.36% vs 0.29% on normal afternoons (about 4.7x). Only ~8 Fed days a year, so a Fed-only setup would take years to reach 30 trades; use it as context (e.g. avoid or size down into 2 PM) rather than a standalone setup.
   - [x] Market cycle check (Daniel, Oct 28; setups/market_mood.py, daily GLD in gld_daily.csv). Alpaca daily history only goes back to 2016, not 2004 (2,721 days). Each day gets a mood: Hot (within 5% of the record close), Falling (200-day average down 2%+ over 3 months), Flat (200-day average within 2% over 3 months), Cooling (everything else).
     - **Correction: gold is not near its record now.** GLD peaked at $495.90 on Jan 29, 2026 and closed at $373.51 on Oct 28, 2026 (24.7% below the record and 9.7% below its 200-day average). Today's mood is Flat.
     - Since 2016: Hot 38% of days (0.95% daily range, 10% of days move 1%+ open to close), Cooling 23% (1.10%, 13%), Flat 34% (0.77%, 6%), Falling 5% (0.68%, 5%). Flat days give a day trader about half as many big moves as Hot or Cooling days.
     - Our minute data is two moods, not one: the measuring period (Oct 2025 - Jun 2026) was 55 Hot + 113 Cooling days; the unseen months (Jul - Oct 2026) were 55 Cooling + 29 Flat. So the unseen check is also a test in a calmer market.
     - [x] Mood label wired in (Oct 28): rules live in mood.py. The diary has a new Mood column (old rows backfilled), refreshed daily from Alpaca. Every setup test now tags each trade with the previous day's mood (known before the open) and shows results per mood.
     - Per mood, measuring period: ORB Hot -0.163R (54) / Cooling +0.085R (113); VWAP pullback Hot -0.658R (30) / Cooling -0.282R (55); ORB fade Hot +0.023R (37) / Cooling -0.225R (84); trend day Hot +0.069R (16) / Cooling +0.021R (31). No setup is clearly good in any mood; the samples per mood are small, so don't pick a mood after the fact (same overfitting rule).
   - [x] Ten years of minute data (Oct 29): GLD 1-minute bars backfilled from Jan 4, 2016, so every market day since then is saved (2,721 days, 75 MB, no failures; the short days are half days plus a few days with 10-30 missing minutes). The measuring period is now Jan 2016 - Jun 2026; Jul - Oct 2026 stays unseen. Tests now also print a t-value (about 2 or more = unlikely to be luck).
     - ORB: 2,623 trades, +0.003R, t 0.14. No edge.
     - VWAP pullback: 1,124 trades, -0.268R, t -6.3. Reliably loses, in every mood.
     - ORB fade: 1,909 trades, -0.217R, t -9.0. Reliably loses, in every mood.
     - Trend day: 320 trades, +0.045R, t 1.06, worst drop -8.2R. Still slightly positive over 10 years, but could be luck. Longs +0.092R (151), shorts +0.003R (169). By mood: Hot +0.006R (132), Cooling +0.074R (85), Flat +0.030R (67), Falling -0.088R (11).
     - **Bottom line: none of the 4 setups has a proven edge.** The one-year results were not misleading, just too small to tell. Next: new setup ideas, judged on all 10 years and per mood, with rules fixed before the first run.
4. [ ] Paper trader on the Alpaca paper account, using the guardrails above.
5. [ ] Evaluator + learner, running unattended on watchtower.
6. [ ] Real money: only after a long paper record and Daniel's explicit decision.

## Later

- Overnight Asia (Tokyo, Hong Kong, Shanghai) and Europe (London, Frankfurt) moves before the US open. Wait until one market is learned; then download the history and compare it with what the agent saw live.
- Other markets like SPY, each with its own memory. Then cross-market links (e.g. stocks drop, gold rises), held to the same 30+ case, unseen-trade bar.
- Lookahead: "next event in X days".
- Calm morning report: what the agent did, balance and trend, and plain-language requests for approval. Keep the "report for Claude" idea from Bullion Lab.

## Open questions

- [ ] Kill switch level: 10%, 15% or 20%?
- [ ] Risk per trade: 1% or 2.5%?
- [ ] GLD only, or gold futures/miners later?
- [ ] Which Bullion Lab setups carry over, and which new ones to try?
- [ ] Daily results: dashboard page, daily email, or both?
- [ ] Run gold_event_study.py for real-history evidence on how gold reacts to news.
- [ ] Economic calendar source for events with expected-vs-actual numbers.

## Notes

- The PDT $25k rule was replaced in 2026 with a $2k margin minimum ([E*TRADE](https://us.etrade.com/knowledge/library/margin/pattern-day-trading-rule-change)).
- Fed 2027 dates must be added to the events list before Jan 2027.
- GLD tracks roughly one-tenth of the price of an ounce of gold.
- Runs on watchtower (DigitalOcean droplet). Alpaca paper account and basic data are free.
