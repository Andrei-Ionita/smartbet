"""
Deep Historical Prediction Pattern Analysis
============================================
Analyzes all completed PredictionLog entries to discover patterns
between correct and incorrect predictions. Produces actionable
recommendations for tuning PredictionEnhancer thresholds.

Usage:
    python manage.py analyze_prediction_patterns
    python manage.py analyze_prediction_patterns --backtest
    python manage.py analyze_prediction_patterns --export-csv
"""

from django.core.management.base import BaseCommand
from django.db.models import Count, Avg, Q, Sum, StdDev, Min, Max, F
from core.models import PredictionLog
from collections import defaultdict
import json
import csv
import os
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Deep analysis of prediction patterns to improve accuracy'

    def add_arguments(self, parser):
        parser.add_argument(
            '--backtest',
            action='store_true',
            help='Run threshold backtesting to find optimal parameters'
        )
        parser.add_argument(
            '--export-csv',
            action='store_true',
            help='Export raw prediction data to CSV for external analysis'
        )
        parser.add_argument(
            '--recommended-only',
            action='store_true',
            help='Only analyze recommended predictions'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 90))
        self.stdout.write(self.style.SUCCESS(
            '  DEEP HISTORICAL PREDICTION PATTERN ANALYSIS'))
        self.stdout.write(self.style.SUCCESS(
            '  Goal: Find patterns to improve accuracy without overfitting'))
        self.stdout.write(self.style.SUCCESS('=' * 90 + '\n'))

        # Load all completed predictions
        base_qs = PredictionLog.objects.filter(
            actual_outcome__isnull=False,
            was_correct__isnull=False,
        )

        if options['recommended_only']:
            base_qs = base_qs.filter(is_recommended=True)
            self.stdout.write(self.style.WARNING(
                'Filtering to RECOMMENDED predictions only\n'))

        predictions = list(base_qs.order_by('kickoff'))
        total = len(predictions)

        if total == 0:
            self.stdout.write(self.style.ERROR(
                'No completed predictions found in the database.'))
            return

        correct = [p for p in predictions if p.was_correct]
        incorrect = [p for p in predictions if not p.was_correct]

        self.stdout.write('  Total Completed Predictions: %d' % total)
        self.stdout.write(self.style.SUCCESS(
            '  Correct: %d (%.1f%%)' % (len(correct), len(correct)/total*100)))
        self.stdout.write(self.style.ERROR(
            '  Incorrect: %d (%.1f%%)' % (len(incorrect), len(incorrect)/total*100)))
        self.stdout.write('')

        # Run all analyses
        self._analyze_confidence_calibration(predictions)
        self._analyze_miss_patterns(correct, incorrect)
        self._analyze_consensus_variance(predictions)
        self._analyze_ev_vs_accuracy(predictions)
        self._analyze_by_league(predictions)
        self._analyze_by_market_type(predictions)
        self._analyze_by_odds_range(predictions)
        self._analyze_by_outcome_type(predictions)
        self._analyze_probability_gap(predictions)
        self._analyze_form_correlation(predictions)

        if options['backtest']:
            self._run_threshold_backtest(predictions)

        if options['export_csv']:
            self._export_to_csv(predictions)

        # Final recommendations
        self._generate_recommendations(predictions, correct, incorrect)

    # ──────────────────────────────────────────────────────────────
    # HELPER
    # ──────────────────────────────────────────────────────────────
    @staticmethod
    def _conf_pct(p):
        c = p.confidence
        return c * 100 if c < 1 else c

    @staticmethod
    def _ev_pct(p):
        ev = p.expected_value
        if ev is None:
            return 0
        return ev * 100 if abs(ev) < 1 else ev

    @staticmethod
    def _predicted_odds(p):
        outcome = (p.predicted_outcome or '').lower()
        if outcome == 'home' and p.odds_home:
            return p.odds_home
        elif outcome == 'draw' and p.odds_draw:
            return p.odds_draw
        elif outcome == 'away' and p.odds_away:
            return p.odds_away
        return None

    @staticmethod
    def _prob_gap(p):
        probs = []
        if p.probability_home is not None:
            probs.append(p.probability_home if p.probability_home <= 1 else p.probability_home / 100)
        if p.probability_draw is not None:
            probs.append(p.probability_draw if p.probability_draw <= 1 else p.probability_draw / 100)
        if p.probability_away is not None:
            probs.append(p.probability_away if p.probability_away <= 1 else p.probability_away / 100)
        if len(probs) < 2:
            return None
        sorted_probs = sorted(probs, reverse=True)
        return sorted_probs[0] - sorted_probs[1]

    def _print_table_header(self, columns):
        """Print a formatted table header. columns is list of (label, width, align)."""
        parts = []
        for label, width, align in columns:
            if align == 'l':
                parts.append(('%-' + str(width) + 's') % label)
            else:
                parts.append(('%' + str(width) + 's') % label)
        self.stdout.write('  ' + ' '.join(parts))
        total_width = sum(w for _, w, _ in columns) + len(columns) - 1
        self.stdout.write('  ' + '-' * total_width)

    # ──────────────────────────────────────────────────────────────
    # 1. CONFIDENCE CALIBRATION
    # ──────────────────────────────────────────────────────────────
    def _analyze_confidence_calibration(self, predictions):
        self.stdout.write(self.style.SUCCESS('-' * 90))
        self.stdout.write(self.style.SUCCESS(
            '  1. CONFIDENCE CALIBRATION'))
        self.stdout.write(self.style.SUCCESS(
            '  Is our stated confidence matching actual accuracy?'))
        self.stdout.write(self.style.SUCCESS('-' * 90))

        bands = [
            (30, 40, '30-40%'),
            (40, 50, '40-50%'),
            (50, 55, '50-55%'),
            (55, 60, '55-60%'),
            (60, 65, '60-65%'),
            (65, 70, '65-70%'),
            (70, 80, '70-80%'),
            (80, 100, '80-100%'),
        ]

        self._print_table_header([
            ('Band', 12, 'l'), ('Total', 6, 'r'), ('Correct', 8, 'r'),
            ('Accuracy', 10, 'r'), ('Expected', 10, 'r'),
            ('Gap', 8, 'r'), ('Status', 20, 'l')
        ])

        for low, high, label in bands:
            bucket = [p for p in predictions
                      if low <= self._conf_pct(p) < high]
            if not bucket:
                continue

            total = len(bucket)
            correct = sum(1 for p in bucket if p.was_correct)
            accuracy = correct / total * 100
            expected = (low + high) / 2
            gap = accuracy - expected

            if gap >= 5:
                status = 'Under-confident [OK]'
                style = self.style.SUCCESS
            elif gap <= -10:
                status = 'OVER-CONFIDENT!'
                style = self.style.ERROR
            elif gap <= -5:
                status = 'Over-confident'
                style = self.style.WARNING
            else:
                status = 'Well-calibrated'
                style = self.style.SUCCESS

            self.stdout.write(style(
                '  %-12s %6d %8d %9.1f%% %9.1f%% %+7.1f%% %-20s' % (
                    label, total, correct, accuracy, expected, gap, status)
            ))

        self.stdout.write('')

    # ──────────────────────────────────────────────────────────────
    # 2. MISS PATTERN ANALYSIS
    # ──────────────────────────────────────────────────────────────
    def _analyze_miss_patterns(self, correct, incorrect):
        self.stdout.write(self.style.SUCCESS('-' * 90))
        self.stdout.write(self.style.SUCCESS(
            '  2. MISS PATTERN ANALYSIS'))
        self.stdout.write(self.style.SUCCESS(
            '  What do our INCORRECT predictions have in common?'))
        self.stdout.write(self.style.SUCCESS('-' * 90))

        if not incorrect:
            self.stdout.write('  No incorrect predictions found!\n')
            return

        # Avg confidence of correct vs incorrect
        avg_conf_c = sum(self._conf_pct(p) for p in correct) / len(correct) if correct else 0
        avg_conf_i = sum(self._conf_pct(p) for p in incorrect) / len(incorrect)

        avg_ev_c = sum(self._ev_pct(p) for p in correct) / len(correct) if correct else 0
        avg_ev_i = sum(self._ev_pct(p) for p in incorrect) / len(incorrect)

        self._print_table_header([
            ('Metric', 30, 'l'), ('Correct', 15, 'r'),
            ('Incorrect', 15, 'r'), ('Delta', 12, 'r')
        ])

        self.stdout.write(
            '  %-30s %14.1f%% %14.1f%% %+11.1f%%' % (
                'Avg Confidence', avg_conf_c, avg_conf_i, avg_conf_c - avg_conf_i))
        self.stdout.write(
            '  %-30s %14.1f%% %14.1f%% %+11.1f%%' % (
                'Avg Expected Value', avg_ev_c, avg_ev_i, avg_ev_c - avg_ev_i))

        # Avg odds
        correct_odds = [self._predicted_odds(p) for p in correct if self._predicted_odds(p)]
        incorrect_odds = [self._predicted_odds(p) for p in incorrect if self._predicted_odds(p)]

        avg_odds_c = sum(correct_odds) / len(correct_odds) if correct_odds else 0
        avg_odds_i = sum(incorrect_odds) / len(incorrect_odds) if incorrect_odds else 0

        self.stdout.write(
            '  %-30s %15.2f %15.2f %+12.2f' % (
                'Avg Predicted Odds', avg_odds_c, avg_odds_i, avg_odds_c - avg_odds_i))

        # Consensus / Variance
        correct_cons = [p.consensus for p in correct if p.consensus is not None]
        incorrect_cons = [p.consensus for p in incorrect if p.consensus is not None]
        correct_var = [p.variance for p in correct if p.variance is not None]
        incorrect_var = [p.variance for p in incorrect if p.variance is not None]

        if correct_cons and incorrect_cons:
            avg_cons_c = sum(correct_cons) / len(correct_cons)
            avg_cons_i = sum(incorrect_cons) / len(incorrect_cons)
            if avg_cons_c < 1:
                avg_cons_c *= 100
            if avg_cons_i < 1:
                avg_cons_i *= 100
            self.stdout.write(
                '  %-30s %14.1f%% %14.1f%% %+11.1f%%' % (
                    'Avg Consensus', avg_cons_c, avg_cons_i, avg_cons_c - avg_cons_i))

        if correct_var and incorrect_var:
            avg_var_c = sum(correct_var) / len(correct_var)
            avg_var_i = sum(incorrect_var) / len(incorrect_var)
            self.stdout.write(
                '  %-30s %15.3f %15.3f %+12.3f' % (
                    'Avg Variance', avg_var_c, avg_var_i, avg_var_c - avg_var_i))

        # Breakdown of misses by outcome type
        self.stdout.write('\n  Misses by Predicted Outcome:')
        miss_outcomes = defaultdict(int)
        for p in incorrect:
            miss_outcomes[p.predicted_outcome or 'Unknown'] += 1
        for outcome, count in sorted(miss_outcomes.items(),
                                      key=lambda x: x[1], reverse=True):
            pct = count / len(incorrect) * 100
            self.stdout.write('    [X] %s: %d (%.1f%% of misses)' % (outcome, count, pct))

        # Breakdown by league
        self.stdout.write('\n  Misses by League:')
        miss_leagues = defaultdict(int)
        total_by_league = defaultdict(int)
        correct_by_league = defaultdict(int)
        for p in correct + incorrect:
            total_by_league[p.league] += 1
        for p in correct:
            correct_by_league[p.league] += 1
        for p in incorrect:
            miss_leagues[p.league] += 1
        for league, count in sorted(miss_leagues.items(),
                                     key=lambda x: x[1], reverse=True):
            total_in_league = total_by_league[league]
            acc = correct_by_league[league] / total_in_league * 100 if total_in_league > 0 else 0
            self.stdout.write(
                '    [X] %s: %d misses / %d total (league accuracy: %.1f%%)' % (
                    league, count, total_in_league, acc))

        self.stdout.write('')

    # ──────────────────────────────────────────────────────────────
    # 3. CONSENSUS / VARIANCE CORRELATION
    # ──────────────────────────────────────────────────────────────
    def _analyze_consensus_variance(self, predictions):
        self.stdout.write(self.style.SUCCESS('-' * 90))
        self.stdout.write(self.style.SUCCESS(
            '  3. MODEL CONSENSUS & VARIANCE ANALYSIS'))
        self.stdout.write(self.style.SUCCESS(
            '  Does higher model agreement = higher accuracy?'))
        self.stdout.write(self.style.SUCCESS('-' * 90))

        with_var = [p for p in predictions if p.variance is not None]

        if not with_var:
            self.stdout.write('  No variance data available.\n')
            return

        var_bands = [
            (0, 2, 'Very Low (0-2)'),
            (2, 5, 'Low (2-5)'),
            (5, 10, 'Medium (5-10)'),
            (10, 20, 'High (10-20)'),
            (20, 100, 'Very High (20+)'),
        ]

        self._print_table_header([
            ('Variance Band', 20, 'l'), ('Total', 6, 'r'),
            ('Correct', 8, 'r'), ('Accuracy', 10, 'r'), ('Signal', 25, 'l')
        ])

        for low, high, label in var_bands:
            bucket = [p for p in with_var if low <= p.variance < high]
            if not bucket:
                continue

            total = len(bucket)
            correct = sum(1 for p in bucket if p.was_correct)
            accuracy = correct / total * 100

            if accuracy >= 75:
                signal = '[STRONG]'
            elif accuracy >= 60:
                signal = '[MODERATE]'
            else:
                signal = '[WEAK]'

            self.stdout.write(
                '  %-20s %6d %8d %9.1f%% %-25s' % (
                    label, total, correct, accuracy, signal))

        # Consensus analysis
        with_cons = [p for p in predictions if p.consensus is not None]
        if with_cons:
            self.stdout.write('\n  Consensus Bands:')
            cons_bands = [
                (0.0, 0.60, 'Low (<60%)'),
                (0.60, 0.75, 'Medium (60-75%)'),
                (0.75, 0.90, 'High (75-90%)'),
                (0.90, 1.01, 'Very High (90%+)'),
            ]

            for low, high, label in cons_bands:
                bucket = [p for p in with_cons
                          if (low <= p.consensus < high) or
                          (low * 100 <= p.consensus < high * 100)]
                if not bucket:
                    continue

                total = len(bucket)
                correct = sum(1 for p in bucket if p.was_correct)
                accuracy = correct / total * 100

                self.stdout.write(
                    '    %-20s %6d %8d %9.1f%%' % (label, total, correct, accuracy))

        self.stdout.write('')

    # ──────────────────────────────────────────────────────────────
    # 4. EV vs ACCURACY
    # ──────────────────────────────────────────────────────────────
    def _analyze_ev_vs_accuracy(self, predictions):
        self.stdout.write(self.style.SUCCESS('-' * 90))
        self.stdout.write(self.style.SUCCESS(
            '  4. EXPECTED VALUE vs ACCURACY'))
        self.stdout.write(self.style.SUCCESS(
            '  Do high-EV predictions actually hit more often?'))
        self.stdout.write(self.style.SUCCESS('-' * 90))

        with_ev = [(p, self._ev_pct(p)) for p in predictions
                   if p.expected_value is not None]

        if not with_ev:
            self.stdout.write('  No EV data available.\n')
            return

        ev_bands = [
            (-100, 0, 'Negative EV'),
            (0, 5, 'Low (0-5%)'),
            (5, 10, 'Moderate (5-10%)'),
            (10, 15, 'Good (10-15%)'),
            (15, 25, 'High (15-25%)'),
            (25, 50, 'Very High (25-50%)'),
            (50, 500, 'Extreme (50%+)'),
        ]

        self._print_table_header([
            ('EV Range', 20, 'l'), ('Total', 6, 'r'), ('Correct', 8, 'r'),
            ('Accuracy', 10, 'r'), ('Avg P/L', 10, 'r'), ('Signal', 20, 'l')
        ])

        for low, high, label in ev_bands:
            bucket = [(p, ev) for p, ev in with_ev if low <= ev < high]
            if not bucket:
                continue

            total = len(bucket)
            correct = sum(1 for p, _ in bucket if p.was_correct)
            accuracy = correct / total * 100

            pls = [p.profit_loss_10 for p, _ in bucket if p.profit_loss_10 is not None]
            avg_pl = sum(pls) / len(pls) if pls else 0

            if accuracy >= 70:
                signal = '[STRONG]'
            elif accuracy >= 55:
                signal = '[MODERATE]'
            else:
                signal = '[WEAK]'

            self.stdout.write(
                '  %-20s %6d %8d %9.1f%% $%+8.2f %-20s' % (
                    label, total, correct, accuracy, avg_pl, signal))

        self.stdout.write('')

    # ──────────────────────────────────────────────────────────────
    # 5. LEAGUE PERFORMANCE
    # ──────────────────────────────────────────────────────────────
    def _analyze_by_league(self, predictions):
        self.stdout.write(self.style.SUCCESS('-' * 90))
        self.stdout.write(self.style.SUCCESS(
            '  5. LEAGUE PERFORMANCE ANALYSIS'))
        self.stdout.write(self.style.SUCCESS(
            '  Which leagues are we best/worst at predicting?'))
        self.stdout.write(self.style.SUCCESS('-' * 90))

        leagues = defaultdict(lambda: {'total': 0, 'correct': 0, 'pl': 0})

        for p in predictions:
            league = p.league or 'Unknown'
            leagues[league]['total'] += 1
            if p.was_correct:
                leagues[league]['correct'] += 1
            if p.profit_loss_10 is not None:
                leagues[league]['pl'] += p.profit_loss_10

        self._print_table_header([
            ('League', 35, 'l'), ('Total', 6, 'r'), ('Correct', 8, 'r'),
            ('Accuracy', 10, 'r'), ('P/L ($10)', 10, 'r'), ('Signal', 15, 'l')
        ])

        for league, data in sorted(leagues.items(),
                                    key=lambda x: x[1]['total'],
                                    reverse=True):
            accuracy = data['correct'] / data['total'] * 100 if data['total'] > 0 else 0

            if accuracy >= 75:
                signal = '[STRONG]'
            elif accuracy >= 60:
                signal = '[OK]'
            elif accuracy >= 50:
                signal = '[WEAK]'
            else:
                signal = '[AVOID?]'

            self.stdout.write(
                '  %-35s %6d %8d %9.1f%% $%+8.2f %-15s' % (
                    league, data['total'], data['correct'], accuracy,
                    data['pl'], signal))

        self.stdout.write('')

    # ──────────────────────────────────────────────────────────────
    # 6. MARKET TYPE ANALYSIS
    # ──────────────────────────────────────────────────────────────
    def _analyze_by_market_type(self, predictions):
        self.stdout.write(self.style.SUCCESS('-' * 90))
        self.stdout.write(self.style.SUCCESS(
            '  6. MARKET TYPE ANALYSIS'))
        self.stdout.write(self.style.SUCCESS(
            '  Which market types are most accurate?'))
        self.stdout.write(self.style.SUCCESS('-' * 90))

        markets = defaultdict(lambda: {'total': 0, 'correct': 0, 'pl': 0})

        for p in predictions:
            market = p.market_type or '1x2'
            markets[market]['total'] += 1
            if p.was_correct:
                markets[market]['correct'] += 1
            if p.profit_loss_10 is not None:
                markets[market]['pl'] += p.profit_loss_10

        self._print_table_header([
            ('Market Type', 25, 'l'), ('Total', 6, 'r'),
            ('Correct', 8, 'r'), ('Accuracy', 10, 'r'), ('P/L ($10)', 10, 'r')
        ])

        for market, data in sorted(markets.items(),
                                    key=lambda x: x[1]['total'],
                                    reverse=True):
            accuracy = data['correct'] / data['total'] * 100 if data['total'] > 0 else 0
            self.stdout.write(
                '  %-25s %6d %8d %9.1f%% $%+8.2f' % (
                    market, data['total'], data['correct'], accuracy, data['pl']))

        self.stdout.write('')

    # ──────────────────────────────────────────────────────────────
    # 7. ODDS RANGE ANALYSIS
    # ──────────────────────────────────────────────────────────────
    def _analyze_by_odds_range(self, predictions):
        self.stdout.write(self.style.SUCCESS('-' * 90))
        self.stdout.write(self.style.SUCCESS(
            '  7. ODDS RANGE ANALYSIS'))
        self.stdout.write(self.style.SUCCESS(
            '  What odds range gives us the best accuracy?'))
        self.stdout.write(self.style.SUCCESS('-' * 90))

        odds_bands = [
            (1.0, 1.3, '1.00-1.30 (Heavy Fav)'),
            (1.3, 1.6, '1.30-1.60 (Fav)'),
            (1.6, 2.0, '1.60-2.00 (Moderate)'),
            (2.0, 2.5, '2.00-2.50 (Even)'),
            (2.5, 3.0, '2.50-3.00 (Slight Dog)'),
            (3.0, 4.0, '3.00-4.00 (Underdog)'),
            (4.0, 20.0, '4.00+ (Long Shot)'),
        ]

        self._print_table_header([
            ('Odds Range', 30, 'l'), ('Total', 6, 'r'),
            ('Correct', 8, 'r'), ('Accuracy', 10, 'r'),
            ('Avg P/L', 10, 'r'), ('ROI', 8, 'r')
        ])

        for low, high, label in odds_bands:
            bucket = [p for p in predictions
                      if self._predicted_odds(p) is not None
                      and low <= self._predicted_odds(p) < high]
            if not bucket:
                continue

            total = len(bucket)
            correct = sum(1 for p in bucket if p.was_correct)
            accuracy = correct / total * 100

            pls = [p.profit_loss_10 for p in bucket if p.profit_loss_10 is not None]
            avg_pl = sum(pls) / len(pls) if pls else 0
            total_pl = sum(pls) if pls else 0
            roi = (total_pl / (total * 10) * 100) if total > 0 else 0

            self.stdout.write(
                '  %-30s %6d %8d %9.1f%% $%+8.2f %+7.1f%%' % (
                    label, total, correct, accuracy, avg_pl, roi))

        self.stdout.write('')

    # ──────────────────────────────────────────────────────────────
    # 8. OUTCOME TYPE ANALYSIS
    # ──────────────────────────────────────────────────────────────
    def _analyze_by_outcome_type(self, predictions):
        self.stdout.write(self.style.SUCCESS('-' * 90))
        self.stdout.write(self.style.SUCCESS(
            '  8. PREDICTED OUTCOME TYPE ANALYSIS'))
        self.stdout.write(self.style.SUCCESS(
            '  Home vs Draw vs Away prediction performance'))
        self.stdout.write(self.style.SUCCESS('-' * 90))

        outcomes = defaultdict(lambda: {'total': 0, 'correct': 0, 'pl': 0,
                                         'confidences': []})

        for p in predictions:
            outcome = p.predicted_outcome or 'Unknown'
            outcomes[outcome]['total'] += 1
            conf = p.confidence * 100 if p.confidence < 1 else p.confidence
            outcomes[outcome]['confidences'].append(conf)
            if p.was_correct:
                outcomes[outcome]['correct'] += 1
            if p.profit_loss_10 is not None:
                outcomes[outcome]['pl'] += p.profit_loss_10

        self._print_table_header([
            ('Outcome', 15, 'l'), ('Total', 6, 'r'),
            ('Correct', 8, 'r'), ('Accuracy', 10, 'r'),
            ('Avg Conf', 10, 'r'), ('P/L ($10)', 10, 'r')
        ])

        for outcome, data in sorted(outcomes.items(),
                                     key=lambda x: x[1]['total'],
                                     reverse=True):
            accuracy = data['correct'] / data['total'] * 100 if data['total'] > 0 else 0
            avg_conf = sum(data['confidences']) / len(data['confidences']) if data['confidences'] else 0

            self.stdout.write(
                '  %-15s %6d %8d %9.1f%% %9.1f%% $%+8.2f' % (
                    outcome, data['total'], data['correct'], accuracy,
                    avg_conf, data['pl']))

        self.stdout.write('')

    # ──────────────────────────────────────────────────────────────
    # 9. PROBABILITY GAP ANALYSIS
    # ──────────────────────────────────────────────────────────────
    def _analyze_probability_gap(self, predictions):
        self.stdout.write(self.style.SUCCESS('-' * 90))
        self.stdout.write(self.style.SUCCESS(
            '  9. PROBABILITY GAP ANALYSIS'))
        self.stdout.write(self.style.SUCCESS(
            '  Does a wider gap between #1 and #2 probability = better accuracy?'))
        self.stdout.write(self.style.SUCCESS('-' * 90))

        gap_bands = [
            (0.0, 0.05, '0-5% (Tossup)'),
            (0.05, 0.10, '5-10% (Slight edge)'),
            (0.10, 0.15, '10-15% (Clear edge)'),
            (0.15, 0.25, '15-25% (Strong edge)'),
            (0.25, 0.40, '25-40% (Dominant)'),
            (0.40, 1.00, '40%+ (Crush)'),
        ]

        self._print_table_header([
            ('Gap Range', 25, 'l'), ('Total', 6, 'r'),
            ('Correct', 8, 'r'), ('Accuracy', 10, 'r'), ('Signal', 20, 'l')
        ])

        for low, high, label in gap_bands:
            bucket = [p for p in predictions
                      if self._prob_gap(p) is not None
                      and low <= self._prob_gap(p) < high]
            if not bucket:
                continue

            total = len(bucket)
            correct = sum(1 for p in bucket if p.was_correct)
            accuracy = correct / total * 100

            if accuracy >= 75:
                signal = '[STRONG]'
            elif accuracy >= 60:
                signal = '[MODERATE]'
            else:
                signal = '[RISKY]'

            self.stdout.write(
                '  %-25s %6d %8d %9.1f%% %-20s' % (
                    label, total, correct, accuracy, signal))

        self.stdout.write('')

    # ──────────────────────────────────────────────────────────────
    # 10. TEAM FORM CORRELATION
    # ──────────────────────────────────────────────────────────────
    def _analyze_form_correlation(self, predictions):
        self.stdout.write(self.style.SUCCESS('-' * 90))
        self.stdout.write(self.style.SUCCESS(
            '  10. TEAM FORM CORRELATION'))
        self.stdout.write(self.style.SUCCESS(
            '  Does recent form data correlate with correct predictions?'))
        self.stdout.write(self.style.SUCCESS('-' * 90))

        def form_win_pct(form_str):
            if not form_str:
                return None
            results = [r.strip().upper() for r in form_str.split(',') if r.strip()]
            if not results:
                return None
            wins = sum(1 for r in results if r == 'W')
            return wins / len(results) * 100

        with_form = [p for p in predictions
                     if p.home_team_form or p.away_team_form]

        if not with_form:
            self.stdout.write('  No team form data available.\n')
            return

        predicted_team_forms = []
        for p in with_form:
            outcome = (p.predicted_outcome or '').lower()
            if outcome == 'home':
                form = form_win_pct(p.home_team_form)
            elif outcome == 'away':
                form = form_win_pct(p.away_team_form)
            else:
                continue
            if form is not None:
                predicted_team_forms.append((p, form))

        if not predicted_team_forms:
            self.stdout.write('  Insufficient form data for analysis.\n')
            return

        form_bands = [
            (0, 20, '0-20% (Very Poor)'),
            (20, 40, '20-40% (Poor)'),
            (40, 60, '40-60% (Average)'),
            (60, 80, '60-80% (Good)'),
            (80, 101, '80-100% (Excellent)'),
        ]

        self._print_table_header([
            ('Predicted Team Form', 25, 'l'), ('Total', 6, 'r'),
            ('Correct', 8, 'r'), ('Accuracy', 10, 'r')
        ])

        for low, high, label in form_bands:
            bucket = [(p, f) for p, f in predicted_team_forms
                      if low <= f < high]
            if not bucket:
                continue

            total = len(bucket)
            correct = sum(1 for p, _ in bucket if p.was_correct)
            accuracy = correct / total * 100

            self.stdout.write(
                '  %-25s %6d %8d %9.1f%%' % (label, total, correct, accuracy))

        self.stdout.write('')

    # ──────────────────────────────────────────────────────────────
    # THRESHOLD BACKTESTING
    # ──────────────────────────────────────────────────────────────
    def _run_threshold_backtest(self, predictions):
        self.stdout.write(self.style.SUCCESS('-' * 90))
        self.stdout.write(self.style.SUCCESS(
            '  THRESHOLD BACKTESTING'))
        self.stdout.write(self.style.SUCCESS(
            '  What would our accuracy be with different filtering thresholds?'))
        self.stdout.write(self.style.SUCCESS('-' * 90))

        # Test parameter grid
        confidence_thresholds = [50, 55, 60, 65, 70]
        ev_thresholds = [0, 5, 10, 15, 20]
        max_odds_options = [2.5, 3.0, 3.5, 4.0, 5.0]

        # Current settings
        current_conf = 60
        current_ev = 15
        current_max_odds = 3.0

        self.stdout.write(
            '\n  Current thresholds: Confidence >= %d%%, EV >= %d%%, '
            'Max Odds <= %.1f' % (current_conf, current_ev, current_max_odds))
        self.stdout.write('')

        # ── Part A: Confidence x EV Grid ──
        self.stdout.write('  Confidence x EV Grid (accuracy%% / count):')
        self.stdout.write('')

        header = '  %-12s' % 'Conf \\ EV'
        for ev_th in ev_thresholds:
            header += '  EV>=%d%%    ' % ev_th
        self.stdout.write(header)
        self.stdout.write('  ' + '-' * (12 + len(ev_thresholds) * 12))

        best_accuracy = 0
        best_params = {}
        min_sample = 10

        for conf_th in confidence_thresholds:
            row = '  C>=%d%%      ' % conf_th
            if conf_th >= 100:
                row = '  C>=%d%%     ' % conf_th
            for ev_th in ev_thresholds:
                filtered = [p for p in predictions
                            if self._conf_pct(p) >= conf_th
                            and self._ev_pct(p) >= ev_th]
                total = len(filtered)
                if total >= min_sample:
                    correct = sum(1 for p in filtered if p.was_correct)
                    acc = correct / total * 100
                    cell = '%.0f%%/%d' % (acc, total)

                    if acc > best_accuracy:
                        best_accuracy = acc
                        best_params = {'conf': conf_th, 'ev': ev_th,
                                       'total': total, 'correct': correct}
                else:
                    cell = '--/%d' % total

                row += '  %-10s' % cell
            self.stdout.write(row)

        self.stdout.write('')

        if best_params:
            self.stdout.write(self.style.SUCCESS(
                '  BEST threshold combo (min %d preds): '
                'Confidence >= %d%%, EV >= %d%% -> '
                '%.1f%% accuracy (%d/%d)' % (
                    min_sample, best_params['conf'], best_params['ev'],
                    best_accuracy, best_params['correct'], best_params['total'])))

        # ── Part B: Max Odds Impact ──
        self.stdout.write('\n  Max Odds Impact:')
        self._print_table_header([
            ('Max Odds', 15, 'l'), ('Total', 6, 'r'),
            ('Correct', 8, 'r'), ('Accuracy', 10, 'r'), ('Change', 10, 'r')
        ])

        current_filtered = [p for p in predictions
                            if self._conf_pct(p) >= current_conf
                            and self._ev_pct(p) >= current_ev
                            and (self._predicted_odds(p) or 2.0) <= current_max_odds]
        current_total = len(current_filtered)
        current_correct = sum(1 for p in current_filtered if p.was_correct)
        current_acc = current_correct / current_total * 100 if current_total > 0 else 0

        for max_odds in max_odds_options:
            filtered = [p for p in predictions
                        if self._conf_pct(p) >= current_conf
                        and self._ev_pct(p) >= current_ev
                        and (self._predicted_odds(p) or 2.0) <= max_odds]
            total = len(filtered)
            if total > 0:
                correct = sum(1 for p in filtered if p.was_correct)
                acc = correct / total * 100
                change = acc - current_acc

                marker = ' <-- current' if max_odds == current_max_odds else ''
                self.stdout.write(
                    '  <= %-11.1f %6d %8d %9.1f%% %+9.1f%%%s' % (
                        max_odds, total, correct, acc, change, marker))

        # ── Part C: Probability Gap Filter ──
        self.stdout.write('\n  Minimum Probability Gap Impact:')
        self._print_table_header([
            ('Min Gap', 15, 'l'), ('Total', 6, 'r'),
            ('Correct', 8, 'r'), ('Accuracy', 10, 'r')
        ])

        for min_gap in [0.0, 0.05, 0.10, 0.15, 0.20, 0.25]:
            filtered = [p for p in predictions
                        if (self._prob_gap(p) or 0) >= min_gap]
            total = len(filtered)
            if total > 0:
                correct = sum(1 for p in filtered if p.was_correct)
                acc = correct / total * 100
                self.stdout.write(
                    '  >= %-11.0f%% %6d %8d %9.1f%%' % (
                        min_gap * 100, total, correct, acc))

        self.stdout.write('')

    # ──────────────────────────────────────────────────────────────
    # RECOMMENDATIONS
    # ──────────────────────────────────────────────────────────────
    def _generate_recommendations(self, predictions, correct, incorrect):
        self.stdout.write(self.style.SUCCESS('-' * 90))
        self.stdout.write(self.style.SUCCESS(
            '  ACTIONABLE RECOMMENDATIONS'))
        self.stdout.write(self.style.SUCCESS('-' * 90))

        total = len(predictions)
        overall_acc = len(correct) / total * 100 if total > 0 else 0

        recommendations = []

        # Check draw performance
        draw_preds = [p for p in predictions
                      if (p.predicted_outcome or '').lower() == 'draw']
        if draw_preds:
            draw_correct = sum(1 for p in draw_preds if p.was_correct)
            draw_acc = draw_correct / len(draw_preds) * 100
            if draw_acc < overall_acc - 10:
                recommendations.append(
                    'Draw predictions accuracy (%.1f%%) is significantly below '
                    'overall (%.1f%%). Consider stricter criteria for draw '
                    'recommendations or requiring higher confidence for draws.' % (
                        draw_acc, overall_acc))

        # Check low confidence misses
        low_conf_misses = [p for p in incorrect if self._conf_pct(p) < 60]
        if low_conf_misses and len(low_conf_misses) > len(incorrect) * 0.3:
            recommendations.append(
                '%d of %d misses (%.0f%%) had confidence < 60%%. '
                'Consider raising the confidence floor.' % (
                    len(low_conf_misses), len(incorrect),
                    len(low_conf_misses) / len(incorrect) * 100))

        # Check high-odds misses
        high_odds_misses = [p for p in incorrect
                            if self._predicted_odds(p) and self._predicted_odds(p) > 3.0]
        if high_odds_misses and len(high_odds_misses) > len(incorrect) * 0.2:
            recommendations.append(
                '%d misses had odds > 3.0. '
                'Consider lowering max_odds to reduce variance.' % len(high_odds_misses))

        # Check league-specific issues
        league_stats = defaultdict(lambda: {'total': 0, 'correct': 0})
        for p in predictions:
            league_stats[p.league]['total'] += 1
            if p.was_correct:
                league_stats[p.league]['correct'] += 1

        for league, stats in league_stats.items():
            if stats['total'] >= 5:
                league_acc = stats['correct'] / stats['total'] * 100
                if league_acc < 50:
                    recommendations.append(
                        '%s accuracy is only %.1f%% (%d/%d). '
                        'Consider excluding or requiring higher thresholds '
                        'for this league.' % (
                            league, league_acc, stats['correct'], stats['total']))

        # Check EV vs accuracy alignment
        high_ev = [p for p in predictions if self._ev_pct(p) >= 25]
        if high_ev:
            high_ev_acc = sum(1 for p in high_ev if p.was_correct) / len(high_ev) * 100
            if high_ev_acc < overall_acc:
                recommendations.append(
                    'High-EV (>=25%%) predictions accuracy (%.1f%%) is below '
                    'overall (%.1f%%). Very high EV may indicate '
                    'bookmaker-model disagreement, not true edge.' % (
                        high_ev_acc, overall_acc))

        # Check if "Value Bet" track is underperforming
        value_bets = [p for p in predictions
                      if self._conf_pct(p) < 60 and self._ev_pct(p) >= 10]
        if value_bets and len(value_bets) >= 3:
            vb_acc = sum(1 for p in value_bets if p.was_correct) / len(value_bets) * 100
            if vb_acc < 50:
                recommendations.append(
                    'Value Bet track (conf<60%%, EV>=10%%) accuracy is only '
                    '%.1f%% (%d bets). This track may be hurting overall '
                    'accuracy. Consider requiring higher EV or disabling.' % (
                        vb_acc, len(value_bets)))

        # Check variance-based filtering potential
        high_var = [p for p in predictions
                    if p.variance is not None and p.variance > 10]
        if high_var and len(high_var) >= 3:
            hv_acc = sum(1 for p in high_var if p.was_correct) / len(high_var) * 100
            if hv_acc < overall_acc - 15:
                recommendations.append(
                    'High-variance predictions (var>10) accuracy is %.1f%% '
                    '(%d preds). Adding a max_variance filter could improve '
                    'accuracy.' % (hv_acc, len(high_var)))

        # Print recommendations
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                self.stdout.write('\n  %d. %s' % (i, rec))
        else:
            self.stdout.write(self.style.SUCCESS(
                '\n  No critical issues found! Current thresholds appear well-calibrated.'))

        # Summary
        self.stdout.write('\n\n  SUMMARY')
        self.stdout.write('  ' + '-' * 40)
        self.stdout.write('  Total predictions analyzed: %d' % total)
        self.stdout.write('  Overall accuracy: %.1f%%' % overall_acc)
        self.stdout.write('  Recommendations generated: %d' % len(recommendations))
        self.stdout.write('  Run with --backtest for threshold optimization')
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=' * 90 + '\n'))

    # ──────────────────────────────────────────────────────────────
    # CSV EXPORT
    # ──────────────────────────────────────────────────────────────
    def _export_to_csv(self, predictions):
        filepath = os.path.join(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(__file__)))),
            'analysis_export.csv')

        fields = [
            'fixture_id', 'home_team', 'away_team', 'league', 'kickoff',
            'predicted_outcome', 'confidence', 'probability_home',
            'probability_draw', 'probability_away', 'odds_home', 'odds_draw',
            'odds_away', 'expected_value', 'model_count', 'consensus',
            'variance', 'market_type', 'home_team_form', 'away_team_form',
            'actual_outcome', 'actual_score_home', 'actual_score_away',
            'was_correct', 'profit_loss_10', 'is_recommended',
        ]

        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            for p in predictions:
                row = {}
                for field in fields:
                    val = getattr(p, field, None)
                    if hasattr(val, 'isoformat'):
                        val = val.isoformat()
                    row[field] = val
                writer.writerow(row)

        self.stdout.write(self.style.SUCCESS(
            '\n  Data exported to: %s\n' % filepath))
