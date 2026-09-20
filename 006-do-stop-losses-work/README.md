# Research Note 006 — Do Stop-Losses Actually Improve Risk-Adjusted Returns?

> **Status: complete.** 30 stop rules tested on 5,031 days of the NASDAQ Composite
> (1999–2018), cross-checked on GOOG. Finding: **the apparent edge is the search.**
> The best rule beats buy-and-hold by **+0.094** Sharpe — and running the *same
> 30-rule search* on shuffled bars, with every trend destroyed, beats it by
> **+0.095** (*p* = **0.43**). Picking the winner on the first half and running it
> forward **loses** by **−0.166** Sharpe, and in-sample rank **anti-correlates**
> with out-of-sample rank (−0.28). Two real findings survive: **20.6%** of stops
> gap through their price, and a tight trailing stop genuinely cuts drawdown —
> mostly, though not always, by more than simply holding less.
> See [`paper/paper.pdf`](paper/paper.pdf).

**The question:** "Always use a stop loss" is the most repeated rule in retail
trading and one of the least tested. A stop isn't a forecast — it's a
path-dependent rule that truncates a holding period. So: does it actually improve
**risk-adjusted** returns, or does it just take less risk (which you can do for
free by holding less)?

**Hypothesis (stated before running it):** a stop will **not** improve
risk-adjusted returns on a positively drifting index — it sells after a decline,
sits out part of the drift, and must buy back, so it should cut return roughly in
proportion to cut exposure, leaving Sharpe flat or worse. It *will* cut maximum
drawdown, but not by more than holding the same average exposure passively. A rule
that beat buy-and-hold by more than a 30-way search buys on trendless data **and**
held up out of sample would refute this.

**Success metric, fixed in advance:** out-of-sample Sharpe after costs — *not*
maximum drawdown, which any stop can reduce simply by trading less.

## What the code does

- **The grid (30 rules, fixed before looking at results)** — trailing vs fixed ×
  {5, 10, 15, 20, 25}% × re-entry after {1, 5, 21} days.
- **Honest execution** — the stop level on day *t* uses only data through *t−1*;
  it triggers when that day's **low** touches it; and if the day **opened below**
  the level, it fills at the **open**, not the stop, because the market gapped
  through it overnight. `gap_aware=False` reproduces the usual backtesting error
  so its size can be measured instead of assumed.
- **The null that matters** — each bar is stored as its shape relative to the
  prior close and the bars are **shuffled**, preserving the return distribution
  and every bar's geometry exactly while destroying all trend structure. A
  trailing stop is a trend-following device, so whatever the best-of-30 still
  earns there is what the *search alone* is worth. Repeated 1,000 times.
- **The fair benchmark** — a constant exposure equal to the stop's own time in
  market. (With cash at 0% this has the same Sharpe as buy-and-hold, so drawdown
  is the only axis on which a stop can actually win.)
- **Out-of-sample** — choose the best rule on the first half, score it on the
  second, and report the rank correlation across all 30.

Validated by six self-tests that run before every experiment: a rising series never
triggers; a hand-built bar fills at the stop; the same bar gapping through fills at
the open; **changing the future leaves every past return unchanged** (no lookahead);
costs reconcile exactly against trade count; and shuffling preserves buy-and-hold's
Sharpe, cumulative return, and bar coherence.

## Reproduce

```bash
pip install arch backtesting numpy matplotlib
python experiment.py              # grid, null, out-of-sample, gaps, figures
python experiment.py --selftest   # validation checks only
python paper/build_pdf.py         # rebuild the PDF
```

Data is pinned to frozen datasets in `arch` 8.0.0 and `backtesting` 0.6.6 (see
[Note 005](../005-overnight-vs-intraday/) for why), so every number reproduces
exactly. The 1,000-shuffle null takes a couple of minutes.
