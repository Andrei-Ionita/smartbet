"""
Guards the two DIFFERENT behaviours the pricing-integrity cutoff must have.

Production and tests need opposite things from the same setting:

* **Production must fail closed.** With ``PRICING_INTEGRITY_CUTOFF`` unset, the
  cutoff is a far-future sentinel, so every prediction classifies as
  ``legacy_unverified`` and nothing is published as verified. An unconfigured
  deployment therefore under-claims. That is a safety property, not a bug.

* **Tests must be deterministic.** The same fail-closed default made ~54 claim
  and pricing tests fail for a reason unrelated to what they assert, purely
  because the variable was absent from a developer's ``.env``. A suite that is
  red for an unrelated reason trains people to ignore red.

The resolution is a single test-only value in ``smartbet/settings.py``
(``TEST_PRICING_INTEGRITY_CUTOFF``), applied with ``os.environ.setdefault``
only when ``RUNNING_TESTS``. Production is untouched; an explicit value from CI
still wins; and the fail-closed path stays reachable and tested below.
"""
import importlib
import os
from unittest import mock

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from core.services import public_universe


class PricingIntegrityCutoffConfigTests(SimpleTestCase):
    def tearDown(self):
        # Every test here reloads the module; put the real one back so later
        # tests in the run see the configured cutoff.
        importlib.reload(public_universe)

    def test_tests_run_with_a_configured_cutoff(self):
        """The suite must never depend on a developer's local .env."""
        self.assertTrue(settings.RUNNING_TESTS)
        self.assertTrue(
            public_universe.CUTOFF_IS_CONFIGURED,
            'Tests ran without PRICING_INTEGRITY_CUTOFF configured. '
            'smartbet.settings should have applied TEST_PRICING_INTEGRITY_CUTOFF.',
        )

    def test_test_cutoff_is_the_single_centralised_value(self):
        expected = public_universe.parse_datetime(
            settings.TEST_PRICING_INTEGRITY_CUTOFF
        )
        self.assertEqual(public_universe.PRICING_INTEGRITY_CUTOFF, expected)

    def test_production_fails_closed_when_unset(self):
        """Unset must mean far-future, so nothing can be marked verified."""
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop('PRICING_INTEGRITY_CUTOFF', None)
            reloaded = importlib.reload(public_universe)

            self.assertFalse(reloaded.CUTOFF_IS_CONFIGURED)
            self.assertEqual(reloaded.PRICING_INTEGRITY_CUTOFF.year, 2999)

    def test_invalid_value_is_a_direct_configuration_error(self):
        """A malformed cutoff must name itself, not surface as failing asserts."""
        with mock.patch.dict(
            os.environ, {'PRICING_INTEGRITY_CUTOFF': 'not-a-timestamp'}
        ):
            with self.assertRaises(ImproperlyConfigured) as ctx:
                importlib.reload(public_universe)

        self.assertIn('PRICING_INTEGRITY_CUTOFF', str(ctx.exception))

    def test_explicit_environment_value_wins_over_the_test_default(self):
        """setdefault, not assignment — CI can still pin a specific cutoff."""
        with mock.patch.dict(
            os.environ, {'PRICING_INTEGRITY_CUTOFF': '2020-01-02T03:04:05+00:00'}
        ):
            reloaded = importlib.reload(public_universe)
            self.assertEqual(reloaded.PRICING_INTEGRITY_CUTOFF.year, 2020)
