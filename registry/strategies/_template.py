"""Template for a registry submission. Copy this file, rename it, fill it in.

The only thing the scoring engine asks of you is a `position` function. It is
called once per day with every closing price up to and including that day, and
must return the position you want to hold *the next day*, from -1 (fully short)
to +1 (fully long). You never receive a future price, so you cannot cheat even
if you want to.

Keep it deterministic and dependency-free (standard library only) so anyone can
reproduce your score exactly.
"""

NAME = "My Strategy"                 # shown on the board
AUTHOR = "Your Name"                 # your name or handle — the record is yours
KIND = "submission"                  # leave as "submission"
LOCKED_AS_OF = "2026-01-01"          # set to the date you open the PR; do not backdate
HYPOTHESIS = "State, in one sentence, what you believe and why — before the score exists."


def position(history: list[float]) -> float:
    """Return next-day position in [-1, 1] using only `history` (past closes).

    `history[-1]` is today's close; `history[-2]` was yesterday; and so on. Return
    0.0 while you lack the history you need.
    """
    if len(history) < 2:
        return 0.0
    # Example placeholder: hold long. Replace with your actual signal.
    return 1.0
