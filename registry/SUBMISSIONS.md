# Submitting a strategy

The registry scores strategies on data that did not exist when they were locked.
Submitting is deliberately simple; the discipline is in the rules, not the
paperwork.

## The contract

Your submission is a single Python file in `strategies/` that defines:

| Field | Meaning |
|---|---|
| `NAME` | Display name on the board. |
| `AUTHOR` | Your name or handle. The record is attributed to you. |
| `LOCKED_AS_OF` | An ISO date. **Set it to the day you open the pull request.** Scoring ignores every day on or before it. |
| `HYPOTHESIS` | One sentence: what you believe, stated before the score exists. |
| `position(history)` | The strategy. Given every close up to and including today, return the position to hold tomorrow, in `[-1, 1]`. |

Copy [`strategies/_template.py`](strategies/_template.py) to start.

## The rules

1. **No lookahead.** `position` only ever receives past prices; the harness
   guarantees this. Do not try to smuggle the future in by other means (reading
   files, network calls, wall-clock dates). Submissions must be pure functions of
   `history`.
2. **No backdating.** `LOCKED_AS_OF` is the day you submit. The entire point is
   that the score comes from data you had not seen. Backdated submissions are the
   one thing that breaks the registry, and they will be rejected.
3. **Deterministic and dependency-free.** Standard library only, no randomness
   without a fixed seed. Anyone must be able to reproduce your score to the
   decimal by running [`score.py`](score.py).
4. **Own your hypothesis.** State it plainly. A strategy that fades out-of-sample
   is not a failure — an honest negative result is exactly what this registry
   exists to record, and it stays on the board.

## What happens after you open the PR

- A maintainer checks the file follows the contract and that the lock date is
  today, then merges.
- On the next scoring run your strategy appears on the board with a lengthening
  out-of-sample window. Early on it has too few days to mean anything; that is
  honest, and the board says so.
- Its record — locked date, hypothesis, and everything the strategy did afterward
  — is public, timestamped in git, and yours to cite.

## Scoring, precisely

For each day *t* after the lock date, the harness calls `position(closes[:t+1])`,
clips the result to `[-1, 1]`, applies it to the return from *t* to *t+1*, and
charges `1 bp × |change in position|` in costs. From that daily return stream it
reports total return, annualised Sharpe, and maximum drawdown, against a
buy-and-hold benchmark over the identical window. The full method is in
[`score.py`](score.py) — there is no hidden logic.
