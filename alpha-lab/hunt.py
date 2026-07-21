#!/usr/bin/env python3
"""Run every candidate strategy through the honest harness and print a leaderboard.

    python hunt.py

Fetches real SPY daily closes (Yahoo, then stooq) and falls back to a labelled
synthetic series offline. For each candidate it reports full-sample and
out-of-sample risk metrics, and flags whether it actually beats buy & hold on the
untouched out-of-sample tail — the only result that counts.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import urllib.request

import harness
from strategies import CANDIDATES

HERE = os.path.dirname(os.path.abspath(__file__))
YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/SPY?range=15y&interval=1d"
STOOQ = "https://stooq.com/q/d/l/?s=spy.us&i=d"
UA = {"User-Agent": "Mozilla/5.0 (compatible; NeilQuantLabs/1.0)"}


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
def _yahoo():
    with urllib.request.urlopen(urllib.request.Request(YAHOO, headers=UA), timeout=30) as r:
        d = json.loads(r.read().decode())
    res = d["chart"]["result"][0]
    adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose")
    closes = adj or res["indicators"]["quote"][0]["close"]
    return [float(c) for c in closes if c is not None]


def _stooq():
    with urllib.request.urlopen(urllib.request.Request(STOOQ, headers=UA), timeout=30) as r:
        lines = r.read().decode().strip().splitlines()[1:]
    return [float(x.split(",")[4]) for x in lines if len(x.split(",")) >= 5]


def _synthetic(n=3000, seed=7):
    """Deterministic SPY-like series with volatility clustering and occasional
    crashes — enough structure for the risk-based strategies to matter offline."""
    import random
    rng = random.Random(seed)
    price, sigma, closes = 200.0, 0.01, []
    for i in range(n):
        if rng.random() < 0.004:                 # rare shock -> a crash + high vol
            sigma = 0.05
        shock = rng.gauss(0.0004, sigma)
        price *= math.exp(shock)
        sigma = math.sqrt(0.0000012 + 0.93 * sigma ** 2 + 0.06 * shock ** 2)
        closes.append(price)
    return closes


def load_closes():
    for label, fn in (("real SPY (Yahoo)", _yahoo), ("real SPY (stooq)", _stooq)):
        try:
            c = fn()
            if len(c) >= 500:
                return label, c
        except Exception as exc:
            print(f"[data] {label} failed ({exc})")
    print("[data] offline — using labelled synthetic series")
    return "synthetic (offline)", _synthetic()


# --------------------------------------------------------------------------- #
# Report
# --------------------------------------------------------------------------- #
def main():
    source, closes = load_closes()
    print(f"data: {source} · {len(closes)} daily closes\n")

    rows = {}
    for name, fn in CANDIDATES.items():
        rows[name] = harness.evaluate(fn, closes)
    bh = rows["Buy & Hold"]

    def line(name, r):
        f, o = r["full"], r["oos"]
        beat = "" if name == "Buy & Hold" else (
            " WINS" if o["sharpe"] > bh["oos"]["sharpe"] + 0.02 else "")
        return (f"{name:22s} | full  Sh {f['sharpe']:5.2f}  ret {f['ann_return']*100:6.1f}%  "
                f"vol {f['ann_vol']*100:5.1f}%  DD {f['max_drawdown']*100:6.1f}%  Cal {f['calmar']:4.2f} "
                f"| OOS  Sh {o['sharpe']:5.2f}  DD {o['max_drawdown']*100:6.1f}%  "
                f"Cal {o['calmar']:4.2f}  exp {r['avg_exposure']:.2f}{beat}")

    order = sorted(rows, key=lambda n: rows[n]["oos"]["sharpe"], reverse=True)
    print("ranked by out-of-sample Sharpe (the last 40% of history, never tuned on):\n")
    for name in order:
        print("  " + line(name, rows[name]))

    survivors = [n for n in rows if n != "Buy & Hold"
                 and rows[n]["oos"]["sharpe"] > bh["oos"]["sharpe"] + 0.02]
    print("\n" + ("survives out-of-sample (beats buy & hold risk-adjusted): "
                  + ", ".join(survivors) if survivors
                  else "nothing clears buy & hold out-of-sample — an honest null."))

    out = {"data_source": source, "n_days": len(closes),
           "oos_fraction": harness.OOS_FRACTION,
           "results": {n: {"full": rows[n]["full"], "oos": rows[n]["oos"],
                           "turnover": rows[n]["turnover"],
                           "avg_exposure": rows[n]["avg_exposure"]} for n in rows},
           "survivors": survivors}
    with open(os.path.join(HERE, "results.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("\nwrote results.json")


if __name__ == "__main__":
    main()
