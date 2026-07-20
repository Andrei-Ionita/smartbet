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

    # E3-E5 wired in by subsequent tasks.
    return 0


if __name__ == '__main__':
    sys.exit(main())
