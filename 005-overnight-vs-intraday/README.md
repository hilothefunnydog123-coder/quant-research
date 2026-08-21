# Research Note 005 — Where Do Returns Actually Come From: Overnight or Intraday?

> **Status: complete.** Run on 5,030 days of the NASDAQ Composite (1999–2018),
> cross-checked on GOOG. Finding: **the split is real, and it is not an edge.**
> Overnight compounds **+917%** while the intraday session loses **−70%** — the
> index's entire gain happened while the market was shut. But break-even cost is
> **2.46 bp per side** at the day's two widest spreads, **+274.5%** of the gain
> came from 1999–2000 alone, and in 2009–2018 the two sessions are effectively
> **tied** (+7.77% vs +7.15%). At the median they are a dead heat; what separates
> them is that **18 of the 20 worst sessions in 20 years were intraday**.
> Separately, a widely distributed S&P 500 feed answers this question **backwards**
> because its opens are stale. See [`paper/paper.pdf`](paper/paper.pdf).

**The question:** Every trading day is two sessions — the **overnight** gap
(yesterday's close → today's open) and the **intraday** move (open → close). They
multiply to the daily return, so the split is an *accounting identity*, not a
model. A popular claim says the market's entire long-run return is earned
overnight and the regular session contributes nothing. Is that true, does it
survive costs, and does it hold up out of sample?

**Hypothesis (stated before running it):** the gap will be **real and measurable**
— it is an identity, not a fitted signal — but **not exploitable after realistic
costs**, because collecting it requires a round trip every single day at the open
and the close. A gap that survived costs, held across sub-periods, and was not
concentrated in one era would refute this.

## What the code does

- **The decomposition** — splits every day into its two sessions and *asserts* the
  identity `(1+overnight)(1+intraday) = (1+close-to-close)` rather than assuming
  it (max residual: 2.2 × 10⁻¹⁶). Day 0 is dropped — it has no prior close.
- **A data audit that runs first** — two tests decide which series may be used at
  all: how often the open is *exactly* the prior close, and the ratio of overnight
  to intraday volatility. A series failing the second is rejected before any
  analysis, because dividing by a fake opening price invalidates everything
  downstream.
- **Costs** — a session strategy enters and exits daily, so it crosses the spread
  twice a day and is charged for both. Reports the full cost curve and the
  break-even.
- **Robustness** — paired test with a bootstrap CI (the sessions share days, so
  the comparison must be paired), split-sample, per-year, symmetric trimmed means,
  and a count of which session held the worst days.
- **A controlled contamination experiment** — takes the *clean* feed and breaks it
  on purpose, overwriting the open with the prior close on a fraction *p* of days,
  to show the data defect **causes** the reversed conclusion rather than merely
  accompanying it.

**Reproducibility.** Unlike Notes 002–004, this note does **not** fetch live data
— it is pinned to frozen datasets shipped inside `arch` 8.0.0 and `backtesting`
0.6.6, so every number in the paper reproduces exactly, permanently. For a study
about data quality, that seemed like the only defensible choice.

Validated by a self-test that runs before every experiment: the identity holds on
random prices, a planted overnight drift is recovered with no phantom intraday
drift, data with **no** planted edge correctly yields **no** significant gap, and
the audit flags a stale-open feed while clearing a clean one.

## Reproduce

```bash
pip install arch backtesting numpy scipy matplotlib
python experiment.py              # audit, decomposition, costs, robustness, figures
python experiment.py --selftest   # validation checks only
python paper/build_pdf.py         # rebuild the PDF
```
