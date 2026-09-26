# Pre-registration addendum — Research Note 007

**Filed:** 2026-09-26, after the pre-registered analysis ran and **before any data for
the holdout contracts below was downloaded.**

## What had been seen when this was written

Everything in the original plan (commit `377bf67`) had run on the 62 discovery
contracts: H1–H6, the robustness list, the capture P&L, and the event-time path
figure. In summary: the instantaneous jump prices ~6% of funding (β = 0.060);
the placebo is flat; the natural experiment and the |F| gradient go the predicted
way; H5 and H6 failed. The path figure showed that for large |F| the basis
**drifts against the payer for the hour before settlement, reprices sharply in the
minute after the stamp, and keeps moving in the direction of funding for the next
hour.** Also seen: 24.5% of instantaneous premium-index changes are exactly zero,
which makes the pre-registered median regression uninformative.

## Why an addendum

The original plan assumed that funding is settled at an instant. Binance's
documentation, checked only after the paths were seen, says otherwise: the funding
transfer has "a 1-minute deviation", positions within a "~15-second deviation window"
of the stamp may or may not be counted, and "the system may require up to 1 min to
complete all funding fee settlement". A 5-second window cannot see a repricing that
the settlement mechanism itself spreads over a minute. The original results stand
as filed and will be reported as filed. The window-based questions below are
**exploratory**: they were chosen after looking at the paths, so the discovery
contracts cannot test them. Only the holdout can.

## Holdout (untouched when this was filed)

Every Binance USDT-margined perpetual whose funding history begins in 2021 and
continues through 2026-08 — **34 contracts**, listed in `holdout_universe.txt`, with
no overlap with the 62 discovery contracts. Same archive, same pipeline, same period
rule, extracted after this file is pushed.

## Windows (1-minute bar closes; premium index sampled every 5 s)

- **W, settlement window:** close of bar T−2 (≈ T−65 s) → close of bar T+1
  (≈ T+115 s). Starts before the ±15 s deviation window and ends after the stated
  one-minute settlement, so a trader holding across W is sure to be on the books.
- **PRE:** close of bar T−61 (≈ T−60 m) → close of bar T−2.
- **POST:** close of bar T+1 → close of bar T+59 (≈ T+60 m).

Events: hour marks at 00/04/08/12/16/20 UTC with complete paths, as in the
original descriptive analysis. Settlement status and F as in the original plan.

## Exploratory hypotheses, tested on the holdout only

- **E1.** The settlement-window change in the premium index loads positively on F
  (β_W > 0), and β_W exceeds the instantaneous β from the original H1 measure.
- **E2.** β_PRE < 0: the basis moves against the payers before settlement.
- **E3.** β_POST > 0: the basis keeps moving with funding after settlement.
- **E4.** The settlement-minus-placebo difference has the predicted sign for each of
  W (+), PRE (−) and POST (+).
- **E5.** Binance **spot** log-returns (not examined in either sample) show the same
  pattern: PRE slope < 0, W slope > 0, POST slope > 0 — the funding schedule moving
  the underlying market, not only the basis.

Each test is OLS with standard errors clustered by timestamp; a hypothesis is
confirmed only if the predicted sign holds with p < 0.05 after a Holm correction
across E1–E5. The discovery-sample estimates of the same quantities are reported
alongside, as estimates rather than tests.

## Descriptive

The capture available to a trader who must hold across W: `|F| − sign(F)·ΔPI_W`,
net of 4 and 10 bp round-trip costs, in both samples.
