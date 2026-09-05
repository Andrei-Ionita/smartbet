"""Forward publication, freshness, cross-market ranking and shared receipts."""
import copy
from io import StringIO
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import GemFeedCache, HomepageSelectionAppearance, PublicSelection, SelectionBoard, StrategyLabObservation
from core.services import evidence_capture, public_selections
from core.services import selection_portfolio as portfolio
from core.tests_signal_evidence import _candidate
from core.tests_strategy_lab import candidate as asian_candidate, result as fixture_result


class SelectionPortfolioTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        portfolio.calibration_pairs.cache_clear()

    def direct(self, fixture=100, market='btts', side='yes', probability=.65, odds=2):
        vectors = {
            'btts': {'yes': probability, 'no': 1-probability},
            '1x2': {'home': probability, 'draw': (1-probability)/2, 'away': (1-probability)/2},
            'over_under_1.5': {'over': probability, 'under': 1-probability},
            'over_under_2.5': {'over': probability, 'under': 1-probability},
            'over_under_3.5': {'over': probability, 'under': 1-probability},
            'half_time_result': {'home': probability, 'draw': (1-probability)/2, 'away': (1-probability)/2},
            'half_time_full_time': {f'{a}_{b}': probability if f'{a}_{b}' == side else (1-probability)/8 for a in ('home','draw','away') for b in ('home','draw','away')},
            'double_chance': {'1x': .8, 'x2': .6, '12': .6},
            'correct_score': {'1-0': probability, 'other': 1-probability},
        }
        vector = vectors[market]
        return _candidate(
            fixture_id=fixture, market=market, outcome=side,
            kickoff=(self.now + timedelta(hours=8)).isoformat(), observed_at=self.now.isoformat(),
            normalized_probability=vector[side], raw_probability=vector[side]*100,
            raw_vector=vector, vector_sum=sum(vector.values()), odds=odds,
            odds_captured_at=self.now.isoformat(),
            odds_provenance={'odds_market_id': min(portfolio.DIRECT_PRICE_IDS[market]), 'odds_bookmaker_count': 4,
                             'odds_line': float(market.rsplit('_', 1)[-1]) if market.startswith('over_under_') else None,
                             'odds_bookmaker_name': 'Test', 'odds_min': odds-.05, 'odds_max': odds+.05,
                             'odds_captured_at': self.now.isoformat()},
            market_price_vector={key: {'odds': odds if key == side else max(1.5, (len(vector)-1)*2)} for key in vector},
        )

    def capture(self, direct=(), asian=()):
        with patch('django.utils.timezone.now', return_value=self.now):
            return evidence_capture.capture({'observed_at': self.now.isoformat(),
                'candidates': list(direct), 'strategy_candidates': list(asian), 'fixtures_seen': len(direct)+len(asian)})

    def test_market_caps_homepage_uniqueness_and_same_receipts(self):
        rows = [self.direct(fixture=i, market=market, side=side) for i in range(10, 17)
                for market, side in [('1x2', 'home'), ('btts', 'yes')]]
        self.capture(rows)
        first = portfolio.publish_portfolio(self.now)
        second = portfolio.publish_portfolio(self.now)
        self.assertEqual(first['published'], 10)
        self.assertEqual(second['published'], 0)
        self.assertEqual(SelectionBoard.objects.count(), 1)
        body = portfolio.read_portfolio(self.now)
        self.assertEqual(len(body['homepage']), 5)
        self.assertEqual(len({r['fixture_id'] for r in body['homepage']}), 5)
        # The better market may legitimately fill the entire homepage.
        self.assertEqual(len({r['market_type'] for r in body['homepage']}), 1)
        ids = {r['selection_id'] for m in body['markets'] for r in m['selections']}
        self.assertTrue(all(r['selection_id'] in ids for r in body['homepage']))
        self.assertEqual(PublicSelection.objects.count(), 10)
        self.assertEqual(HomepageSelectionAppearance.objects.count(), 5)

    def test_all_direct_markets_compete_without_a_60_percent_floor(self):
        rows = [self.direct(fixture=i, market=market, side=side) for i, (market, side) in enumerate([
            ('1x2','home'), ('btts','yes'), ('over_under_1.5','over'),
            ('over_under_2.5','over'), ('over_under_3.5','over'),
            ('half_time_result','home'), ('half_time_full_time','home_home'),
            ('correct_score','1-0'),
        ], 100)]
        rows.append(self.direct(fixture=500, market='1x2', side='home', probability=.4, odds=3.2))
        self.capture(rows)
        portfolio.publish_portfolio(self.now)
        self.assertEqual(PublicSelection.objects.count(), 9)
        self.assertTrue(PublicSelection.objects.filter(fixture_id=500).exists())

    def test_fresh_recheck_does_not_duplicate_archive_or_reprice_receipt(self):
        original = self.direct()
        self.capture([original])
        portfolio.publish_portfolio(self.now)
        row = PublicSelection.objects.get()
        original_hash = row.selection_hash
        count = StrategyLabObservation.objects.count()
        self.now += timedelta(hours=3)
        fresh = copy.deepcopy(original)
        fresh.update(observed_at=self.now.isoformat(), odds_captured_at=self.now.isoformat())
        self.capture([fresh])
        self.assertEqual(StrategyLabObservation.objects.count(), count)
        portfolio.publish_portfolio(self.now)
        self.assertEqual(len(portfolio.read_portfolio(self.now)['homepage']), 1)
        row.refresh_from_db()
        self.assertEqual(row.selection_hash, original_hash)
        self.assertTrue(row.verify_integrity())

    def test_stale_and_missing_current_quotes_are_not_republished(self):
        self.capture([self.direct()])
        portfolio.publish_portfolio(self.now)
        self.assertEqual(portfolio.read_portfolio(self.now + timedelta(hours=3))['homepage'], [])
        self.capture([])
        portfolio.publish_portfolio(self.now + timedelta(seconds=1))
        self.assertEqual(portfolio.read_portfolio(self.now + timedelta(seconds=1))['homepage'], [])
        self.assertEqual(PublicSelection.objects.count(), 1)

    def test_side_cannot_change_after_publication_and_losses_remain(self):
        original = self.direct()
        self.capture([original])
        portfolio.publish_portfolio(self.now)
        changed = self.direct(side='no', probability=.3, odds=2)
        self.capture([changed])
        portfolio.publish_portfolio(self.now + timedelta(seconds=1))
        row = PublicSelection.objects.get()
        self.assertEqual(row.side, 'yes')
        fixture_result(row.fixture_id, 0, 0)
        public_selections.settle_public_selections()
        report = portfolio.read_results()
        self.assertEqual(report['performance']['overall']['lost'], 1)
        self.assertEqual(report['performance']['overall']['roi_percent'], -100)
        self.assertEqual(report['homepage_performance']['overall']['lost'], 1)

    def test_asian_quarter_settlement_and_no_invented_probability(self):
        c = asian_candidate(fixture_id=999, handicap=-.25, lower=.15)
        c.update(kickoff=(self.now+timedelta(hours=8)).isoformat(),
                 observed_at=self.now.isoformat(), captured_at=self.now.isoformat())
        self.capture(asian=[c])
        portfolio.publish_portfolio(self.now)
        body = portfolio.read_portfolio(self.now)
        self.assertIsNone(body['homepage'][0]['evidence']['model_probability'])
        fixture_result(999, 1, 1)
        public_selections.settle_public_selections()
        report = portfolio.read_results()['performance']['overall']
        self.assertEqual(report['half_lost'], 1)
        self.assertEqual(report['profit_units'], -.5)

    def test_no_vig_double_chance_uses_underlying_1x2_book(self):
        self.capture([self.direct(fixture=123, market='1x2', side='home'),
                      self.direct(fixture=123, market='double_chance', side='1x', odds=1.5)])
        portfolio.publish_portfolio(self.now)
        dc = next(m for m in portfolio.read_portfolio(self.now)['markets'] if m['key'] == 'double_chance')
        self.assertEqual(len(dc['selections']), 1)
        self.assertAlmostEqual(dc['selections'][0]['evidence']['market_probability'], .75)

    def test_read_api_does_not_publish_and_preserves_empty_state(self):
        response = APIClient().get('/api/selection-portfolio/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'delayed')
        self.assertEqual(PublicSelection.objects.count(), 0)

    def test_snapshot_integrity_failure_hides_live_cards(self):
        self.capture([self.direct()])
        portfolio.publish_portfolio(self.now)
        SelectionBoard.objects.update(evidence_hash='tampered')
        self.assertEqual(portfolio.read_portfolio(self.now)['homepage'], [])

    def test_calibration_cannot_use_a_result_that_arrived_after_asof(self):
        c = self.direct()
        c.update(kickoff=(self.now-timedelta(hours=5)).isoformat(),
                 observed_at=(self.now-timedelta(hours=8)).isoformat())
        self.capture([c])
        fixture_result(100, 1, 1)
        self.assertEqual(portfolio.calibration_pairs('btts', 'yes', self.now), ())
        self.assertEqual(len(portfolio.calibration_pairs('btts', 'yes', timezone.now()+timedelta(seconds=1))), 1)

    def test_wrong_market_quote_cannot_enter_record(self):
        c = self.direct(market='over_under_2.5', side='over')
        c['odds_provenance']['odds_market_id'] = 53  # second-half total
        self.capture([c])
        portfolio.publish_portfolio(self.now)
        self.assertEqual(PublicSelection.objects.count(), 0)

    def test_changed_rules_require_a_new_engine_version(self):
        self.capture([self.direct()])
        portfolio.publish_portfolio(self.now)
        with patch.object(portfolio, 'POLICY_HASH', 'different'):
            with self.assertRaisesRegex(ValueError, 'new version'):
                portfolio.publish_portfolio(self.now + timedelta(seconds=1))

    def test_scheduler_command_publishes_through_the_new_path(self):
        self.capture([self.direct()])
        output = StringIO()
        call_command('publish_public_selections', stdout=output)
        self.assertIn('portfolio +1', output.getvalue())
        self.assertEqual(HomepageSelectionAppearance.objects.count(), 1)

    def test_scheduler_reports_a_missing_scan_instead_of_false_success(self):
        with self.assertRaises(CommandError):
            call_command('publish_public_selections', stdout=StringIO())
