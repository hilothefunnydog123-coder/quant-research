#!/usr/bin/env python3
# © 2026 Neil Gilani (Neil Quant Labs) — MIT License.
# Research Note 003 — Momentum vs. mean reversion across regimes, after costs.
#
# Reproducible: run `python experiment.py` (needs internet for yfinance).
# In Google Colab: run `!pip install yfinance matplotlib numpy` first.
"""Two of the oldest ideas in trading pull in opposite directions:
  * MOMENTUM  — what went up keeps going up (bet on continuation).
  * MEAN REVERSION — what went up comes back down (bet on reversal).
Both can't be right all the time. This tests when each one works on SPY, splits
the record into trending (bull) vs. falling (bear) regimes, and — crucially —
charges realistic trading costs, because a signal that only works for free isn't
a strategy."""
from __future__ import annotations

import json
import os

import numpy as np

HERE = os.path.dirname(__file__)
FIG = os.path.join(HERE, "paper", "figures")
os.makedirs(FIG, exist_ok=True)

# --- fixed choices, stated BEFORE running (no tuning after seeing results) ---
MOM_LOOKBACK = 20      # momentum looks at the trailing 20-day return
MA_WINDOW = 200        # regime: price above/below its 200-day average
TRADING_DAYS = 252     # for annualizing


# ---------------------------------------------------------------------------
# Data — real daily closes via yfinance
# ---------------------------------------------------------------------------
def load_prices(ticker: str = "SPY", start: str = "2007-01-01") -> list[float]:
    import yfinance as yf
    frame = yf.download(ticker, start=start, progress=False, auto_adjust=True)
    if frame is None or len(frame) == 0:
        raise RuntimeError(f"no data for {ticker!r}")
    closes = frame["Close"]
    if hasattr(closes, "columns"):
        closes = closes[ticker]
    return [float(c) for c in closes.dropna().values]


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------
def daily_returns(prices: list[float]) -> list[float]:
    """Percent change day to day. returns[t] is the move realized on day t+1."""
    return [prices[i] / prices[i - 1] - 1 for i in range(1, len(prices))]


def moving_average(levels: list[float], window: int) -> list[float | None]:
    """Trailing average of `levels`; None until there is enough history."""
    out: list[float | None] = []
    for t in range(len(levels)):
        if t + 1 < window:
            out.append(None)
        else:
            out.append(float(np.mean(levels[t - window + 1: t + 1])))
    return out


def sharpe(daily: list[float]) -> float:
    """Annualized Sharpe ratio of a daily-return stream (0 if no variation)."""
    if len(daily) < 2:
        return 0.0
    arr = np.array(daily, dtype=float)
    sd = arr.std(ddof=1)
    if sd == 0:
        return 0.0
    return float(arr.mean() / sd * np.sqrt(TRADING_DAYS))


# ---------------------------------------------------------------------------
# Signals — each returns a position in {+1, -1} for every return-day t,
# meaning "the position you HOLD going into day t+1", using only data <= t.
# ---------------------------------------------------------------------------
def momentum_positions(returns: list[float], lookback: int = MOM_LOOKBACK) -> list[float | None]:
    """+1 (long) if the trailing `lookback` return is positive, else -1 (short).
    Bet that the recent trend continues."""
    pos: list[float | None] = []
    for t in range(len(returns)):
        if t + 1 < lookback:
            pos.append(None)
        else:
            trail = np.prod([1 + r for r in returns[t - lookback + 1: t + 1]]) - 1
            pos.append(1.0 if trail > 0 else -1.0)
    return pos


def reversion_positions(returns: list[float]) -> list[float | None]:
    """+1 (long) if YESTERDAY (day t) was down, else -1. Bet the last move reverses.
    None on t=0 (no prior day). Only uses returns[t], so no lookahead."""
    pos: list[float | None] = []
    for t in range(len(returns)):
        pos.append(None if t == 0 else (1.0 if returns[t] < 0 else -1.0))
    return pos


