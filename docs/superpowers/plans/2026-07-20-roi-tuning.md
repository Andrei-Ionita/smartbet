# ROI Tuning (Approach 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Execute the 5 tactical-quick-win experiments defined in `docs/superpowers/specs/2026-07-20-roi-tuning-design.md`, produce a committed tuning report with per-experiment SHIP/INVESTIGATE/DISCARD verdicts, and (conditionally) deploy production changes for any SHIP-verdict experiments.

**Architecture:** Single-file Python analysis script (`docs/audit/roi-tuning-2026-07-20.py`) that reads from the existing sqlite snapshot and runs all 5 experiments. Reuses statistical helpers copied from the audit script (`docs/audit/roi-audit-2026-07-16.py`). Analysis phase writes a Markdown report; deployment phase is gated by the report's verdicts and modifies backend/frontend filter code.

**Tech Stack:** Python 3.11+, pandas 2.x, numpy, sqlite3 (stdlib), pytest for the two testable helper functions.

## Global Constraints

Values copied verbatim from `2026-07-20-roi-tuning-design.md`. Every task inherits these.

- **Script path:** `docs/audit/roi-tuning-2026-07-20.py` (exact).
- **Report path:** `docs/audit/roi-tuning-2026-07-20.md` (exact).
- **Test file path:** `docs/audit/test_roi_tuning_helpers.py` (exact).
- **Snapshot source:** `docs/audit/snapshot-2026-07-16.sqlite` (already exists, post-backfill, 275 in universe).
- **Universe filter (exact):** `is_recommended=True AND actual_outcome IS NOT NULL AND match_status != 'archived' AND is_audit_excluded != True` — same as the audit.
- **Bootstrap iterations:** 10,000; seed 42 (matches audit convention).
- **Confidence bucket edges (E4):** `[0.55, 0.60, 0.70, 0.80, 1.001]` — same as audit `_CONF_EDGES`.
- **E1 threshold sweep:** 0.50 to 0.75 inclusive, step 0.01.
- **E2 shrinkage sweep:** 0.5 to 1.0 inclusive, step 0.05.
- **E3 per-league minimum for consideration:** n ≥ 15.
- **E4 grid:** 4 markets (`1x2`, `btts`, `over_under_2.5`, `double_chance`) × 4 confidence buckets.
- **E5 starting bankroll:** $1000. Kelly fraction: 0.25. Flat baseline: $10 stake.
- **Verdict thresholds (E1/E2/E3):** SHIP requires `CI_lo > +1%` AND `n ≥ 100`.
- **Verdict thresholds (E4 per-cell):** SHIP requires `CI_lo > +1%` AND `n ≥ 30`.
- **Verdict thresholds (E5):** SHIP requires Kelly final bankroll > Flat final bankroll by ≥5% AND max drawdown ≤ 50%.
- **Verdict values (exact strings):** `SHIP` / `INVESTIGATE` / `DISCARD`.

## File Structure

| File | Purpose | Committed? |
|---|---|---|
| `docs/audit/roi-tuning-2026-07-20.py` | Single-file analysis script. All 5 experiments + `assemble_report`. | ✓ |
| `docs/audit/roi-tuning-2026-07-20.md` | Human-readable tuning report with per-experiment verdicts + combined recommendation. Produced by Task 7. | ✓ |
| `docs/audit/test_roi_tuning_helpers.py` | Unit tests for pure helpers (bootstrap CI copy, Kelly formula). | ✓ |
| Deployment targets (conditional; see Tasks 8–12) | Backend filter, frontend filter, blacklist constant, market thresholds, stake-sizing default. | ✓ per-experiment |

---

## Task 1: Scaffold script + copy statistical helpers

**Files:**
- Create: `docs/audit/roi-tuning-2026-07-20.py`
- Create: `docs/audit/test_roi_tuning_helpers.py`

**Interfaces:**
- Consumes: `docs/audit/snapshot-2026-07-16.sqlite` (universe rows).
- Produces:
  - `load_universe(snapshot_path: str) -> pd.DataFrame` — returns the universe (275 rows), NOT filter-split.
  - `bootstrap_ci(profits: np.ndarray, n_iter: int = 10000, seed: int = 42) -> dict` — same keys as audit's `q2_bootstrap_ci`: `point_roi_pct, ci_lo, ci_median, ci_hi`.
  - Module-level `TRUE_STRINGS = {'True', 't', '1', 'true'}`.
  - CLI: `python roi-tuning-2026-07-20.py --snapshot <path> [--out <report.md>]`. When `--out` absent, prints all sections to stdout.

- [ ] **Step 1: Create the script scaffold**

Create `docs/audit/roi-tuning-2026-07-20.py`:

```python
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
```

- [ ] **Step 2: Create test file with the module-load sanity test**

Create `docs/audit/test_roi_tuning_helpers.py`:

```python
"""Tests for pure helper functions in roi-tuning-2026-07-20.py."""
import importlib.util
import pathlib

import numpy as np

_MODULE_PATH = pathlib.Path(__file__).parent / 'roi-tuning-2026-07-20.py'
_spec = importlib.util.spec_from_file_location('roi_tuning', _MODULE_PATH)
_roi_tuning = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_roi_tuning)


def test_module_loads():
    """Sanity check that the tuning script is importable with expected API."""
    assert hasattr(_roi_tuning, 'load_universe')
    assert hasattr(_roi_tuning, 'bootstrap_ci')
    assert hasattr(_roi_tuning, 'classify_verdict')


def test_bootstrap_ci_recovers_known_mean():
    """CI should contain the true mean for a known synthetic distribution."""
    rng = np.random.default_rng(0)
    profits = rng.normal(loc=1.0, scale=8.0, size=500)
    result = _roi_tuning.bootstrap_ci(profits, n_iter=2000, seed=42)
    assert result['ci_lo'] < 10.0 < result['ci_hi']


def test_classify_verdict_ship():
    assert _roi_tuning.classify_verdict(ci_lo=2.0, point=8.0, n=150) == 'SHIP'


def test_classify_verdict_investigate():
    assert _roi_tuning.classify_verdict(ci_lo=-2.0, point=5.0, n=150) == 'INVESTIGATE'


def test_classify_verdict_discard():
    assert _roi_tuning.classify_verdict(ci_lo=-2.0, point=0.5, n=150) == 'DISCARD'


def test_classify_verdict_ship_needs_sample():
    # Point + CI look great but n too low.
    assert _roi_tuning.classify_verdict(ci_lo=2.0, point=8.0, n=50) == 'INVESTIGATE'
```

