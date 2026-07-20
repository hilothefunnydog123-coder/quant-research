# Does Volatility Predict the Size of the Next-Day Move?

**Neil Quant Labs · Research Note 003**
*Author: Neil Gilani · Reproducible code: [`experiment.py`](../experiment.py)*

## Abstract

<!-- Write last, once you have the real numbers. Template:
We test whether a stock's recent volatility predicts the SIZE of its next-day
move (|return|, direction removed), using ~2,900 trading days of SPY data.
Pairing each day's 20-day volatility with the *following* day's absolute return
across N days, we find a correlation of **+X.XX**. Unlike Note 002 — where
volatility did not predict direction — volatility clearly predicts move size:
average |next-day return| rises from A% in the calmest quintile to B% in the
stormiest. This is volatility clustering: turbulence persists. -->
**PENDING real-data run — fill in from `results.json`.**

## 1. Introduction

Note 002 asked whether recent volatility predicts the *direction* of tomorrow's
return and found essentially nothing: a correlation of +0.035, indistinguishable
from zero. But a scatter of the data showed a distinctive *fan shape* — when
today was volatile, tomorrow's returns spread out more, both up and down. That
hints at a different, weaker-sounding but very real claim: volatility may predict
the **size** of the next move without predicting its **direction**.

This note tests exactly that. **Hypothesis (stated before running it):** recent
volatility *does* predict the size of the next day's move — high-volatility days
tend to be followed by larger moves (in either direction), and calm days by
smaller ones. This is the well-documented "volatility clustering" effect. A
clearly positive correlation between today's volatility and the *absolute value*
of tomorrow's return would support it; a correlation near zero would refute it.
Fixing the hypothesis in advance is a rule of this lab's
[methodology](../../METHODOLOGY.md).

Note the deliberate contrast with Note 002. Same data, same volatility measure —
the *only* change is that the thing we try to predict is `|return|` (size) rather
than `return` (direction). If 002 comes back ~0 and 003 comes back clearly
positive, that pair of results is itself the lesson: **volatility is about how
big moves are, not which way they go.**

## 2. Data & Method

**Data.** Daily closing prices for SPY (an ETF tracking the S&P 500) from
January 2015 to July 2026 — about 2,900 trading days — downloaded via `yfinance`.

**Returns.** Each day's return is `today's close / yesterday's close − 1`.

**Volatility.** For each day, the standard deviation of the trailing 20 daily
returns — the same measure used in Note 002. The first 19 days lack enough
history and are excluded.

**Move size.** The quantity we try to predict is `|return|` — the return with its
sign thrown away. A +1.2% day and a −1.2% day are the same "size." This is what
isolates *magnitude* from *direction*.

**The key step (no lookahead).** Each day's volatility — computed only from
returns *up to and including that day* — is paired with the *absolute* return on
the *next* day. Pairing with the same day's move would let the predictor see the
very move it is meant to forecast (lookahead bias, Note 001). Using tomorrow's
move keeps the test honest.

**Metrics.** Two, reported together:
1. The **Pearson correlation** between today's volatility and `|tomorrow's return|`.
2. A **bucket table**: sort all days low→high by today's volatility, split into 5
   equal groups, and report the average size of the *next* day's move in each. A
   rising staircase from bucket 1 to bucket 5 is a direct, assumption-free picture
   of volatility persistence.

## 3. Results

<!-- Fill from results.json after the real-data run. -->
- Paired days analyzed: **PENDING**
- Correlation (today's volatility → |tomorrow's return|): **PENDING**

| Today's volatility bucket (1 = calmest, 5 = stormiest) | Avg size of tomorrow's move |
|---|---|
| 1 | PENDING |
| 2 | PENDING |
| 3 | PENDING |
| 4 | PENDING |
| 5 | PENDING |

![Volatility today vs. size of tomorrow's move](figures/clustering.png)

<!-- One or two sentences on what the numbers show, once you have them. -->

## 4. Discussion

<!-- Fill in once you have the numbers. Points to hit:
- How large is the correlation vs. Note 002's +0.035? (expect much larger)
- The bucket staircase: how many times bigger is bucket 5's average move than
  bucket 1's? That ratio is the headline.
- The interpretation: this is volatility clustering / persistence. It does NOT
  give a directional edge (002 showed that), but it is exactly what options
  pricing and risk models rely on — you can forecast RISK even when you can't
  forecast RETURN.
- Tie the pair of notes together: direction is unpredictable, size is not. -->
**PENDING real-data run.**

## 5. Limitations

This study is deliberately narrow. It examines a single instrument (SPY), a
single volatility window (20 days), and a single historical period; a different
asset, window, or era could differ. `|return|` is one of several ways to measure
move size (squared returns and the high–low range are others) and could give a
different number. Pearson correlation captures only *linear* relationships. A
positive result would show volatility is *persistent*, not that this persistence
is large enough, after costs, to trade profitably — that is a separate question.
And correlation is not causation.

## 6. Conclusion

<!-- Restate the question and your honest one-paragraph answer once you have the
numbers. If the hypothesis holds: recent volatility does not tell you which way
the market goes tomorrow (Note 002), but it does tell you how *big* the move is
likely to be — turbulence clusters. -->
**PENDING real-data run.**

## References

- Cont, R. (2001). *Empirical properties of asset returns: stylized facts and
  statistical issues.* (Volatility clustering is stylized fact #2.)
- Mandelbrot, B. (1963). *The variation of certain speculative prices.* (The
  original observation that "large changes tend to be followed by large changes.")
- Neil Quant Labs, Research Note 002 — *Does Volatility Predict Next-Day Returns?*

---

## How to cite

> Gilani, N. (2026). *Does Volatility Predict the Size of the Next-Day Move?* Neil Quant Labs, Research Note 003. https://github.com/hilothefunnydog123-coder/quant-research

© 2026 Neil Gilani. Code: MIT License. Text, figures, and findings: CC BY 4.0 (reuse with attribution).
