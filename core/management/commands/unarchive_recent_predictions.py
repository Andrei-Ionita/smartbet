"""
Clear the 'archived' flag from fixtures that were never actually archived.

WHY THIS EXISTS
---------------
`update_results` marked a prediction `match_status='archived'` whenever the
provider returned 404, and the pending query then excluded archived rows
forever. The provider call was itself malformed — SportMonks v3 wants
semicolon-separated includes and we sent commas — so it failed for every
fixture, and every past-kickoff row got permanently flagged.

On 2026-08-09 that was all 17 of them, including Cardiff City v Swindon Town,
which had kicked off the previous evening. No published claim could settle,
and the verified record was structurally frozen at zero while appearing merely
patient ("16 awaiting a provider result").

Fixing the request and the archive rule stops it recurring, but the rows
already poisoned stay excluded until their flag is cleared. That is this
command.

SAFETY
------
Only rows that are STILL INSIDE the result-lookback window are touched, and
only when they carry no outcome — a genuinely aged-out fixture keeps its flag,
and no graded row is ever altered. Nothing here writes a result; it only makes
rows eligible to be asked about again.

    python manage.py unarchive_recent_predictions --dry-run
    python manage.py unarchive_recent_predictions
"""
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import PredictionLog
from core.services.result_updater import ResultUpdaterService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = ("Clear 'archived' from predictions still inside the result "
            "lookback window so they can be settled.")

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Report what would be cleared, write nothing.')

    def handle(self, *args, **options):
        dry = options['dry_run']
        cutoff = timezone.now() - timedelta(days=ResultUpdaterService.MAX_LOOKBACK_DAYS)

        stuck = PredictionLog.objects.filter(
            match_status='archived',
            actual_outcome__isnull=True,
            kickoff__gte=cutoff,
        ).order_by('kickoff')

        count = stuck.count()
        if not count:
            self.stdout.write('  nothing to clear — no recent row is archived')
            return

        for row in stuck[:50]:
            self.stdout.write(
                f'  {row.fixture_id} {row.home_team} v {row.away_team} '
                f'(kickoff {row.kickoff:%Y-%m-%d %H:%M})'
            )
        if count > 50:
            self.stdout.write(f'  ... and {count - 50} more')

        if dry:
            self.stdout.write(f'\nwould clear {count} wrongly-archived row(s)')
            return

        # .update() bypasses the model's save() invariants deliberately: we are
        # clearing a status flag, not revalidating odds or EV on these rows.
        cleared = stuck.update(match_status=None)
        logger.warning('Cleared archived flag from %s recent predictions', cleared)
        self.stdout.write(self.style.SUCCESS(
            f'\ncleared {cleared} wrongly-archived row(s) — they will be '
            f'retried on the next result update'))
