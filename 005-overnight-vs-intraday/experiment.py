#!/usr/bin/env python3
# © 2026 Neil Gilani (Martingale) — MIT License.
# Research Note 005 — Where do returns actually come from: overnight or intraday?
#
# Reproducible: `pip install arch backtesting numpy matplotlib scipy && python experiment.py`
# Self-test only (no figures):  python experiment.py --selftest
"""Every trading day is two sessions: the *overnight* gap from yesterday's close
to today's open, and the *intraday* move from the open to the close. They multiply
to the daily return, so the split is an accounting identity, not a model — which
makes it one of the few questions in this lab that can be answered exactly.

The claim in circulation is dramatic: index gains happen overnight while the
regular session goes nowhere. This note measures the split on 20 years of data,
asks whether it survives costs and holds up out of sample — and, along the way,
shows how a silently defective free data feed produces the exact opposite answer.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "paper", "figures")

TRADING_DAYS = 252
COST_GRID_BP = (0.0, 0.5, 1.0, 2.0, 5.0)   # per side, in basis points
SEED = 7

# A series whose overnight volatility is this small a fraction of its intraday
# volatility is not reporting real opening prices. Calibrated below: clean series
# land at 0.55-0.80; a stale-open series lands near 0.1.
VOL_RATIO_FLOOR = 0.35


# --------------------------------------------------------------------------- #
# Data — frozen, versioned datasets so the paper's numbers stay reproducible
# --------------------------------------------------------------------------- #
def load_datasets():
    """Return {label: (dates, open, close)} of real daily OHLC.

    Deliberately *not* a live download. Notes 002-004 fetch from yfinance, which
    means their numbers drift with every re-run. Here the sample is pinned to
    redistributable datasets shipped inside `arch` and `backtesting`, so every
    number in the paper reproduces exactly, forever.
    """
    import arch.data.nasdaq
    import arch.data.sp500
    from backtesting.test import GOOG

    def unpack(frame, name):
        frame = frame.dropna(subset=["Open", "Close"])
        dates = [str(d)[:10] for d in frame.index]
        return name, (dates,
                      frame["Open"].to_numpy(float),
                      frame["Close"].to_numpy(float))

    return dict([
        unpack(arch.data.nasdaq.load(), "NASDAQ Composite"),
        unpack(GOOG, "GOOG"),
        unpack(arch.data.sp500.load(), "S&P 500 (defective opens)"),
    ])


# --------------------------------------------------------------------------- #
# The decomposition — an identity, checked rather than assumed
# --------------------------------------------------------------------------- #
def decompose(opens, closes):
    """Split each day into its two sessions.

    overnight[t] = open[t]  / close[t-1] - 1     (yesterday's close -> today's open)
    intraday[t]  = close[t] / open[t]    - 1     (today's open -> today's close)

    By construction (1+overnight)(1+intraday) = (1+close-to-close), so no return
    is double-counted and none goes missing. Day 0 is dropped: it has no prior
    close, and using it would be a one-bar lookahead of exactly the kind Note 001
    is about.
    """
    overnight = opens[1:] / closes[:-1] - 1
    intraday = closes[1:] / opens[1:] - 1
    close_close = closes[1:] / closes[:-1] - 1
    residual = float(np.max(np.abs((1 + overnight) * (1 + intraday) - (1 + close_close))))
    assert residual < 1e-9, f"decomposition identity violated by {residual:.2e}"
    return overnight, intraday, close_close


def stats(returns, cost_bp_per_side=0.0):
    """Summarise a return stream. A session strategy enters and exits once a day,
    so it pays the cost twice — once at each end."""
    r = returns - 2 * cost_bp_per_side / 1e4
    n = len(r)
    mean, sd = float(np.mean(r)), float(np.std(r, ddof=1))
    cumulative = float(np.prod(1 + r) - 1)
    return {
        "n": n,
        "mean_bp": mean * 1e4,
        "median_bp": float(np.median(r)) * 1e4,
        "ann_vol": sd * math.sqrt(TRADING_DAYS),
        "ann_return": float((1 + cumulative) ** (TRADING_DAYS / n) - 1),
        "cumulative": cumulative,
        "sharpe": mean / sd * math.sqrt(TRADING_DAYS) if sd > 0 else float("nan"),
        "t_stat": mean / (sd / math.sqrt(n)) if sd > 0 else float("nan"),
        "pct_positive": float(np.mean(r > 0)),
    }


def paired_difference(overnight, intraday, seed=SEED, draws=5000):
    """Overnight and intraday are measured on the *same* days, so the honest test
    of "is one bigger" is paired, not two independent samples. Bootstrap the CI
    rather than leaning on normality of a fat-tailed daily series."""
    diff = overnight - intraday
    n = len(diff)
    se = float(np.std(diff, ddof=1)) / math.sqrt(n)
    rng = np.random.default_rng(seed)
    boot = np.array([diff[rng.integers(0, n, n)].mean() for _ in range(draws)])
    return {
        "mean_bp": float(np.mean(diff)) * 1e4,
        "t_stat": float(np.mean(diff)) / se if se > 0 else float("nan"),
        "ci95_bp": [float(np.percentile(boot, 2.5)) * 1e4,
                    float(np.percentile(boot, 97.5)) * 1e4],
    }


# --------------------------------------------------------------------------- #
# Data quality — run BEFORE the analysis, because it decides what is usable
# --------------------------------------------------------------------------- #
def audit(dates, opens, closes):
    """Two tests for whether a feed's opening prices are real.

    1. `stale_open_rate` — how often today's open is *exactly* yesterday's close.
       A blunt tell: some feeds carry the prior close forward as the open.
    2. `vol_ratio` — overnight volatility divided by intraday volatility. This is
       the sharper test, because a feed can be smoothed rather than exactly
       copied. Real equities gap on overnight news; a series that says they
       barely move between the close and the open is describing a market that
       does not exist.
    """
    overnight, intraday, _ = decompose(opens, closes)
    stale = np.abs(opens[1:] - closes[:-1]) < 1e-9
    ratio = float(np.std(overnight, ddof=1) / np.std(intraday, ddof=1))
    return {
        "stale_open_rate": float(np.mean(stale)),
        "vol_ratio": ratio,
        "big_gap_rate": float(np.mean(np.abs(overnight) > 0.005)),
        "usable": bool(ratio >= VOL_RATIO_FLOOR),
    }


def contamination_sweep(opens, closes, rates=(0.0, 0.1, 0.25, 0.4, 0.6, 0.95), seed=42):
    """Take a *clean* series and deliberately break it: overwrite the open with
    the prior close on a random fraction `p` of days, exactly the defect found in
    the S&P 500 feed. If that defect is what flips the answer, the flip should
    appear smoothly as p rises — a controlled demonstration of the mechanism
    rather than an assertion about it."""
    out = []
    for p in rates:
        rng = np.random.default_rng(seed)
        broken = opens.copy()
        hit = rng.random(len(opens) - 1) < p
        broken[1:][hit] = closes[:-1][hit]
        overnight, intraday, _ = decompose(broken, closes)
        out.append({
            "p": p,
            "overnight_ann": stats(overnight)["ann_return"],
            "overnight_vol": stats(overnight)["ann_vol"],
            "intraday_ann": stats(intraday)["ann_return"],
            "vol_ratio": float(np.std(overnight, ddof=1) / np.std(intraday, ddof=1)),
        })
    return out


# --------------------------------------------------------------------------- #
# Robustness
# --------------------------------------------------------------------------- #
def by_period(dates, overnight, intraday, periods):
    years = np.array([int(d[:4]) for d in dates[1:]])
    rows = []
    for label, lo, hi in periods:
        m = (years >= lo) & (years <= hi)
        if m.sum() < TRADING_DAYS:
            continue
        rows.append({"label": label,
                     "overnight": stats(overnight[m]),
                     "intraday": stats(intraday[m])})
    return rows


def by_year(dates, overnight, intraday):
    years = np.array([int(d[:4]) for d in dates[1:]])
    rows = []
    for y in sorted(set(years.tolist())):
        m = years == y
        rows.append({"year": int(y),
                     "overnight": float(np.prod(1 + overnight[m]) - 1),
                     "intraday": float(np.prod(1 + intraday[m]) - 1)})
    return rows


def trimmed_profile(overnight, intraday, trims=(0, 1, 2, 5, 10, 25)):
    """Is the gap a broad property of the distribution, or a handful of days?
    Symmetric trimming answers it: cut the same fraction off both tails and watch
    what survives."""
    from scipy import stats as sps
    return [{"trim_pct": t,
             "overnight_bp": float(sps.trim_mean(overnight, t / 100)) * 1e4,
             "intraday_bp": float(sps.trim_mean(intraday, t / 100)) * 1e4}
            for t in trims]


def worst_sessions(overnight, intraday, k=20):
    """Of the k worst single sessions in the sample, how many were overnight?"""
    pooled = np.concatenate([overnight, intraday])
    is_overnight = np.concatenate([np.ones(len(overnight), bool),
                                   np.zeros(len(intraday), bool)])
    order = np.argsort(pooled)[:k]
    return {"k": k, "overnight": int(is_overnight[order].sum()),
            "intraday": int((~is_overnight[order]).sum())}


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
def _dark(ax, fig):
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")
    ax.tick_params(colors="#8b949e", labelsize=8)
    for s in ax.spines.values():
        s.set_color("#30363d")
    ax.grid(color="#21262d", linewidth=0.6)


def _legend(ax):
    leg = ax.legend(facecolor="#161b22", edgecolor="#30363d", fontsize=8)
    for t in leg.get_texts():
        t.set_color("#e6edf3")


def fig_decomposition(dates, overnight, intraday, close_close, label, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 5))
    _dark(ax, fig)
    x = np.arange(len(overnight))
    for series, colour, name in ((overnight, "#58a6ff", "overnight (close → open)"),
                                 (intraday, "#f85149", "intraday (open → close)"),
                                 (close_close, "#f0c674", "buy & hold (close → close)")):
        ax.plot(x, np.cumprod(1 + series) * 100, color=colour, linewidth=1.5, label=name)
    ax.set_yscale("log")
    ax.axhline(100, color="#8b949e", linewidth=0.8)
    ticks = [i for i in range(0, len(overnight), TRADING_DAYS * 2)]
    ax.set_xticks(ticks)
    ax.set_xticklabels([dates[1:][i][:4] for i in ticks], color="#8b949e", fontsize=8)
    ax.set_ylabel("growth of 100 (log scale)", color="#8b949e")
    ax.set_title(f"{label}: the whole gain happened while the market was closed",
                 color="#e6edf3", fontsize=11)
    _legend(ax)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor="#0d1117")
    plt.close(fig)
    print(f"saved -> {path}")


def fig_data_quality(sweep, audits, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax in (ax1, ax2):
        _dark(ax, fig)

    ps = [row["p"] * 100 for row in sweep]
    ax1.plot(ps, [r["overnight_ann"] * 100 for r in sweep], "o-",
             color="#58a6ff", linewidth=1.6, label="overnight")
    ax1.plot(ps, [r["intraday_ann"] * 100 for r in sweep], "o-",
             color="#f85149", linewidth=1.6, label="intraday")
    ax1.axhline(0, color="#8b949e", linewidth=0.8)
    ax1.set_xlabel("% of opens overwritten with the prior close", color="#8b949e")
    ax1.set_ylabel("annualised return (%)", color="#8b949e")
    ax1.set_title("Breaking a clean feed on purpose", color="#e6edf3", fontsize=10)
    _legend(ax1)

    names = list(audits)
    ratios = [audits[n]["vol_ratio"] for n in names]
    colours = ["#3fb950" if r >= VOL_RATIO_FLOOR else "#f85149" for r in ratios]
    y = np.arange(len(names))
    ax2.barh(y, ratios, color=colours, alpha=0.9)
    ax2.axvline(VOL_RATIO_FLOOR, color="#f0c674", linestyle="--", linewidth=1.4,
                label=f"plausibility floor ({VOL_RATIO_FLOOR})")
    ax2.set_yticks(y)
    ax2.set_yticklabels([n.replace(" (defective opens)", "\n(defective opens)") for n in names],
                        color="#8b949e", fontsize=8)
    ax2.set_xlabel("overnight vol ÷ intraday vol", color="#8b949e")
    ax2.set_title("The diagnostic that catches it", color="#e6edf3", fontsize=10)
    ax2.grid(axis="y", linewidth=0)
    _legend(ax2)

    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor="#0d1117")
    plt.close(fig)
    print(f"saved -> {path}")


# --------------------------------------------------------------------------- #
# Self-test — validate the machinery on data with a known answer
# --------------------------------------------------------------------------- #
def selftest():
    rng = np.random.default_rng(0)
    n = 4000

    # 1. Identity holds on arbitrary positive prices.
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    o = c * np.exp(rng.normal(0, 0.008, n))
    ov, it, cc = decompose(o, c)
    assert np.allclose((1 + ov) * (1 + it), 1 + cc), "identity broken"

    # 2. Planted edge is recovered. Build prices where ALL drift is overnight:
    #    open[t] = close[t-1] * (1 + mu + noise); close[t] = open[t] * (1 + noise).
    mu = 0.0005
    closes = [100.0]
    opens = [100.0]
    for _ in range(n):
        op = closes[-1] * (1 + mu + rng.normal(0, 0.004))
        cl = op * (1 + rng.normal(0, 0.008))
        opens.append(op)
        closes.append(cl)
    ov, it, _ = decompose(np.array(opens), np.array(closes))
    assert abs(np.mean(ov) - mu) < 3e-4, f"overnight drift not recovered: {np.mean(ov)}"
    assert abs(np.mean(it)) < 3e-4, f"phantom intraday drift: {np.mean(it)}"

    # 3. No planted edge -> no detected edge (guards against a false positive).
    closes = [100.0]
    opens = [100.0]
    for _ in range(n):
        op = closes[-1] * (1 + rng.normal(0, 0.004))
        cl = op * (1 + rng.normal(0, 0.008))
        opens.append(op)
        closes.append(cl)
    ov, it, _ = decompose(np.array(opens), np.array(closes))
    assert abs(paired_difference(ov, it)["t_stat"]) < 3, "false positive on null data"

    # 4. The audit flags a stale-open feed and clears a clean one.
    clean = audit([""] * (n + 1), np.array(opens), np.array(closes))
    assert clean["usable"], "clean series wrongly flagged"
    broken_opens = np.array(opens).copy()
    broken_opens[1:] = np.array(closes)[:-1]
    broken = audit([""] * (n + 1), broken_opens, np.array(closes))
    assert not broken["usable"] and broken["stale_open_rate"] > 0.99, "audit missed stale opens"

    # 5. Costs are charged twice a day, in the right direction.
    r = np.full(500, 0.001)
    assert abs(stats(r, 1.0)["mean_bp"] - (10 - 2)) < 1e-9, "cost accounting wrong"

    print("self-test: all checks passed "
          "(identity, edge recovery, null control, data audit, cost accounting)")


# --------------------------------------------------------------------------- #
def main():
    if "--selftest" in sys.argv:
        selftest()
        return
    selftest()
    os.makedirs(FIG, exist_ok=True)

    datasets = load_datasets()
    results = {"trading_days": TRADING_DAYS, "vol_ratio_floor": VOL_RATIO_FLOOR,
               "datasets": {}}

    print("\n=== DATA AUDIT (runs before any analysis) ===")
    audits = {}
    for name, (dates, o, c) in datasets.items():
        a = audit(dates, o, c)
        audits[name] = a
        flag = "OK" if a["usable"] else "REJECTED"
        print(f"  {name:26s} n={len(dates):5d} {dates[0]}..{dates[-1]}  "
              f"stale={a['stale_open_rate']*100:5.1f}%  vol-ratio={a['vol_ratio']:.3f}  [{flag}]")

    for name, (dates, o, c) in datasets.items():
        overnight, intraday, close_close = decompose(o, c)
        entry = {
            "start": dates[0], "end": dates[-1], "n_days": len(dates),
            "audit": audits[name],
            "overnight": stats(overnight),
            "intraday": stats(intraday),
            "close_to_close": stats(close_close),
            "paired_difference": paired_difference(overnight, intraday),
        }

        if audits[name]["usable"]:
            entry["costs"] = [
                {"bp_per_side": bp,
                 "overnight": stats(overnight, bp),
                 "intraday": stats(intraday, bp)}
                for bp in COST_GRID_BP
            ]
            entry["breakeven_bp_per_side"] = float(np.mean(overnight)) / 2 * 1e4
            y0, y1 = int(dates[1][:4]), int(dates[-1][:4])
            mid = (y0 + y1) // 2
            entry["subperiods"] = by_period(dates, overnight, intraday, [
                (f"{y0}-{mid} (first half)", y0, mid),
                (f"{mid+1}-{y1} (second half)", mid + 1, y1),
                (f"{y0+2}-{y1} (ex first 2 years)", y0 + 2, y1),
            ])
            entry["by_year"] = by_year(dates, overnight, intraday)
            entry["trimmed"] = trimmed_profile(overnight, intraday)
            entry["worst_sessions"] = worst_sessions(overnight, intraday)

        results["datasets"][name] = entry

        print(f"\n=== {name} ({dates[0]} .. {dates[-1]}, {len(dates)} bars) ===")
        if not audits[name]["usable"]:
            print("  [rejected by the audit — reported only as a data-quality case study]")
        for lbl in ("overnight", "intraday", "close_to_close"):
            s = entry[lbl]
            print(f"  {lbl:15s} mean={s['mean_bp']:+6.2f}bp  ann={s['ann_return']*100:+7.2f}%  "
                  f"vol={s['ann_vol']*100:5.1f}%  Sharpe={s['sharpe']:+5.2f}  "
                  f"cum={s['cumulative']*100:+8.1f}%")
        pd_ = entry["paired_difference"]
        print(f"  overnight - intraday: {pd_['mean_bp']:+.2f}bp/day  t={pd_['t_stat']:+.2f}  "
              f"95% CI [{pd_['ci95_bp'][0]:+.2f}, {pd_['ci95_bp'][1]:+.2f}]bp")

        if audits[name]["usable"]:
            print(f"  break-even cost: {entry['breakeven_bp_per_side']:.2f} bp per side")
            for row in entry["costs"]:
                print(f"    {row['bp_per_side']:4.1f}bp/side -> overnight ann "
                      f"{row['overnight']['ann_return']*100:+7.2f}%  "
                      f"Sharpe {row['overnight']['sharpe']:+5.2f}")
            for row in entry["subperiods"]:
                print(f"    {row['label']:28s} overnight {row['overnight']['ann_return']*100:+6.2f}% "
                      f"| intraday {row['intraday']['ann_return']*100:+6.2f}%")

    primary = "NASDAQ Composite"
    dates, o, c = datasets[primary]
    overnight, intraday, close_close = decompose(o, c)
    results["contamination_sweep"] = contamination_sweep(o, c)
    print("\n=== CONTROLLED CONTAMINATION (clean NASDAQ feed, broken on purpose) ===")
    for row in results["contamination_sweep"]:
        print(f"  {row['p']*100:5.1f}% stale -> overnight ann {row['overnight_ann']*100:+6.2f}% "
              f"(vol {row['overnight_vol']*100:4.1f}%, ratio {row['vol_ratio']:.3f})  "
              f"| intraday ann {row['intraday_ann']*100:+6.2f}%")

    print("\n=== WHERE THE GAP LIVES (symmetric trimmed means) ===")
    for row in results["datasets"][primary]["trimmed"]:
        print(f"  trim {row['trim_pct']:2d}%/side: overnight {row['overnight_bp']:+6.2f}bp  "
              f"intraday {row['intraday_bp']:+6.2f}bp  gap "
              f"{row['overnight_bp'] - row['intraday_bp']:+6.2f}bp")
    w = results["datasets"][primary]["worst_sessions"]
    print(f"  of the {w['k']} worst sessions: {w['intraday']} intraday, {w['overnight']} overnight")

    # How much of the whole overnight gain came from the first two years?
    years = results["datasets"][primary]["by_year"]
    first_two = float(np.prod([1 + y["overnight"] for y in years[:2]]) - 1)
    results["datasets"][primary]["overnight_first_two_years"] = first_two
    print(f"  of the {results['datasets'][primary]['overnight']['cumulative']*100:+.1f}% cumulative "
          f"overnight gain, {first_two*100:+.1f}% came from "
          f"{years[0]['year']}-{years[1]['year']} alone")

    fig_decomposition(dates, overnight, intraday, close_close, primary,
                      os.path.join(FIG, "decomposition.png"))
    fig_data_quality(results["contamination_sweep"], audits,
                     os.path.join(FIG, "data_quality.png"))

    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print("\nwrote results.json")


if __name__ == "__main__":
    main()
