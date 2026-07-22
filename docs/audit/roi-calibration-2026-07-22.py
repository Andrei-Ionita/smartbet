"""ROI calibration study (Approach C — segmented diagnostic).

Design spec: docs/superpowers/specs/2026-07-22-roi-calibration-design.md
Parent context: prior audit and tuning at docs/audit/roi-audit-2026-07-16.md
and docs/audit/roi-tuning-2026-07-20.md.

Fits a Platt calibrator on the 252 resolved O/U 2.5 rows via 5-fold CV,
computes global calibration metrics + miscalibration heatmap by
confidence bucket / league / time period, emits per-target verdicts
(Display / Kelly / Filter re-selection).

Usage:
    python roi-calibration-2026-07-22.py --snapshot <sqlite> [--out <report.md>]
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
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold


# ---- Data loading (adapted from prior scripts) ------------------------

TRUE_STRINGS = {'True', 't', '1', 'true'}


def _coerce_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).isin(TRUE_STRINGS)


def load_universe(snapshot_path: str) -> pd.DataFrame:
    """Load snapshot; filter to the calibration universe.

    Universe filter (from prior audit/tuning + calibration-specific
    market restriction):
      is_recommended=True
      AND actual_outcome IS NOT NULL AND actual_outcome != ''
      AND match_status != 'archived' AND is_audit_excluded != True
      AND profit_loss_10 NOT NULL AND confidence NOT NULL
      AND market_type = 'over_under_2.5'
    """
    conn = sqlite3.connect(snapshot_path)
    df = pd.read_sql_query('SELECT * FROM prediction_log', conn)
    conn.close()

    df['is_recommended'] = _coerce_bool(df['is_recommended'])
    df['is_audit_excluded'] = _coerce_bool(
        df.get('is_audit_excluded', pd.Series([False] * len(df)))
    )
    df['was_correct'] = _coerce_bool(df.get('was_correct',
                                             pd.Series([False] * len(df))))
    df['confidence'] = pd.to_numeric(df['confidence'], errors='coerce')
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
        & df['confidence'].notna()
        & (df['market_type'] == 'over_under_2.5')
    ].copy()
    return universe


# ---- Bootstrap CI (general-purpose; works on any metric) --------------

def bootstrap_ci(values: np.ndarray, n_iter: int = 10000,
                 seed: int = 42) -> dict:
    """Bootstrap 95% CI on the mean of `values`.

    Returns dict with NaN values for empty input.
    """
    if len(values) == 0:
        return {'point': float('nan'),
                'ci_lo': float('nan'), 'ci_hi': float('nan'),
                'ci_median': float('nan')}
    rng = np.random.default_rng(seed)
    n = len(values)
    idx = rng.integers(0, n, size=(n_iter, n))
    resamples = values[idx]
    means = resamples.mean(axis=1)
    return {
        'point': float(values.mean()),
        'ci_lo': float(np.percentile(means, 2.5)),
        'ci_median': float(np.percentile(means, 50)),
        'ci_hi': float(np.percentile(means, 97.5)),
    }


# ---- Platt calibrator -------------------------------------------------

def fit_platt(confidence: np.ndarray, outcomes: np.ndarray) -> tuple[float, float]:
    """Fit Platt scaling: sigmoid(a * confidence + b).

    Returns (a, b). Uses sklearn's LogisticRegression under the hood
    (single feature, no regularization scaling).
    """
    X = confidence.reshape(-1, 1)
    y = outcomes.astype(int)
    lr = LogisticRegression(C=1e10, solver='lbfgs')  # near-zero regularization
    lr.fit(X, y)
    a = float(lr.coef_[0][0])
    b = float(lr.intercept_[0])
    return a, b


def apply_platt(confidence: np.ndarray, a: float, b: float) -> np.ndarray:
    """Apply calibrator: sigmoid(a * confidence + b)."""
    logits = a * confidence + b
    return 1.0 / (1.0 + np.exp(-logits))


# ---- Main -------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--out', help='If set, write assembled report to this path.')
    args = parser.parse_args(argv)

    universe = load_universe(args.snapshot)
    print(f"Universe loaded: {len(universe)} rows (O/U 2.5, resolved)\n")

    # Hard stop if universe too small
    if len(universe) < 100:
        print(f"HARD STOP: universe n={len(universe)} < 100. Verdict: INSUFFICIENT_SIGNAL")
        return 2

    # Subsequent tasks will fill in Q&A sections.
    return 0


if __name__ == '__main__':
    sys.exit(main())
