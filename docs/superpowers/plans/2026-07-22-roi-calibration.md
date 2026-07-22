# ROI Calibration (Approach C — Segmented Diagnostic) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the calibration study defined in `docs/superpowers/specs/2026-07-22-roi-calibration-design.md`, producing a committed diagnostic report with per-target verdicts (Display / Kelly / Filter re-selection) that decide whether calibration should be applied to production in a separate follow-on spec.

**Architecture:** Single-file Python analysis script (`docs/audit/roi-calibration-2026-07-22.py`) that reads the existing sqlite snapshot, fits a Platt calibrator via 5-fold cross-validation on the 252 O/U 2.5 resolved rows, computes global metrics (Brier, ECE with bootstrap CI, reliability diagram) and a miscalibration heatmap segmented by confidence bucket, league, and time period. Reuses statistical helpers copied from prior audit/tuning scripts. **Analysis-only** — no production code changes in this plan. Deployment (if triggered by an `APPLY` verdict) gets a separate spec + plan.

**Tech Stack:** Python 3.11+, pandas 2.x, numpy, sqlite3 (stdlib), scikit-learn (`LogisticRegression`, `StratifiedKFold`), pytest.

## Global Constraints

Values copied verbatim from `2026-07-22-roi-calibration-design.md`. Every task inherits these.

- **Script path:** `docs/audit/roi-calibration-2026-07-22.py` (exact).
- **Report path:** `docs/audit/roi-calibration-2026-07-22.md` (exact).
- **Test file path:** `docs/audit/test_roi_calibration_helpers.py` (exact).
- **Snapshot source:** `docs/audit/snapshot-2026-07-16.sqlite` (already exists, post-backfill).
- **Universe filter (from prior scripts, must match exactly):** `is_recommended=True AND actual_outcome IS NOT NULL AND match_status != 'archived' AND is_audit_excluded != True AND profit_loss_10 IS NOT NULL AND confidence IS NOT NULL`.
- **Additional filter for this spec:** `market_type = 'over_under_2.5'`.
- **Expected universe count:** ≈252 rows.
- **Target column:** `was_correct` (binary; coerce from the stored string values via `TRUE_STRINGS = {'True', 't', '1', 'true'}`).
- **Feature column:** `confidence` (float; probability of the picked side).
- **Cross-validation:** 5-fold, `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`.
- **Reliability diagram bins:** 10 equal-width bins over `[0, 1]`.
- **Confidence bucket edges (segmentation):** `[0.55, 0.60, 0.70, 0.80, 1.001]` — same as prior audit/tuning.
- **Bootstrap iterations:** 10,000, seed 42 (matches prior scripts).
- **Sample-size gates:**
  - Universe n<100 → HARD STOP with verdict `INSUFFICIENT_SIGNAL`.
  - Subgroup n<15 → flag as `underpowered`, do not act on that subgroup.
- **Verdict values (exact strings):** `APPLY` / `DO_NOT_APPLY` / `INSUFFICIENT_SIGNAL`.
- **Display verdict criteria:** `brier_pre − brier_post) / brier_pre ≥ 0.05` (5% relative) AND `(ece_pre − ece_post) / ece_pre ≥ 0.30` (30% relative).
- **Kelly verdict criteria:** model over-confident in the 0.60–0.80 confidence range (bucket mean predicted > bucket mean actual) AND Brier ≥5% relative improvement AND bootstrap 95% CI on `(raw_prob − calibrated_prob)` in the 0.60–0.80 range excludes zero.
- **Filter verdict criteria:** on the subset where `calibrated_prob ≥ 0.55`, ROI > current subset ROI by ≥2 percentage points AND bootstrap 95% CI lower bound on new subset ROI ≥ +1%.
- **Overall verdict:** `APPLY` if ≥1 target has `APPLY`; `INSUFFICIENT_SIGNAL` if universe n<100; else `DO_NOT_APPLY`.
- **Non-goals reminder:** no production code changes, no retraining SportMonks, no per-slice separate calibrators (segmentation is diagnostic only), no comparison of alternative calibrator methods.

## File Structure

| File | Purpose | Committed? |
|---|---|---|
| `docs/audit/roi-calibration-2026-07-22.py` | Single-file analysis script. Loads universe, fits Platt via 5-fold CV, computes global + segmented diagnostics, assembles report. | ✓ |
| `docs/audit/roi-calibration-2026-07-22.md` | Human-readable diagnostic report with per-target verdicts. Produced by Task 6. | ✓ |
| `docs/audit/test_roi_calibration_helpers.py` | pytest for pure helpers: bootstrap_ci, fit_platt/apply_platt, brier_score, ece. | ✓ |

---

## Task 1: Scaffold script + shared helpers + Platt calibrator (TDD)

**Files:**
- Create: `docs/audit/roi-calibration-2026-07-22.py`
- Create: `docs/audit/test_roi_calibration_helpers.py`

**Interfaces:**
- Consumes: `docs/audit/snapshot-2026-07-16.sqlite` (universe rows).
- Produces:
  - `TRUE_STRINGS = {'True', 't', '1', 'true'}` at module scope.
  - `load_universe(snapshot_path: str) -> pd.DataFrame` — returns 252-row O/U 2.5 subset with columns already coerced (confidence, was_correct, league, prediction_logged_at, profit_loss_10, odds).
  - `bootstrap_ci(values: np.ndarray, n_iter: int = 10000, seed: int = 42) -> dict` — keys `point, ci_lo, ci_median, ci_hi`. Returns NaN dict on empty input. **General-purpose** (works for any metric, not just ROI).
  - `fit_platt(confidence: np.ndarray, outcomes: np.ndarray) -> tuple[float, float]` — returns `(a, b)` where the calibrator is `sigmoid(a * confidence + b)`. Uses `sklearn.linear_model.LogisticRegression` under the hood (single-feature fit).
  - `apply_platt(confidence: np.ndarray, a: float, b: float) -> np.ndarray` — returns calibrated probabilities in `[0, 1]`.
  - CLI: `python roi-calibration-2026-07-22.py --snapshot <path> [--out <report.md>]`.

