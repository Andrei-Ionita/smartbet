"""Backfill historical signals into the retrospective Strategies Lab phase."""
import json
from collections import Counter

from django.core.management.base import BaseCommand

from core.models import SignalObservation, StrategyLabObservation
from core.services import strategy_lab


class Command(BaseCommand):
    help = (
        'Register strategy hypotheses, materialise immutable historical signal '
        'evidence as retrospective only, settle it, and print the private report.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-settle', action='store_true',
            help='Materialise observations without grading available results.',
        )
        parser.add_argument(
            '--compact', action='store_true',
            help='Print one compact JSON line instead of indented JSON.',
        )

    def handle(self, *args, **options):
        experiments = strategy_lab.ensure_all_experiments()
        materialised = Counter()
        # Only evidence that predates registration is retrospective. Running
        # this command again months later must never clone forward observations
        # into a backtest phase.
        for experiment in experiments:
            definition = strategy_lab.DEFINITION_BY_KEY.get((
                experiment.strategy_key, experiment.version,
            ))
            if not definition:
                continue
            summary = strategy_lab.capture_signal_observations(
                SignalObservation.objects.filter(
                    market=experiment.market,
                    created_at__lt=experiment.created_at,
                ).iterator(),
                phase=StrategyLabObservation.PHASE_RETROSPECTIVE,
                ingestion_run_id='strategy-lab-retrospective-v2',
                definitions=[definition],
            )
            materialised.update(summary)
        settlement = None
        if not options['no_settle']:
            settlement = strategy_lab.settle()
        payload = {
            'materialised': dict(materialised),
            'settlement': settlement,
            'report': strategy_lab.build_report(),
        }
        self.stdout.write(json.dumps(
            payload,
            sort_keys=True,
            indent=None if options['compact'] else 2,
        ))
