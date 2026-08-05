"""Append-only result evidence capture. Scheduler stage 6.

Works from SignalObservation's fixture universe, never PredictionLog. Writes
only FixtureResultObservation rows: no settlement, no publication, no change to
any prediction.
"""
from django.core.management.base import BaseCommand

from core.services import result_evidence


class Command(BaseCommand):
    help = 'Capture provider fixture results for observed fixtures (append-only).'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=500)
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        out = self.stdout.write

        pending = result_evidence.fixtures_needing_results(limit=options['limit'])
        out(f'fixtures past kickoff needing a result: {len(pending)}')
        if not pending:
            out('nothing to fetch')
            return

        fixtures = result_evidence.fetch_results(pending)
        out(f'provider returned {len(fixtures)} fixtures')

        if options['dry_run']:
            for fixture in fixtures[:10]:
                state = (fixture.get('state') or {}).get('state')
                out(f"  {fixture.get('id')} status={state}")
            out('dry run — nothing written')
            return

        summary = result_evidence.capture(fixtures)
        out(f"run {summary['ingestion_run_id']}: "
            f"{summary['written']} appended, "
            f"{summary['duplicate']} duplicate, "
            f"{summary['confirmed']} confirmed, "
            f"{summary['corrections']} corrections, "
            f"{summary['invalid']} invalid")