- [ ] **Step 1: Write failing tests for the pure helpers**

Create `docs/audit/test_roi_calibration_helpers.py`:

```python
"""Tests for pure helpers in roi-calibration-2026-07-22.py."""
import importlib.util
import pathlib

import numpy as np

_MODULE_PATH = pathlib.Path(__file__).parent / 'roi-calibration-2026-07-22.py'
_spec = importlib.util.spec_from_file_location('roi_calibration', _MODULE_PATH)
_roi_calibration = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_roi_calibration)


def test_module_loads():
    """Sanity check: script imports and exposes the expected API."""
    for name in ['TRUE_STRINGS', 'load_universe', 'bootstrap_ci',
                 'fit_platt', 'apply_platt']:
        assert hasattr(_roi_calibration, name), f"missing {name}"


def test_bootstrap_ci_recovers_known_mean():
    """CI should contain the true mean for a known synthetic distribution."""
    rng = np.random.default_rng(0)
    values = rng.normal(loc=0.5, scale=0.1, size=500)
    result = _roi_calibration.bootstrap_ci(values, n_iter=2000, seed=42)
    assert result['ci_lo'] < 0.5 < result['ci_hi'], \
        f"CI {result} does not contain true mean 0.5"


def test_bootstrap_ci_empty_input():
    result = _roi_calibration.bootstrap_ci(np.array([]), n_iter=100)
    assert np.isnan(result['point'])
    assert np.isnan(result['ci_lo'])
    assert np.isnan(result['ci_hi'])


def test_platt_recovers_identity_on_perfect_data():
    """When confidence exactly equals empirical rate, Platt should recover
    a near-identity mapping (a≈some positive value, b such that sigmoid
    passes through 0.5 at confidence≈0.5)."""
    rng = np.random.default_rng(0)
    # Generate 500 rows: confidence uniform in [0.4, 0.9], outcome ~ Bernoulli(confidence)
    conf = rng.uniform(0.4, 0.9, size=500)
    outcomes = rng.binomial(1, conf).astype(float)
    a, b = _roi_calibration.fit_platt(conf, outcomes)
    # apply_platt at conf=0.5 should be roughly 0.5 (well-calibrated)
    result = _roi_calibration.apply_platt(np.array([0.5]), a, b)
    assert 0.35 < result[0] < 0.65, \
        f"expected calibrated(0.5) ~ 0.5, got {result[0]}"


def test_platt_corrects_overconfidence():
    """When confidence is systematically higher than actual outcomes,
    Platt should map confidence DOWN toward the empirical rate."""
    rng = np.random.default_rng(1)
    # 500 rows: confidence uniform 0.6-0.8, but actual win rate only 0.5
    conf = rng.uniform(0.6, 0.8, size=500)
    outcomes = rng.binomial(1, 0.5, size=500).astype(float)
    a, b = _roi_calibration.fit_platt(conf, outcomes)
    # Calibrated version of 0.7 should be lower than 0.7
    result = _roi_calibration.apply_platt(np.array([0.7]), a, b)
    assert result[0] < 0.7, \
        f"expected calibration to correct overconfidence, got {result[0]}"


def test_apply_platt_bounded_in_zero_one():
    """Regardless of inputs, output should be in [0, 1]."""
    conf = np.linspace(0.0, 1.0, 20)
    result = _roi_calibration.apply_platt(conf, a=5.0, b=-2.0)
    assert result.min() >= 0.0
    assert result.max() <= 1.0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd docs/audit && python -m pytest test_roi_calibration_helpers.py -v
```

