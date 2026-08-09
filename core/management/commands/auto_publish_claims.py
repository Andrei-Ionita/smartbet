"""
Automatic public commitment from the versioned recommendation feed.

The FULL selection rule, stated publicly on the site before activation:
a signal becomes a public commitment when, and only when, ALL of these hold —

  1. it passes the standard publication eligibility gate
     (`check_snapshot_publication_eligibility`: recommended, verified price
     with complete provenance, coherent timestamps, not superseded,
     pre-kickoff, integrity hash intact);
  2. kickoff is at least ``--min-lead-hours`` (default 6) away at
     publication time;
  3. the fixture does not already carry a non-superseded public commitment
     (hourly runs append a snapshot per run — the FIRST commitment for a
     fixture is the one the record keeps; later snapshots for the same
     fixture are context, not new commitments);
  4. the snapshot is the fixture's NEWEST — an older eligible snapshot is
     never committed over a newer signal state, even when the newer one is
     itself ineligible (that fixture simply waits for the next cycle).

There is NO per-fixture human veto and NO additional selection rule. "Top
ranked outcome in its market" is structural, not a filter applied here: the
ingest pipeline only ever snapshots the best market's selection.

This command contains no eligibility logic of its own — it delegates entirely
to `claim_publication.publish_prediction_claim`, the ONLY supported way to
create a claim. Idempotent: publication is unique per snapshot, and the
fixture-level dedup makes re-runs no-ops.

    python manage.py auto_publish_claims --dry-run
    python manage.py auto_publish_claims
"""
import logging
from datetime import timedelta
from types import SimpleNamespace

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import PredictionLog, PredictionSnapshot, PublishedClaim
from core.services import claim_publication

logger = logging.getLogger(__name__)

# Recorded in the publication log line — a claim committed by this policy is
# attributable to the policy version, never to an anonymous "system".
AUTO_PUBLISHER = SimpleNamespace(username='auto:versioned-feed')


class Command(BaseCommand):
    help = ('Automatically publish every eligible signal from the versioned '
            'strategy feed as a public commitment.')

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='Report what would publish without writing.')
        parser.add_argument('--min-lead-hours', type=float, default=6.0,
                            help='Minimum hours between publication and '
                                 'kickoff (default: 6).')

    def handle(self, *args, **options):
        dry = options['dry_run']
        now = timezone.now()
        lead_cutoff = now + timedelta(hours=options['min_lead_hours'])

        # Cheap DB pre-filter only — the authoritative gate stays inside
        # publish_prediction_claim. Ordering gives newest-snapshot-first per
        # fixture, which the seen-set below turns into "latest per fixture"
        # without a Postgres-only DISTINCT ON.
        candidates = (
            PredictionSnapshot.objects
            .filter(
                is_recommended=True,
                is_audit_excluded=False,
                pricing_integrity_status=PredictionLog.PRICING_VERIFIED,
                kickoff__gte=lead_cutoff,
            )
            .order_by('fixture_id', '-prediction_generated_at')
        )

        committed_fixtures = set(
            PublishedClaim.objects
            .filter(superseded_by__isnull=True)
            .values_list('fixture_id', flat=True)
        )

        published = 0
        already_committed = 0
        ineligible = 0
        seen_fixtures = set()

        for snap in candidates:
            if snap.fixture_id in seen_fixtures:
                continue
            seen_fixtures.add(snap.fixture_id)

            # Criterion 3: one non-superseded commitment per fixture.
            if snap.fixture_id in committed_fixtures:
                already_committed += 1
                continue

            # Criterion 4: only the fixture's newest snapshot OVERALL may be
            # committed — measured against ALL of its snapshots, not just the
            # pre-filtered candidates. If the newest signal state failed the
            # pre-filter (e.g. its price could not be verified), committing an
            # older snapshot would publish a state we know has been replaced;
            # the fixture waits for the next cycle instead.
            newer_exists = PredictionSnapshot.objects.filter(
                fixture_id=snap.fixture_id,
                prediction_generated_at__gt=snap.prediction_generated_at,
            ).exists()
            if newer_exists:
                ineligible += 1
                logger.info(
                    'auto-publish skipping snapshot %s (fixture %s): a newer '
                    'snapshot exists but is not currently publishable',
                    snap.snapshot_id, snap.fixture_id)
                continue

            problems = claim_publication.check_snapshot_publication_eligibility(
                snap, now=now)
            if problems:
                ineligible += 1
                logger.info('auto-publish skipping snapshot %s (fixture %s): %s',
                            snap.snapshot_id, snap.fixture_id,
                            '; '.join(problems))
                continue

            if dry:
                published += 1
                self.stdout.write(
                    f'  would commit {snap.home_team} v {snap.away_team} '
                    f'{snap.market_type}/{snap.predicted_outcome} '
                    f'(fixture {snap.fixture_id}, KO {snap.kickoff:%Y-%m-%d %H:%M})'
                )
                continue

            try:
                claim = claim_publication.publish_prediction_claim(
                    snap.snapshot_id, published_by=AUTO_PUBLISHER, now=now)
            except claim_publication.PublicationError as exc:
                # The pre-filter passed but the authoritative gate refused —
                # e.g. a snapshot tampered with, or a race. Loud, not fatal.
                ineligible += 1
                logger.warning('auto-publish refused for snapshot %s: %s',
                               snap.snapshot_id, exc)
                self.stdout.write(self.style.WARNING(
                    f'  REFUSED fixture {snap.fixture_id}: {exc}'))
                continue

            published += 1
            committed_fixtures.add(snap.fixture_id)
            self.stdout.write(self.style.SUCCESS(
                f'  committed {claim.claim_id} — {claim.home_team} v '
                f'{claim.away_team} {claim.market_type}/{claim.predicted_outcome}'
            ))

        verb = 'would commit' if dry else 'committed'
        self.stdout.write(
            f'\n{verb} {published}; {already_committed} fixtures already hold '
            f'a commitment; {ineligible} candidates ineligible this cycle'
        )
