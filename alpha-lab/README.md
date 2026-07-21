# Alpha Lab — an honest hunt for a real edge

Notes 001–004 spent their time showing what *doesn't* work: lookahead-inflated
backtests, volatility as a direction signal, momentum and mean-reversion after
costs, fair value gaps and liquidity grabs. This is the other half of the job —
systematically looking for something that *does*, and being just as honest when
it doesn't.

## The premise

You cannot predict the **direction** of returns on a liquid index; four notes now
say so. But you can predict **risk**: volatility is persistent (Note 002/003), and
the worst losses cluster in high-volatility, below-trend regimes. So the search
starts where an edge can actually exist — not in forecasting returns, but in
*sizing* exposure to risk. The candidates here scale down when volatility rises
and step aside in downtrends. Their rationale is economic and non-arbitrageable:
they don't claim free money, they claim better risk-adjusted returns.

## The candidates

| Strategy | Idea | Reference |
|---|---|---|
| Buy & Hold | the benchmark | — |
| **Volatility Targeting** | scale exposure to hold volatility roughly constant | Moreira & Muir (2017) |
| **Defensive Trend (200d)** | invested above the 200-day average, cash below | Faber (2007) |
| **Vol-Managed Trend** | the two combined — take risk only in uptrends, sized by vol | — |
| **Momentum 12-1** | long if the past year (skipping last month) was up | Jegadeesh & Titman (1993) |

## The rules that make it honest

- **No lookahead.** Every strategy is a pure function of *past* prices; the
  harness ([`harness.py`](harness.py)) hands them one day at a time and this is
  tested ([`test_harness.py`](test_harness.py)).
- **Out-of-sample split.** Metrics are reported on the full history *and* on an
  untouched last-40% tail. A strategy that looks great in-sample and falls apart
  out-of-sample is overfit, and the gap makes it obvious.
- **Fixed, conventional parameters.** 20-day vol window, 15% vol target, 200-day
  trend, 12-1 momentum — set a priori, not tuned, so the out-of-sample test isn't
  quietly rigged.
- **Costs.** 1 bp per unit of turnover, charged on every position change.
- **Risk-adjusted, not raw.** Ranking is by Sharpe and drawdown, not headline
  return — leverage can fake return, but not risk-adjusted return.

## Run it

```bash
python hunt.py     # fetches real SPY (Yahoo/stooq), falls back to a labelled sample
```

It prints a leaderboard and writes [`results.json`](results.json). A candidate is
flagged a survivor only if it beats buy & hold on **out-of-sample** Sharpe. Some
runs end with *"nothing clears buy & hold — an honest null"*, and that is a
perfectly good result to publish.

## What happens to a survivor

Anything that genuinely survives here is a candidate for the
[Out-of-Sample Registry](../registry/): locked at today's date and tracked
forward on data it has never seen. Surviving a backtest is a hypothesis;
surviving the registry is the proof.

---

Part of [Neil Quant Labs](../). Code: MIT. Text: CC BY 4.0.
