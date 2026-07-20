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


# ---- Main -------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--out', help='If set, write assembled report to this path.')
    args = parser.parse_args(argv)

    universe = load_universe(args.snapshot)
    print(f"Universe loaded: {len(universe)} rows\n")

    # E1-E5 sections wired in by subsequent tasks.
    return 0


if __name__ == '__main__':
    sys.exit(main())
