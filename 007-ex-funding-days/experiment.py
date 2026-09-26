#!/usr/bin/env python3
# © 2026 Neil Gilani (Martingale) — MIT License.
# Research Note 007 — Ex-Funding Days: do perpetual-futures prices adjust to
# scheduled funding payments?
#
# Reproducible:  pip install numpy pandas statsmodels matplotlib pyarrow
#                python pipeline.py        # ~15 min, streams the public archive
#                python experiment.py      # runs the pre-registered analysis
# Self-test only: python experiment.py --selftest
"""Implements PREREGISTRATION.md (commit 377bf67) section by section. Every test is
labelled with the hypothesis it answers. Anything not in the pre-registration is
labelled EXPLORATORY and never enters the headline.

At a funding settlement T a long pays F x notional to a short. In a frictionless
market a round trip across T earns zero, so the perpetual's basis over its index
must rise by F across the settlement instant:  J_T = basis(T+) - basis(T-) = F_T.
The ex-dividend price drop, mirrored. The estimand is beta in J = a + beta F:
the share of the funding payment the market prices at the moment it is paid."""
from __future__ import annotations

import glob
import io
import json
import math
import os
import sys
import zipfile

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FIG = os.path.join(HERE, "paper", "figures")
BP = 1e4
SPLIT = pd.Timestamp("2025-01-01")          # pre-registered period split
ABS_BINS = [(0, 1), (1, 5), (5, 10), (10, np.inf)]          # H4, |F| in bp
PATH_BINS = [("F ≤ −10 bp", -np.inf, -10), ("−10 < F < 0", -10, 0),
             ("0 ≤ F ≤ +1 (baseline)", 0, 1), ("+1 < F ≤ +10", 1, 10), ("F > +10 bp", 10, np.inf)]
COSTS_BP = (2.0, 4.0, 10.0)                 # round-trip, for the descriptive P&L

# figure tokens (validated with the dataviz palette checker on #0d1117)
SURFACE, INK, INK2, GRID, EDGE = "#0d1117", "#e6edf3", "#8b949e", "#21262d", "#30363d"
C_SETTLE, C_PLACEBO = "#3987e5", "#6e7681"


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_funding(sym):
    """Settlement minute, funding rate (bp) and interval (h) for one contract."""
    rows = []
    for f in sorted(glob.glob(os.path.join(DATA, "funding", f"{sym}-fundingRate-*.zip"))):
        with zipfile.ZipFile(f) as z:
            lines = z.read(z.namelist()[0]).decode().strip().splitlines()
        if lines and not lines[0][:1].isdigit():
            lines = lines[1:]
        for ln in lines:
            p = ln.split(",")
            rows.append((int(round(int(p[0]) / 60000)), float(p[1]) if p[1] else np.nan,
                         float(p[2]) * BP))
    fd = pd.DataFrame(rows, columns=["minute", "interval", "F"])
    return fd.drop_duplicates("minute").sort_values("minute").reset_index(drop=True)


def load_hours(sym):
    z = np.load(os.path.join(DATA, "contracts", f"{sym}.npz"))
    table = {k[2:]: z[k] for k in z.files if k.startswith("t_")}
    paths = {k[2:]: z[k] for k in z.files if k.startswith("p_")}
    return pd.DataFrame(table), paths


def attach_funding(minutes, fd):
    """For each hour mark: is it a settlement, and the F / interval of the next
    settlement at or after it (itself, if it is one). Marks after the last
    settlement get NaN."""
    sm = fd.minute.to_numpy()
    i = np.searchsorted(sm, minutes, side="left")
    ok = i < len(sm)
    ii = np.where(ok, i, 0)
    settle = ok & (sm[ii] == minutes)
    F = np.where(ok, fd.F.to_numpy()[ii], np.nan)
    interval = np.where(ok, fd.interval.to_numpy()[ii], np.nan)
    return settle, F, interval


