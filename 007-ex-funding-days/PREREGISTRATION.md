# Pre-registration — Research Note 007: Ex-Funding Days

**Filed:** 2026-09-26, before any outcome variable was loaded.
**Author:** Neil Gilani (Martingale)

The only data examined before filing were (a) file coverage in the Binance public
archive and (b) the funding rates themselves — the *treatment* variable. No premium
index, trade price, or order-flow series (the *outcomes*) had been downloaded or
examined. This file is committed and pushed before the analysis code runs, so the
repository history timestamps the plan against the results. Any deviation from it
will be listed in the paper under "Deviations from pre-registration".

## 1. Question

Perpetual futures pay **funding** at fixed, pre-announced timestamps: at each
settlement *T*, holders of a long position pay *F* × notional to holders of a short
(*F* < 0 reverses the direction). The payment applies only to positions open at *T*.

In a frictionless market, a position opened just before *T* and closed just after
must earn zero. A long that holds through *T* pays *F*, so the perpetual's price
relative to the underlying must rise by *F* across the settlement instant:

    J_T  ≡  basis(T+) − basis(T−)  =  F_T          (frictionless benchmark)

This is the perpetual-futures analogue of the **ex-dividend price drop** (Elton &
Gruber, 1970), with the payment's sign reversed from the long's point of view, both
signs occurring, and the event repeating every few hours. With a round-trip trading
cost *c*, no-arbitrage only requires |J − F| ≤ c.

**Question:** by how much does the basis actually jump at settlement, as a fraction
of the funding payment?

## 2. Data

- **Universe (fixed by an outcome-blind rule):** every Binance USDⓈ-M perpetual
  quoted in USDT whose funding history begins no later than 2020-12 and continues
  through 2026-08 — **62 contracts**, listed in `universe.txt`.
- **Sample:** every funding settlement for those contracts, 2020-01-01 to
  2026-08-31 (438,155 events), from `data/futures/um/monthly/fundingRate`.
- **Outcomes (1-minute bars from the same archive):** `premiumIndexKlines`
  (perpetual vs. index basis, sampled every 5 s), perpetual `klines` (traded
  prices and taker volume), spot `klines` for the same symbol.
- **Not used as an outcome:** the mark price. Binance's mark-price formula
  mechanically embeds a funding term that decays to zero at settlement, so it
  would manufacture a jump by construction.

## 3. Variables

- **F_T** — the funding rate paid at settlement *T* (`last_funding_rate`), in bp.
- **Primary outcome J_T** — premium index at the first 5-second sample at or after
  *T*, minus the last sample before *T*: `PI_open(bar T) − PI_close(bar T−1)`, in bp.
- **Traded-price outcome J_T^trade** — perpetual log gap across *T* minus spot log gap
  across *T*: `[ln P_open(T) − ln P_close(T−1)] − [ln S_open(T) − ln S_close(T−1)]`.
- **Order-flow imbalance** — (taker-buy − taker-sell) / total perpetual volume, in
  `[T−15m, T)` and `[T, T+15m)`.
- **Placebo events** — every hour mark *h* that is *not* a settlement for that
  contract at that time, assigned the *F* of the next settlement after *h*.

## 4. Hypotheses and tests

**H1 (primary).** At settlement, the basis jumps in the direction of funding:
`J_T = α + β·F_T + ε`, pooled over all 62 contracts. **Test: β > 0.** β is also
tested against the frictionless value **β = 1**. Standard errors clustered by
settlement timestamp (every contract settles at the same instant, so events are
cross-sectionally correlated). Two-sided, α = 0.05.

Interpretation fixed in advance:
- β significantly > 0 and not significantly different from 1 → **full adjustment**
- β significantly in (0, 1) → **partial adjustment**; 1 − β is the share of funding a
  harvester keeps
- β not significantly > 0 → **no adjustment** — a known cash flow left unpriced
- β significantly > 1 → **over-adjustment**

**H2 (placebo).** The same regression at non-settlement hour marks gives β ≈ 0, and
the settlement β exceeds the placebo β (pooled regression with an F × settlement
interaction).

**H3 (natural experiment).** For contracts whose funding interval changed (32
switches across 14 contracts), clock hours that become settlement times after a
switch show the jump only once they are settlements. Estimated by comparing β at
those clock hours in the regime where they settle versus the regime where they do not.

**H4 (arbitrage band).** The share of funding priced at settlement rises with |F|:
β estimated separately for |F| bins `[0,1] bp`, `(1,5] bp`, `(5,10] bp`, `>10 bp`.
Predicted: non-decreasing in |F|.

**H5 (mechanism).** Order-flow imbalance in `[T−15m, T)` is decreasing in F (payers
exit and receivers enter before the timestamp), and in `[T, T+15m)` increasing in F.

**H6 (traded prices and spot).** `J_T^trade` gives the same sign and significance as
the premium-index β, and the spot gap alone does not load on F.

H2–H6 are secondary; their p-values are Holm-corrected as a family of five.

## 5. Robustness and stability (fixed in advance)

- The primary β is reported for the full sample and separately for **2020–2024** and
  **2025–2026**. A result is called robust only if both periods agree in sign and
  significance.
- Two-way clustering (timestamp and contract); median regression; 1% winsorised
  outcome; BTC and ETH alone; excluding events at the +1 bp baseline.
- Data rule: an event is dropped if either bar adjacent to *T* is missing. The count
  of dropped events is reported.

## 6. Descriptive, not tested

- The event-time path of the basis from T−60m to T+60m, averaged by F bin — to show
  *where* adjustment happens (before, at, or after *T*).
- The funding-capture P&L of the receiving side, `F − J`, net of 2, 4 and 10 bp
  round-trip costs — to judge whether any unpriced funding is actually harvestable.

## 7. What each outcome would mean

Every outcome is informative, which is the point of filing this first. Full
adjustment is a clean confirmation of no-arbitrage at a 5-second horizon. Partial or
no adjustment is an anomaly: a scheduled, publicly known cash flow that prices fail to
reflect, whose size is the upper bound on what harvesting earns before costs.
