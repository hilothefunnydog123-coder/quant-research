# Methodology Standard

Every research note in this lab follows this checklist. It exists because the
easiest person to fool with a backtest is yourself, and these are the specific
ways it happens. (Note 001 measures how badly two of them distort results.)

## Before running anything

- [ ] **Write the hypothesis down first.** State what you expect and what would
      falsify it. A result you went looking for is not evidence.
- [ ] **Decide the success metric in advance** (e.g. out-of-sample Sharpe after
      costs), so you can't move the goalposts once you see the numbers.

## Designing the experiment

- [ ] **No lookahead.** A decision at time *t* may use only data through *t*, and
      earns the return *t → t+1*. Never credit a strategy a bar it has seen.
- [ ] **Train / test split.** Hold out data that is never touched during search
      or parameter tuning. Judge the strategy only on it.
- [ ] **Realistic frictions.** Charge transaction costs on turnover. High-turnover
      strategies must pay for it.
- [ ] **Control for multiple testing.** If you evaluate *N* strategies, the best
      one's in-sample performance is the expected maximum of *N* noise draws, not
      a discovery. Report *N*, and prefer out-of-sample confirmation.
- [ ] **Use an appropriate benchmark.** Beating zero is not the bar; beating
      buy-and-hold (or the relevant passive baseline) after costs is.

## Reporting

- [ ] **Reproducibility.** One seeded script regenerates every number and figure.
      Commit `results.json`.
- [ ] **Publish null and negative results.** "This doesn't work" is a valid,
      valuable conclusion and gets published the same as a positive one.
- [ ] **State limitations honestly** — data source, regime dependence, what the
      study does *not* show.
- [ ] **No overclaiming.** Simulation results are about the simulation until
      confirmed on real data; real-data results are about the sample studied.

## Data

- Simulated data (via [quantsim](https://github.com/hilothefunnydog123-coder/quantsim))
  is the right tool for studying *methodology* — it gives a known ground-truth
  edge. Real market data (via the data pipeline) is required for *market claims*.
  Every note states which it used and why.

## The one-sentence version

**Assume every edge is noise until the methodology has ruled that out.**
