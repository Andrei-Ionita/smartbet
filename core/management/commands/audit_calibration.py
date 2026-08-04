"""
READ-ONLY calibration evidence audit for the BET / NO-BET price-qualification
phase. Writes nothing, calls no provider, touches no claim.

WHAT THIS ANSWERS
-----------------
Can BetGlitch's stored `confidence` support calibrated probabilities, fair odds
and an explicit BET / NO-BET decision?

It must not be assumed to be a probability. What is stored is:

    confidence = min(sportmonks_probability * form_multiplier, 0.95)

where `form_multiplier` is a hand-set heuristic in [0.85, 1.08] applied to ONE
outcome without renormalising the others (app/api/recommendations/route.ts).
A number produced that way is not a probability distribution, whatever its
range suggests, so this command measures how far off it actually is rather
than assuming either way.

METHOD
------
* One row per fixture. PredictionLog holds exactly one row per fixture, so a
  fixture cannot straddle a split — but the grouping is enforced explicitly
  rather than relied upon.
* Chronological split on kickoff. Never shuffled: a shuffled split would let a
  later match inform an earlier prediction.
* Calibrators are fitted on the EARLIER partition only and scored on the LATER
  one.
* Rows without a settled outcome, audit-excluded rows, and rows first logged
  after kickoff are excluded before anything is computed.
"""
import math
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand

from core.models import PredictionLog

BUCKETS = [(0.0, 0.5), (0.5, 0.55), (0.55, 0.6), (0.6, 0.65), (0.65, 0.7),
           (0.7, 0.8), (0.8, 1.01)]


# ── metrics ──────────────────────────────────────────────────────────────────
def brier(pairs):
    """Mean squared error of a probabilistic forecast. Lower is better."""
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs) if pairs else None


def log_loss(pairs, eps=1e-12):
    if not pairs:
        return None
    total = 0.0
    for p, y in pairs:
        p = min(max(p, eps), 1 - eps)
        total += -(y * math.log(p) + (1 - y) * math.log(1 - p))
    return total / len(pairs)


def reliability(pairs):
    """Observed frequency per forecast bucket, plus expected calibration error."""
    rows, ece, n = [], 0.0, len(pairs)
    for lo, hi in BUCKETS:
        bucket = [(p, y) for p, y in pairs if lo <= p < hi]
        if not bucket:
            continue
        mean_p = sum(p for p, _ in bucket) / len(bucket)
        observed = sum(y for _, y in bucket) / len(bucket)
        rows.append((lo, hi, len(bucket), mean_p, observed, observed - mean_p))
        ece += (len(bucket) / n) * abs(observed - mean_p)
    return rows, ece


def discrimination(pairs):
    """AUC via the Mann-Whitney identity. 0.5 = no discrimination at all."""
    pos = [p for p, y in pairs if y == 1]
    neg = [p for p, y in pairs if y == 0]
    if not pos or not neg:
        return None
    wins = ties = 0
    for a in pos:
        for b in neg:
            if a > b:
                wins += 1
            elif a == b:
                ties += 1
    return (wins + 0.5 * ties) / (len(pos) * len(neg))


# ── calibrators (fit on earlier rows only) ───────────────────────────────────
def fit_platt(pairs, iters=2000, lr=0.05):
    """Logistic calibration on the logit of the raw score."""
    a, b = 1.0, 0.0
    for _ in range(iters):
        ga = gb = 0.0
        for p, y in pairs:
            z = min(max(p, 1e-6), 1 - 1e-6)
            x = math.log(z / (1 - z))
            q = 1 / (1 + math.exp(-(a * x + b)))
            ga += (q - y) * x
            gb += (q - y)
        a -= lr * ga / len(pairs)
        b -= lr * gb / len(pairs)
    def apply(p):
        z = min(max(p, 1e-6), 1 - 1e-6)
        x = math.log(z / (1 - z))
        return 1 / (1 + math.exp(-(a * x + b)))
    return apply, (a, b)