# ---------------------------------------------------------------------------
# Turn a position stream into an after-cost daily-return stream
# ---------------------------------------------------------------------------
def strategy_stream(positions: list[float | None], returns: list[float],
                    cost_per_unit: float) -> tuple[list[float], float]:
    """Apply position held after day t to the return on day t+1, minus trading
    cost proportional to how much the position changed. Returns (daily strat
    returns, average daily turnover). cost_per_unit is charged per unit of
    |Δposition| (a full +1↔-1 flip = 2 units)."""
    stream, turns, prev = [], [], None
    for t in range(len(returns) - 1):
        p = positions[t]
        if p is None:
            continue
        turnover = 0.0 if prev is None else abs(p - prev)
        stream.append(p * returns[t + 1] - cost_per_unit * turnover)
        turns.append(turnover)
        prev = p
    avg_turnover = float(np.mean(turns)) if turns else 0.0
    return stream, avg_turnover


def regime_split(positions, returns, levels_after_day, ma, cost_per_unit):
    """Same as strategy_stream, but also bucket each day's strat return by whether
    the market was in a BULL (price >= 200d MA) or BEAR regime that day."""
    bull, bear, prev = [], [], None
    for t in range(len(returns) - 1):
        p = positions[t]
        if p is None or ma[t] is None:
            continue
        turnover = 0.0 if prev is None else abs(p - prev)
        sr = p * returns[t + 1] - cost_per_unit * turnover
        (bull if levels_after_day[t] >= ma[t] else bear).append(sr)
        prev = p
    return bull, bear


