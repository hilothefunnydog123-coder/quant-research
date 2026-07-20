# Does Volatility Predict Next-Day Returns?

**Neil Quant Labs · Research Note 002** — *DRAFT (awaiting the author's real-data run)*
*Author: Neil Gilani · Reproducible code: [`experiment.py`](../experiment.py)*

> **How to finish this note:** the three places marked `【FILL】` need a real
> number that only comes from running `experiment.py` on live SPY data (see the
> repo README for the Colab steps). Everything else is a draft in a neutral
> voice — rewrite it in *your own words* so the paper is truly yours, and edit
> anything you'd say differently. Then delete these quote-blocks.

## Abstract

> Write this LAST, once you have your number.

We test whether a stock's recent volatility predicts its next-day return, using
【FILL: N】 trading days of SPY data. Pairing each day's 20-day volatility with
the *following* day's return, we find a correlation of **【FILL: r】**. This
indicates that today's volatility 【FILL: does / does not】 meaningfully predict
the direction of tomorrow's move, consistent with 【your one-line takeaway】.

## 1. Introduction

Markets clearly go through calm stretches and stormy ones — a fact so visible
that traders often assume the storminess itself is a signal. A natural question
follows: if a stock has been unusually volatile lately, does that tell us
anything about where it goes *next*?

This note tests one precise version of that question. **Hypothesis (stated
before looking at the result):** a day's recent volatility has *no* reliable
relationship with the direction of the next day's return — i.e., volatility
measures how *big* moves are, not which *way* they go. A correlation near zero
would support this; a clearly non-zero correlation would refute it. Fixing the
hypothesis in advance is a rule of this lab's [methodology](../../METHODOLOGY.md):
it stops us from inventing a story to fit whatever we happen to find.

## 2. Data & Method

**Data.** Daily closing prices for SPY (an ETF tracking the S&P 500) from
【FILL: start date】 to 【FILL: end date】 — 【FILL: N】 trading days — downloaded
via `yfinance`.

**Returns.** Each day's return is `today's close / yesterday's close − 1`.

**Volatility.** For each day, we take the standard deviation of the trailing 20
daily returns — a standard measure of how "bouncy" recent price action has been.
The first 19 days have too little history and are excluded.

**The key step (no lookahead).** We pair each day's volatility — computed only
from returns *up to and including that day* — with the return on the *next* day.
Pairing it with the *same* day's return would let the predictor "see" the very
move it is supposed to forecast; that is lookahead bias, the error quantified in
[Note 001](../../001-how-backtests-lie/). Using tomorrow's return keeps the test
honest.

**Metric.** We report the Pearson correlation between today's volatility and
tomorrow's return, a single number from −1 to +1, where 0 means no linear
relationship.

## 3. Results

> Paste the real output of `experiment.py` here.

- Paired days analyzed: **【FILL: N】**
- Correlation (today's volatility → tomorrow's return): **【FILL: r】**

![Volatility today vs. return tomorrow](figures/scatter.png)

> Describe the chart in a sentence: is the yellow best-fit line essentially
> flat (no relationship), or does it clearly slope? Is |r| close to 0 (weak) or
> closer to 1 (strong)?

【FILL: one or two sentences describing what the number and chart show】

## 4. Discussion

> Interpret honestly once you have the number. Guidance:
> - If **|r| is near 0** (very likely): today's volatility does not predict the
>   *direction* of tomorrow's move. That is a real, valuable result — it says
>   the "stormy market" feeling isn't a directional edge, echoing Note 001's
>   lesson that easy prediction doesn't survive scrutiny.
> - If **r is clearly non-zero**: be skeptical before believing it. Could it be
>   one lucky period? Would it hold on a different ETF or a different decade?

【FILL: your interpretation of what the result means】

## 5. Limitations

This study is deliberately narrow, and several caveats bound what it can claim.
It examines a single instrument (SPY), a single volatility window (20 days), and
a single historical period; a different asset, window, or era could differ. It
tests only the *direction* of the next-day return, not its *size* — volatility
may well predict how large tomorrow's move is without predicting which way it
goes. Pearson correlation captures only *linear* relationships, so a non-linear
link could be missed. And correlation, even if found, is not causation.

## 6. Conclusion

> One paragraph, written last.

We asked whether recent volatility predicts the next day's return on SPY. Across
【FILL: N】 days the correlation was **【FILL: r】**, meaning 【FILL: your honest
one-sentence answer】.

## References

- Cont, R. (2001). *Empirical properties of asset returns: stylized facts and
  statistical issues.*
- Neil Quant Labs, Research Note 001 — *How Backtests Lie.*

---

## How to cite

> Gilani, N. (2026). *Does Volatility Predict Next-Day Returns?* Neil Quant Labs, Research Note 002. https://github.com/hilothefunnydog123-coder/quant-research

© 2026 Neil Gilani. Code: MIT License. Text, figures, and findings: CC BY 4.0 (reuse with attribution).
