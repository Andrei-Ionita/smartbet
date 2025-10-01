"""
Django management command to test ML model predictions on upcoming matches.

This command picks upcoming matches with odds and runs model predictions,
displaying probabilities, predicted outcomes, EV, and confidence levels.
"""

import logging
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q

from core.models import Match, OddsSnapshot
from predictor.ml_model import MatchPredictionModel
from predictor.scoring_model import calculate_expected_value

# Configure logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test ML model predictions on upcoming matches with odds'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=5,
            help='Number of upcoming matches to test (default: 5)',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Look for matches in the next N days (default: 7)',
        )
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.0,
            help='Minimum confidence threshold (0.0-1.0)',
        )

    def get_confidence_badge(self, confidence: float) -> str:
        """Get confidence badge based on confidence score."""
        if confidence >= 0.3:
            return "🔥 HIGH"
        elif confidence >= 0.15:
            return "⚡ MEDIUM"
        else:
            return "💭 LOW"

    def get_ev_badge(self, ev: float) -> str:
        """Get EV badge based on expected value."""
        if ev >= 10:
            return "💰 EXCELLENT"
        elif ev >= 5:
            return "✅ GOOD"
        elif ev >= 1:
            return "📈 POSITIVE"
        elif ev >= -1:
            return "➖ NEUTRAL"
        else:
            return "❌ NEGATIVE"

    def format_probability(self, prob: float) -> str:
        """Format probability as percentage."""
        return f"{prob:.3f} ({prob*100:.1f}%)"

    def handle(self, *args, **options):
        count = options.get('count')
        days = options.get('days')
        min_confidence = options.get('min_confidence')
        
        self.stdout.write(self.style.SUCCESS(f"🔮 Testing ML Model Predictions"))
        self.stdout.write(f"Looking for {count} matches in the next {days} days...")
        
        # Find upcoming matches with odds
        now = timezone.now()
        end_date = now + timedelta(days=days)
        
        matches_with_odds = Match.objects.filter(
            status="NS",  # Not Started
            kickoff__gte=now,
            kickoff__lte=end_date,
            odds_snapshots__isnull=False
        ).distinct().order_by('kickoff')[:count * 2]  # Get more than needed to filter
        
        if not matches_with_odds.exists():
            self.stdout.write(self.style.WARNING("❌ No upcoming matches with odds found"))
            return
        
        # Load the ML model
        try:
            model = MatchPredictionModel()
            self.stdout.write(f"✅ Loaded ML model: {model.training_metadata.get('version', 'unknown')}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to load ML model: {e}"))
            return
        
        predictions_made = 0
        
        self.stdout.write(self.style.SUCCESS(f"\n🎯 === MODEL PREDICTIONS ===\n"))
        
        for match in matches_with_odds:
            if predictions_made >= count:
                break
                
            try:
                # Get the latest odds for this match
                latest_odds = match.odds_snapshots.order_by('-fetched_at').first()
                
                if not latest_odds:
                    continue
                
                # Prepare features for prediction
                features = {
                    'odds_home': latest_odds.odds_home,
                    'odds_draw': latest_odds.odds_draw,
                    'odds_away': latest_odds.odds_away,
                    'league_id': match.league.api_id if match.league.api_id else 274,
                    'team_home_rating': getattr(match, 'team_home_rating', 75),
                    'team_away_rating': getattr(match, 'team_away_rating', 73),
                    'injured_home_starters': match.injured_starters_home or 0,
                    'injured_away_starters': match.injured_starters_away or 0,
                    'recent_form_diff': getattr(match, 'recent_form_diff', 0),
                    'home_goals_avg': match.avg_goals_home or 1.5,
                    'away_goals_avg': match.avg_goals_away or 1.3,
                }
                
                # Get model predictions
                home_prob, draw_prob, away_prob = model.predict_outcome_probabilities(features)
                
                # Calculate confidence
                probabilities = (home_prob, draw_prob, away_prob)
                confidence = model.get_confidence(probabilities)
                
                # Skip if below minimum confidence threshold
                if confidence < min_confidence:
                    continue
                
                # Get predicted outcome
                predicted_outcome = model.get_predicted_outcome(probabilities)
                
                # Calculate Expected Value for the predicted outcome
                odds_map = {
                    'home': latest_odds.odds_home,
                    'draw': latest_odds.odds_draw,
                    'away': latest_odds.odds_away
                }
                prob_map = {
                    'home': home_prob,
                    'draw': draw_prob,
                    'away': away_prob
                }
                
                predicted_odds = odds_map[predicted_outcome]
                predicted_prob = prob_map[predicted_outcome]
                
                # Calculate EV: (probability * (odds - 1)) - (1 - probability)
                ev = (predicted_prob * (predicted_odds - 1)) - (1 - predicted_prob)
                ev_percentage = ev * 100
                
                # Format output
                match_title = f"{match.home_team.name_en} vs {match.away_team.name_en}"
                kickoff_str = match.kickoff.strftime("%Y-%m-%d %H:%M")
                
                self.stdout.write(self.style.SUCCESS(f"⚽ {match_title}"))
                self.stdout.write(f"📅 {kickoff_str} | 🏟️ {match.venue or 'TBD'}")
                
                # Probabilities
                self.stdout.write(f"🏠 Home: {self.format_probability(home_prob)}")
                self.stdout.write(f"🤝 Draw: {self.format_probability(draw_prob)}")
                self.stdout.write(f"✈️ Away: {self.format_probability(away_prob)}")
                
                # Odds
                self.stdout.write(f"📊 Odds: H={latest_odds.odds_home:.2f}, D={latest_odds.odds_draw:.2f}, A={latest_odds.odds_away:.2f}")
                
                # Prediction
                outcome_emoji = {"home": "🏠", "draw": "🤝", "away": "✈️"}
                prediction_line = f"🎯 Pick: {outcome_emoji[predicted_outcome]} {predicted_outcome.upper()}"
                
                # EV and Confidence
                ev_badge = self.get_ev_badge(ev_percentage)
                confidence_badge = self.get_confidence_badge(confidence)
                
                prediction_line += f" (EV: {ev_percentage:+.1f}%) | Confidence: {confidence_badge}"
                
                # Color code based on EV
                if ev_percentage >= 5:
                    self.stdout.write(self.style.SUCCESS(prediction_line))
                elif ev_percentage >= 1:
                    self.stdout.write(self.style.WARNING(prediction_line))
                else:
                    self.stdout.write(prediction_line)
                
                # Additional insights
                if latest_odds.opening_odds_home and latest_odds.closing_odds_home:
                    opening_odds = getattr(latest_odds, f'opening_odds_{predicted_outcome}')
                    closing_odds = getattr(latest_odds, f'closing_odds_{predicted_outcome}')
                    if opening_odds and closing_odds:
                        odds_movement = closing_odds - opening_odds
                        movement_emoji = "📈" if odds_movement > 0 else "📉" if odds_movement < 0 else "➡️"
                        self.stdout.write(f"📊 Odds Movement: {movement_emoji} {odds_movement:+.2f}")
                
                self.stdout.write("─" * 60)
                
                predictions_made += 1
                
            except Exception as e:
                logger.error(f"Error processing match {match.id}: {e}")
                self.stdout.write(self.style.ERROR(f"❌ Error processing {match}: {e}"))
                continue
        
        # Summary
        if predictions_made == 0:
            self.stdout.write(self.style.WARNING("❌ No predictions made (no matches met criteria)"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\n✅ Generated {predictions_made} predictions"))
            
            if min_confidence > 0:
                self.stdout.write(f"🎯 Filtered by minimum confidence: {min_confidence:.2f}")
            
            # Model info
            model_info = model.training_metadata
            if model_info:
                trained_at = model_info.get('trained_at', 'unknown')
                model_type = model_info.get('model_type', 'unknown')
                self.stdout.write(f"🤖 Model: {model_type} (trained: {trained_at})")
                
                # Show model performance if available
                metrics = model_info.get('metrics', {})
                if metrics:
                    accuracy = metrics.get('accuracy', 0)
                    self.stdout.write(f"📈 Model Accuracy: {accuracy:.3f}")
        
        self.stdout.write(self.style.SUCCESS("\n🎉 Prediction testing completed!")) 