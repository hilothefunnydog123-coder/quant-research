#!/usr/bin/env python3
# © 2026 Neil Gilani (Martingale) — MIT License.
# Research Note 007 — the pre-registration addendum (commit e51757a).
#
#   python holdout.py            # discovery estimates + the holdout tests E1–E5
"""The addendum's window hypotheses were chosen after seeing the discovery paths,
so on the 62 discovery contracts they are estimates, not tests. They are tested
once, on 34 contracts listed in 2021 that were not downloaded until the addendum
was pushed.

Windows, from 1-minute bar closes (paths store closes of bars T-61 .. T+59):
    PRE  close(T-61) -> close(T-2)      ~T-60m  -> ~T-65s
    W    close(T-2)  -> close(T+1)      ~T-65s  -> ~T+115s   (spans Binance's
                                                              <=1-min settlement)
    POST close(T+1)  -> close(T+59)     ~T+115s -> ~T+60m
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
import pandas as pd

import experiment as E

HERE = E.HERE
K_PRE0, K_W0, K_W1, K_POST1 = 0, 59, 62, 120      # path column indices


def window_events(syms):
    """One row per complete path (hour marks at 00/04/../20 UTC)."""
    rows = []
    for sym in syms:
        path = os.path.join(E.DATA, "contracts", f"{sym}.npz")
        if not os.path.exists(path):
            continue
        hours, paths = E.load_hours(sym)
        fd = E.load_funding(sym)
        settle, F, interval = E.attach_funding(paths["minute"], fd)
        pi = paths["pi"].astype(float)
        sp = paths["sp"].astype(float)
        pf = paths["pf"].astype(float)
        with np.errstate(divide="ignore", invalid="ignore"):
            d = pd.DataFrame({
                "sym": sym, "minute": paths["minute"], "settle": settle, "F": F,
                "interval": interval,
                "PRE": (pi[:, K_W0] - pi[:, K_PRE0]) * E.BP,
                "W": (pi[:, K_W1] - pi[:, K_W0]) * E.BP,
                "POST": (pi[:, K_POST1] - pi[:, K_W1]) * E.BP,
                "sPRE": np.log(sp[:, K_W0] / sp[:, K_PRE0]) * E.BP,
                "sW": np.log(sp[:, K_W1] / sp[:, K_W0]) * E.BP,
                "sPOST": np.log(sp[:, K_POST1] / sp[:, K_W1]) * E.BP,
                "pPRE": np.log(pf[:, K_W0] / pf[:, K_PRE0]) * E.BP,
                "pW": np.log(pf[:, K_W1] / pf[:, K_W0]) * E.BP,
                "pPOST": np.log(pf[:, K_POST1] / pf[:, K_W1]) * E.BP,
            })
        # the instantaneous (original H1) jump for the same events
        inst = pd.DataFrame({"minute": hours.minute.to_numpy(),
                             "J_inst": (hours.pi_post - hours.pi_pre).to_numpy() * E.BP})
        d = d.merge(inst, on="minute", how="left")
        rows.append(d[d.F.notna()])
    d = pd.concat(rows, ignore_index=True)
    d["ts"] = pd.to_datetime(d.minute * 60, unit="s")
    return d


def slope(d, y):
    x = d.dropna(subset=[y])
    r = E.ols(x[y], [x.F], x.minute, ["F"])
    return {"n": r["n"], **r["F"]}


def interaction(d, y):
    x = d.dropna(subset=[y])
    S = x.settle.astype(float)
    r = E.ols(x[y], [x.F, S, x.F * S], x.minute, ["F", "settle", "F_x_settle"])
    return {"placebo_slope": r["F"]["coef"], "diff": r["F_x_settle"]["coef"],
            "diff_se": r["F_x_settle"]["se"], "diff_p": r["F_x_settle"]["p"]}


def tests(d):
    """E1–E5 exactly as filed. Returns estimates and directional p-values."""
    s = d[d.settle]
    out = {"n_settle": int(len(s)), "n_placebo": int((~d.settle).sum()),
           "n_contracts": int(d.sym.nunique())}
    # E1: beta_W > 0 and beta_W > beta_inst (slope of W - J_inst on F)
    e1a = slope(s, "W")
    s2 = s.dropna(subset=["W", "J_inst"]).assign(gap=lambda x: x.W - x.J_inst)
    e1b = slope(s2, "gap")
    out["E1"] = {"beta_W": e1a, "beta_inst": slope(s2, "J_inst"), "W_minus_inst": e1b,
                 "p": max(E.directional_p({"F": e1a}, "F", +1), E.directional_p({"F": e1b}, "F", +1))}
    e2 = slope(s, "PRE")
    out["E2"] = {"beta_PRE": e2, "p": E.directional_p({"F": e2}, "F", -1)}
    e3 = slope(s, "POST")
    out["E3"] = {"beta_POST": e3, "p": E.directional_p({"F": e3}, "F", +1)}
    e4 = {w: interaction(d, w) for w in ("W", "PRE", "POST")}
    signs = {"W": +1, "PRE": -1, "POST": +1}
    e4p = max(e4[w]["diff_p"] if np.sign(e4[w]["diff"]) == signs[w] else 1.0 for w in e4)
    out["E4"] = {**e4, "p": e4p}
    e5 = {w: slope(s, w) for w in ("sPRE", "sW", "sPOST")}
    e5p = max(E.directional_p({"F": e5["sPRE"]}, "F", -1), E.directional_p({"F": e5["sW"]}, "F", +1),
              E.directional_p({"F": e5["sPOST"]}, "F", +1))
    out["E5"] = {**e5, "p": e5p}
    out["perp"] = {w: slope(s, w) for w in ("pPRE", "pW", "pPOST")}
    ps = [out[k]["p"] for k in ("E1", "E2", "E3", "E4", "E5")]
    out["holm"] = dict(zip(("E1", "E2", "E3", "E4", "E5"), E.holm(ps)))
    return out


def capture(d):
    s = d[d.settle].dropna(subset=["W"])
    a = s.F.abs()
    rows = []
    for lo, hi in E.ABS_BINS:
        m = (a > lo) & (a <= hi) if lo > 0 else (a <= hi)
        x = s[m]
        g = x.F.abs() - np.sign(x.F) * x.W
        # a hedge you can actually trade: the perp against Binance spot, same window
        y = x.dropna(subset=["pW", "sW"])
        gt = y.F.abs() - np.sign(y.F) * (y.pW - y.sW)
        rows.append({"bin": f"{lo}-{hi}", "n": int(m.sum()), "mean_abs_F": float(x.F.abs().mean()),
                     "gross_bp": float(g.mean()), "share_kept": float(g.mean() / x.F.abs().mean()),
                     "net_4bp": float(g.mean() - 4), "net_10bp": float(g.mean() - 10),
                     "priced_share": float(1 - g.mean() / x.F.abs().mean()),
                     "n_tradeable": int(len(y)),
                     "gross_tradeable_bp": float(gt.mean()), "se_tradeable_bp": float(gt.sem()),
                     "share_kept_tradeable": float(gt.mean() / y.F.abs().mean()),
                     "net_8bp_tradeable": float(gt.mean() - 8)})
    return rows


def report(label, t):
    print(f"\n=== {label}: {t['n_contracts']} contracts, {t['n_settle']:,} settlements, "
          f"{t['n_placebo']:,} placebo marks ===")
    e = t["E1"]
    print(f"  E1  beta_W {e['beta_W']['coef']:+.3f} (t {e['beta_W']['t']:.1f})  vs instantaneous "
          f"{e['beta_inst']['coef']:+.3f};  W - inst {e['W_minus_inst']['coef']:+.3f} "
          f"(t {e['W_minus_inst']['t']:.1f})")
    print(f"  E2  beta_PRE  {t['E2']['beta_PRE']['coef']:+.3f} (t {t['E2']['beta_PRE']['t']:.1f})")
    print(f"  E3  beta_POST {t['E3']['beta_POST']['coef']:+.3f} (t {t['E3']['beta_POST']['t']:.1f})")
    print("  E4  settle - placebo:  " + "  ".join(
        f"{w} {t['E4'][w]['diff']:+.3f} (placebo {t['E4'][w]['placebo_slope']:+.3f})" for w in ("W", "PRE", "POST")))
    print("  E5  spot slopes:  " + "  ".join(
        f"{w} {t['E5'][w]['coef']:+.4f} (t {t['E5'][w]['t']:.1f})" for w in ("sPRE", "sW", "sPOST")))
    print("      perp slopes:  " + "  ".join(
        f"{w} {t['perp'][w]['coef']:+.4f} (t {t['perp'][w]['t']:.1f})" for w in ("pPRE", "pW", "pPOST")))
    print("  Holm-adjusted p:  " + ", ".join(f"{k} {v:.2g}" for k, v in t["holm"].items()))


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #
C_WINDOW, C_INSTANT, C_NONE = E.C_SETTLE, "#d95926", E.C_PLACEBO     # validated on #0d1117
C_DISC, C_HOLD = E.C_SETTLE, "#d95926"
EDGES = [-60, -30, -15, -7.5, -3, -1, 0, 0.99, 1.01, 3, 7.5, 15, 30, 60]


def fig_jump_vs_funding(d, path):
    """Mean basis change against F in fixed-width bins, for the instant and for the
    settlement window, with non-settlement marks as the control. Intervals are
    event-level 95% (not clustered) and are for display only."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    fig.patch.set_facecolor(E.SURFACE)
    E._ax(ax)
    ax.set_axisbelow(True)
    xs = np.array([-45, 45])
    ax.plot(xs, xs, color=E.INK2, linewidth=1.1, linestyle="--", zorder=1)
    ax.text(25.5, 28.2, "frictionless: basis jumps by F", color=E.INK2, fontsize=8, ha="right", va="center")
    ax.axhline(0, color=E.INK2, linewidth=0.8, zorder=1)
    s, p = d[d.settle], d[~d.settle]
    series = ((p, "W", C_NONE, "s", "non-settlement marks, same 3-minute window"),
              (s, "J_inst", C_INSTANT, "D", "settlement, at the stamp (5 s)"),
              (s, "W", C_WINDOW, "o", "settlement, across the 3-minute window"))
    for x, col, colour, mk, name in series:
        x = x.dropna(subset=[col])
        b = pd.cut(x.F, EDGES)
        g = x.groupby(b, observed=True).agg(F=("F", "mean"), y=(col, "mean"), se=(col, "sem"), n=(col, "size"))
        g = g[g.n >= 200]
        ax.errorbar(g.F, g.y, yerr=1.96 * g.se, fmt=mk + "-", ms=6.5, lw=1.6, color=colour, ecolor=colour,
                    elinewidth=1, capsize=0, label=name, mec=E.SURFACE, mew=1.2, zorder=3)
    ax.set_xlim(-45, 45)
    ax.set_ylim(-30, 30)
    ax.set_xlabel("funding rate paid at settlement, F (bp)", color=E.INK2)
    ax.set_ylabel("change in the basis (bp)", color=E.INK2)
    ax.set_title("How much of the funding payment the basis prices, and when (96 contracts)",
                 color=E.INK, fontsize=11)
    E._legend(ax, loc="upper left")
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=E.SURFACE)
    plt.close(fig)
    print(f"saved -> {path}")


