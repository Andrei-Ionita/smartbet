"""Read-only forward evaluation of the provider-native value strategy.

The strategy is evaluated only from append-only SignalObservation rows carrying
the provider context that was available before kickoff.  Nothing is rebuilt
from present-day API responses, so a league rating or value flag cannot leak
backwards into an old decision.
"""
from collections import Counter
from math import sqrt

from django.core.management.base import BaseCommand

from core.models import SignalObservation
from core.services import market_outcomes, result_evidence


def wilson_interval(wins, total, z=1.96):
    if not total:
        return None
    p = wins / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    spread = z * sqrt((p * (1 - p) + z * z / (4 * total)) / total) / denom
    return max(0.0, centre - spread), min(1.0, centre + spread)


class Command(BaseCommand):
    help = 'READ-ONLY out-of-sample audit of value-strategy observations.'

    def add_arguments(self, parser):
        parser.add_argument('--horizon', type=float, default=6.0)
        parser.add_argument('--tolerance', type=float, default=4.0)
        parser.add_argument('--minimum-evidence', type=int, default=30)

    def handle(self, *args, **options):
        out = self.stdout.write
        target = options['horizon']
        tolerance = options['tolerance']

        rows = list(
            SignalObservation.objects
            .filter(
                market='1x2',
                is_selected_outcome=True,
                hours_to_kickoff__gte=max(0, target - tolerance),
                hours_to_kickoff__lte=target + tolerance,
            )
            .exclude(provider_context={})
            .order_by('fixture_id', 'hours_to_kickoff')
        )

        # Closest observation to the target horizon, one decision per fixture.
        selected = {}
        for row in rows:
            previous = selected.get(row.fixture_id)
            if previous is None or abs(row.hours_to_kickoff - target) < abs(
                    previous.hours_to_kickoff - target):
                selected[row.fixture_id] = row

        canonical = result_evidence.canonical_results()
        decisions = []
        rejected = Counter()
        missing_context = 0

        for fixture_id, row in selected.items():
            result = canonical.get(fixture_id)
            if result is None or not result.is_scoreable:
                continue
            evaluation = (row.provider_context or {}).get('strategy_evaluation')
            if not isinstance(evaluation, dict):
                missing_context += 1
                continue
            if not evaluation.get('eligible'):
                reasons = evaluation.get('rejectionReasons') or ['unspecified']
                rejected.update(reasons)
                continue

            truth = market_outcomes.outcome_vector(
                '1x2', result.home_score, result.away_score,
            )
            won = bool(truth.get(row.outcome))
            profit = (row.odds - 1.0) if won and row.odds and row.odds > 1 else -1.0
            decisions.append((row.kickoff, won, profit, row))

        decisions.sort(key=lambda item: item[0])
        n = len(decisions)
        wins = sum(1 for _, won, _, _ in decisions if won)
        profit = sum(item[2] for item in decisions)
        interval = wilson_interval(wins, n)

        out(f'value strategy audit at {target:g}h ± {tolerance:g}h')
        out(f'candidate fixtures at horizon: {len(selected)}')
        out(f'scoreable eligible decisions: {n}')
        out(f'missing recorded strategy context: {missing_context}')
        out(f'top rejection reasons: {rejected.most_common(12)}')

        if not n:
            out('NO FORWARD EVIDENCE YET. The pipeline is ready; no eligible '
                'recorded fixture at this horizon has settled.')
            return

        out(f'wins: {wins}/{n} ({wins / n:.1%})')
        out(f'flat-stake profit: {profit:+.3f} units; ROI {profit / n:+.1%}')
        out('95% Wilson hit-rate interval: '
            f'{interval[0]:.1%} to {interval[1]:.1%}')

        split = n // 2
        if split:
            halves = [('earlier', decisions[:split]), ('later', decisions[split:])]
            for label, part in halves:
                part_wins = sum(1 for _, won, _, _ in part if won)
                part_profit = sum(item[2] for item in part)
                out(f'{label:7s}: n={len(part):3d}  hit={part_wins / len(part):.1%}  '
                    f'ROI={part_profit / len(part):+.1%}')

        if n < options['minimum_evidence']:
            out('*** PIPELINE VALIDATION ONLY — TOO FEW INDEPENDENT FIXTURES TO '
                'CLAIM THE STRATEGY WORKS. ***')
        else:
            out('Evidence threshold reached. Interpret ROI with its time split '
                'and interval; do not select a new filter on this same sample.')
