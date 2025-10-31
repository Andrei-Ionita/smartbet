from rest_framework import serializers
from .models import PredictionLog, PerformanceSnapshot
from django.utils import timezone
import hashlib


class PredictionLogSerializer(serializers.ModelSerializer):
    """Serializer for PredictionLog model"""
    
    class Meta:
        model = PredictionLog
        fields = [
            'id', 'fixture_id', 'home_team', 'away_team', 'league', 'league_id',
            'kickoff', 'predicted_outcome', 'confidence', 'probability_home',
            'probability_draw', 'probability_away', 'odds_home', 'odds_draw',
            'odds_away', 'bookmaker', 'expected_value', 'model_count',
            'consensus', 'variance', 'ensemble_strategy', 'actual_outcome',
            'actual_score_home', 'actual_score_away', 'match_status',
            'was_correct', 'profit_loss_10', 'roi_percent',
            'prediction_logged_at', 'result_logged_at', 'recommendation_score', 'notes'
        ]


class PerformanceSnapshotSerializer(serializers.ModelSerializer):
    """Serializer for PerformanceSnapshot model"""
    
    class Meta:
        model = PerformanceSnapshot
        fields = [
            'id', 'snapshot_date', 'total_predictions', 'correct_predictions',
            'accuracy_percent', 'home_predictions', 'home_correct', 'home_accuracy',
            'draw_predictions', 'draw_correct', 'draw_accuracy', 'away_predictions',
            'away_correct', 'away_accuracy', 'total_profit_loss', 'roi_percent',
            'high_confidence_predictions', 'high_confidence_correct', 'high_confidence_accuracy',
            'medium_confidence_predictions', 'medium_confidence_correct', 'medium_confidence_accuracy',
            'low_confidence_predictions', 'low_confidence_correct', 'low_confidence_accuracy',
            'created_at', 'updated_at'
        ] 