# Momentum vs. Mean Reversion, Across Regimes, After Costs

**Neil Quant Labs · Research Note 003**
*Author: Neil Gilani · Reproducible code: [`experiment.py`](../experiment.py)*

## Abstract

<!-- Write last, from results.json. Template:
We compare two opposing trading ideas — momentum (bet the trend continues) and
mean reversion (bet the last move reverses) — on ~N years of SPY, splitting the
record into bull and bear regimes and charging realistic costs. After 1bp costs,
momentum's Sharpe is X and mean reversion's is Y overall; but the picture flips
by regime (bull: …, bear: …). Because mean reversion trades T× more, costs erase
most of its gross edge. The lesson: neither idea is universally right — each is a
bet on a regime, and costs decide which survives. -->
**PENDING real-data run — fill in from `results.json`.**

## 1. Introduction

Two of the oldest instincts in markets flatly contradict each other. **Momentum**
says a rising asset tends to keep rising — buy strength, sell weakness. **Mean
reversion** says moves overshoot and snap back — buy weakness, sell strength.
Both have made money; both have blown up. So the interesting question isn't
"which is right?" but **"when is each right, and does the edge survive the cost of
trading it?"**

This note tests both on SPY, with three disciplines that separate a real result
from a backtest fantasy (all part of this lab's [methodology](../../METHODOLOGY.md)):

1. **Regimes.** Markets behave differently when trending up vs. falling. We label
   each day *bull* (price at or above its 200-day average) or *bear* (below) and
   measure each strategy *within* each regime, not just on average.
2. **Costs.** A signal that only works for free isn't a strategy. We charge a
   realistic per-trade cost and report results at 0, 1, and 5 basis points.
3. **No lookahead.** Every position is decided from data up to day *t* and earns
   day *t+1*'s return — the exact error dissected in [Note 001](../../001-how-backtests-lie/).

**Hypothesis (stated before running it):** momentum works better in trending
*bull* regimes, mean reversion better in *bear* / choppy regimes; and mean
reversion — which flips position far more often — loses much more of its gross
edge to costs. A result matching this supports the "each idea is a bet on a
regime" view; a strategy that wins everywhere after costs would refute it.

## 2. Data & Method

**Data.** Daily closing prices for SPY (an ETF tracking the S&P 500) from January
2007 to July 2026 — chosen to include the 2008 crash, so both a violent bear
market and long bull runs are in the sample — downloaded via `yfinance`.

**Signals.** Each day *t* produces a position (`+1` long or `−1` short) held into
day *t+1*, using only information available through day *t*:

- **Momentum:** `+1` if the trailing 20-day return is positive, else `−1`.
- **Mean reversion:** `+1` if *yesterday's* return was negative, else `−1`.

**Regime.** Day *t* is *bull* if that day's closing price is at or above its
trailing 200-day average, else *bear*.

**Costs.** Each day we charge `cost × |change in position|`. A full flip from
`−1` to `+1` moves 2 units, so at 1 bp per unit it costs 2 bps. We also report the
average daily **turnover** of each strategy, which explains its sensitivity to costs.

**Metric.** Annualized Sharpe ratio — average daily strategy return ÷ its standard
deviation, × √252. Reported gross and net of costs, overall and within each regime,
with **buy & hold** as the benchmark.

## 3. Results

<!-- Fill from results.json after the real-data run. -->

**Overall (1 bp costs):**

| Strategy | Gross Sharpe | Net Sharpe | Avg turnover |
|---|---|---|---|
| Buy & hold | PENDING | PENDING | 0 |
| Momentum | PENDING | PENDING | PENDING |
| Mean reversion | PENDING | PENDING | PENDING |

**After-cost Sharpe by regime:**

| Regime | Momentum | Mean reversion |
|---|---|---|
| Bull (price ≥ 200d MA) | PENDING | PENDING |
| Bear (price < 200d MA) | PENDING | PENDING |

**Cost sensitivity (net Sharpe):**

| Cost | Momentum | Mean reversion |
|---|---|---|
| 0 bps | PENDING | PENDING |
| 1 bp | PENDING | PENDING |
| 5 bps | PENDING | PENDING |

![Equity curves and regime Sharpe](figures/regimes.png)

<!-- A couple sentences on what the numbers actually show. -->

## 4. Discussion

<!-- Fill in from the numbers. Points to hit:
- Which strategy wins overall after costs — and by how little/much vs. buy & hold?
- The regime story: does momentum lead in bull and reversion in bear (or not)?
  Report the actual Sharpe gap.
- Costs: how far does each strategy's Sharpe fall from 0 -> 5 bps, and does the
  higher-turnover strategy (mean reversion) fall faster? Tie turnover to the drop.
- The honest takeaway: is either a standalone strategy after costs, or is the real
  finding that each is a conditional (regime-dependent) bet? Don't overclaim.
- Connect to Note 001: an in-sample winner that ignores costs is exactly the trap. -->
**PENDING real-data run.**

## 5. Limitations

This study is deliberately simple. It uses one instrument (SPY), one momentum
lookback (20 days), one reversal horizon (1 day), and one regime definition (the
200-day average); other choices could give different numbers, and testing many and
reporting the best would be the data-snooping error of Note 001 — so these were
fixed in advance. The cost model is a flat per-turnover charge and ignores
slippage, borrowing costs for shorts, and the fact that shorting an index isn't
free. Sharpe assumes returns are roughly comparable day to day and says nothing
about crash risk. A positive after-cost Sharpe here would be evidence a signal
exists, not proof it is tradable at size. And past regime behavior need not repeat.

## 6. Conclusion

<!-- Restate the question and the honest one-paragraph answer from the numbers. If
the hypothesis holds: neither momentum nor mean reversion is universally right —
each is a bet on a market regime, and once realistic costs are charged, the
high-turnover strategy keeps far less of its paper edge. -->
**PENDING real-data run.**

## References

- Jegadeesh, N. & Titman, S. (1993). *Returns to Buying Winners and Selling
  Losers.* (The classic momentum result.)
- Jegadeesh, N. (1990). *Evidence of Predictable Behavior of Security Returns.*
  (Short-term reversal / mean reversion.)
- Moskowitz, T., Ooi, Y. H. & Pedersen, L. (2012). *Time Series Momentum.*
- Neil Quant Labs, Research Note 001 — *How Backtests Lie.*

---

## How to cite

> Gilani, N. (2026). *Momentum vs. Mean Reversion, Across Regimes, After Costs.* Neil Quant Labs, Research Note 003. https://github.com/hilothefunnydog123-coder/quant-research

© 2026 Neil Gilani. Code: MIT License. Text, figures, and findings: CC BY 4.0 (reuse with attribution).
