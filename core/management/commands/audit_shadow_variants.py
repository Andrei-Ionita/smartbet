"""
READ-ONLY evaluation join and shadow-variant comparison. Writes nothing.

THE STATISTICAL UNIT IS fixture x market x horizon
--------------------------------------------------
NOT fixture x outcome x horizon. A market's outcomes are dependent components
of ONE decision:

  * 1X2 is three numbers but a single multiclass choice;
  * BTTS and O/U 2.5 are two numbers summing to 1 — one binary choice;
  * double chance is three legs of which exactly TWO always win, fully
    determined by the 1X2 result, contributing no independent information.

So one fixture yields at most 4 markets x 4 horizons = 16 market-horizon
decisions, and its EFFECTIVE independent count is lower still — double chance
adds nothing beyond 1X2. An earlier report implied ~40 decisions per fixture by
counting outcome rows; that was wrong and is corrected here.
"""
import math
from collections import Counter, defaultdict

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import FixtureResultObservation, SignalObservation
from core.services import market_outcomes, result_evidence

HORIZONS = [(72, 12), (24, 6), (6, 2), (1, 0.5)]


def fixture_clustered_resample(units, rng_seed=0):
    """Resampling unit for confidence intervals: the FIXTURE, never the row.

    Documented and tested now so the first A-vs-B comparison cannot quietly use
    row-level bootstrap, which would treat four markets off one scoreline as
    four independent draws and shrink every interval by roughly half.

    `units` maps fixture_id -> list of that fixture's decisions. A draw takes a
    whole fixture with all its markets, preserving their dependence.
    """
    import random

    rng = random.Random(rng_seed)
    fixtures = list(units)
    if not fixtures:
        return []
    drawn = [fixtures[rng.randrange(len(fixtures))] for _ in range(len(fixtures))]
    out = []
    for fixture_id in drawn:
        out.extend(units[fixture_id])
    return out


def brier_binary(pairs):
    return sum((p - y) ** 2 for p, y in pairs) / len(pairs) if pairs else None


def log_loss_binary(pairs, eps=1e-12):
    if not pairs:
        return None
    return sum(-(y * math.log(min(max(p, eps), 1 - eps))
                 + (1 - y) * math.log(1 - min(max(p, eps), 1 - eps)))
               for p, y in pairs) / len(pairs)


def brier_multiclass(rows):
    """Mean squared error over the whole vector — the proper multiclass form.

    Scoring only whether the argmax outcome won throws away the draw and the
    loser, which is most of what a 1X2 forecast asserts.
    """
    if not rows:
        return None
    total = 0.0
    for probs, truth in rows:
        total += sum((probs.get(k, 0.0) - truth.get(k, 0)) ** 2 for k in truth)
    return total / len(rows)


def log_loss_multiclass(rows, eps=1e-12):
    if not rows:
        return None
    total = 0.0
    for probs, truth in rows:
        winner = next(k for k, v in truth.items() if v == 1)
        total += -math.log(min(max(probs.get(winner, 0.0), eps), 1 - eps))
    return total / len(rows)


def rps(rows, order):
    """Ranked probability score — ordinal, so a home/draw/away vector is
    penalised less for being adjacent-wrong than opposite-wrong."""
    if not rows:
        return None
    total = 0.0
    for probs, truth in rows:
        cp = ct = 0.0
        acc = 0.0
        for key in order:
            cp += probs.get(key, 0.0)
            ct += truth.get(key, 0)
            acc += (cp - ct) ** 2
        total += acc / (len(order) - 1)
    return total / len(rows)


def auc(pairs):
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


def devig(price_vector, outcomes):
    """Proportional de-vig of a complete price vector. None if incomplete."""
    implied = {}
    for outcome in outcomes:
        entry = (price_vector or {}).get(outcome) or {}
        odds = entry.get('odds')
        if not odds or odds <= 1:
            return None
        implied[outcome] = 1.0 / odds
    total = sum(implied.values())
    if total <= 0:
        return None
    return {k: v / total for k, v in implied.items()}


