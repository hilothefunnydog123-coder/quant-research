"""Time-series momentum — bet that recent direction persists.

Long if the trailing 60-day return is positive, short otherwise. This is the
single-asset version of one of the most studied effects in finance (Moskowitz,
Ooi & Pedersen, 2012); included as a baseline to see whether it survives
out-of-sample on SPY after costs.
"""

NAME = "Time-Series Momentum (60d)"
AUTHOR = "Neil Quant Labs"
KIND = "baseline"
LOCKED_AS_OF = "2022-01-01"
HYPOTHESIS = "A positive trailing 60-day return predicts a positive next day."

LOOKBACK = 60


def position(history: list[float]) -> float:
    if len(history) < LOOKBACK + 1:
        return 0.0
    trailing = history[-1] / history[-(LOOKBACK + 1)] - 1
    return 1.0 if trailing > 0 else -1.0