def build_events(sym):
    """One row per hour mark with the pre-registered variables (all in bp)."""
    h, paths = load_hours(sym)
    fd = load_funding(sym)
    settle, F, interval = attach_funding(h.minute.to_numpy(), fd)
    with np.errstate(divide="ignore", invalid="ignore"):
        ev = pd.DataFrame({
            "sym": sym,
            "minute": h.minute.to_numpy(),
            "settle": settle,
            "F": F,
            "interval": interval,
            # primary outcome: premium-index change across the mark
            "J": (h.pi_post - h.pi_pre).to_numpy() * BP,
            "pi_level": h.pi_pre.to_numpy() * BP,
            "dpi_pre15": (h.pi_pre - h.pi_m15).to_numpy() * BP,
            "dpi_post15": (h.pi_p15 - h.pi_post).to_numpy() * BP,
            # traded prices
            "perp_gap": np.log(h.pf_post / h.pf_pre).to_numpy() * BP,
            "spot_gap": np.log(h.sp_post / h.sp_pre).to_numpy() * BP,
            "trades_pre": h.pf_n_pre.to_numpy(), "trades_post": h.pf_n_post.to_numpy(),
            # order flow
            "ofi_pre": ((2 * h.buy_pre - h.vol_pre) / h.vol_pre).to_numpy(),
            "ofi_post": ((2 * h.buy_post - h.vol_post) / h.vol_post).to_numpy(),
            "vol_ratio": (h.vol_pre / (h.vol_base / 3)).to_numpy(),
        })
    ev["J_trade"] = ev.perp_gap - ev.spot_gap
    ev["clock"] = (ev.minute // 60) % 24
    ev["ts"] = pd.to_datetime(ev.minute * 60, unit="s")
    return ev, paths, fd


# --------------------------------------------------------------------------- #
# Inference
# --------------------------------------------------------------------------- #
def ols(y, X, groups, names, groups2=None):
    """OLS with standard errors clustered by `groups` (and `groups2`, two-way)."""
    import statsmodels.api as sm
    X = np.column_stack([np.ones(len(y))] + [np.asarray(x, float) for x in X])
    m = sm.OLS(np.asarray(y, float), X)
    if groups2 is None:
        r = m.fit(cov_type="cluster", cov_kwds={"groups": np.asarray(groups)})
    else:
        g = np.column_stack([pd.factorize(groups)[0], pd.factorize(groups2)[0]])
        r = m.fit(cov_type="cluster", cov_kwds={"groups": g})
    out = {"n": int(len(y)), "n_clusters": int(pd.Series(groups).nunique())}
    for j, nm in enumerate(["const"] + names):
        out[nm] = {"coef": float(r.params[j]), "se": float(r.bse[j]),
                   "t": float(r.tvalues[j]), "p": float(r.pvalues[j])}
    return out


def vs_one(res, name="F"):
    """t-test of a coefficient against 1 (the frictionless benchmark)."""
    from scipy import stats
    c, se = res[name]["coef"], res[name]["se"]
    t = (c - 1) / se
    return {"t": t, "p": float(2 * stats.norm.sf(abs(t)))}


def holm(pvals):
    """Holm step-down adjusted p-values, returned in the input order."""
    p = np.asarray(pvals, float)
    order = np.argsort(p)
    m = len(p)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p[i]))
        adj[i] = running
    return adj.tolist()


def directional_p(res, name, sign):
    """Two-sided p if the coefficient has the predicted sign, else 1 — a result in
    the wrong direction does not count as support."""
    return res[name]["p"] if np.sign(res[name]["coef"]) == sign else 1.0


# --------------------------------------------------------------------------- #
# The pre-registered tests
# --------------------------------------------------------------------------- #
def h1(s):
    r = ols(s.J, [s.F], s.minute, ["F"])
    r["vs_one"] = vs_one(r)
    return r


def h2(ev):
    d = ev.dropna(subset=["J", "F"])
    S = d.settle.astype(float)
    r = ols(d.J, [d.F, S, d.F * S], d.minute, ["F", "settle", "F_x_settle"])
    p = d[~d.settle]
    r["placebo"] = ols(p.J, [p.F], p.minute, ["F"])
    return r


def switching_contracts(fds):
    """Contracts whose funding interval changed at least once in the sample."""
    return [s for s, fd in fds.items() if fd.interval.dropna().nunique() > 1]