- [ ] **Step 3: Run tests to verify scaffold**

```bash
cd docs/audit && python -m pytest test_roi_tuning_helpers.py -v
```

Expected: 6/6 passing.

- [ ] **Step 4: Run the script against the snapshot to confirm it loads the universe**

```bash
python docs/audit/roi-tuning-2026-07-20.py --snapshot docs/audit/snapshot-2026-07-16.sqlite
```

Expected: `Universe loaded: 275 rows` printed.

- [ ] **Step 5: Commit**

```bash
git add docs/audit/roi-tuning-2026-07-20.py docs/audit/test_roi_tuning_helpers.py
git commit -m "tuning(roi): script scaffold + shared helpers + verdict classifier"
```

---

## Task 2: E1 — Confidence threshold sweep

**Files:**
- Modify: `docs/audit/roi-tuning-2026-07-20.py` — append E1 functions, wire into `main()`.

**Interfaces:**
- Consumes: `load_universe`, `bootstrap_ci`, `classify_verdict` from Task 1.
- Produces:
  - `e1_threshold_sweep(universe: pd.DataFrame, thresholds: list[float]) -> pd.DataFrame` — columns: `threshold, n, roi_pct, ci_lo, ci_hi, verdict`.
  - `format_e1(sweep_df: pd.DataFrame) -> str` — Markdown block for the report.
  - `e1_recommendation(sweep_df: pd.DataFrame) -> dict` — returns `{'best_threshold': float, 'best_ci_lo': float, 'best_n': int, 'verdict': str}` for the highest-CI-lower-bound SHIP threshold, or the closest INVESTIGATE if none SHIP.

- [ ] **Step 1: Implement E1 functions**

Append to `docs/audit/roi-tuning-2026-07-20.py` **before** the `# ---- Main ----` line:

```python
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
    lines = ['## E1 — Confidence threshold sweep', '',
             '**Hypothesis:** current `≥ 0.60` filter is not optimal; the 0.55–0.60 bucket carries edge that is currently discarded.',
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
```

- [ ] **Step 2: Wire E1 into main()**

Replace the `# E1-E5 sections wired in by subsequent tasks.` line in `main()` with:

```python
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

    # E2-E5 wired in by subsequent tasks.
    return 0
```

- [ ] **Step 3: Run script and eyeball E1 output**

```bash
python docs/audit/roi-tuning-2026-07-20.py --snapshot docs/audit/snapshot-2026-07-16.sqlite
```

Expected: a 26-row table (thresholds 0.50 through 0.75). Every row has n, ROI, CI, verdict. The recommendation line at the bottom names the best threshold.

**Sanity check:** at threshold 0.60, `n` should be ≈ 210 and ROI ≈ −2% (matches the audit). At 0.55, `n` should be ≈ 267 and ROI should be different (higher if the 0.55–0.60 bucket carries the edge).

- [ ] **Step 4: Run tests**

```bash
cd docs/audit && python -m pytest test_roi_tuning_helpers.py -v
```

Expected: 6/6 still passing.

- [ ] **Step 5: Commit**

```bash
git add docs/audit/roi-tuning-2026-07-20.py
git commit -m "tuning(roi): E1 confidence threshold sweep"
```

---

## Task 3: E2 — EV shrinkage factor sweep

**Files:**
- Modify: `docs/audit/roi-tuning-2026-07-20.py` — append E2 functions, wire into `main()`.

**Interfaces:**
- Consumes: `load_universe`, `bootstrap_ci`, `classify_verdict`.
- Produces:
  - `e2_shrinkage_sweep(universe: pd.DataFrame, factors: list[float]) -> pd.DataFrame` — columns: `factor, n, roi_pct, ci_lo, ci_hi, verdict`. Applies `ev_shrunk = ev * factor` then filters `ev_shrunk >= 0.05`.
  - `format_e2(sweep_df: pd.DataFrame) -> str`.
  - `e2_recommendation(sweep_df: pd.DataFrame) -> dict` — same shape as E1.

- [ ] **Step 1: Implement E2**

Append to `docs/audit/roi-tuning-2026-07-20.py` before the `# ---- Main ----` line:

```python
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
    lines = ['## E2 — EV shrinkage factor sweep', '',
             "**Hypothesis:** model's EV is ~20 pp too optimistic; shrinkage factor before the `ev ≥ 0.05` filter keeps only genuinely-value picks.",
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
```

- [ ] **Step 2: Wire E2 into main()**

Replace the `# E2-E5 wired in by subsequent tasks.` line with:

```python
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
```

- [ ] **Step 3: Run script and eyeball E2 output**

```bash
python docs/audit/roi-tuning-2026-07-20.py --snapshot docs/audit/snapshot-2026-07-16.sqlite
```

Expected: 11-row shrinkage table (0.50 through 1.00 in steps of 0.05). At factor=1.00 (no shrinkage), results should approximate the audit's unfiltered numbers.

- [ ] **Step 4: Commit**

```bash
git add docs/audit/roi-tuning-2026-07-20.py
git commit -m "tuning(roi): E2 EV shrinkage factor sweep"
```

---

