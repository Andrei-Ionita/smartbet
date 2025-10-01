import random
import logging # For logging errors
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, IntegrityError
from django.utils import timezone # For timezone.now() if created_at wasn't auto_now_add
from core.models import Match, Prediction, Team # Assuming Team model is needed for features

# Get an instance of a logger
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generates mock predictions for matches that do not have any.'

    MODEL_VERSION = "v0.1-mock"

    def _generate_dummy_features(self, match: Match) -> dict:
        """
        Generates a dictionary of dummy features for a given match.
        - Team "embeddings" are represented by a simple hash of their names.
        - Kickoff weekday is an integer (0=Monday, 6=Sunday).
        """
        home_team_name_feature = hash(match.home_team.name_ro) % 1000  # Example hash feature
        away_team_name_feature = hash(match.away_team.name_ro) % 1000  # Example hash feature
        kickoff_weekday_feature = match.kickoff.weekday()
        
        return {
            "home_team_name_hash": home_team_name_feature,
            "away_team_name_hash": away_team_name_feature,
            "kickoff_weekday": kickoff_weekday_feature,
            # In a real scenario, these features would be structured for a model
        }

    def _mock_model_predict_proba(self, features: dict) -> list[float]:
        """
        Mocks a pre-trained model's prediction.
        Outputs a list of [prob_home, prob_draw, prob_away].
        For now, uses random normalized values.
        The input 'features' are not used in this mock version but are
        included to show the conceptual flow.
        """
        # Example fixed probabilities
        # return [0.55, 0.25, 0.20] 

        # Using random normalized values as per previous implementation
        rand_vals = [random.random() for _ in range(3)]
        total = sum(rand_vals)
        
        if total == 0: 
            return [1/3, 1/3, 1/3]
            
        prob_home = rand_vals[0] / total
        prob_draw = rand_vals[1] / total
        prob_away = rand_vals[2] / total
        
        return [prob_home, prob_draw, prob_away]

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Starting prediction process for matches without predictions...")

        # Updated queryset to find matches without any Prediction records.
        # This gets a list of all Match IDs that *do* have predictions,
        # and then excludes them from the Match queryset.
        predicted_match_ids = Prediction.objects.values_list('match_id', flat=True).distinct()
        matches_to_predict = Match.objects.exclude(id__in=predicted_match_ids)
        
        if not matches_to_predict.exists():
            self.stdout.write(self.style.SUCCESS("No matches found requiring predictions."))
            return

        self.stdout.write(f"Found {matches_to_predict.count()} matches to predict.")
        
        predictions_created_count = 0
        predictions_failed_count = 0
        
        for match in matches_to_predict: # This loop will now use the corrected queryset
            self.stdout.write(f"Processing Match ID: {match.id} ({match.home_team.name_ro} vs {match.away_team.name_ro})") # Corrected away_team to match.away_team

            try:
                # 1. Generate dummy features (optional for this mock, but good practice for structure)
                features = self._generate_dummy_features(match)

                # 2. Get mocked model prediction
                probabilities = self._mock_model_predict_proba(features)
                prob_home, prob_draw, prob_away = probabilities
            
                # 3. Set confidence
                confidence = max(prob_home, prob_draw, prob_away)
            
                # 4. Save the prediction
                Prediction.objects.create(
                    match=match,
                    model_version=self.MODEL_VERSION,
                    prob_home=prob_home,
                    prob_draw=prob_draw,
                    prob_away=prob_away,
                    confidence=confidence
                )
                predictions_created_count += 1
                self.stdout.write(f"  Successfully created prediction: H={prob_home:.2f}, D={prob_draw:.2f}, A={prob_away:.2f}, Conf={confidence:.2f}")

            except IntegrityError as e:
                self.stderr.write(self.style.ERROR(f"  Failed to create prediction for Match ID {match.id} due to IntegrityError: {e}"))
                logger.error(f"IntegrityError for Match ID {match.id}: {e}", exc_info=True)
                predictions_failed_count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  Failed to create prediction for Match ID {match.id}: {e}"))
                logger.error(f"Unexpected error for Match ID {match.id}: {e}", exc_info=True)
                predictions_failed_count += 1


        if predictions_failed_count > 0:
            self.stdout.write(self.style.WARNING(f"Process completed. Created: {predictions_created_count}, Failed: {predictions_failed_count} predictions."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully created {predictions_created_count} predictions.")) 