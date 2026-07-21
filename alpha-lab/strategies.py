"""Candidate strategies for the edge hunt.

Each is a pure function of past closing prices returning a target position for
tomorrow. None tries to predict the *direction* of returns — Notes 002-004 showed
that road is a dead end. They exploit the one thing that genuinely is
predictable: **risk**. Volatility is persistent (Note 002/003), and the worst
crashes happen in high-volatility, below-trend regimes — so scaling exposure to
volatility and stepping aside in downtrends is risk management with a real,
non-arbitrageable rationale, not a return forecast.

Parameters are fixed here at conventional values, not tuned, so the out-of-sample
test in the harness means something.
"""
from __future__ import annotations

import math

VOL_LOOKBACK = 20        # trailing window for the realized-vol estimate
TARGET_VOL = 0.15        # annualized volatility we scale toward
TREND_MA = 200           # days in the trend filter
MOM_LOOKBACK = 252       # ~12 months
MOM_SKIP = 21            # skip the most recent month (classic 12-1 momentum)
TRADING_DAYS = 252


def _trailing_ann_vol(history, window=VOL_LOOKBACK):
    if len(history) < window + 1:
        return None
    rets = [history[i] / history[i - 1] - 1 for i in range(len(history) - window, len(history))]
    m = sum(rets) / len(rets)
    sd = math.sqrt(sum((r - m) ** 2 for r in rets) / (len(rets) - 1))
    return sd * math.sqrt(TRADING_DAYS)


def _sma(history, window):
    return sum(history[-window:]) / window if len(history) >= window else None


# --------------------------------------------------------------------------- #
# The benchmark
# --------------------------------------------------------------------------- #
def buy_hold(history):
    """Always fully invested. The bar to clear."""
    return 1.0


# --------------------------------------------------------------------------- #
# Candidate 1 — volatility targeting
# --------------------------------------------------------------------------- #
def vol_target(history):
    """Scale exposure inversely to recent volatility, aiming for a constant risk
    level. Lever up (a little) when calm, cut exposure when stormy. Because vol is
    persistent and crashes cluster in high-vol periods, this tends to sidestep the
    worst days. (Moreira & Muir, 2017, *Volatility-Managed Portfolios*.)"""
    vol = _trailing_ann_vol(history)
    if vol is None or vol == 0:
        return 1.0
    return TARGET_VOL / vol


# --------------------------------------------------------------------------- #
# Candidate 2 — defensive trend filter
# --------------------------------------------------------------------------- #
def defensive_trend(history):
    """Fully invested while price is above its 200-day average, in cash below it.
    Sacrifices some upside to avoid the deep, slow bear markets that live below
    trend. (Faber, 2007, *A Quantitative Approach to Tactical Asset Allocation*.)"""
    ma = _sma(history, TREND_MA)
    if ma is None:
        return 1.0
    return 1.0 if history[-1] > ma else 0.0


# --------------------------------------------------------------------------- #
# Candidate 3 — volatility-managed trend (the two ideas combined)
# --------------------------------------------------------------------------- #
def vol_managed_trend(history):
    """Only take risk when the trend is up, and size that risk by volatility."""
    ma = _sma(history, TREND_MA)
    if ma is None:
        return 1.0
    if history[-1] <= ma:
        return 0.0
    vol = _trailing_ann_vol(history)
    if vol is None or vol == 0:
        return 1.0
    return TARGET_VOL / vol


# --------------------------------------------------------------------------- #
# Candidate 4 — 12-1 time-series momentum (long / flat)
# --------------------------------------------------------------------------- #
def momentum_12_1(history):
    """Long if the return over the past year, skipping the most recent month, is
    positive; otherwise in cash. The single-asset, long/flat version of the most
    studied effect in finance."""
    if len(history) < MOM_LOOKBACK + 1:
        return 1.0
    past = history[-(MOM_LOOKBACK + 1)]
    recent = history[-(MOM_SKIP + 1)]
    return 1.0 if recent / past - 1 > 0 else 0.0


CANDIDATES = {
    "Buy & Hold": buy_hold,
    "Volatility Targeting": vol_target,
    "Defensive Trend (200d)": defensive_trend,
    "Vol-Managed Trend": vol_managed_trend,
    "Momentum 12-1": momentum_12_1,
}
