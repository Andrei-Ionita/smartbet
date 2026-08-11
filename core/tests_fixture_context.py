from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from core.models import FixtureContextObservation
from core.services import evidence_capture
from core.services.fixture_context_timeline import build_timeline


def context(**overrides):
    now = timezone.now()
    value = {
        'fixture_id': 7001,
        'home_team': 'Alpha',
        'away_team': 'Beta',
        'home_team_id': 10,
        'away_team_id': 20,
        'league': 'Test League',
        'league_id': 1,
        'kickoff': (now + timedelta(hours=24)).isoformat(),
        'observed_at': now.isoformat(),
        'fixture_predictable': True,
        'lineup_status': 'unavailable',
        'home_formation': '',
        'away_formation': '',
        'home_form': 'WWDLW',
        'away_form': 'LDWDL',
        'sidelined': [
            {'participant_id': 10, 'player_id': 101, 'player_name': 'A One'},
            {'participant_id': 20, 'player_id': 201, 'player_name': 'B One'},
        ],
        'lineups': [],
        'referees': [],
        'venue': {'id': 3, 'name': 'Example Ground'},
        'neutral_venue': False,
        'data_availability': {'venue': True, 'lineups': False},
        'calculation_version': 'test-sha',
    }
    value.update(overrides)
    return value


def payload(*contexts):
    return {
        'success': True,
        'observed_at': timezone.now().isoformat(),
        'candidates': [],
        'fixture_contexts': list(contexts),
    }


class FixtureContextCaptureTests(TestCase):
    def test_context_is_persisted_with_team_specific_absence_counts(self):
        summary = evidence_capture.capture(payload(context()))
        row = FixtureContextObservation.objects.get()

        self.assertEqual(summary['context_written'], 1)
        self.assertEqual(row.home_sidelined_count, 1)
        self.assertEqual(row.away_sidelined_count, 1)
        self.assertEqual(row.venue['name'], 'Example Ground')

    def test_unchanged_scheduler_retry_does_not_create_timeline_noise(self):
        first = context()
        later = {
            **first,
            'observed_at': (timezone.now() + timedelta(hours=1)).isoformat(),
        }
        evidence_capture.capture(payload(first))
        summary = evidence_capture.capture(payload(later))

        self.assertEqual(summary['context_written'], 0)
        self.assertEqual(summary['context_skipped_duplicate'], 1)
        self.assertEqual(FixtureContextObservation.objects.count(), 1)

    def test_a_real_context_change_appends_instead_of_overwriting(self):
        now = timezone.now()
        first = context(observed_at=now.isoformat())
        changed = context(
            observed_at=(now + timedelta(hours=2)).isoformat(),
            lineup_status='confirmed',
            home_formation='4-3-3',
            lineups=[{'participant_id': 10, 'player_id': 101}],
        )
        evidence_capture.capture(payload(first))
        evidence_capture.capture(payload(changed))

        self.assertEqual(FixtureContextObservation.objects.count(), 2)
        timeline = build_timeline(7001)
        codes = {event['code'] for event in timeline['events']}
        self.assertIn('lineup_status_changed', codes)
        self.assertIn('formation_changed', codes)
        self.assertEqual(timeline['current']['lineup_status'], 'confirmed')

    def test_context_rows_are_structurally_append_only(self):
        evidence_capture.capture(payload(context()))
        row = FixtureContextObservation.objects.get()
        row.home_form = 'LLLLL'
        with self.assertRaises(ValueError):
            row.save()

    def test_post_kickoff_context_is_preserved_but_not_published(self):
        now = timezone.now()
        evidence_capture.capture(payload(context(
            kickoff=(now - timedelta(hours=1)).isoformat(),
            observed_at=now.isoformat(),
        )))
        self.assertEqual(FixtureContextObservation.objects.count(), 1)
        self.assertEqual(build_timeline(7001)['snapshot_count'], 0)

    def test_public_endpoint_returns_only_the_derived_timeline(self):
        evidence_capture.capture(payload(context()))
        response = self.client.get('/api/fixture/7001/context-timeline/')

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['success'])
        self.assertEqual(body['data']['source'], 'append_only_pre_match_observations')
        self.assertEqual(body['data']['snapshot_count'], 1)
        self.assertNotIn('sidelined', body['data']['current'])
        self.assertNotIn('referees', body['data']['current'])
        self.assertNotIn('latitude', body['data']['current']['venue'])
