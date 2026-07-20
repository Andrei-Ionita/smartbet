"""ROI tuning experiments (Approach 1 quick-wins).

Design spec: docs/superpowers/specs/2026-07-20-roi-tuning-design.md
Parent context: docs/audit/roi-audit-2026-07-16.md (audit that revealed near-zero real ROI)

Reads the post-backfill snapshot and runs 5 experiments:
  E1: confidence threshold sweep
  E2: EV shrinkage factor sweep
  E3: league blacklist/whitelist analysis
  E4: market × confidence 2D grid
  E5: Kelly stake sizing simulation

Every experiment carries a bootstrap 95% CI and emits a SHIP/INVESTIGATE/DISCARD verdict.

Usage:
    python roi-tuning-2026-07-20.py --snapshot <sqlite> [--out <report.md>]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os as _os
import sqlite3
import sys
from typing import Optional

import numpy as np
import pandas as pd


# ---- Data loading (copied from audit script for reproducibility) ------

TRUE_STRINGS = {'True', 't', '1', 'true'}


def _coerce_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).isin(TRUE_STRINGS)


def load_universe(snapshot_path: str) -> pd.DataFrame:
    """Load snapshot and return the audit universe as a DataFrame.

    Universe filter (verbatim from audit spec):
      is_recommended=True AND actual_outcome IS NOT NULL
      AND match_status != 'archived' AND is_audit_excluded != True
    """
    conn = sqlite3.connect(snapshot_path)
    df = pd.read_sql_query('SELECT * FROM prediction_log', conn)
    conn.close()

    df['is_recommended'] = _coerce_bool(df['is_recommended'])
    df['is_audit_excluded'] = _coerce_bool(
        df.get('is_audit_excluded', pd.Series([False] * len(df)))
    )
    df['confidence'] = pd.to_numeric(df['confidence'], errors='coerce')
    df['expected_value'] = pd.to_numeric(df['expected_value'], errors='coerce')
    df['profit_loss_10'] = pd.to_numeric(df['profit_loss_10'], errors='coerce')
    df['odds'] = pd.to_numeric(df['odds'], errors='coerce')
    df['prediction_logged_at'] = pd.to_datetime(
        df['prediction_logged_at'], errors='coerce', utc=True,
    )

    universe = df[
        df['is_recommended']
        & df['actual_outcome'].notna() & (df['actual_outcome'] != '')
        & (df['match_status'].fillna('') != 'archived')
        & (~df['is_audit_excluded'])
        & df['profit_loss_10'].notna()
    ].copy()
    return universe


# ---- Bootstrap CI (copied from audit script) --------------------------

def bootstrap_ci(profits: np.ndarray, n_iter: int = 10000, seed: int = 42) -> dict:
    """Bootstrap 95% CI on ROI (%). ROI = mean(profit_loss_10) / 10 * 100.

    Returns dict with NaN values for empty input.
    """
    if len(profits) == 0:
        return {'point_roi_pct': float('nan'),
                'ci_lo': float('nan'), 'ci_hi': float('nan'), 'ci_median': float('nan')}
    rng = np.random.default_rng(seed)
    n = len(profits)
    idx = rng.integers(0, n, size=(n_iter, n))
    resamples = profits[idx]
    roi_samples = resamples.mean(axis=1) / 10.0 * 100.0
    return {
        'point_roi_pct': float(profits.mean() / 10.0 * 100.0),
        'ci_lo': float(np.percentile(roi_samples, 2.5)),
        'ci_median': float(np.percentile(roi_samples, 50)),
        'ci_hi': float(np.percentile(roi_samples, 97.5)),
    }


# ---- Verdict helper ---------------------------------------------------

def classify_verdict(ci_lo: float, point: float, n: int,
                     ship_n_min: int = 100, ship_ci_lo_min: float = 1.0,
                     investigate_point_min: float = 3.0) -> str:
    """Return one of 'SHIP', 'INVESTIGATE', 'DISCARD'."""
    if np.isnan(ci_lo) or np.isnan(point):
        return 'DISCARD'
    if ci_lo > ship_ci_lo_min and n >= ship_n_min:
        return 'SHIP'
    if point > investigate_point_min:
        return 'INVESTIGATE'
    return 'DISCARD'


# ---- E1: Threshold sweep ----------------------------------------------

def e1_threshold_sweep(universe: pd.DataFrame, thresholds: list[float]) -> pd.DataFrame:
    rows = []
    for t in thresholds:
        subset = universe[universe['confidence'] >= t]
        n = len(subset)
        if n == 0:
            rows.append({'threshold': t, 'n': 0, 'roi_pct': float('nan'),
                         'ci_lo': float('nan'), 'ci_hi': float('nan'),
                         'verdict': 'DISCARD'})
            continue
        ci = bootstrap_ci(subset['profit_loss_10'].to_numpy())
        rows.append({
            'threshold': round(t, 2),
            'n': n,
            'roi_pct': ci['point_roi_pct'],
            'ci_lo': ci['ci_lo'],
            'ci_hi': ci['ci_hi'],
            'verdict': classify_verdict(ci['ci_lo'], ci['point_roi_pct'], n),
        })
    return pd.DataFrame(rows)


def format_e1(sweep_df: pd.DataFrame) -> str:
    lines = ['## E1 - Confidence threshold sweep', '',
             '**Hypothesis:** current `>= 0.60` filter is not optimal; the 0.55-0.60 bucket carries edge that is currently discarded.',
             '',
             '```',
             '  threshold   n     ROI       CI_lo    CI_hi    verdict']
    for _, r in sweep_df.iterrows():
        if r['n'] == 0:
            lines.append(f"  {r['threshold']:>5.2f}      0     n/a       n/a      n/a      DISCARD")
            continue
        lines.append(
            f"  {r['threshold']:>5.2f}   {int(r['n']):>4}  "
            f"{r['roi_pct']:+6.2f}%  {r['ci_lo']:+6.2f}%  {r['ci_hi']:+6.2f}%  {r['verdict']}"
        )
    lines.append('```')
    lines.append('')
    return '\n'.join(lines) + '\n'


def e1_recommendation(sweep_df: pd.DataFrame) -> dict:
    ships = sweep_df[sweep_df['verdict'] == 'SHIP']
    if not ships.empty:
        best = ships.sort_values('ci_lo', ascending=False).iloc[0]
        return {
            'best_threshold': float(best['threshold']),
            'best_ci_lo': float(best['ci_lo']),
            'best_n': int(best['n']),
            'best_point': float(best['roi_pct']),
            'verdict': 'SHIP',
        }
    investigates = sweep_df[sweep_df['verdict'] == 'INVESTIGATE']
    if not investigates.empty:
        best = investigates.sort_values('roi_pct', ascending=False).iloc[0]
        return {
            'best_threshold': float(best['threshold']),
            'best_ci_lo': float(best['ci_lo']),
            'best_n': int(best['n']),
            'best_point': float(best['roi_pct']),
            'verdict': 'INVESTIGATE',
        }
    return {'best_threshold': float('nan'), 'best_ci_lo': float('nan'),
            'best_n': 0, 'best_point': float('nan'), 'verdict': 'DISCARD'}


# ---- E2: EV shrinkage sweep -------------------------------------------

def e2_shrinkage_sweep(universe: pd.DataFrame, factors: list[float]) -> pd.DataFrame:
    """For each shrinkage factor k, apply ev_shrunk = ev * k and keep rows
    where ev_shrunk >= 0.05 (matches current frontend filter threshold)."""
    rows = []
    for k in factors:
        subset = universe[(universe['expected_value'] * k) >= 0.05]
        n = len(subset)
        if n == 0:
            rows.append({'factor': round(k, 2), 'n': 0, 'roi_pct': float('nan'),
                         'ci_lo': float('nan'), 'ci_hi': float('nan'),
                         'verdict': 'DISCARD'})
            continue
        ci = bootstrap_ci(subset['profit_loss_10'].to_numpy())
        rows.append({
            'factor': round(k, 2),
            'n': n,
            'roi_pct': ci['point_roi_pct'],
            'ci_lo': ci['ci_lo'],
            'ci_hi': ci['ci_hi'],
            'verdict': classify_verdict(ci['ci_lo'], ci['point_roi_pct'], n),
        })
    return pd.DataFrame(rows)


def format_e2(sweep_df: pd.DataFrame) -> str:
    lines = ['## E2 - EV shrinkage factor sweep', '',
             "**Hypothesis:** model's EV is ~20 pp too optimistic; shrinkage factor before the `ev >= 0.05` filter keeps only genuinely-value picks.",
             '',
             '```',
             '  factor   n     ROI       CI_lo    CI_hi    verdict']
    for _, r in sweep_df.iterrows():
        if r['n'] == 0:
            lines.append(f"  {r['factor']:>4.2f}     0     n/a       n/a      n/a      DISCARD")
            continue
        lines.append(
            f"  {r['factor']:>4.2f}  {int(r['n']):>4}  "
            f"{r['roi_pct']:+6.2f}%  {r['ci_lo']:+6.2f}%  {r['ci_hi']:+6.2f}%  {r['verdict']}"
        )
    lines.append('```')
    lines.append('')
    return '\n'.join(lines) + '\n'


def e2_recommendation(sweep_df: pd.DataFrame) -> dict:
    ships = sweep_df[sweep_df['verdict'] == 'SHIP']
    if not ships.empty:
        best = ships.sort_values('ci_lo', ascending=False).iloc[0]
        return {
            'best_factor': float(best['factor']),
            'best_ci_lo': float(best['ci_lo']),
            'best_n': int(best['n']),
            'best_point': float(best['roi_pct']),
            'verdict': 'SHIP',
        }
    investigates = sweep_df[sweep_df['verdict'] == 'INVESTIGATE']
    if not investigates.empty:
        best = investigates.sort_values('roi_pct', ascending=False).iloc[0]
        return {
            'best_factor': float(best['factor']),
            'best_ci_lo': float(best['ci_lo']),
            'best_n': int(best['n']),
            'best_point': float(best['roi_pct']),
            'verdict': 'INVESTIGATE',
        }
    return {'best_factor': float('nan'), 'best_ci_lo': float('nan'),
            'best_n': 0, 'best_point': float('nan'), 'verdict': 'DISCARD'}


# ---- E3: League analysis ----------------------------------------------

def e3_league_analysis(universe: pd.DataFrame, min_n: int = 15) -> pd.DataFrame:
    """Per-league ROI + CI. Category tags blacklist (CI_hi < 0),
    whitelist (CI_lo > 0), or neutral."""
    rows = []
    for league, g in universe.groupby(universe['league'].fillna('unknown')):
        if len(g) < min_n:
            continue
        ci = bootstrap_ci(g['profit_loss_10'].to_numpy())
        if ci['ci_hi'] < 0:
            category = 'blacklist'
        elif ci['ci_lo'] > 0:
            category = 'whitelist'
        else:
            category = 'neutral'
        rows.append({
            'league': league,
            'n': len(g),
            'roi_pct': ci['point_roi_pct'],
            'ci_lo': ci['ci_lo'],
            'ci_hi': ci['ci_hi'],
            'category': category,
        })
    return pd.DataFrame(rows).sort_values('n', ascending=False)


def e3_scenarios(universe: pd.DataFrame, per_league: pd.DataFrame) -> pd.DataFrame:
    """Compute ROI under three scenarios."""
    scenarios = []
    # Current: entire universe
    ci = bootstrap_ci(universe['profit_loss_10'].to_numpy())
    scenarios.append({
        'scenario': 'current',
        'n': len(universe),
        'roi_pct': ci['point_roi_pct'],
        'ci_lo': ci['ci_lo'],
        'ci_hi': ci['ci_hi'],
        'verdict': classify_verdict(ci['ci_lo'], ci['point_roi_pct'], len(universe)),
    })

    blacklist_leagues = per_league[per_league['category'] == 'blacklist']['league'].tolist()
    subset_bl = universe[~universe['league'].isin(blacklist_leagues)]
    ci_bl = bootstrap_ci(subset_bl['profit_loss_10'].to_numpy())
    scenarios.append({
        'scenario': f'blacklist_applied ({len(blacklist_leagues)} leagues removed)',
        'n': len(subset_bl),
        'roi_pct': ci_bl['point_roi_pct'],
        'ci_lo': ci_bl['ci_lo'],
        'ci_hi': ci_bl['ci_hi'],
        'verdict': classify_verdict(ci_bl['ci_lo'], ci_bl['point_roi_pct'], len(subset_bl)),
    })

    whitelist_leagues = per_league[per_league['category'] == 'whitelist']['league'].tolist()
    subset_wl = universe[universe['league'].isin(whitelist_leagues)]
    ci_wl = bootstrap_ci(subset_wl['profit_loss_10'].to_numpy())
    scenarios.append({
        'scenario': f'whitelist_only ({len(whitelist_leagues)} leagues kept)',
        'n': len(subset_wl),
        'roi_pct': ci_wl['point_roi_pct'],
        'ci_lo': ci_wl['ci_lo'],
        'ci_hi': ci_wl['ci_hi'],
        'verdict': classify_verdict(ci_wl['ci_lo'], ci_wl['point_roi_pct'], len(subset_wl)),
    })

    return pd.DataFrame(scenarios)


def format_e3(per_league: pd.DataFrame, scenarios: pd.DataFrame) -> str:
    lines = ['## E3 - League blacklist/whitelist', '',
             '**Hypothesis:** a few leagues drag overall ROI down; removing them lifts total edge.',
             '',
             '**Per-league (n >= 15):**', '',
             '```',
             '  league                        n     ROI       CI_lo    CI_hi    category']
    for _, r in per_league.iterrows():
        lines.append(
            f"  {str(r['league']):<28} {int(r['n']):>4}  "
            f"{r['roi_pct']:+6.2f}%  {r['ci_lo']:+6.2f}%  {r['ci_hi']:+6.2f}%  {r['category']}"
        )
    lines.append('```')
    lines.append('')
    lines.append('**Scenarios:**')
    lines.append('')
    lines.append('```')
    lines.append('  scenario                                n     ROI       CI_lo    CI_hi    verdict')
    for _, r in scenarios.iterrows():
        lines.append(
            f"  {str(r['scenario']):<38} {int(r['n']):>4}  "
            f"{r['roi_pct']:+6.2f}%  {r['ci_lo']:+6.2f}%  {r['ci_hi']:+6.2f}%  {r['verdict']}"
        )
    lines.append('```')
    lines.append('')
    return '\n'.join(lines) + '\n'


def e3_recommendation(scenarios: pd.DataFrame, per_league: pd.DataFrame) -> dict:
    blacklist_row = scenarios[scenarios['scenario'].str.startswith('blacklist_applied')].iloc[0]
    blacklist_leagues = per_league[per_league['category'] == 'blacklist']['league'].tolist()
    return {
        'blacklist_leagues': blacklist_leagues,
        'scenario_verdict': str(blacklist_row['verdict']),
        'scenario_ci_lo': float(blacklist_row['ci_lo']),
        'scenario_n': int(blacklist_row['n']),
        'scenario_point': float(blacklist_row['roi_pct']),
    }


# ---- Main -------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--out', help='If set, write assembled report to this path.')
    args = parser.parse_args(argv)

    universe = load_universe(args.snapshot)
    print(f"Universe loaded: {len(universe)} rows\n")

    thresholds = [round(0.50 + i * 0.01, 2) for i in range(int((0.75 - 0.50) / 0.01) + 1)]
    e1_df = e1_threshold_sweep(universe, thresholds)
    print(format_e1(e1_df))
    e1_reco = e1_recommendation(e1_df)
    print(f"### E1 recommendation: {e1_reco['verdict']}")
    if e1_reco['verdict'] != 'DISCARD':
        print(f"  best threshold = {e1_reco['best_threshold']:.2f}  "
              f"point = {e1_reco['best_point']:+.2f}%  "
              f"CI_lo = {e1_reco['best_ci_lo']:+.2f}%  n = {e1_reco['best_n']}")
    print()

    factors = [round(0.5 + i * 0.05, 2) for i in range(int((1.0 - 0.5) / 0.05) + 1)]
    e2_df = e2_shrinkage_sweep(universe, factors)
    print(format_e2(e2_df))
    e2_reco = e2_recommendation(e2_df)
    print(f"### E2 recommendation: {e2_reco['verdict']}")
    if e2_reco['verdict'] != 'DISCARD':
        print(f"  best factor = {e2_reco['best_factor']:.2f}  "
              f"point = {e2_reco['best_point']:+.2f}%  "
              f"CI_lo = {e2_reco['best_ci_lo']:+.2f}%  n = {e2_reco['best_n']}")
    print()

    e3_per_league = e3_league_analysis(universe)
    e3_scen = e3_scenarios(universe, e3_per_league)
    print(format_e3(e3_per_league, e3_scen))
    e3_reco = e3_recommendation(e3_scen, e3_per_league)
    print(f"### E3 recommendation: {e3_reco['scenario_verdict']}")
    print(f"  proposed blacklist: {e3_reco['blacklist_leagues']}")
    print(f"  post-blacklist: point={e3_reco['scenario_point']:+.2f}%  "
          f"CI_lo={e3_reco['scenario_ci_lo']:+.2f}%  n={e3_reco['scenario_n']}")
    print()

    # E4-E5 wired in by subsequent tasks.
    return 0


if __name__ == '__main__':
    sys.exit(main())
