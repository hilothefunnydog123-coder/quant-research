#!/usr/bin/env python3
# © 2026 Neil Gilani (Martingale) — MIT License.
# Research Note 007 — data pipeline.
#
# Streams 1-minute bars from Binance's public archive (data.binance.vision, served
# from S3), extracts what the analysis needs around every hour mark, and discards
# the raw files. Run:  python pipeline.py [--workers 16] [--symbols BTCUSDT,ETHUSDT]
"""For each contract-month this downloads three 1-minute series — the premium index
(perpetual vs. index basis, sampled every 5 s), perpetual trades, and spot trades —
and writes one row per hour mark with the values just before and just after the
mark, a few window endpoints, and order flow. For hour marks divisible by four it
also keeps the full ±60-minute path, for the event-time figures.

Nothing here knows which hour marks are funding settlements or what the funding
rate was. That join happens in experiment.py, so the extraction cannot be tuned to
the result."""
from __future__ import annotations

import argparse
import io
import os
import sys
import time
import urllib.request
import zipfile
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "contracts")
ARCHIVE = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision/data"
START, END = (2020, 1), (2026, 8)
PATH_HALF = 60                      # minutes each side kept for event-time paths
WIN = 15                            # minutes for the pre/post windows


def months():
    y, m = START
    while (y, m) <= END:
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def fetch(url, tries=4):
    """Return the CSV text inside a monthly zip, or None if the file does not exist."""
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                blob = r.read()
            with zipfile.ZipFile(io.BytesIO(blob)) as z:
                return z.read(z.namelist()[0]).decode()
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                return None
        except Exception:
            pass
        time.sleep(2 ** k)
    raise RuntimeError(f"failed after {tries} tries: {url}")


