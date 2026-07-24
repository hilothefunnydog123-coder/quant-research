# The Out-of-Sample Registry

*A public record of whether trading strategies actually held up — scored on data that did not exist when they were submitted.*

Most published trading edges do not survive contact with new data. Reviews of the
academic factor literature find that a large share of documented "anomalies"
shrink sharply, or vanish, once tested out-of-sample or after publication
([McLean & Pontiff, 2016](https://onlinelibrary.wiley.com/doi/10.1111/jofi.12365);
[Harvey, Liu & Zhu, 2016](https://academic.oup.com/rfs/article/29/1/5/1843824)).
The reason is structural: a backtest is run *after* the data is known, so it can
be tuned — consciously or not — until it looks good. The only honest test is
time.

This registry runs that test. Every entry is a strategy locked at a fixed date.
The scoring engine then evaluates it **only on market data dated after that lock**,
handing the strategy prices one day at a time so it can never see the future.
What you see below is not a backtest anyone optimised. It is what each strategy
actually did on days that came later.

## Scoreboard

<!--SCOREBOARD:START-->
_Last run **2026-07-24** · data source: **real SPY daily (Yahoo)** · cost: 1&nbsp;bp per turnover · benchmark: buy &amp; hold SPY._

| # | Strategy | Author | Locked | OOS window | OOS return | Sharpe | Max DD | vs B&H | Status |
|--:|---|---|:--:|:--:|--:|--:|--:|--:|:--|
| 1 | Buy & Hold | Martingale | `2022-01-01` | 1142d from 2022-01-03 | +65.1% | 0.72 | -24.5% | — | _benchmark_ |
| 2 | Time-Series Momentum (60d) | Martingale | `2022-01-01` | 1142d from 2022-01-03 | +15.6% | 0.27 | -27.5% | -0.45 | trailed benchmark |
| 3 | Mean Reversion (1d reversal) | Martingale | `2022-01-01` | 1142d from 2022-01-03 | +3.5% | 0.13 | -28.4% | -0.59 | trailed benchmark |
| 4 | SMA Crossover (20/100) | Martingale | `2022-01-01` | 1142d from 2022-01-03 | -0.4% | 0.08 | -32.9% | -0.64 | trailed benchmark |
<!--SCOREBOARD:END-->

*Sharpe is the annualised return-to-risk ratio (higher is better; ~0.6 is roughly
buy-and-hold). "vs B&H" is the entry's Sharpe minus the benchmark's over the same
window. An entry only reads as real once it has cleared the benchmark across a
meaningful stretch of genuinely out-of-sample days.*

## How it works

1. A strategy is a small Python file that implements one function,
   `position(history) -> float`, returning a target position in `[-1, 1]` for the
   next day given all prices **up to and including today**. The harness never
   passes future prices, so lookahead is impossible by construction — the exact
   failure dissected in [Note 001](../001-how-backtests-lie/).
2. The file declares `LOCKED_AS_OF`, a date. Scoring ignores every day on or
   before it; performance is measured purely on what came after.
3. [`score.py`](score.py) fetches SPY daily closes (real data when reachable,
   a clearly-labelled synthetic sample otherwise), walks each strategy forward,
   charges 1&nbsp;bp per unit of turnover, and writes the board above and
   [`scoreboard.json`](scoreboard.json). A GitHub Action re-runs it as new data
   arrives, so scores update on their own.

The four entries currently on the board are transparent, well-known baselines
(buy-and-hold, a moving-average crossover, time-series momentum, one-day
reversal). They are backfilled to a 2022 lock date to seed the registry — there
is nothing to overfit in a textbook rule, so the date is not doing any work.
Every *submitted* strategy, by contrast, is locked at the moment it is committed,
which makes its out-of-sample record genuine from day one.

## Submit a strategy

Read [`SUBMISSIONS.md`](SUBMISSIONS.md), copy
[`strategies/_template.py`](strategies/_template.py), open a pull request. Once
merged, your strategy is locked and the clock starts. If it holds up out-of-sample,
the record is public, timestamped, and yours.

---

Part of [Martingale](../). Code: MIT. Scores and text: CC BY 4.0.
