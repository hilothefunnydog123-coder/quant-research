# Research Note 004 — Do Liquidity Grabs and Fair Value Gaps Have a Statistical Edge?

> **Status: complete.** Run on 2,903 days of real SPY (2015–2026). Finding: **no
> edge.** At 1 day nothing is significant; at 5 days the only "significant" results
> are just the market's drift — and the supposedly *bearish* patterns are followed
> by the *largest positive* moves, the opposite of the claim. FVGs "fill" 73–88% of
> the time, but bearish gaps fill *more*, which is what upward drift does, not a
> magnet. See [`paper/paper.pdf`](paper/paper.pdf).

**The question:** Two chart patterns anchor a huge amount of online trading
education — the **fair value gap** (a 3-candle price imbalance) and the
**liquidity grab** (a stop hunt that sweeps a recent high or low and reverses).
The claims made for them are large; the public testing is almost nonexistent.
This note gives each a precise, mechanical definition and asks the only question
that matters: **after the pattern appears, is the forward return different from
the market's baseline — or is it noise?**

**Hypothesis (stated before running it):** consistent with efficient markets and
with Notes 001–003, these patterns will show **no meaningful forward-return edge**
once defined precisely and measured honestly. A clearly non-zero, significant
conditional return would refute this.

## What the code does

- **Fair value gaps** — a bullish FVG is confirmed when candle 1's high is below
  candle 3's low (a gap the middle candle left); bearish is the mirror.
- **Liquidity grabs** — a bearish grab is a new 20-day high that *closes below the
  prior close* (swept, then rejected); bullish is a swept 20-day low that closes up.
- **The edge test** — for each event, the forward return over 1 and 5 days,
  compared to the market baseline, with a t-stat, a p-value, and a hit rate. No
  lookahead: every signal is confirmed at a day's close and returns start from there.
- **The "gaps always get filled" claim** — the fraction of FVGs price trades back
  into within 10 days, so the claim can be checked against how often price wanders
  back anyway.

Validated on synthetic data: detection matches hand-built cases, and on a pure
random walk the test correctly finds **no** significant edge (no false positives).

## How I'm working on it

1. Open [Google Colab](https://colab.research.google.com). Cell 1: `!pip install yfinance matplotlib numpy`.
2. Paste [`experiment.py`](experiment.py) and run it on real SPY data.
3. Read off the per-pattern table (mean forward return, t, p, hit rate), the fill
   rates, and the chart it saves.
4. Put those real numbers into [`paper/paper.md`](paper/paper.md) and write the
   finding honestly — whatever it is.

## Reproduce

```bash
pip install yfinance matplotlib numpy
python experiment.py     # loads real SPY OHLC, prints the stats, saves the chart
```
