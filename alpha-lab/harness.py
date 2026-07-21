#!/usr/bin/env python3
"""Edge-hunt harness — an honest out-of-sample evaluator.

A strategy here is a function that, given closing prices up to and including
today, returns the position to hold tomorrow (0 = cash, 1 = fully invested, >1 =
levered, <0 = short). The harness walks it forward one day at a time — so it can
never see the future — charges trading costs, and reports risk-adjusted metrics
both on the full history and, separately, on a held-out out-of-sample tail that
no parameter was ever tuned on.

The point is not to make a strategy look good. It is to find out whether one is
actually better than doing nothing (buy & hold), and to make overfitting show up
as the gap between in-sample and out-of-sample results.
"""
from __future__ import annotations

import math

TRADING_DAYS = 252
OOS_FRACTION = 0.40          # last 40% of history is the untouched out-of-sample tail
COST_PER_TURNOVER = 0.0001   # 1 bp charged on |change in position|


def daily_returns(closes: list[float]) -> list[float]:
    return [closes[i] / closes[i - 1] - 1 for i in range(1, len(closes))]


# --------------------------------------------------------------------------- #
# Metrics (all take a stream of daily returns)
# --------------------------------------------------------------------------- #
def _mean(xs): return sum(xs) / len(xs) if xs else 0.0


def _std(xs):
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def ann_return(daily):
    if not daily:
        return 0.0
    growth = 1.0
    for r in daily:
        growth *= (1 + r)
    return growth ** (TRADING_DAYS / len(daily)) - 1


def ann_vol(daily):
    return _std(daily) * math.sqrt(TRADING_DAYS)


def sharpe(daily):
    sd = _std(daily)
    return 0.0 if sd == 0 else _mean(daily) / sd * math.sqrt(TRADING_DAYS)


def sortino(daily):
    downside = [min(r, 0.0) for r in daily]
    dd = math.sqrt(_mean([d * d for d in downside]))
    return 0.0 if dd == 0 else _mean(daily) / dd * math.sqrt(TRADING_DAYS)


def max_drawdown(daily):
    equity, peak, worst = 1.0, 1.0, 0.0
    for r in daily:
        equity *= (1 + r)
        peak = max(peak, equity)
        worst = min(worst, equity / peak - 1)
    return worst


def calmar(daily):
    mdd = max_drawdown(daily)
    return 0.0 if mdd == 0 else ann_return(daily) / abs(mdd)


def metrics(daily):
    return {
        "ann_return": ann_return(daily),
        "ann_vol": ann_vol(daily),
        "sharpe": sharpe(daily),
        "sortino": sortino(daily),
        "max_drawdown": max_drawdown(daily),
        "calmar": calmar(daily),
    }


# --------------------------------------------------------------------------- #
# Evaluation
# --------------------------------------------------------------------------- #
def run(strategy, closes, max_leverage=1.5, cost=COST_PER_TURNOVER):
    """Walk `strategy` forward over `closes`, returning its after-cost daily
    return stream, its average daily turnover, and average exposure. The strategy
    is handed only past prices, and its position is clipped to [-max_leverage,
    max_leverage]."""
    stream, turns, exposures, prev = [], [], [], 0.0
    for t in range(len(closes) - 1):
        pos = float(strategy(closes[: t + 1]))
        pos = max(-max_leverage, min(max_leverage, pos))
        ret = closes[t + 1] / closes[t] - 1
        turn = abs(pos - prev)
        stream.append(pos * ret - cost * turn)
        turns.append(turn)
        exposures.append(pos)
        prev = pos
    return {
        "daily": stream,
        "turnover": _mean(turns),
        "avg_exposure": _mean(exposures),
    }


def evaluate(strategy, closes, **kw):
    """Full-sample and out-of-sample metrics for one strategy. The OOS tail is the
    last OOS_FRACTION of days; a large gap between full and OOS is the fingerprint
    of overfitting."""
    result = run(strategy, closes, **kw)
    daily = result["daily"]
    split = int(len(daily) * (1 - OOS_FRACTION))
    full = metrics(daily)
    oos = metrics(daily[split:])
    return {"full": full, "oos": oos, "turnover": result["turnover"],
            "avg_exposure": result["avg_exposure"], "daily": daily,
            "oos_split_index": split, "n_days": len(daily)}
