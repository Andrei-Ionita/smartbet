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


# ---- Metrics ----------------------------------------------------------

def brier_score(probs: np.ndarray, outcomes: np.ndarray) -> float:
    """Mean squared error between predicted probs and binary outcomes."""
    return float(np.mean((probs - outcomes.astype(float)) ** 2))


def reliability_curve(probs: np.ndarray, outcomes: np.ndarray,
                      n_bins: int = 10) -> pd.DataFrame:
    """Reliability diagram: 10 equal-width bins on [0, 1].
    Columns: bin_lo, bin_hi, n, mean_predicted, mean_actual, gap.
    """
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    edges[-1] += 1e-9  # include 1.0 in the last bin
    rows = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (probs >= lo) & (probs < hi)
        n = int(mask.sum())
        if n == 0:
            rows.append({'bin_lo': float(lo), 'bin_hi': float(hi), 'n': 0,
                         'mean_predicted': float('nan'),
                         'mean_actual': float('nan'), 'gap': float('nan')})
            continue
        mp = float(probs[mask].mean())
        ma = float(outcomes[mask].mean())
        rows.append({'bin_lo': float(lo), 'bin_hi': float(hi), 'n': n,
                     'mean_predicted': mp, 'mean_actual': ma, 'gap': mp - ma})
    return pd.DataFrame(rows)


def ece(probs: np.ndarray, outcomes: np.ndarray, n_bins: int = 10) -> float:
    """Expected Calibration Error: weighted mean absolute gap."""
    curve = reliability_curve(probs, outcomes, n_bins)
    total = int(curve['n'].sum())
    if total == 0:
        return float('nan')
    weighted = 0.0
    for _, r in curve.iterrows():
        if r['n'] == 0:
            continue
        weighted += r['n'] * abs(r['gap'])
    return float(weighted / total)


# ---- Cross-validated calibration --------------------------------------

def _bootstrap_ece_ci(probs: np.ndarray, outcomes: np.ndarray,
                      n_bins: int = 10, n_iter: int = 10000,
                      seed: int = 42) -> dict:
    """Bootstrap 95% CI on ECE."""
    if len(probs) == 0:
        return {'point': float('nan'), 'ci_lo': float('nan'),
                'ci_hi': float('nan'), 'ci_median': float('nan')}
    rng = np.random.default_rng(seed)
    n = len(probs)
    samples = []
    for _ in range(n_iter):
        idx = rng.integers(0, n, size=n)
        samples.append(ece(probs[idx], outcomes[idx], n_bins))
    samples = np.array(samples)
    return {
        'point': float(ece(probs, outcomes, n_bins)),
        'ci_lo': float(np.percentile(samples, 2.5)),
        'ci_median': float(np.percentile(samples, 50)),
        'ci_hi': float(np.percentile(samples, 97.5)),
    }


def cross_val_calibration(universe: pd.DataFrame, n_splits: int = 5,
                          seed: int = 42) -> dict:
    """5-fold CV: fit Platt on training folds, aggregate held-out preds.

    Also fits a "final" calibrator on all rows for the reliability
    diagram + the calibrator that would be applied downstream.
    """
    conf = universe['confidence'].to_numpy()
    outcomes = universe['was_correct'].to_numpy().astype(int)

    # Collect held-out predictions across all folds
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
    held_out_pre = np.empty_like(conf)
    held_out_post = np.empty_like(conf)
    for train_idx, test_idx in skf.split(conf, outcomes):
        a, b = fit_platt(conf[train_idx], outcomes[train_idx])
        held_out_pre[test_idx] = conf[test_idx]  # pre-cal = raw confidence
        held_out_post[test_idx] = apply_platt(conf[test_idx], a, b)

    # Final calibrator: fit on all data (used for reliability + downstream)
    final_a, final_b = fit_platt(conf, outcomes)

    # Metrics on held-out predictions (honest CV estimate)
    brier_pre = brier_score(held_out_pre, outcomes)
    brier_post = brier_score(held_out_post, outcomes)
    ece_pre = ece(held_out_pre, outcomes)
    ece_post = ece(held_out_post, outcomes)
    ece_pre_ci = _bootstrap_ece_ci(held_out_pre, outcomes)
    ece_post_ci = _bootstrap_ece_ci(held_out_post, outcomes)

    # Reliability curves: use held-out predictions (honest)
    reliability_pre = reliability_curve(held_out_pre, outcomes)
    reliability_post = reliability_curve(held_out_post, outcomes)

    return {
        'brier_pre': brier_pre,
        'brier_post': brier_post,
        'ece_pre': ece_pre,
        'ece_post': ece_post,
        'ece_pre_ci': ece_pre_ci,
        'ece_post_ci': ece_post_ci,
        'reliability_pre': reliability_pre,
        'reliability_post': reliability_post,
        'final_a': final_a,
        'final_b': final_b,
        'held_out_pre': held_out_pre,   # for downstream targets
        'held_out_post': held_out_post,
    }


def format_global(cv: dict) -> str:
    def _fmt_curve(label, d):
        lines = [f"**{label}**", '', '```',
                 '  bin_lo  bin_hi   n     mean_pred   mean_actual   gap']
        for _, r in d.iterrows():
            if r['n'] == 0:
                lines.append(f"  {r['bin_lo']:>5.2f}  {r['bin_hi']:>5.2f}    0     n/a         n/a           n/a")
                continue
            lines.append(
                f"  {r['bin_lo']:>5.2f}  {r['bin_hi']:>5.2f}  {int(r['n']):>3}  "
                f"{r['mean_predicted']:>6.3f}       {r['mean_actual']:>6.3f}       "
                f"{r['gap']:+6.3f}"
            )
        lines.append('```')
        return '\n'.join(lines)

    brier_delta = (cv['brier_pre'] - cv['brier_post']) / cv['brier_pre'] * 100.0 \
                  if cv['brier_pre'] > 0 else float('nan')
    ece_delta = (cv['ece_pre'] - cv['ece_post']) / cv['ece_pre'] * 100.0 \
                if cv['ece_pre'] > 0 else float('nan')

    return (
        "## Global calibration (5-fold CV)\n\n"
        f"**Fitted Platt (full-sample):** `sigmoid({cv['final_a']:.3f} * confidence + {cv['final_b']:.3f})`\n\n"
        f"**Brier score:** {cv['brier_pre']:.4f} -> {cv['brier_post']:.4f} ({brier_delta:+.1f}% relative)\n\n"
        f"**ECE:** {cv['ece_pre']:.4f} (CI {cv['ece_pre_ci']['ci_lo']:.4f} -> {cv['ece_pre_ci']['ci_hi']:.4f})"
        f" -> {cv['ece_post']:.4f} (CI {cv['ece_post_ci']['ci_lo']:.4f} -> {cv['ece_post_ci']['ci_hi']:.4f})"
        f"  ({ece_delta:+.1f}% relative)\n\n"
        f"### Reliability diagram\n\n"
        f"{_fmt_curve('Pre-calibration (raw confidence)', cv['reliability_pre'])}\n\n"
        f"{_fmt_curve('Post-calibration (held-out CV)', cv['reliability_post'])}\n"
    )


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

    cv = cross_val_calibration(universe)
    print(format_global(cv))

    # Task 3-5 wire in segmentation + verdicts.
    return 0


if __name__ == '__main__':
    sys.exit(main())
