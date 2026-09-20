#!/usr/bin/env python3
# © 2026 Neil Gilani (Martingale) — MIT License.
# Research Note 006 — Do stop-losses actually improve risk-adjusted returns?
#
# Reproducible: `pip install arch backtesting numpy matplotlib && python experiment.py`
# Self-test only (no figures):  python experiment.py --selftest
""""Always use a stop loss" is the most repeated rule in retail trading, and one
of the least tested. A stop is not a forecast; it is a path-dependent rule that
truncates a holding period. That makes it easy to evaluate and easy to fool
yourself with, because a stop changes *both* return and risk, and because there
are many stops to choose from.

This note tests a grid of 30 stop rules, then asks the three questions that decide
whether any of them means anything: does the winner beat buy-and-hold by more than
a 30-way search would buy you on data with no trends at all; does the winner chosen
on the first decade still work in the second; and what does a stop actually fill at
when the market gaps through it?
"""
from __future__ import annotations

import itertools
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "paper", "figures")

TRADING_DAYS = 252
COST_BP = 1.0                       # per side, charged on every entry and exit
STOP_KINDS = ("trailing", "fixed")
STOP_LEVELS = (0.05, 0.10, 0.15, 0.20, 0.25)
REENTRY_DAYS = (1, 5, 21)
GRID = list(itertools.product(STOP_KINDS, STOP_LEVELS, REENTRY_DAYS))
N_SHUFFLES = 1000
SEED = 11


def label(g):
    kind, pct, re_ = g
    return f"{kind} {int(pct*100)}% re{re_}d"


# --------------------------------------------------------------------------- #
# Data — frozen, versioned datasets (see Note 005 for why this is not a live fetch)
# --------------------------------------------------------------------------- #
def load_datasets():
    import arch.data.nasdaq
    from backtesting.test import GOOG

    def unpack(frame, name):
        frame = frame.dropna(subset=["Open", "High", "Low", "Close"])
        cols = [frame[k].to_numpy(float) for k in ("Open", "High", "Low", "Close")]
        years = np.array([d.year for d in frame.index])
        return name, (*cols, years, str(frame.index[0])[:10], str(frame.index[-1])[:10])

    return dict([unpack(arch.data.nasdaq.load(), "NASDAQ Composite"),
                 unpack(GOOG, "GOOG")])


def coherence_violations(o, h, l, c):
    """A stop study triggers on the LOW, so the bars must be internally consistent
    before anything else is worth computing."""
    return int(((o > h) | (o < l) | (c > h) | (c < l) | (l > h)).sum())


# --------------------------------------------------------------------------- #
# The stop engine
# --------------------------------------------------------------------------- #
def run_stop(opens, highs, lows, closes, stop_pct, kind="trailing",
             reentry_days=5, cost_bp=COST_BP, gap_aware=True):
    """Long-only buy-and-hold with a stop. Returns (daily returns, diagnostics).

    **No lookahead.** The stop level active on day *t* is built only from data
    through *t−1*: the running peak is updated at each close and applies from the
    next bar. The stop triggers intraday when that day's LOW touches the level.

    **Fill realism.** If the day *opened* below the stop, the stop could not have
    filled at its price — the market gapped through it overnight and the order
    becomes a market order at the open. `gap_aware=False` reproduces the common
    backtesting error of always filling at the stop price, so the size of that
    error can be measured rather than assumed.
    """
    n = len(closes)
    r = np.zeros(n)
    invested = np.zeros(n)
    in_pos, entry_price, peak, flat_until = True, closes[0], highs[0], -1
    trades = triggers = gapped = 0
    slippage = []
    cost = cost_bp / 1e4

    for t in range(1, n):
        if in_pos:
            level = (1 - stop_pct) * (peak if kind == "trailing" else entry_price)
            if lows[t] <= level:
                triggers += 1
                if gap_aware and opens[t] <= level:
                    fill = opens[t]
                    gapped += 1
                else:
                    fill = level
                slippage.append(fill / level - 1)
                r[t] = fill / closes[t - 1] - 1 - cost
                invested[t] = 1
                in_pos = False
                trades += 1
                flat_until = t + reentry_days
            else:
                r[t] = closes[t] / closes[t - 1] - 1
                invested[t] = 1
                peak = max(peak, highs[t])
        elif t >= flat_until:                      # re-enter at this close
            in_pos, entry_price, peak = True, closes[t], highs[t]
            trades += 1
            r[t] = -cost

    return r, {"trades": trades, "triggers": triggers, "gapped": gapped,
               "gap_rate": gapped / triggers if triggers else 0.0,
               "time_in_market": float(np.mean(invested)),
               "mean_slippage_pct": float(np.mean(slippage) * 100) if slippage else 0.0}


