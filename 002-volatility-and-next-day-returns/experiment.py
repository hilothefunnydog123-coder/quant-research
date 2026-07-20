#!/usr/bin/env python3
# © 2026 Neil Gilani (Neil Quant Labs) — MIT License.
# Research Note 002 — Does volatility predict next-day returns?
#
# SCAFFOLD STATUS:
#   • Plumbing (data loading, plotting, structure) is DONE — you can ignore it.
#   • The ANALYSIS is yours. Fill in every `TODO(Neil)` block. Those functions
#     are the actual research — the part you'll explain to a professor someday.
#
# Run it once now: `python experiment.py`. It will stop at the first TODO and
# tell you exactly what to write. Implement one function, run again, repeat.
"""Does how volatile a stock has *been* predict how it moves *next*?"""
from __future__ import annotations

import numpy as np

# ===========================================================================
# PLUMBING (done for you) — real market data via yfinance
# ===========================================================================
def load_prices(ticker: str = "SPY", start: str = "2015-01-01") -> list[float]:
    """Download real daily closing prices. Returns a plain list of floats.

    In Google Colab, run `!pip install yfinance` in a cell first.
    """
    import yfinance as yf
    frame = yf.download(ticker, start=start, progress=False, auto_adjust=True)
    if frame is None or len(frame) == 0:
        raise RuntimeError(f"no data for {ticker!r} — check the ticker/spelling")
    closes = frame["Close"]
    if hasattr(closes, "columns"):        # single-ticker frames are 2-D
        closes = closes[ticker]
    return [float(c) for c in closes.dropna().values]


# ===========================================================================
# YOUR ANALYSIS (the science) — fill in each TODO(Neil)
# ===========================================================================
def daily_returns(prices: list[float]) -> list[float]:
    """Turn prices into daily percent returns.

    TODO(Neil): return a list where each element is today's price divided by
    yesterday's price, minus 1.  ([100, 110, 99] -> [0.10, -0.10])
    Hint: start a loop at index 1:  for i in range(1, len(prices)):
          then use prices[i] and prices[i-1].
    """
    raise NotImplementedError("TODO(Neil): write daily_returns")


def rolling_volatility(returns: list[float], window: int = 20) -> list[float | None]:
    """Volatility = how bouncy recent returns have been (their std deviation).

    TODO(Neil): for each day t, compute the standard deviation of the last
    `window` returns (the ones you already know by day t — no peeking ahead!).
    For the first `window-1` days there isn't enough history, so put None.
    Return a list the SAME length as `returns`.
    Hint: np.std(returns[t-window+1 : t+1])   once you have enough history.
    """
    raise NotImplementedError("TODO(Neil): write rolling_volatility")


def pair_today_vol_with_tomorrow_return(
    vol: list[float | None], returns: list[float]
) -> tuple[list[float], list[float]]:
    """THE most important step — and the exact lesson from Note 001.

    TODO(Neil): build two aligned lists:
      xs = volatility measured THROUGH day t   (what you'd know today)
      ys = the return on day t+1               (tomorrow — what you're predicting)
    Skip any day where vol[t] is None. NEVER pair vol[t] with returns[t] — that
    would be lookahead. It must be returns[t+1].
    Return (xs, ys).
    """
    raise NotImplementedError("TODO(Neil): write pair_today_vol_with_tomorrow_return")


def correlation(xs: list[float], ys: list[float]) -> float:
    """How strongly two lists move together, from -1 to +1 (0 = no relationship).

    TODO(Neil): return the Pearson correlation between xs and ys.
    Hint: np.corrcoef(xs, ys)[0, 1]
    """
    raise NotImplementedError("TODO(Neil): write correlation")


# ===========================================================================
# PLUMBING (done for you) — the scatter plot for your paper
# ===========================================================================
def save_scatter(xs, ys, path, title):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(7.5, 5))
    fig.patch.set_facecolor("#0d1117"); ax.set_facecolor("#0d1117")
    ax.tick_params(colors="#8b949e", labelsize=8)
    for s in ax.spines.values():
        s.set_color("#30363d")
    ax.grid(color="#21262d", linewidth=0.6)
    ax.scatter(xs, ys, s=6, alpha=0.35, color="#58a6ff")
    # best-fit line so the trend (if any) is visible
    if len(xs) > 2:
        m, b = np.polyfit(xs, ys, 1)
        line_x = np.array([min(xs), max(xs)])
        ax.plot(line_x, m * line_x + b, color="#f0c674", linewidth=2)
    ax.set_xlabel("volatility today (last 20 days)", color="#8b949e")
    ax.set_ylabel("return tomorrow", color="#8b949e")
    ax.set_title(title, color="#e6edf3", fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=150, facecolor="#0d1117")
    plt.close(fig)
    print(f"saved chart -> {path}")


# ===========================================================================
# Orchestration — wires your analysis together
# ===========================================================================
def main():
    ticker = "SPY"
    print(f"loading {ticker} …")
    prices = load_prices(ticker)
    print(f"got {len(prices)} daily closes")

    rets = daily_returns(prices)
    vol = rolling_volatility(rets, window=20)
    xs, ys = pair_today_vol_with_tomorrow_return(vol, rets)
    r = correlation(xs, ys)

    print(f"\nData points: {len(xs)}")
    print(f"Correlation (today's volatility vs tomorrow's return): {r:.4f}")
    save_scatter(xs, ys, "paper/figures/scatter.png",
                 f"{ticker}: does today's volatility predict tomorrow's return?")

    # TODO(Neil): look at r and the chart. Is there a real relationship, or is
    # it basically zero? Write what you find (and what it means) in paper/paper.md.


if __name__ == "__main__":
    main()
