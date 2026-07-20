# Does Volatility Predict Next-Day Returns?

**Neil Quant Labs · Research Note 002** *(DRAFT — analysis in progress)*
*Author: Neil Gilani · Reproducible code: [`experiment.py`](../experiment.py)*

> ✍️ **This is your paper to write.** The scaffold below gives you the section
> structure (the same shape as Note 001). Fill in each `[…]` with your own
> words and your own numbers *after* you run the experiment. Delete these
> quote-blocks as you go.

## Abstract

> ✍️ Write this LAST. 3–4 sentences: the question, what you did, the single
> most important number you found, and what it means. Example shape: "We test
> whether … on N days of SPY data. We find a correlation of […], meaning …."

[YOUR ABSTRACT]

## 1. Introduction

> ✍️ Why does this question matter? A common belief is that volatile markets
> behave differently the next day. State the belief, and state your hypothesis
> *before* you look — e.g. "H: higher volatility today predicts lower/higher/no
> different returns tomorrow." Writing the hypothesis first is the rule from
> Note 001's methodology.

[YOUR INTRODUCTION + HYPOTHESIS]

## 2. Data & Method

> ✍️ Fill in the real details once you run it:
> - **Data:** SPY daily closes from [start date] to [end date], [N] trading
>   days (real market data via yfinance).
> - **Volatility:** standard deviation of the trailing [20] daily returns.
> - **The key step (no lookahead):** each day's volatility is paired with the
>   *next* day's return — explain, in your own words, why pairing it with the
>   *same* day's return would be cheating (this is Note 001's lesson in action).
> - **Metric:** Pearson correlation between today's volatility and tomorrow's
>   return.

[YOUR METHOD]

## 3. Results

> ✍️ Paste your real numbers from running `experiment.py`.

- Data points analyzed: **[N]**
- Correlation (today's volatility → tomorrow's return): **[r value]**

![Volatility today vs. return tomorrow](figures/scatter.png)

> ✍️ Describe the chart. Is the yellow best-fit line flat (no relationship),
> sloping up, or sloping down? Does the correlation count as strong (|r| near
> 1), weak (near 0), or in between?

[YOUR DESCRIPTION OF THE RESULTS]

## 4. Discussion

> ✍️ What does your number actually mean? If the correlation is near zero, that
> is a real and valuable finding — it says today's volatility does *not* predict
> tomorrow's direction (which connects to Note 001: no free prediction). If it's
> not zero, be careful and skeptical: could it be luck? Would it survive on a
> different stock or time period?

[YOUR DISCUSSION]

## 5. Limitations

> ✍️ Be honest about what this does NOT show. Ideas: single stock (SPY),
> single volatility window (20 days), correlation ≠ causation, predicting
> *direction* vs *size* of the move, one time period.

[YOUR LIMITATIONS]

## 6. Conclusion

> ✍️ One paragraph: restate the question and your honest answer.

[YOUR CONCLUSION]

---

## How to cite

> Gilani, N. (2026). *Does Volatility Predict Next-Day Returns?* Neil Quant Labs, Research Note 002. https://github.com/hilothefunnydog123-coder/quant-research

© 2026 Neil Gilani. Code: MIT License. Text, figures, and findings: CC BY 4.0 (reuse with attribution).