## Task 4: E3 — League blacklist/whitelist analysis

**Files:**
- Modify: `docs/audit/roi-tuning-2026-07-20.py` — append E3 functions, wire into `main()`.

**Interfaces:**
- Consumes: `load_universe`, `bootstrap_ci`, `classify_verdict`.
- Produces:
  - `e3_league_analysis(universe: pd.DataFrame, min_n: int = 15) -> pd.DataFrame` — per-league table with `league, n, roi_pct, ci_lo, ci_hi, category` where `category` ∈ `{'blacklist', 'whitelist', 'neutral'}`.
  - `e3_scenarios(universe: pd.DataFrame, per_league: pd.DataFrame) -> pd.DataFrame` — scenario table with 3 rows: `current`, `blacklist_applied`, `whitelist_only`.
  - `format_e3(per_league: pd.DataFrame, scenarios: pd.DataFrame) -> str`.
  - `e3_recommendation(scenarios: pd.DataFrame, per_league: pd.DataFrame) -> dict` — returns `{'blacklist_leagues': list[str], 'scenario_verdict': str, 'scenario_ci_lo': float, 'scenario_n': int}`.

- [ ] **Step 1: Implement E3**

Append to `docs/audit/roi-tuning-2026-07-20.py` before `# ---- Main ----`:

```python
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
    lines = ['## E3 — League blacklist/whitelist', '',
             '**Hypothesis:** a few leagues drag overall ROI down; removing them lifts total edge.',
             '',
             '**Per-league (n ≥ 15):**', '',
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
```

- [ ] **Step 2: Wire E3 into main()**

Replace `# E3-E5 wired in by subsequent tasks.` with:

```python
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
```

- [ ] **Step 3: Run script**

```bash
python docs/audit/roi-tuning-2026-07-20.py --snapshot docs/audit/snapshot-2026-07-16.sqlite
```

Expected: per-league table (rows for leagues with n ≥ 15) + 3-row scenario table. E3 recommendation names any blacklist candidates.

- [ ] **Step 4: Commit**

```bash
git add docs/audit/roi-tuning-2026-07-20.py
git commit -m "tuning(roi): E3 league blacklist/whitelist analysis"
```

---

## Task 5: E4 — Market × confidence 2D grid

**Files:**
- Modify: `docs/audit/roi-tuning-2026-07-20.py` — append E4 functions, wire into `main()`.

**Interfaces:**
- Consumes: `load_universe`, `bootstrap_ci`, `classify_verdict`.
- Produces:
  - `e4_market_conf_grid(universe: pd.DataFrame) -> pd.DataFrame` — long-format table: `market, bucket, n, roi_pct, ci_lo, ci_hi, verdict` (16 rows: 4 × 4).
  - `format_e4(grid_df: pd.DataFrame) -> str`.
  - `e4_recommendation(grid_df: pd.DataFrame) -> dict` — returns `{'ship_cells': list[dict], 'proposed_market_thresholds': dict[str, float]}` — for each market that has a SHIP-verdict cell, the recommended minimum confidence threshold.

- [ ] **Step 1: Implement E4**

Append to `docs/audit/roi-tuning-2026-07-20.py` before `# ---- Main ----`:

```python
# ---- E4: Market × confidence grid -------------------------------------

_MARKETS = ['1x2', 'btts', 'over_under_2.5', 'double_chance']
_CONF_EDGES = [0.55, 0.60, 0.70, 0.80, 1.001]
_CONF_LABELS = ['0.55–0.60', '0.60–0.70', '0.70–0.80', '0.80–1.00']


def e4_market_conf_grid(universe: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for market in _MARKETS:
        mkt_df = universe[universe['market_type'] == market]
        for i, label in enumerate(_CONF_LABELS):
            lo, hi = _CONF_EDGES[i], _CONF_EDGES[i + 1]
            cell = mkt_df[(mkt_df['confidence'] >= lo) & (mkt_df['confidence'] < hi)]
            n = len(cell)
            if n == 0:
                rows.append({'market': market, 'bucket': label, 'n': 0,
                             'roi_pct': float('nan'), 'ci_lo': float('nan'),
                             'ci_hi': float('nan'), 'verdict': 'DISCARD'})
                continue
            ci = bootstrap_ci(cell['profit_loss_10'].to_numpy())
            # E4 uses looser n threshold (30) per spec
            v = classify_verdict(ci['ci_lo'], ci['point_roi_pct'], n, ship_n_min=30)
            rows.append({
                'market': market,
                'bucket': label,
                'n': n,
                'roi_pct': ci['point_roi_pct'],
                'ci_lo': ci['ci_lo'],
                'ci_hi': ci['ci_hi'],
                'verdict': v,
            })
    return pd.DataFrame(rows)


def format_e4(grid_df: pd.DataFrame) -> str:
    lines = ['## E4 — Market × confidence 2D grid', '',
             '**Hypothesis:** edge lives in specific market-confidence combinations, not uniformly.',
             '',
             '```',
             '  market            bucket        n     ROI       CI_lo    CI_hi    verdict']
    for _, r in grid_df.iterrows():
        if r['n'] == 0:
            lines.append(f"  {str(r['market']):<16}  {str(r['bucket']):<10}    0     n/a       n/a      n/a      DISCARD")
            continue
        lines.append(
            f"  {str(r['market']):<16}  {str(r['bucket']):<10}  {int(r['n']):>3}  "
            f"{r['roi_pct']:+6.2f}%  {r['ci_lo']:+6.2f}%  {r['ci_hi']:+6.2f}%  {r['verdict']}"
        )
    lines.append('```')
    lines.append('')
    return '\n'.join(lines) + '\n'


