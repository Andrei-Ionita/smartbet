"""
Backtest harness for the recommendation filter.

Given a list of settled PredictionLog rows (already cleared by the audit
quarantine), apply different `FilterConfig`s and report yield/ROI/accuracy/
streaks/drawdown — stratified by league, odds bucket, market type, month, and
confidence bucket.

What this CAN answer:
  - "If we'd been more selective on dimension X, would yield have been higher?"
  - "Which strata (leagues, odds ranges, markets) carry the yield?"
  - "Does the current max_odds=2.50 cap help or hurt?"

What this CANNOT answer (by design — the data doesn't support it):
  - "What if we'd accepted bets we currently reject?" The DB only contains rows
    that passed the live filter, so this is fundamentally unanswerable without
    re-running the prediction engine against historical fixtures.

Read-only on the DB. All work is in-memory over the loaded row list.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Iterable, List, Optional, Sequence


# ────────────────────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class FilterConfig:
    """A candidate filter/ranker. Mirrors the current Django + V2 design space.

    All values are *decimal*, never percent. A row passes iff every populated
    condition matches (None = ignore that condition).
    """

    name: str
    # Hard floors / ceilings
    min_confidence: Optional[float] = None    # e.g. 0.35
    max_odds: Optional[float] = None          # e.g. 2.50
    min_odds: Optional[float] = None          # e.g. 1.30
    min_ev: Optional[float] = None            # e.g. 0.10
    max_ev: Optional[float] = None            # e.g. 0.30 (upper trim)
    # Two-track support: a row passes the "Safe" track if conf >= safe_min_confidence,
    # and the "Value" track if conf >= value_min_confidence AND EV >= value_min_ev.
    # If both are populated, EITHER track passing is enough — matches today's logic.
    safe_min_confidence: Optional[float] = None
    value_min_confidence: Optional[float] = None
    value_min_ev: Optional[float] = None
    # League gating
    league_blacklist: Sequence[str] = field(default_factory=list)
    league_watchlist: Sequence[str] = field(default_factory=list)
    watchlist_min_confidence: Optional[float] = None
    # Per-league overrides ({league_name: {min_confidence, min_ev}})
    league_tiers: dict = field(default_factory=dict)
    # Market filter
    market_types_allowed: Optional[Sequence[str]] = None
    # Outcome filter (e.g. drop "Under 2.5")
    drop_outcomes_substrings: Sequence[str] = field(default_factory=list)


def passes(row, cfg: FilterConfig) -> bool:
    """Return True if `row` would be recommended under `cfg`."""

    # Normalize a couple of fields the in-memory row may have in either unit.
    conf = row.confidence or 0
    if conf > 1:
        conf = conf / 100.0
    ev = row.expected_value
    if ev is not None and abs(ev) > 1:
        ev = ev / 100.0

    odds = row.odds
    # Legacy rows may have odds=None and only odds_home/draw/away set; back-fill
    # by predicted outcome for 1X2 so older data isn't discarded by the harness.
    if not odds and (row.market_type or '1x2') == '1x2':
        pred = (row.predicted_outcome or '').lower()
        odds = {
            'home': row.odds_home,
            'draw': row.odds_draw,
            'away': row.odds_away,
        }.get(pred)

    # Market filter
    if cfg.market_types_allowed is not None:
        if (row.market_type or '1x2') not in cfg.market_types_allowed:
            return False

    # Outcome substring filter (e.g. block "Under 2.5")
    pred_raw = (row.predicted_outcome or '').lower()
    for needle in cfg.drop_outcomes_substrings:
        if needle.lower() in pred_raw:
            return False

    # League gating
    league = row.league or ''
    if league in cfg.league_blacklist:
        return False
    # Per-league tier override has highest priority
    tier = cfg.league_tiers.get(league)
    if tier:
        if 'min_confidence' in tier and conf < tier['min_confidence']:
            return False
        if 'min_ev' in tier and (ev is None or ev < tier['min_ev']):
            return False
    if league in cfg.league_watchlist and cfg.watchlist_min_confidence is not None:
        if conf < cfg.watchlist_min_confidence:
            return False

    # Odds bounds
    if odds is not None:
        if cfg.max_odds is not None and odds > cfg.max_odds:
            return False
        if cfg.min_odds is not None and odds < cfg.min_odds:
            return False

    # EV bounds
    if ev is not None:
        if cfg.max_ev is not None and ev > cfg.max_ev:
            return False
        if cfg.min_ev is not None and ev < cfg.min_ev:
            return False

    # Two-track check: pass if EITHER track matches
    has_two_track = (
        cfg.safe_min_confidence is not None
        or (cfg.value_min_confidence is not None and cfg.value_min_ev is not None)
    )
    if has_two_track:
        safe_pass = (
            cfg.safe_min_confidence is not None
            and conf >= cfg.safe_min_confidence
        )
        value_pass = (
            cfg.value_min_confidence is not None
            and cfg.value_min_ev is not None
            and conf >= cfg.value_min_confidence
            and (ev or 0) >= cfg.value_min_ev
        )
        if not (safe_pass or value_pass):
            return False
    elif cfg.min_confidence is not None:
        if conf < cfg.min_confidence:
            return False

    return True


# ────────────────────────────────────────────────────────────────────────────
# Metrics
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class Metrics:
    n_total: int                 # rows considered
    n_kept: int                  # rows that passed the filter
    n_settled: int               # of kept, how many have a result
    correct: int
    accuracy: Optional[float]    # %
    total_pl: float              # $ (flat $10)
    yield_percent: Optional[float]  # P/L / staked * 100
    avg_roi: Optional[float]
    brier: Optional[float]       # against `was_correct` (binary 0/1)
    longest_win_streak: int
    longest_loss_streak: int
    max_drawdown: float          # most negative point on cumulative P/L (relative to running peak)


def metrics(rows: Iterable, *, only_settled: bool = True) -> Metrics:
    """Compute headline metrics on an iterable of PredictionLog rows."""
    rows = list(rows)
    n_total = len(rows)
    settled = [r for r in rows if r.was_correct is not None]
    n_settled = len(settled)

    if not n_settled:
        return Metrics(
            n_total=n_total, n_kept=n_total, n_settled=0,
            correct=0, accuracy=None, total_pl=0.0,
            yield_percent=None, avg_roi=None, brier=None,
            longest_win_streak=0, longest_loss_streak=0, max_drawdown=0.0,
        )

    correct = sum(1 for r in settled if r.was_correct)
    total_pl = sum((r.profit_loss_10 or 0) for r in settled)
    rois = [r.roi_percent for r in settled if r.roi_percent is not None]
    avg_roi = sum(rois) / len(rois) if rois else None

    accuracy = correct / n_settled * 100
    # Flat $10 stake => total staked == n_settled * 10.
    yield_pct = total_pl / (n_settled * 10) * 100

    # Brier score: mean squared error between confidence and outcome (1/0).
    # Many of our rows store confidence in percent or decimal — auto-detect.
    brier_terms = []
    for r in settled:
        c = r.confidence or 0
        if c > 1:
            c = c / 100.0
        outcome = 1 if r.was_correct else 0
        brier_terms.append((c - outcome) ** 2)
    brier = sum(brier_terms) / len(brier_terms) if brier_terms else None

    # Streaks + drawdown over chronological order.
    chrono = sorted(settled, key=lambda r: r.kickoff or datetime.min)
    longest_win = longest_loss = cur_win = cur_loss = 0
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for r in chrono:
        if r.was_correct:
            cur_win += 1
            cur_loss = 0
        else:
            cur_loss += 1
            cur_win = 0
        longest_win = max(longest_win, cur_win)
        longest_loss = max(longest_loss, cur_loss)
        cumulative += (r.profit_loss_10 or 0)
        peak = max(peak, cumulative)
        dd = cumulative - peak  # ≤ 0
        max_dd = min(max_dd, dd)

    return Metrics(
        n_total=n_total, n_kept=n_total, n_settled=n_settled,
        correct=correct, accuracy=accuracy, total_pl=total_pl,
        yield_percent=yield_pct, avg_roi=avg_roi, brier=brier,
        longest_win_streak=longest_win, longest_loss_streak=longest_loss,
        max_drawdown=max_dd,
    )


# ────────────────────────────────────────────────────────────────────────────
# Stratification
# ────────────────────────────────────────────────────────────────────────────

def _odds_bucket(row) -> str:
    o = row.odds
    if not o and (row.market_type or '1x2') == '1x2':
        pred = (row.predicted_outcome or '').lower()
        o = {'home': row.odds_home, 'draw': row.odds_draw, 'away': row.odds_away}.get(pred)
    if not o:
        return 'unknown'
    if o < 1.50:
        return '1.00-1.50'
    if o < 2.00:
        return '1.50-2.00'
    if o < 2.50:
        return '2.00-2.50'
    if o < 3.00:
        return '2.50-3.00'
    return '3.00+'


def _confidence_bucket(row) -> str:
    c = row.confidence or 0
    if c > 1:
        c = c / 100.0
    pct = c * 100
    if pct < 55:
        return '<55%'
    if pct < 60:
        return '55-60%'
    if pct < 65:
        return '60-65%'
    if pct < 70:
        return '65-70%'
    return '70%+'


def _month(row) -> str:
    return row.kickoff.strftime('%Y-%m') if row.kickoff else 'unknown'


DIMENSIONS = {
    'league':     lambda r: r.league or 'unknown',
    'market':     lambda r: r.market_type or '1x2',
    'odds':       _odds_bucket,
    'confidence': _confidence_bucket,
    'month':      _month,
}


def stratify(rows: Iterable, dim: str) -> List[tuple]:
    """Return a list of (bucket_label, Metrics) sorted by yield descending."""
    key_fn = DIMENSIONS[dim]
    buckets: dict = {}
    for r in rows:
        buckets.setdefault(key_fn(r), []).append(r)
    out = [(label, metrics(group)) for label, group in buckets.items()]
    # Sort: settled rows first (highest n_settled), tie-break on yield, then label.
    out.sort(key=lambda kv: (-(kv[1].n_settled or 0), -(kv[1].yield_percent or -math.inf), kv[0]))
    return out


# ────────────────────────────────────────────────────────────────────────────
# Top-level
# ────────────────────────────────────────────────────────────────────────────

def evaluate(rows: Iterable, cfg: FilterConfig) -> tuple[Metrics, List]:
    """Apply `cfg` to `rows`, return (metrics_on_kept, kept_rows)."""
    rows = list(rows)
    kept = [r for r in rows if passes(r, cfg)]
    m = metrics(kept)
    # Patch n_total / n_kept so the caller can see how aggressive the filter was.
    return replace(m, n_total=len(rows), n_kept=len(kept)), kept


def compare(rows: Iterable, configs: Sequence[FilterConfig]) -> List[tuple]:
    """Apply every config to the same `rows`, return [(cfg, Metrics, kept_rows)]."""
    rows = list(rows)
    return [(cfg, *evaluate(rows, cfg)) for cfg in configs]


# ────────────────────────────────────────────────────────────────────────────
# Baseline configs — mirrors what's live + a few hypotheses to test.
#
# These reflect the *Django-side* filter. The Next.js engine has additional
# upstream gating (probability_gap min, EV >= 5% per market, evaluateValueZone
# trap cap) that we can't re-run here without replaying SportMonks fixtures.
# ────────────────────────────────────────────────────────────────────────────

CURRENT_PROD = FilterConfig(
    name='current_prod',
    # Two-track: Safe (conf >= 60%) OR Value (conf >= 35% AND EV >= 10%)
    safe_min_confidence=0.60,
    value_min_confidence=0.35,
    value_min_ev=0.10,
    # Hard ceiling shipped Feb 2026
    max_odds=2.50,
)

NO_MAX_ODDS = replace(CURRENT_PROD, name='no_max_odds', max_odds=None)

EV_TRIM_30 = replace(
    CURRENT_PROD, name='ev_trim_30', max_ev=0.30,
)
EV_TRIM_20 = replace(
    CURRENT_PROD, name='ev_trim_20', max_ev=0.20,
)

VALUE_ONLY = FilterConfig(
    name='value_only',
    value_min_confidence=0.35,
    value_min_ev=0.10,
    max_odds=2.50,
)

SAFE_ONLY = FilterConfig(
    name='safe_only',
    safe_min_confidence=0.60,
    max_odds=2.50,
)

# V2-style league tiers from prediction_enhancer_v2 (lines 127–209 on the
# experiment/prediction-improvements branch). Tier-1 leagues no override;
# tier-3 leagues require higher confidence AND higher EV.
V2_LEAGUE_TIERS = {
    'Premier League':          {'min_confidence': 0.60, 'min_ev': 0.05},
    'La Liga':                 {'min_confidence': 0.60, 'min_ev': 0.05},
    'Serie A':                 {'min_confidence': 0.60, 'min_ev': 0.05},
    'Bundesliga':              {'min_confidence': 0.60, 'min_ev': 0.05},
    'Ligue 1':                 {'min_confidence': 0.60, 'min_ev': 0.05},
    'Eredivisie':              {'min_confidence': 0.60, 'min_ev': 0.05},
    # Tier-3: known-noisy leagues, stricter
    'Admiral Bundesliga':      {'min_confidence': 0.68, 'min_ev': 0.12},
    'Liga Portugal':           {'min_confidence': 0.68, 'min_ev': 0.12},
    'Super Lig':               {'min_confidence': 0.68, 'min_ev': 0.12},
    'Russian Premier League':  {'min_confidence': 0.68, 'min_ev': 0.12},
    # Cups: medium strictness
    'FA Cup':                  {'min_confidence': 0.65, 'min_ev': 0.10},
    'Carabao Cup':             {'min_confidence': 0.65, 'min_ev': 0.10},
    'Copa Del Rey':            {'min_confidence': 0.65, 'min_ev': 0.10},
    'Coppa Italia':            {'min_confidence': 0.65, 'min_ev': 0.10},
}

V2_TIERS = replace(
    CURRENT_PROD,
    name='v2_league_tiers',
    league_tiers=V2_LEAGUE_TIERS,
)

DROP_UNDER_25 = replace(
    CURRENT_PROD,
    name='drop_under_2.5',
    drop_outcomes_substrings=['under 2.5'],
)

# League blacklist informed by the actual stratification, not just a priori beliefs.
# Includes the current production list + the leagues backtesting confirms are losing money.
DATA_DRIVEN_BLACKLIST = [
    'Admiral Bundesliga',  # currently blacklisted, confirmed -33% yield
    'Liga Portugal',       # currently blacklisted, confirmed -29% yield
    'Allsvenskan',         # not currently blacklisted, -31% yield over 6 rows
    'Eliteserien',         # not currently blacklisted, -21% yield over 14 rows
    # NOTE: Premier League shows -21% yield over 10 rows but the sample is too
    # thin and it's a structurally important league — do NOT blacklist on n=10.
]

# Stacks the wins from the individual configs: drop Under 2.5 + EV trim at 20% +
# data-driven league blacklist. Are they additive?
CANDIDATE = replace(
    CURRENT_PROD,
    name='candidate',
    max_ev=0.20,
    drop_outcomes_substrings=['under 2.5'],
    league_blacklist=DATA_DRIVEN_BLACKLIST,
)

# What Phase 2a deploys: same as drop_under_2.5 + the data-driven blacklist, but
# no EV trim. Live filter as of commit 9dddafe.
PHASE_2A = replace(
    CURRENT_PROD,
    name='phase_2a',
    drop_outcomes_substrings=['under 2.5'],
    league_blacklist=DATA_DRIVEN_BLACKLIST,
)

# Phase 2b adds the EV ≤ 0.20 cap on top of Phase 2a. Live filter once shipped.
PHASE_2B = replace(
    PHASE_2A,
    name='phase_2b',
    max_ev=0.20,
)

# Phase 2c adds a soft watchlist on top of Phase 2b. Premier League picks must
# clear confidence ≥ 65% AND EV ≥ 12% to pass. Live filter as of 2026-05-25.
PHASE_2C = replace(
    PHASE_2B,
    name='phase_2c',
    league_tiers={
        **PHASE_2B.league_tiers,
        'Premier League': {'min_confidence': 0.65, 'min_ev': 0.12},
    },
)

BASELINES: List[FilterConfig] = [
    CURRENT_PROD,
    NO_MAX_ODDS,
    EV_TRIM_30,
    EV_TRIM_20,
    VALUE_ONLY,
    SAFE_ONLY,
    V2_TIERS,
    DROP_UNDER_25,
    PHASE_2A,
    PHASE_2B,
    PHASE_2C,
    CANDIDATE,
]
