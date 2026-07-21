"""Moving-average crossover — the canonical trend-following rule.

Long when the short average is above the long average (an uptrend), short when
it is below. A textbook strategy, included as a baseline so the board has a
familiar reference point that most retail traders have tried.
"""

NAME = "SMA Crossover (20/100)"
AUTHOR = "Neil Quant Labs"
KIND = "baseline"
LOCKED_AS_OF = "2022-01-01"
HYPOTHESIS = "When the 20-day average is above the 100-day average, the trend continues."

FAST, SLOW = 20, 100


def position(history: list[float]) -> float:
    if len(history) < SLOW:
        return 0.0
    fast = sum(history[-FAST:]) / FAST
    slow = sum(history[-SLOW:]) / SLOW
    return 1.0 if fast > slow else -1.0