def parse(text, month_start_min, n_min):
    """Kline CSV -> dict of arrays indexed by minute-of-month (NaN where missing).

    Spot files switched from millisecond to microsecond timestamps in 2025; both
    are normalised to minutes here."""
    cols = {k: np.full(n_min, np.nan) for k in
            ("open", "close", "volume", "taker_buy", "count")}
    if text is None:
        return cols
    lines = text.strip().splitlines()
    if lines and not lines[0][:1].isdigit():
        lines = lines[1:]
    if not lines:
        return cols
    a = np.array([ln.split(",")[:9] + ln.split(",")[9:10] for ln in lines], dtype=object)
    t = a[:, 0].astype(np.int64)
    t = np.where(t > 10**14, t // 1000, t)          # microseconds -> milliseconds
    idx = (t // 60000) - month_start_min
    ok = (idx >= 0) & (idx < n_min)
    idx = idx[ok]
    cols["open"][idx] = a[ok, 1].astype(float)
    cols["close"][idx] = a[ok, 4].astype(float)
    cols["volume"][idx] = a[ok, 5].astype(float)
    cols["count"][idx] = a[ok, 8].astype(float)
    cols["taker_buy"][idx] = a[ok, 9].astype(float)
    return cols


def month_bounds(y, m):
    import calendar
    import datetime as dt
    start = dt.datetime(y, m, 1, tzinfo=dt.timezone.utc)
    n_min = calendar.monthrange(y, m)[1] * 1440
    return int(start.timestamp()) // 60, n_min


def fetch_month(sym, y, m):
    """Download the three series for one month concurrently."""
    from concurrent.futures import ThreadPoolExecutor
    m0, n = month_bounds(y, m)
    tag = f"{y}-{m:02d}"
    urls = [f"{ARCHIVE}/futures/um/monthly/premiumIndexKlines/{sym}/1m/{sym}-1m-{tag}.zip",
            f"{ARCHIVE}/futures/um/monthly/klines/{sym}/1m/{sym}-1m-{tag}.zip",
            f"{ARCHIVE}/spot/monthly/klines/{sym}/1m/{sym}-1m-{tag}.zip"]
    with ThreadPoolExecutor(3) as ex:
        texts = list(ex.map(fetch, urls))
    return m0, [parse(t, m0, n) for t in texts]


def concat(a, b):
    return {k: np.concatenate([a[k], b[k]]) for k in a}


def extract(block, base, marks):
    """Hour-mark table and paths for the absolute minutes `marks`, from a contiguous
    block of bars starting at absolute minute `base`. Pure function of the bars; no
    funding information is used."""
    pi, pf, sp = block
    hours = marks - base

    def at(series, offs):
        return series[hours + offs]

    def window_sum(series, lo, hi):                 # sum over minutes [h+lo, h+hi)
        c = np.concatenate([[0.0], np.cumsum(np.nan_to_num(series))])
        return c[hours + hi] - c[hours + lo]

    table = {
        "minute": marks.astype(np.int64),            # minutes since epoch, UTC
        # premium index: last 5-s sample before the mark, first at/after it
        "pi_pre": at(pi["close"], -1), "pi_post": at(pi["open"], 0),
        "pi_m15": at(pi["close"], -WIN - 1), "pi_p15": at(pi["close"], WIN - 1),
        "pi_m60": at(pi["close"], -PATH_HALF - 1), "pi_p60": at(pi["close"], PATH_HALF - 1),
        "pi_count_pre": at(pi["count"], -1), "pi_count_post": at(pi["count"], 0),
        # perpetual trades
        "pf_pre": at(pf["close"], -1), "pf_post": at(pf["open"], 0),
        "pf_m15": at(pf["close"], -WIN - 1), "pf_p15": at(pf["close"], WIN - 1),
        "pf_n_pre": at(pf["count"], -1), "pf_n_post": at(pf["count"], 0),
        "vol_pre": window_sum(pf["volume"], -WIN, 0), "vol_post": window_sum(pf["volume"], 0, WIN),
        "buy_pre": window_sum(pf["taker_buy"], -WIN, 0), "buy_post": window_sum(pf["taker_buy"], 0, WIN),
        "vol_base": window_sum(pf["volume"], -PATH_HALF, -WIN),
        # spot trades
        "sp_pre": at(sp["close"], -1), "sp_post": at(sp["open"], 0),
        "sp_m15": at(sp["close"], -WIN - 1), "sp_p15": at(sp["close"], WIN - 1),
    }

    # full paths for hour marks divisible by 4 (00,04,...,20 UTC)
    sel = hours[(marks // 60) % 4 == 0]
    offs = np.arange(-PATH_HALF - 1, PATH_HALF)      # close of bar h-61 ... close of bar h+59
    grid = sel[:, None] + offs[None, :]
    paths = {
        "minute": (base + sel).astype(np.int64),
        "pi": pi["close"][grid].astype(np.float32),
        "pf": pf["close"][grid].astype(np.float32),
        "sp": sp["close"][grid].astype(np.float32),
    }
    return table, paths


def job(sym):
    """Walk one contract's months in order. The last few hours of each month are
    carried into the next, so settlements at 00:00 on the 1st keep their
    pre-settlement minute and no hour mark is lost at a month boundary."""
    out = os.path.join(OUT, f"{sym}.npz")
    if os.path.exists(out):
        return sym, "cached", 0
    tables, paths, carry, carry_base, done_upto = [], [], None, None, -1
    keep = 3 * PATH_HALF
    for y, m in months():
        m0, cur = fetch_month(sym, y, m)
        if all(np.all(np.isnan(c["close"])) for c in cur[:1]):   # no perpetual yet
            carry = None
            continue
        if carry is not None and carry_base + len(carry[0]["close"]) == m0:
            block = tuple(concat(a, b) for a, b in zip(carry, cur))
            base = carry_base
        else:
            block, base = cur, m0
        n = len(block[0]["close"])
        first = base + PATH_HALF + 1
        last = base + n - PATH_HALF - 1
        marks = np.arange(((first + 59) // 60) * 60, last + 1, 60)
        marks = marks[marks > done_upto]
        if len(marks):
            t, p = extract(block, base, marks)
            tables.append(t)
            paths.append(p)
            done_upto = int(marks[-1])
        carry = tuple({k: v[-keep:] for k, v in b.items()} for b in block)
        carry_base = base + n - keep
    if not tables:
        return sym, "no-data", 0
    os.makedirs(OUT, exist_ok=True)
    merged = {f"t_{k}": np.concatenate([t[k] for t in tables]) for k in tables[0]}
    merged.update({f"p_{k}": np.concatenate([p[k] for p in paths]) for k in paths[0]})
    np.savez_compressed(out + ".tmp.npz", **merged)
    os.replace(out + ".tmp.npz", out)
    return sym, "ok", len(merged["t_minute"])


def fetch_funding(sym):
    """Monthly funding-rate files for one contract, kept as downloaded."""
    os.makedirs(os.path.join(HERE, "data", "funding"), exist_ok=True)
    got = 0
    for y, m in months():
        name = f"{sym}-fundingRate-{y}-{m:02d}.zip"
        dest = os.path.join(HERE, "data", "funding", name)
        if os.path.exists(dest):
            got += 1
            continue
        url = f"{ARCHIVE}/futures/um/monthly/fundingRate/{sym}/{name}"
        blob, absent = None, False
        for k in range(5):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    blob = r.read()
                break
            except urllib.error.HTTPError as e:
                if e.code in (403, 404):
                    absent = True
                    break
            except Exception:
                pass
            time.sleep(2 ** k)
        if absent:
            continue
        if blob is None:
            raise RuntimeError(f"failed after 5 tries: {url}")
        with open(dest, "wb") as f:
            f.write(blob)
        got += 1
    return got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--symbols", default="")
    args = ap.parse_args()
    syms = args.symbols.split(",") if args.symbols else \
        [s.strip() for s in open(os.path.join(HERE, "universe.txt")) if s.strip()]
    print(f"{len(syms)} contracts, {len(list(months()))} months each", flush=True)
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(16) as ex:
        n_files = sum(ex.map(fetch_funding, syms))
    print(f"funding files: {n_files}", flush=True)
    t0, status = time.time(), {}
    with ProcessPoolExecutor(args.workers) as ex:
        futs = {ex.submit(job, s): s for s in syms}
        for i, f in enumerate(as_completed(futs), 1):
            s, st, n = f.result()
            status[st] = status.get(st, 0) + 1
            print(f"  [{i}/{len(syms)}] {s:10s} {st:8s} {n:7d} hour marks  "
                  f"{(time.time() - t0) / 60:5.1f} min", flush=True)
    print("done", status)


if __name__ == "__main__":
    sys.exit(main())
