# Research Note 002 — Does Volatility Predict Next-Day Returns? 🚧

> **Status: in progress.** The data pipeline, plotting, and paper skeleton are
> scaffolded. The **analysis and the finding are being written by the author**
> — that's the whole point of this note.

**The question:** does how volatile a stock has *been* (its recent price
bounciness) tell you anything about how it moves the *next* day?

## What's done vs. what's mine to write

| Part | Status |
|---|---|
| Load real SPY market data (yfinance) | ✅ scaffolded |
| Scatter-plot helper for the paper | ✅ scaffolded |
| Paper structure (`paper/paper.md`) | ✅ skeleton |
| `daily_returns`, `rolling_volatility`, alignment, `correlation` | ✍️ **mine to write** (`TODO(Neil)` in `experiment.py`) |
| The finding + interpretation | ✍️ **mine to write** |

## How I'm working on it

1. Open [Google Colab](https://colab.research.google.com) (free, no setup).
2. First cell: `!pip install yfinance matplotlib` then run it.
3. Copy the plumbing from [`experiment.py`](experiment.py) in, then fill in each
   `TODO(Neil)` function — one at a time, testing as I go.
4. Run it on real SPY data, read the correlation and the chart.
5. Write up what I actually found in [`paper/paper.md`](paper/paper.md) — honestly,
   whatever the answer is (a "no relationship" result is a real finding).
6. Commit and push the finished analysis.

## Reproduce (once finished)

```bash
pip install yfinance matplotlib numpy
python experiment.py     # loads real SPY data, prints the correlation, saves the chart
```
