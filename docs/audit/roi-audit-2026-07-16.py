"""ROI audit — reproducible analysis over a frozen PredictionLog snapshot.

Design spec: docs/superpowers/specs/2026-07-16-roi-audit-design.md
Reproducibility: docs/audit/README.md

Usage:
    python roi-audit-2026-07-16.py --snapshot <sqlite> [--out <report.md>]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from typing import Optional

import numpy as np
import pandas as pd


# ---- Data loading -----------------------------------------------------

TRUE_STRINGS = {'True', 't', '1', 'true'}


def _coerce_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).isin(TRUE_STRINGS)


def load_and_filter(snapshot_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load the snapshot and apply the audit universe filter.

    Returns (df_ui_matching, df_unfiltered).
    """
    conn = sqlite3.connect(snapshot_path)
    df = pd.read_sql_query('SELECT * FROM prediction_log', conn)
    conn.close()

    df['is_recommended'] = _coerce_bool(df['is_recommended'])
    df['is_audit_excluded'] = _coerce_bool(df.get('is_audit_excluded', pd.Series([False] * len(df))))
    df['confidence'] = pd.to_numeric(df['confidence'], errors='coerce')
    df['profit_loss_10'] = pd.to_numeric(df['profit_loss_10'], errors='coerce')
    df['odds'] = pd.to_numeric(df['odds'], errors='coerce')
    df['prediction_logged_at'] = pd.to_datetime(df['prediction_logged_at'], errors='coerce', utc=True)

    universe = df[
        df['is_recommended']
        & df['actual_outcome'].notna() & (df['actual_outcome'] != '')
        & (df['match_status'].fillna('') != 'archived')
        & (~df['is_audit_excluded'])
        & df['profit_loss_10'].notna()
    ].copy()

    ui_matching = universe[universe['confidence'] >= 0.60].copy()
    return ui_matching, universe


# ---- Q1: Sample size and time coverage --------------------------------

def q1_sample_size(df: pd.DataFrame) -> dict:
    if len(df) == 0:
        return {'n': 0, 'date_min': None, 'date_max': None,
                'months_covered': 0, 'per_month': []}
    dates = df['prediction_logged_at'].dropna()
    per_month = (
        df.assign(_m=df['prediction_logged_at'].dt.to_period('M'))
          .groupby('_m').size().sort_index()
    )
    return {
        'n': len(df),
        'date_min': dates.min().date().isoformat() if not dates.empty else None,
        'date_max': dates.max().date().isoformat() if not dates.empty else None,
        'months_covered': len(per_month),
        'per_month': [(str(k), int(v)) for k, v in per_month.items()],
    }


def format_q1(ui_stats: dict, unfiltered_stats: dict) -> str:
    def block(label, s):
        if s['n'] == 0:
            return f"**{label}:** 0 bets — nothing to analyze.\n\n"
        pm = '\n'.join(f'  - {m}: {n} bets' for m, n in s['per_month'])
        return (
            f"**{label}**\n\n"
            f"- Total resolved bets: **{s['n']}**\n"
            f"- Date range: {s['date_min']} → {s['date_max']} "
            f"({s['months_covered']} calendar months)\n"
            f"- Per month:\n{pm}\n\n"
        )
    return "## Q1 — Sample size and time coverage\n\n" + block('UI-matching (conf ≥ 0.60)', ui_stats) + block('Unfiltered', unfiltered_stats)


# ---- Verdict gates ----------------------------------------------------

def q1_gate(ui_stats: dict, unfiltered_stats: dict) -> tuple[str, str]:
    """Return (severity, message). severity ∈ {'ok', 'caveat', 'stop'}."""
    if unfiltered_stats['n'] < 30:
        return ('stop',
                f"Unfiltered sample is only {unfiltered_stats['n']} bets — below the 30-bet floor. "
                "HARD STOP: verdict is DO NOT PUBLISH, sample too small.")
    if ui_stats['n'] < 100:
        return ('caveat',
                f"UI-matching sample is only {ui_stats['n']} bets (< 100). "
                "Numbers are directionally informative but statistically weak — verdict will be at best CONDITIONAL TRUST.")
    return ('ok', f"Sample sizes look adequate ({ui_stats['n']} UI, {unfiltered_stats['n']} unfiltered).")


# ---- Main -------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--out', help='If set, write the assembled report to this path.')
    args = parser.parse_args(argv)

    ui_df, unfiltered_df = load_and_filter(args.snapshot)

    ui_stats = q1_sample_size(ui_df)
    un_stats = q1_sample_size(unfiltered_df)
    print(format_q1(ui_stats, un_stats))

    severity, msg = q1_gate(ui_stats, un_stats)
    print(f"### Q1 gate: {severity.upper()}\n\n{msg}\n")

    if severity == 'stop':
        print("HALTING at Q1 as designed.")
        return 2  # nonzero exit to indicate hard-stop verdict

    # Q2-Q8 will be filled in by subsequent tasks.
    return 0


if __name__ == '__main__':
    sys.exit(main())