def e4_recommendation(grid_df: pd.DataFrame) -> dict:
    ships = grid_df[grid_df['verdict'] == 'SHIP']
    ship_cells = ships.to_dict('records')
    proposed_thresholds: dict[str, float] = {}
    for market, g in ships.groupby('market'):
        # Lowest bucket's lower edge (e.g., '0.55–0.60' -> 0.55)
        lowest = g['bucket'].apply(lambda b: float(b.split('–')[0])).min()
        proposed_thresholds[str(market)] = float(lowest)
    return {'ship_cells': ship_cells, 'proposed_market_thresholds': proposed_thresholds}
```

- [ ] **Step 2: Wire E4 into main()**

Replace `# E4-E5 wired in by subsequent tasks.` with:

```python
    e4_df = e4_market_conf_grid(universe)
    print(format_e4(e4_df))
    e4_reco = e4_recommendation(e4_df)
    print(f"### E4 recommendation: {len(e4_reco['ship_cells'])} SHIP cell(s)")
    if e4_reco['ship_cells']:
        for cell in e4_reco['ship_cells']:
            print(f"  SHIP: {cell['market']} / {cell['bucket']} — "
                  f"ROI={cell['roi_pct']:+.2f}% CI_lo={cell['ci_lo']:+.2f}% n={cell['n']}")
        print(f"  proposed market thresholds: {e4_reco['proposed_market_thresholds']}")
    print()

    # E5 wired in by subsequent task.
    return 0
```

- [ ] **Step 3: Run script**

```bash
python docs/audit/roi-tuning-2026-07-20.py --snapshot docs/audit/snapshot-2026-07-16.sqlite
```

Expected: 16-row grid. `over_under_2.5 / 0.60–0.70` should have the largest `n`. Empty cells (0.80–1.00 across all markets) get DISCARD.

- [ ] **Step 4: Commit**

```bash
git add docs/audit/roi-tuning-2026-07-20.py
git commit -m "tuning(roi): E4 market × confidence 2D grid"
```

---

## Task 6: E5 — Kelly stake sizing simulation

**Files:**
- Modify: `docs/audit/roi-tuning-2026-07-20.py` — append E5 functions, wire into `main()`.
- Modify: `docs/audit/test_roi_tuning_helpers.py` — add Kelly formula unit tests.

**Interfaces:**
- Consumes: `load_universe`.
- Produces:
  - `kelly_stake(bankroll: float, prob: float, odds: float, k_fraction: float = 0.25) -> float` — pure helper; returns 0 if edge non-positive.
  - `e5_simulate(universe: pd.DataFrame, starting_bankroll: float = 1000.0, k_fraction: float = 0.25) -> dict` — returns `{'flat_final': float, 'flat_max_dd_pct': float, 'kelly_final': float, 'kelly_max_dd_pct': float, 'n_bets': int, 'verdict': str}`.
  - `format_e5(sim: dict) -> str`.

- [ ] **Step 1: Write failing tests for kelly_stake**

Append to `docs/audit/test_roi_tuning_helpers.py`:

```python
def test_kelly_stake_positive_edge():
    """Kelly formula: prob=0.6, odds=2.0 => edge = 0.6*2 - 1 = 0.2. Kelly f = 0.2/1 = 0.2.
    Quarter Kelly on $1000 bankroll => stake = 1000 * 0.25 * 0.2 = 50."""
    stake = _roi_tuning.kelly_stake(bankroll=1000.0, prob=0.6, odds=2.0, k_fraction=0.25)
    assert abs(stake - 50.0) < 0.01


def test_kelly_stake_zero_when_no_edge():
    """prob * odds - 1 <= 0 => stake=0 (no bet)."""
    stake = _roi_tuning.kelly_stake(bankroll=1000.0, prob=0.5, odds=2.0, k_fraction=0.25)
    assert stake == 0.0


def test_kelly_stake_zero_when_negative_edge():
    stake = _roi_tuning.kelly_stake(bankroll=1000.0, prob=0.4, odds=2.0, k_fraction=0.25)
    assert stake == 0.0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd docs/audit && python -m pytest test_roi_tuning_helpers.py::test_kelly_stake_positive_edge -v
```

Expected: FAIL — `AttributeError: module 'roi_tuning' has no attribute 'kelly_stake'`.

- [ ] **Step 3: Implement E5**

Append to `docs/audit/roi-tuning-2026-07-20.py` before `# ---- Main ----`:

