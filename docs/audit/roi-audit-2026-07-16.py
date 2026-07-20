"""ROI audit — reproducible analysis over a frozen PredictionLog snapshot.

Design spec: docs/superpowers/specs/2026-07-16-roi-audit-design.md
Reproducibility: docs/audit/README.md

Usage:
    python roi-audit-2026-07-16.py --snapshot <sqlite> [--out <report.md>]
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


# ---- Q2: Bootstrap confidence interval --------------------------------

def q2_bootstrap_ci(profits: np.ndarray, n_iter: int = 10000, seed: int = 42) -> dict:
    """Bootstrap 95% CI on ROI (%). ROI = mean(profit_loss_10) / 10 * 100.

    Returns NaN dict for empty input.
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


def format_q2(ui_ci: dict, un_ci: dict) -> str:
    def line(label, r):
        if any(map(np.isnan, [r['point_roi_pct'], r['ci_lo'], r['ci_hi']])):
            return f"- {label}: no data\n"
        return (f"- {label}: **{r['point_roi_pct']:.2f}%** "
                f"(95% CI: {r['ci_lo']:.2f}% → {r['ci_hi']:.2f}%)\n")
    return ("## Q2 — Point estimate and 95% confidence interval\n\n"
            + line('UI-matching (conf ≥ 0.60)', ui_ci)
            + line('Unfiltered', un_ci)
            + "\n")


# ---- Q3: Monthly ROI stability ----------------------------------------

def q3_monthly_roi(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) == 0:
        return pd.DataFrame(columns=['month', 'n', 'roi_pct', 'pl_total'])
    g = df.assign(_m=df['prediction_logged_at'].dt.to_period('M').astype(str))
    out = g.groupby('_m').agg(n=('profit_loss_10', 'size'),
                              pl_total=('profit_loss_10', 'sum')).reset_index()
    out = out.rename(columns={'_m': 'month'})
    out['roi_pct'] = out['pl_total'] / (out['n'] * 10.0) * 100.0
    return out[['month', 'n', 'roi_pct', 'pl_total']].sort_values('month').reset_index(drop=True)


def ascii_bar_chart(values: list[tuple[str, float]], width: int = 30) -> str:
    """Render (label, value) pairs as a monospace horizontal bar chart.

    Handles negatives by splitting positive/negative around a zero axis.
    """
    if not values:
        return '(no data)'
    max_abs = max(abs(v) for _, v in values) or 1.0
    label_w = max(len(l) for l, _ in values)
    lines = []
    for label, v in values:
        bar_len = int(round(abs(v) / max_abs * width))
        bar = ('▆' * bar_len) if v >= 0 else ('▁' * bar_len)
        sign = '+' if v >= 0 else '−'
        lines.append(f"{label:<{label_w}}  {sign}{abs(v):6.2f}%  {bar}")
    return '\n'.join(lines)


def format_q3(ui_df: pd.DataFrame, un_df: pd.DataFrame) -> str:
    def block(label, d):
        if len(d) == 0:
            return f"**{label}:** no data.\n\n"
        # Annotate months with n<10 as underpowered
        def annotate(row):
            m = row['month']
            return f"{m} (n={int(row['n'])})" if row['n'] < 10 else m
        chart = ascii_bar_chart(
            [(annotate(row), row['roi_pct']) for _, row in d.iterrows()]
        )
        pos = int((d['roi_pct'] > 0).sum())
        return (f"**{label}** — {pos}/{len(d)} months positive\n\n"
                f"```\n{chart}\n```\n\n")
    return ("## Q3 — Monthly ROI stability\n\n"
            + block('UI-matching', ui_df)
            + block('Unfiltered', un_df))


# ---- Q4: Confidence buckets -------------------------------------------

_CONF_EDGES = [0.55, 0.60, 0.70, 0.80, 1.001]  # 1.001 to include 1.0
_CONF_LABELS = ['0.55–0.60', '0.60–0.70', '0.70–0.80', '0.80–1.00']