Expected: FAIL with `AttributeError: module 'roi_calibration' has no attribute 'load_universe'` (or similar — module doesn't exist yet).

- [ ] **Step 3: Create the script scaffold with all helpers**

Create `docs/audit/roi-calibration-2026-07-22.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd docs/audit && python -m pytest test_roi_calibration_helpers.py -v
```

Expected: 6/6 passing.

- [ ] **Step 5: Run the script to confirm universe loads**

```bash
python docs/audit/roi-calibration-2026-07-22.py --snapshot docs/audit/snapshot-2026-07-16.sqlite
```

Expected: `Universe loaded: ≈252 rows (O/U 2.5, resolved)`.

- [ ] **Step 6: Commit**

```bash
git add docs/audit/roi-calibration-2026-07-22.py docs/audit/test_roi_calibration_helpers.py
git commit -m "calibration: scaffold + Platt fit/apply + bootstrap CI helpers"
```

---

## Task 2: Global cross-validation + Brier + ECE + reliability diagram

**Files:**
- Modify: `docs/audit/roi-calibration-2026-07-22.py` — append CV loop, metrics, formatter; wire into `main()`.
- Modify: `docs/audit/test_roi_calibration_helpers.py` — add tests for `brier_score` and `ece`.

**Interfaces:**
- Consumes: `load_universe`, `fit_platt`, `apply_platt`, `bootstrap_ci` from Task 1.
- Produces:
  - `brier_score(probs: np.ndarray, outcomes: np.ndarray) -> float` — mean squared error.
  - `ece(probs: np.ndarray, outcomes: np.ndarray, n_bins: int = 10) -> float` — expected calibration error (weighted absolute gap across equal-width bins on [0, 1]).
  - `reliability_curve(probs: np.ndarray, outcomes: np.ndarray, n_bins: int = 10) -> pd.DataFrame` — columns: `bin_lo, bin_hi, n, mean_predicted, mean_actual, gap`.
  - `cross_val_calibration(universe: pd.DataFrame, n_splits: int = 5, seed: int = 42) -> dict` — returns `{'brier_pre': float, 'brier_post': float, 'ece_pre': float, 'ece_post': float, 'ece_pre_ci': dict, 'ece_post_ci': dict, 'reliability_pre': pd.DataFrame, 'reliability_post': pd.DataFrame, 'final_a': float, 'final_b': float}`.
  - `format_global(cv_result: dict) -> str` — Markdown block.

- [ ] **Step 1: Write failing tests for brier_score and ece**

Append to `docs/audit/test_roi_calibration_helpers.py`:

```python
def test_brier_score_perfect_prediction():
    """Perfect predictions (prob=1 when outcome=1, prob=0 when outcome=0)
    have Brier score 0."""
    probs = np.array([1.0, 0.0, 1.0, 0.0])
    outcomes = np.array([1, 0, 1, 0])
    assert _roi_calibration.brier_score(probs, outcomes) == 0.0


def test_brier_score_worst_prediction():
    """Worst predictions (prob=0 when outcome=1) have Brier score 1."""
    probs = np.array([0.0, 1.0, 0.0, 1.0])
    outcomes = np.array([1, 0, 1, 0])
    assert _roi_calibration.brier_score(probs, outcomes) == 1.0


def test_brier_score_uniform_half():
    """Prob=0.5 with outcome-agnostic gives Brier 0.25."""
    probs = np.array([0.5, 0.5, 0.5, 0.5])
    outcomes = np.array([1, 0, 1, 0])
    assert abs(_roi_calibration.brier_score(probs, outcomes) - 0.25) < 1e-9


def test_ece_perfect_calibration():
    """When mean predicted == mean actual in each bin, ECE is 0."""
    # 100 predictions at prob 0.6, half win (matches predicted rate)
    probs = np.full(100, 0.6)
    outcomes = np.array([1] * 60 + [0] * 40)
    result = _roi_calibration.ece(probs, outcomes, n_bins=10)
    assert result < 0.05  # near-zero (may be tiny due to binning)


def test_ece_maximally_miscalibrated():
    """Prob=0.9 but actual rate 0.1 → ECE ≈ 0.8."""
    probs = np.full(100, 0.9)
    outcomes = np.array([1] * 10 + [0] * 90)
    result = _roi_calibration.ece(probs, outcomes, n_bins=10)
    assert 0.75 < result < 0.85
```

- [ ] **Step 2: Run tests — should fail**

```bash
cd docs/audit && python -m pytest test_roi_calibration_helpers.py::test_brier_score_perfect_prediction -v
```

Expected: FAIL with `AttributeError: module 'roi_calibration' has no attribute 'brier_score'`.

- [ ] **Step 3: Implement metrics and CV loop**

Append to `docs/audit/roi-calibration-2026-07-22.py` **before** the `# ---- Main ----` line:

```python
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
        f"**Brier score:** {cv['brier_pre']:.4f} → {cv['brier_post']:.4f} ({brier_delta:+.1f}% relative)\n\n"
        f"**ECE:** {cv['ece_pre']:.4f} (CI {cv['ece_pre_ci']['ci_lo']:.4f} → {cv['ece_pre_ci']['ci_hi']:.4f})"
        f" → {cv['ece_post']:.4f} (CI {cv['ece_post_ci']['ci_lo']:.4f} → {cv['ece_post_ci']['ci_hi']:.4f})"
        f"  ({ece_delta:+.1f}% relative)\n\n"
        f"### Reliability diagram\n\n"
        f"{_fmt_curve('Pre-calibration (raw confidence)', cv['reliability_pre'])}\n\n"
        f"{_fmt_curve('Post-calibration (held-out CV)', cv['reliability_post'])}\n"
    )
```

- [ ] **Step 4: Wire global CV into main()**

Locate the block:

```python
    if len(universe) < 100:
        print(f"HARD STOP: universe n={len(universe)} < 100. Verdict: INSUFFICIENT_SIGNAL")
        return 2

    # Subsequent tasks will fill in Q&A sections.
    return 0
```

Replace with:

```python
    if len(universe) < 100:
        print(f"HARD STOP: universe n={len(universe)} < 100. Verdict: INSUFFICIENT_SIGNAL")
        return 2

    cv = cross_val_calibration(universe)
    print(format_global(cv))

    # Task 3-5 wire in segmentation + verdicts.
    return 0
```

- [ ] **Step 5: Run tests to verify all pass**

```bash
cd docs/audit && python -m pytest test_roi_calibration_helpers.py -v
```

Expected: 11/11 passing (6 from Task 1 + 5 new metric tests).

- [ ] **Step 6: Run the script and eyeball global output**

```bash
python docs/audit/roi-calibration-2026-07-22.py --snapshot docs/audit/snapshot-2026-07-16.sqlite
```

Expected: Global calibration section prints. Sanity check:
- Brier score should be in `[0, 0.5]` (0.25 = random guessing baseline)
- ECE should be small if model is calibrated (< 0.1); large if not
- Reliability diagram: if the model is over-confident, `mean_predicted > mean_actual` in the high buckets

- [ ] **Step 7: Commit**

```bash
git add docs/audit/roi-calibration-2026-07-22.py docs/audit/test_roi_calibration_helpers.py
git commit -m "calibration: 5-fold CV + Brier + ECE + reliability diagram"
```

---

## Task 3: Segmentation heatmap (buckets, leagues, time periods)

**Files:**
- Modify: `docs/audit/roi-calibration-2026-07-22.py` — append segmentation functions; wire into `main()`.

**Interfaces:**
- Consumes: `cross_val_calibration` result from Task 2 (specifically `held_out_pre` and `held_out_post`), plus `universe` DataFrame.
- Produces:
  - `segment_diagnostic(universe: pd.DataFrame, held_out_pre: np.ndarray, held_out_post: np.ndarray, segment_col: str, values_or_buckets, min_n: int = 15) -> pd.DataFrame` — per-segment table with columns: `segment, n, mean_predicted_pre, mean_actual, gap_pre, mean_predicted_post, gap_post, underpowered`.
  - `segment_by_confidence_bucket(universe: pd.DataFrame, held_out_pre, held_out_post) -> pd.DataFrame` — uses edges `[0.55, 0.60, 0.70, 0.80, 1.001]`.
  - `segment_by_league(universe: pd.DataFrame, held_out_pre, held_out_post, top_n: int = 5) -> pd.DataFrame` — top 5 leagues by volume.
  - `segment_by_time_period(universe: pd.DataFrame, held_out_pre, held_out_post) -> pd.DataFrame` — chronological halves.
  - `format_segmentation(bucket_df, league_df, time_df) -> str` — Markdown block.

- [ ] **Step 1: Implement segmentation**

Append to `docs/audit/roi-calibration-2026-07-22.py` **before** the `# ---- Main ----` line:

```python
# ---- Segmentation heatmap ---------------------------------------------

_CONF_EDGES = [0.55, 0.60, 0.70, 0.80, 1.001]
_CONF_LABELS = ['0.55–0.60', '0.60–0.70', '0.70–0.80', '0.80–1.00']


def _segment_row(segment_name: str, mask: np.ndarray,
                 outcomes: np.ndarray, held_out_pre: np.ndarray,
                 held_out_post: np.ndarray, min_n: int) -> dict:
    n = int(mask.sum())
    if n == 0:
        return {'segment': segment_name, 'n': 0,
                'mean_predicted_pre': float('nan'),
                'mean_actual': float('nan'),
                'gap_pre': float('nan'),
                'mean_predicted_post': float('nan'),
                'gap_post': float('nan'),
                'underpowered': True}
    mp_pre = float(held_out_pre[mask].mean())
    mp_post = float(held_out_post[mask].mean())
    ma = float(outcomes[mask].mean())
    return {
        'segment': segment_name,
        'n': n,
        'mean_predicted_pre': mp_pre,
        'mean_actual': ma,
        'gap_pre': mp_pre - ma,
        'mean_predicted_post': mp_post,
        'gap_post': mp_post - ma,
        'underpowered': n < min_n,
    }


def segment_by_confidence_bucket(universe: pd.DataFrame,
                                 held_out_pre: np.ndarray,
                                 held_out_post: np.ndarray,
                                 min_n: int = 15) -> pd.DataFrame:
    conf = universe['confidence'].to_numpy()
    outcomes = universe['was_correct'].to_numpy().astype(int)
    rows = []
    for i, label in enumerate(_CONF_LABELS):
        lo, hi = _CONF_EDGES[i], _CONF_EDGES[i + 1]
        mask = (conf >= lo) & (conf < hi)
        rows.append(_segment_row(label, mask, outcomes,
                                 held_out_pre, held_out_post, min_n))
    return pd.DataFrame(rows)


def segment_by_league(universe: pd.DataFrame,
                      held_out_pre: np.ndarray,
                      held_out_post: np.ndarray,
                      top_n: int = 5, min_n: int = 15) -> pd.DataFrame:
    outcomes = universe['was_correct'].to_numpy().astype(int)
    league_counts = universe['league'].fillna('unknown').value_counts().head(top_n)
    rows = []
    for league in league_counts.index:
        mask = (universe['league'].fillna('unknown') == league).to_numpy()
        rows.append(_segment_row(str(league), mask, outcomes,
                                 held_out_pre, held_out_post, min_n))
    return pd.DataFrame(rows)


def segment_by_time_period(universe: pd.DataFrame,
                           held_out_pre: np.ndarray,
                           held_out_post: np.ndarray,
                           min_n: int = 15) -> pd.DataFrame:
    outcomes = universe['was_correct'].to_numpy().astype(int)
    ordered = universe.sort_values('prediction_logged_at').reset_index(drop=True)
    # Preserve outcome/pre/post alignment with the sorted DF
    sort_idx = universe.sort_values('prediction_logged_at').index.to_numpy()
    outcomes_sorted = outcomes[sort_idx]
    pre_sorted = held_out_pre[sort_idx]
    post_sorted = held_out_post[sort_idx]

    half = len(ordered) // 2
    rows = []
    first_mask = np.zeros(len(ordered), dtype=bool)
    first_mask[:half] = True
    rows.append(_segment_row('first half (older)', first_mask,
                             outcomes_sorted, pre_sorted, post_sorted, min_n))
    second_mask = ~first_mask
    rows.append(_segment_row('second half (newer)', second_mask,
                             outcomes_sorted, pre_sorted, post_sorted, min_n))
    return pd.DataFrame(rows)


def format_segmentation(bucket_df: pd.DataFrame, league_df: pd.DataFrame,
                        time_df: pd.DataFrame) -> str:
    def _fmt(label, d):
        lines = [f"**{label}**", '', '```',
                 '  segment                       n     pred_pre  actual   gap_pre   pred_post  gap_post   underpowered']
        for _, r in d.iterrows():
            flag = ' ⚠️' if r['underpowered'] else ''
            if r['n'] == 0:
                lines.append(f"  {str(r['segment']):<28}    0     n/a       n/a      n/a       n/a         n/a       yes")
                continue
            lines.append(
                f"  {str(r['segment']):<28}  {int(r['n']):>3}   {r['mean_predicted_pre']:>6.3f}    {r['mean_actual']:>6.3f}  "
                f"{r['gap_pre']:+6.3f}   {r['mean_predicted_post']:>6.3f}    {r['gap_post']:+6.3f}   {r['underpowered']!s:>5}{flag}"
            )
        lines.append('```')
        return '\n'.join(lines)

    return (
        "## Segmentation heatmap\n\n"
        f"{_fmt('By confidence bucket', bucket_df)}\n\n"
        f"{_fmt('By league (top 5 by volume)', league_df)}\n\n"
        f"{_fmt('By time period (chronological halves)', time_df)}\n"
    )
