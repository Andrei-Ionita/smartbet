"""
Production-grade SmartBet ML model builder using real betting data.

This command fetches historical data from SportMonks and OddsAPI for major leagues,
performs comprehensive feature engineering, trains an optimized LightGBM model,
and saves all production outputs.
"""

import os
import json
import time
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

import lightgbm as lgb
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import log_loss, accuracy_score, brier_score_loss
import optuna

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db.models import Q, Count

from core.models import League, Match, OddsSnapshot, Team

# Configure logging
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Build production-grade SmartBet prediction model using real betting data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--priority-leagues',
            nargs='+',
            default=['Liga I', 'English Premier League'],
            help='Priority leagues to start with (default: Romanian Liga I, EPL)'
        )
        parser.add_argument(
            '--all-leagues',
            action='store_true',
            help='Include all major leagues in training'
        )
        parser.add_argument(
            '--min-matches',
            type=int,
            default=10,
            help='Minimum matches required per league (default: 10)'
        )
        parser.add_argument(
            '--optuna-trials',
            type=int,
            default=50,
            help='Number of Optuna optimization trials (default: 50)'
        )
        parser.add_argument(
            '--cv-folds',
            type=int,
            default=5,
            help='Cross-validation folds (default: 5)'
        )
        parser.add_argument(
            '--output-dir',
            default='production_model',
            help='Output directory for model artifacts'
        )

    def log_step(self, message, level='info'):
        """Log message with timestamp and styling."""
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] {message}"
        
        if level == 'info':
            self.stdout.write(self.style.SUCCESS(log_message))
        elif level == 'warning':
            self.stdout.write(self.style.WARNING(log_message))
        elif level == 'error':
            self.stdout.write(self.style.ERROR(log_message))
        
        logger.log(getattr(logging, level.upper()), message)

    def create_output_directory(self, output_dir):
        """Create output directory with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(output_dir) / f"smartbet_production_{timestamp}"
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path

    def get_target_leagues(self, priority_leagues, all_leagues):
        """Get target leagues for training."""
        if all_leagues:
            # Get all available leagues with data
            leagues = League.objects.annotate(
                completed_matches=Count('matches', filter=Q(matches__status='FT'))
            ).filter(completed_matches__gt=0)
        else:
            # Get priority leagues
            leagues = League.objects.filter(
                Q(name_en__icontains='Liga I') |
                Q(name_en__icontains='Premier League') |
                Q(name_en__icontains='EPL')
            )
        
        return leagues

    def fetch_training_data(self, leagues, min_matches):
        """Fetch and prepare training data from real matches with odds."""
        self.log_step("📥 Fetching real historical match data...")
        
        # Get completed matches with valid odds
        matches_query = Match.objects.filter(
            league__in=leagues,
            status='FT',
            home_score__isnull=False,
            away_score__isnull=False,
            odds_snapshots__isnull=False
        ).distinct().select_related('league', 'home_team', 'away_team')
        
        # Check data availability per league
        league_data = {}
        total_matches = 0
        unmatched_odds_log = []
        
        for league in leagues:
            league_matches = matches_query.filter(league=league)
            count = league_matches.count()
            league_data[league.name_en] = count
            total_matches += count
            
            self.log_step(f"  📊 {league.name_en}: {count} completed matches with odds")
            
            if count < min_matches:
                self.log_step(f"  ⚠️ {league.name_en} has insufficient data (<{min_matches})", 'warning')

        if total_matches < 10:
            raise CommandError(f"Insufficient training data: only {total_matches} matches found")

        self.log_step(f"✅ Total training matches: {total_matches}")

        # Extract data
        training_data = []
        
        for match in matches_query:
            # Get latest odds
            latest_odds = match.odds_snapshots.order_by('-fetched_at').first()
            
            if not latest_odds:
                unmatched_odds_log.append({
                    'match_id': match.id,
                    'home_team': match.home_team.name_en,
                    'away_team': match.away_team.name_en,
                    'league': match.league.name_en,
                    'reason': 'no_odds_snapshot'
                })
                continue
            
            # Determine outcome
            if match.home_score > match.away_score:
                outcome = 'home'
            elif match.home_score < match.away_score:
                outcome = 'away'
            else:
                outcome = 'draw'
            
            # Basic match data
            match_data = {
                'match_id': match.id,
                'home_team': match.home_team.name_en,
                'away_team': match.away_team.name_en,
                'league_name': match.league.name_en,
                'kickoff_time': match.kickoff,
                'final_result': outcome,
                'home_score': match.home_score,
                'away_score': match.away_score,
                
                # Odds data
                'odds_home': latest_odds.odds_home,
                'odds_draw': latest_odds.odds_draw,
                'odds_away': latest_odds.odds_away,
                'bookmaker': latest_odds.bookmaker,
                'odds_fetched_at': latest_odds.fetched_at,
                
                # Team statistics (if available)
                'avg_goals_home': match.avg_goals_home,
                'avg_goals_away': match.avg_goals_away,
                'avg_cards_home': match.avg_cards_home,
                'avg_cards_away': match.avg_cards_away,
                'team_form_home': match.team_form_home,
                'team_form_away': match.team_form_away,
                'injured_starters_home': match.injured_starters_home,
                'injured_starters_away': match.injured_starters_away,
            }
            
            training_data.append(match_data)

        self.log_step(f"📋 Extracted {len(training_data)} valid training samples")
        
        if unmatched_odds_log:
            self.log_step(f"⚠️ {len(unmatched_odds_log)} matches missing odds data", 'warning')
        
        return pd.DataFrame(training_data), unmatched_odds_log, league_data

    def engineer_features(self, df):
        """Comprehensive feature engineering for betting predictions."""
        self.log_step("🧠 Engineering features for production model...")
        
        # Ensure we have required columns
        required_cols = ['odds_home', 'odds_draw', 'odds_away', 'final_result']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise CommandError(f"Missing required columns: {missing_cols}")

        # Core betting features
        df['implied_prob_home'] = 1 / df['odds_home']
        df['implied_prob_draw'] = 1 / df['odds_draw']
        df['implied_prob_away'] = 1 / df['odds_away']
        
        # Bookmaker margin
        df['bookmaker_margin'] = (df['implied_prob_home'] + 
                                 df['implied_prob_draw'] + 
                                 df['implied_prob_away']) - 1
        
        # True probabilities (margin removed)
        total_implied = df['implied_prob_home'] + df['implied_prob_draw'] + df['implied_prob_away']
        df['true_prob_home'] = df['implied_prob_home'] / total_implied
        df['true_prob_draw'] = df['implied_prob_draw'] / total_implied
        df['true_prob_away'] = df['implied_prob_away'] / total_implied
        
        # Log odds ratios
        df['log_odds_home_away'] = np.log(df['odds_away'] / df['odds_home'])
        df['log_odds_home_draw'] = np.log(df['odds_draw'] / df['odds_home'])
        df['log_odds_draw_away'] = np.log(df['odds_away'] / df['odds_draw'])
        
        # Time-based features
        df['kickoff_time'] = pd.to_datetime(df['kickoff_time'])
        df['weekday'] = df['kickoff_time'].dt.dayofweek
        df['kickoff_hour'] = df['kickoff_time'].dt.hour
        df['is_weekend'] = (df['weekday'] >= 5).astype(int)
        df['month'] = df['kickoff_time'].dt.month
        df['year'] = df['kickoff_time'].dt.year
        
        # League encoding
        le_league = LabelEncoder()
        df['league_encoded'] = le_league.fit_transform(df['league_name'])
        
        # Team statistics features (if available)
        if 'avg_goals_home' in df.columns and df['avg_goals_home'].notna().any():
            df['goals_diff'] = df['avg_goals_home'].fillna(1.5) - df['avg_goals_away'].fillna(1.5)
            df['cards_diff'] = df['avg_cards_home'].fillna(2.0) - df['avg_cards_away'].fillna(2.0)
            df['form_diff'] = df['team_form_home'].fillna(5.0) - df['team_form_away'].fillna(5.0)
            df['injured_diff'] = df['injured_starters_home'].fillna(0) - df['injured_starters_away'].fillna(0)
        else:
            # Set defaults if team stats not available
            df['goals_diff'] = 0.0
            df['cards_diff'] = 0.0
            df['form_diff'] = 0.0
            df['injured_diff'] = 0.0
        
        # Additional betting indicators
        df['favorite_home'] = (df['odds_home'] < df['odds_away']).astype(int)
        df['heavy_favorite'] = ((df['odds_home'] < 1.5) | (df['odds_away'] < 1.5)).astype(int)
        df['close_odds'] = (abs(df['odds_home'] - df['odds_away']) < 0.3).astype(int)
        
        # Odds volatility
        df['odds_home_level'] = pd.cut(df['odds_home'], bins=[0, 1.5, 2.5, 4.0, float('inf')], 
                                      labels=[0, 1, 2, 3]).astype(int)
        df['odds_away_level'] = pd.cut(df['odds_away'], bins=[0, 1.5, 2.5, 4.0, float('inf')], 
                                      labels=[0, 1, 2, 3]).astype(int)
        
        self.log_step(f"✅ Engineered {len([col for col in df.columns if col not in required_cols])} features")
        
        return df, le_league

    def prepare_ml_features(self, df):
        """Prepare features for ML training."""
        # Define feature columns (exclude target and metadata)
        exclude_cols = [
            'match_id', 'home_team', 'away_team', 'league_name', 'final_result',
            'home_score', 'away_score', 'kickoff_time', 'bookmaker', 'odds_fetched_at'
        ]
        
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        
        X = df[feature_cols].copy()
        y = df['final_result'].copy()
        
        # Handle any remaining NaN values
        X = X.fillna(0)
        
        # Encode target
        le_target = LabelEncoder()
        y_encoded = le_target.fit_transform(y)
        
        self.log_step(f"📊 Training features: {len(feature_cols)}")
        self.log_step(f"📊 Training samples: {len(X)}")
        self.log_step(f"📊 Target classes: {list(le_target.classes_)}")
        
        return X, y_encoded, feature_cols, le_target

    def train_production_model(self, X, y, cv_folds):
        """Train production model with good default parameters."""
        self.log_step("🧠 Training production LightGBM model...")
        
        # Production-ready parameters
        params = {
            'objective': 'multiclass',
            'num_class': 3,
            'metric': 'multi_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.1,
            'feature_fraction': 0.9,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'min_child_samples': 20,
            'max_depth': 6,
            'lambda_l1': 0.1,
            'lambda_l2': 0.1,
            'verbosity': -1
        }
        
        # Train on full dataset
        train_data = lgb.Dataset(X, label=y)
        
        model = lgb.train(
            params,
            train_data,
            num_boost_round=500,
            callbacks=[lgb.log_evaluation(100)]
        )
        
        # Cross-validation evaluation
        skf = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=42)
        cv_scores = {
            'log_loss': [],
            'accuracy': [],
            'brier_score_home': [],
            'brier_score_draw': [],
            'brier_score_away': []
        }
        
        for train_idx, val_idx in skf.split(X, y):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y[train_idx], y[val_idx]
            
            train_data = lgb.Dataset(X_train, label=y_train)
            cv_model = lgb.train(params, train_data, num_boost_round=500, callbacks=[lgb.log_evaluation(0)])
            
            y_pred_proba = cv_model.predict(X_val)
            y_pred = np.argmax(y_pred_proba, axis=1)
            
            cv_scores['log_loss'].append(log_loss(y_val, y_pred_proba))
            cv_scores['accuracy'].append(accuracy_score(y_val, y_pred))
            
            # Brier scores for each class
            for i, class_name in enumerate(['home', 'draw', 'away']):
                y_true_binary = (y_val == i).astype(int)
                y_pred_binary = y_pred_proba[:, i]
                cv_scores[f'brier_score_{class_name}'].append(
                    brier_score_loss(y_true_binary, y_pred_binary)
                )
        
        # Calculate mean CV scores
        mean_scores = {metric: np.mean(scores) for metric, scores in cv_scores.items()}
        
        self.log_step(f"📈 CV Log Loss: {mean_scores['log_loss']:.4f}")
        self.log_step(f"📈 CV Accuracy: {mean_scores['accuracy']:.4f}")
        self.log_step(f"📈 CV Brier Score (avg): {np.mean([mean_scores['brier_score_home'], mean_scores['brier_score_draw'], mean_scores['brier_score_away']]):.4f}")
        
        return model, mean_scores, params

    def save_production_artifacts(self, model, df, X, feature_cols, le_target, mean_scores, 
                                params, unmatched_odds_log, league_data, output_path):
        """Save all production model artifacts."""
        self.log_step("📦 Saving production model artifacts...")
        
        # 1. Save trained model
        model_path = output_path / 'lgbm_smartbet_production.pkl'
        model.save_model(str(model_path))
        
        # 2. Save training dataset
        training_data_path = output_path / 'training_data.csv'
        df.to_csv(training_data_path, index=False)
        
        # 3. Save model metrics
        metrics = {
            'cross_validation_scores': mean_scores,
            'model_parameters': params,
            'training_samples': len(df),
            'feature_count': len(feature_cols),
            'target_classes': list(le_target.classes_),
            'league_distribution': league_data,
            'model_created_at': datetime.now().isoformat(),
            'model_type': 'lightgbm_multiclass',
            'objective': 'match_outcome_prediction'
        }
        
        metrics_path = output_path / 'model_metrics.json'
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        # 4. Save feature importances
        importance_df = pd.DataFrame({
            'feature': feature_cols,
            'importance': model.feature_importance(importance_type='gain'),
            'importance_split': model.feature_importance(importance_type='split')
        }).sort_values('importance', ascending=False)
        
        importance_path = output_path / 'feature_importances.csv'
        importance_df.to_csv(importance_path, index=False)
        
        # 5. Save unmatched odds log
        unmatched_path = output_path / 'unmatched_odds_log.json'
        with open(unmatched_path, 'w') as f:
            json.dump(unmatched_odds_log, f, indent=2)
        
        self.log_step(f"✅ All artifacts saved to: {output_path}")
        
        return {
            'model_path': model_path,
            'training_data_path': training_data_path,
            'metrics_path': metrics_path,
            'importance_path': importance_path,
            'unmatched_path': unmatched_path
        }

    def handle(self, *args, **options):
        """Main execution flow."""
        start_time = time.time()
        
        self.log_step("🚀 Starting SmartBet Production Model Builder...")
        
        # Extract options
        priority_leagues = options['priority_leagues']
        all_leagues = options['all_leagues']
        min_matches = options['min_matches']
        cv_folds = options['cv_folds']
        output_dir = options['output_dir']
        
        try:
            # Create output directory
            output_path = self.create_output_directory(output_dir)
            self.log_step(f"📁 Output directory: {output_path}")
            
            # Step 1: Get target leagues
            leagues = self.get_target_leagues(priority_leagues, all_leagues)
            self.log_step(f"🎯 Target leagues: {[l.name_en for l in leagues]}")
            
            # Step 2: Fetch training data
            df, unmatched_odds_log, league_data = self.fetch_training_data(leagues, min_matches)
            
            # Step 3: Feature engineering
            df, le_league = self.engineer_features(df)
            
            # Step 4: Prepare ML features
            X, y, feature_cols, le_target = self.prepare_ml_features(df)
            
            # Step 5: Train production model
            model, mean_scores, params = self.train_production_model(X, y, cv_folds)
            
            # Step 6: Save production artifacts
            artifacts = self.save_production_artifacts(
                model, df, X, feature_cols, le_target, mean_scores,
                params, unmatched_odds_log, league_data, output_path
            )
            
            # Execution summary
            execution_time = time.time() - start_time
            self.log_step(f"⏱️ Total execution time: {execution_time:.2f} seconds")
            
            # Final summary
            self.stdout.write(self.style.SUCCESS("\n🎉 Production Model Build Complete!"))
            self.stdout.write(f"📊 Training samples: {len(df)}")
            self.stdout.write(f"📊 Features: {len(feature_cols)}")
            self.stdout.write(f"📊 CV Accuracy: {mean_scores['accuracy']:.4f}")
            self.stdout.write(f"📊 CV Log Loss: {mean_scores['log_loss']:.4f}")
            self.stdout.write(f"📁 Model saved: {artifacts['model_path']}")
            
        except Exception as e:
            self.log_step(f"❌ Error building production model: {e}", 'error')
            raise CommandError(f"Production model build failed: {e}") 