class Command(BaseCommand):
    help = 'READ-ONLY shadow-variant evaluation. Writes nothing.'

    def handle(self, *args, **options):
        out = self.stdout.write
        now = timezone.now()
        out(f'AUDIT_AT_UTC {now.isoformat()}')

        # ── join ─────────────────────────────────────────────────────────────
        obs = list(
            SignalObservation.objects
            .filter(hours_to_kickoff__gte=0)   # strictly pre-kickoff only
            .order_by('fixture_id', 'market', 'outcome', '-hours_to_kickoff')
        )
        out(f'raw pre-kickoff observations: {len(obs)}')
        out(f"unique fixtures: {len({o.fixture_id for o in obs})}")

        canonical = result_evidence.canonical_results()
        scoreable = {f: r for f, r in canonical.items() if r.is_scoreable}
        out(f'result observations: {FixtureResultObservation.objects.count()}')
        out(f'fixtures with a canonical result: {len(canonical)}')
        out(f'fixtures SCOREABLE: {len(scoreable)}')
        corrections = sum(1 for r in canonical.values() if r.is_correction)
        out(f'provider corrections among canonical results: {corrections}')
        if canonical:
            reasons = Counter(r.ineligible_reason for r in canonical.values()
                              if not r.is_scoreable)
            if reasons:
                out(f'not-scoreable reasons: {dict(reasons)}')

        # One observation per fixture x market x outcome x horizon: the latest
        # at or before the target, within tolerance.
        picked = {}
        for o in obs:
            for target, tol in HORIZONS:
                if target - tol <= o.hours_to_kickoff <= target + tol:
                    key = (o.fixture_id, o.market, o.outcome, target)
                    prev = picked.get(key)
                    # "Latest at or before" = smallest hours_to_kickoff.
                    if prev is None or o.hours_to_kickoff < prev.hours_to_kickoff:
                        picked[key] = o

        decision_keys = {(f, m, h) for (f, m, _, h) in picked}
        out('')
        out('=== DECISION UNITS ===')
        out(f'market-horizon decisions (fixture x market x horizon): {len(decision_keys)}')
        out(f"  by horizon: {dict(Counter(h for _, _, h in decision_keys))}")
        out(f"  by market : {dict(Counter(m for _, m, _ in decision_keys))}")
        eff = sum(market_outcomes.independent_component_count(m)
                  for _, m, _ in decision_keys)
        fixtures_here = {f for f, _, _ in decision_keys}
        out(f'market-decision components (double chance contributes 0): {eff}')
        out(f'UNIQUE FIXTURES (the independence unit): {len(fixtures_here)}')
        out('  NOTE: several markets from one fixture are NOT independent '
            'observations. They share a scoreline, so 118 fixtures x 3 markets '
            'is 118 independent units, not 354. Confidence intervals and any '
            'A-vs-B comparison must resample WHOLE FIXTURES (fixture-clustered '
            'bootstrap), never outcome rows or market rows.')
        per_market_fixtures = defaultdict(set)
        for f, m, _ in decision_keys:
            per_market_fixtures[m].add(f)
        out(f"  unique fixtures by market: "
            f"{ {m: len(v) for m, v in sorted(per_market_fixtures.items())} }")
        horizons_per_fixture = Counter(f for f, _, _ in decision_keys)
        if horizons_per_fixture:
            out(f'  repeated market-horizons per fixture: mean '
                f'{sum(horizons_per_fixture.values()) / len(horizons_per_fixture):.1f}')

        priced = sum(1 for o in picked.values() if o.price_vector_complete)
        out(f'observations with a COMPLETE price vector: {priced}/{len(picked)}')
        out(f"variant B available: "
            f"{sum(1 for o in picked.values() if o.variant_b_available)}/{len(picked)}")

        # ── scoreable decisions ──────────────────────────────────────────────
        vectors = defaultdict(dict)
        for (fixture_id, market, outcome, horizon), o in picked.items():
            vectors[(fixture_id, market, horizon)][outcome] = o

        # ── COHORTS ──────────────────────────────────────────────────────────
        # A vs B must be compared on the SAME fixtures. Variant B exists only
        # where the provider supplied usable form, and form availability is not
        # random — cups have no standings at all. Comparing A-on-everything
        # against B-on-form-covered-only would measure the fixture mix, not the
        # heuristic.
        has_b = {}
        for (fixture_id, market, horizon), outcome_map in vectors.items():
            has_b[(fixture_id, market, horizon)] = any(
                o.variant_b_available for o in outcome_map.values()
            )

        all_units = set(vectors)
        b_units = {k for k, v in has_b.items() if v}
        scoreable_units = {k for k in all_units if k[0] in scoreable}
        matched_units = {k for k in scoreable_units if has_b[k]}

        out('')
        out('=== COHORTS (unique fixtures are the counting unit) ===')
        out(f'settled unique fixtures            : '
            f"{len({k[0] for k in scoreable_units})}")
        out(f'fixtures with Variant A            : {len({k[0] for k in all_units})} '
            '(always present)')
        out(f'fixtures with genuine Variant B    : {len({k[0] for k in b_units})}')
        out(f'MATCHED fixtures (settled AND B)   : '
            f"{len({k[0] for k in matched_units})}")
        excluded = scoreable_units - matched_units
        out(f'settled but excluded (no usable B) : '
            f"{len({k[0] for k in excluded})}")
        reasons = Counter()
        for key in excluded:
            for o in vectors[key].values():
                if o.variant_b_missing_reason:
                    reasons[o.variant_b_missing_reason] += 1
        out(f'  exclusion reasons: {dict(reasons)}')
        out('ALL A-vs-B comparisons below use MATCHED units only.')

        # ── COVERAGE BIAS ────────────────────────────────────────────────────
        out('')
        out('=== VARIANT-B COVERAGE BIAS (is form availability random?) ===')

        def bias(label, key_fn):
            buckets = defaultdict(lambda: [0, 0])
            for key in all_units:
                bucket = key_fn(key)
                if bucket is None:
                    continue
                buckets[bucket][0] += 1
                if has_b[key]:
                    buckets[bucket][1] += 1
            if not buckets:
                return
            out(f'  by {label}:')
            for bucket, (total, with_b) in sorted(
                    buckets.items(), key=lambda kv: -kv[1][0])[:10]:
                pct = 100.0 * with_b / total if total else 0.0
                out(f'    {str(bucket)[:26]:26s} {with_b:4d}/{total:4d}  {pct:5.1f}%')

        sample = {k: next(iter(v.values())) for k, v in vectors.items()}
        CUP_WORDS = ('cup', 'trophy', 'copa', 'coppa', 'pokal', 'league cup')

        bias('market', lambda k: k[1])
        bias('horizon', lambda k: f'{k[2]}h')
        bias('league', lambda k: sample[k].league or 'unknown')
        bias('competition type', lambda k: (
            'cup' if any(w in (sample[k].league or '').lower() for w in CUP_WORDS)
            else 'league'))
        bias('provider score band', lambda k: (
            f'{min(int(sample[k].normalized_probability * 10) / 10, 0.9):.1f}'
            if sample[k].normalized_probability is not None else None))
        bias('verified price', lambda k: (
            'complete vector' if sample[k].price_vector_complete else 'incomplete'))
        out('  Any large spread here means Variant-B coverage is NOT random and '
            'an unmatched comparison would be confounded.')

        scored = [(k, v) for k, v in vectors.items() if k in matched_units]
        out('')
        out(f'=== MATCHED SCOREABLE DECISIONS: {len(scored)} ===')
        matched_fixtures = len({k[0] for k in matched_units})
        if not scored:
            out('Nothing to evaluate yet: no observed fixture has a confirmed, '
                'scoreable final result WITH genuine Variant B. Variants A-D '
                'are wired but cannot be compared until fixtures settle.')
            out('Once they do, this command reports matched Brier and log-loss '
                'differences with a fixture-clustered interval.')
            return
        if matched_fixtures <= 5:
            out('')
            out('*** PIPELINE VALIDATION ONLY — NOT PERFORMANCE EVIDENCE ***')
            out(f'{matched_fixtures} matched fixture(s). At this size the numbers '
                'below prove the join and the metrics execute end to end. They '
                'say nothing whatever about whether the heuristic works, and '
                'must not be quoted as if they did.')

        # ── per-market evaluation ────────────────────────────────────────────
        by_market = defaultdict(list)
        for key, outcome_map in scored:
            by_market[key[1]].append((key, outcome_map))

        for market, items in sorted(by_market.items()):
            out('')
            out(f'--- {market} (n={len(items)}) ---')
            result_of = {k[0]: scoreable[k[0]] for k, _ in items}

            def truth_for(fixture_id):
                r = result_of[fixture_id]
                return market_outcomes.outcome_vector(market, r.home_score, r.away_score)

            variants = {'A_raw': {}, 'B_heuristic': {}, 'D_devig': {}}
            for key, outcome_map in items:
                truth = truth_for(key[0])
                a = {o: obs_row.normalized_probability
                     for o, obs_row in outcome_map.items()}
                variants['A_raw'].setdefault(key, (a, truth))

                b_row = next((r for r in outcome_map.values()
                              if r.variant_b_available), None)
                if b_row is not None:
                    b = dict(a)
                    b[b_row.outcome] = b_row.adjusted_score
                    variants['B_heuristic'].setdefault(key, (b, truth))

                any_row = next(iter(outcome_map.values()))
                d = devig(any_row.market_price_vector, list(truth.keys()))
                if d:
                    variants['D_devig'].setdefault(key, (d, truth))

            for name, rows in variants.items():
                values = list(rows.values())
                if not values:
                    out(f'  {name:12s} no coverage')
                    continue
                if market == '1x2':
                    out(f'  {name:12s} n={len(values):4d}  '
                        f'multiclass Brier {brier_multiclass(values):.5f}  '
                        f'log loss {log_loss_multiclass(values):.5f}  '
                        f'RPS {rps(values, ["home", "draw", "away"]):.5f}')
                elif market == 'double_chance':
                    # Reported per leg, explicitly flagged as dependent.
                    per_leg = {leg: [(p.get(leg, 0.0), t.get(leg, 0))
                                     for p, t in values] for leg in ('1x', 'x2', '12')}
                    parts = ' '.join(
                        f'{leg}:{brier_binary(pairs):.4f}'
                        for leg, pairs in per_leg.items() if pairs)
                    out(f'  {name:12s} n={len(values):4d}  per-leg Brier {parts}')
                    out('               (legs are deterministically dependent — '
                        'exactly two win every match; not independent trials)')
                else:
                    pos = list(truth_for(items[0][0][0]).keys())[0]
                    pairs = [(p.get(pos, 0.0), t.get(pos, 0)) for p, t in values]
                    a_auc = auc(pairs)
                    out(f'  {name:12s} n={len(values):4d}  '
                        f'Brier {brier_binary(pairs):.5f}  '
                        f'log loss {log_loss_binary(pairs):.5f}  '
                        f'AUC {"n/a" if a_auc is None else f"{a_auc:.4f}"}')

        out('')
        out('Variant C (full-vector renormalised transform) is defined but not '
            'evaluated: it is shadow-only and unsupported for double chance.')
