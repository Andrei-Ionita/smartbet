"""READ-ONLY evidence accumulation report. Writes nothing.

Answers one operational question: is the evidence base actually growing, and is
it growing in the shape a calibration study needs?
"""
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.models import Min, Max
from django.utils import timezone

from core.models import PredictionLog, SignalObservation

# Target horizons for decision construction, with tolerance (hours).
HORIZONS = [(72, 12), (24, 6), (6, 2), (1, 0.5)]


class Command(BaseCommand):
    help = 'READ-ONLY signal-evidence accumulation report.'

    def handle(self, *args, **options):
        out = self.stdout.write
        qs = SignalObservation.objects.all()
        total = qs.count()
        out(f'AUDIT_AT_UTC {timezone.now().isoformat()}')
        out(f'observations: {total}')
        if not total:
            out('no evidence captured yet')
            return

        span = qs.aggregate(a=Min('observed_at'), b=Max('observed_at'))
        out(f"observed_at span: {span['a'].isoformat()} -> {span['b'].isoformat()}")
        out(f"unique fixtures: {qs.values('fixture_id').distinct().count()}")
        out(f"ingestion runs: {qs.values('ingestion_run_id').distinct().count()}")

        out('')
        out('=== COVERAGE ===')
        out(f"by market: {dict(Counter(qs.values_list('market', flat=True)))}")
        out(f"by market/outcome: {dict(Counter(qs.values_list('market', 'outcome')))}")
        out(f"complete provider vectors: {qs.filter(vector_complete=True).count()} / {total}")
        out(f"verified price on the outcome: {qs.filter(price_status='verified').count()} / {total}")
        out(f"COMPLETE price vector (de-vig possible): "
            f"{qs.filter(price_vector_complete=True).count()} / {total}")
        out(f"missing provenance: {qs.filter(provenance_complete=False).count()} / {total}")
        out(f"post-kickoff (excluded from decisions): "
            f"{qs.filter(hours_to_kickoff__lt=0).count()}")

        # Vector-sum sanity: a vector that does not sum to ~1 must not be
        # silently treated as a probability distribution.
        sums = list(qs.values_list('market', 'vector_sum'))
        by_market_sum = {}
        for market, s in sums:
            by_market_sum.setdefault(market, []).append(s)
        out('')
        out('=== VECTOR SUMS (is this a distribution at all?) ===')
        for market, values in sorted(by_market_sum.items()):
            mean = sum(values) / len(values)
            near_one = sum(1 for v in values if 0.98 <= v <= 1.02)
            out(f'  {market:16s} n={len(values):5d}  mean={mean:.4f}  '
                f'within 1%±2pp: {near_one}/{len(values)}')

        out('')
        out('=== EVALUATION DECISIONS (fixture x market x horizon) ===')
        out('Hourly rows are NOT decisions. One decision per horizon, using the '
            'latest valid observation at or before the target.')
        rows = list(qs.filter(hours_to_kickoff__gte=0)
                    .values_list('fixture_id', 'market', 'hours_to_kickoff'))
        decisions = 0
        per_h = Counter()
        keys = {(f, m) for f, m, _ in rows}
        for fixture_id, market in keys:
            hs = [h for f, m, h in rows if f == fixture_id and m == market]
            for target, tol in HORIZONS:
                if any(target - tol <= h <= target + tol for h in hs):
                    decisions += 1
                    per_h[f'{target}h'] += 1
        out(f'raw observations (pre-kickoff): {len(rows)}')
        out(f'unique fixture x market: {len(keys)}')
        out(f'evaluation decisions: {decisions}   by horizon: {dict(per_h)}')
        if len(keys):
            out(f'repetition factor (rows per fixture-market): '
                f'{len(rows) / len(keys):.1f}x  — this is the correlation a naive '
                f'row count would hide')

        out('')
        out('=== CLOSING PRICE ===')
        closing = qs.filter(hours_to_kickoff__gte=0, price_status='verified')
        out(f'observations with a verified pre-kickoff price: {closing.count()}')
        ages = sorted(closing.values_list('hours_to_kickoff', flat=True))
        if ages:
            def pct(p):
                return ages[min(int(len(ages) * p), len(ages) - 1)]
            out(f'closing-age distribution (h to kickoff): '
                f'min={ages[0]:.2f} p25={pct(0.25):.2f} median={pct(0.5):.2f} '
                f'p75={pct(0.75):.2f} max={ages[-1]:.2f}')
            out('A usable closing price needs the LAST valid quote strictly '
                'before kickoff; hourly cadence bounds freshness at ~1h.')

        out('')
        out('=== RESULT EVIDENCE ===')
        from core.models import FixtureResultObservation
        from core.services import result_evidence

        rows = FixtureResultObservation.objects.all()
        canonical = result_evidence.canonical_results()
        obs_fixtures = set(qs.values_list('fixture_id', flat=True))
        past = set(qs.filter(kickoff__lt=timezone.now())
                   .values_list('fixture_id', flat=True))

        out(f'result observations: {rows.count()} '
            f'(versions>1: {rows.filter(result_version__gt=1).count()})')
        out(f'observed fixtures awaiting kickoff: {len(obs_fixtures - past)}')
        out(f'observed fixtures past kickoff: {len(past)}')
        out(f'past kickoff WITHOUT any result: {len(past - set(canonical))}')
        out(f'provisional (final, unconfirmed): '
            f'{sum(1 for r in canonical.values() if r.is_final and not r.confirmed)}')
        out(f'confirmed finals: '
            f'{sum(1 for r in canonical.values() if r.confirmed)}')
        out(f'corrected results: '
            f'{sum(1 for r in canonical.values() if r.is_correction)}')
        out(f'scoreable: {sum(1 for r in canonical.values() if r.is_scoreable)}')
        out(f"statuses: {dict(Counter(r.provider_status for r in canonical.values()))}")
        ambiguous = Counter(r.ineligible_reason for r in canonical.values()
                            if not r.is_scoreable and r.ineligible_reason)
        out(f'non-scoreable reasons: {dict(ambiguous)}')
        if canonical:
            lat = [(r.captured_at - r.kickoff).total_seconds() / 3600
                   for r in canonical.values()]
            lat.sort()
            out(f'result-capture latency after kickoff (h): '
                f'min={lat[0]:.1f} median={lat[len(lat) // 2]:.1f} max={lat[-1]:.1f}')
        out(f"results by league: "
            f"{dict(Counter(r.league for r in canonical.values()).most_common(8))}")

        out('')
        out('=== VARIANT COVERAGE ===')
        out(f'Variant A (raw provider): {total}/{total} — always present')
        vb = qs.filter(variant_b_available=True).count()
        out(f'Variant B (current heuristic): {vb}/{total}')
        missing = Counter(qs.exclude(variant_b_missing_reason='')
                          .values_list('variant_b_missing_reason', flat=True))
        out(f'Variant B missing reasons: {dict(missing)}')
        out(f'Variant D (de-vig eligible, complete price vector): '
            f'{qs.filter(price_vector_complete=True).count()}/{total}')

        out('')
        out('=== SETTLED COVERAGE ==='  )
        settled = set(
            PredictionLog.objects
            .filter(actual_outcome__isnull=False)
            .values_list('fixture_id', flat=True)
        )
        obs_fixtures = set(qs.values_list('fixture_id', flat=True))
        out(f'observed fixtures with a settled outcome: '
            f'{len(obs_fixtures & settled)} / {len(obs_fixtures)}')
        out('Outcomes still come from PredictionLog, which stores only the '
            'SELECTED market per fixture — so non-selected markets have no '
            'outcome source yet. That is the next gap to close.')