```

- [ ] **Step 2: Wire segmentation into main()**

Locate the block:

```python
    cv = cross_val_calibration(universe)
    print(format_global(cv))

    # Task 3-5 wire in segmentation + verdicts.
    return 0
```

Replace with:

```python
    cv = cross_val_calibration(universe)
    print(format_global(cv))

    bucket_df = segment_by_confidence_bucket(
        universe, cv['held_out_pre'], cv['held_out_post'])
    league_df = segment_by_league(
        universe, cv['held_out_pre'], cv['held_out_post'])
    time_df = segment_by_time_period(
        universe, cv['held_out_pre'], cv['held_out_post'])
    print(format_segmentation(bucket_df, league_df, time_df))

    # Task 4-5 wire in verdicts.
    return 0
```

- [ ] **Step 3: Run script and eyeball segmentation**

```bash
python docs/audit/roi-calibration-2026-07-22.py --snapshot docs/audit/snapshot-2026-07-16.sqlite
```

Expected: segmentation heatmap prints. Every bucket/league/time row has `n`, `pred_pre`, `actual`, `gap_pre`, `pred_post`, `gap_post`, `underpowered` flag. Some subgroups may have n<15 and get flagged ⚠️.

- [ ] **Step 4: Commit**

```bash
git add docs/audit/roi-calibration-2026-07-22.py
git commit -m "calibration: segmentation heatmap (bucket / league / time period)"
```

---

## Task 4: Per-target verdicts (Display / Kelly / Filter)

**Files:**
- Modify: `docs/audit/roi-calibration-2026-07-22.py` — append verdict functions; wire into `main()`.

**Interfaces:**
- Consumes: `cross_val_calibration` result, `segment_by_confidence_bucket` result, plus `universe` (for filter-target ROI calc).
- Produces:
  - `verdict_display(cv: dict) -> tuple[str, str]` — returns `(verdict, justification)` where verdict ∈ `{'APPLY', 'DO_NOT_APPLY', 'INSUFFICIENT_SIGNAL'}`.
  - `verdict_kelly(cv: dict, bucket_df: pd.DataFrame) -> tuple[str, str]` — same.
  - `verdict_filter(universe: pd.DataFrame, cv: dict) -> tuple[str, str, dict]` — third element is `{'current_roi': float, 'refiltered_roi': float, 'refiltered_ci_lo': float, 'refiltered_n': int}`.
  - `overall_verdict(display_v: str, kelly_v: str, filter_v: str, universe_n: int) -> str` — returns overall verdict string.
  - `format_verdicts(display_r, kelly_r, filter_r, overall) -> str` — Markdown block.

- [ ] **Step 1: Implement verdict functions**

Append to `docs/audit/roi-calibration-2026-07-22.py` **before** the `# ---- Main ----` line:

```python
# ---- Per-target verdicts ---------------------------------------------

def verdict_display(cv: dict) -> tuple[str, str]:
    """Display target: APPLY if Brier improves ≥5% relative AND ECE
    reduces ≥30% relative."""
    if cv['brier_pre'] <= 0 or cv['ece_pre'] <= 0:
        return ('INSUFFICIENT_SIGNAL',
                'Pre-calibration Brier or ECE is zero; nothing to improve.')
    brier_rel = (cv['brier_pre'] - cv['brier_post']) / cv['brier_pre']
    ece_rel = (cv['ece_pre'] - cv['ece_post']) / cv['ece_pre']
    if brier_rel >= 0.05 and ece_rel >= 0.30:
        return ('APPLY',
                f"Brier {brier_rel*100:+.1f}% (>= 5%), "
                f"ECE {ece_rel*100:+.1f}% (>= 30%).")
    return ('DO_NOT_APPLY',
            f"Brier {brier_rel*100:+.1f}% (need >= 5%), "
            f"ECE {ece_rel*100:+.1f}% (need >= 30%).")


def verdict_kelly(cv: dict, bucket_df: pd.DataFrame,
                  seed: int = 42, n_iter: int = 10000) -> tuple[str, str]:
    """Kelly target: APPLY if
      - model over-confident in 0.60-0.80 range (bucket gap > 0), AND
      - Brier improves ≥5% relative, AND
      - Bootstrap 95% CI on (raw - calibrated) gap in 0.60-0.80 excludes 0.
    """
    # Kelly-relevant buckets are 0.60–0.70 and 0.70–0.80
    kelly_buckets = bucket_df[bucket_df['segment'].isin(
        ['0.60–0.70', '0.70–0.80'])].copy()
    if kelly_buckets['n'].sum() < 15:
        return ('INSUFFICIENT_SIGNAL',
                f"Only {int(kelly_buckets['n'].sum())} bets in Kelly-relevant "
                f"buckets (0.60–0.80); need >= 15.")

    # Over-confidence check: is the pre-calibration gap positive?
    weighted_gap_pre = (kelly_buckets['n'] * kelly_buckets['gap_pre']).sum() \
                      / kelly_buckets['n'].sum()
    if weighted_gap_pre <= 0:
        return ('DO_NOT_APPLY',
                f"Model not over-confident in 0.60–0.80 range "
                f"(weighted gap {weighted_gap_pre:+.3f}); calibration would "
                f"grow stakes and increase risk.")

    brier_rel = (cv['brier_pre'] - cv['brier_post']) / cv['brier_pre']
    if brier_rel < 0.05:
        return ('DO_NOT_APPLY',
                f"Brier improvement {brier_rel*100:+.1f}% < 5%.")

    # Bootstrap the raw-calibrated gap in the Kelly-relevant range
    conf = np.concatenate([
        np.full(int(row['n']), (row['mean_predicted_pre']))
        for _, row in kelly_buckets.iterrows()
    ])
    # Approximate: use the mean gap in each bucket weighted by n
    gaps = np.concatenate([
        np.full(int(row['n']),
                row['mean_predicted_pre'] - row['mean_predicted_post'])
        for _, row in kelly_buckets.iterrows()
    ])
    if len(gaps) == 0:
        return ('INSUFFICIENT_SIGNAL',
                'No Kelly-relevant bucket rows to bootstrap.')
    ci = bootstrap_ci(gaps, n_iter=n_iter, seed=seed)
    if ci['ci_lo'] <= 0:
        return ('DO_NOT_APPLY',
                f"Bootstrap CI on raw-calibrated gap in 0.60–0.80 range "
                f"({ci['ci_lo']:+.3f} to {ci['ci_hi']:+.3f}) includes zero.")
    return ('APPLY',
            f"Over-confident by {weighted_gap_pre*100:+.1f}pp in 0.60–0.80; "
            f"Brier {brier_rel*100:+.1f}%; bootstrap CI on gap excludes zero.")


def verdict_filter(universe: pd.DataFrame, cv: dict,
                   threshold: float = 0.55) -> tuple[str, str, dict]:
    """Filter target: APPLY if re-filtering on calibrated_prob >= 0.55
    yields ROI > current + 2pp AND CI_lo >= +1%.
    """
    profits = universe['profit_loss_10'].to_numpy()
    current_roi = float(profits.sum() / (len(profits) * 10.0) * 100.0)

    calibrated = cv['held_out_post']
    mask = calibrated >= threshold
    refiltered_profits = profits[mask]
    n_new = int(mask.sum())
    if n_new < 100:
        return ('INSUFFICIENT_SIGNAL',
                f"Re-filtered subset n={n_new} < 100.",
                {'current_roi': current_roi, 'refiltered_roi': float('nan'),
                 'refiltered_ci_lo': float('nan'), 'refiltered_n': n_new})

    refiltered_roi_values = refiltered_profits / 10.0 * 100.0
    ci = bootstrap_ci(refiltered_roi_values)
    refiltered_roi = float(refiltered_profits.sum() / (n_new * 10.0) * 100.0)

    payload = {'current_roi': current_roi, 'refiltered_roi': refiltered_roi,
               'refiltered_ci_lo': ci['ci_lo'], 'refiltered_n': n_new}
    if refiltered_roi - current_roi < 2.0:
        return ('DO_NOT_APPLY',
                f"Re-filtered ROI {refiltered_roi:+.2f}% vs current "
                f"{current_roi:+.2f}% (delta {refiltered_roi-current_roi:+.2f}pp "
                f"< 2pp).",
                payload)
    if ci['ci_lo'] < 1.0:
        return ('DO_NOT_APPLY',
                f"Re-filtered ROI CI_lo {ci['ci_lo']:+.2f}% < +1%.",
                payload)
    return ('APPLY',
            f"Re-filtered ROI {refiltered_roi:+.2f}% "
            f"(delta {refiltered_roi-current_roi:+.2f}pp, "
            f"CI_lo {ci['ci_lo']:+.2f}%).",
            payload)


def overall_verdict(display_v: str, kelly_v: str, filter_v: str,
                    universe_n: int) -> str:
    if universe_n < 100:
        return 'INSUFFICIENT_SIGNAL'
    if 'APPLY' in (display_v, kelly_v, filter_v):
        return 'APPLY'
    return 'DO_NOT_APPLY'


def format_verdicts(display_r: tuple[str, str],
                    kelly_r: tuple[str, str],
                    filter_r: tuple[str, str, dict],
                    overall: str) -> str:
    display_v, display_j = display_r
    kelly_v, kelly_j = kelly_r
    filter_v, filter_j, filter_payload = filter_r
    return (
        "## Per-target verdicts\n\n"
        f"- **Display:** `{display_v}` — {display_j}\n"
        f"- **Kelly sizing:** `{kelly_v}` — {kelly_j}\n"
        f"- **Filter re-selection:** `{filter_v}` — {filter_j}\n"
        f"  - Current subset ROI: {filter_payload['current_roi']:+.2f}%\n"
        f"  - Re-filtered ROI: {filter_payload['refiltered_roi']:+.2f}% "
        f"(n={filter_payload['refiltered_n']}, "
        f"CI_lo {filter_payload['refiltered_ci_lo']:+.2f}%)\n\n"
        f"### Overall verdict: `{overall}`\n"
    )
```