```python
# ---- E5: Kelly sizing simulation --------------------------------------

def kelly_stake(bankroll: float, prob: float, odds: float, k_fraction: float = 0.25) -> float:
    """Fractional Kelly stake in dollars.

    Kelly: f* = (p*(o-1) - (1-p)) / (o-1) = (p*o - 1) / (o-1)
    Returns 0 if edge is non-positive (never place a losing bet).
    """
    if odds <= 1.0 or prob <= 0 or prob >= 1:
        return 0.0
    edge = prob * odds - 1.0
    if edge <= 0:
        return 0.0
    f_star = edge / (odds - 1.0)
    return bankroll * k_fraction * f_star


def e5_simulate(universe: pd.DataFrame, starting_bankroll: float = 1000.0,
                k_fraction: float = 0.25) -> dict:
    """Simulate flat and Kelly stake strategies chronologically through resolved bets."""
    ordered = universe.sort_values('prediction_logged_at').copy()
    # Rows must have valid odds AND probability estimate (confidence).
    playable = ordered[ordered['odds'].notna() & (ordered['odds'] > 1.0)
                       & ordered['confidence'].notna()]

    # Flat baseline: $10 stake, win => +profit_loss_10, loss => -10
    flat_bankroll = starting_bankroll
    flat_peak = flat_bankroll
    flat_max_dd = 0.0
    for _, r in playable.iterrows():
        flat_bankroll += float(r['profit_loss_10'])
        flat_peak = max(flat_peak, flat_bankroll)
        dd = (flat_peak - flat_bankroll) / flat_peak * 100.0
        flat_max_dd = max(flat_max_dd, dd)

    # Kelly: stake sized per row from current bankroll; P/L scales by stake/10
    # because profit_loss_10 assumes $10 stake.
    kelly_bankroll = starting_bankroll
    kelly_peak = kelly_bankroll
    kelly_max_dd = 0.0
    for _, r in playable.iterrows():
        stake = kelly_stake(kelly_bankroll, float(r['confidence']), float(r['odds']), k_fraction)
        if stake > 0:
            # profit_loss_10 already computed for $10 stake; scale
            pl_scaled = float(r['profit_loss_10']) * (stake / 10.0)
            kelly_bankroll += pl_scaled
        kelly_peak = max(kelly_peak, kelly_bankroll)
        dd = (kelly_peak - kelly_bankroll) / kelly_peak * 100.0
        kelly_max_dd = max(kelly_max_dd, dd)

    # Verdict
    improvement_pct = (kelly_bankroll - flat_bankroll) / flat_bankroll * 100.0
    if improvement_pct >= 5.0 and kelly_max_dd <= 50.0:
        verdict = 'SHIP'
    elif improvement_pct >= 5.0:
        verdict = 'INVESTIGATE'  # Improvement but too much drawdown
    else:
        verdict = 'DISCARD'

    return {
        'starting_bankroll': starting_bankroll,
        'flat_final': flat_bankroll,
        'flat_max_dd_pct': flat_max_dd,
        'kelly_final': kelly_bankroll,
        'kelly_max_dd_pct': kelly_max_dd,
        'n_bets': len(playable),
        'improvement_pct': improvement_pct,
        'verdict': verdict,
    }


def format_e5(sim: dict) -> str:
    lines = ['## E5 — Kelly stake sizing simulation', '',
             '**Hypothesis:** flat $10 stakes leave value on the table; Kelly-optimal fractional stakes capture more.',
             '',
             f"- Starting bankroll: ${sim['starting_bankroll']:.2f}",
             f"- Bets simulated: {sim['n_bets']}",
             f"- **Flat $10:** final ${sim['flat_final']:.2f}, max drawdown {sim['flat_max_dd_pct']:.1f}%",
             f"- **Kelly (k=0.25):** final ${sim['kelly_final']:.2f}, max drawdown {sim['kelly_max_dd_pct']:.1f}%",
             f"- Kelly vs Flat improvement: {sim['improvement_pct']:+.2f}%",
             '',
             f"### E5 recommendation: {sim['verdict']}",
             '']
    return '\n'.join(lines) + '\n'
```

- [ ] **Step 4: Wire E5 into main()**

Replace `# E5 wired in by subsequent task.` with:

```python
    e5_sim = e5_simulate(universe)
    print(format_e5(e5_sim))

    return 0
```

- [ ] **Step 5: Run tests**

```bash
cd docs/audit && python -m pytest test_roi_tuning_helpers.py -v
```

Expected: 9/9 passing (6 from Task 1 + 3 new Kelly tests).

- [ ] **Step 6: Run script**

```bash
python docs/audit/roi-tuning-2026-07-20.py --snapshot docs/audit/snapshot-2026-07-16.sqlite
```

Expected: E5 block prints flat and Kelly final bankrolls with drawdown %.

- [ ] **Step 7: Commit**

```bash
git add docs/audit/roi-tuning-2026-07-20.py docs/audit/test_roi_tuning_helpers.py
git commit -m "tuning(roi): E5 Kelly stake sizing simulation"
```

---

## Task 7: Assemble the tuning report + committed Markdown

**Files:**
- Modify: `docs/audit/roi-tuning-2026-07-20.py` — add `assemble_report` and `combined_recommendation`; rewrite `main()` to write report when `--out` set.
- Create: `docs/audit/roi-tuning-2026-07-20.md` — the committed report.

**Interfaces:**
- Consumes: every `e{N}_recommendation` and section formatter.
- Produces:
  - `combined_recommendation(e1, e2, e3, e4, e5) -> dict` — returns `{'ship_experiments': list[str], 'production_changes': list[str], 'executive_verdict': str}`.
  - `assemble_report(...) -> str` — full Markdown.
  - `main()` writes to `--out` path when supplied.

- [ ] **Step 1: Implement combined_recommendation + assemble_report**

Append to `docs/audit/roi-tuning-2026-07-20.py` before `# ---- Main ----`:

```python
# ---- Combined recommendation + report assembly ------------------------

def combined_recommendation(e1: dict, e2: dict, e3: dict, e4: dict, e5: dict) -> dict:
    """Pick concrete production changes based on which experiments SHIPed.

    E1 (global threshold) and E4 (per-market threshold) are alternatives —
    prefer E4 when it SHIPs since it's more granular.
    """
    ships: list[str] = []
    changes: list[str] = []

    if e1['verdict'] == 'SHIP':
        ships.append('E1')
    if e2['verdict'] == 'SHIP':
        ships.append('E2')
    if e3['scenario_verdict'] == 'SHIP':
        ships.append('E3')
    if e4['ship_cells']:
        ships.append('E4')
    if e5['verdict'] == 'SHIP':
        ships.append('E5')

    # E1 vs E4: prefer E4 (per-market thresholds override global threshold change)
    if 'E4' in ships and 'E1' in ships:
        changes.append(f"E4 (chosen over E1 — per-market thresholds are more granular): "
                       f"set per-market confidence thresholds {e4['proposed_market_thresholds']}")
    elif 'E1' in ships:
        changes.append(f"E1: lower global confidence threshold from 0.60 to {e1['best_threshold']:.2f}")
    elif 'E4' in ships:
        changes.append(f"E4: set per-market confidence thresholds {e4['proposed_market_thresholds']}")

    if 'E2' in ships:
        changes.append(f"E2: apply EV shrinkage factor {e2['best_factor']:.2f} before the ev>=0.05 filter")

    if 'E3' in ships:
        changes.append(f"E3: add to Phase 2a blacklist: {e3['blacklist_leagues']}")

    if 'E5' in ships:
        changes.append("E5: change default stake sizing strategy to Kelly (k=0.25)")

    if not ships:
        exec_verdict = ("NO SHIP — Approach 1 cannot lift the current pipeline to defensible positive "
                        "ROI. Escalate to Approach 2 (Deep Model Rebuild) or Approach 3 (Niche Specialization).")
    else:
        exec_verdict = (f"SHIP — {len(ships)} experiment(s) reached the ship bar: {ships}. "
                        f"Proposed production changes: {len(changes)} item(s) below.")

    return {'ship_experiments': ships, 'production_changes': changes,
            'executive_verdict': exec_verdict}


def assemble_report(snapshot_path: str, universe_n: int,
                    section_bodies: list[str], combined: dict) -> str:
    now = _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    snap_size = _os.path.getsize(snapshot_path) if _os.path.exists(snapshot_path) else 0
    changes_md = '\n'.join(f'- {c}' for c in combined['production_changes']) \
                 if combined['production_changes'] else '- (none — no experiment reached the SHIP bar)'
    return f"""# ROI Tuning Report — 2026-07-20

**Executive verdict:** {combined['executive_verdict']}

---

## Data provenance

- Snapshot file: `{snapshot_path}` ({snap_size:,} bytes)
- Universe size: {universe_n} rows
- Report generated at: {now}
- Same snapshot as `docs/audit/roi-audit-2026-07-16.md`, post-backfill.

---

{''.join(section_bodies)}

## Combined recommendation

**SHIP experiments:** {combined['ship_experiments'] if combined['ship_experiments'] else 'none'}

**Proposed production changes:**

{changes_md}

---

## Non-goals (this tuning does NOT test)

- Feature engineering (xG, lineups, injuries, referee, weather)
- New model IP (own trained model, ensemble with SportMonks)
- Reprocessing historical SportMonks responses
- New markets or leagues
- User-facing UI redesign
- Prospective forward-test (Phase 2 territory)

---

*Report generated by `docs/audit/roi-tuning-2026-07-20.py`. Re-run against a fresh snapshot to regenerate.*
"""
```

- [ ] **Step 2: Rewrite main() to collect all sections and optionally write report**

Replace the entire `main()` function with:

```python
def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--out', help='If set, write assembled report to this path.')
    args = parser.parse_args(argv)

    universe = load_universe(args.snapshot)
    print(f"Universe loaded: {len(universe)} rows\n")

    sections: list[str] = []

    # E1
    thresholds = [round(0.50 + i * 0.01, 2) for i in range(int((0.75 - 0.50) / 0.01) + 1)]
    e1_df = e1_threshold_sweep(universe, thresholds)
    sections.append(format_e1(e1_df))
    e1_reco = e1_recommendation(e1_df)

    # E2
    factors = [round(0.5 + i * 0.05, 2) for i in range(int((1.0 - 0.5) / 0.05) + 1)]
    e2_df = e2_shrinkage_sweep(universe, factors)
    sections.append(format_e2(e2_df))
    e2_reco = e2_recommendation(e2_df)

    # E3
    e3_per_league = e3_league_analysis(universe)
    e3_scen = e3_scenarios(universe, e3_per_league)
    sections.append(format_e3(e3_per_league, e3_scen))
    e3_reco = e3_recommendation(e3_scen, e3_per_league)

    # E4
    e4_df = e4_market_conf_grid(universe)
    sections.append(format_e4(e4_df))
    e4_reco = e4_recommendation(e4_df)

    # E5
    e5_sim = e5_simulate(universe)
    sections.append(format_e5(e5_sim))

    combined = combined_recommendation(e1_reco, e2_reco, e3_reco, e4_reco, e5_sim)

    # Print everything for immediate consumption
    for s in sections:
        print(s)
    print(f"## Combined recommendation")
    print(f"  Ship experiments: {combined['ship_experiments']}")
    for c in combined['production_changes']:
        print(f"  - {c}")

    if args.out:
        report = assemble_report(args.snapshot, len(universe), sections, combined)
        with open(args.out, 'w', encoding='utf-8') as fh:
            fh.write(report)
        print(f"\nReport written to {args.out}")

    return 0 if combined['ship_experiments'] else 1
```

- [ ] **Step 3: Generate the committed report**

```bash
PYTHONIOENCODING=utf-8 python docs/audit/roi-tuning-2026-07-20.py \
  --snapshot docs/audit/snapshot-2026-07-16.sqlite \
  --out docs/audit/roi-tuning-2026-07-20.md
```

Expected: `Report written to docs/audit/roi-tuning-2026-07-20.md`. Exit code 0 (any SHIP) or 1 (no SHIP).

- [ ] **Step 4: Read the report and confirm structure**

Open `docs/audit/roi-tuning-2026-07-20.md`. Verify: executive verdict line, data provenance, E1–E5 sections all present, combined recommendation at the end.

- [ ] **Step 5: Final test suite run**

```bash
cd docs/audit && python -m pytest test_roi_tuning_helpers.py -v
```

Expected: 9/9 passing.

- [ ] **Step 6: Commit script + report**

```bash
git add docs/audit/roi-tuning-2026-07-20.py \
        docs/audit/roi-tuning-2026-07-20.md \
        docs/audit/test_roi_tuning_helpers.py
git commit -m "tuning(roi): full report — verdict $(head -3 docs/audit/roi-tuning-2026-07-20.md | grep -oE 'SHIP|NO SHIP' | head -1)"
```

**HUMAN CHECKPOINT** — read the report. Decide which of Tasks 8–12 (if any) to execute based on the SHIP list.

---

## Deployment Phase (Conditional)

