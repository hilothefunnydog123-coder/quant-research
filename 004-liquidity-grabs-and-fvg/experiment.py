#!/usr/bin/env python3
# © 2026 Neil Gilani (Neil Quant Labs) — MIT License.
# Research Note 004 — Do liquidity grabs and fair value gaps have a statistical edge?
#
# Reproducible: run `python experiment.py` (needs internet for yfinance).
# In Google Colab: run `!pip install yfinance matplotlib numpy` first.
"""A whole genre of trading content is built on two chart patterns — the "fair
value gap" (a 3-candle imbalance) and the "liquidity grab" (a stop hunt that
sweeps a recent high or low and reverses). The claims are enormous and the
testing is almost nonexistent. This gives each a precise definition and asks the
only question that matters: after the pattern appears, is the forward return
different from the market's baseline — or is it noise dressed up as a signal?"""
from __future__ import annotations

import json
import math
import os

import numpy as np

HERE = os.path.dirname(__file__)
FIG = os.path.join(HERE, "paper", "figures")
os.makedirs(FIG, exist_ok=True)

LOOKBACK = 20        # window that defines a "recent" high/low for liquidity grabs
HORIZONS = (1, 5)    # forward-return horizons in trading days


# --------------------------------------------------------------------------- #
# Data — real daily OHLC via yfinance
# --------------------------------------------------------------------------- #
def load_ohlc(ticker: str = "SPY", start: str = "2015-01-01"):
    import yfinance as yf
    frame = yf.download(ticker, start=start, progress=False, auto_adjust=True)
    if frame is None or len(frame) == 0:
        raise RuntimeError(f"no data for {ticker!r}")

    def col(name):
        s = frame[name]
        if hasattr(s, "columns"):
            s = s[ticker]
        return [float(x) for x in s.values]

    return col("Open"), col("High"), col("Low"), col("Close")


# --------------------------------------------------------------------------- #
# Pattern detection — each returns the indices where the signal is CONFIRMED
# (known at that day's close), so forward returns start the same day with no
# lookahead.
# --------------------------------------------------------------------------- #
def bullish_fvgs(highs, lows):
    """3-candle bullish gap: candle 1's high sits below candle 3's low. Confirmed
    at candle 3. Returns (confirm_index, gap_bottom, gap_top)."""
    out = []
    for j in range(1, len(highs) - 1):
        if lows[j + 1] > highs[j - 1]:               # a gap exists
            out.append((j + 1, highs[j - 1], lows[j + 1]))
    return out


def bearish_fvgs(highs, lows):
    """3-candle bearish gap: candle 1's low sits above candle 3's high."""
    out = []
    for j in range(1, len(highs) - 1):
        if highs[j + 1] < lows[j - 1]:
            out.append((j + 1, highs[j + 1], lows[j - 1]))
    return out


def liquidity_grab_highs(highs, closes, window=LOOKBACK):
    """Bearish stop hunt: a new `window`-day high is printed intraday but the day
    closes below the prior close — highs swept, then rejected."""
    out = []
    for t in range(window, len(highs)):
        if highs[t] > max(highs[t - window:t]) and closes[t] < closes[t - 1]:
            out.append(t)
    return out


def liquidity_grab_lows(lows, closes, window=LOOKBACK):
    """Bullish stop hunt: a new `window`-day low is swept but the day closes up."""
    out = []
    for t in range(window, len(lows)):
        if lows[t] < min(lows[t - window:t]) and closes[t] > closes[t - 1]:
            out.append(t)
    return out


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #
def _norm_cdf(x):
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def forward_returns(closes, indices, k):
    return [closes[i + k] / closes[i] - 1 for i in indices if i + k < len(closes)]


def baseline_returns(closes, k):
    return [closes[t + k] / closes[t] - 1 for t in range(len(closes) - k)]


def summarize(sample, baseline):
    """Mean forward return of the event set, its standard error, a t-stat and
    two-sided p-value versus zero, and how it compares to the market baseline."""
    n = len(sample)
    if n < 2:
        return {"n": n, "mean": float("nan"), "se": float("nan"),
                "t": float("nan"), "p": float("nan"), "hit_rate": float("nan"),
                "baseline_mean": float(np.mean(baseline))}
    m = float(np.mean(sample))
    se = float(np.std(sample, ddof=1) / math.sqrt(n))
    t = m / se if se > 0 else 0.0
    return {
        "n": n,
        "mean": m,
        "se": se,
        "t": t,
        "p": 2 * (1 - _norm_cdf(abs(t))),
        "hit_rate": float(np.mean([1 if x > 0 else 0 for x in sample])),
        "baseline_mean": float(np.mean(baseline)),
    }