def q4_confidence_buckets(df: pd.DataFrame, min_n: int = 30) -> pd.DataFrame:
    if len(df) == 0:
        return pd.DataFrame(columns=['bucket', 'n', 'roi_pct', 'pl_total', 'underpowered'])
    d = df.copy()
    d['_bucket'] = pd.cut(d['confidence'], bins=_CONF_EDGES,
                          labels=_CONF_LABELS, right=False, include_lowest=True)
    out = d.groupby('_bucket', observed=False).agg(
        n=('profit_loss_10', 'size'),
        pl_total=('profit_loss_10', 'sum'),
    ).reset_index().rename(columns={'_bucket': 'bucket'})
    out['roi_pct'] = np.where(out['n'] > 0,
                              out['pl_total'] / (out['n'].replace(0, 1) * 10.0) * 100.0, 0.0)
    out['underpowered'] = out['n'] < min_n
    return out


def _format_breakdown_df(d: pd.DataFrame, key_col: str) -> str:
    if len(d) == 0:
        return '(no data)\n'
    lines = []
    for _, row in d.iterrows():
        flag = ' ⚠️ n<30' if row['underpowered'] else ''
        roi = f"{row['roi_pct']:+7.2f}%"
        extra = ''
        if 'win_rate_pct' in row:
            extra = f"  win {row['win_rate_pct']:5.1f}%"
        lines.append(f"  {str(row[key_col]):<28} n={int(row['n']):>4}  ROI {roi}{extra}{flag}")
    return '\n'.join(lines) + '\n'


def format_q4(ui_df: pd.DataFrame, un_df: pd.DataFrame, ui_n: int, un_n: int) -> str:
    def block(label, d, universe_n):
        body = _format_breakdown_df(d, 'bucket')
        shown = int(d['n'].sum()) if len(d) > 0 else 0
        missing = universe_n - shown
        footer = ""
        if missing > 0:
            footer = f"  (not shown: {missing} bet(s) with confidence < 0.55 or NaN)\n"
        return f"**{label}**\n```\n{body}{footer}```\n\n"
    return ("## Q4 — Confidence bucket effect\n\n"
            + block('UI-matching (conf ≥ 0.60)', ui_df, ui_n)
            + block('Unfiltered', un_df, un_n))


# ---- Q5: Market breakdown ---------------------------------------------

def q5_market_breakdown(df: pd.DataFrame, min_n: int = 30) -> pd.DataFrame:
    if len(df) == 0:
        return pd.DataFrame(columns=['market_type', 'n', 'roi_pct', 'win_rate_pct', 'underpowered'])
    d = df.copy()
    d['_won'] = _coerce_bool(d.get('was_correct', pd.Series([False] * len(d)))).astype(int)
    out = d.groupby(d['market_type'].fillna('unknown')).agg(
        n=('profit_loss_10', 'size'),
        pl_total=('profit_loss_10', 'sum'),
        wins=('_won', 'sum'),
    ).reset_index().rename(columns={'market_type': 'market_type'})
    out['roi_pct'] = out['pl_total'] / (out['n'] * 10.0) * 100.0
    out['win_rate_pct'] = out['wins'] / out['n'] * 100.0
    out['underpowered'] = out['n'] < min_n
    return out[['market_type', 'n', 'roi_pct', 'win_rate_pct', 'underpowered']].sort_values('n', ascending=False)


def format_q5(ui_df: pd.DataFrame, un_df: pd.DataFrame) -> str:
    return ("## Q5 — Market breakdown\n\n"
            f"**UI-matching**\n```\n{_format_breakdown_df(ui_df, 'market_type')}```\n\n"
            f"**Unfiltered**\n```\n{_format_breakdown_df(un_df, 'market_type')}```\n\n")


# ---- Q6: League breakdown ---------------------------------------------

def q6_league_breakdown(df: pd.DataFrame, top_n: int = 10, min_n: int = 30) -> pd.DataFrame:
    if len(df) == 0:
        return pd.DataFrame(columns=['league', 'n', 'roi_pct', 'win_rate_pct', 'underpowered'])
    d = df.copy()
    d['_won'] = _coerce_bool(d.get('was_correct', pd.Series([False] * len(d)))).astype(int)
    out = d.groupby(d['league'].fillna('unknown')).agg(
        n=('profit_loss_10', 'size'),
        pl_total=('profit_loss_10', 'sum'),
        wins=('_won', 'sum'),
    ).reset_index().rename(columns={'league': 'league'})
    out['roi_pct'] = out['pl_total'] / (out['n'] * 10.0) * 100.0
    out['win_rate_pct'] = out['wins'] / out['n'] * 100.0
    out['underpowered'] = out['n'] < min_n
    return out.sort_values('n', ascending=False).head(top_n)[
        ['league', 'n', 'roi_pct', 'win_rate_pct', 'underpowered']
    ]