def buy_hold(closes, cost_bp=COST_BP):
    r = np.zeros(len(closes))
    r[1:] = closes[1:] / closes[:-1] - 1
    r[0] = -cost_bp / 1e4
    return r


def blend(closes, exposure, cost_bp=COST_BP):
    """Hold a constant `exposure` of the index and the rest in cash at 0%.

    This is the benchmark a stop actually has to beat. A stop spends part of its
    life out of the market, so it delivers *less market* — and less market is
    available for free, without path dependence, trading, or gap risk.
    """
    return buy_hold(closes, cost_bp) * exposure


def metrics(r, td=TRADING_DAYS):
    r = np.asarray(r)
    mean, sd = float(np.mean(r)), float(np.std(r, ddof=1))
    eq = np.cumprod(1 + r)
    return {"ann_return": float(eq[-1] ** (td / len(r)) - 1),
            "ann_vol": sd * math.sqrt(td),
            "sharpe": mean / sd * math.sqrt(td) if sd > 0 else float("nan"),
            "max_drawdown": float(np.min(eq / np.maximum.accumulate(eq)) - 1),
            "cumulative": float(eq[-1] - 1)}


def grid_sharpes(o, h, l, c, cost_bp=COST_BP):
    return np.array([metrics(run_stop(o, h, l, c, p, k, re_, cost_bp)[0])["sharpe"]
                     for k, p, re_ in GRID])


# --------------------------------------------------------------------------- #
# The null: the same search, on data with the trends removed
# --------------------------------------------------------------------------- #
def shuffled_path(o, h, l, c, rng):
    """Rebuild a price path from the SAME daily bars in a random order.

    Each bar is stored as its multiplicative shape relative to the prior close
    (gap, high, low, close), so shuffling preserves the daily-return distribution
    and each bar's internal geometry *exactly*, while destroying every trend and
    every scrap of serial dependence. Buy-and-hold's Sharpe is unchanged by
    construction. A trailing stop is a trend-following device, so on this data it
    has nothing left to exploit — anything it still earns is what searching a
    30-rule grid buys you for free.
    """
    g, hi, lo, cl = o[1:] / c[:-1], h[1:] / c[:-1], l[1:] / c[:-1], c[1:] / c[:-1]
    i = rng.permutation(len(cl))
    g, hi, lo, cl = g[i], hi[i], lo[i], cl[i]
    C = np.r_[c[0], c[0] * np.cumprod(cl)]
    return np.r_[o[0], C[:-1] * g], np.r_[h[0], C[:-1] * hi], np.r_[l[0], C[:-1] * lo], C


def null_distribution(o, h, l, c, n_shuffles=N_SHUFFLES, seed=SEED):
    rng = np.random.default_rng(seed)
    best, n_beat = np.empty(n_shuffles), np.empty(n_shuffles)
    for i in range(n_shuffles):
        O, H, L, C = shuffled_path(o, h, l, c, rng)
        s = grid_sharpes(O, H, L, C)
        best[i] = s.max()
        n_beat[i] = (s > metrics(buy_hold(C))["sharpe"]).sum()
    return best, n_beat


def round_trip_drag(o, h, l, c, stop_pct, kind, reentry_days):
    """Every exit price paired with the price paid to get back in. This is the
    mechanism in one number: a stop sells after a fall and buys back later."""
    n = len(c)
    in_pos, entry, peak, flat, last_exit = True, c[0], h[0], -1, None
    pairs = []
    for t in range(1, n):
        if in_pos:
            level = (1 - stop_pct) * (peak if kind == "trailing" else entry)
            if l[t] <= level:
                last_exit = o[t] if o[t] <= level else level
                in_pos, flat = False, t + reentry_days
            else:
                peak = max(peak, h[t])
        elif t >= flat:
            in_pos, entry, peak = True, c[t], h[t]
            if last_exit is not None:
                pairs.append((last_exit, c[t]))
    if not pairs:
        return {"round_trips": 0, "bought_back_higher": float("nan"), "avg_drag_pct": float("nan")}
    p = np.array(pairs)
    return {"round_trips": len(p),
            "bought_back_higher": float(np.mean(p[:, 1] > p[:, 0])),
            "avg_drag_pct": float(np.mean(p[:, 1] / p[:, 0] - 1) * 100)}


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


