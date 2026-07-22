#!/usr/bin/env python3
# © 2026 Neil Gilani (Martingale) — MIT License.
# Part of quant-research: https://github.com/hilothefunnydog123-coder/quant-research
"""How Backtests Lie — reproducible experiments.

Two controlled experiments quantifying the two most common ways a trading
backtest overstates performance. Both use *simulated* data on purpose: to
measure a methodological bias you need a world where the ground-truth edge is
known, which real data can never give you. Every number in the paper is
produced by this script; run it to reproduce.

    python experiment.py            # writes results.json + paper/figures/*.png

Requires: quantsim (github.com/hilothefunnydog123-coder/quantsim), matplotlib.
"""
from __future__ import annotations

import json
import os

import numpy as np

from quantsim import simulate_gbm
from quantsim.backtest import Strategy, run_backtest
from quantsim.strategies import Momentum, MeanReversion, SMACrossover

FIG = os.path.join(os.path.dirname(__file__), "paper", "figures")
os.makedirs(FIG, exist_ok=True)

DARK = {"bg": "#0d1117", "grid": "#21262d", "text": "#e6edf3", "dim": "#8b949e",
        "green": "#3fb950", "blue": "#58a6ff", "red": "#f85149", "purple": "#a371f7"}


def _style(ax):
    ax.set_facecolor(DARK["bg"])
    ax.tick_params(colors=DARK["dim"], labelsize=8)
    for s in ax.spines.values():
        s.set_color("#30363d")
    ax.grid(color=DARK["grid"], linewidth=0.6)


# ---------------------------------------------------------------------------
# A backtester with an intentional lookahead switch.
# honest: the weight decided from data through bar t earns the return t -> t+1
# cheat : the same weight is credited the return t-1 -> t — the bar the signal
#         itself used. This is the classic, subtle off-by-one lookahead bug.
# ---------------------------------------------------------------------------
def backtest_sharpe(closes, strategy: Strategy, lookahead: bool, cost_bps=1.0):
    closes = np.asarray(closes, float)
    n = len(closes)
    bar_ret = closes[1:] / closes[:-1] - 1.0
    strategy.reset()
    w = np.zeros(n - 1)
    for t in range(strategy.warmup, n - 1):
        w[t] = float(np.clip(strategy.target_weight(closes[: t + 1]), -1, 1))
    turn = np.abs(np.diff(np.concatenate([[0.0], w])))
    if lookahead:
        # credit each weight the PREVIOUS bar's return (the one it peeked at)
        earned = np.concatenate([[0.0], w[1:] * bar_ret[:-1]])
    else:
        earned = w * bar_ret
    ret = earned - turn * (cost_bps / 1e4)
    if ret.std(ddof=1) == 0:
        return 0.0
    return float(ret.mean() / ret.std(ddof=1) * np.sqrt(252))


def experiment_lookahead(n_paths=500, years=4, seed=0):
    """Same strategies, same data, honest vs 1-bar lookahead. Measure inflation."""
    rng = np.random.default_rng(seed)
    strategies = {
        "SMA crossover": lambda: SMACrossover(20, 100),
        "Momentum": lambda: Momentum(60),
        "Mean reversion": lambda: MeanReversion(20),
    }
    results = {name: {"honest": [], "cheat": []} for name in strategies}
    for i in range(n_paths):
        closes = simulate_gbm(100, 0.05, 0.20, years=years, n_paths=1,
                              seed=int(rng.integers(1 << 31)))[0]
        for name, make in strategies.items():
            results[name]["honest"].append(backtest_sharpe(closes, make(), False))
            results[name]["cheat"].append(backtest_sharpe(closes, make(), True))
    summary = {}
    for name, r in results.items():
        h, c = np.array(r["honest"]), np.array(r["cheat"])
        summary[name] = {
            "honest_sharpe": float(h.mean()), "cheat_sharpe": float(c.mean()),
            "inflation": float(c.mean() - h.mean()),
        }
    _plot_lookahead(results, summary)
    return summary


def _plot_lookahead(results, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8, 4.2))
    _style(ax)
    names = list(results)
    x = np.arange(len(names))
    honest = [summary[n]["honest_sharpe"] for n in names]
    cheat = [summary[n]["cheat_sharpe"] for n in names]
    ax.bar(x - 0.2, honest, 0.4, label="honest backtest", color=DARK["green"])
    ax.bar(x + 0.2, cheat, 0.4, label="1-bar lookahead", color=DARK["red"])
    ax.axhline(0, color=DARK["dim"], linewidth=0.8)
    ax.set_xticks(x); ax.set_xticklabels(names, color=DARK["dim"], fontsize=9)
    ax.set_ylabel("mean annualized Sharpe", color=DARK["dim"])
    ax.set_title("A one-bar lookahead bug turns nothing into 'alpha'",
                 color=DARK["text"], fontsize=11)
    ax.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor=DARK["text"])
    fig.patch.set_facecolor(DARK["bg"]); fig.tight_layout()
    fig.savefig(os.path.join(FIG, "lookahead.png"), dpi=150, facecolor=DARK["bg"])
    plt.close(fig)


