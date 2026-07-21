#!/usr/bin/env python3
"""Tests for the scoring engine. Run: python test_score.py

These check the two properties the whole registry rests on: that a strategy can
never see the future, and that the metrics are computed correctly.
"""
import score


def test_no_lookahead():
    """Every call to position() must receive only prices up to that day — never
    more. We record the longest history any call sees and assert it never exceeds
    the current day index."""
    dates = [f"2020-01-{i+1:02d}" for i in range(28)] + \
            [f"2020-02-{i+1:02d}" for i in range(28)]
    closes = [100 + i for i in range(len(dates))]
    seen = []

    class Spy:
        NAME, AUTHOR, LOCKED_AS_OF = "spy", "t", "2020-01-15"

        @staticmethod
        def position(history):
            seen.append(len(history))
            return 0.0
    Spy._file = "spy.py"

    row = score.evaluate(Spy, dates, closes)
    start = next(i for i, d in enumerate(dates) if d > "2020-01-15")
    # the k-th scored day is index start+k, so history length must be start+k+1
    expected = [start + k + 1 for k in range(len(seen))]
    assert seen == expected, "strategy saw a different amount of history than the past"
    assert max(seen) <= len(closes) - 1, "strategy saw the final (future) price"
    print("ok  no-lookahead: position() only ever receives past prices")


def test_buy_and_hold_matches_benchmark():
    dates = [f"d{i:04d}" for i in range(300)]
    closes = [100 * 1.0004 ** i for i in range(300)]

    class BH:
        NAME, AUTHOR, LOCKED_AS_OF = "bh", "t", "d0000"

        @staticmethod
        def position(history):
            return 1.0
    BH._file = "buy_and_hold.py"

    row = score.evaluate(BH, dates, closes)
    # identical to benchmark except a one-off cost to establish the first position
    assert abs(row["oos_return"] - row["benchmark_return"]) < 0.001
    assert row["sharpe"] > 0
    print("ok  buy & hold tracks the benchmark it defines")


def test_metrics():
    # a flat return stream: zero sharpe, zero drawdown, zero return
    assert score.annualized_sharpe([0.0] * 50) == 0.0
    assert score.total_return([0.0] * 50) == 0.0
    assert score.max_drawdown([0.0] * 50) == 0.0
    # a steady loser draws down monotonically
    assert score.max_drawdown([-0.01] * 20) < -0.15
    # sharpe of a constant positive drift with no variance guards against /0
    assert score.annualized_sharpe([0.001, 0.001, 0.001]) == 0.0
    print("ok  metrics: sharpe, drawdown, total return behave correctly")


if __name__ == "__main__":
    test_no_lookahead()
    test_buy_and_hold_matches_benchmark()
    test_metrics()
    print("\nall tests passed")