def _legend(ax, loc="best"):
    leg = ax.legend(facecolor="#161b22", edgecolor="#30363d", fontsize=8, loc=loc)
    for t in leg.get_texts():
        t.set_color("#e6edf3")


def fig_search(null_best, real_best, bh_sharpe, ins, oos, spans, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax in (a1, a2):
        _dark(ax, fig)

    a1.hist(null_best, bins=40, color="#58a6ff", alpha=0.75,
            label=f"best of {len(GRID)} on shuffled data")
    a1.axvline(real_best, color="#f85149", linewidth=2,
               label=f"best of {len(GRID)} on real data ({real_best:+.2f})")
    a1.axvline(bh_sharpe, color="#f0c674", linewidth=1.6, linestyle="--",
               label=f"buy & hold ({bh_sharpe:+.2f})")
    a1.set_xlabel("Sharpe ratio", color="#8b949e")
    a1.set_ylabel("shuffles", color="#8b949e")
    a1.set_title("The winner is exactly what searching noise gives you",
                 color="#e6edf3", fontsize=10)
    _legend(a1, "upper left")

    a2.axhline(0, color="#8b949e", linewidth=0.8)
    a2.axvline(0, color="#8b949e", linewidth=0.8)
    a2.scatter(ins, oos, s=34, color="#58a6ff", alpha=0.85, edgecolor="#0d1117")
    lo, hi = float(np.min(ins)), float(np.max(ins))
    fit = np.polyfit(ins, oos, 1)
    xs = np.linspace(lo, hi, 20)
    a2.plot(xs, np.polyval(fit, xs), color="#f85149", linewidth=1.6,
            label=f"fit (rank corr {np.corrcoef(ins, oos)[0, 1]:+.2f})")
    best_i = int(np.argmax(ins))
    a2.scatter([ins[best_i]], [oos[best_i]], s=150, facecolor="none",
               edgecolor="#f0c674", linewidth=2, label="in-sample winner")
    a2.set_xlabel(f"in-sample Sharpe ({spans[0]})", color="#8b949e")
    a2.set_ylabel(f"out-of-sample Sharpe ({spans[1]})", color="#8b949e")
    a2.set_title("Picking the best stop anti-predicts the future",
                 color="#e6edf3", fontsize=10)
    _legend(a2)

    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor="#0d1117")
    plt.close(fig)
    print(f"saved -> {path}")


def fig_what_stops_do(closes, years, best_g, dd_rows, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax in (a1, a2):
        _dark(ax, fig)

    o, h, l, c = closes
    r_stop, diag = run_stop(o, h, l, c, best_g[1], best_g[0], best_g[2])
    curves = [(buy_hold(c), "#f0c674", "buy & hold"),
              (r_stop, "#58a6ff", f"{label(best_g)} (best of {len(GRID)})"),
              (blend(c, diag["time_in_market"]), "#8b949e",
               f"constant {diag['time_in_market']*100:.0f}% exposure")]
    for r, colour, name in curves:
        a1.plot(np.cumprod(1 + r) * 100, color=colour, linewidth=1.5, label=name)
    a1.set_yscale("log")
    ticks = list(range(0, len(c), TRADING_DAYS * 3))
    a1.set_xticks(ticks)
    a1.set_xticklabels([str(years[i]) for i in ticks], color="#8b949e", fontsize=8)
    a1.set_ylabel("growth of 100 (log scale)", color="#8b949e")
    a1.set_title("The best stop, and the same exposure held passively",
                 color="#e6edf3", fontsize=10)
    _legend(a1, "upper left")

    x = np.arange(len(dd_rows))
    w = 0.38
    a2.bar(x - w / 2, [-r["stop_dd"] * 100 for r in dd_rows], w,
           color="#58a6ff", label="stop-loss")
    a2.bar(x + w / 2, [-r["blend_dd"] * 100 for r in dd_rows], w,
           color="#8b949e", label="same exposure, held passively")
    a2.set_xticks(x)
    a2.set_xticklabels([r["label"].replace(" re21d", "") for r in dd_rows],
                       color="#8b949e", fontsize=8, rotation=12)
    a2.set_ylabel("max drawdown (%)", color="#8b949e")
    a2.set_title("Drawdown: usually — not always — better than holding less",
                 color="#e6edf3", fontsize=10)
    a2.grid(axis="x", linewidth=0)
    _legend(a2)

    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor="#0d1117")
    plt.close(fig)
    print(f"saved -> {path}")


