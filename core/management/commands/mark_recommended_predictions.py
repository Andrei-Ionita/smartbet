"""
Management command to mark predictions as recommended based on quality criteria.
This identifies high-quality predictions that should be tracked separately.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import PredictionLog


class Command(BaseCommand):
    help = 'Mark high-quality predictions as recommended based on confidence and EV criteria'

    def add_arguments(self, parser):
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=60.0,
            help='Minimum confidence percentage (default: 60.0) - optimized for accuracy'
        )
        parser.add_argument(
            '--min-ev',
            type=float,
            default=15.0,
            help='Minimum expected value percentage (default: 15.0) - optimized for accuracy'
        )
        parser.add_argument(
            '--only-future',
            action='store_true',
            help='Only mark predictions for future matches'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be marked without actually marking them'
        )
        parser.add_argument(
            '--top-n',
            type=int,
            default=10,
            help='Number of top predictions to mark (default: 10, matches home page)'
        )

    def handle(self, *args, **options):
        min_confidence = options['min_confidence']
        min_ev = options['min_ev']
        only_future = options['only_future']
        dry_run = options['dry_run']

        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('MARKING RECOMMENDED PREDICTIONS'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))
        
        self.stdout.write(f'Criteria:')
        self.stdout.write(f'  - Minimum Confidence: {min_confidence}%')
        self.stdout.write(f'  - Minimum Expected Value: {min_ev}%')
        self.stdout.write(f'  - Only Future Matches: {only_future}')
        self.stdout.write(f'  - Dry Run: {dry_run}')
        self.stdout.write(f'\nNote: This uses the same criteria as home page recommendations:\n')
        self.stdout.write(f'  - EV > 0 AND confidence >= 55% AND EV >= 10%\n')
        self.stdout.write(f'  - Then scores by revenue vs risk and takes top 10\n')

        # Build query
        # Data seems to be stored in decimal format (0.55 = 55%, 0.10 = 10%)
        # But some may be in percentage format (55.0 = 55%, 10.0 = 10%)
        # So we check both formats
        from django.db.models import Q
        
        # Convert to both formats - check if values are likely decimals (< 1) or percentages (>= 1)
        min_confidence_decimal = min_confidence / 100  # e.g., 55% -> 0.55
        min_confidence_percent = min_confidence  # e.g., 55
        
        min_ev_decimal = min_ev / 100  # e.g., 10% -> 0.10
        min_ev_percent = min_ev  # e.g., 10
        
        # Query: confidence >= min (either format) AND ev >= min (either format)
        queryset = PredictionLog.objects.filter(
            (Q(confidence__gte=min_confidence_decimal) | Q(confidence__gte=min_confidence_percent)),
            Q(expected_value__isnull=False),
            (Q(expected_value__gte=min_ev_decimal) | Q(expected_value__gte=min_ev_percent))
        )

        # Always strictly filter for FUTURE matches for *new* recommendations
        # We don't want to recommend a match that already happened
        now = timezone.now()
        queryset = queryset.filter(kickoff__gte=now)

        # Apply the same scoring logic as the home page recommendations API
        # Score all matching predictions and take top 10
        predictions_list = []
        for pred in queryset:
            # Normalize confidence and EV to percentage format for scoring
            confidence = pred.confidence
            if confidence < 1:
                confidence = confidence * 100  # Convert decimal to percentage
            
            ev = pred.expected_value
            if ev < 1:
                ev = ev * 100  # Convert decimal to percentage
            
            # Calculate scores (same as recommendations API)
            revenue_score = ev * (confidence / 100)
            risk_score = 1 - (confidence / 100)
            combined_score = revenue_score - (risk_score * 0.8)
            
            # Quality bonuses
            quality_bonus = 0
            if confidence >= 70:
                quality_bonus = 0.5
            elif confidence >= 65:
                quality_bonus = 0.3
            elif confidence >= 60:
                quality_bonus = 0.2
            
            ev_bonus = 0
            if ev >= 30:
                ev_bonus = 0.2
            elif ev >= 15:
                ev_bonus = 0.1
            
            revenue_vs_risk_score = combined_score + quality_bonus + ev_bonus
            
            predictions_list.append({
                'prediction': pred,
                'score': revenue_vs_risk_score
            })
        
        # Sort by score (highest first) and take top N
        top_n = options.get('top_n', 10)
        predictions_list.sort(key=lambda x: x['score'], reverse=True)
        top_predictions = predictions_list[:top_n]
        
        if len(top_predictions) == 0:
            self.stdout.write(self.style.WARNING('No predictions found matching the criteria.'))
            return

        # Show what will be marked
        top_n = options.get('top_n', 10)
        self.stdout.write(self.style.SUCCESS(f'Top {top_n} predictions that will be marked as recommended:'))
        self.stdout.write(self.style.SUCCESS('-'*80))
        
        for i, item in enumerate(top_predictions, 1):
            pred = item['prediction']
            score = item['score']
            # Determine display values (handle decimal vs percent)
            disp_conf = pred.confidence * 100 if pred.confidence < 1 else pred.confidence
            disp_ev = pred.expected_value * 100 if pred.expected_value < 1 else pred.expected_value
            
            self.stdout.write(
                f'  [{i}] {pred.home_team} vs {pred.away_team} | '
                f'{pred.predicted_outcome} (Conf: {disp_conf:.1f}%, '
                f'EV: {disp_ev:.2f}%) | Score: {score:.2f} | {pred.league}'
            )

        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN - No predictions were actually marked'))
            return

        # CRITICAL FIX: Only unmark FUTURE recommendations to refresh the current slip.
        # Do NOT unmark past games - they are part of history now.
        now = timezone.now()
        
        # 1. Unmark only future recommendations (refreshing the "Upcoming" list)
        unmarked_count = PredictionLog.objects.filter(
            is_recommended=True,
            kickoff__gte=now
        ).update(is_recommended=False)
        
        self.stdout.write(f'Refreshing {unmarked_count} future recommendations (History preserved)')
        
        # 2. Mark the top N *FUTURE* matches as recommended
        top_fixture_ids = [item['prediction'].fixture_id for item in top_predictions]
        updated = PredictionLog.objects.filter(
            fixture_id__in=top_fixture_ids
        ).update(is_recommended=True)

        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully marked {updated} predictions as recommended!\n'))

        # Show statistics
        total_recommended = PredictionLog.objects.filter(is_recommended=True).count()
        self.stdout.write(f'Total recommended predictions in database: {total_recommended}')
        
        if only_future:
            future_recommended = PredictionLog.objects.filter(
                is_recommended=True,
                kickoff__gte=timezone.now()
            ).count()
            self.stdout.write(f'Future recommended predictions: {future_recommended}')

