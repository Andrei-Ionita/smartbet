"""
Classify every PredictionLog row's pricing-integrity status.

Idempotent and safe to re-run. Writes ONLY `pricing_integrity_status` — it
never alters odds, confidence, predictions or results, and it never deletes
anything.

Context: the 2026-07-29 audit found that predictions written before the
deterministic odds selector shipped were priced by substring matching across
~38 "2.5"-containing entries spanning seven SportMonks markets, so a full-time
Over 2.5 pick could carry a SECOND-HALF quote. SportMonks does not expose
historical point-in-time odds, so those prices cannot be reconstructed. They
are preserved but permanently excluded from public pricing statistics.

    python manage.py classify_pricing_integrity --dry-run
    python manage.py classify_pricing_integrity
"""
from collections import Counter

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import PredictionLog
from core.services import public_universe


class Command(BaseCommand):
    help = "Assign pricing_integrity_status to every PredictionLog row."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Report what would change without writing.',
        )

    def handle(self, *args, **options):
        dry = options['dry_run']
        rows = PredictionLog.objects.all().only(
            'id', 'odds', 'odds_provenance', 'prediction_logged_at',
            'is_audit_excluded', 'pricing_integrity_status',
        )

        before = Counter()
        after = Counter()
        changed = []

        for pred in rows.iterator(chunk_size=500):
            current = pred.pricing_integrity_status
            target = public_universe.classify_row(pred)
            before[current] += 1
            after[target] += 1
            if current != target:
                pred.pricing_integrity_status = target
                changed.append(pred)

        self.stdout.write(
            f'Cutoff: {public_universe.PRICING_INTEGRITY_CUTOFF.isoformat()}'
        )
        self.stdout.write(f'Scanned {sum(before.values())} rows\n')

        self.stdout.write('Resulting distribution:')
        for status, _label in PredictionLog.PRICING_INTEGRITY_CHOICES:
            self.stdout.write(f'  {status:24s} {after.get(status, 0):6d}')

        verified = after.get(PredictionLog.PRICING_VERIFIED, 0)
        self.stdout.write(f'\n{len(changed)} rows would change' if dry
                          else f'\n{len(changed)} rows changed')

        if not dry and changed:
            with transaction.atomic():
                PredictionLog.objects.bulk_update(
                    changed, ['pricing_integrity_status'], batch_size=500
                )

        if verified == 0:
            self.stdout.write(self.style.WARNING(
                '\nNo rows are pricing-verified. This is EXPECTED immediately '
                'after the odds fix: the public record restarts empty and '
                'accumulates as new picks settle. Public ROI will read "no '
                'verified results yet" until then — that is correct, not a bug.'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'\n{verified} rows are pricing-verified and eligible for '
                'public statistics.'
            ))