# ---------------------------------------------------------------------------
# Chart — equity curves + after-cost Sharpe by regime
# ---------------------------------------------------------------------------
def save_figure(curves, regime_sharpes, path, ticker):
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

    colors = {"buy & hold": "#8b949e", "momentum": "#58a6ff", "mean reversion": "#f0c674"}
    for name, eq in curves.items():
        axL.plot(eq, label=name, color=colors.get(name, "#3fb950"), linewidth=1.6)
    axL.set_yscale("log")
    axL.set_xlabel("trading day", color="#8b949e")
    axL.set_ylabel("$1 grows to … (log scale, after costs)", color="#8b949e")
    axL.set_title("Equity curves, after costs", color="#e6edf3", fontsize=11)
    leg = axL.legend(facecolor="#161b22", edgecolor="#30363d", fontsize=8)
    for txt in leg.get_texts():
        txt.set_color("#e6edf3")

    labels = ["Momentum", "Mean reversion"]
    bull_vals = [regime_sharpes["bull"]["momentum"], regime_sharpes["bull"]["reversion"]]
    bear_vals = [regime_sharpes["bear"]["momentum"], regime_sharpes["bear"]["reversion"]]
    x = np.arange(len(labels)); w = 0.35
    axR.bar(x - w / 2, bull_vals, w, label="bull (price > 200d MA)", color="#3fb950")
    axR.bar(x + w / 2, bear_vals, w, label="bear (price < 200d MA)", color="#f85149")
    axR.axhline(0, color="#8b949e", linewidth=0.8)
    axR.set_xticks(x); axR.set_xticklabels(labels, color="#8b949e")
    axR.set_ylabel("after-cost annualized Sharpe", color="#8b949e")
    axR.set_title("Which idea works in which regime?", color="#e6edf3", fontsize=11)
    leg2 = axR.legend(facecolor="#161b22", edgecolor="#30363d", fontsize=8)
    for txt in leg2.get_texts():
        txt.set_color("#e6edf3")

    fig.suptitle(f"{ticker}: momentum vs. mean reversion, across regimes, after costs",
                 color="#e6edf3", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(path, dpi=150, facecolor="#0d1117")
    plt.close(fig)
    print(f"saved chart -> {path}")


def equity_curve(daily: list[float]) -> list[float]:
    eq, v = [], 1.0
    for r in daily:
        v *= (1 + r)
        eq.append(v)
    return eq


def main():
    ticker = "SPY"
    cost = 0.0001  # 1 basis point per unit of turnover (per side)
    print(f"loading {ticker} …")
    prices = load_prices(ticker)
    rets = daily_returns(prices)
    # price level at the close of return-day t is prices[t+1]
    levels_after_day = prices[1:]
    ma = moving_average(levels_after_day, MA_WINDOW)

    mom = momentum_positions(rets)
    rev = reversion_positions(rets)
    bh = [1.0] * len(rets)  # buy & hold: always long

    mom_net, mom_turn = strategy_stream(mom, rets, cost)
    rev_net, rev_turn = strategy_stream(rev, rets, cost)
    mom_gross, _ = strategy_stream(mom, rets, 0.0)
    rev_gross, _ = strategy_stream(rev, rets, 0.0)
    bh_net, _ = strategy_stream(bh, rets, 0.0)

    # regime split (after cost)
    mom_bull, mom_bear = regime_split(mom, rets, levels_after_day, ma, cost)
    rev_bull, rev_bear = regime_split(rev, rets, levels_after_day, ma, cost)
    regime_sharpes = {
        "bull": {"momentum": sharpe(mom_bull), "reversion": sharpe(rev_bull)},
        "bear": {"momentum": sharpe(mom_bear), "reversion": sharpe(rev_bear)},
    }

    # cost sensitivity
    cost_rows = []
    for bps in (0.0, 1.0, 5.0):
        c = bps / 10000.0
        ms, _ = strategy_stream(mom, rets, c)
        rs, _ = strategy_stream(rev, rets, c)
        cost_rows.append({"cost_bps": bps, "momentum_sharpe": round(sharpe(ms), 3),
                          "reversion_sharpe": round(sharpe(rs), 3)})

    print(f"\n{ticker}: {len(prices)} daily closes")
    print(f"{'strategy':<16}{'gross Sharpe':>14}{'net Sharpe':>13}{'avg turnover':>14}")
    print(f"{'buy & hold':<16}{sharpe(bh_net):>14.3f}{sharpe(bh_net):>13.3f}{0.0:>14.3f}")
    print(f"{'momentum':<16}{sharpe(mom_gross):>14.3f}{sharpe(mom_net):>13.3f}{mom_turn:>14.3f}")
    print(f"{'mean reversion':<16}{sharpe(rev_gross):>14.3f}{sharpe(rev_net):>13.3f}{rev_turn:>14.3f}")
    print("\nafter-cost Sharpe by regime:")
    print(f"  bull  momentum={regime_sharpes['bull']['momentum']:.3f}  "
          f"reversion={regime_sharpes['bull']['reversion']:.3f}")
    print(f"  bear  momentum={regime_sharpes['bear']['momentum']:.3f}  "
          f"reversion={regime_sharpes['bear']['reversion']:.3f}")
    print("\ncost sensitivity (net Sharpe):")
    for row in cost_rows:
        print(f"  {row['cost_bps']:>4.0f} bps   momentum={row['momentum_sharpe']:.3f}   "
              f"reversion={row['reversion_sharpe']:.3f}")

    curves = {"buy & hold": equity_curve(bh_net),
              "momentum": equity_curve(mom_net),
              "mean reversion": equity_curve(rev_net)}
    save_figure(curves, regime_sharpes, os.path.join(FIG, "regimes.png"), ticker)

    results = {
        "ticker": ticker, "n_days": len(prices), "cost_bps_per_side": 1.0,
        "mom_lookback": MOM_LOOKBACK, "ma_window": MA_WINDOW,
        "overall": {
            "buy_hold_sharpe": round(sharpe(bh_net), 3),
            "momentum_gross_sharpe": round(sharpe(mom_gross), 3),
            "momentum_net_sharpe": round(sharpe(mom_net), 3),
            "reversion_gross_sharpe": round(sharpe(rev_gross), 3),
            "reversion_net_sharpe": round(sharpe(rev_net), 3),
            "momentum_turnover": round(mom_turn, 3),
            "reversion_turnover": round(rev_turn, 3),
        },
        "by_regime": {k: {kk: round(vv, 3) for kk, vv in v.items()}
                      for k, v in regime_sharpes.items()},
        "cost_sensitivity": cost_rows,
    }
    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print("\nwrote results.json — now write up what you found in paper/paper.md")


if __name__ == "__main__":
    main()
