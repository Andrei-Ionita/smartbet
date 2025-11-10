"""
Accuracy Calculator Service - Comprehensive performance metrics
Calculates accuracy, ROI, and performance statistics for transparency
"""

from django.db.models import Q, Count, Avg, Sum, F
from django.utils import timezone
from datetime import datetime, timedelta
from typing import Dict, List
from decimal import Decimal

from core.models import PredictionLog


class AccuracyCalculator:
    """
    Calculate comprehensive accuracy metrics for SmartBet predictions.
    """
    
    def get_overall_accuracy(self) -> Dict:
        """
        Get overall accuracy across all completed predictions.
        """
        completed = PredictionLog.objects.filter(
            actual_outcome__isnull=False,
            was_correct__isnull=False
        )
        
        total = completed.count()
        correct = completed.filter(was_correct=True).count()
        accuracy = (correct / total * 100) if total > 0 else 0
        
        # Breakdown by outcome
        home_total = completed.filter(predicted_outcome='Home').count()
        home_correct = completed.filter(predicted_outcome='Home', was_correct=True).count()
        home_accuracy = (home_correct / home_total * 100) if home_total > 0 else 0
        
        draw_total = completed.filter(predicted_outcome='Draw').count()
        draw_correct = completed.filter(predicted_outcome='Draw', was_correct=True).count()
        draw_accuracy = (draw_correct / draw_total * 100) if draw_total > 0 else 0
        
        away_total = completed.filter(predicted_outcome='Away').count()
        away_correct = completed.filter(predicted_outcome='Away', was_correct=True).count()
        away_accuracy = (away_correct / away_total * 100) if away_total > 0 else 0
        
        return {
            'overall': {
                'total_predictions': total,
                'correct_predictions': correct,
                'incorrect_predictions': total - correct,
                'accuracy_percent': round(accuracy, 1)
            },
            'by_outcome': {
                'home': {
                    'total': home_total,
                    'correct': home_correct,
                    'accuracy': round(home_accuracy, 1)
                },
                'draw': {
                    'total': draw_total,
                    'correct': draw_correct,
                    'accuracy': round(draw_accuracy, 1)
                },
                'away': {
                    'total': away_total,
                    'correct': away_correct,
                    'accuracy': round(away_accuracy, 1)
                }
            }
        }
    
    def get_accuracy_by_confidence(self) -> List[Dict]:
        """
        Get accuracy breakdown by confidence levels.
        Shows if higher confidence = higher accuracy.
        """
        completed = PredictionLog.objects.filter(
            actual_outcome__isnull=False,
            was_correct__isnull=False
        )
        
        # Define confidence ranges
        ranges = [
            (0.70, 1.00, '70-100%', 'Very High'),
            (0.65, 0.70, '65-70%', 'High'),
            (0.60, 0.65, '60-65%', 'Medium-High'),
            (0.55, 0.60, '55-60%', 'Medium'),
            (0.50, 0.55, '50-55%', 'Low'),
        ]
        
        results = []
        
        for min_conf, max_conf, label, category in ranges:
            preds = completed.filter(confidence__gte=min_conf, confidence__lt=max_conf)
            total = preds.count()
            correct = preds.filter(was_correct=True).count()
            accuracy = (correct / total * 100) if total > 0 else 0
            
            if total > 0:  # Only include ranges with data
                results.append({
                    'confidence_range': label,
                    'category': category,
                    'total': total,
                    'correct': correct,
                    'accuracy': round(accuracy, 1)
                })
        
        return results
    
    def get_accuracy_by_league(self) -> List[Dict]:
        """
        Get accuracy breakdown by league.
        Shows which leagues have best prediction accuracy.
        """
        completed = PredictionLog.objects.filter(
            actual_outcome__isnull=False,
            was_correct__isnull=False
        )
        
        # Get unique leagues
        leagues = completed.values_list('league', flat=True).distinct()
        
        results = []
        
        for league in leagues:
            league_preds = completed.filter(league=league)
            total = league_preds.count()
            correct = league_preds.filter(was_correct=True).count()
            accuracy = (correct / total * 100) if total > 0 else 0
            
            # Calculate ROI for this league
            roi_predictions = league_preds.filter(profit_loss_10__isnull=False)
            total_pl = sum(float(p.profit_loss_10) for p in roi_predictions)
            roi = (total_pl / (total * 10) * 100) if total > 0 else 0
            
            results.append({
                'league': league,
                'total_predictions': total,
                'correct_predictions': correct,
                'accuracy_percent': round(accuracy, 1),
                'roi_percent': round(roi, 1)
            })
        
        # Sort by total predictions (most active leagues first)
        results.sort(key=lambda x: x['total_predictions'], reverse=True)
        
        return results
    
    def get_roi_simulation(self, stake_per_bet: float = 10.0) -> Dict:
        """
        Calculate theoretical ROI if user followed all recommendations.
        
        Args:
            stake_per_bet: Stake amount per bet (default $10)
        
        Returns:
            Dictionary with ROI calculations
        """
        completed = PredictionLog.objects.filter(
            actual_outcome__isnull=False,
            is_recommended=True,  # Only recommendations shown to users
            profit_loss_10__isnull=False
        )
        
        total_bets = completed.count()
        total_staked = total_bets * stake_per_bet
        
        # Calculate total P/L
        total_pl = sum(
            float(pred.profit_loss_10 or 0) * (stake_per_bet / 10)
            for pred in completed
        )
        
        roi = (total_pl / total_staked * 100) if total_staked > 0 else 0
        
        # Calculate by outcome type
        wins = completed.filter(was_correct=True).count()
        losses = completed.filter(was_correct=False).count()
        win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
        
        return {
            'total_bets': total_bets,
            'total_staked': round(total_staked, 2),
            'total_profit_loss': round(total_pl, 2),
            'roi_percent': round(roi, 1),
            'wins': wins,
            'losses': losses,
            'win_rate': round(win_rate, 1),
            'avg_profit_per_bet': round(total_pl / total_bets, 2) if total_bets > 0 else 0,
            'stake_per_bet': stake_per_bet
        }
    
    def get_performance_over_time(self, days: int = 30) -> List[Dict]:
        """
        Get accuracy performance over time periods.
        
        Args:
            days: Number of days to look back
        
        Returns:
            List of daily/weekly performance data
        """
        cutoff_date = timezone.now() - timedelta(days=days)
        
        completed = PredictionLog.objects.filter(
            actual_outcome__isnull=False,
            kickoff__gte=cutoff_date
        ).order_by('kickoff')
        
        # Group by week
        results = []
        current_week_start = None
        week_data = {'correct': 0, 'total': 0, 'week_start': None}
        
        for pred in completed:
            # Get week start (Monday)
            week_start = pred.kickoff.date() - timedelta(days=pred.kickoff.weekday())
            
            if current_week_start != week_start:
                # Save previous week
                if week_data['total'] > 0:
                    week_data['accuracy'] = round((week_data['correct'] / week_data['total']) * 100, 1)
                    results.append(week_data.copy())
                
                # Start new week
                current_week_start = week_start
                week_data = {
                    'week_start': week_start.isoformat(),
                    'correct': 0,
                    'total': 0
                }
            
            week_data['total'] += 1
            if pred.was_correct:
                week_data['correct'] += 1
        
        # Add last week
        if week_data['total'] > 0:
            week_data['accuracy'] = round((week_data['correct'] / week_data['total']) * 100, 1)
            results.append(week_data)
        
        return results
    
    def get_comprehensive_stats(self) -> Dict:
        """
        Get all statistics in one call for dashboard.
        """
        return {
            'overall_accuracy': self.get_overall_accuracy(),
            'accuracy_by_confidence': self.get_accuracy_by_confidence(),
            'accuracy_by_league': self.get_accuracy_by_league(),
            'roi_simulation': self.get_roi_simulation(stake_per_bet=10.0),
            'last_30_days': self.get_performance_over_time(days=30),
            'timestamp': timezone.now().isoformat()
        }

