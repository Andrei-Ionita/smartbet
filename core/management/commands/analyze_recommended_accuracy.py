"""
Management command to analyze accuracy of recommended vs non-recommended predictions.
This is crucial for tracking the performance of predictions we actually recommend to users.
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Avg, Q, Sum, FloatField
from django.db.models.functions import Cast
from core.models import PredictionLog


class Command(BaseCommand):
    help = 'Analyze accuracy of recommended vs non-recommended predictions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--league',
            type=str,
            help='Filter by league name'
        )
        parser.add_argument(
            '--min-confidence',
            type=float,
            help='Minimum confidence threshold for analysis'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '='*80))
        self.stdout.write(self.style.SUCCESS('📊 RECOMMENDED vs NON-RECOMMENDED PREDICTION ACCURACY ANALYSIS'))
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))

        # Build base query
        base_query = PredictionLog.objects.filter(actual_outcome__isnull=False)
        
        if options['league']:
            base_query = base_query.filter(league__icontains=options['league'])
            self.stdout.write(self.style.WARNING(f'Filtering by league: {options["league"]}\n'))
        
        if options.get('min_confidence'):
            base_query = base_query.filter(confidence__gte=options['min_confidence'])
            self.stdout.write(self.style.WARNING(f'Filtering by min confidence: {options["min_confidence"]}%\n'))

        # RECOMMENDED PREDICTIONS ANALYSIS
        recommended = base_query.filter(is_recommended=True)
        recommended_total = recommended.count()
        recommended_correct = recommended.filter(was_correct=True).count()
        recommended_incorrect = recommended.filter(was_correct=False).count()
        recommended_accuracy = (recommended_correct / recommended_total * 100) if recommended_total > 0 else 0
        
        # Financial metrics for recommended
        recommended_profit = recommended.aggregate(
            total=Sum('profit_loss_10')
        )['total'] or 0
        recommended_roi = recommended.aggregate(
            avg_roi=Avg('roi_percent')
        )['avg_roi'] or 0
        recommended_avg_confidence = recommended.aggregate(
            avg_conf=Avg('confidence')
        )['avg_conf'] or 0
        recommended_avg_ev = recommended.aggregate(
            avg_ev=Avg('expected_value')
        )['avg_ev'] or 0

        # NON-RECOMMENDED PREDICTIONS ANALYSIS
        non_recommended = base_query.filter(is_recommended=False)
        non_recommended_total = non_recommended.count()
        non_recommended_correct = non_recommended.filter(was_correct=True).count()
        non_recommended_incorrect = non_recommended.filter(was_correct=False).count()
        non_recommended_accuracy = (non_recommended_correct / non_recommended_total * 100) if non_recommended_total > 0 else 0
        
        # Financial metrics for non-recommended
        non_recommended_profit = non_recommended.aggregate(
            total=Sum('profit_loss_10')
        )['total'] or 0
        non_recommended_roi = non_recommended.aggregate(
            avg_roi=Avg('roi_percent')
        )['avg_roi'] or 0
        non_recommended_avg_confidence = non_recommended.aggregate(
            avg_conf=Avg('confidence')
        )['avg_conf'] or 0
        non_recommended_avg_ev = non_recommended.aggregate(
            avg_ev=Avg('expected_value')
        )['avg_ev'] or 0

        # OVERALL ANALYSIS
        overall_total = recommended_total + non_recommended_total
        overall_correct = recommended_correct + non_recommended_correct
        overall_accuracy = (overall_correct / overall_total * 100) if overall_total > 0 else 0

        # Display Results
        self.stdout.write(self.style.SUCCESS('🎯 RECOMMENDED PREDICTIONS (CRITICAL - These are what we recommend to users)'))
        self.stdout.write(self.style.SUCCESS('-'*80))
        if recommended_total > 0:
            self.stdout.write(f'   Total Recommended Predictions: {recommended_total}')
            self.stdout.write(f'   ✅ Correct: {recommended_correct}')
            self.stdout.write(f'   ❌ Incorrect: {recommended_incorrect}')
            
            # Highlight accuracy with color coding
            if recommended_accuracy >= 80:
                accuracy_style = self.style.SUCCESS
                accuracy_status = 'EXCELLENT ⭐⭐⭐'
            elif recommended_accuracy >= 70:
                accuracy_style = self.style.SUCCESS
                accuracy_status = 'VERY GOOD ⭐⭐'
            elif recommended_accuracy >= 60:
                accuracy_style = self.style.WARNING
                accuracy_status = 'GOOD ⭐'
            elif recommended_accuracy >= 50:
                accuracy_style = self.style.WARNING
                accuracy_status = 'NEEDS IMPROVEMENT ⚠️'
            else:
                accuracy_style = self.style.ERROR
                accuracy_status = 'CRITICAL - BELOW 50% ⚠️⚠️⚠️'
            
            self.stdout.write(accuracy_style(f'   📈 Accuracy: {recommended_accuracy:.2f}% - {accuracy_status}'))
            self.stdout.write(f'   💰 Total P/L ($10 stakes): ${recommended_profit:.2f}')
            self.stdout.write(f'   📊 Average ROI: {recommended_roi:.2f}%')
            self.stdout.write(f'   🎲 Average Confidence: {recommended_avg_confidence:.2f}%')
            self.stdout.write(f'   📉 Average Expected Value: {recommended_avg_ev:.2f}%')
        else:
            self.stdout.write(self.style.WARNING('   ⚠️  No recommended predictions with results yet'))
        
        self.stdout.write('')

        self.stdout.write(self.style.HTTP_INFO('📋 NON-RECOMMENDED PREDICTIONS (For comparison)'))
        self.stdout.write(self.style.HTTP_INFO('-'*80))
        if non_recommended_total > 0:
            self.stdout.write(f'   Total Non-Recommended Predictions: {non_recommended_total}')
            self.stdout.write(f'   ✅ Correct: {non_recommended_correct}')
            self.stdout.write(f'   ❌ Incorrect: {non_recommended_incorrect}')
            self.stdout.write(f'   📈 Accuracy: {non_recommended_accuracy:.2f}%')
            self.stdout.write(f'   💰 Total P/L ($10 stakes): ${non_recommended_profit:.2f}')
            self.stdout.write(f'   📊 Average ROI: {non_recommended_roi:.2f}%')
            self.stdout.write(f'   🎲 Average Confidence: {non_recommended_avg_confidence:.2f}%')
            self.stdout.write(f'   📉 Average Expected Value: {non_recommended_avg_ev:.2f}%')
        else:
            self.stdout.write(self.style.WARNING('   ⚠️  No non-recommended predictions with results yet'))
        
        self.stdout.write('')

        # Comparison
        self.stdout.write(self.style.SUCCESS('⚖️  COMPARISON'))
        self.stdout.write(self.style.SUCCESS('-'*80))
        if recommended_total > 0 and non_recommended_total > 0:
            accuracy_diff = recommended_accuracy - non_recommended_accuracy
            if accuracy_diff > 0:
                self.stdout.write(self.style.SUCCESS(
                    f'   ✅ Recommended predictions are {accuracy_diff:.2f}% MORE accurate'
                ))
            elif accuracy_diff < 0:
                self.stdout.write(self.style.ERROR(
                    f'   ❌ Recommended predictions are {abs(accuracy_diff):.2f}% LESS accurate (CRITICAL ISSUE!)'
                ))
            else:
                self.stdout.write('   ➡️  Recommended and non-recommended have similar accuracy')
            
            profit_diff = recommended_profit - non_recommended_profit
            if profit_diff > 0:
                self.stdout.write(self.style.SUCCESS(
                    f'   💰 Recommended predictions are ${profit_diff:.2f} MORE profitable'
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f'   💰 Recommended predictions are ${abs(profit_diff):.2f} LESS profitable'
                ))
        
        self.stdout.write('')

        # Overall Summary
        self.stdout.write(self.style.SUCCESS('📊 OVERALL SUMMARY'))
        self.stdout.write(self.style.SUCCESS('-'*80))
        self.stdout.write(f'   Total Predictions Analyzed: {overall_total}')
        self.stdout.write(f'   ✅ Overall Correct: {overall_correct}')
        self.stdout.write(f'   📈 Overall Accuracy: {overall_accuracy:.2f}%')
        self.stdout.write(f'   📊 Recommended: {recommended_total} ({recommended_total/overall_total*100:.1f}%)' if overall_total > 0 else '   📊 Recommended: 0')
        self.stdout.write(f'   📊 Non-Recommended: {non_recommended_total} ({non_recommended_total/overall_total*100:.1f}%)' if overall_total > 0 else '   📊 Non-Recommended: 0')
        
        self.stdout.write('')

        # Recommendations
        self.stdout.write(self.style.SUCCESS('💡 RECOMMENDATIONS'))
        self.stdout.write(self.style.SUCCESS('-'*80))
        if recommended_total > 0:
            if recommended_accuracy < 60:
                self.stdout.write(self.style.ERROR(
                    '   ⚠️  CRITICAL: Recommended prediction accuracy is below 60%!'
                ))
                self.stdout.write(self.style.ERROR(
                    '      Action: Review recommendation criteria - confidence thresholds, EV thresholds, etc.'
                ))
            elif recommended_accuracy < 70:
                self.stdout.write(self.style.WARNING(
                    '   ⚠️  Recommended prediction accuracy is below 70%'
                ))
                self.stdout.write(self.style.WARNING(
                    '      Action: Consider tightening recommendation criteria for higher accuracy'
                ))
            elif recommended_accuracy >= 80:
                self.stdout.write(self.style.SUCCESS(
                    '   ✅ Excellent accuracy on recommended predictions!'
                ))
            
            if recommended_accuracy < non_recommended_accuracy:
                self.stdout.write(self.style.ERROR(
                    '   ⚠️  CRITICAL: Recommended predictions are LESS accurate than non-recommended!'
                ))
                self.stdout.write(self.style.ERROR(
                    '      Action: Urgently review and fix recommendation selection criteria'
                ))
        else:
            self.stdout.write(self.style.WARNING(
                '   ⚠️  No recommended predictions with results yet'
            ))
            self.stdout.write(self.style.WARNING(
                '      Action: Wait for recommended predictions to complete and check again'
            ))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('='*80 + '\n'))