def h3(ev, fds):
    """Among contracts that changed funding interval: clock hours that are
    settlements in some regime and not in another. Compare the F-slope at those
    clock hours when they settle versus when they do not."""
    parts = []
    for sym in switching_contracts(fds):
        e = ev[(ev.sym == sym)].dropna(subset=["J", "F"])
        by_clock = e.groupby("clock").settle.agg(["min", "max"])
        switching = by_clock[(by_clock["min"] == False) & (by_clock["max"] == True)].index  # noqa: E712
        parts.append(e[e.clock.isin(switching)])
    d = pd.concat(parts)
    S = d.settle.astype(float)
    r = ols(d.J, [d.F, S, d.F * S], d.minute, ["F", "settle", "F_x_settle"])
    r["contracts"] = int(d.sym.nunique())
    r["n_settle"] = int(d.settle.sum())
    r["n_nonsettle"] = int((~d.settle).sum())
    r["beta_when_settling"] = r["F"]["coef"] + r["F_x_settle"]["coef"]
    r["beta_when_not"] = r["F"]["coef"]
    # each regime's slope with its own clustered SE, for the figure's intervals
    for lab, m in (("settling", d.settle), ("not_settling", ~d.settle)):
        x = d[m]
        r[f"slope_{lab}"] = ols(x.J, [x.F], x.minute, ["F"])["F"]
    return r


def h4(s):
    out = []
    a = s.F.abs()
    for lo, hi in ABS_BINS:
        m = (a > lo) & (a <= hi) if lo > 0 else (a <= hi)
        d = s[m]
        r = ols(d.J, [d.F], d.minute, ["F"])
        out.append({"bin": f"{lo}-{hi}", "n": int(m.sum()), "beta": r["F"]["coef"],
                    "se": r["F"]["se"], "mean_F": float(d.F.mean()), "mean_J": float(d.J.mean())})
    # operationalisation: the top bin's slope exceeds the bottom bin's
    bins = np.select([(a <= 1), (a > 1) & (a <= 5), (a > 5) & (a <= 10)], [0, 1, 2], 3)
    X, names = [], []
    for k in range(4):
        X += [(bins == k).astype(float), s.F * (bins == k)]
        names += [f"bin{k}", f"F_bin{k}"]
    import statsmodels.api as sm
    Xm = np.column_stack(X)
    fit = sm.OLS(s.J.to_numpy(), Xm).fit(cov_type="cluster", cov_kwds={"groups": s.minute.to_numpy()})
    L = np.zeros(Xm.shape[1]); L[names.index("F_bin3")] = 1; L[names.index("F_bin0")] = -1
    tt = fit.t_test(L)
    diff = float(np.squeeze(tt.effect)); p = float(np.squeeze(tt.pvalue))
    return {"bins": out, "top_minus_bottom": diff, "p": p}


def h5(s):
    a = s.dropna(subset=["ofi_pre"])
    b = s.dropna(subset=["ofi_post"])
    pre = ols(a.ofi_pre, [a.F], a.minute, ["F"])
    post = ols(b.ofi_post, [b.F], b.minute, ["F"])
    p = max(directional_p(pre, "F", -1), directional_p(post, "F", +1))
    return {"pre": pre, "post": post, "p": p}


def h6(s):
    d = s.dropna(subset=["J_trade"])
    d = d[(d.trades_pre > 0) & (d.trades_post > 0)]
    trade = ols(d.J_trade, [d.F], d.minute, ["F"])
    spot = ols(d.spot_gap, [d.F], d.minute, ["F"])
    perp = ols(d.perp_gap, [d.F], d.minute, ["F"])
    return {"trade": trade, "spot": spot, "perp": perp, "p": directional_p(trade, "F", +1)}


def robustness(s):
    out = {}
    for lab, m in [("2020-2024", s.ts < SPLIT), ("2025-2026", s.ts >= SPLIT)]:
        d = s[m]
        r = ols(d.J, [d.F], d.minute, ["F"])
        out[lab] = {"n": r["n"], **r["F"], "vs_one": vs_one(r)}
    r = ols(s.J, [s.F], s.minute, ["F"], groups2=s.sym)
    out["two_way_cluster"] = r["F"]
    import statsmodels.api as sm
    q = sm.QuantReg(s.J.to_numpy(), sm.add_constant(s.F.to_numpy())).fit(q=0.5)
    out["median_regression"] = {"coef": float(q.params[1]), "se": float(q.bse[1])}
    lo, hi = np.percentile(s.J, [1, 99])
    r = ols(s.J.clip(lo, hi), [s.F], s.minute, ["F"])
    out["winsorised_1pct"] = r["F"]
    d = s[s.sym.isin(["BTCUSDT", "ETHUSDT"])]
    r = ols(d.J, [d.F], d.minute, ["F"])
    out["btc_eth"] = {"n": r["n"], **r["F"]}
    d = s[(s.F - 1).abs() > 1e-6]
    r = ols(d.J, [d.F], d.minute, ["F"])
    out["excluding_baseline"] = {"n": r["n"], **r["F"]}
    return out


