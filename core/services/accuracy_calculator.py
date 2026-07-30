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
from core.services import public_universe

# Per-market confidence thresholds (ROI tuning E4, SHIP verdict).
# See docs/audit/roi-tuning-2026-07-20.md — the 0.55-0.60 confidence bucket
# for over_under_2.5 showed +31.50% ROI on n=49 (CI_lo +1.36%, significant),
# but was being filtered out by the global >=0.60 threshold.
#
# These names are re-exported from core.services.public_universe, which is now
# THE single definition of the public verified universe. Do not redefine them
# here — divergent filters are how the 2026-07-29 audit found the public ROI
# reading +10.61% against a defensible -4.90%.
PER_MARKET_CONF_THRESHOLDS = public_universe.PER_MARKET_CONF_THRESHOLDS
DEFAULT_CONF_THRESHOLD = public_universe.DEFAULT_CONF_THRESHOLD


def _claim_won(claim):
    """Win/loss from the RECORDED settlement, never the mutable prediction."""
    from core.models import PublishedClaim

    return claim.result_status == PublishedClaim.STATUS_WON


class AccuracyCalculator:
    """
    Calculate comprehensive accuracy metrics for SmartBet predictions.

    All public metrics denominate on ONE universe: recommended, resolved bets
    passing the per-market confidence gate. This matches the platform's
    transparency thesis ("we track only what we recommend to you") and keeps
    the accuracy card and ROI card consistent — previously accuracy counted all
    completed predictions (incl. picks never recommended) at a flat 0.60 gate,
    while ROI counted recommended bets at the per-market gate, producing a
    confusing ~120-row denominator mismatch on the dashboard.
    """

    def _confidence_filter(self) -> Q:
        """Per-market confidence gate. Delegates to the shared definition."""
        return public_universe.confidence_filter()

    def _recommended_base_qs(self):
        """Base queryset every public metric denominates on.

        Delegates to `public_universe.resolved_qs()`, which additionally
        excludes quarantined rows and any pick whose price provenance is not
        verified. Before 2026-07-29 this method omitted BOTH exclusions, so 8
        quarantined NULL-odds rows inflated the published ROI from 5.59% to
        10.61% while every audit script excluded them.
        """
        return public_universe.resolved_qs()

    # ── Public performance: ALL metrics denominate on resolved PublishedClaims ──
    # PredictionLog rows were mutable across pipeline re-runs. Grading was always
    # correct, but we cannot prove a stored predicted_outcome is identical to the
    # one generated at its timestamp. Only a published claim carries that
    # guarantee, so accuracy and ROI now share one claim-based universe.
    # See docs/audit/gem-selector-diagnostics-2026-07-29.md.

    def _resolved_claims(self):
        return public_universe.resolved_claims()

    def get_overall_accuracy(self) -> Dict:
        """Overall accuracy across resolved, verified published claims."""
        claims = self._resolved_claims()
        total = len(claims)
        correct = sum(1 for c in claims if _claim_won(c))
        accuracy = (correct / total * 100) if total > 0 else 0

        def outcome_block(name):
            subset = [c for c in claims if c.predicted_outcome == name]
            hits = sum(1 for c in subset if _claim_won(c))
            return {
                'total': len(subset),
                'correct': hits,
                'accuracy': round(hits / len(subset) * 100, 1) if subset else 0,
            }

        return {
            'overall': {
                'total_predictions': total,
                'correct_predictions': correct,
                'incorrect_predictions': total - correct,
                'accuracy_percent': round(accuracy, 1),
                # Lets every surface render "Building verified record" instead of
                # a 0% that reads as break-even performance.
                'has_verified_results': total > 0,
            },
            'by_outcome': {
                'home': outcome_block('Home'),
                'draw': outcome_block('Draw'),
                'away': outcome_block('Away'),
            },
        }

    def get_accuracy_by_confidence(self) -> List[Dict]:
        """Accuracy by confidence band, over resolved verified claims."""
        claims = self._resolved_claims()
        ranges = [
            (0.70, 1.01, '70-100%', 'Very High'),
            (0.65, 0.70, '65-70%', 'High'),
            (0.60, 0.65, '60-65%', 'Medium-High'),
            (0.55, 0.60, '55-60%', 'Medium'),
        ]

        results = []
        for min_conf, max_conf, label, category in ranges:
            subset = [c for c in claims if min_conf <= (c.confidence or 0) < max_conf]
            if not subset:
                continue
            hits = sum(1 for c in subset if _claim_won(c))
            results.append({
                'confidence_range': label,
                'category': category,
                'total': len(subset),
                'correct': hits,
                'accuracy': round(hits / len(subset) * 100, 1),
            })
        return results

    def get_accuracy_by_league(self) -> List[Dict]:
        """Accuracy + ROI by league, over resolved verified claims.

        Returns exactly one row per league. The previous queryset version
        de-duplicated on (league, kickoff) because PredictionLog.Meta.ordering
        leaked `kickoff` into DISTINCT, returning 241 rows for 25 leagues
        (2026-07-29 audit, finding F8).
        """
        claims = self._resolved_claims()
        by_league = {}
        for c in claims:
            by_league.setdefault(c.league, []).append(c)

        results = []
        for league, subset in by_league.items():
            total = len(subset)
            correct = sum(1 for c in subset if _claim_won(c))
            pls = [public_universe.claim_profit_loss(c) for c in subset]
            total_pl = sum(v for v in pls if v is not None)
            results.append({
                'league': league,
                'total_predictions': total,
                'correct_predictions': correct,
                'accuracy_percent': round(correct / total * 100, 1) if total else 0,
                'roi_percent': round(total_pl / (total * 10) * 100, 1) if total else 0,
            })

        # Sort by total predictions (most active leagues first)
        results.sort(key=lambda x: x['total_predictions'], reverse=True)
        
        return results
    
    def get_roi_simulation(self, stake_per_bet: float = 10.0) -> Dict:
        """Flat-stake ROI over resolved, verified published claims.

        Money figures use each CLAIM's published price, not the mutable row's
        `profit_loss_10`, so the number can never drift from what was posted.
        """
        claims = self._resolved_claims()

        entries = []
        for claim in claims:
            pl = public_universe.claim_profit_loss(claim, stake=stake_per_bet)
            if pl is not None:
                entries.append((claim, pl))

        total_bets = len(entries)
        total_staked = total_bets * stake_per_bet
        total_pl = sum(pl for _, pl in entries)
        roi = (total_pl / total_staked * 100) if total_staked > 0 else 0

        wins = sum(1 for c, _ in entries if _claim_won(c))
        losses = total_bets - wins
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
            'stake_per_bet': stake_per_bet,
            # Surfaces must render "No verified results yet" rather than +0%.
            'has_verified_results': total_bets > 0,
        }
    
    def get_performance_over_time(self, days: int = 30) -> List[Dict]:
        """
        Get accuracy performance over time for recommended bets passing the
        per-market confidence gate (same universe as the ROI card).
        """
        cutoff_date = timezone.now() - timedelta(days=days)

        # Public surface -> the verified claim universe, like every other metric.
        completed = [
            c.prediction for c in public_universe.resolved_claims()
            if c.kickoff >= cutoff_date
        ]
        completed.sort(key=lambda p: p.kickoff)
        
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

