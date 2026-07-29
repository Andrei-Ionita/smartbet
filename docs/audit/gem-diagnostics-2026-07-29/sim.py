"""Gate simulation + sensitivity for the hidden-gem selector (read-only)."""
from collections import defaultdict

from analysis import (bucket, conf_gate, f, load, roi_pct, shrunk, tier,
                      universe_b, wins)

MARGIN_FALLBACK = 0.05
SAFETY_EPS = 0.01


def market_margins(rows):
    """Measured over-confidence per market: mean(conf) - win_rate."""
    by = defaultdict(list)
    for r in rows:
        by[r["market_type"]].append(r)
    out = {}
    for m, rs in by.items():
        n = len(rs)
        out[m] = dict(
            n=n,
            margin=(sum(f(r["confidence"]) for r in rs) / n) - (wins(rs) / n),
        )
    return out


def build_cells(rows):
    cells = defaultdict(list)
    for r in rows:
        cells[(r["market_type"], bucket(f(r["confidence"])))].append(r)
    return cells


CONFIGS = {
    "conservative": dict(MIN_CELL_N=60, MIN_SHRUNK_ROI=5.0, MIN_EDGE=0.04,
                         MIN_TIER_N=15, TIER_VETO=-3.0, MIN_ODDS=1.4, MAX_ODDS=3.5,
                         RECENT_N=20, MIN_RECENT_N=20, RECENT_VETO=-5.0),
    "balanced":     dict(MIN_CELL_N=40, MIN_SHRUNK_ROI=2.0, MIN_EDGE=0.02,
                         MIN_TIER_N=15, TIER_VETO=-3.0, MIN_ODDS=1.4, MAX_ODDS=3.5,
                         RECENT_N=20, MIN_RECENT_N=20, RECENT_VETO=-5.0),
    "permissive":   dict(MIN_CELL_N=25, MIN_SHRUNK_ROI=1.0, MIN_EDGE=0.01,
                         MIN_TIER_N=10, TIER_VETO=-8.0, MIN_ODDS=1.3, MAX_ODDS=5.0,
                         RECENT_N=20, MIN_RECENT_N=20, RECENT_VETO=-10.0),
}


def cell_stats(cells, cfg):
    """Which cells qualify under cfg, plus tier/recency verdicts."""
    out = {}
    for key, rs in cells.items():
        n = len(rs)
        raw = roi_pct(rs)
        sh = shrunk(n, raw)
        rs_sorted = sorted(rs, key=lambda r: r["kickoff"])
        rec = rs_sorted[-cfg["RECENT_N"]:]
        rec_roi = roi_pct(rec)
        rec_veto = len(rec) >= cfg["MIN_RECENT_N"] and rec_roi < cfg["RECENT_VETO"]
        tiers = defaultdict(list)
        for r in rs:
            tiers[tier(r["league"])].append(r)
        tier_verdict = {}
        for t, trs in tiers.items():
            troi = roi_pct(trs)
            tier_verdict[t] = dict(
                n=len(trs), roi=troi,
                veto=(len(trs) >= cfg["MIN_TIER_N"] and troi < cfg["TIER_VETO"]),
            )
        out[key] = dict(n=n, raw=raw, shrunk=sh, rec_roi=rec_roi,
                        rec_veto=rec_veto, tiers=tier_verdict,
                        passes=(n >= cfg["MIN_CELL_N"]
                                and sh >= cfg["MIN_SHRUNK_ROI"]
                                and not rec_veto))
    return out


