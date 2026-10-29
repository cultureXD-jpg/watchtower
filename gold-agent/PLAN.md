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
