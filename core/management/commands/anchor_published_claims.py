"""
Anchor published claims to an independent, external timestamp.

Runs in the scheduler IMMEDIATELY AFTER auto-publication. That ordering is the
entire value of the feature: every claim in the batch is still at least six
hours from kickoff when the digest reaches the OpenTimestamps calendars, so
the resulting Bitcoin attestation proves foresight rather than hindsight. A
nightly sweep would produce a proof that the record existed after the matches
had already been played, which proves nothing worth publishing.

Two jobs, both safe to re-run:

  * stamp any claim that has no anchor yet (one batch digest per run)
  * upgrade earlier pending anchors once the calendars have committed them to
    a Bitcoin block, which typically takes a few hours

Anchoring never blocks or reverses publication. If every calendar is
unreachable the command reports the failure and the claims stay unanchored,
to be picked up by the next cycle.

    python manage.py anchor_published_claims --dry-run
    python manage.py anchor_published_claims
    python manage.py anchor_published_claims --upgrade-only
"""
import logging

from django.core.management.base import BaseCommand

from core.models import ClaimAnchor
from core.services import claim_anchoring

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = ('Timestamp published claims with independent OpenTimestamps '
            'calendars, and upgrade pending proofs to Bitcoin attestations.')

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Report what would be anchored without '
                                 'contacting any calendar or writing.')
        parser.add_argument('--upgrade-only', action='store_true',
                            help='Skip new stamping; only upgrade pending.')
        parser.add_argument('--max-upgrades', type=int, default=25,
                            help='Pending anchors to attempt per run.')

    def handle(self, *args, **options):
        if not options['upgrade_only']:
            self._stamp(dry=options['dry_run'])
        self._upgrade(dry=options['dry_run'], limit=options['max_upgrades'])

    def _stamp(self, dry):
        pending = list(claim_anchoring.unanchored_claims()[:500])
        if not pending:
            self.stdout.write('  nothing to anchor — every claim is stamped')
            return

        if dry:
            manifest = claim_anchoring.build_manifest(
                (str(c.claim_id), c.claim_hash) for c in pending)
            self.stdout.write(
                f'  would anchor {len(pending)} claims as digest '
                f'{claim_anchoring.compute_digest(manifest)}')
            return

        try:
            anchor = claim_anchoring.anchor_pending_claims()
        except claim_anchoring.AnchoringUnavailable as exc:
            # Loud, but never fatal: the claims remain published and unanchored,
            # and the next cycle retries them.
            logger.warning('claim anchoring unavailable: %s', exc)
            self.stdout.write(self.style.WARNING(
                f'  anchoring unavailable ({exc}) — {len(pending)} claims '
                f'left for the next cycle'))
            return

        if anchor is None:
            self.stdout.write('  nothing to anchor')
            return

        self.stdout.write(self.style.SUCCESS(
            f'  anchored {anchor.claim_count} claims — digest {anchor.digest} '
            f'via {len(anchor.calendars)} calendar(s)'))

    def _upgrade(self, dry, limit):
        pending = list(
            ClaimAnchor.objects
            .filter(status=ClaimAnchor.STATUS_PENDING)
            .order_by('created_at')[:limit]
        )
        if not pending:
            return

        if dry:
            self.stdout.write(f'  would attempt {len(pending)} upgrade(s)')
            return

        confirmed = 0
        for anchor in pending:
            try:
                if claim_anchoring.upgrade_anchor(anchor):
                    confirmed += 1
                    self.stdout.write(self.style.SUCCESS(
                        f'  confirmed {anchor.digest[:12]} in Bitcoin block '
                        f'{anchor.bitcoin_block_height}'))
            except claim_anchoring.AnchoringUnavailable as exc:
                logger.warning('upgrade unavailable for %s: %s',
                               anchor.digest, exc)
            except Exception as exc:
                # An upgrade failure is expected while the calendar is still
                # aggregating; never let it fail the scheduler stage.
                logger.info('anchor %s not upgraded: %s', anchor.digest, exc)

        self.stdout.write(
            f'  {confirmed} of {len(pending)} pending anchor(s) reached Bitcoin')