def fit_isotonic(pairs):
    """Pool-adjacent-violators. Monotone, non-parametric, needs more data."""
    pts = sorted(pairs)
    xs = [p for p, _ in pts]
    ys = [float(y) for _, y in pts]
    w = [1.0] * len(ys)
    i = 0
    while i < len(ys) - 1:
        if ys[i] <= ys[i + 1]:
            i += 1
            continue
        total_w = w[i] + w[i + 1]
        merged = (ys[i] * w[i] + ys[i + 1] * w[i + 1]) / total_w
        ys[i:i + 2] = [merged]
        w[i:i + 2] = [total_w]
        xs[i:i + 2] = [xs[i]]
        i = max(i - 1, 0)
    def apply(p):
        best = ys[0]
        for x, y in zip(xs, ys):
            if p >= x:
                best = y
            else:
                break
        return min(max(best, 1e-6), 1 - 1e-6)
    return apply, len(xs)


class Command(BaseCommand):
    help = 'READ-ONLY calibration evidence audit. Writes nothing.'

    def add_arguments(self, parser):
        parser.add_argument('--split', type=float, default=0.7,
                            help='Chronological train fraction (default 0.7)')
        parser.add_argument('--min-test', type=int, default=40,
                            help='Minimum test rows before reporting a method')

    def handle(self, *args, **options):
        out = self.stdout.write

        # ── dataset ──────────────────────────────────────────────────────────
        raw = list(
            PredictionLog.objects
            .filter(actual_outcome__isnull=False, was_correct__isnull=False)
            .only('fixture_id', 'market_type', 'predicted_outcome', 'confidence',
                  'kickoff', 'prediction_logged_at', 'league', 'was_correct',
                  'odds', 'pricing_integrity_status', 'is_audit_excluded',
                  'probability_home', 'probability_draw', 'probability_away')
        )
        out(f'candidate settled rows: {len(raw)}')

        excluded = Counter()
        rows = []
        for p in raw:
            if p.is_audit_excluded:
                excluded['audit_excluded'] += 1
                continue
            if p.confidence is None:
                excluded['no_confidence'] += 1
                continue
            if not p.kickoff or not p.prediction_logged_at:
                excluded['missing_timestamps'] += 1
                continue
            if p.prediction_logged_at >= p.kickoff:
                # First write already after kickoff — cannot have been available.
                excluded['logged_after_kickoff'] += 1
                continue
            conf = p.confidence if p.confidence <= 1 else p.confidence / 100
            if not (0.0 < conf < 1.0):
                excluded['confidence_out_of_range'] += 1
                continue
            rows.append({
                'fixture_id': p.fixture_id,
                'market': p.market_type or 'unknown',
                'outcome': p.predicted_outcome,
                'score': conf,
                'y': 1 if p.was_correct else 0,
                'kickoff': p.kickoff,
                'logged_at': p.prediction_logged_at,
                'league': p.league,
                'odds': p.odds,
                'pricing': p.pricing_integrity_status,
                'horizon_h': (p.kickoff - p.prediction_logged_at).total_seconds() / 3600,
            })

        out(f'excluded: {dict(excluded)}')
        out(f'usable rows: {len(rows)}')

        # One fixture must never appear twice.
        per_fixture = Counter(r['fixture_id'] for r in rows)
        dupes = {k: v for k, v in per_fixture.items() if v > 1}
        out(f'distinct fixtures: {len(per_fixture)}   fixtures with >1 row: {len(dupes)}')

        if not rows:
            out('NO USABLE ROWS — cannot evaluate.')
            return

        rows.sort(key=lambda r: r['kickoff'])
        out(f"kickoff span: {rows[0]['kickoff'].isoformat()} -> {rows[-1]['kickoff'].isoformat()}")

        out('')
        out('=== COVERAGE ===')
        out(f"by market: {dict(Counter(r['market'] for r in rows))}")
        out(f"by pricing integrity: {dict(Counter(r['pricing'] for r in rows))}")
        leagues = Counter(r['league'] for r in rows)
        out(f'leagues: {len(leagues)}  top: {leagues.most_common(6)}')
        hz = Counter()
        for r in rows:
            h = r['horizon_h']
            hz['<6h' if h < 6 else '6-24h' if h < 24 else '1-3d' if h < 72 else '>3d'] += 1
        out(f'by prediction horizon: {dict(hz)}')

        # ── per-market evaluation ────────────────────────────────────────────
        by_market = defaultdict(list)
        for r in rows:
            by_market[r['market']].append(r)
        by_market['ALL_POOLED'] = rows

        for market, mrows in sorted(by_market.items(), key=lambda kv: -len(kv[1])):
            out('')
            out(f'=== MARKET: {market}  (n={len(mrows)}) ===')
            pairs = [(r['score'], r['y']) for r in mrows]
            base = sum(y for _, y in pairs) / len(pairs)
            out(f'base rate (observed hit rate): {base:.4f}')
            out(f'raw Brier   : {brier(pairs):.5f}')
            out(f'raw log loss: {log_loss(pairs):.5f}')
            auc = discrimination(pairs)
            out(f'raw AUC     : {"n/a" if auc is None else f"{auc:.4f}"}')

            rel, ece = reliability(pairs)
            out(f'raw ECE     : {ece:.4f}')
            out('reliability  [lo,hi)     n   mean_score  observed   gap')
            for lo, hi, n, mp, ob, gap in rel:
                out(f'             [{lo:.2f},{hi:.2f})  {n:5d}   {mp:.4f}     {ob:.4f}   {gap:+.4f}')

            # Baselines on the same rows.
            const_pairs = [(base, y) for _, y in pairs]
            out(f'baseline base-rate Brier: {brier(const_pairs):.5f}  '
                f'log loss: {log_loss(const_pairs):.5f}')

            priced = [r for r in mrows if r['odds'] and r['odds'] > 1
                      and r['pricing'] == 'verified']
            out(f'rows with VERIFIED price for a market baseline: {len(priced)}')
            if len(priced) >= 30:
                mk = [(1 / r['odds'], r['y']) for r in priced]
                out(f'market-implied Brier: {brier(mk):.5f}  log loss: {log_loss(mk):.5f}')
            else:
                out('market baseline NOT computed — too few verified prices '
                    '(legacy rows carry contaminated odds).')

            # ── chronological calibration ────────────────────────────────────
            cut = int(len(mrows) * options['split'])
            train, test = mrows[:cut], mrows[cut:]
            if len(test) < options['min_test']:
                out(f'calibration SKIPPED — test partition {len(test)} < '
                    f"{options['min_test']}")
                continue

            # No fixture may cross the boundary.
            overlap = {r['fixture_id'] for r in train} & {r['fixture_id'] for r in test}
            assert not overlap, f'fixture leaked across split: {overlap}'
            assert train[-1]['kickoff'] <= test[0]['kickoff'], 'split not chronological'

            tr = [(r['score'], r['y']) for r in train]
            te = [(r['score'], r['y']) for r in test]
            out(f'chronological split: train={len(tr)} '
                f"(-> {train[-1]['kickoff'].date()})  test={len(te)} "
                f"({test[0]['kickoff'].date()} ->)")
            out(f'  raw       test Brier {brier(te):.5f}  log loss {log_loss(te):.5f}  '
                f'ECE {reliability(te)[1]:.4f}')

            tr_base = sum(y for _, y in tr) / len(tr)
            const_te = [(tr_base, y) for _, y in te]
            out(f'  base-rate test Brier {brier(const_te):.5f}  '
                f'log loss {log_loss(const_te):.5f}   (train base {tr_base:.4f})')

            platt, (a, b) = fit_platt(tr)
            pl = [(platt(p), y) for p, y in te]
            out(f'  Platt     test Brier {brier(pl):.5f}  log loss {log_loss(pl):.5f}  '
                f'ECE {reliability(pl)[1]:.4f}   (a={a:.3f} b={b:.3f})')

            iso, knots = fit_isotonic(tr)
            it = [(iso(p), y) for p, y in te]
            out(f'  Isotonic  test Brier {brier(it):.5f}  log loss {log_loss(it):.5f}  '
                f'ECE {reliability(it)[1]:.4f}   (knots={knots})')

            auc_raw = discrimination(te)
            auc_pl = discrimination(pl)
            out(f'  AUC raw {"n/a" if auc_raw is None else f"{auc_raw:.4f}"} -> '
                f'Platt {"n/a" if auc_pl is None else f"{auc_pl:.4f}"} '
                '(monotone calibration cannot change ranking)')
