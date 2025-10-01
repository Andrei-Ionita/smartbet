"""
Django management command for automated ML model retraining.

This command runs the complete retraining pipeline:
1. Sync real-time data
2. Generate training dataset
3. Train the ML model
4. Save training reports and metrics
"""

import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.utils import timezone

# Configure logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Automated ML model retraining pipeline'

    def add_arguments(self, parser):
        parser.add_argument(
            '--months',
            type=int,
            default=24,
            help='Number of months of historical data to include (default: 24)',
        )
        parser.add_argument(
            '--cv',
            type=int,
            default=5,
            help='Number of cross-validation folds (default: 5)',
        )
        parser.add_argument(
            '--save-report',
            action='store_true',
            help='Save detailed training summary to timestamped file',
        )
        parser.add_argument(
            '--skip-sync',
            action='store_true',
            help='Skip the data sync step (use existing data)',
        )
        parser.add_argument(
            '--demo',
            action='store_true',
            help='Use demo mode for data sync',
        )

    def log_with_timestamp(self, message, level='info'):
        """Log message with timestamp."""
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        
        if level == 'info':
            self.stdout.write(self.style.SUCCESS(log_message))
            logger.info(message)
        elif level == 'warning':
            self.stdout.write(self.style.WARNING(log_message))
            logger.warning(message)
        elif level == 'error':
            self.stdout.write(self.style.ERROR(log_message))
            logger.error(message)

    def handle(self, *args, **options):
        start_time = time.time()
        
        # Extract options
        months = options.get('months')
        cv_folds = options.get('cv')
        save_report = options.get('save_report')
        skip_sync = options.get('skip_sync')
        demo_mode = options.get('demo')
        
        self.log_with_timestamp("🚀 Starting automated ML model retraining pipeline...")
        
        # Step 1: Sync real-time data (unless skipped)
        if not skip_sync:
            try:
                self.log_with_timestamp("📡 Step 1/3: Syncing real-time data...")
                
                sync_args = []
                if demo_mode:
                    sync_args.append('--demo')
                
                call_command('sync_realtime_data', *sync_args)
                self.log_with_timestamp("✅ Data sync completed successfully")
                
            except Exception as e:
                self.log_with_timestamp(f"❌ Error in data sync: {e}", level='error')
                raise CommandError("Failed to sync real-time data")
        else:
            self.log_with_timestamp("⏭️ Skipping data sync step")
        
        # Step 2: Generate training dataset
        try:
            self.log_with_timestamp(f"🔄 Step 2/3: Generating training dataset ({months} months)...")
            
            call_command('generate_training_data', '--months', str(months))
            self.log_with_timestamp("✅ Training dataset generated successfully")
            
        except Exception as e:
            self.log_with_timestamp(f"❌ Error generating training data: {e}", level='error')
            raise CommandError("Failed to generate training dataset")
        
        # Step 3: Train the model
        try:
            self.log_with_timestamp(f"🧠 Step 3/3: Training ML model (CV={cv_folds})...")
            
            call_command('train_smartbet_model', '--refresh', '--cv', str(cv_folds))
            self.log_with_timestamp("✅ Model training completed successfully")
            
        except Exception as e:
            self.log_with_timestamp(f"❌ Error training model: {e}", level='error')
            raise CommandError("Failed to train ML model")
        
        # Load and display training metrics
        try:
            self.log_with_timestamp("📊 Loading training metrics...")
            
            # Load the training report
            base_dir = Path(__file__).resolve().parent.parent.parent.parent
            report_path = base_dir / "predictor" / "training_report.json"
            
            if report_path.exists():
                with open(report_path, 'r') as f:
                    report = json.load(f)
                
                # Display key metrics
                metrics = report.get('metrics', {})
                ev_dist = report.get('ev_distribution', {})
                cm_summary = report.get('confusion_matrix_summary', {})
                
                self.stdout.write(self.style.SUCCESS("\n🎯 === TRAINING RESULTS ==="))
                
                # Core metrics
                if metrics:
                    accuracy = metrics.get('accuracy', 0)
                    log_loss = metrics.get('log_loss', 0)
                    self.stdout.write(f"📈 Accuracy: {accuracy:.4f}")
                    self.stdout.write(f"📉 Log Loss: {log_loss:.4f}")
                
                # Confusion matrix summary
                if cm_summary:
                    total = cm_summary.get('total_predictions', 0)
                    self.stdout.write(f"🔢 Total Predictions: {total}")
                    self.stdout.write(f"🏠 Home Precision: {cm_summary.get('home_precision', 0):.4f}")
                    self.stdout.write(f"🤝 Draw Precision: {cm_summary.get('draw_precision', 0):.4f}")
                    self.stdout.write(f"✈️ Away Precision: {cm_summary.get('away_precision', 0):.4f}")
                
                # EV distribution
                if ev_dist:
                    high_ev = ev_dist.get('high_ev_percentage', 0)
                    avg_ev = ev_dist.get('average_ev', 0)
                    profitable = ev_dist.get('profitable_picks', 0)
                    self.stdout.write(f"💰 High EV Picks: {high_ev:.1f}%")
                    self.stdout.write(f"📊 Average EV: {avg_ev:.1f}%")
                    self.stdout.write(f"💵 Profitable Picks: {profitable:.1f}%")
                
                # Model info
                model_type = report.get('model_type', 'unknown')
                version = report.get('version', 'unknown')
                trained_at = report.get('trained_at', 'unknown')
                
                self.stdout.write(f"🤖 Model Type: {model_type}")
                self.stdout.write(f"🏷️ Version: {version}")
                self.stdout.write(f"⏰ Trained At: {trained_at}")
                
                # Save detailed report if requested
                if save_report:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    summary_path = base_dir / "ml" / "reports" / f"retraining_summary_{timestamp}.json"
                    summary_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Create summary report
                    summary = {
                        "retraining_completed_at": datetime.now().isoformat(),
                        "pipeline_duration_seconds": time.time() - start_time,
                        "parameters": {
                            "months": months,
                            "cv_folds": cv_folds,
                            "demo_mode": demo_mode,
                            "skip_sync": skip_sync
                        },
                        "results": report
                    }
                    
                    with open(summary_path, 'w') as f:
                        json.dump(summary, f, indent=2)
                    
                    self.log_with_timestamp(f"📄 Detailed report saved to: {summary_path}")
                
            else:
                self.log_with_timestamp("⚠️ Training report not found", level='warning')
                
        except Exception as e:
            self.log_with_timestamp(f"⚠️ Error loading training metrics: {e}", level='warning')
        
        # Calculate and log total execution time
        execution_time = time.time() - start_time
        self.log_with_timestamp(f"🏁 Retraining pipeline completed in {execution_time:.2f} seconds")
        
        # Final success message
        self.stdout.write(self.style.SUCCESS("\n🎉 === RETRAINING SUCCESSFUL ==="))
        self.stdout.write("✅ Model is ready for predictions!") 