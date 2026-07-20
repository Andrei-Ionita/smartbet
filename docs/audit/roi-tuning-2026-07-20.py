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


# ---- E5: Kelly sizing simulation ----------------------------------------

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


# ---- Main -------------------------------------------------------------

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


if __name__ == '__main__':
    sys.exit(main())