# --------------------------------------------------------------------------- #
# Descriptive (pre-registered as descriptive) and exploratory
# --------------------------------------------------------------------------- #
def capture_pnl(s):
    """Receiving side, hedged against the index: collect |F| at T, lose the basis
    jump in its direction. P&L = |F| - sign(F) * J, before costs."""
    rows = []
    a = s.F.abs()
    for lo, hi in ABS_BINS:
        m = (a > lo) & (a <= hi) if lo > 0 else (a <= hi)
        d = s[m]
        gross = (d.F.abs() - np.sign(d.F) * d.J)
        row = {"bin": f"{lo}-{hi}", "n": int(m.sum()), "mean_abs_F": float(d.F.abs().mean()),
               "gross_capture_bp": float(gross.mean()),
               "capture_share": float(gross.mean() / d.F.abs().mean())}
        for c in COSTS_BP:
            row[f"net_{int(c)}bp"] = float(gross.mean() - c)
        rows.append(row)
    return rows


def event_paths(all_paths, all_fd):
    """Mean premium-index path, T-60m..T+60m, relative to T-61m, by F bin — for
    8-hour settlements (00/08/16) and for the 04/12/20 marks while they are not
    settlements. Descriptive."""
    acc = {(lab, kind): [] for lab, *_ in PATH_BINS for kind in ("settle", "placebo")}
    for sym, paths in all_paths.items():
        fd = all_fd[sym]
        settle, F, interval = attach_funding(paths["minute"], fd)
        clock = (paths["minute"] // 60) % 24
        rel = (paths["pi"] - paths["pi"][:, [0]]) * BP
        ok = ~np.isnan(rel).any(axis=1)
        is8 = interval == 8
        for lab, lo, hi in PATH_BINS:
            fb = (F > lo) & (F <= hi) if np.isfinite(lo) else (F <= hi)
            if lab.startswith("0 ≤"):
                fb = (F >= 0) & (F <= 1)
            m_s = ok & fb & settle & is8 & np.isin(clock, [0, 8, 16])
            m_p = ok & fb & ~settle & is8 & np.isin(clock, [4, 12, 20])
            acc[(lab, "settle")].append(rel[m_s])
            acc[(lab, "placebo")].append(rel[m_p])
    out = {}
    for k, v in acc.items():
        arr = np.concatenate(v) if v else np.empty((0, 121))
        out[k] = {"n": int(len(arr)), "mean": arr.mean(axis=0) if len(arr) else None,
                  "se": arr.std(axis=0, ddof=1) / math.sqrt(len(arr)) if len(arr) > 1 else None}
    return out


def per_contract(s):
    rows = []
    for sym, d in s.groupby("sym"):
        if len(d) < 500 or d.F.std() == 0:
            continue
        r = ols(d.J, [d.F], d.minute, ["F"])
        rows.append({"sym": sym, "n": r["n"], "beta": r["F"]["coef"], "se": r["F"]["se"]})
    return rows


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
def _ax(ax):
    ax.set_facecolor(SURFACE)
    ax.tick_params(colors=INK2, labelsize=8)
    for sp in ax.spines.values():
        sp.set_color(EDGE)
    ax.grid(color=GRID, linewidth=0.6)


def _legend(ax, **kw):
    leg = ax.legend(facecolor="#161b22", edgecolor=EDGE, fontsize=8, **kw)
    for t in leg.get_texts():
        t.set_color(INK)


def fig_binscatter(s, placebo, path, nb=24):
    """Binned scatter of the jump J against F, settlement vs. placebo, with the
    frictionless line (slope 1) and the no-adjustment line (slope 0)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8.6, 5.2))
    fig.patch.set_facecolor(SURFACE)
    _ax(ax)
    lim = np.nanpercentile(s.F, [0.5, 99.5])
    xs = np.linspace(lim[0], lim[1], 50)
    ax.plot(xs, xs, color=INK2, linewidth=1.2, linestyle="--", label="frictionless: J = F")
    ax.axhline(0, color=INK2, linewidth=0.8)
    for d, colour, name, mk in ((placebo, C_PLACEBO, "non-settlement hour marks (placebo)", "s"),
                                (s, C_SETTLE, "funding settlements", "o")):
        d = d[(d.F >= lim[0]) & (d.F <= lim[1])]
        q = pd.qcut(d.F.rank(method="first"), nb, labels=False)
        g = d.groupby(q).agg(F=("F", "mean"), J=("J", "mean"), se=("J", "sem"))
        ax.errorbar(g.F, g.J, yerr=1.96 * g.se, fmt=mk, ms=6, color=colour, ecolor=colour,
                    elinewidth=1, capsize=0, label=name, mec=SURFACE, mew=1.5)
    ax.set_xlabel("funding rate paid at the mark, F (bp)", color=INK2)
    ax.set_ylabel("basis jump across the mark, J (bp)", color=INK2)
    ax.set_title("Does the basis jump by the funding payment at settlement?", color=INK, fontsize=11)
    _legend(ax, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(f"saved -> {path}")


def fig_paths(paths_res, path, title="The basis around 8-hour settlements, by the funding rate being paid"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, len(PATH_BINS), figsize=(13, 3.9), sharey=True)
    fig.patch.set_facecolor(SURFACE)
    t = np.arange(-60, 61)
    for ax, (lab, *_r) in zip(axes, PATH_BINS):
        _ax(ax)
        for kind, colour, name in (("placebo", C_PLACEBO, "non-settlement"), ("settle", C_SETTLE, "settlement")):
            r = paths_res[(lab, kind)]
            if r["mean"] is None:
                continue
            ax.plot(t, r["mean"], color=colour, linewidth=2, label=f"{name} (n={r['n']:,})")
            ax.fill_between(t, r["mean"] - 1.96 * r["se"], r["mean"] + 1.96 * r["se"],
                            color=colour, alpha=0.18, linewidth=0)
        ax.axvline(0, color=INK2, linewidth=0.8, linestyle=":")
        ax.set_title(lab, color=INK, fontsize=9)
        ax.set_xlabel("minutes from the mark", color=INK2, fontsize=8)
        _legend(ax, loc="lower left" if lab.startswith("F ≤") or lab.startswith("−") else "upper left")
    axes[0].set_ylabel("premium index vs. T−61m (bp)", color=INK2)
    fig.suptitle(title, color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(f"saved -> {path}")


def fig_natural_experiment(r3, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    fig.patch.set_facecolor(SURFACE)
    _ax(ax)
    ax.set_axisbelow(True)
    ax.grid(axis="x", linewidth=0)
    a, b = r3["slope_not_settling"], r3["slope_settling"]
    ax.bar([0], [a["coef"]], color=C_PLACEBO, width=0.55, zorder=2)
    ax.bar([1], [b["coef"]], color=C_SETTLE, width=0.55, zorder=2)
    ax.errorbar([0, 1], [a["coef"], b["coef"]], yerr=[1.96 * a["se"], 1.96 * b["se"]], fmt="none",
                ecolor=INK, elinewidth=1.2, capsize=4, zorder=3)
    ax.axhline(1, color=INK2, linestyle="--", linewidth=1)
    ax.axhline(0, color=INK2, linewidth=0.8)
    ax.text(1.62, 1.03, "frictionless (β = 1)", color=INK2, fontsize=8, ha="right", va="bottom")
    for x, v in ((0, a["coef"]), (1, b["coef"])):
        ax.text(x, v + 0.07, f"β = {v:.2f}", color=INK, fontsize=9, ha="center")
    ax.set_xticks([0, 1])
    ax.set_xticklabels([f"same clock hours,\nwhile they do not settle\n(n = {r3['n_nonsettle']:,})",
                        f"same clock hours,\nwhile they settle\n(n = {r3['n_settle']:,})"],
                       color=INK2, fontsize=8)
    ax.set_ylabel("share of funding priced at the mark (β)", color=INK2)
    ax.set_ylim(-0.1, 1.15)
    ax.set_xlim(-0.6, 1.7)
    ax.set_title(f"Natural experiment: {r3['contracts']} contracts that changed funding interval",
                 color=INK, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print(f"saved -> {path}")


# --------------------------------------------------------------------------- #
# Self-test on synthetic data with planted effects
# --------------------------------------------------------------------------- #
def selftest():
    rng = np.random.default_rng(0)

    # 1. attach_funding assigns the right settlement flag and next-settlement F.
    fd = pd.DataFrame({"minute": [480, 960, 1440], "interval": [8, 8, 8], "F": [1.0, 5.0, -3.0]})
    s, F, iv = attach_funding(np.array([420, 480, 540, 960, 1500]), fd)
    assert s.tolist() == [False, True, False, True, False]
    assert F[:4].tolist() == [1.0, 1.0, 5.0, 5.0] and np.isnan(F[4])

    # 2. Planted beta is recovered, and clustered SEs exceed naive ones when
    #    events at the same instant share a common shock.
    n_t, n_s = 3000, 20
    minute = np.repeat(np.arange(n_t), n_s)
    Fv = rng.choice([1.0] * 5 + [-2.0, 3.0, 8.0, -12.0, 25.0], size=n_t * n_s)
    common = np.repeat(rng.normal(0, 2.0, n_t), n_s)
    y = 0.6 * Fv + common + rng.normal(0, 1.5, n_t * n_s)
    r = ols(y, [Fv], minute, ["F"])
    assert abs(r["F"]["coef"] - 0.6) < 0.03, r["F"]
    import statsmodels.api as sm
    naive = sm.OLS(y, sm.add_constant(Fv)).fit()
    assert r["F"]["se"] > naive.bse[1] * 0.9
    assert vs_one(r)["p"] < 1e-6

    # 3. The interaction recovers settlement-minus-placebo.
    settle = rng.random(n_t * n_s) < 0.3
    y2 = np.where(settle, 0.8 * Fv, 0.1 * Fv) + rng.normal(0, 1.0, n_t * n_s)
    ev = pd.DataFrame({"J": y2, "F": Fv, "settle": settle, "minute": minute})
    r2 = h2(ev)
    assert abs(r2["F_x_settle"]["coef"] - 0.7) < 0.05 and abs(r2["placebo"]["F"]["coef"] - 0.1) < 0.05

    # 4. A null effect is not detected (false-positive guard).
    y3 = rng.normal(0, 3, n_t * n_s)
    r3 = ols(y3, [Fv], minute, ["F"])
    assert abs(r3["F"]["t"]) < 3.5

    # 5. Holm correction matches a hand calculation.
    assert np.allclose(holm([0.01, 0.04, 0.03, 0.2]), [0.04, 0.09, 0.09, 0.2])

    # 6. directional_p refuses a wrong-signed result.
    assert directional_p({"F": {"coef": -1.0, "p": 0.001}}, "F", +1) == 1.0

    print("self-test: all checks passed (settlement join, planted beta, clustered SEs, "
          "interaction, null control, Holm, directional p)")


# --------------------------------------------------------------------------- #
def main():
    if "--selftest" in sys.argv:
        selftest()
        return
    selftest()
    os.makedirs(FIG, exist_ok=True)
    syms = [s.strip() for s in open(os.path.join(HERE, "universe.txt")) if s.strip()]

    evs, all_paths, fds = [], {}, {}
    for sym in syms:
        if not os.path.exists(os.path.join(DATA, "contracts", f"{sym}.npz")):
            print(f"  missing extract for {sym} — run pipeline.py")
            continue
        ev, paths, fd = build_events(sym)
        evs.append(ev)
        all_paths[sym] = paths
        fds[sym] = fd
    ev = pd.concat(evs, ignore_index=True)
    ev = ev[ev.F.notna()]

    # ---- data rule (pre-registered): drop events missing either adjacent bar
    settle_all = ev[ev.settle]
    s = settle_all.dropna(subset=["J"])
    placebo = ev[~ev.settle].dropna(subset=["J"])
    n_funding = int(sum(len(f) for f in fds.values()))
    print(f"\ncontracts: {ev.sym.nunique()}   funding settlements in files: {n_funding:,}")
    print(f"settlement events matched to an hour mark: {len(settle_all):,}   "
          f"dropped for a missing adjacent bar: {len(settle_all) - len(s):,}   used: {len(s):,}")
    print(f"placebo hour marks used: {len(placebo):,}")

    res = {"prereg_commit": "377bf67", "n_contracts": int(ev.sym.nunique()),
           "n_settlements_in_files": n_funding, "n_settlements_matched": int(len(settle_all)),
           "n_settlements_used": int(len(s)), "n_placebo": int(len(placebo)),
           "sample": [str(s.ts.min()), str(s.ts.max())]}

    # ---- H1
    r1 = h1(s)
    res["H1"] = r1
    print(f"\nH1  J = a + beta*F at settlement:  beta = {r1['F']['coef']:.3f} "
          f"(se {r1['F']['se']:.3f}, t {r1['F']['t']:.1f}, p {r1['F']['p']:.2g})   "
          f"vs 1: t {r1['vs_one']['t']:.1f}, p {r1['vs_one']['p']:.2g}   alpha = {r1['const']['coef']:.3f} bp")

    # ---- H2..H6
    r2, r3, r4, r5, r6 = h2(ev), h3(ev, fds), h4(s), h5(s), h6(s)
    res.update({"H2": r2, "H3": r3, "H4": r4, "H5": r5, "H6": r6})
    ps = [directional_p(r2, "F_x_settle", +1), directional_p(r3, "F_x_settle", +1),
          r4["p"] if r4["top_minus_bottom"] > 0 else 1.0, r5["p"], r6["p"]]
    adj = holm(ps)
    res["secondary_holm"] = dict(zip(["H2", "H3", "H4", "H5", "H6"], adj))
    res["secondary_raw"] = dict(zip(["H2", "H3", "H4", "H5", "H6"], ps))
    print(f"H2  placebo beta = {r2['placebo']['F']['coef']:.3f} (se {r2['placebo']['F']['se']:.3f});  "
          f"settle - placebo = {r2['F_x_settle']['coef']:.3f} (t {r2['F_x_settle']['t']:.1f})")
    print(f"H3  {r3['contracts']} switching contracts: beta when settling {r3['beta_when_settling']:.3f} vs "
          f"when not {r3['beta_when_not']:.3f}; difference {r3['F_x_settle']['coef']:.3f} "
          f"(t {r3['F_x_settle']['t']:.1f})   n settle {r3['n_settle']:,} / not {r3['n_nonsettle']:,}")
    print("H4  beta by |F| bin: " + "  ".join(f"[{b['bin']}] {b['beta']:.3f}±{b['se']:.3f} (n {b['n']:,})"
                                          for b in r4["bins"]))
    print(f"    top - bottom = {r4['top_minus_bottom']:.3f}, p {r4['p']:.2g}")
    print(f"H5  OFI pre slope {r5['pre']['F']['coef']:.5f} (t {r5['pre']['F']['t']:.1f});  "
          f"post slope {r5['post']['F']['coef']:.5f} (t {r5['post']['F']['t']:.1f})")
    print(f"H6  traded-price beta {r6['trade']['F']['coef']:.3f} (t {r6['trade']['F']['t']:.1f});  "
          f"perp gap {r6['perp']['F']['coef']:.3f};  spot gap {r6['spot']['F']['coef']:.3f} "
          f"(t {r6['spot']['F']['t']:.1f})")
    print("Holm-adjusted p (H2..H6): " + ", ".join(f"{k} {v:.2g}" for k, v in res["secondary_holm"].items()))

    # ---- robustness
    rb = robustness(s)
    res["robustness"] = rb
    print("\nROBUSTNESS")
    for k, v in rb.items():
        print(f"  {k:20s} beta {v['coef']:.3f} (se {v['se']:.3f})" + (f"  n {v['n']:,}" if "n" in v else ""))

    # ---- descriptive + exploratory
    res["capture_pnl"] = capture_pnl(s)
    print("\nDESCRIPTIVE: receiving-side capture (|F| - sign(F)*J), by |F| bin")
    for row in res["capture_pnl"]:
        print(f"  |F| {row['bin']:>9s} bp  n {row['n']:7,}  mean |F| {row['mean_abs_F']:6.2f}  "
              f"gross {row['gross_capture_bp']:+6.2f}  share {row['capture_share']:+.2f}  "
              f"net@4bp {row['net_4bp']:+6.2f}")
    res["per_contract"] = per_contract(s)
    pr = event_paths(all_paths, fds)
    res["paths_n"] = {f"{k[0]} | {k[1]}": v["n"] for k, v in pr.items()}

    fig_paths(pr, os.path.join(FIG, "paths.png"))
    fig_natural_experiment(r3, os.path.join(FIG, "natural_experiment.png"))

    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(res, f, indent=2, default=float)
    print("\nwrote results.json")


if __name__ == "__main__":
    main()