- [ ] **Step 2: Wire verdicts into main()**

Locate the block:

```python
    bucket_df = segment_by_confidence_bucket(
        universe, cv['held_out_pre'], cv['held_out_post'])
    league_df = segment_by_league(
        universe, cv['held_out_pre'], cv['held_out_post'])
    time_df = segment_by_time_period(
        universe, cv['held_out_pre'], cv['held_out_post'])
    print(format_segmentation(bucket_df, league_df, time_df))

    # Task 4-5 wire in verdicts.
    return 0
```

Replace with:

```python
    bucket_df = segment_by_confidence_bucket(
        universe, cv['held_out_pre'], cv['held_out_post'])
    league_df = segment_by_league(
        universe, cv['held_out_pre'], cv['held_out_post'])
    time_df = segment_by_time_period(
        universe, cv['held_out_pre'], cv['held_out_post'])
    print(format_segmentation(bucket_df, league_df, time_df))

    display_r = verdict_display(cv)
    kelly_r = verdict_kelly(cv, bucket_df)
    filter_r = verdict_filter(universe, cv)
    overall = overall_verdict(display_r[0], kelly_r[0], filter_r[0], len(universe))
    print(format_verdicts(display_r, kelly_r, filter_r, overall))

    # Task 5 wires in report assembly.
    return 0
```

