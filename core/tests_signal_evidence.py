"""
Evidence-capture contracts (Priority 1B).

Each test pins something the 2026-08-04 calibration audit found missing: the
losing side of every market, the raw provider vector, the raw probability kept
apart from the heuristic score, and an append-only store that a scheduler retry
cannot inflate.
"""
import uuid
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from core.models import SignalObservation
from core.services import evidence_capture


def _candidate(**overrides):
    now = timezone.now()
    base = {
        'fixture_id': 5001,
        'home_team': 'A', 'away_team': 'B', 'league': 'Test League', 'league_id': 1,
        'kickoff': (now + timedelta(days=2)).isoformat(),
        'observed_at': now.isoformat(),
        'market': 'over_under_2.5',
        'outcome': 'over',
        'provider': 'sportmonks',
        'provider_type_id': 235,
        'provider_context': {
            'fixture_predictable': True,
            'league_market_performance': {
                'predictability': 'good', 'predictivePower': 'up',
            },
            'native_value_bet': None,
        },
        'raw_probability': 62.0,
        'normalized_probability': 0.62,
        'raw_vector': {'over': 0.62, 'under': 0.38},
        'vector_sum': 1.0,
        'vector_complete': True,
        'price_status': 'verified',
        'odds': 1.75,
        'bookmaker': 'bet365',
        'odds_captured_at': now.isoformat(),
        'odds_provenance': {'odds_bookmaker_name': 'bet365'},
        'market_price_vector': {'over': {'odds': 1.75}, 'under': {'odds': 2.05}},
        'price_vector_complete': True,
        'pipeline_version': 'evidence-v1',
        'calculation_version': 'abc123',
    }
    base.update(overrides)
    return base


def _payload(candidates, observed_at=None):
    return {
        'success': True,
        'observed_at': observed_at or timezone.now().isoformat(),
        'candidate_count': len(candidates),
        'candidates': candidates,
    }


class EvidenceCaptureTests(TestCase):
    def test_persists_every_outcome_including_the_losing_side(self):
        payload = _payload([
            _candidate(outcome='over', normalized_probability=0.62),
            _candidate(outcome='under', normalized_probability=0.38,
                       raw_probability=38.0),
        ])
        summary = evidence_capture.capture(payload)

        self.assertEqual(summary['written'], 2)
        outcomes = set(SignalObservation.objects.values_list('outcome', flat=True))
        self.assertEqual(outcomes, {'over', 'under'})

    def test_keeps_the_full_vector_with_outcome_identities(self):
        evidence_capture.capture(_payload([_candidate()]))
        row = SignalObservation.objects.get()

        self.assertEqual(row.raw_vector, {'over': 0.62, 'under': 0.38})
        self.assertTrue(row.vector_complete)
        # The losing side is stored, never inferred as 1 - p.
        self.assertIn('under', row.raw_vector)

    def test_persists_pre_match_provider_quality_context(self):
        evidence_capture.capture(_payload([_candidate()]))
        row = SignalObservation.objects.get()

        self.assertTrue(row.provider_context['fixture_predictable'])
        self.assertEqual(
            row.provider_context['league_market_performance']['predictability'],
            'good',
        )

    def test_changed_provider_context_appends_new_evidence(self):
        evidence_capture.capture(_payload([_candidate()]))
        evidence_capture.capture(_payload([_candidate(provider_context={
            'fixture_predictable': True,
            'league_market_performance': {
                'predictability': 'high', 'predictivePower': 'up',
            },
            'native_value_bet': None,
        })]))

        self.assertEqual(SignalObservation.objects.count(), 2)

    def test_raw_probability_is_never_overwritten_by_the_adjusted_score(self):
        evidence_capture.capture(_payload([_candidate()]))
        row = SignalObservation.objects.get()

        self.assertEqual(row.normalized_probability, 0.62)
        self.assertEqual(row.raw_probability, 62.0)
        # The heuristic lives in its own column and is absent unless supplied.
        self.assertIsNone(row.adjusted_score)
        self.assertIsNone(row.form_multiplier)

    def test_an_incomplete_vector_is_flagged_not_assumed_normalized(self):
        payload = _payload([_candidate(
            raw_vector={'over': 0.62}, vector_sum=0.62, vector_complete=False,
        )])
        evidence_capture.capture(payload)
        row = SignalObservation.objects.get()

        self.assertFalse(row.vector_complete)
        self.assertAlmostEqual(row.vector_sum, 0.62)

    def test_replaying_the_same_payload_is_idempotent(self):
        payload = _payload([_candidate(outcome='over'), _candidate(outcome='under')])
        first = evidence_capture.capture(payload)
        second = evidence_capture.capture(payload)

        self.assertEqual(first['written'], 2)
        self.assertEqual(second['written'], 0)
        self.assertEqual(second['skipped_duplicate'], 2)
        self.assertEqual(SignalObservation.objects.count(), 2)

    def test_a_moved_price_is_new_evidence_not_a_duplicate(self):
        evidence_capture.capture(_payload([_candidate()]))
        evidence_capture.capture(_payload([_candidate(odds=1.95)]))

        self.assertEqual(SignalObservation.objects.count(), 2)

    def test_a_restamped_but_unchanged_quote_is_not_new_evidence(self):
        # odds_captured_at advances whenever the provider re-stamps an unchanged
        # price. Treating that as new would write tens of thousands of
        # near-identical rows a day for nothing.
        now = timezone.now()
        evidence_capture.capture(_payload([_candidate(
            odds_captured_at=now.isoformat())]))
        evidence_capture.capture(_payload([_candidate(
            odds_captured_at=(now + timedelta(hours=1)).isoformat())]))

        self.assertEqual(SignalObservation.objects.count(), 1)

    def test_a_changed_probability_is_new_evidence(self):
        evidence_capture.capture(_payload([_candidate()]))
        evidence_capture.capture(_payload([_candidate(
            normalized_probability=0.64, raw_vector={'over': 0.64, 'under': 0.36})]))

        self.assertEqual(SignalObservation.objects.count(), 2)

    def test_a_later_observation_cannot_overwrite_an_earlier_one(self):
        evidence_capture.capture(_payload([_candidate()]))
        row = SignalObservation.objects.get()
        original = row.normalized_probability

        row.normalized_probability = 0.99
        with self.assertRaises(ValueError):
            row.save()

        row.refresh_from_db()
        self.assertEqual(row.normalized_probability, original)

    def test_post_kickoff_observations_are_recorded_but_marked_negative(self):
        now = timezone.now()
        payload = _payload([_candidate(
            kickoff=(now - timedelta(hours=3)).isoformat(),
            observed_at=now.isoformat(),
        )])
        summary = evidence_capture.capture(payload)

        self.assertEqual(summary['post_kickoff'], 1)
        row = SignalObservation.objects.get()
        self.assertLess(row.hours_to_kickoff, 0)

    def test_hours_to_kickoff_is_computed_from_the_observation(self):
        now = timezone.now()
        payload = _payload([_candidate(
            kickoff=(now + timedelta(hours=24)).isoformat(),
            observed_at=now.isoformat(),
        )])
        evidence_capture.capture(payload)
        self.assertAlmostEqual(SignalObservation.objects.get().hours_to_kickoff,
                               24, places=1)

    def test_price_vector_completeness_gates_a_devigged_baseline(self):
        evidence_capture.capture(_payload([
            _candidate(outcome='over'),
            _candidate(outcome='under',
                       market_price_vector={'over': {'odds': 1.75},
                                            'under': {'odds': None}},
                       price_vector_complete=False),
        ]))
        rows = {r.outcome: r for r in SignalObservation.objects.all()}
        self.assertTrue(rows['over'].price_vector_complete)
        self.assertFalse(rows['under'].price_vector_complete)

    def test_a_candidate_without_a_probability_is_rejected(self):
        summary = evidence_capture.capture(
            _payload([_candidate(normalized_probability=None)])
        )
        self.assertEqual(summary['written'], 0)
        self.assertEqual(summary['invalid'], 1)


