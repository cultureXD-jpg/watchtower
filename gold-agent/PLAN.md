# Gold Agent plan

Source of truth for the Gold Agent. Update it as steps finish.

**Goal:** an agent that day trades gold on its own (paper money first), then other stocks later.

## Done

- **Phase 1: Observer.** Daily diary on watchtower at 1:15 PM PT: GLD price, direction, change, dollar (UUP), CPI, events (CPI/Jobs/Fed). Retries on FRED errors. 10-day test Oct 12-23.

## Next steps

1. [ ] Verify the Oct 23 row and the Oct 28 "Fed decision" event.
2. [ ] Intraday watcher: record GLD every 1-5 min during market hours (Alpaca free minute data).
3. [ ] Setup catalog: trends, support/resistance, moving averages, RSI, volume, breakouts. Test each on history; keep only what works.
4. [ ] Paper trader on the Alpaca paper account. Risk 1% per trade (confirm vs 2.5%), ~15% drawdown kill switch, 30+ similar trades before trusting a lesson.
5. [ ] Evaluator + learner.

## Later

- Overnight Asia/Europe moves (wait until one market is learned; compare downloaded history vs live).
- Other stocks, like SPY.
- Lookahead: "next event in X days".

## Notes

- The PDT $25k rule was replaced in 2026 with a $2k margin minimum.
- Fed 2027 dates must be added to the events list before Jan 2027.
