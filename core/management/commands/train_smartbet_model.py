"""
Django management command to train the SmartBet ML model.

This command trains the machine learning model for match outcome prediction
using the training data generated from completed matches.
"""

import os
import json
import logging
from django.core.management.base import BaseCommand, CommandError
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

from predictor.ml_model import train_model, get_model_version, get_feature_importance
from core.training.generate_training_dataset import generate_and_save_dataset

# Configure logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Train the SmartBet ML model for match outcome prediction'

    def add_arguments(self, parser):
        parser.add_argument(
            '--data',
            type=str,
            help='Custom path to training data CSV file',
        )
        parser.add_argument(
            '--months',
            type=int,
            default=24,  # Default to 2 years of data
            help='Number of months of historical data to include',
        )
        parser.add_argument(
            '--refresh',
            action='store_true',
            help='Force regeneration of training dataset before training',
        )
        parser.add_argument(
            '--cv',
            type=int,
            default=5,
            help='Number of cross-validation folds to use',
        )
        parser.add_argument(
            '--no-plots',
            action='store_true',
            help='Skip generating plots and visualizations',
        )

    def handle(self, *args, **options):
        try:
            # Process arguments
            data_path = options.get('data')
            months_limit = options.get('months')
            refresh = options.get('refresh')
            cv_folds = options.get('cv')
            skip_plots = options.get('no_plots')
            
            # Print initial message
            self.stdout.write(self.style.SUCCESS("Starting SmartBet ML model training..."))
            
            # Generate/refresh training data if needed
            if refresh or not data_path:
                self.stdout.write("Generating fresh training dataset...")
                output_path = data_path or None  # None will use default location
                
                # Generate dataset with the specified months limit
                data_path = generate_and_save_dataset(months_limit, output_path)
                
                if not data_path:
                    raise CommandError("Failed to generate training dataset")
                
                self.stdout.write(self.style.SUCCESS(f"Generated training dataset at: {data_path}"))
            
            # Print training parameters
            if data_path:
                self.stdout.write(f"Using training data from: {data_path}")
                
                # Show preview of the dataset
                try:
                    df = pd.read_csv(data_path)
                    self.stdout.write(f"Dataset has {len(df)} samples and {len(df.columns)} features")
                    self.stdout.write(f"Class distribution: {df['outcome'].value_counts().to_dict()}")
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Could not read dataset for preview: {e}"))
            
            # Train the model with additional parameters
            self.stdout.write("Training model...")
            train_model(data_path, cv_folds=cv_folds, create_plots=(not skip_plots))
            
            # Get the model version
            model_version = get_model_version()
            
            # Print success message
            self.stdout.write(self.style.SUCCESS(f"Model training completed successfully!"))
            self.stdout.write(f"Model version: {model_version}")
            
            # Display feature importance
            try:
                feature_importance = get_feature_importance()
                if feature_importance:
                    self.stdout.write("\nTop 10 most important features:")
                    # Sort by importance
                    sorted_importance = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
                    for i, (feature, importance) in enumerate(sorted_importance[:10]):
                        self.stdout.write(f"{i+1}. {feature}: {importance:.4f}")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Could not display feature importance: {e}"))
            
            # Try to get the training report path
            try:
                base_dir = Path(__file__).resolve().parent.parent.parent.parent
                report_path = base_dir / "predictor" / "training_report.json"
                plot_path = base_dir / "predictor" / "feature_importance.png"
                
                if report_path.exists():
                    self.stdout.write(f"Training report saved to: {report_path}")
                    
                    # Display some key metrics from the report
                    with open(report_path, 'r') as f:
                        report = json.load(f)
                        metrics = report.get('metrics', {})
                        if metrics:
                            self.stdout.write("\nModel performance metrics:")
                            self.stdout.write(f"Accuracy: {metrics.get('accuracy', 'N/A'):.4f}")
                            self.stdout.write(f"Log Loss: {metrics.get('log_loss', 'N/A'):.4f}")
                
                if plot_path.exists():
                    self.stdout.write(f"Feature importance plot saved to: {plot_path}")
            except Exception as e:
                pass
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error training model: {e}"))
            logger.exception("Error in train_smartbet_model command")
            raise CommandError("Failed to train SmartBet model") 