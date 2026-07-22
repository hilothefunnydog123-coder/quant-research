"""Buy and hold — the benchmark every other entry is measured against.

Being long the index has been very hard to beat after costs; it is here as the
reference line, not as a contender.
"""

NAME = "Buy & Hold"
AUTHOR = "Martingale"
KIND = "baseline"
LOCKED_AS_OF = "2022-01-01"
HYPOTHESIS = "Hold the index. Do nothing. This is the bar."


def position(history: list[float]) -> float:
    """Always fully long, regardless of history."""
    return 1.0
