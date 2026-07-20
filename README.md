<div align="center">

# 🔬 Neil Quant Labs

**Monthly quantitative-finance research. A question, an experiment, an honest answer.**

*Every note: a reproducible experiment, a written paper, and results that stand on their own — including the null ones.*

</div>

---

## Why this exists

Most projects claim to *find* edges. This lab is built on the opposite instinct: **rigorously testing whether claimed edges are real**, and reporting what the data actually says — even when the answer is "it doesn't work." That skepticism is the entire point. A study that honestly concludes "momentum doesn't survive costs" is worth more than a dozen that claim to have beaten the market, because it's the one a serious reader believes.

## The standard (every note follows this)

See [`METHODOLOGY.md`](METHODOLOGY.md) for the full checklist. In short, every experiment must:

1. **State the hypothesis before running it** — no fishing for a result.
2. **Have no lookahead** — decisions use only past data; this is enforced in code and tested.
3. **Reserve out-of-sample data** never touched during search.
4. **Count attempts** — if 300 strategies were tried, correct for it (see Note 001 for why).
5. **Charge realistic costs.**
6. **Publish the null results** — a failed hypothesis is a finding, not a failure.
7. **Be reproducible** — one script regenerates every number and figure.

## Research notes

| # | Question | Finding | Paper |
|---|---|---|---|
| **001** | How do backtests overstate performance? | A 1-line lookahead bug inflates momentum's Sharpe by **+1.12**; cherry-picking 337 strategies on random data fakes a **0.77** Sharpe that goes **−0.54** out of sample | [📄 PDF](001-how-backtests-lie/paper/paper.pdf) · [code](001-how-backtests-lie/) |
| **002** | Does realized volatility predict next-day returns? | Across 2,881 days of SPY, today's volatility → tomorrow's return correlation is **+0.035** (R² ≈ 0.1%, p ≈ 0.06) — **no meaningful directional prediction** | [paper](002-volatility-and-next-day-returns/paper/paper.md) · [code](002-volatility-and-next-day-returns/) |
| 003 | *Momentum vs. mean reversion across regimes, after costs* | *planned* | — |
| 004 | *How effective are liquidity-grab / FVG setups, statistically?* | *planned* | — |

## The pipeline (one note per month)

```
pick a question  ──▶  form a hypothesis  ──▶  design the experiment
       ▲                                              │
       │                                              ▼
  LinkedIn post  ◀──  render the paper (PDF)  ◀──  run it, honestly
```

Each note is a self-contained folder: `experiment.py` (reproducible), `paper/paper.md` → `paper.pdf`, `results.json`, and a `README`.

## 🤝 Open to contributors

This is an **open research collective** — anyone can submit a quant research note, and it's published here under **your** name once it passes review. See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the submission flow, copy the **[`_template/`](_template/)** folder to start, and open a pull request. Have an idea but not a full note? Open a **[Discussion](../../discussions)** or an Issue. Every submission is peer-reviewed against the [methodology standard](METHODOLOGY.md).

## Reproduce any note

```bash
pip install "git+https://github.com/hilothefunnydog123-coder/quantsim.git" matplotlib
cd 001-how-backtests-lie && python experiment.py     # regenerates results + figures
python paper/build_pdf.py                            # rebuilds the PDF
```

## About

Independent quant research by **Neil Gilani** ([@hilothefunnydog123-coder](https://github.com/hilothefunnydog123-coder)), exploring market microstructure, strategy evaluation, and the statistics of trading — with an emphasis on methodology over hype. Built on [quantsim](https://github.com/hilothefunnydog123-coder/quantsim) and [exchange-simulator](https://github.com/hilothefunnydog123-coder/exchange-simulator).

## License & citation

© 2026 **Neil Gilani**. This work is dual-licensed so the terms fit what's being reused:

- **Code** (`experiment.py`, `build_pdf.py`, etc.) — [MIT License](LICENSE). Free to reuse, but the copyright notice must be kept.
- **Written research** (the papers, text, figures, and findings) — **[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)**. You may share and build on it, *but you must credit the author.*

If you reference this work, please cite it (GitHub's **"Cite this repository"** button uses [`CITATION.cff`](CITATION.cff)):

> Gilani, N. (2026). *Neil Quant Labs — Quantitative Finance Research.* https://github.com/hilothefunnydog123-coder/quant-research

*The commit history in this repository is a timestamped, public record of authorship.*
