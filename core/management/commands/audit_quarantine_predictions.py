"""
Stage B of the data-integrity audit.

Find historical PredictionLog rows whose stored values are implausible enough that
including them in public-facing stats would mislead users (e.g. EV > 50%, EV < -30%,
odds <= 1.01), and flag them with `is_audit_excluded=True` so the monitoring API
hides them from accuracy / P/L / ROI / yield aggregates.

Dry-run by default. Use --apply to actually update rows.

Examples:
    python manage.py audit_quarantine_predictions               # dry-run, default thresholds
    python manage.py audit_quarantine_predictions --apply       # mark rows
    python manage.py audit_quarantine_predictions --unquarantine --apply  # clear all flags
    python manage.py audit_quarantine_predictions --max-ev 0.40 # custom threshold
"""

from django.core.management.base import BaseCommand
from core.models import PredictionLog


class Command(BaseCommand):
    help = "Mark PredictionLog rows with implausible EV/odds as audit-excluded so they don't poison public stats."

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply',
            action='store_true',
            help='Actually update rows. Without this flag, command runs in dry-run mode.',
        )
        parser.add_argument(
            '--skip-normalize',
            action='store_true',
            help='Skip the unit-normalization pass (only useful if the DB is already known to be decimal-stored).',
        )

    def handle(self, *args, **options):
        apply_changes = options['apply']
        skip_normalize = options['skip_normalize']

        self.stdout.write(self.style.MIGRATE_HEADING('=' * 72))
        self.stdout.write(self.style.MIGRATE_HEADING(
            'AUDIT QUARANTINE — PredictionLog data-integrity sweep'
        ))
        self.stdout.write(self.style.MIGRATE_HEADING('=' * 72))
        self.stdout.write(
            f'Thresholds: EV in [{PredictionLog.EV_PLAUSIBLE_MIN*100:+.1f}%, '
            f'{PredictionLog.EV_PLAUSIBLE_MAX*100:+.1f}%]   odds > 1.01'
        )
        self.stdout.write(f"Mode: {'APPLY' if apply_changes else 'DRY-RUN (no changes)'}")
        self.stdout.write('')

        if not skip_normalize:
            normalized_rows = self._normalize_pass(apply_changes)
        else:
            self.stdout.write('(--skip-normalize given; skipping unit-normalization pass)')
            normalized_rows = list(PredictionLog.objects.all())

        flagged = [r for r in normalized_rows if r.is_audit_excluded]
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Quarantined rows after sweep: {len(flagged)}'
        ))

        if flagged:
            self._report(flagged)
            self._impact_summary(normalized_rows, flagged)

        if not apply_changes:
            self.stdout.write('\nDry-run only. Re-run with --apply to persist normalization + flags.')

    def _normalize_pass(self, apply_changes):
        """
        Walk every PredictionLog and re-save it. Reusing the model's save() invariants is the
        single source of truth: percent->decimal conversion, EV clamping, odds sanity, and
        is_audit_excluded all happen there. Idempotent — safe to re-run.

        Returns the list of post-normalization rows (in-memory mutations applied either way),
        so callers can report on the would-be state without round-tripping through the DB.
        """
        all_rows = list(PredictionLog.objects.all())
        normalized_evs = clamped = bad_odds = 0
        for r in all_rows:
            before_ev = r.expected_value
            before_excluded = r.is_audit_excluded
            before_odds = r.odds

            if apply_changes:
                r.save()
            else:
                self._simulate_save_invariants(r)

            if before_ev is not None and r.expected_value is not None and abs(before_ev) > 1 and abs(r.expected_value) <= 1:
                normalized_evs += 1
            if r.is_audit_excluded and not before_excluded:
                clamped += 1
            if before_odds is not None and r.odds is None:
                bad_odds += 1

        self.stdout.write(f'Normalize pass over {len(all_rows)} rows:')
        self.stdout.write(f'  EV percent->decimal:      {normalized_evs}')
        self.stdout.write(f'  EV clamped + flagged:    {clamped}')
        self.stdout.write(f'  Invalid odds nulled:     {bad_odds}')
        return all_rows

    @staticmethod
    def _simulate_save_invariants(r):
        """Mirror PredictionLog.save() in memory so dry-run shows the same outcome as --apply."""
        if r.confidence is not None and r.confidence > 1:
            r.confidence = r.confidence / 100.0
        if r.expected_value is not None and abs(r.expected_value) > 1:
            r.expected_value = r.expected_value / 100.0
        if r.raw_expected_value is None and r.expected_value is not None:
            r.raw_expected_value = r.expected_value
        if r.expected_value is not None and (
            r.expected_value > PredictionLog.EV_PLAUSIBLE_MAX
            or r.expected_value < PredictionLog.EV_PLAUSIBLE_MIN
        ):
            r.expected_value = max(
                PredictionLog.EV_PLAUSIBLE_MIN,
                min(PredictionLog.EV_PLAUSIBLE_MAX, r.expected_value),
            )
            r.is_audit_excluded = True
        if r.odds is not None and r.odds <= 1.01:
            r.odds = None

    def _report(self, rows):
        """Print one line per affected row so the operator can spot-check before applying.

        Accepts a list of (possibly in-memory-mutated) PredictionLog instances so dry-run
        output matches what --apply would persist.
        """
        rows = sorted(rows, key=lambda r: r.kickoff or 0, reverse=True)
        if not rows:
            return
        self.stdout.write(self.style.WARNING('Rows that match quarantine rules:'))
        self.stdout.write(
            f"  {'fixture_id':>11} {'kickoff':>12} {'market':>14} {'pred':>10} "
            f"{'conf%':>6} {'ev%':>7} {'raw_ev%':>8} {'odds':>6} {'P/L':>8}  reason"
        )
        for r in rows:
            # raw_expected_value preserves the original pre-clamp value, which is what makes
            # the row "bad". Fall back to expected_value if raw isn't recorded.
            tested_ev = r.raw_expected_value if r.raw_expected_value is not None else r.expected_value
            reasons = []
            if tested_ev is not None and tested_ev > PredictionLog.EV_PLAUSIBLE_MAX:
                reasons.append(f'raw EV={tested_ev*100:.1f}% > {PredictionLog.EV_PLAUSIBLE_MAX*100:.0f}%')
            elif tested_ev is not None and tested_ev < PredictionLog.EV_PLAUSIBLE_MIN:
                reasons.append(f'raw EV={tested_ev*100:.1f}% < {PredictionLog.EV_PLAUSIBLE_MIN*100:.0f}%')
            if r.odds is not None and r.odds < 1.05:
                reasons.append(f'odds={r.odds}<1.05')

            kickoff = r.kickoff.strftime('%Y-%m-%d') if r.kickoff else '-'
            conf = f'{r.confidence*100:.1f}' if r.confidence and r.confidence < 1 else (f'{r.confidence:.1f}' if r.confidence else '-')
            ev = f'{r.expected_value*100:.1f}' if r.expected_value is not None and abs(r.expected_value) < 1 else (f'{r.expected_value:.1f}' if r.expected_value is not None else '-')
            raw_ev = f'{r.raw_expected_value*100:.1f}' if r.raw_expected_value is not None and abs(r.raw_expected_value) < 1 else (f'{r.raw_expected_value:.1f}' if r.raw_expected_value is not None else '-')
            odds = f'{r.odds:.2f}' if r.odds else '-'
            pl = f'{r.profit_loss_10:+.2f}' if r.profit_loss_10 is not None else '-'
            self.stdout.write(
                f"  {r.fixture_id:>11} {kickoff:>12} {r.market_type:>14} "
                f"{(r.predicted_outcome or '')[:10]:>10} {conf:>6} {ev:>7} {raw_ev:>8} {odds:>6} {pl:>8}  {', '.join(reasons)}"
            )

    def _impact_summary(self, all_rows, flagged_rows):
        """Show how aggregate stats change once the flagged rows are excluded.

        Operates on the in-memory normalized rows so dry-run reflects --apply behavior.
        """
        flagged_pks = {r.pk for r in flagged_rows}
        settled = [r for r in all_rows if r.is_recommended and r.actual_outcome is not None]
        kept = [r for r in settled if r.pk not in flagged_pks]

        def stats(rows):
            n = len(rows)
            if n == 0:
                return n, None, 0.0, 0.0
            correct = sum(1 for r in rows if r.was_correct)
            pl = sum((r.profit_loss_10 or 0) for r in rows)
            yld = pl / (n * 10) * 100
            return n, correct / n * 100, pl, yld

        before_n, before_acc, before_pl, before_yld = stats(settled)
        after_n, after_acc, after_pl, after_yld = stats(kept)

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING('Aggregate impact on public stats:'))
        self.stdout.write(
            f"  {'':14} {'BEFORE':>10} {'AFTER':>10} {'DELTA':>10}"
        )
        self.stdout.write(
            f"  {'settled rows':14} {before_n:>10} {after_n:>10} {after_n - before_n:>+10}"
        )
        if before_acc is not None and after_acc is not None:
            self.stdout.write(
                f"  {'accuracy %':14} {before_acc:>10.2f} {after_acc:>10.2f} {after_acc - before_acc:>+10.2f}"
            )
        self.stdout.write(
            f"  {'total P/L $':14} {before_pl:>10.2f} {after_pl:>10.2f} {after_pl - before_pl:>+10.2f}"
        )
        self.stdout.write(
            f"  {'yield %':14} {before_yld:>10.2f} {after_yld:>10.2f} {after_yld - before_yld:>+10.2f}"
        )
