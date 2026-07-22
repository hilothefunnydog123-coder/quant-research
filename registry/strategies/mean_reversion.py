"""Short-term reversal — bet that the last move overshoots and snaps back.

Long after a down day, short after an up day. The mirror image of momentum at a
one-day horizon (Jegadeesh, 1990); included as a baseline because it trades
constantly, which makes it the clearest illustration on the board of how costs
punish turnover.
"""

NAME = "Mean Reversion (1d reversal)"
AUTHOR = "Martingale"
KIND = "baseline"
LOCKED_AS_OF = "2022-01-01"
HYPOTHESIS = "Yesterday's move reverses: buy after a down day, sell after an up day."


def position(history: list[float]) -> float:
    if len(history) < 2:
        return 0.0
    yesterday_return = history[-1] / history[-2] - 1
    return 1.0 if yesterday_return < 0 else -1.0