def fill_rate(lows, highs, fvgs, direction, k=10):
    """Fraction of gaps that price trades back into within `k` days — the "gaps
    always get filled" claim. For a bullish gap (bottom, top), a fill means a
    later low drops back to `top` (re-enters the gap); mirror for bearish."""
    filled = 0
    for idx, bottom, top in fvgs:
        window = range(idx + 1, min(idx + 1 + k, len(lows)))
        if direction == "bull":
            if any(lows[t] <= top for t in window):
                filled += 1
        else:
            if any(highs[t] >= bottom for t in window):
                filled += 1
    return filled / len(fvgs) if fvgs else float("nan")


# --------------------------------------------------------------------------- #
# Chart
# --------------------------------------------------------------------------- #
def save_chart(rows, baseline_mean, path, ticker, k):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor("#0d1117"); ax.set_facecolor("#0d1117")
    ax.tick_params(colors="#8b949e", labelsize=8)
    for s in ax.spines.values():
        s.set_color("#30363d")
    ax.grid(color="#21262d", linewidth=0.6, axis="y")

    names = [r["label"] for r in rows]
    means = [r["mean"] * 100 for r in rows]
    errs = [r["se"] * 100 for r in rows]
    colors = ["#58a6ff" if r["bull"] else "#f85149" for r in rows]
    x = np.arange(len(names))
    ax.bar(x, means, yerr=errs, capsize=4, color=colors, alpha=0.85,
           error_kw={"ecolor": "#8b949e", "elinewidth": 1})
    ax.axhline(baseline_mean * 100, color="#f0c674", linewidth=1.4, linestyle="--",
               label=f"market baseline ({baseline_mean*100:+.3f}%)")
    ax.axhline(0, color="#8b949e", linewidth=0.8)
    ax.set_xticks(x); ax.set_xticklabels(names, color="#8b949e", fontsize=8, rotation=12)
    ax.set_ylabel(f"avg {k}-day forward return (%)", color="#8b949e")
    ax.set_title(f"{ticker}: is there an edge after the pattern? ({k}-day forward return ± std error)",
                 color="#e6edf3", fontsize=11)
    leg = ax.legend(facecolor="#161b22", edgecolor="#30363d", fontsize=8)
    for txt in leg.get_texts():
        txt.set_color("#e6edf3")
    fig.tight_layout(); fig.savefig(path, dpi=150, facecolor="#0d1117")
    plt.close(fig)
    print(f"saved chart -> {path}")


def main():
    ticker = "SPY"
    print(f"loading {ticker} OHLC …")
    opens, highs, lows, closes = load_ohlc(ticker)
    print(f"{ticker}: {len(closes)} daily bars")

    bull_fvg = bullish_fvgs(highs, lows)
    bear_fvg = bearish_fvgs(highs, lows)
    grab_hi = liquidity_grab_highs(highs, closes)   # bearish
    grab_lo = liquidity_grab_lows(lows, closes)     # bullish

    events = {
        "Bullish FVG": ([i for i, _, _ in bull_fvg], True),
        "Bearish FVG": ([i for i, _, _ in bear_fvg], False),
        "Liquidity grab (highs)": (grab_hi, False),
        "Liquidity grab (lows)": (grab_lo, True),
    }
    print(f"events found — bullFVG {len(bull_fvg)}, bearFVG {len(bear_fvg)}, "
          f"grabHi {len(grab_hi)}, grabLo {len(grab_lo)}")

    results = {"ticker": ticker, "n_bars": len(closes), "lookback": LOOKBACK, "by_horizon": {}}
    for k in HORIZONS:
        base = baseline_returns(closes, k)
        rows = []
        print(f"\n=== {k}-day forward return (baseline mean {np.mean(base)*100:+.3f}%) ===")
        for label, (idx, bull) in events.items():
            stat = summarize(forward_returns(closes, idx, k), base)
            stat.update(label=label, bull=bull)
            rows.append(stat)
            print(f"  {label:24s} n={stat['n']:4d}  mean={stat['mean']*100:+.3f}%  "
                  f"t={stat['t']:+.2f}  p={stat['p']:.3f}  hit={stat['hit_rate']*100:.0f}%")
        results["by_horizon"][str(k)] = {
            "baseline_mean": float(np.mean(base)),
            "events": [{kk: vv for kk, vv in r.items()} for r in rows],
        }
        if k == HORIZONS[0]:
            save_chart(rows, float(np.mean(base)),
                       os.path.join(FIG, "edge.png"), ticker, k)

    results["fill_rate_10d"] = {
        "bullish_fvg": fill_rate(lows, highs, bull_fvg, "bull"),
        "bearish_fvg": fill_rate(lows, highs, bear_fvg, "bear"),
    }
    print(f"\nFVG fill rate within 10 days — bullish "
          f"{results['fill_rate_10d']['bullish_fvg']*100:.0f}%, bearish "
          f"{results['fill_rate_10d']['bearish_fvg']*100:.0f}%")

    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print("\nwrote results.json — now write up what you found in paper/paper.md")


if __name__ == "__main__":
    main()
