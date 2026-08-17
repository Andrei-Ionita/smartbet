"""Append-only evidence capture. Scheduler stage 5.

Writes SignalObservation rows and nothing else. A failure here must not affect
predictions, snapshots, claims or settlement — the scheduler's run_task()
already isolates per-stage exceptions, and this command adds no writes outside
its own table.
"""
from django.core.management.base import BaseCommand

from core.services import evidence_capture


class Command(BaseCommand):
    help = 'Capture private signal and strategy evidence (append-only).'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=5,
                            help='Fixture window to sweep (default 5)')
        parser.add_argument('--dry-run', action='store_true',
                            help='Fetch and report without writing')

    def handle(self, *args, **options):
        out = self.stdout.write
        try:
            payload = evidence_capture.fetch_evidence(days=options['days'])
        except Exception as exc:
            # Surfaced, not swallowed: the scheduler logs it and the heartbeat
            # keeps its own counters honest.
            out(self.style.ERROR(f'evidence fetch failed: {exc}'))
            raise

        out(f"feed: {payload.get('candidate_count')} candidates across "
            f"{payload.get('fixtures_seen')} fixtures")

        if options['dry_run']:
            out('dry run — nothing written')
            return

        summary = evidence_capture.capture(payload)
        out(f"run {summary['ingestion_run_id']}: "
            f"{summary['written']} appended, "
            f"{summary['skipped_duplicate']} duplicate, "
            f"{summary['invalid']} invalid, "
            f"{summary['post_kickoff']} post-kickoff, "
            f"{summary['fixtures']} fixtures")