def format_q6(ui_df: pd.DataFrame, un_df: pd.DataFrame) -> str:
    return ("## Q6 — League breakdown (top 10 by volume)\n\n"
            f"**UI-matching**\n```\n{_format_breakdown_df(ui_df, 'league')}```\n\n"
            f"**Unfiltered**\n```\n{_format_breakdown_df(un_df, 'league')}```\n\n")


# ---- Q7: Profit concentration -----------------------------------------

def q7_concentration(df: pd.DataFrame, top_ns: list[int] = None) -> dict:
    if top_ns is None:
        top_ns = [1, 5, 10, 25]
    if len(df) == 0:
        return {'total_profit': 0.0, 'total_bets': 0, 'top_shares': []}
    profits = df['profit_loss_10'].to_numpy()
    sorted_desc = np.sort(profits)[::-1]
    total_net = float(profits.sum())
    total_positive = float(profits[profits > 0].sum())
    shares = []
    for n in top_ns:
        take = sorted_desc[:n].sum() if n <= len(sorted_desc) else sorted_desc.sum()
        share_pos = float(take / total_positive * 100.0) if total_positive > 0 else float('nan')
        share_net = float(take / total_net * 100.0) if total_net != 0 else float('nan')
        shares.append((n, share_pos, share_net))
    return {'total_profit': total_net, 'total_bets': len(df), 'top_shares': shares}


def format_q7(ui_stats: dict, un_stats: dict) -> str:
    def block(label, s):
        if s['total_bets'] == 0:
            return f"**{label}:** no data.\n\n"
        lines = [f"- Total net profit (over {s['total_bets']} bets): {s['total_profit']:+.2f}"]
        for n, sp, sn in s['top_shares']:
            spf = f"{sp:.1f}%" if not np.isnan(sp) else 'n/a'
            snf = f"{sn:.1f}%" if not np.isnan(sn) else 'n/a'
            lines.append(f"- Top {n} bets: {spf} of gross positive profit, {snf} of net profit")
        return f"**{label}**\n\n" + '\n'.join(lines) + "\n\n"
    return ("## Q7 — Profit concentration\n\n"
            + block('UI-matching', ui_stats)
            + block('Unfiltered', un_stats))


# ---- Q8: Odds sanity --------------------------------------------------

def q8_odds_sanity(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) == 0:
        return pd.DataFrame(columns=['bucket', 'n', 'avg_odds', 'avg_confidence', 'implied_prob_from_odds'])
    d = df[df['odds'].notna() & (df['odds'] > 1.0)].copy()
    d['_bucket'] = pd.cut(d['confidence'], bins=_CONF_EDGES,
                          labels=_CONF_LABELS, right=False, include_lowest=True)
    out = d.groupby('_bucket', observed=False).agg(
        n=('odds', 'size'),
        avg_odds=('odds', 'mean'),
        avg_confidence=('confidence', 'mean'),
    ).reset_index().rename(columns={'_bucket': 'bucket'})
    out['implied_prob_from_odds'] = 1.0 / out['avg_odds']
    return out


def format_q8(ui_df: pd.DataFrame, un_df: pd.DataFrame) -> str:
    def block(label, d):
        if len(d) == 0:
            return f"**{label}:** no data.\n\n"
        lines = []
        prev_avg_odds = None
        anomaly_note = ''
        for _, row in d.iterrows():
            lines.append(f"  {str(row['bucket']):<12} n={int(row['n']):>4}  "
                         f"avg_odds={row['avg_odds']:5.2f}  "
                         f"avg_conf={row['avg_confidence']:5.3f}  "
                         f"implied_p={row['implied_prob_from_odds']:5.3f}")
            if prev_avg_odds is not None and row['avg_odds'] > prev_avg_odds:
                anomaly_note = ("\n⚠️ ANOMALY: average odds INCREASE as confidence rises. "
                                "Expected inverse relationship — investigate odds capture.")
            prev_avg_odds = row['avg_odds']
        return f"**{label}**\n\n```\n" + '\n'.join(lines) + f"\n```{anomaly_note}\n\n"
    return ("## Q8 — Odds sanity\n\n"
            + block('UI-matching', ui_df)
            + block('Unfiltered', un_df))


# ---- Verdict + report assembly ----------------------------------------

