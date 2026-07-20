#!/usr/bin/env python3
# © 2026 Neil Gilani (Neil Quant Labs) — MIT License.
# Research Note 003 — Does volatility predict the SIZE of the next-day move?
#
# Reproducible: run `python experiment.py` (needs internet for yfinance).
# In Google Colab: run `!pip install yfinance matplotlib numpy` first.
"""Note 002 found today's volatility does NOT predict tomorrow's *direction*.
This asks the companion question: does it predict tomorrow's *size* — how big
the move is, regardless of which way — i.e. is volatility persistent?"""
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


def pair_today_vol_with_tomorrow_size(
    vol: list[float | None], returns: list[float]
) -> tuple[list[float], list[float]]:
    """Pair volatility known THROUGH day t with the SIZE of the day t+1 move,
    where size = |return|. Using |returns[t]| instead of |returns[t+1]| would
    be lookahead (Note 001): the predictor would see the move it must forecast."""
    xs, ys = [], []
    for t in range(len(returns) - 1):
        if vol[t] is not None:
            xs.append(vol[t])
            ys.append(abs(returns[t + 1]))
    return xs, ys


def correlation(xs: list[float], ys: list[float]) -> float:
    """Pearson correlation, -1..+1 (0 = no relationship)."""
    return float(np.corrcoef(xs, ys)[0, 1])


def vol_buckets(xs: list[float], ys: list[float], n_buckets: int = 5) -> list[dict]:
    """Sort days low->high by today's volatility, split into equal-size buckets,
    and report the average SIZE of the next day's move in each. If volatility is
    persistent, average |tomorrow| should rise from bucket 1 to bucket 5."""
    order = np.argsort(xs)
    xs_sorted = np.array(xs)[order]
    ys_sorted = np.array(ys)[order]
    rows = []
    for i, idx in enumerate(np.array_split(np.arange(len(xs_sorted)), n_buckets)):
        rows.append({
            "bucket": i + 1,
            "avg_vol_today": float(np.mean(xs_sorted[idx])),
            "avg_abs_return_tomorrow": float(np.mean(ys_sorted[idx])),
            "n": int(len(idx)),
        })
    return rows


# ---------------------------------------------------------------------------
# Chart — two panels: the scatter, and the bucket bars
# ---------------------------------------------------------------------------
def save_figure(xs, ys, buckets, path, ticker):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(11, 5))
    for ax in (axL, axR):
        ax.set_facecolor("#0d1117")
        ax.tick_params(colors="#8b949e", labelsize=8)
        for s in ax.spines.values():
            s.set_color("#30363d")
        ax.grid(color="#21262d", linewidth=0.6)
    fig.patch.set_facecolor("#0d1117")

    # Left: scatter of today's vol vs the size of tomorrow's move
    axL.scatter(xs, ys, s=6, alpha=0.30, color="#58a6ff")
    if len(xs) > 2:
        m, b = np.polyfit(xs, ys, 1)
        line_x = np.array([min(xs), max(xs)])
        axL.plot(line_x, m * line_x + b, color="#f0c674", linewidth=2)
    axL.set_xlabel("volatility today (last 20 days)", color="#8b949e")
    axL.set_ylabel("size of tomorrow's move  |return|", color="#8b949e")
    axL.set_title("Today's volatility vs. tomorrow's move size", color="#e6edf3", fontsize=11)

    # Right: average size of tomorrow's move across today's-vol buckets
    labels = [f"{r['bucket']}" for r in buckets]
    heights = [r["avg_abs_return_tomorrow"] * 100 for r in buckets]  # in %
    axR.bar(labels, heights, color="#3fb950", alpha=0.85)
    axR.set_xlabel("today's volatility, low → high (5 equal buckets)", color="#8b949e")
    axR.set_ylabel("avg size of tomorrow's move (%)", color="#8b949e")
    axR.set_title("Calm days → calm tomorrows; stormy → stormy", color="#e6edf3", fontsize=11)

    fig.suptitle(f"{ticker}: does volatility predict the SIZE of the next move?",
                 color="#e6edf3", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=150, facecolor="#0d1117")
    plt.close(fig)
    print(f"saved chart -> {path}")


def main():
    ticker = "SPY"
    print(f"loading {ticker} …")
    prices = load_prices(ticker)
    rets = daily_returns(prices)
    vol = rolling_volatility(rets, window=20)
    xs, ys = pair_today_vol_with_tomorrow_size(vol, rets)
    r = correlation(xs, ys)
    buckets = vol_buckets(xs, ys)

    print(f"{ticker}: {len(prices)} daily closes, {len(xs)} paired days")
    print(f"correlation (today's volatility -> SIZE of tomorrow's move): {r:.4f}")
    print("bucket  avg_vol_today  avg_|tomorrow|")
    for row in buckets:
        print(f"  {row['bucket']}      {row['avg_vol_today']:.5f}       "
              f"{row['avg_abs_return_tomorrow']:.5f}")

    save_figure(xs, ys, buckets, os.path.join(FIG, "clustering.png"), ticker)

    results = {"ticker": ticker, "n_days": len(prices), "n_pairs": len(xs),
               "correlation_vol_to_abs_next_return": round(r, 4),
               "buckets": buckets}
    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print("wrote results.json — now write up what you found in paper/paper.md")


if __name__ == "__main__":
    main()
