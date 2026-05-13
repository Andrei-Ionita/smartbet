"""
Backtest the recommendation filter against settled PredictionLog rows.

Examples:
    python manage.py backtest                      # run all baselines, side-by-side
    python manage.py backtest --config current_prod
    python manage.py backtest --stratify league    # show stats per league
    python manage.py backtest --stratify odds      # show stats per odds bucket
    python manage.py backtest --since 2026-01-01   # only rows kicked off after this date
    python manage.py backtest --include-excluded   # don't filter out audit_excluded rows
    python manage.py backtest --json               # machine-readable output

Read-only — does not touch the DB.
"""

from __future__ import annotations

import json
from datetime import datetime, date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models import PredictionLog
from core.services import backtester


class Command(BaseCommand):
    help = "Replay candidate filter configs over historical settled PredictionLog rows."

    def add_arguments(self, parser):
        parser.add_argument(
            '--config',
            action='append',
            dest='configs',
            help='Name of a baseline config (repeatable). Defaults to all baselines.',
        )
        parser.add_argument(
            '--stratify',
            choices=sorted(backtester.DIMENSIONS.keys()),
            help='Show stats stratified by this dimension for the first config.',
        )
        parser.add_argument(
            '--since',
            help='Only include rows with kickoff >= YYYY-MM-DD.',
        )
        parser.add_argument(
            '--include-excluded',
            action='store_true',
            help='Include rows with is_audit_excluded=True. Off by default — these are bad-data rows.',
        )
        parser.add_argument(
            '--include-pending',
            action='store_true',
            help='Include rows without a result yet. Off by default — backtest needs outcomes.',
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Emit JSON instead of human-readable tables.',
        )

    def handle(self, *args, **options):
        rows = self._load_rows(options)
        if not rows:
            raise CommandError('No rows match the filters.')

        configs = self._resolve_configs(options.get('configs'))

        results = backtester.compare(rows, configs)

        if options['json']:
            self._emit_json(rows, configs, results, options.get('stratify'))
            return

        self._print_header(rows, options)
        self._print_comparison(results)

        if options.get('stratify'):
            self._print_stratification(results[0], options['stratify'])

    # ── helpers ──────────────────────────────────────────────────────────

    def _load_rows(self, options):
        qs = PredictionLog.objects.filter(is_recommended=True)
        if not options['include_excluded']:
            qs = qs.filter(is_audit_excluded=False)
        if not options['include_pending']:
            qs = qs.exclude(was_correct__isnull=True)
        if options.get('since'):
            try:
                d = date.fromisoformat(options['since'])
            except ValueError:
                raise CommandError(f"--since must be YYYY-MM-DD, got {options['since']!r}")
            qs = qs.filter(kickoff__date__gte=d)
        return list(qs)

    def _resolve_configs(self, names):
        if not names:
            return backtester.BASELINES
        by_name = {c.name: c for c in backtester.BASELINES}
        unknown = [n for n in names if n not in by_name]
        if unknown:
            raise CommandError(
                f"Unknown config(s): {unknown}. Available: {sorted(by_name)}"
            )
        return [by_name[n] for n in names]

    def _print_header(self, rows, options):
        self.stdout.write('=' * 88)
        self.stdout.write(self.style.MIGRATE_HEADING('BACKTEST'))
        self.stdout.write('=' * 88)
        kickoff_min = min((r.kickoff for r in rows if r.kickoff), default=None)
        kickoff_max = max((r.kickoff for r in rows if r.kickoff), default=None)
        self.stdout.write(f'Sample size:      {len(rows)} settled rows')
        if kickoff_min and kickoff_max:
            self.stdout.write(
                f'Date range:       {kickoff_min.date()} to {kickoff_max.date()}'
            )
        flags = []
        if options['include_excluded']:
            flags.append('include_excluded')
        if options['include_pending']:
            flags.append('include_pending')
        if options['since']:
            flags.append(f"since={options['since']}")
        if flags:
            self.stdout.write(f'Flags:            {", ".join(flags)}')
        self.stdout.write('')

    def _print_comparison(self, results):
        # Header
        headers = ('config', 'n_kept', 'acc%', 'P/L $', 'yield%', 'avg_roi%', 'brier', 'maxDD', 'winS', 'lossS')
        widths  = ( 22,        7,        7,      9,      8,        9,         7,       8,       5,      5)
        line = '  '.join(f'{h:>{w}}' for h, w in zip(headers, widths))
        self.stdout.write(line)
        self.stdout.write('  '.join('-' * w for w in widths))

        # Top row: the first config acts as the baseline for comparison.
        baseline_metrics = results[0][1] if results else None

        for cfg, m, _ in results:
            yld = f'{m.yield_percent:+.2f}' if m.yield_percent is not None else '   -'
            acc = f'{m.accuracy:.1f}'      if m.accuracy is not None else '  -'
            avg_roi = f'{m.avg_roi:+.2f}'  if m.avg_roi is not None else '   -'
            brier = f'{m.brier:.3f}'       if m.brier is not None else '   -'
            row_vals = (
                cfg.name,
                m.n_kept,
                acc,
                f'{m.total_pl:+.2f}',
                yld,
                avg_roi,
                brier,
                f'{m.max_drawdown:+.2f}',
                m.longest_win_streak,
                m.longest_loss_streak,
            )
            line = '  '.join(f'{v:>{w}}' for v, w in zip(row_vals, widths))

            # Annotate with delta vs baseline yield
            if baseline_metrics and m.yield_percent is not None and baseline_metrics.yield_percent is not None and cfg is not results[0][0]:
                delta = m.yield_percent - baseline_metrics.yield_percent
                annotation = f'   ({delta:+.2f}pp yield vs {results[0][0].name})'
                line = line + annotation

            self.stdout.write(line)

    def _print_stratification(self, first_result, dim):
        cfg, _, kept = first_result
        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Stratification by {dim} (config: {cfg.name}, {len(kept)} rows kept)"
        ))
        rows = backtester.stratify(kept, dim)

        headers = (dim, 'n', 'acc%', 'P/L $', 'yield%', 'winS', 'lossS')
        widths  = (24,   5,    7,     9,       8,       5,      5)
        self.stdout.write('  '.join(f'{h:>{w}}' for h, w in zip(headers, widths)))
        self.stdout.write('  '.join('-' * w for w in widths))
        for label, m in rows:
            yld = f'{m.yield_percent:+.2f}' if m.yield_percent is not None else '   -'
            acc = f'{m.accuracy:.1f}'      if m.accuracy is not None else '  -'
            row_vals = (
                (label or 'unknown')[:24],
                m.n_settled,
                acc,
                f'{m.total_pl:+.2f}',
                yld,
                m.longest_win_streak,
                m.longest_loss_streak,
            )
            self.stdout.write('  '.join(f'{v:>{w}}' for v, w in zip(row_vals, widths)))

    def _emit_json(self, rows, configs, results, stratify_dim):
        def cfg_dict(c):
            return {
                k: v for k, v in c.__dict__.items()
                if v not in (None, [], {}, ())
            }

        def metrics_dict(m):
            return {
                'n_total': m.n_total,
                'n_kept': m.n_kept,
                'n_settled': m.n_settled,
                'correct': m.correct,
                'accuracy': m.accuracy,
                'total_pl': m.total_pl,
                'yield_percent': m.yield_percent,
                'avg_roi': m.avg_roi,
                'brier': m.brier,
                'longest_win_streak': m.longest_win_streak,
                'longest_loss_streak': m.longest_loss_streak,
                'max_drawdown': m.max_drawdown,
            }

        out = {
            'sample_size': len(rows),
            'kickoff_min': min((r.kickoff for r in rows if r.kickoff), default=None),
            'kickoff_max': max((r.kickoff for r in rows if r.kickoff), default=None),
            'configs': [
                {'config': cfg_dict(cfg), 'metrics': metrics_dict(m)}
                for cfg, m, _ in results
            ],
            'generated_at': timezone.now().isoformat(),
        }
        if stratify_dim:
            cfg, _, kept = results[0]
            out['stratification'] = {
                'config': cfg.name,
                'dimension': stratify_dim,
                'buckets': [
                    {'label': label, **metrics_dict(m)}
                    for label, m in backtester.stratify(kept, stratify_dim)
                ],
            }

        def default(o):
            if isinstance(o, (datetime, date)):
                return o.isoformat()
            raise TypeError(f'Not JSON serializable: {type(o).__name__}')

        self.stdout.write(json.dumps(out, indent=2, default=default))