def _fmt_pct(v):
    return 'n/a' if (v is None or (isinstance(v, float) and np.isnan(v))) else f"{v:+.2f}%"


def derive_verdict(
    ui_stats: dict, un_stats: dict,
    ui_ci: dict, un_ci: dict,
    ui_month: pd.DataFrame,
    ui_conc: dict,
    ui_odds: pd.DataFrame,
) -> tuple[str, list[str], list[str]]:
    """Return (verdict, findings, recommended_actions).

    Rules (evaluated in order — first hard fail wins):
    - Unfiltered n < 30 → DO NOT PUBLISH (sample too small)
    - UI CI includes zero or crosses to negative → DO NOT PUBLISH
    - UI n < 100 → CONDITIONAL TRUST + "collect more data" action
    - Q3: < 50% of months positive → CONDITIONAL TRUST + "streak-dependent" note
    - Q7: top 5 > 60% of positive profit → CONDITIONAL TRUST + "fragile concentration" note
    - Q8: any inversion in avg_odds vs confidence → DO NOT PUBLISH (data quality)
    - Otherwise → TRUST
    """
    findings: list[str] = []
    actions: list[str] = []
    hard_stop = False
    conditional = False

    if un_stats['n'] < 30:
        findings.append(f"Unfiltered sample only {un_stats['n']} bets (< 30 floor).")
        actions.append("Collect more resolved bets before re-auditing.")
        hard_stop = True

    if not any(map(np.isnan, [ui_ci['ci_lo'], ui_ci['ci_hi']])):
        if ui_ci['ci_lo'] <= 0.0:
            findings.append(f"UI-matching 95% CI includes zero or negative "
                            f"({ui_ci['ci_lo']:+.2f}% → {ui_ci['ci_hi']:+.2f}%).")
            actions.append("Do not publish a specific ROI figure until CI is entirely above zero.")
            hard_stop = True

    if ui_stats['n'] < 100 and not hard_stop:
        findings.append(f"UI-matching sample is {ui_stats['n']} bets (< 100).")
        actions.append("Add a sample-size disclosure to the public track record.")
        conditional = True

    if len(ui_month) > 0:
        positive_months = int((ui_month['roi_pct'] > 0).sum())
        if positive_months / len(ui_month) < 0.5:
            findings.append(f"Only {positive_months}/{len(ui_month)} months positive — "
                            f"streak-dependent, not consistent skill.")
            actions.append("Investigate what drove the winning months before claiming edge.")
            conditional = True

    if ui_conc['total_bets'] > 0:
        top5 = next((sp for n, sp, sn in ui_conc['top_shares'] if n == 5), None)
        if top5 is not None and not np.isnan(top5) and top5 > 60.0:
            findings.append(f"Top 5 bets contribute {top5:.1f}% of positive profit — fragile.")
            actions.append("Report concentration alongside headline ROI on the public track page.")
            conditional = True

    if ui_odds['n'].sum() < 30 or (ui_odds['n'] > 0).sum() < 2:
        total_ui_bets = ui_stats['n']
        valid_odds = int(ui_odds['n'].sum())
        coverage_pct = (valid_odds / total_ui_bets * 100.0) if total_ui_bets else 0.0
        findings.append(
            f"Q8 odds coverage is thin: only {valid_odds}/{total_ui_bets} "
            f"UI-matching bets ({coverage_pct:.1f}%) have valid odds populated "
            f"across ≥2 confidence buckets. Q8's inversion test could not run "
            f"meaningfully on this dataset — treat Q8 as inconclusive."
        )
        actions.append(
            "Investigate why the majority of resolved bets have missing or "
            "invalid odds. Q8 (odds sanity) is the audit's foundational check "
            "on the odds field; without odds coverage, the entire P&L calc "
            "sits on data we haven't validated."
        )
        conditional = True

    if len(ui_odds) > 1:
        prev = None
        for _, row in ui_odds.iterrows():
            if prev is not None and row['avg_odds'] > prev:
                findings.append("Q8 anomaly: avg odds INCREASES as confidence rises.")
                actions.append("Investigate odds capture pipeline — audit rests on this field.")
                hard_stop = True
                break
            prev = row['avg_odds']

    if hard_stop:
        return ('DO NOT PUBLISH', findings, actions)
    if conditional:
        return ('CONDITIONAL TRUST', findings, actions)
    return ('TRUST', findings, actions)