class EvidenceFetchFailsClosedTests(TestCase):
    def test_missing_secret_refuses_to_call_the_feed(self):
        with self.assertRaises(RuntimeError) as ctx:
            evidence_capture.fetch_evidence(base_url='https://example.test', secret='')
        self.assertIn('INTERNAL_API_SECRET', str(ctx.exception))


class EvidenceIsolationTests(TestCase):
    """Evidence capture must not touch the public record."""

    def test_capture_writes_only_signal_observations(self):
        from core.models import (
            PredictionLog, PredictionSnapshot, PublishedClaim, PublishedClaimResult,
        )
        before = (
            PredictionLog.objects.count(), PredictionSnapshot.objects.count(),
            PublishedClaim.objects.count(), PublishedClaimResult.objects.count(),
        )
        evidence_capture.capture(_payload([_candidate()]))
        after = (
            PredictionLog.objects.count(), PredictionSnapshot.objects.count(),
            PublishedClaim.objects.count(), PublishedClaimResult.objects.count(),
        )
        self.assertEqual(before, after)
        self.assertEqual(SignalObservation.objects.count(), 1)

    def test_the_capture_service_never_imports_a_publication_path(self):
        import inspect
        import re

        # Strip docstrings and comments: prose may name the models this code
        # must not touch, and does.
        src = inspect.getsource(evidence_capture)
        code = re.sub(r'"""[\s\S]*?"""', '', src)
        code = re.sub(r'#[^\r\n]*', '', code)

        for forbidden in ('PublishedClaim', 'PredictionSnapshot', 'PredictionLog',
                          'claim_publication', 'settle'):
            self.assertNotIn(
                forbidden, code,
                f'{forbidden} must be unreachable from evidence capture — this '
                'service writes SignalObservation and nothing else.',
            )
        self.assertIn('SignalObservation', code)


class EvidenceHorizonTests(TestCase):
    """Hourly rows are observations, not decisions."""

    def test_many_hourly_rows_collapse_to_few_decisions(self):
        now = timezone.now()
        kickoff = now + timedelta(hours=80)
        candidates = []
        for hours_ago in range(0, 40):
            candidates.append(_candidate(
                observed_at=(now + timedelta(hours=hours_ago)).isoformat(),
                kickoff=kickoff.isoformat(),
                odds=1.70 + hours_ago * 0.01,  # each is genuinely new evidence
            ))
        evidence_capture.capture(_payload(candidates))
        self.assertEqual(SignalObservation.objects.count(), 40)

        # One fixture-market, so at most one decision per target horizon.
        pairs = SignalObservation.objects.values('fixture_id', 'market').distinct()
        self.assertEqual(pairs.count(), 1)
