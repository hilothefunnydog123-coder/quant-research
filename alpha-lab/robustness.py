#!/usr/bin/env python3
"""Robustness sweep — the honest alternative to "optimizing for the best stats".

Picking the single parameter with the highest backtest Sharpe is data snooping
(Note 001): on enough tries you will always find a great-looking number, and it
will not survive out-of-sample. This script does the opposite. It sweeps a
parameter across its whole range and asks one question: *does the edge exist
everywhere, or only at one lucky value?* A real edge is a broad plateau above the
benchmark; a fake one is a lonely spike. We never select the peak — we measure how
wide the plateau is.

    python robustness.py

Fetches real SPY (Yahoo/stooq), falls back to a labelled synthetic series.
"""
from __future__ import annotations

import json
import math
import os

import harness
from hunt import load_closes


# --------------------------------------------------------------------------- #
# Parameterised strategies (factories) — same logic as strategies.py, but with
# the parameter exposed so we can sweep it.
# --------------------------------------------------------------------------- #
def trend(window):
    def f(history):
        if len(history) < window:
            return 1.0
        return 1.0 if history[-1] > sum(history[-window:]) / window else 0.0
    return f


def vol_target(lookback, target=0.15):
    def f(history):
        if len(history) < lookback + 1:
            return 1.0
        rets = [history[i] / history[i - 1] - 1 for i in range(len(history) - lookback, len(history))]
        m = sum(rets) / len(rets)
        sd = math.sqrt(sum((r - m) ** 2 for r in rets) / (len(rets) - 1))
        vol = sd * math.sqrt(harness.TRADING_DAYS)
        return target / vol if vol > 0 else 1.0
    return f


# --------------------------------------------------------------------------- #
# Sweep
# --------------------------------------------------------------------------- #
def sweep(name, factory, values, closes, bh_oos):
    print(f"\n=== {name} — sweeping across {len(values)} values ===")
    print(f"{'param':>8} | {'full Sharpe':>11} | {'OOS Sharpe':>10} | {'OOS maxDD':>9} | beats B&H?")
    rows = []
    for v in values:
        ev = harness.evaluate(factory(v), closes)
        beats = ev["oos"]["sharpe"] > bh_oos + 0.02
        rows.append({"param": v, "full_sharpe": ev["full"]["sharpe"],
                     "oos_sharpe": ev["oos"]["sharpe"],
                     "oos_maxdd": ev["oos"]["max_drawdown"], "beats": beats})
        print(f"{v:>8} | {ev['full']['sharpe']:>11.2f} | {ev['oos']['sharpe']:>10.2f} | "
              f"{ev['oos']['max_drawdown']*100:>8.1f}% | {'yes' if beats else 'no'}")
    n_beat = sum(1 for r in rows if r["beats"])
    frac = n_beat / len(rows)
    peak = max(rows, key=lambda r: r["oos_sharpe"])
    print(f"\n  {n_beat}/{len(rows)} ({frac*100:.0f}%) of values beat buy & hold out-of-sample.")
    print(f"  best OOS value = {peak['param']} (Sharpe {peak['oos_sharpe']:.2f}) — "
          f"do NOT just use this; it is the peak, not proof.")
    verdict = ("ROBUST: the edge holds across most of the range — not a fluke of one value."
               if frac >= 0.7 else
               "FRAGILE: the edge only shows up at a few values — likely overfit, treat with suspicion."
               if frac <= 0.4 else
               "MIXED: partial support — the edge is real-ish but parameter-sensitive.")
    print(f"  VERDICT: {verdict}")
    return {"name": name, "rows": rows, "frac_beating": frac,
            "peak_param": peak["param"], "verdict": verdict}


def save_chart(sweeps, bh_oos, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, len(sweeps), figsize=(6 * len(sweeps), 4.5))
    if len(sweeps) == 1:
        axes = [axes]
    fig.patch.set_facecolor("#0d1117")
    for ax, sw in zip(axes, sweeps):
        ax.set_facecolor("#0d1117")
        ax.tick_params(colors="#8b949e", labelsize=8)
        for s in ax.spines.values():
            s.set_color("#30363d")
        ax.grid(color="#21262d", linewidth=0.6)
        xs = [r["param"] for r in sw["rows"]]
        ys = [r["oos_sharpe"] for r in sw["rows"]]
        ax.plot(xs, ys, color="#3fb950", linewidth=2, marker="o", markersize=3)
        ax.axhline(bh_oos, color="#f0c674", linestyle="--", linewidth=1.4,
                   label=f"buy & hold ({bh_oos:.2f})")
        ax.fill_between(xs, bh_oos, ys, where=[y > bh_oos for y in ys],
                        color="#3fb950", alpha=0.15)
        ax.set_xlabel(sw["name"], color="#8b949e")
        ax.set_ylabel("out-of-sample Sharpe", color="#8b949e")
        ax.set_title(sw["verdict"].split(":")[0], color="#e6edf3", fontsize=10)
        leg = ax.legend(facecolor="#161b22", edgecolor="#30363d", fontsize=8)
        for t in leg.get_texts():
            t.set_color("#e6edf3")
    fig.suptitle("Is the edge a broad plateau (real) or a lonely spike (overfit)?",
                 color="#e6edf3", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(path, dpi=150, facecolor="#0d1117")
    print(f"\nsaved chart -> {path}")


def main():
    source, closes = load_closes()
    print(f"data: {source} · {len(closes)} closes")
    bh = harness.evaluate(lambda h: 1.0, closes)
    bh_oos = bh["oos"]["sharpe"]
    print(f"benchmark: buy & hold OOS Sharpe = {bh_oos:.2f}")

    sweeps = [
        sweep("Trend MA window (days)", trend, list(range(20, 301, 10)), closes, bh_oos),
        sweep("Vol-target lookback (days)", lambda lb: vol_target(lb), list(range(5, 61, 5)), closes, bh_oos),
    ]
    try:
        save_chart(sweeps, bh_oos, os.path.join(os.path.dirname(__file__), "robustness.png"))
    except Exception as exc:
        print(f"(chart skipped: {exc})")

    with open(os.path.join(os.path.dirname(__file__), "robustness.json"), "w") as f:
        json.dump({"data_source": source, "bh_oos_sharpe": bh_oos, "sweeps": sweeps}, f, indent=2)
    print("\nwrote robustness.json")
    print("\nHONEST TAKEAWAY: a wide green plateau above the dashed line = a real, "
          "parameter-insensitive edge. If it's a lonely spike, you found noise.")


if __name__ == "__main__":
    main()
