"""
Settle published claims whose fixtures have finished.

This is the missing half of the lifecycle: `update_results` fetches third-party
scores and grades the latest-state PredictionLog rows (via
`PredictionLog.calculate_performance`, which owns ALL market grading), and this
command turns those graded results into immutable PublishedClaimResult records.

It contains NO grading logic of its own — it delegates entirely to
`claim_publication.settle_published_claim`, which reads the graded prediction.
Duplicating market grading here is exactly the divergence that produced the
2026-07-29 defect.

Idempotent and safe to re-run: a claim already settled with the same status is a
no-op, and a contradictory status is refused rather than applied.

    python manage.py settle_published_claims --dry-run
    python manage.py settle_published_claims
"""
import logging

from django.core.management.base import BaseCommand

from core.models import PublishedClaim
from core.services import claim_publication

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Record settlement for published claims whose fixtures have finished.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Report what would settle without writing.')
        parser.add_argument('--max', type=int, default=200,
                            help='Maximum claims to process in one run.')

    def handle(self, *args, **options):
        dry = options['dry_run']
        limit = options['max']

        pending = (
            PublishedClaim.objects
            .filter(result__isnull=True)
            .select_related('prediction')
            .order_by('kickoff')[:limit]
        )

        settled = skipped = failed = 0
        for claim in pending:
            status = claim_publication.derive_settlement(claim)
            if status is None:
                # The provider has not returned a usable result yet. Leave the
                # claim PENDING — never guess.
                skipped += 1
                continue

            if dry:
                self.stdout.write(
                    f'  would settle {claim.claim_id} -> {status} '
                    f'({claim.home_team} v {claim.away_team})'
                )
                settled += 1
                continue

            try:
                claim_publication.settle_published_claim(claim)
                settled += 1
                self.stdout.write(self.style.SUCCESS(
                    f'  settled {claim.claim_id} -> {status} '
                    f'({claim.home_team} v {claim.away_team})'
                ))
            except claim_publication.SettlementError as exc:
                failed += 1
                # A contradictory settlement is a data-integrity signal, not a
                # transient error — surface it loudly.
                logger.error('Settlement refused for claim %s: %s',
                             claim.claim_id, exc)
                self.stdout.write(self.style.ERROR(
                    f'  REFUSED {claim.claim_id}: {exc}'
                ))

        # ── Divergence check ──────────────────────────────────────────────
        # An already-settled claim is never re-settled, but if the provider now
        # implies a DIFFERENT outcome that is a data-integrity signal and must be
        # surfaced, not silently ignored. Nothing is rewritten either way.
        diverged = 0
        for claim in (PublishedClaim.objects
                      .filter(result__isnull=False)
                      .select_related('prediction', 'result')[:limit]):
            implied = claim_publication.derive_settlement(claim)
            if implied is not None and implied != claim.result.status:
                diverged += 1
                logger.error(
                    'Settlement divergence on claim %s: recorded %s, provider '
                    'now implies %s. Claim left unchanged.',
                    claim.claim_id, claim.result.status, implied,
                )
                self.stdout.write(self.style.ERROR(
                    f'  REFUSED (divergence) {claim.claim_id}: recorded '
                    f'{claim.result.status}, provider now implies {implied} — '
                    f'claim left unchanged'
                ))

        verb = 'would settle' if dry else 'settled'
        self.stdout.write(
            f'\n{verb} {settled}; {skipped} awaiting a provider result; '
            f'{failed} refused; {diverged} diverged'
        )
        if diverged:
            self.stdout.write(self.style.ERROR(
                'Divergences need investigation — the provider disagrees with a '
                'result we already published.'
            ))
        if failed:
            self.stdout.write(self.style.ERROR(
                'Refused settlements need investigation — a claim already '
                'carries a different result.'
            ))