# --------------------------------------------------------------------------- #
# Self-test
# --------------------------------------------------------------------------- #
def selftest():
    # 1. A series that only rises never triggers a stop.
    c = np.cumprod(np.r_[100.0, np.full(200, 1.001)])
    r, d = run_stop(c, c, c, c, 0.10, cost_bp=0)
    assert d["triggers"] == 0 and np.allclose(r[1:], buy_hold(c, 0)[1:]), "monotonic case"

    # 2. Hand-built trigger: level is 90, the day opens at 99 and lows at 89.
    c = np.array([100.0, 100.0, 100.0, 95.0]); h = c.copy()
    l = np.array([100.0, 100.0, 100.0, 89.0])
    o = np.array([100.0, 100.0, 100.0, 99.0])
    r, d = run_stop(o, h, l, c, 0.10, cost_bp=0, reentry_days=999)
    assert d["triggers"] == 1 and d["gapped"] == 0 and abs(r[3] - (90 / 100 - 1)) < 1e-12

    # 3. Same bar, but it opens at 85 — gapped through, so it cannot fill at 90.
    o2 = np.array([100.0, 100.0, 100.0, 85.0])
    r, d = run_stop(o2, h, l, c, 0.10, cost_bp=0, reentry_days=999)
    assert d["gapped"] == 1 and abs(r[3] - (85 / 100 - 1)) < 1e-12, "gap fill"

    # 4. No lookahead: altering the future must not change any past return.
    rng = np.random.default_rng(0)
    c = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, 400)))
    o = c * (1 + rng.normal(0, 0.002, 400))
    h = np.maximum(o, c) * 1.003
    l = np.minimum(o, c) * 0.997
    a, _ = run_stop(o, h, l, c, 0.10, cost_bp=0)
    mod = [x.copy() for x in (o, h, l, c)]
    for x in mod:
        x[300:] *= 1.5
    b, _ = run_stop(*mod, 0.10, cost_bp=0)
    assert np.allclose(a[:300], b[:300]), "lookahead detected"

    # 5. Costs are charged once per trade.
    r0, d0 = run_stop(o, h, l, c, 0.10, cost_bp=0)
    r1, _ = run_stop(o, h, l, c, 0.10, cost_bp=10)
    assert abs((r0.sum() - r1.sum()) - d0["trades"] * 10 / 1e4) < 1e-9, "cost accounting"

    # 6. Shuffling preserves the return distribution and buy-and-hold's Sharpe.
    O, H, L, C = shuffled_path(o, h, l, c, np.random.default_rng(1))
    assert abs(metrics(buy_hold(C))["sharpe"] - metrics(buy_hold(c))["sharpe"]) < 1e-9
    assert abs(np.prod(C[1:] / C[:-1]) - np.prod(c[1:] / c[:-1])) < 1e-6
    assert coherence_violations(O, H, L, C) == 0, "shuffle broke bar geometry"

    print("self-test: all checks passed (no trigger on a rising series, stop fill, "
          "gap fill, no lookahead, cost accounting, shuffle invariants)")