def fig_coefficients(res, path):
    """Discovery estimates beside holdout tests, for every window and price."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    rows = [("basis · at the stamp (5 s)", lambda t: t["E1"]["beta_inst"]),
            ("basis · settlement window (≈3 min)", lambda t: t["E1"]["beta_W"]),
            ("basis · hour before", lambda t: t["E2"]["beta_PRE"]),
            ("basis · hour after", lambda t: t["E3"]["beta_POST"]),
            ("perpetual price · hour before", lambda t: t["perp"]["pPRE"]),
            ("perpetual price · settlement window", lambda t: t["perp"]["pW"]),
            ("spot price · hour before", lambda t: t["E5"]["sPRE"]),
            ("spot price · settlement window", lambda t: t["E5"]["sW"])]
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    fig.patch.set_facecolor(E.SURFACE)
    E._ax(ax)
    ax.set_axisbelow(True)
    y = np.arange(len(rows))[::-1]
    for off, key, colour, name in ((0.16, "discovery", C_DISC, "discovery: 62 contracts (estimates)"),
                                   (-0.16, "holdout", C_HOLD, "holdout: 34 unseen contracts (tests)")):
        c = np.array([f(res[key])["coef"] for _, f in rows])
        se = np.array([f(res[key])["se"] for _, f in rows])
        ax.errorbar(c, y + off, xerr=1.96 * se, fmt="o", ms=7, color=colour, ecolor=colour,
                    elinewidth=1.4, capsize=0, label=name, mec=E.SURFACE, mew=1.2, zorder=3)
    ax.axvline(0, color=E.INK2, linewidth=0.8, zorder=1)
    ax.axvline(1, color=E.INK2, linewidth=1, linestyle="--", zorder=1)
    ax.axvline(-1, color=E.INK2, linewidth=1, linestyle=":", zorder=1)
    ax.text(1.03, y[0] + 0.45, "+F", color=E.INK2, fontsize=8, ha="left")
    ax.text(-0.97, y[0] + 0.45, "−F", color=E.INK2, fontsize=8, ha="left")
    ax.set_yticks(y)
    ax.set_yticklabels([r[0] for r in rows], color=E.INK2, fontsize=8)
    ax.set_ylim(y[-1] - 0.6, y[0] + 0.75)
    ax.grid(axis="y", linewidth=0)
    ax.set_xlabel("slope on the funding rate (1 = moves by the full funding payment)", color=E.INK2)
    ax.set_title("Where the funding payment gets priced", color=E.INK, fontsize=11, pad=30)
    E._legend(ax, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False)
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=E.SURFACE)
    plt.close(fig)
    print(f"saved -> {path}")


def main():
    disc = [s.strip() for s in open(os.path.join(HERE, "universe.txt")) if s.strip()]
    hold = [s.strip() for s in open(os.path.join(HERE, "holdout_universe.txt")) if s.strip()]
    only_disc = "--discovery-only" in sys.argv
    res = {"addendum_commit": "e51757a"}

    dd = window_events(disc)
    res["discovery"] = tests(dd)
    res["discovery_capture"] = capture(dd)
    report("DISCOVERY (estimates, not tests)", res["discovery"])
    if only_disc:
        return

    missing = [s for s in hold if not os.path.exists(os.path.join(E.DATA, "contracts", f"{s}.npz"))]
    if missing:
        sys.exit(f"holdout extracts missing for {missing} — run pipeline.py on holdout_universe.txt")
    hd = window_events(hold)
    res["holdout"] = tests(hd)
    res["holdout_capture"] = capture(hd)
    report("HOLDOUT (the tests)", res["holdout"])
    for lab in ("discovery", "holdout"):
        print(f"\n  capture across W ({lab}): " + "  ".join(
            f"|F| {r['bin']}: keep {r['share_kept']:.2f} of |F| ({r['gross_bp']:+.1f}bp, net@4 {r['net_4bp']:+.1f})"
            for r in res[f"{lab}_capture"]))
        print(f"  tradeable hedge ({lab}): " + "  ".join(
            f"|F| {r['bin']}: keep {r['share_kept_tradeable']:.2f} ({r['gross_tradeable_bp']:+.1f}"
            f"±{r['se_tradeable_bp']:.1f}bp, net of 8bp {r['net_8bp_tradeable']:+.1f})"
            for r in res[f"{lab}_capture"]))

    # holdout path figure — same construction as the original descriptive figure
    all_paths, fds = {}, {}
    for s in hold:
        _, p = E.load_hours(s)
        all_paths[s], fds[s] = p, E.load_funding(s)
    pr = E.event_paths(all_paths, fds)
    res["holdout_paths_n"] = {f"{k[0]} | {k[1]}": v["n"] for k, v in pr.items()}
    E.fig_paths(pr, os.path.join(E.FIG, "paths_holdout.png"),
                title="Holdout: 34 contracts never examined before the addendum")
    res["robustness_discovery"] = robustness_windows(dd, disc)
    res["robustness_holdout"] = robustness_windows(hd, hold)
    print_robustness("discovery (62 contracts)", res["robustness_discovery"])
    print_robustness("holdout (34 contracts)", res["robustness_holdout"])
    fig_jump_vs_funding(pd.concat([dd, hd]), os.path.join(E.FIG, "jump_vs_funding.png"))
    fig_coefficients(res, os.path.join(E.FIG, "coefficients.png"))
    with open(os.path.join(HERE, "results_addendum.json"), "w") as f:
        json.dump(res, f, indent=2, default=float)
    print("\nwrote results_addendum.json")



# --------------------------------------------------------------------------- #
# EXPLORATORY robustness (not in the addendum's test list; reported as such)
# --------------------------------------------------------------------------- #
def lagged_funding(d, syms):
    """Attach the PREVIOUS settlement's funding rate — known ~8 hours before the
    event, so conditioning on it involves no look-ahead."""
    out = []
    for sym in syms:
        fd = E.load_funding(sym)
        x = d[d.sym == sym].copy()
        sm = fd.minute.to_numpy()
        i = np.searchsorted(sm, x.minute.to_numpy(), side="left") - 1   # strictly earlier settlement
        x["F_lag"] = np.where(i >= 0, fd.F.to_numpy()[np.clip(i, 0, None)], np.nan)
        out.append(x)
    return pd.concat(out)


def robustness_windows(d, syms):
    s = d[d.settle].dropna(subset=["W", "PRE"])
    out = {}
    # 1. extreme events
    lo, hi = np.percentile(s.F, [1, 99])
    for lab, x in [("all", s), ("F winsorised 1/99", s.assign(F=s.F.clip(lo, hi))),
                   ("|F| <= 50bp", s[s.F.abs() <= 50])]:
        out[lab] = {w: slope(x, w)["coef"] for w in ("PRE", "W", "POST")}
    wz = s.assign(W=s.W.clip(*np.percentile(s.W, [1, 99])), PRE=s.PRE.clip(*np.percentile(s.PRE, [1, 99])))
    out["outcomes winsorised 1/99"] = {w: slope(wz, w)["coef"] for w in ("PRE", "W")}
    # 2. by year
    out["by_year"] = {}
    for y, x in s.groupby(s.ts.dt.year):
        out["by_year"][int(y)] = {w: slope(x, w)["coef"] for w in ("PRE", "W")} | {"n": int(len(x))}
    # 3. by contract
    per = []
    for sym, x in s.groupby("sym"):
        if len(x) > 300 and x.F.std() > 0:
            per.append({"sym": sym, "W": slope(x, "W")["coef"], "PRE": slope(x, "PRE")["coef"]})
    per = pd.DataFrame(per)
    out["contracts"] = {"n": int(len(per)), "share_W_pos": float((per.W > 0).mean()),
                        "share_PRE_neg": float((per.PRE < 0).mean())}
    # 4. no look-ahead: condition on the previous settlement's rate
    z = lagged_funding(s, syms).dropna(subset=["F_lag"])
    out["lagged_F"] = {w: slope(z.assign(F=z.F_lag), w) for w in ("PRE", "W", "pPRE", "pW")}
    out["lag_persistence"] = float(np.corrcoef(z.F, z.F_lag)[0, 1])
    # the implied trade: when the previous rate was >= 10bp in absolute value,
    # take the side the pattern predicts over PRE (against the payer), then over W
    big = z[z.F_lag.abs() >= 10]
    sgn = np.sign(big.F_lag)
    out["trade_lag10"] = {
        "n": int(len(big)),
        "pre_perp_bp": float((-sgn * big.pPRE).mean()), "pre_perp_se": float((-sgn * big.pPRE).sem()),
        "w_perp_bp": float((sgn * big.pW).mean()), "w_perp_se": float((sgn * big.pW).sem()),
        "mean_abs_F_lag": float(big.F_lag.abs().mean()),
    }
    return out


def print_robustness(label, r):
    print(f"\n--- EXPLORATORY robustness: {label} ---")
    for k in ("all", "F winsorised 1/99", "|F| <= 50bp", "outcomes winsorised 1/99"):
        print(f"  {k:26s} " + "  ".join(f"{w} {v:+.3f}" for w, v in r[k].items()))
    print("  by year:   " + "  ".join(f"{y}: PRE {v['PRE']:+.2f} W {v['W']:+.2f}" for y, v in r["by_year"].items()))
    c = r["contracts"]
    print(f"  contracts: {c['n']}  beta_W > 0 in {c['share_W_pos']*100:.0f}%   beta_PRE < 0 in {c['share_PRE_neg']*100:.0f}%")
    print(f"  lagged F (known 8h ahead; corr with F {r['lag_persistence']:.2f}): " + "  ".join(
        f"{w} {v['coef']:+.3f} (t {v['t']:.1f})" for w, v in r["lagged_F"].items()))
    t = r["trade_lag10"]
    print(f"  trade when |F_lag| >= 10bp (n {t['n']:,}, mean |F_lag| {t['mean_abs_F_lag']:.1f}bp): "
          f"PRE leg {t['pre_perp_bp']:+.1f}bp (se {t['pre_perp_se']:.1f}),  W leg {t['w_perp_bp']:+.1f}bp (se {t['w_perp_se']:.1f})  gross, per event")


if __name__ == "__main__":
    main()