def assemble_report(
    snapshot_path: str,
    ui_stats: dict, un_stats: dict,
    section_bodies: list[str],
    verdict: str,
    findings: list[str],
    actions: list[str],
) -> str:
    snap_size = _os.path.getsize(snapshot_path) if _os.path.exists(snapshot_path) else 0
    now = _dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    findings_md = '\n'.join(f'- {f}' for f in findings) if findings else '- (none)'
    actions_md = '\n'.join(f'- {a}' for a in actions) if actions else '- (none)'
    verdict_reason = findings[0] if findings else 'All statistical gates passed.'
    return f"""# ROI Audit Report — 2026-07-16

**Verdict:** `{verdict}` — {verdict_reason}

---

## Data provenance

- Snapshot file: `{snapshot_path}` ({snap_size:,} bytes)
- Audit run at: {now}
- Universe filter: `is_recommended=True AND actual_outcome IS NOT NULL AND match_status!='archived' AND is_audit_excluded!=True`
- UI-matching filter adds: `confidence >= 0.60`
- Sample sizes: {ui_stats['n']} (UI-matching), {un_stats['n']} (unfiltered)

---

{''.join(section_bodies)}

## Findings

{findings_md}

## Recommended actions before publishing (or launching Phase 2)

{actions_md}

## Non-goals (this audit does NOT prove)

- Odds achievability — logged odds are from one bookmaker at fetch time; whether a real user could place a bet at those odds 30 min before kickoff is not tested here.
- Real-world friction — no accounting for bookmaker limits/bans, minimum stakes, currency conversion, tax.
- Prospective validity — everything is retrospective. Only a sealed forward-test (Phase 2) can answer whether the future looks like the past.
- Model attribution — the audit measures pipeline output, not which model/signal is producing the edge.

---

*Report generated by `docs/audit/roi-audit-2026-07-16.py`. Re-run against a fresh snapshot to regenerate.*
"""


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

    sections: list[str] = []

    ui_stats = q1_sample_size(ui_df)
    un_stats = q1_sample_size(unfiltered_df)
    sections.append(format_q1(ui_stats, un_stats))

    severity, msg = q1_gate(ui_stats, un_stats)
    print(sections[-1])
    print(f"### Q1 gate: {severity.upper()}\n\n{msg}\n")

    # Even if gate is 'stop' we still compute the remaining sections so the
    # report is complete — verdict logic will reflect the hard stop.

    ui_ci = q2_bootstrap_ci(ui_df['profit_loss_10'].to_numpy())
    un_ci = q2_bootstrap_ci(unfiltered_df['profit_loss_10'].to_numpy())
    sections.append(format_q2(ui_ci, un_ci))

    ui_month = q3_monthly_roi(ui_df)
    un_month = q3_monthly_roi(unfiltered_df)
    sections.append(format_q3(ui_month, un_month))

    sections.append(format_q4(q4_confidence_buckets(ui_df),
                              q4_confidence_buckets(unfiltered_df),
                              len(ui_df), len(unfiltered_df)))
    sections.append(format_q5(q5_market_breakdown(ui_df),
                              q5_market_breakdown(unfiltered_df)))
    sections.append(format_q6(q6_league_breakdown(ui_df),
                              q6_league_breakdown(unfiltered_df)))

    ui_conc = q7_concentration(ui_df)
    un_conc = q7_concentration(unfiltered_df)
    sections.append(format_q7(ui_conc, un_conc))

    ui_odds = q8_odds_sanity(ui_df)
    un_odds = q8_odds_sanity(unfiltered_df)
    sections.append(format_q8(ui_odds, un_odds))

    # Print all remaining sections
    for s in sections[1:]:
        print(s)

    verdict, findings, actions = derive_verdict(
        ui_stats, un_stats, ui_ci, un_ci, ui_month, ui_conc, ui_odds,
    )
    print(f"## Verdict: {verdict}\n")
    for f in findings:
        print(f"  - {f}")

    if args.out:
        report = assemble_report(
            args.snapshot, ui_stats, un_stats, sections, verdict, findings, actions,
        )
        with open(args.out, 'w', encoding='utf-8') as fh:
            fh.write(report)
        print(f"\nReport written to {args.out}")

    return 0 if verdict == 'TRUST' else 1


if __name__ == '__main__':
    sys.exit(main())
