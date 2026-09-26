# Research Note 007 — Ex-Funding Days: How Perpetual Futures Price a Scheduled Payment

> **Status: complete, pre-registered, and replicated on a holdout.**
> Perpetual futures pay funding at fixed timestamps, so frictionless no-arbitrage
> requires the basis to jump by the funding rate at settlement: the ex-dividend
> drop, mirrored. On 431,752 Binance settlements across 62 contracts, **the basis
> prices only 6% of the payment at the timestamp** (frictionless value rejected at
> *t* = −105). The reason is that Binance settles over a window of up to a minute,
> so there is no instant to price. **Across that window the basis reprices 45% of
> the payment, after drifting 42% the other way in the hour before.** Filed before
> the holdout was downloaded, both numbers replicated on 34 unseen contracts
> (0.449 and −0.422). The perpetual's price reprices by about the full payment,
> and **Binance spot moves by about half of it**, so a derivative's payment
> schedule moves the underlying. Post-settlement predictions failed and are
> reported. See [`paper/paper.pdf`](paper/paper.pdf).

## The question

At each funding settlement, perpetual-futures longs pay shorts *F* × notional (or
the reverse when *F* < 0), but only positions open at that moment are charged. A
trader who could short a second before a positive-funding settlement and buy back a
second after would collect *F* for free unless the price rises by *F* across the
timestamp. This is the ex-dividend question Elton and Gruber asked in 1970, in a
setting with both signs, tens of thousands of events, and no dividend tax wedge.
**How much of a known, scheduled payment does the market price, and when?**

## How it was done, in order

| Step | Commit | What happened |
|---|---|---|
| 1. Pre-registration | [`377bf67`](PREREGISTRATION.md) | Hypotheses, specification, placebo, natural experiment, and the meaning of every outcome fixed **before any price data was downloaded** |
| 2. Pre-registered analysis | — | Run once on the 62 discovery contracts ([`experiment.py`](experiment.py)) |
| 3. Addendum | [`e51757a`](PREREGISTRATION_ADDENDUM.md) | The event paths showed repricing *after* the stamp; Binance's docs confirmed a ~1-minute settlement. New window hypotheses filed **before the holdout was downloaded** |
| 4. Holdout test | — | Run once on 34 unseen contracts ([`holdout.py`](holdout.py)) |

## Headline results

| | Discovery (62 contracts) | Holdout (34 unseen) |
|---|--:|--:|
| Share of funding priced **at the timestamp** (pre-registered H1) | **0.060** | 0.146 |
| ...across the **settlement window** (≈3 min; addendum E1) | 0.444 | **0.449** ✅ |
| Basis drift in the **hour before**, against the payer (E2) | −0.420 | **−0.422** ✅ |
| Basis drift in the hour after (E3) | 0.122 | 0.029 ❌ |
| Perpetual price across the window | 1.14 | 0.95 |
| **Spot** price across the window | 0.66 | 0.44 |
| Share of large funding (\|*F*\| > 10 bp) kept by a spot-hedged harvester | 58.9% | 56.5% |

Also pre-registered: a **placebo** at non-settlement hours (β = 0.003) and a
**natural experiment**, in which the same clock hours go from β = 0.008 to 0.220
once a funding-interval change makes them settlement times. Failed as specified:
post-settlement order flow (H5), a traded-price version of the instantaneous test
(H6), and the post-settlement components of E3–E5.

## Files

- [`PREREGISTRATION.md`](PREREGISTRATION.md), [`PREREGISTRATION_ADDENDUM.md`](PREREGISTRATION_ADDENDUM.md): the two filed plans
- [`universe.txt`](universe.txt), [`holdout_universe.txt`](holdout_universe.txt): the contracts, each chosen by an outcome-blind rule
- [`pipeline.py`](pipeline.py): streams Binance's public archive and extracts every hour mark; knows nothing about funding
- [`experiment.py`](experiment.py): the pre-registered analysis → [`results.json`](results.json)
- [`holdout.py`](holdout.py): the addendum's tests and exploratory robustness → [`results_addendum.json`](results_addendum.json)

Both analysis scripts run self-tests on synthetic data with planted effects before
touching real data: they must recover a planted β, recover a settlement-minus-placebo
interaction, and find nothing in null data.

## Reproduce

```bash
pip install numpy pandas scipy statsmodels matplotlib pyarrow markdown
python pipeline.py                                                     # ~15 min
python pipeline.py --symbols "$(paste -sd, holdout_universe.txt)"      # ~7 min
python experiment.py         # pre-registered analysis
python holdout.py            # addendum tests
python paper/build_pdf.py
```

The pipeline streams about 20 GB from `data.binance.vision` and keeps about 1 GB of
extracted events in `data/`, which is not committed.

## What a journal version would need

This note is written to the standard of a paper, but four things stand between it
and a submission:

1. **Cross-venue evidence.** Bybit and OKX settle at the same instants, which tests
   whether the pattern is Binance's settlement mechanics or funding in general.
   Venues that accrue funding *continuously* (several decentralised exchanges) give
   a sharp prediction: **no V at all.** That contrast would be the paper's
   identification centrepiece.
2. **Trade-level timing.** One-minute bars cannot say where inside the settlement
   minute the repricing lands. Tick data can, and could tie the jump to the moment
   Binance actually posts the payment.
3. **A model.** Equilibrium pricing when the payment's timing is uncertain within a
   window, predicting the ~45% repricing and the size of the pre-settlement drift.
4. **Capacity.** The 56–59% harvestable share applies to large payments in thin
   markets; order-book depth is needed to say how much capital it can absorb.

Natural outlets: the *Journal of Futures Markets* or *Journal of Financial Markets*
for the full paper, or *Finance Research Letters* for a short version of the
current results.
