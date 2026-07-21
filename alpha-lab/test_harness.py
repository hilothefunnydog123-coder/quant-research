#!/usr/bin/env python3
"""Tests for the edge-hunt harness. Run: python test_harness.py"""
import harness
import strategies


def test_no_lookahead():
    """The harness must hand each strategy only past prices."""
    closes = [100 + i * 0.5 for i in range(400)]
    seen = []

    def spy(history):
        seen.append(len(history))
        return 1.0

    harness.run(spy, closes)
    assert seen == list(range(1, len(closes))), "strategy saw non-past prices"
    assert max(seen) == len(closes) - 1, "strategy saw the final future price"
    print("ok  no-lookahead: strategies only ever receive past prices")


def test_buy_hold_equals_market():
    closes = [100 * 1.0003 ** i for i in range(500)]
    r = harness.evaluate(strategies.buy_hold, closes)
    mkt = harness.metrics(harness.daily_returns(closes))
    assert abs(r["full"]["ann_return"] - mkt["ann_return"]) < 0.002
    assert abs(r["avg_exposure"] - 1.0) < 1e-9
    print("ok  buy & hold reproduces the market it benchmarks")


def test_vol_target_cuts_vol():
    """On a series that switches between calm and wild regimes, vol targeting must
    deliver lower realized volatility than buy & hold."""
    import math
    import random
    rng = random.Random(0)
    closes, price = [], 100.0
    for i in range(1500):
        sigma = 0.03 if (i // 100) % 2 else 0.007      # alternating vol regimes
        price *= math.exp(rng.gauss(0.0002, sigma))
        closes.append(price)
    vt = harness.evaluate(strategies.vol_target, closes)
    bh = harness.evaluate(strategies.buy_hold, closes)
    assert vt["full"]["ann_vol"] < bh["full"]["ann_vol"], "vol targeting should reduce vol"
    print("ok  volatility targeting reduces realized volatility as intended")


def test_metrics():
    assert harness.sharpe([0.0] * 50) == 0.0
    assert harness.max_drawdown([-0.01] * 30) < -0.20
    assert harness.ann_return([0.0] * 100) == 0.0
    print("ok  metrics behave correctly")


if __name__ == "__main__":
    test_no_lookahead()
    test_buy_hold_equals_market()
    test_vol_target_cuts_vol()
    test_metrics()
    print("\nall tests passed")