# --------------------------------------------------------------------------- #
def main():
    if "--selftest" in sys.argv:
        selftest()
        return
    selftest()
    os.makedirs(FIG, exist_ok=True)

    datasets = load_datasets()
    results = {"grid_size": len(GRID), "cost_bp_per_side": COST_BP,
               "n_shuffles": N_SHUFFLES, "seed": SEED, "datasets": {}}

    for name, (o, h, l, c, years, start, end) in datasets.items():
        print(f"\n{'='*72}\n{name}  ({start} .. {end}, {len(c)} bars)\n{'='*72}")
        assert coherence_violations(o, h, l, c) == 0, "incoherent OHLC bars"

        bh = metrics(buy_hold(c))
        print(f"  buy & hold: ann {bh['ann_return']*100:+6.2f}%  vol {bh['ann_vol']*100:5.1f}%  "
              f"Sharpe {bh['sharpe']:+.3f}  maxDD {bh['max_drawdown']*100:6.1f}%")

        # --- the full grid -------------------------------------------------- #
        rows = []
        for g in GRID:
            r, diag = run_stop(o, h, l, c, g[1], g[0], g[2])
            m = metrics(r)
            b = metrics(blend(c, diag["time_in_market"]))
            rows.append({"strategy": label(g), "kind": g[0], "pct": g[1], "reentry": g[2],
                         **m, **diag, "blend_sharpe": b["sharpe"],
                         "blend_max_drawdown": b["max_drawdown"]})
        rows.sort(key=lambda x: -x["sharpe"])
        best_row = rows[0]
        best_g = (best_row["kind"], best_row["pct"], best_row["reentry"])
        n_beat = sum(1 for x in rows if x["sharpe"] > bh["sharpe"])
        print(f"  best of {len(GRID)}: {best_row['strategy']}  Sharpe {best_row['sharpe']:+.3f}  "
              f"ann {best_row['ann_return']*100:+.2f}%  maxDD {best_row['max_drawdown']*100:.1f}%  "
              f"in market {best_row['time_in_market']*100:.1f}%")
        print(f"  {n_beat}/{len(GRID)} rules beat buy & hold on Sharpe")

        # --- the null --------------------------------------------------------- #
        print(f"  running {N_SHUFFLES} shuffles ...", flush=True)
        null_best, null_beat = null_distribution(o, h, l, c)
        p_best = float((null_best >= best_row["sharpe"]).mean())
        print(f"  NULL best-of-{len(GRID)}: mean {null_best.mean():+.3f}  "
              f"95th {np.percentile(null_best, 95):+.3f}   ->  p = {p_best:.3f}")
        print(f"  NULL rules beating buy & hold: mean {null_beat.mean():.1f}/{len(GRID)} "
              f"(real: {n_beat})")
        print(f"  searching {len(GRID)} rules on trendless data is worth "
              f"{null_best.mean() - bh['sharpe']:+.3f} Sharpe by itself; "
              f"the real winner is worth {best_row['sharpe'] - bh['sharpe']:+.3f}")

        # --- out of sample ---------------------------------------------------- #
        mid = int(np.median(years))
        tr, te = years <= mid, years > mid
        ins = grid_sharpes(o[tr], h[tr], l[tr], c[tr])
        oos = grid_sharpes(o[te], h[te], l[te], c[te])
        pick = int(np.argmax(ins))
        bh_oos = metrics(buy_hold(c[te]))["sharpe"]
        rank_corr = float(np.corrcoef(ins, oos)[0, 1])
        print(f"  OOS: chose {label(GRID[pick])} on <={mid} (Sharpe {ins[pick]:+.3f}); "
              f"after {mid} it scores {oos[pick]:+.3f} vs buy & hold {bh_oos:+.3f} "
              f"({oos[pick] - bh_oos:+.3f})")
        print(f"  OOS: in-sample vs out-of-sample Sharpe correlation across the grid "
              f"{rank_corr:+.3f}")

        # --- execution realism ------------------------------------------------ #
        gaps = []
        for g in GRID:
            r_real, d = run_stop(o, h, l, c, g[1], g[0], g[2])
            r_naive, _ = run_stop(o, h, l, c, g[1], g[0], g[2], gap_aware=False)
            if d["triggers"] >= 20:
                gaps.append({"strategy": label(g), "triggers": d["triggers"],
                             "gap_rate": d["gap_rate"],
                             "mean_slippage_pct": d["mean_slippage_pct"],
                             "sharpe_naive": metrics(r_naive)["sharpe"],
                             "sharpe_real": metrics(r_real)["sharpe"]})
        if gaps:
            gr = float(np.mean([x["gap_rate"] for x in gaps]))
            illusion = float(np.mean([x["sharpe_naive"] - x["sharpe_real"] for x in gaps]))
            print(f"  GAPS: across {len(gaps)} rules with >=20 triggers, "
                  f"{gr*100:.1f}% of stops gapped through; assuming a fill at the stop "
                  f"price overstates Sharpe by {illusion:+.3f} on average")

        # --- drawdown vs simply holding less ---------------------------------- #
        dd_rows = [{"label": label(g),
                    "stop_dd": next(x["max_drawdown"] for x in rows if x["strategy"] == label(g)),
                    "blend_dd": next(x["blend_max_drawdown"] for x in rows if x["strategy"] == label(g)),
                    "time_in_market": next(x["time_in_market"] for x in rows if x["strategy"] == label(g))}
                   for g in [("trailing", p, 21) for p in STOP_LEVELS]]
        print("  DRAWDOWN vs the same exposure held passively:")
        for row in dd_rows:
            verdict = "better" if row["stop_dd"] > row["blend_dd"] else "WORSE"
            print(f"    {row['label']:22s} in market {row['time_in_market']*100:5.1f}%  "
                  f"stop {row['stop_dd']*100:6.1f}%  passive {row['blend_dd']*100:6.1f}%  [{verdict}]")

        # --- the worst year: does the stop actually protect? ------------------ #
        bh_daily = buy_hold(c)
        year_return = {y: float(np.prod(1 + bh_daily[years == y]) - 1)
                       for y in sorted(set(years.tolist()))}
        worst = min(year_return, key=year_return.get)
        crash = {"year": int(worst), "buy_hold": year_return[worst]}
        for g in [("trailing", 0.05, 21), ("trailing", 0.10, 21), ("fixed", 0.10, 21)]:
            sub = [x[years == worst] for x in (o, h, l, c)]
            crash[label(g)] = float(np.prod(1 + run_stop(*sub, g[1], g[0], g[2])[0]) - 1)
        print(f"  WORST YEAR ({worst}): buy & hold {crash['buy_hold']*100:+.1f}%  " +
              "  ".join(f"{k} {v*100:+.1f}%" for k, v in crash.items()
                        if k not in ("year", "buy_hold")))

        # --- the mechanism ---------------------------------------------------- #
        drag = {label(g): round_trip_drag(o, h, l, c, g[1], g[0], g[2])
                for g in [("trailing", 0.05, 21), ("trailing", 0.10, 21), ("trailing", 0.05, 5)]}
        print("  MECHANISM (sell low, buy back where?):")
        for k, v in drag.items():
            print(f"    {k:22s} {v['round_trips']:3d} round trips, bought back higher "
                  f"{v['bought_back_higher']*100:.1f}% of the time, "
                  f"avg drag {v['avg_drag_pct']:+.2f}%")

        results["datasets"][name] = {
            "start": start, "end": end, "n_bars": len(c),
            "buy_hold": bh, "grid": rows, "best": best_row,
            "n_beating_buy_hold": n_beat,
            "null": {"mean_best": float(null_best.mean()),
                     "median_best": float(np.median(null_best)),
                     "pct95_best": float(np.percentile(null_best, 95)),
                     "max_best": float(null_best.max()),
                     "p_value": p_best,
                     "mean_n_beating": float(null_beat.mean()),
                     "search_premium": float(null_best.mean() - bh["sharpe"])},
            "out_of_sample": {"split_year": int(mid),
                              "chosen": label(GRID[pick]),
                              "in_sample_sharpe": float(ins[pick]),
                              "out_of_sample_sharpe": float(oos[pick]),
                              "buy_hold_out_of_sample": float(bh_oos),
                              "rank_correlation": rank_corr,
                              "in_sample": ins.tolist(), "oos": oos.tolist()},
            "gaps": gaps, "drawdown_vs_blend": dd_rows, "mechanism": drag,
            "worst_year": crash,
        }

        if name == "NASDAQ Composite":
            fig_search(null_best, best_row["sharpe"], bh["sharpe"], ins, oos,
                       (f"{years[0]}–{mid}", f"{mid+1}–{years[-1]}"),
                       os.path.join(FIG, "search.png"))
            fig_what_stops_do((o, h, l, c), years, best_g, dd_rows,
                              os.path.join(FIG, "what_stops_do.png"))

    # --- cost sensitivity (reported once, on the primary series) -------------- #
    o, h, l, c, years, _, _ = datasets["NASDAQ Composite"]
    results["cost_sensitivity"] = []
    print("\n=== COST SENSITIVITY (NASDAQ Composite) ===")
    for cost in (0.0, 1.0, 5.0):
        s = grid_sharpes(o, h, l, c, cost)
        bhs = metrics(buy_hold(c, cost))["sharpe"]
        results["cost_sensitivity"].append(
            {"bp_per_side": cost, "best": float(s.max()), "buy_hold": float(bhs),
             "n_beating": int((s > bhs).sum())})
        print(f"  {cost:3.1f} bp/side: best-of-{len(GRID)} {s.max():+.3f}  "
              f"buy & hold {bhs:+.3f}  {int((s > bhs).sum())}/{len(GRID)} beat it")

    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print("\nwrote results.json")


if __name__ == "__main__":
    main()