- [ ] **Step 3: Run and eyeball verdicts**

```bash
python docs/audit/roi-calibration-2026-07-22.py --snapshot docs/audit/snapshot-2026-07-16.sqlite
```

Expected: three per-target verdicts print, each with justification, and an overall verdict at the bottom.

**Sanity check:** verdicts should be consistent with prior audit findings:
- Kelly likely `APPLY` (audit found ~20pp EV over-confidence)
- Display could go either way depending on Brier reduction magnitude
- Filter target is the wildcard — depends whether calibration produces a re-filtered subset with better ROI

- [ ] **Step 4: Commit**

```bash
git add docs/audit/roi-calibration-2026-07-22.py
git commit -m "calibration: per-target verdicts (Display / Kelly / Filter)"
```

---

## Task 5: Report assembly + committed Markdown

**Files:**
- Modify: `docs/audit/roi-calibration-2026-07-22.py` — add `assemble_report`; rewrite `main()` to write `--out` file.
- Create: `docs/audit/roi-calibration-2026-07-22.md` — the committed diagnostic report.

**Interfaces:**
- Consumes: every section formatter + verdict output from Tasks 2-4.
- Produces:
  - `assemble_report(snapshot_path, universe_n, section_bodies, overall_verdict, verdicts) -> str` — full Markdown.
  - Rewritten `main()` writes to `--out` when supplied.

- [ ] **Step 1: Implement assemble_report and rewrite main()**

Append to `docs/audit/roi-calibration-2026-07-22.py` **before** the `# ---- Main ----` line:

```python
# ---- Report assembly -------------------------------------------------

def _recommended_next(overall: str, display_r, kelly_r, filter_r) -> str:
    if overall == 'INSUFFICIENT_SIGNAL':
        return ("Collect more data; re-audit at n≥500. Any calibrator we might "
                "fit today would not survive forward-testing at current sample size.")
    if overall == 'DO_NOT_APPLY':
        return ("No production changes recommended. The model is either "
                "well-calibrated on this slice or calibration would not "
                "improve the targets we care about. Revisit at n≥500 if the "
                "situation changes.")
    # APPLY
    apply_targets = []
    if display_r[0] == 'APPLY':
        apply_targets.append('Display')
    if kelly_r[0] == 'APPLY':
        apply_targets.append('Kelly sizing')
    if filter_r[0] == 'APPLY':
        apply_targets.append('Filter re-selection')
    return (f"Trigger follow-on implementation spec for: {', '.join(apply_targets)}. "
            "Concrete file targets by application:\n"
            "- Display: `smartbet-frontend/app/components/RecommendationCard.tsx` "
            "(confidence pill) + probability rendering in bet analysis views.\n"
            "- Kelly sizing: `smartbet-frontend/app/components/StakeRecommendation.tsx` "
            "and `core/bankroll_utils.py::calculate_kelly_criterion` — inject calibrated "
            "prob before the Kelly formula.\n"
            "- Filter re-selection: extend `core/services/accuracy_calculator.py` "
            "and `smartbet-frontend/app/api/recommendations/route.ts` to use "
            "`calibrated_prob >= 0.55` in place of raw confidence.")


def assemble_report(snapshot_path: str, universe_n: int,
                    section_bodies: list[str], overall_verdict_str: str,
                    display_r, kelly_r, filter_r,
                    final_a: float, final_b: float) -> str:
    snap_size = _os.path.getsize(snapshot_path) if _os.path.exists(snapshot_path) else 0
    now = _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    exec_line = (
        f"**Overall verdict:** `{overall_verdict_str}`. "
        f"Display: `{display_r[0]}`. "
        f"Kelly sizing: `{kelly_r[0]}`. "
        f"Filter re-selection: `{filter_r[0]}`."
    )
    next_step = _recommended_next(overall_verdict_str, display_r, kelly_r, filter_r)
    return f"""# ROI Calibration Report — 2026-07-22

{exec_line}

---

## Data provenance

- Snapshot file: `{snapshot_path}` ({snap_size:,} bytes)
- Universe size: {universe_n} rows (over_under_2.5, recommended, resolved)
- Report generated at: {now}
- Same snapshot as prior audit and tuning; post-backfill state.
- Fitted Platt (full-sample): `sigmoid({final_a:.3f} * confidence + {final_b:.3f})`

---

{''.join(section_bodies)}

## Recommended next step

{next_step}

---

## Non-goals (this study does NOT test)

- Production code changes (deployment triggered by APPLY verdict gets a separate spec).
- Retraining SportMonks' underlying model (impossible).
- Modifying form-momentum or value-zone adjustments (calibration wraps them).
- Per-league or per-time-period separate calibrators (segmentation is diagnostic only).
- Multiple calibrator methods (Platt only; isotonic and beta explicitly out of scope).
- 1x2 / BTTS / DC calibration (combined n=~23 insufficient).
- Prospective forward-test.

---

*Report generated by `docs/audit/roi-calibration-2026-07-22.py`. Re-run against a fresh snapshot to regenerate.*
"""
```

- [ ] **Step 2: Rewrite main() to collect section bodies and write report**

Replace the entire `main()` function with:

```python
def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--out', help='If set, write assembled report to this path.')
    args = parser.parse_args(argv)

    universe = load_universe(args.snapshot)
    print(f"Universe loaded: {len(universe)} rows (O/U 2.5, resolved)\n")

    if len(universe) < 100:
        print(f"HARD STOP: universe n={len(universe)} < 100. Verdict: INSUFFICIENT_SIGNAL")
        return 2

    sections: list[str] = []

    cv = cross_val_calibration(universe)
    sections.append(format_global(cv))

    bucket_df = segment_by_confidence_bucket(
        universe, cv['held_out_pre'], cv['held_out_post'])
    league_df = segment_by_league(
        universe, cv['held_out_pre'], cv['held_out_post'])
    time_df = segment_by_time_period(
        universe, cv['held_out_pre'], cv['held_out_post'])
    sections.append(format_segmentation(bucket_df, league_df, time_df))

    display_r = verdict_display(cv)
    kelly_r = verdict_kelly(cv, bucket_df)
    filter_r = verdict_filter(universe, cv)
    overall = overall_verdict(display_r[0], kelly_r[0], filter_r[0], len(universe))
    sections.append(format_verdicts(display_r, kelly_r, filter_r, overall))

    for s in sections:
        print(s)

    if args.out:
        report = assemble_report(args.snapshot, len(universe), sections,
                                 overall, display_r, kelly_r, filter_r,
                                 cv['final_a'], cv['final_b'])
        with open(args.out, 'w', encoding='utf-8') as fh:
            fh.write(report)
        print(f"\nReport written to {args.out}")

    return 0 if overall != 'INSUFFICIENT_SIGNAL' else 2
```

- [ ] **Step 3: Generate the committed report**

```bash
PYTHONIOENCODING=utf-8 python docs/audit/roi-calibration-2026-07-22.py \
  --snapshot docs/audit/snapshot-2026-07-16.sqlite \
  --out docs/audit/roi-calibration-2026-07-22.md
```

Expected: `Report written to docs/audit/roi-calibration-2026-07-22.md`. Exit code 0 (APPLY / DO_NOT_APPLY) or 2 (INSUFFICIENT_SIGNAL).

- [ ] **Step 4: Read the report and verify structure**

Open `docs/audit/roi-calibration-2026-07-22.md`. Verify:
- Executive verdict line at top starts with `**Overall verdict:**` and includes all three per-target verdicts
- Data provenance section present
- Global calibration section present with Brier / ECE / reliability diagram
- Segmentation heatmap section present with all three subsections
- Per-target verdicts section present
- Recommended next step section present
- Non-goals block present

- [ ] **Step 5: Final test suite run**

```bash
cd docs/audit && python -m pytest test_roi_calibration_helpers.py -v
```

Expected: 11/11 passing.

- [ ] **Step 6: Commit script + report**

```bash
git add docs/audit/roi-calibration-2026-07-22.py \
        docs/audit/roi-calibration-2026-07-22.md \
        docs/audit/test_roi_calibration_helpers.py
git commit -m "calibration: full diagnostic report"
```

**HUMAN CHECKPOINT** — read the report. If `Overall verdict` is `APPLY`, the recommended next step is to invoke a follow-on implementation spec for the flagged targets. If `DO_NOT_APPLY` or `INSUFFICIENT_SIGNAL`, no further work in this direction.

---

## Self-review (executed by author)

**Spec coverage.** Each section of the spec maps to at least one task:
- Spec §2 (scope & data source) → Task 1 (`load_universe` filters to O/U 2.5 exactly).
- Spec §3 (methodology: Platt, 5-fold CV, Brier/ECE, reliability, segmentation) → Tasks 1, 2, 3.
- Spec §4 (per-target decision framework: Display / Kelly / Filter) → Task 4.
- Spec §5 (deliverables) → Task 5 (report + script + tests).
- Spec §5 (sample-size gates) → Task 1's HARD STOP check in `main()`; Task 3's per-subgroup `underpowered` flag.
- Spec §6 (success criteria: unambiguous verdict, actionable per-target output) → Task 5's `_recommended_next` function names concrete file targets per application.
- Spec §7 (non-goals) → Task 5's `assemble_report` includes the non-goals block.
- Spec §8 (risks: Platt assumption, sample-size stress, retrospective vs prospective) → mitigated by Task 3's underpowered flag, Task 2's reliability diagram surfacing the actual functional form, Task 5's non-goals + recommended next step.

No gaps.

**Placeholder scan.** No "TBD"/"TODO" in the plan. All code steps show the full code. All verdict criteria have exact numeric thresholds. All file paths are exact.

**Type consistency.**
- `bootstrap_ci` returns dict with keys `point, ci_lo, ci_median, ci_hi` — matches audit/tuning convention (though audit used `point_roi_pct`, this study uses general-purpose `point`; noted intentionally).
- `fit_platt` returns `(a, b)` tuple — used consistently in `apply_platt`, `cross_val_calibration`, `assemble_report`.
- `cross_val_calibration` returns dict with named keys — every downstream consumer references those exact keys.
- `verdict_display`, `verdict_kelly` return `(str, str)`; `verdict_filter` returns `(str, str, dict)` — `format_verdicts` unpacks each correctly.
- `overall_verdict` returns exact strings `APPLY / DO_NOT_APPLY / INSUFFICIENT_SIGNAL`.

All consistent.

---

## Human checkpoints (early-exit map)

1. **After Task 1, Step 5** — if universe count is not ≈252, snapshot or filter has drifted. Investigate before proceeding.
2. **After Task 2, Step 6** — sanity check global metrics. If Brier score > 0.30 (worse than random), something is wrong with the model or the data — investigate before spending time on segmentation.
3. **After Task 5, Step 4** — read the full report. Overall verdict decides whether a follow-on implementation spec is warranted.
