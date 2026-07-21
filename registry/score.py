#!/usr/bin/env python3
"""Out-of-Sample Registry — scoring engine.

Every strategy in ``strategies/`` declares a lock date. This harness evaluates
each one *only* on market data dated after that lock date, so the score reflects
genuinely out-of-sample performance: the strategy is handed price history one
day at a time and is never given a future price, which makes lookahead
structurally impossible rather than merely discouraged.

Running it regenerates ``scoreboard.json`` and the scoreboard table inside
``README.md``. It fetches real SPY daily closes when the network allows and
falls back to a bundled synthetic sample otherwise; either way the data source
is recorded on the board so a reader always knows what produced the numbers.

    python score.py
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import math
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STRATEGY_DIR = os.path.join(HERE, "strategies")
SAMPLE = os.path.join(HERE, "_sample_spy.csv")
SCOREBOARD_JSON = os.path.join(HERE, "scoreboard.json")
README = os.path.join(HERE, "README.md")

TICKER = "SPY"
COST_PER_TURNOVER = 0.0001       # 1 bp charged on |change in position|
TRADING_DAYS = 252
STOOQ = "https://stooq.com/q/d/l/?s={sym}&i=d"


# --------------------------------------------------------------------------- #
# Market data
# --------------------------------------------------------------------------- #
def _parse_csv(text: str) -> tuple[list[str], list[float]]:
    dates, closes = [], []
    for line in text.strip().splitlines()[1:]:
        parts = line.split(",")
        if len(parts) < 2:
            continue
        try:
            close = float(parts[-1] if len(parts) == 2 else parts[4])
        except ValueError:
            continue
        dates.append(parts[0])
        closes.append(close)
    return dates, closes


def load_market_data() -> tuple[str, list[str], list[float]]:
    """Return (source_label, dates, closes). Real SPY if reachable, else sample."""
    try:
        url = STOOQ.format(sym=TICKER.lower() + ".us")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            dates, closes = _parse_csv(resp.read().decode("utf-8", "replace"))
        if len(closes) < 500:
            raise RuntimeError(f"stooq returned only {len(closes)} rows")
        return f"real {TICKER} daily (stooq)", dates, closes
    except Exception as exc:  # offline, rate-limited, or source down
        print(f"[data] live fetch failed ({exc}); using bundled sample")
        with open(SAMPLE) as f:
            dates, closes = _parse_csv(f.read())
        return "synthetic sample (offline)", dates, closes


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def _mean(xs): return sum(xs) / len(xs)


def _std(xs):
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def annualized_sharpe(daily: list[float]) -> float:
    if len(daily) < 2:
        return 0.0
    sd = _std(daily)
    return 0.0 if sd == 0 else _mean(daily) / sd * math.sqrt(TRADING_DAYS)


def max_drawdown(daily: list[float]) -> float:
    equity, peak, worst = 1.0, 1.0, 0.0
    for r in daily:
        equity *= (1 + r)
        peak = max(peak, equity)
        worst = min(worst, equity / peak - 1)
    return worst


def total_return(daily: list[float]) -> float:
    equity = 1.0
    for r in daily:
        equity *= (1 + r)
    return equity - 1


# --------------------------------------------------------------------------- #
# Strategy loading + evaluation
# --------------------------------------------------------------------------- #
REQUIRED = ("NAME", "AUTHOR", "LOCKED_AS_OF", "position")


def load_strategies() -> list:
    mods = []
    for fname in sorted(os.listdir(STRATEGY_DIR)):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue
        path = os.path.join(STRATEGY_DIR, fname)
        spec = importlib.util.spec_from_file_location(fname[:-3], path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        missing = [a for a in REQUIRED if not hasattr(mod, a)]
        if missing:
            print(f"[skip] {fname}: missing {missing}")
            continue
        mod._file = fname
        mods.append(mod)
    return mods


def evaluate(mod, dates: list[str], closes: list[float]) -> dict | None:
    """Walk the strategy forward over every day *after* its lock date, handing it
    only past prices, and score the resulting daily returns out-of-sample."""
    lock = mod.LOCKED_AS_OF
    start = next((i for i, d in enumerate(dates) if d > lock), None)
    if start is None or start >= len(closes) - 1:
        return None

    strat_daily, bench_daily, prev_pos = [], [], 0.0
    for t in range(start, len(closes) - 1):
        pos = float(mod.position(closes[: t + 1]))
        pos = max(-1.0, min(1.0, pos))
        ret = closes[t + 1] / closes[t] - 1
        cost = COST_PER_TURNOVER * abs(pos - prev_pos)
        strat_daily.append(pos * ret - cost)
        bench_daily.append(ret)
        prev_pos = pos

    return {
        "name": mod.NAME,
        "author": mod.AUTHOR,
        "kind": getattr(mod, "KIND", "submission"),
        "locked_as_of": lock,
        "hypothesis": getattr(mod, "HYPOTHESIS", ""),
        "file": mod._file,
        "oos_start": dates[start],
        "oos_days": len(strat_daily),
        "oos_return": total_return(strat_daily),
        "sharpe": annualized_sharpe(strat_daily),
        "max_drawdown": max_drawdown(strat_daily),
        "benchmark_return": total_return(bench_daily),
        "benchmark_sharpe": annualized_sharpe(bench_daily),
    }


def status_of(row: dict) -> str:
    if row["file"].startswith("buy_and_hold"):
        return "benchmark"
    if row["sharpe"] <= 0:
        return "faded"
    return "beat benchmark" if row["sharpe"] > row["benchmark_sharpe"] else "trailed benchmark"


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def render_table(rows: list[dict], source: str, asof: str) -> str:
    ranked = sorted(rows, key=lambda r: r["sharpe"], reverse=True)
    label = {"beat benchmark": "**beat benchmark**", "trailed benchmark": "trailed benchmark",
             "faded": "faded", "benchmark": "_benchmark_"}
    lines = [
        f"_Last run **{asof}** · data source: **{source}** · "
        f"cost: 1&nbsp;bp per turnover · benchmark: buy &amp; hold SPY._",
        "",
        "| # | Strategy | Author | Locked | OOS window | OOS return | Sharpe | Max DD | vs B&H | Status |",
        "|--:|---|---|:--:|:--:|--:|--:|--:|--:|:--|",
    ]
    for i, r in enumerate(ranked, 1):
        d_sharpe = r["sharpe"] - r["benchmark_sharpe"]
        vs = "—" if r["file"].startswith("buy_and_hold") else f"{d_sharpe:+.2f}"
        lines.append(
            f"| {i} | {r['name']} | {r['author']} | `{r['locked_as_of']}` | "
            f"{r['oos_days']}d from {r['oos_start']} | {r['oos_return']*100:+.1f}% | "
            f"{r['sharpe']:.2f} | {r['max_drawdown']*100:.1f}% | {vs} | {label[status_of(r)]} |"
        )
    return "\n".join(lines)


def inject(readme_table: str) -> None:
    block = f"<!--SCOREBOARD:START-->\n{readme_table}\n<!--SCOREBOARD:END-->"
    with open(README) as f:
        text = f.read()
    pattern = re.compile(r"<!--SCOREBOARD:START-->.*?<!--SCOREBOARD:END-->", re.DOTALL)
    if not pattern.search(text):
        print("[warn] no SCOREBOARD markers in README; skipping injection")
        return
    with open(README, "w") as f:
        f.write(pattern.sub(block, text))


def main() -> None:
    source, dates, closes = load_market_data()
    asof = dates[-1] if dates else "unknown"
    rows = [r for r in (evaluate(m, dates, closes) for m in load_strategies()) if r]
    if not rows:
        print("[error] no strategies scored")
        return
    for r in rows:
        r["status"] = status_of(r)

    with open(SCOREBOARD_JSON, "w") as f:
        json.dump({"as_of": asof, "data_source": source,
                   "cost_bps_per_turnover": 1.0, "entries": rows}, f, indent=2)
    inject(render_table(rows, source, asof))

    print(f"[done] scored {len(rows)} strategies on {source} (as of {asof})")
    for r in sorted(rows, key=lambda r: r["sharpe"], reverse=True):
        print(f"  {r['sharpe']:+.2f}  {r['name']}  ({r['oos_days']}d OOS)  [{r['status']}]")


if __name__ == "__main__":
    main()
