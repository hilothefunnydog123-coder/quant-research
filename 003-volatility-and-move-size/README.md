# Research Note 003 — Does Volatility Predict the *Size* of the Next-Day Move? 🚧

> **Status: analysis code complete; awaiting the real-data run.** The plumbing,
> the plot, and the paper skeleton are done. The **numbers and the finding come
> from the author running it on real SPY data** — that's the point of this note.

**The question:** Note 002 found today's volatility does *not* predict the
*direction* of tomorrow's return. This asks the companion question: does it
predict the **size** of tomorrow's move — how big the move is, regardless of
which way it goes? In other words, **is volatility persistent** (do stormy days
cluster together, and calm days too)?

**Hypothesis (stated before running it):** *yes.* Recent volatility should
predict the size of the next move even though it says nothing about direction —
the well-known "volatility clustering" effect. This is the mirror image of 002:
we expect a **clearly positive** correlation here, where 002 found ~zero.

## How I'm working on it

1. Open [Google Colab](https://colab.research.google.com) (free, no setup).
2. First cell: `!pip install yfinance matplotlib numpy` then run it.
3. Paste [`experiment.py`](experiment.py) into a cell and run it on real SPY data.
4. Read off the correlation, the 5-bucket table, and the chart it saves.
5. Drop those real numbers into [`paper/paper.md`](paper/paper.md) and write up
   what I actually found — honestly, whatever it is.
6. Commit and push the finished note.

## What the code does

- `pair_today_vol_with_tomorrow_size` — pairs today's 20-day volatility with the
  **absolute** value of tomorrow's return (`|return|` = size, direction removed).
  Uses *tomorrow's* move, never today's, to avoid lookahead (Note 001).
- `correlation` — Pearson correlation between today's vol and tomorrow's move size.
- `vol_buckets` — sorts days low→high by today's volatility into 5 equal buckets
  and reports the average size of the *next* day's move in each. If volatility is
  persistent, bucket 5 (stormiest today) should have much bigger moves tomorrow
  than bucket 1 (calmest today).

## Reproduce

```bash
pip install yfinance matplotlib numpy
python experiment.py     # loads real SPY data, prints correlation + buckets, saves the chart
```
