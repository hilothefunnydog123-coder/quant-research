# Research Note 003 — Momentum vs. Mean Reversion, Across Regimes, After Costs

> **Status: complete.** Run on 4,916 days of real SPY data (2007–2026). Finding:
> **neither strategy beats buy-and-hold after costs** (Sharpe 0.63), but each is a
> regime bet — momentum leads in bull markets, mean reversion earns an after-cost
> Sharpe of **1.07** in bear markets before its ~6× turnover lets costs erase it.
> See [`paper/paper.md`](paper/paper.md).

**The question:** Two of the oldest ideas in trading disagree. **Momentum** says
what's been going up keeps going up (bet on continuation). **Mean reversion** says
what's gone up comes back down (bet on reversal). They can't both be right all the
time — so *when* does each work, does it survive **realistic trading costs**, and
does the answer change between calm bull markets and falling bear markets?

**Hypothesis (stated before running it):** momentum tends to work in trending
**bull** regimes and mean reversion in choppy **bear** regimes; and mean
reversion, because it trades far more often, loses much more of its edge to costs.
We test all of this and report whatever the data actually says.

## What the engine does

- **Momentum signal** — long if the trailing 20-day return is positive, else short.
- **Mean-reversion signal** — long if *yesterday* fell, else short (bet the last move reverses).
- **Regimes** — each day is *bull* (price ≥ its 200-day average) or *bear* (below).
- **Costs** — a per-trade cost charged on how much the position changes; reported at
  0 / 1 / 5 bps, alongside each strategy's **turnover** (how often it trades).
- **No lookahead** — every position uses only data up to day *t* and is applied to
  day *t+1*'s return (the Note 001 rule), and this is checked in the self-tests.
- Everything is benchmarked against **buy & hold**.

The engine is validated on synthetic data with known structure: on trending data
momentum wins, on mean-reverting data reversion wins, costs always lower net
Sharpe, and reversion's turnover is far higher — so the code attributes edges to
the right strategy and never peeks ahead.

## How I'm working on it

1. Open [Google Colab](https://colab.research.google.com). Cell 1: `!pip install yfinance matplotlib numpy`.
2. Paste [`experiment.py`](experiment.py) and run it on real SPY data.
3. Read off the Sharpe table, the regime split, the cost-sensitivity rows, and the chart.
4. Put those real numbers into [`paper/paper.md`](paper/paper.md) and write the finding honestly.
5. Commit and push the finished note.

## Reproduce

```bash
pip install yfinance matplotlib numpy
python experiment.py     # loads real SPY data, prints the tables, saves the chart
```
