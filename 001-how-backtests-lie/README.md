# Research Note 001 — How Backtests Lie

> Quantifying **lookahead bias** and **data snooping**, the two most common ways
> a trading backtest overstates performance.

📄 **[Read the paper (PDF)](paper/paper.pdf)** · 🔁 fully reproducible below

## TL;DR

On data engineered so that **no edge exists**, two ordinary mistakes manufacture
the appearance of alpha:

- **Lookahead bias** — a one-bar, single-line off-by-one inflates a momentum
  strategy's annualized Sharpe from **0.12 → 1.24** (+1.12). It corrupts mean
  reversion in the opposite direction (−2.25), proving the bug distorts rather
  than uniformly inflates.
- **Data snooping** — evaluating **337 strategies** on a random walk and keeping
  the best gives an in-sample Sharpe of **0.77** that collapses to **−0.54** out
  of sample.

Neither is visible in the equity curve. The defense is methodological, not
visual.

![lookahead](paper/figures/lookahead.png)
![data snooping](paper/figures/snooping.png)

## Reproduce

```bash
pip install "git+https://github.com/hilothefunnydog123-coder/quantsim.git" matplotlib
python experiment.py          # -> results.json + paper/figures/*.png
python paper/build_pdf.py     # -> paper/paper.pdf  (needs: pip install markdown playwright)
```

All randomness is seeded; the numbers above reproduce exactly.

## Files

| File | What |
|---|---|
| `experiment.py` | Both experiments; emits `results.json` and the figures |
| `results.json` | Every number cited in the paper |
| `paper/paper.md` | The write-up (renders on GitHub) |
| `paper/paper.pdf` | Print-ready paper |
| `paper/build_pdf.py` | Rebuilds the PDF from the markdown |