def experiment_data_snooping(n_strategies=400, years=4, seed=1):
    """On pure random-walk data (no edge exists by construction), try many
    strategies, keep the best in-sample, then test it out-of-sample."""
    rng = np.random.default_rng(seed)
    # a diverse zoo of strategies (varied params) — none has a real edge here
    zoo = []
    for fast in range(3, 60, 3):
        for slow in range(70, 210, 10):
            if fast < slow:
                zoo.append(SMACrossover(fast, slow))
    for lb in range(10, 240, 5):
        zoo.append(Momentum(lb))
    for w in range(5, 80, 3):
        zoo.append(MeanReversion(w))
    zoo = zoo[:n_strategies]

    # zero-drift random walk => any positive Sharpe is pure luck
    in_sample = simulate_gbm(100, 0.0, 0.20, years=years, n_paths=1, seed=7)[0]
    out_sample = simulate_gbm(100, 0.0, 0.20, years=years, n_paths=1, seed=99)[0]

    in_sharpes = [backtest_sharpe(in_sample, s, False) for s in zoo]
    best_idx = int(np.argmax(in_sharpes))
    best = zoo[best_idx]
    best_in = in_sharpes[best_idx]
    best_out = backtest_sharpe(out_sample, best, False)

    # distribution of a fresh strategy on fresh data, for context
    naive = [backtest_sharpe(
        simulate_gbm(100, 0.0, 0.20, years=years, n_paths=1,
                     seed=int(rng.integers(1 << 31)))[0],
        SMACrossover(20, 100), False) for _ in range(300)]

    summary = {
        "n_strategies_tried": len(zoo),
        "best_in_sample_sharpe": round(best_in, 3),
        "best_out_of_sample_sharpe": round(best_out, 3),
        "best_strategy": best.name,
        "single_strategy_mean_sharpe": round(float(np.mean(naive)), 3),
    }
    _plot_snooping(in_sharpes, best_in, best_out, naive, summary)
    return summary


def _plot_snooping(in_sharpes, best_in, best_out, naive, summary):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.5, 4))
    _style(ax1); _style(ax2)
    ax1.hist(in_sharpes, bins=24, color=DARK["purple"], alpha=0.85)
    ax1.axvline(best_in, color=DARK["red"], linewidth=2,
                label=f"best picked: {best_in:.2f}")
    ax1.set_title(f"{summary['n_strategies_tried']} strategies on random data\n"
                  "(no real edge exists)", color=DARK["text"], fontsize=10)
    ax1.set_xlabel("in-sample Sharpe", color=DARK["dim"])
    ax1.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor=DARK["text"], fontsize=8)

    ax2.bar(["in-sample\n(cherry-picked)", "out-of-sample\n(honest)"],
            [best_in, best_out], color=[DARK["red"], DARK["green"]])
    ax2.axhline(0, color=DARK["dim"], linewidth=0.8)
    ax2.set_title("The 'best' strategy's edge vanishes\nout of sample",
                  color=DARK["text"], fontsize=10)
    ax2.set_ylabel("Sharpe", color=DARK["dim"])
    fig.patch.set_facecolor(DARK["bg"]); fig.tight_layout()
    fig.savefig(os.path.join(FIG, "snooping.png"), dpi=150, facecolor=DARK["bg"])
    plt.close(fig)


def main():
    print("Running experiment 1: lookahead bias …")
    look = experiment_lookahead()
    for name, r in look.items():
        print(f"  {name:16s} honest {r['honest_sharpe']:+.2f} → "
              f"cheat {r['cheat_sharpe']:+.2f}  (inflation {r['inflation']:+.2f})")
    print("Running experiment 2: data snooping …")
    snoop = experiment_data_snooping()
    print(f"  tried {snoop['n_strategies_tried']} strategies on random data")
    print(f"  best in-sample Sharpe {snoop['best_in_sample_sharpe']} → "
          f"out-of-sample {snoop['best_out_of_sample_sharpe']}")

    results = {"lookahead": look, "data_snooping": snoop}
    with open(os.path.join(os.path.dirname(__file__), "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print("wrote results.json and figures")


if __name__ == "__main__":
    main()
