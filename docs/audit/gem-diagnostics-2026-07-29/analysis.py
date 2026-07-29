"""Gem-selector diagnostics D3-D7: cell census, tiers, timing, gate simulation.

Read-only: operates on CSV snapshots pulled by pull.py. No DB writes.
"""
import csv
import math
import random
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone

random.seed(42)  # matches prior audits

# ── Universe B (the audit standard) ───────────────────────────────────────
PER_MARKET = {"over_under_2.5": 0.55}
DEFAULT_CONF = 0.60


def conf_gate(market, conf):
    return conf >= PER_MARKET.get(market, DEFAULT_CONF)


def load(path):
    return list(csv.DictReader(open(path, encoding="utf-8")))


def f(v):
    return float(v) if v not in ("", None, "NULL") else None


def universe_b(rows):
    out = []
    for r in rows:
        if r["is_audit_excluded"].lower() in ("true", "t", "1"):
            continue
        if r["match_status"] == "archived":
            continue
        if r["profit_loss_10"] in ("", None):
            continue
        c = f(r["confidence"])
        if c is None or not conf_gate(r["market_type"], c):
            continue
        out.append(r)
    return out


# ── Buckets ───────────────────────────────────────────────────────────────
def bucket(c):
    if c < 0.60:
        return "0.55-0.60"
    if c < 0.65:
        return "0.60-0.65"
    return "0.65+"


# ── League tiers ──────────────────────────────────────────────────────────
def norm(name):
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in s.lower())
    return " ".join(s.split())


TIER_A = {"premier league", "la liga", "serie a", "bundesliga", "ligue 1",
          "champions league", "uefa champions league", "europa league",
          "uefa europa league", "world cup", "european championship"}
TIER_B = {"championship", "eredivisie", "primeira liga", "scottish premiership",
          "premiership", "major league soccer", "mls", "liga mx", "super league",
          "serie b", "2 bundesliga", "ligue 2", "la liga 2"}


def tier(league):
    n = norm(league)
    if n in TIER_A:
        return "A"
    if n in TIER_B:
        return "B"
    return "C/UNK"


# ── Metrics ───────────────────────────────────────────────────────────────
def roi_pct(rs):
    if not rs:
        return 0.0
    return sum(f(r["profit_loss_10"]) for r in rs) / (len(rs) * 10.0) * 100


def wins(rs):
    return sum(1 for r in rs if r["was_correct"].lower() in ("true", "t", "1"))


def shrunk(n, roi, K=50, prior=0.0):
    return n / (n + K) * roi + K / (n + K) * prior


def boot_ci(rs, iters=10000, lo=2.5, hi=97.5):
    if len(rs) < 2:
        return (float("nan"), float("nan"))
    pls = [f(r["profit_loss_10"]) for r in rs]
    n = len(pls)
    out = []
    for _ in range(iters):
        s = sum(pls[random.randrange(n)] for _ in range(n))
        out.append(s / (n * 10.0) * 100)
    out.sort()
    return (out[int(iters * lo / 100)], out[int(iters * hi / 100)])


def main():
    rows = universe_b(load("universe.csv"))
    print(f"Universe B: {len(rows)} resolved rows\n")

    # ── D5 league census ──────────────────────────────────────────────
    print("=== D5  League census (Universe B) ===")
    lg = defaultdict(list)
    for r in rows:
        lg[r["league"]].append(r)
    print(f"{'league':30s} {'tier':6s} {'n':>4s} {'roi%':>8s}")
    for name, rs in sorted(lg.items(), key=lambda kv: -len(kv[1])):
        print(f"{name[:30]:30s} {tier(name):6s} {len(rs):4d} {roi_pct(rs):8.2f}")
    print(f"distinct leagues: {len(lg)}")
    tc = defaultdict(list)
    for r in rows:
        tc[tier(r["league"])].append(r)
    print("\ntier totals:")
    for t, rs in sorted(tc.items()):
        print(f"  tier {t:6s} n={len(rs):4d} roi={roi_pct(rs):7.2f}%")

    # ── D3 cell census ────────────────────────────────────────────────
    print("\n=== D3  Cell census: market x confidence bucket ===")
    cells = defaultdict(list)
    for r in rows:
        cells[(r["market_type"], bucket(f(r["confidence"])))].append(r)
    hdr = (f"{'cell':32s} {'n':>4s} {'W':>4s} {'L':>4s} {'avgOdds':>8s} "
           f"{'rawROI':>8s} {'shrROI':>8s} {'CI_lo':>8s} {'CI_hi':>8s} {'rec20':>8s}")
    print(hdr)
    print("-" * len(hdr))
    census = {}
    for key, rs in sorted(cells.items(), key=lambda kv: -len(kv[1])):
        n = len(rs)
        raw = roi_pct(rs)
        sh = shrunk(n, raw)
        lo, hi = boot_ci(rs)
        rs_sorted = sorted(rs, key=lambda r: r["kickoff"])
        rec = roi_pct(rs_sorted[-20:]) if n >= 20 else float("nan")
        avg_odds = sum(f(r["odds"]) for r in rs if f(r["odds"])) / max(
            1, sum(1 for r in rs if f(r["odds"])))
        census[key] = dict(n=n, raw=raw, shrunk=sh, lo=lo, hi=hi, rec=rec)
        print(f"{key[0]+'@'+key[1]:32s} {n:4d} {wins(rs):4d} {n-wins(rs):4d} "
              f"{avg_odds:8.3f} {raw:8.2f} {sh:8.2f} {lo:8.2f} {hi:8.2f} {rec:8.2f}")

    # ── D4 tier breakdown of viable cells ─────────────────────────────
    print("\n=== D4  League-tier breakdown within each cell ===")
    for key, rs in sorted(cells.items(), key=lambda kv: -len(kv[1])):
        if len(rs) < 20:
            continue
        print(f"\n  {key[0]}@{key[1]}  (n={len(rs)})")
        byt = defaultdict(list)
        for r in rs:
            byt[tier(r["league"])].append(r)
        for t, trs in sorted(byt.items()):
            print(f"    tier {t:6s} n={len(trs):4d} roi={roi_pct(trs):8.2f}%")

    # ── D7 odds age ───────────────────────────────────────────────────
    print("\n=== D7  Lead time: kickoff - prediction_logged_at (hours) ===")
    ages = []
    for r in rows:
        try:
            ko = datetime.fromisoformat(r["kickoff"])
            lg_ = datetime.fromisoformat(r["prediction_logged_at"])
            ages.append((ko - lg_).total_seconds() / 3600.0)
        except Exception:
            pass
    ages.sort()
    if ages:
        def pct(p):
            return ages[min(len(ages) - 1, int(len(ages) * p / 100))]
        print(f"  n={len(ages)}  min={ages[0]:.1f}h  p25={pct(25):.1f}h  "
              f"median={pct(50):.1f}h  p75={pct(75):.1f}h  max={ages[-1]:.1f}h")
        for lo_, hi_ in [(0, 6), (6, 24), (24, 48), (48, 96), (96, 1e9)]:
            c = sum(1 for a in ages if lo_ <= a < hi_)
            print(f"    {lo_:>4}-{hi_ if hi_ < 1e9 else 'inf':>4}h : {c:4d} "
                  f"({c/len(ages)*100:5.1f}%)")
    return census, cells, rows


if __name__ == "__main__":
    main()
