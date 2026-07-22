#!/usr/bin/env python3
# © 2026 Neil Gilani (Martingale) — MIT License.
# Research Note 002 — Does volatility predict next-day returns?
#
# Reproducible: run `python experiment.py` (needs internet for yfinance).
# In Google Colab: run `!pip install yfinance matplotlib numpy` first.
"""Does how volatile a stock has *been* predict how it moves *next*?"""
from __future__ import annotations

import json
import os

import numpy as np

HERE = os.path.dirname(__file__)
FIG = os.path.join(HERE, "paper", "figures")
os.makedirs(FIG, exist_ok=True)


# ---------------------------------------------------------------------------
# Data — real daily closes via yfinance
# ---------------------------------------------------------------------------
def load_prices(ticker: str = "SPY", start: str = "2015-01-01") -> list[float]:
    import yfinance as yf
    frame = yf.download(ticker, start=start, progress=False, auto_adjust=True)
    if frame is None or len(frame) == 0:
        raise RuntimeError(f"no data for {ticker!r}")
    closes = frame["Close"]
    if hasattr(closes, "columns"):
        closes = closes[ticker]
    return [float(c) for c in closes.dropna().values]


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
def daily_returns(prices: list[float]) -> list[float]:
    """Percent change from each day to the next: [100,110] -> [0.10]."""
    returns = []
    for i in range(1, len(prices)):
        returns.append(prices[i] / prices[i - 1] - 1)
    return returns


def rolling_volatility(returns: list[float], window: int = 20) -> list[float | None]:
    """Std-dev of the trailing `window` returns; None until enough history."""
    vol: list[float | None] = []
    for t in range(len(returns)):
        if t + 1 < window:
            vol.append(None)
        else:
            recent = returns[t - window + 1: t + 1]
            vol.append(float(np.std(recent)))
    return vol


def pair_today_vol_with_tomorrow_return(
    vol: list[float | None], returns: list[float]
) -> tuple[list[float], list[float]]:
    """Pair volatility known THROUGH day t with the return on day t+1.
    Using returns[t] instead of returns[t+1] would be lookahead (Note 001)."""
    xs, ys = [], []
    for t in range(len(returns) - 1):
        if vol[t] is not None:
            xs.append(vol[t])
            ys.append(returns[t + 1])
    return xs, ys


def correlation(xs: list[float], ys: list[float]) -> float:
    """Pearson correlation, -1..+1 (0 = no relationship)."""
    return float(np.corrcoef(xs, ys)[0, 1])


# ---------------------------------------------------------------------------
# Chart
# ---------------------------------------------------------------------------
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


def main():
    ticker = "SPY"
    print(f"loading {ticker} …")
    prices = load_prices(ticker)
    rets = daily_returns(prices)
    vol = rolling_volatility(rets, window=20)
    xs, ys = pair_today_vol_with_tomorrow_return(vol, rets)
    r = correlation(xs, ys)

    print(f"{ticker}: {len(prices)} daily closes, {len(xs)} paired days")
    print(f"correlation (today's volatility -> tomorrow's return): {r:.4f}")
    save_scatter(xs, ys, os.path.join(FIG, "scatter.png"),
                 f"{ticker}: today's volatility vs tomorrow's return")

    results = {"ticker": ticker, "n_days": len(prices), "n_pairs": len(xs),
               "correlation": round(r, 4)}
    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print("wrote results.json — now write up what you found in paper/paper.md")


if __name__ == "__main__":
    main()
