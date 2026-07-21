# Do Liquidity Grabs and Fair Value Gaps Have a Statistical Edge?

**Neil Quant Labs · Research Note 004**
*Author: Neil Gilani · Reproducible code: [`experiment.py`](../experiment.py)*

## Abstract

<!-- Write last, from results.json. Template:
Two chart patterns central to modern trading education — the fair value gap and
the liquidity grab — are tested on ~N days of SPY. Defining each mechanically and
measuring the forward return after every occurrence, we find [conditional means]
against a baseline of [X]%, with p-values of [...]. [Edge / no edge]. FVGs are
"filled" within 10 days [A]% / [B]% of the time — but so is [baseline], because
price wanders back regardless. Conclusion: [what the data says]. -->
**PENDING real-data run — fill in from `results.json`.**

## 1. Introduction

A large share of online trading education is built on two ideas. A **fair value
gap (FVG)** is a three-candle "imbalance" — a gap between the first candle's high
and the third candle's low — said to act as a magnet that price returns to and
respects. A **liquidity grab** (or stop hunt) is a move that pushes just past a
recent high or low, triggering stop orders, before reversing — said to mark where
"smart money" enters. Both are described with great confidence and tested almost
never.

This note tests them the way the rest of this lab tests everything: by fixing a
precise definition in advance and measuring what actually happens next.
**Hypothesis (stated before running it):** consistent with Notes 001–003 and with
the efficient-markets baseline, neither pattern will show a meaningful, significant
forward-return edge once defined mechanically. A clearly non-zero conditional
return, significant after honest accounting, would refute this.

## 2. Data & Method

**Data.** Daily OHLC (open, high, low, close) for SPY from January 2015, via
`yfinance`.

**Definitions (mechanical, no discretion).**
- **Bullish FVG:** confirmed at candle 3 when `high[1] < low[3]`. Bearish is the
  mirror (`low[1] > high[3]`).
- **Liquidity grab, highs (bearish):** a new 20-day high is printed intraday but
  the day closes below the prior close. **Lows (bullish):** a new 20-day low is
  swept but the day closes up.

**The edge test.** Every event is *confirmed at a day's close*, and the forward
return is measured from that close over 1 and 5 trading days — so there is no
lookahead. For each pattern we report the mean forward return, its standard error,
a *t*-statistic and two-sided *p*-value versus zero, and the hit rate (share of
positive outcomes), all against the market's unconditional baseline over the same
horizon. The 1-day horizon is the primary test because consecutive 1-day windows
barely overlap; the 5-day is secondary (overlapping windows inflate significance,
noted below).

**The "always filled" claim.** Separately, we report how often price trades back
into an FVG within 10 days — the popular claim that gaps always fill — so it can
be judged against how often price returns to any level anyway.

## 3. Results

<!-- Fill from results.json after the real-data run. -->

**1-day forward return (baseline: PENDING%):**

| Pattern | n | Mean fwd return | *t* | *p* | Hit rate |
|---|--:|--:|--:|--:|--:|
| Bullish FVG | PENDING | PENDING | | | |
| Bearish FVG | PENDING | PENDING | | | |
| Liquidity grab (highs) | PENDING | PENDING | | | |
| Liquidity grab (lows) | PENDING | PENDING | | | |

**5-day forward return:** PENDING.

**FVG fill rate within 10 days:** bullish PENDING%, bearish PENDING%.

![Edge test: forward return after each pattern vs baseline](figures/edge.png)

<!-- One or two sentences on what the numbers show. -->

## 4. Discussion

<!-- Fill in from the numbers. Points to hit:
- Are any conditional means significant at the 1-day horizon (p < 0.05)? By how
  much do they differ from baseline in basis points — is it even tradeable after
  the ~1bp+ costs from Note 003?
- If nothing is significant: state plainly that the patterns carry no directional
  edge on SPY, and connect to the multiple-testing lesson (we tested 4 patterns x
  2 horizons = 8 tests; at p<0.05 you'd expect ~0.4 false hits by luck alone).
- Fill rate: if FVGs "fill" 90%+ of the time, note that this is unremarkable —
  price on a low-volatility index revisits nearby levels constantly; compare to
  how often ANY recent level is revisited. A high fill rate is not evidence of a
  special force; it is what a near-random walk does.
- Be careful and fair: this tests SPY daily bars, not the intraday timeframes or
  instruments these methods are usually claimed on (a real limitation, section 5). -->
**PENDING real-data run.**

## 5. Limitations

This tests one instrument (SPY) on **daily** bars, while these patterns are most
often claimed on intraday timeframes (minutes to hours) and on futures or FX; a
daily-bar null result does not prove they fail intraday, only that the daily
version carries no edge here. The definitions are one reasonable mechanisation of
concepts that practitioners apply with discretion and additional context (trend,
session, confluence), which a mechanical test cannot capture — though that
discretion is also where hindsight and selection creep in. Testing four patterns
across two horizons is multiple testing, so any lone "significant" result must be
discounted accordingly. Forward returns at the 5-day horizon overlap across nearby
events, which overstates their significance. And, as always, correlation is not
causation.

## 6. Conclusion

<!-- Restate the question and the honest one-paragraph answer from the numbers.
If the hypothesis holds: precisely defined, measured without hindsight, and tested
against the right baseline, liquidity grabs and fair value gaps on daily SPY show
no forward-return edge — the patterns are real as descriptions of price, but not
as predictions of it. -->
**PENDING real-data run.**

## References

- Fama, E. (1970). *Efficient Capital Markets.*
- Harvey, C., Liu, Y. & Zhu, H. (2016). *…and the Cross-Section of Expected
  Returns.* (On how many "discovered" signals fail to replicate.)
- Neil Quant Labs, Research Notes 001–003.

---

## How to cite

> Gilani, N. (2026). *Do Liquidity Grabs and Fair Value Gaps Have a Statistical Edge?* Neil Quant Labs, Research Note 004. https://github.com/hilothefunnydog123-coder/quant-research

© 2026 Neil Gilani. Code: MIT License. Text, figures, and findings: CC BY 4.0 (reuse with attribution).
