"""
Django Management Command: Load Premium Model
Test and initialize the premium ML model for SmartBet
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from core.ml_model_manager import premium_model_manager
from core.models import Match, OddsSnapshot
import json


class Command(BaseCommand):
    help = 'Load and test the premium ML model for SmartBet predictions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-predictions',
            action='store_true',
            help='Test predictions on sample matches',
        )
        parser.add_argument(
            '--force-reload',
            action='store_true',
            help='Force reload the model even if already loaded',
        )
        parser.add_argument(
            '--model-info',
            action='store_true',
            help='Display model information only',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🚀 PREMIUM MODEL LOADER - SmartBet Django Integration')
        )
        self.stdout.write('=' * 60)

        # Load model
        if options['model_info'] and premium_model_manager.is_loaded:
            self.display_model_info()
            return

        self.stdout.write('📥 Loading premium model...')
        
        success = premium_model_manager.load_model(force_reload=options['force_reload'])
        
        if not success:
            raise CommandError('❌ Failed to load premium model')
        
        self.stdout.write(
            self.style.SUCCESS('✅ Premium model loaded successfully!')
        )
        
        # Display model information
        self.display_model_info()
        
        # Test predictions if requested
        if options['test_predictions']:
            self.test_predictions()
        
        self.stdout.write(
            self.style.SUCCESS('\n🎉 Premium model is ready for production use!')
        )

    def display_model_info(self):
        """Display information about the loaded model."""
        self.stdout.write('\n📊 MODEL INFORMATION:')
        self.stdout.write('-' * 30)
        
        model_info = premium_model_manager.get_model_info()
        
        if model_info['status'] == 'not_loaded':
            self.stdout.write(self.style.ERROR('❌ Model not loaded'))
            return
        elif model_info['status'] == 'error':
            self.stdout.write(self.style.ERROR(f'❌ Error: {model_info["error"]}'))
            return
        
        self.stdout.write(f'✅ Status: {model_info["status"]}')
        self.stdout.write(f'🏷️  Version: {model_info["version"]}')
        self.stdout.write(f'🎯 Accuracy: {model_info["accuracy"]:.3f} ({model_info["accuracy"]*100:.1f}%)')
        self.stdout.write(f'🏆 Features: {model_info["feature_count"]}')
        self.stdout.write(f'📊 Classes: {model_info["classes"]}')
        self.stdout.write(f'📈 Training samples: {model_info["training_samples"]:,}')
        self.stdout.write(f'📅 Created: {model_info["created_at"][:19]}')
        self.stdout.write(f'📁 Location: {model_info["model_path"]}')

    def test_predictions(self):
        """Test predictions on sample matches."""
        self.stdout.write('\n🧪 TESTING PREDICTIONS:')
        self.stdout.write('-' * 30)
        
        # Get sample matches with odds
        matches = Match.objects.filter(
            status='NS',
            odds_snapshots__isnull=False,
            kickoff__gte=timezone.now()
        ).distinct()[:5]
        
        if not matches.exists():
            self.stdout.write(self.style.WARNING('⚠️ No suitable matches found for testing'))
            
            # Create a test prediction on any match with odds
            matches = Match.objects.filter(
                odds_snapshots__isnull=False
            ).distinct()[:3]
            
            if not matches.exists():
                self.stdout.write(self.style.ERROR('❌ No matches with odds found in database'))
                return
        
        self.stdout.write(f'📊 Testing on {matches.count()} matches...\n')
        
        predictions = premium_model_manager.predict_batch(list(matches))
        
        if not predictions:
            self.stdout.write(self.style.ERROR('❌ No predictions generated'))
            return
        
        for i, prediction in enumerate(predictions, 1):
            match_info = prediction['match_info']
            probs = prediction['probabilities']
            
            self.stdout.write(f'🎯 Match {i}: {match_info["home_team"]} vs {match_info["away_team"]}')
            self.stdout.write(f'   🏆 League: {match_info["league"]}')
            self.stdout.write(f'   ⏰ Kickoff: {match_info["kickoff"][:16]}')
            self.stdout.write(f'   🎲 Prediction: {prediction["predicted_outcome"].upper()}')
            self.stdout.write(f'   📊 Confidence: {prediction["confidence"].upper()}')
            self.stdout.write(f'   🎯 Probabilities:')
            self.stdout.write(f'      🏠 Home: {probs["home"]:.3f} ({probs["home"]*100:.1f}%)')
            self.stdout.write(f'      ⚖️  Draw: {probs["draw"]:.3f} ({probs["draw"]*100:.1f}%)')
            self.stdout.write(f'      ✈️  Away: {probs["away"]:.3f} ({probs["away"]*100:.1f}%)')
            self.stdout.write(f'   🚀 Max probability: {prediction["max_probability"]:.3f}')
            self.stdout.write('')

        self.stdout.write(
            self.style.SUCCESS(f'✅ Generated {len(predictions)} predictions successfully!')
        ) 