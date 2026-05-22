"""
One-off remediation for the 2026-05-22 audit finding: mark_recommended_predictions
and the mark-recommended-by-fixture-ids endpoint were stripping is_recommended=True
from future picks that aged out of the rolling top-10. Those picks then settled and
disappeared from the public monitoring page entirely — hiding real profit.

This command flips is_recommended back to True on every row that:
  - was originally engine-logged (has market_type set — every log_recommendations
    write populates this; non-engine writes leave it blank or NULL)
  - was logged after the Phase 2 deploy boundary (2026-05-14) — earlier rows have
    their own audit history and shouldn't be touched in this sweep
  - currently has is_recommended=False
  - is NOT audit-excluded (we don't want to re-promote the 8 quarantined rows)

Dry-run by default. Use --apply to persist.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import PredictionLog


PHASE_2_DEPLOY = '2026-05-14T00:00:00Z'


class Command(BaseCommand):
    help = "Restore is_recommended=True on engine picks the mark_recommended cron stripped."

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Actually persist the flag updates.')
        parser.add_argument('--since', default=PHASE_2_DEPLOY,
                            help='Only restore rows logged on/after this ISO timestamp (UTC). '
                                 f'Default {PHASE_2_DEPLOY}.')

    def handle(self, *args, **options):
        from django.utils.dateparse import parse_datetime
        since = parse_datetime(options['since'])
        if since is None:
            self.stdout.write(self.style.ERROR(f'Invalid --since value: {options["since"]!r}'))
            return
        if since.tzinfo is None:
            since = timezone.make_aware(since)

        self.stdout.write(self.style.MIGRATE_HEADING('=' * 72))
        self.stdout.write(self.style.MIGRATE_HEADING(
            'RESTORE STRIPPED RECOMMENDATIONS (one-off audit remediation)'
        ))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 72))
        self.stdout.write(f'Since: {since.isoformat()}')
        self.stdout.write(f"Mode:  {'APPLY' if options['apply'] else 'DRY-RUN (no changes)'}")
        self.stdout.write('')

        # Eligibility: engine-logged (market_type populated), post-deploy, currently
        # stripped, not audit-excluded.
        candidates = PredictionLog.objects.filter(
            is_recommended=False,
            is_audit_excluded=False,
            prediction_logged_at__gte=since,
            market_type__isnull=False,
        ).exclude(market_type='')

        n = candidates.count()
        settled = candidates.filter(actual_outcome__isnull=False)
        n_settled = settled.count()
        correct = settled.filter(was_correct=True).count()
        wrong = settled.filter(was_correct=False).count()
        pl = sum(r.profit_loss_10 or 0 for r in settled)

        self.stdout.write(f'Candidate rows to restore: {n}')
        self.stdout.write(f'  of which already settled: {n_settled}')
        self.stdout.write(f'    correct:   {correct}')
        self.stdout.write(f'    incorrect: {wrong}')
        self.stdout.write(f'    settled P/L this restores: ${pl:+.2f}')
        if n_settled:
            self.stdout.write(f'    settled accuracy of restored: {correct/n_settled*100:.1f}%')
            self.stdout.write(f'    settled yield of restored:    {pl/(n_settled*10)*100:+.2f}%')

        if n == 0:
            self.stdout.write(self.style.SUCCESS('\nNothing to restore.'))
            return

        # Sample so the operator can eyeball before --apply.
        self.stdout.write('\nSample (newest 12):')
        for r in candidates.order_by('-prediction_logged_at')[:12]:
            pl_str = f'${r.profit_loss_10:+.2f}' if r.profit_loss_10 is not None else '   pending'
            outcome = r.actual_outcome or '   -'
            self.stdout.write(
                f"  logged={r.prediction_logged_at.date()}  kickoff={r.kickoff.date()}  "
                f"{(r.home_team or '')[:18]:>18} vs {(r.away_team or '')[:18]:<18}  "
                f"{(r.predicted_outcome or '')[:10]:>10} -> {outcome:<6}  {pl_str}  ({r.league})"
            )

        if not options['apply']:
            self.stdout.write('\nDry-run only. Re-run with --apply to persist.')
            return

        updated = candidates.update(is_recommended=True)
        self.stdout.write(self.style.SUCCESS(
            f'\nRestored is_recommended=True on {updated} rows.'
        ))
        self.stdout.write('Public monitoring page will reflect the cleaned numbers immediately.')