def evaluate(pick, cells_stats, margins, cfg):
    """Return (eligible, reasons) for one live pick."""
    reasons = []
    m = pick["market_type"]
    c = f(pick["confidence"])
    odds = f(pick["odds"])
    if c is None or not conf_gate(m, c):
        reasons.append("G3_below_market_threshold")
    if odds is None:
        reasons.append("G2_null_odds")
    elif not (cfg["MIN_ODDS"] <= odds <= cfg["MAX_ODDS"]):
        reasons.append(f"G2_odds_out_of_band({odds})")
    key = (m, bucket(c)) if c is not None else None
    cs = cells_stats.get(key)
    if cs is None:
        reasons.append("G4_no_cell_history")
    else:
        if cs["n"] < cfg["MIN_CELL_N"]:
            reasons.append(f"G4_cell_n_too_small({cs['n']}<{cfg['MIN_CELL_N']})")
        if cs["shrunk"] < cfg["MIN_SHRUNK_ROI"]:
            reasons.append(f"G4_shrunk_roi_below_bar({cs['shrunk']:.2f})")
        if cs["rec_veto"]:
            reasons.append(f"G6_recent_veto({cs['rec_roi']:.2f})")
        tv = cs["tiers"].get(tier(pick["league"]))
        if tv and tv["veto"]:
            reasons.append(f"G5_tier_veto({tier(pick['league'])},{tv['roi']:.1f})")
    if c is not None and odds is not None:
        mg = margins.get(m)
        margin = mg["margin"] if mg and mg["n"] >= 30 else MARGIN_FALLBACK
        margin = max(0.0, margin)
        p_cons = max(0.0, min(1.0, c - margin - SAFETY_EPS))
        edge = p_cons * odds - 1
        if edge < cfg["MIN_EDGE"]:
            reasons.append(f"G7_edge_below_bar({edge:+.3f})")
        pick["_edge"] = edge
        pick["_p_cons"] = p_cons
    return (len(reasons) == 0), reasons


def main():
    rows = universe_b(load("universe.csv"))
    pending = load("pending.csv")
    margins = market_margins(rows)
    cells = build_cells(rows)

    print("=== Measured over-confidence margin (Universe B) ===")
    for m, d in sorted(margins.items(), key=lambda kv: -kv[1]["n"]):
        used = d["margin"] if d["n"] >= 30 else MARGIN_FALLBACK
        print(f"  {m:16s} n={d['n']:4d} measured={d['margin']:+.4f} "
              f"used={max(0.0,used):+.4f}"
              f"{'  (fallback: n<30)' if d['n'] < 30 else ''}")

    print("\n=== Odds distribution, over_under_2.5 (sanity check) ===")
    ou = [f(r["odds"]) for r in rows
          if r["market_type"] == "over_under_2.5" and f(r["odds"])]
    ou.sort()
    print(f"  n={len(ou)} min={ou[0]:.2f} p25={ou[len(ou)//4]:.2f} "
          f"median={ou[len(ou)//2]:.2f} p75={ou[3*len(ou)//4]:.2f} max={ou[-1]:.2f}")
    print(f"  above 3.0: {sum(1 for o in ou if o > 3.0)}  "
          f"above 3.5: {sum(1 for o in ou if o > 3.5)}")

    for name, cfg in CONFIGS.items():
        cs = cell_stats(cells, cfg)
        print(f"\n{'='*78}\n=== CONFIG: {name.upper()} ===")
        print(f"  MIN_CELL_N={cfg['MIN_CELL_N']} MIN_SHRUNK_ROI={cfg['MIN_SHRUNK_ROI']} "
              f"MIN_EDGE={cfg['MIN_EDGE']} odds[{cfg['MIN_ODDS']},{cfg['MAX_ODDS']}]")
        elig = [k for k, v in cs.items() if v["passes"]]
        print(f"  eligible historical cells: {len(elig)}")
        for k in sorted(elig):
            v = cs[k]
            print(f"    {k[0]}@{k[1]}  n={v['n']} shrunkROI={v['shrunk']:.2f}% "
                  f"recent20={v['rec_roi']:.2f}%")
        # live picks
        live_ok = []
        print("  --- live pending picks ---")
        for p in pending:
            ok, reasons = evaluate(dict(p), cs, margins, cfg)
            tagfail = "PASS" if ok else "fail"
            if ok:
                live_ok.append(p)
            edge = p.get("_edge")
            print(f"    [{tagfail}] {p['home_team'][:16]:16s} v {p['away_team'][:16]:16s} "
                  f"{p['market_type']:15s} conf={f(p['confidence']):.3f} odds={p['odds']:>5s}"
                  + ("" if ok else f"  <- {reasons[0]}"))
        print(f"  ==> LIVE GEMS: {len(live_ok)}")
        # historical posting frequency
        hist_ok = 0
        for r in rows:
            ok, _ = evaluate(dict(r), cs, margins, cfg)
            if ok:
                hist_ok += 1
        span_days = 200.0
        print(f"  ==> historical picks passing: {hist_ok}/{len(rows)} "
              f"(~{hist_ok/span_days*7:.1f}/week over ~{span_days:.0f}d)")


if __name__ == "__main__":
    main()