**Precondition for the entire section:** Task 7's report contains an `Executive verdict` starting with `SHIP`. If it starts with `NO SHIP`, skip Tasks 8–12 entirely; the outcome is "Approach 1 didn't find edge — escalate to Approach 2 or 3."

Each task below is gated by a specific SHIP verdict from the report. Execute only the tasks whose gate is satisfied.

---

## Task 8: Deploy E1 (global confidence threshold) — CONDITIONAL

**GATE:** Task 7's report lists `E1` in `SHIP experiments` AND `E4` is NOT in SHIP experiments (E4 preferred when both ship — see combined_recommendation logic).

**Files:**
- Modify: `core/services/accuracy_calculator.py` (single-line change at the filter — search for `confidence__gte=0.60`).
- Modify: `smartbet-frontend/app/api/recommendations/route.ts` (find the O/U 2.5 branch's `gap >= 0.12 && ev >= 0.05` filter, near line 529).

- [ ] **Step 1: Read Task 7's report to extract E1 best threshold**

```bash
grep "E1 recommendation" -A 2 docs/audit/roi-tuning-2026-07-20.md
```

Note the recommended threshold value (e.g., `0.55`). Call it `T`.

- [ ] **Step 2: Update backend AccuracyCalculator filter**

Read `core/services/accuracy_calculator.py` around line 149. Find `confidence__gte=0.60`. Replace with `confidence__gte=T` where T is the recommended value.

- [ ] **Step 3: Update frontend confidence filter for O/U 2.5**

Read `smartbet-frontend/app/api/recommendations/route.ts` around line 529. Find the O/U 2.5 branch's filter `if (outcome === 'over' && gap >= 0.12 && ev >= 0.05)`. Leave `gap` unchanged; the change is elsewhere. Actually, the threshold that limits which picks are surfaced by confidence lives in `maxProb` used for the market's probability — verify the recommendation includes only picks where the underlying probability meets threshold T. If not directly available, add a `maxProb >= T` clause.

- [ ] **Step 4: Redeploy backend and frontend**

```bash
git add core/services/accuracy_calculator.py smartbet-frontend/app/api/recommendations/route.ts
git commit -m "deploy(tuning): E1 — lower confidence threshold to T"
git push origin master
```

Railway auto-deploys backend and frontend on push.

- [ ] **Step 5: Verify live ROI moved**

Wait ~3 minutes for deploy. Then:

```bash
curl -sk https://api.betglitch.com/api/transparency/dashboard/ | python -c "import json,sys; d=json.load(sys.stdin); r=d['stats']['roi_simulation']; print(f'roi={r[\"roi_percent\"]}%, n={r[\"total_bets\"]}')"
```

Expected: ROI number moves toward the value predicted by E1's `best_point`. Sample count grows (more picks pass the lower threshold).

---

## Task 9: Deploy E2 (EV shrinkage) — CONDITIONAL

**GATE:** Task 7's report lists `E2` in `SHIP experiments`.

**Files:**
- Modify: `smartbet-frontend/app/api/recommendations/route.ts` — apply shrinkage before every `ev >= 0.05` filter check (three locations: 1x2 at line 405-407, O/U 2.5 at line 529-531, and analogous for BTTS/DC).

- [ ] **Step 1: Read Task 7's report to extract E2 best factor**

```bash
grep "E2 recommendation" -A 2 docs/audit/roi-tuning-2026-07-20.md
```

Note the recommended factor K (e.g., `0.80`).

- [ ] **Step 2: Update every `ev >= 0.05` filter to `(ev * K) >= 0.05`**

Read `smartbet-frontend/app/api/recommendations/route.ts`. Search for `ev >= 0.05`. In every filter clause where this appears, change to `(ev * ${K}) >= 0.05` (substitute the numeric K value).

- [ ] **Step 3: Add a comment above the constant**

At the top of the same file (near the imports), add:

```typescript
// EV shrinkage factor from tuning report roi-tuning-2026-07-20.md (audit action item #4).
// Model EV is systematically over-optimistic; shrinkage before the filter selects only
// picks with genuine value. Re-tune when the sample doubles.
const EV_SHRINKAGE = K;  // substitute numeric value
```

Then reference `EV_SHRINKAGE` in the filter clauses.

- [ ] **Step 4: Commit + push**

```bash
git add smartbet-frontend/app/api/recommendations/route.ts
git commit -m "deploy(tuning): E2 — apply EV shrinkage factor K before filter"
git push origin master
```

- [ ] **Step 5: Verify**

Same live-ROI curl as Task 8 Step 5. New picks over the next 24-48 hours should show the effect (older picks are unaffected because they're already logged).

---

## Task 10: Deploy E3 (league blacklist) — CONDITIONAL

**GATE:** Task 7's report lists `E3` in `SHIP experiments`.

**Files:**
- Modify: `core/api_views.py` — extend `PHASE_2A_BLACKLISTED_LEAGUES` constant (search for the exact identifier).

- [ ] **Step 1: Read Task 7's report to extract E3 blacklist**

```bash
grep "E3 recommendation" -A 2 docs/audit/roi-tuning-2026-07-20.md
```

Note the recommended list of leagues to blacklist.

- [ ] **Step 2: Read the current blacklist constant**

```bash
grep -n "PHASE_2A_BLACKLISTED_LEAGUES" core/api_views.py | head
```

Note the current constant contents.

- [ ] **Step 3: Append the new blacklist entries**

Edit `core/api_views.py` to append the E3-recommended leagues to `PHASE_2A_BLACKLISTED_LEAGUES`. Preserve existing entries.

- [ ] **Step 4: Commit + push**

```bash
git add core/api_views.py
git commit -m "deploy(tuning): E3 — add loser leagues to Phase 2a blacklist"
git push origin master
```

- [ ] **Step 5: Verify**

After deploy, the next log-recommendations cycle should exclude the new blacklist entries. Check live ROI in 24 hours.

---

## Task 11: Deploy E4 (market-specific thresholds) — CONDITIONAL

**GATE:** Task 7's report lists `E4` in `SHIP experiments`.

**Files:**
- Modify: `core/services/accuracy_calculator.py` — replace the single confidence filter with a per-market conditional.
- Modify: `smartbet-frontend/app/api/recommendations/route.ts` — apply per-market thresholds in the market-specific branches.

- [ ] **Step 1: Read Task 7's report to extract E4 per-market thresholds**

```bash
grep "proposed market thresholds" docs/audit/roi-tuning-2026-07-20.md
```

Note the dict, e.g., `{'over_under_2.5': 0.55, '1x2': 0.70}`.

- [ ] **Step 2: Update backend AccuracyCalculator to filter per-market**

Read `core/services/accuracy_calculator.py`. Replace the single `confidence__gte=0.60` filter with a per-market conditional using Django's `Q` objects:

```python
from django.db.models import Q
# ... inside get_roi_simulation:
per_market_filter = Q()
for market, thresh in E4_MARKET_THRESHOLDS.items():
    per_market_filter |= Q(market_type=market, confidence__gte=thresh)
predictions = PredictionLog.objects.filter(
    is_recommended=True,
    actual_outcome__isnull=False,
).filter(per_market_filter)
```

Define `E4_MARKET_THRESHOLDS` at module top with the dict from the report.

- [ ] **Step 3: Update frontend per-market filters**

Each market branch in `route.ts` (1x2, BTTS, O/U 2.5, DC) has its own filter. Update each branch to enforce its market's threshold: e.g., in the O/U 2.5 branch, add `maxProb >= 0.55` alongside the existing gap/ev checks.

- [ ] **Step 4: Commit + push + verify**

```bash
git add core/services/accuracy_calculator.py smartbet-frontend/app/api/recommendations/route.ts
git commit -m "deploy(tuning): E4 — per-market confidence thresholds"
git push origin master
```

Live-ROI curl as before.

---

## Task 12: Deploy E5 (Kelly default) — CONDITIONAL

**GATE:** Task 7's report lists `E5` in `SHIP experiments`.

**Files:**
- Modify: `core/models.py` — change `UserBankroll.staking_strategy` default to `'kelly_fractional'` (was likely `'fixed_amount'`).
- Modify: `smartbet-frontend/app/components/BankrollSetupModal.tsx` — highlight Kelly as recommended in the setup wizard (visual only).

- [ ] **Step 1: Read the current default staking strategy**

```bash
grep -n "staking_strategy" core/models.py | head
```

Note current default.

- [ ] **Step 2: Change default to kelly_fractional**

Edit `core/models.py` — set the `staking_strategy` field's `default='kelly_fractional'` (leave existing user records untouched; this only affects new bankroll setups).

- [ ] **Step 3: Update the setup modal to visually recommend Kelly**

Read `smartbet-frontend/app/components/BankrollSetupModal.tsx`. Find where staking strategies are rendered. Add a "Recommended" badge or highlight to the `kelly_fractional` option.

- [ ] **Step 4: Commit + push**

```bash
git add core/models.py smartbet-frontend/app/components/BankrollSetupModal.tsx
git commit -m "deploy(tuning): E5 — Kelly (k=0.25) as default staking strategy"
git push origin master
```

- [ ] **Step 5: Verify (manual)**

Open the site, register a new user (or use the existing test user), go through bankroll setup, confirm Kelly is preselected/recommended.

---

## Self-review (executed by author)

**Spec coverage.** Each section of the spec maps to at least one task:
- Spec §2 (scope & filters) → Task 1 (`load_universe` matches audit's universe filter exactly).
- Spec §3 E1–E5 → Tasks 2, 3, 4, 5, 6 (one experiment per task, same numbers).
- Spec §4 (deliverable — report + script) → Task 7.
- Spec §5 (decision framework, verdict criteria, production diffs) → Tasks 8–12 (each experiment has its own conditional deployment task; verdict classifier from Task 1 enforces SHIP/INVESTIGATE/DISCARD criteria).
- Spec §6 (non-goals) → Task 7's `assemble_report` embeds the non-goals block.
- Spec §7 (success criteria — one focused session, no placeholders, verdict unambiguous) → structure of Task 7's report.
- Spec §8 risks → mitigated by bootstrap CI everywhere, human checkpoint at Task 7.

No gaps.

**Placeholder scan.** No "TBD"/"TODO" in the plan. All code steps show complete code. Task 8's threshold `T`, Task 9's factor `K`, Task 10's blacklist, Task 11's dict, Task 12's strategy string are all extracted from Task 7's report — the plan explicitly names the extraction step and substitutes the concrete value into the diff.

**Type consistency.**
- `bootstrap_ci` returns keys `point_roi_pct, ci_lo, ci_median, ci_hi` — matches audit and all callers.
- `classify_verdict(ci_lo, point, n)` positional args — consistent across E1, E2, E3, E4.
- `e{N}_recommendation` returns dicts with consistent naming: E1/E2/E3 use `best_*` keys; E4 uses `ship_cells`/`proposed_market_thresholds`; E5 uses simulation keys.
- `combined_recommendation` unpacks each `e{N}_reco` correctly based on the shape produced.

All consistent.

---

## Human checkpoints (early-exit map)

Reader is expected to pause and make a decision at these points:

1. **After Task 7, Step 6** — read the report. If `Executive verdict` starts with `NO SHIP`, skip Tasks 8–12; the outcome is "Approach 1 falsified, escalate to Approach 2 (Deep Model Rebuild) or Approach 3 (Niche Specialization)."
2. **Before each of Tasks 8–12** — check the GATE clause. Execute only if the report's SHIP list includes that experiment.
3. **After each deployed task (Tasks 8–12, Step 5)** — verify the live ROI moved in the expected direction. If not, investigate before continuing to the next deployment task.
