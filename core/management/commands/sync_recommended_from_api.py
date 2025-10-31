"""
Management command to sync recommended predictions based on the same logic as the home page recommendations API.
This ensures that only predictions shown on the home page are marked as recommended.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from core.models import PredictionLog


class Command(BaseCommand):
    help = 'Mark predictions as recommended based on home page recommendations API logic'

    def add_arguments(self, parser):
        parser.add_argument(
            '--unmark-others',
            action='store_true',
            help='Unmark predictions that no longer match the criteria'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be marked without actually marking them'
        )

    def handle(self, *args, **options):
        unmark_others = options['unmark_others']
        dry_run = options['dry_run']

        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('SYNCING RECOMMENDED PREDICTIONS FROM HOME PAGE API LOGIC'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))

        # This replicates the logic from smartbet-frontend/app/api/recommendations/route.ts
        # Filter: expectedValue > 0 && confidence >= 55 && expectedValue >= 0.10
        
        now = timezone.now()
        end_date = now + timedelta(days=14)  # 14-day window like the API
        
        # Initial filter: future matches with predictions
        queryset = PredictionLog.objects.filter(
            kickoff__gte=now,
            kickoff__lte=end_date,
            predicted_outcome__isnull=False,
            expected_value__isnull=False
        )
        
        # Apply the same filters as the recommendations API
        # The API uses: expectedValue > 0 && confidence >= 55 && expectedValue >= 0.10
        # But expectedValue is multiplied by 100 in the API (so 0.10 becomes 10.0)
        # Confidence is already in percentage format (55 means 55%)
        
        # The API checks:
        # - confidence >= 55 (as percentage)
        # - expectedValue > 0 (but then multiplied by 100, so stored as percentage like 10.0)
        # - expectedValue >= 0.10 (but multiplied by 100, so stored as 10.0)
        
        # So in our database, we need to handle:
        # - Confidence: could be 55.0 (percentage) or 0.55 (decimal)
        # - EV: could be 10.0 (percentage) or 0.10 (decimal)
        
        min_confidence_decimal = 0.55
        min_confidence_percent = 55.0
        min_ev_decimal = 0.10  # 10% as decimal
        min_ev_percent = 10.0   # 10% as percentage
        
        filtered_queryset = queryset.filter(
            # Confidence >= 55% (either format)
            (Q(confidence__gte=min_confidence_decimal) | Q(confidence__gte=min_confidence_percent)),
            # EV > 0 (either format)
            (Q(expected_value__gt=min_ev_decimal) | Q(expected_value__gt=min_ev_percent) | Q(expected_value__gt=0)),
            # EV >= 10% (either format)
            (Q(expected_value__gte=min_ev_decimal) | Q(expected_value__gte=min_ev_percent))
        )
        
        # Now we need to score them like the API does:
        # revenueScore = expected_value * (confidence / 100)
        # riskScore = 1 - (confidence / 100)
        # combinedScore = revenueScore - (riskScore * 0.8)
        # qualityBonus = confidence >= 70 ? 0.5 : confidence >= 65 ? 0.3 : confidence >= 60 ? 0.2 : 0
        # evBonus = expected_value >= 0.3 ? 0.2 : expected_value >= 0.15 ? 0.1 : 0
        # revenue_vs_risk_score = combinedScore + qualityBonus + evBonus
        
        predictions_list = []
        for pred in filtered_queryset:
            # Normalize confidence and EV to percentage format for scoring
            confidence = pred.confidence
            if confidence < 1:
                confidence = confidence * 100  # Convert decimal to percentage
            
            ev = pred.expected_value
            if ev < 1:
                ev = ev * 100  # Convert decimal to percentage
            
            # Calculate scores (using percentage values)
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
        
        # Sort by score (highest first) and take top 10
        predictions_list.sort(key=lambda x: x['score'], reverse=True)
        top_10 = predictions_list[:10]
        
        top_10_fixture_ids = [item['prediction'].fixture_id for item in top_10]
        
        self.stdout.write(f'Found {len(predictions_list)} predictions matching criteria')
        self.stdout.write(f'Top 10 fixture IDs to mark as recommended: {top_10_fixture_ids}\n')
        
        if len(top_10) == 0:
            self.stdout.write(self.style.WARNING('No predictions found matching the criteria.'))
            return
        
        self.stdout.write(self.style.SUCCESS('Predictions that will be marked as recommended:'))
        self.stdout.write(self.style.SUCCESS('-'*80))
        
        for i, item in enumerate(top_10, 1):
            pred = item['prediction']
            score = item['score']
            self.stdout.write(
                f'  [{i}] {pred.home_team} vs {pred.away_team} | '
                f'{pred.predicted_outcome} (Conf: {pred.confidence:.1f}%, '
                f'EV: {pred.expected_value:.2f}%) | Score: {score:.2f} | {pred.league}'
            )
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nDRY RUN - No predictions were actually marked'))
            return
        
        # First, unmark all current recommendations if requested
        if unmark_others:
            unmarked_count = PredictionLog.objects.filter(
                is_recommended=True
            ).exclude(
                fixture_id__in=top_10_fixture_ids
            ).update(is_recommended=False)
            
            if unmarked_count > 0:
                self.stdout.write(self.style.WARNING(f'\nUnmarked {unmarked_count} predictions that no longer match criteria'))
        
        # Mark the top 10 as recommended
        updated_count = PredictionLog.objects.filter(
            fixture_id__in=top_10_fixture_ids
        ).update(is_recommended=True)
        
        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully marked {updated_count} predictions as recommended!\n'))
        
        # Show statistics
        total_recommended = PredictionLog.objects.filter(is_recommended=True).count()
        self.stdout.write(f'Total recommended predictions in database: {total_recommended}')

