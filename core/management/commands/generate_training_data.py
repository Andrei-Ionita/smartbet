"""
Django management command to generate training data for ML models.

This command extracts features from completed matches in the database and
creates a CSV file that can be used to train ML models for match outcome prediction.
"""

import os
import logging
from django.core.management.base import BaseCommand, CommandError
from pathlib import Path

from core.training.generate_training_dataset import generate_and_save_dataset

# Configure logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate ML training dataset from completed matches'

    def add_arguments(self, parser):
        parser.add_argument(
            '--months',
            type=int,
            help='Limit data to matches from the last N months',
        )
        parser.add_argument(
            '--output',
            type=str,
            help='Custom output path for the CSV file',
        )

    def handle(self, *args, **options):
        try:
            # Process arguments
            months_limit = options.get('months')
            output_path = options.get('output')
            
            # Print initial message
            if months_limit:
                self.stdout.write(f"Generating training dataset from matches in the last {months_limit} months...")
            else:
                self.stdout.write("Generating training dataset from all completed matches...")
            
            # Generate and save the dataset
            result_path = generate_and_save_dataset(
                months_limit=months_limit,
                output_path=output_path
            )
            
            # Check result
            if result_path:
                self.stdout.write(self.style.SUCCESS(f"Training dataset successfully saved to {result_path}"))
                # Try to count rows
                try:
                    import pandas as pd
                    df = pd.read_csv(result_path)
                    self.stdout.write(f"Dataset contains {len(df)} rows with the following columns:")
                    for col in df.columns:
                        self.stdout.write(f"  - {col}")
                except Exception as e:
                    self.stdout.write(f"Generated file but couldn't read it back: {e}")
            else:
                self.stdout.write(self.style.WARNING("No dataset was generated. Check logs for details."))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error generating training dataset: {e}"))
            logger.exception("Error in generate_training_data command")
            raise CommandError("Failed to generate training dataset") 