"""
Secrets must never reach stdout, stderr, a log record, or an HTTP body.

The 2026-08-06 exposure was not a stray print. SportMonks authenticates with the
token as a QUERY PARAMETER, and `requests` embeds the fully resolved URL in its
exception message — so every `print(f"...{e}")` around a provider call is a
credential disclosure waiting for the provider to go down. One of them also fed
an HTTP response body.

These tests use a FAKE token throughout. A real one must never appear in a test
fixture; the last test here fails if the live production token is readable in
this process at all while the suite runs.
"""
import io
import logging
import os
from unittest.mock import patch

import requests
from django.test import SimpleTestCase

from core.services.redaction import (REDACTED, RedactingFilter, redact,
                                     redact_exception)

FAKE_TOKEN = 'FAKE_SPORTMONKS_TOKEN_abcdef0123456789'
FAKE_SECRET = 'FAKE_INTERNAL_SECRET_9876543210zyxw'


class RedactKnownSecretValues(SimpleTestCase):
    """Rule 1: the live value of a known secret, wherever it appears."""

    def test_token_in_a_url_is_removed(self):
        with patch.dict(os.environ, {'SPORTMONKS_API_TOKEN': FAKE_TOKEN}):
            url = f'https://api.sportmonks.com/v3/football/fixtures?api_token={FAKE_TOKEN}&include=x'
            out = redact(url)
        self.assertNotIn(FAKE_TOKEN, out)
        self.assertIn(REDACTED, out)
        # The rest of the URL survives — a redacted log line must still diagnose.
        self.assertIn('api.sportmonks.com', out)
        self.assertIn('include=x', out)

    def test_secret_is_removed_from_arbitrary_text(self):
        with patch.dict(os.environ, {'INTERNAL_API_SECRET': FAKE_SECRET}):
            out = redact(f'header was {FAKE_SECRET} lol')
        self.assertNotIn(FAKE_SECRET, out)

    def test_short_values_are_not_blanket_replaced(self):
        # A 1-char "secret" would otherwise mangle every unrelated line.
        with patch.dict(os.environ, {'SPORTMONKS_API_TOKEN': 'x'}):
            self.assertEqual(redact('a x b'), 'a x b')


class RedactCredentialShapedParams(SimpleTestCase):
    """Rule 2: credential-shaped query params, even for unknown values."""

    def test_unknown_token_value_is_still_removed(self):
        with patch.dict(os.environ, {}, clear=False):
            out = redact('https://x.test/a?api_token=SOME_UNREGISTERED_VALUE&b=1')
        self.assertNotIn('SOME_UNREGISTERED_VALUE', out)
        self.assertIn('b=1', out)

    def test_various_credential_params(self):
        for param in ('token', 'api_key', 'secret', 'password', 'signature',
                      'access_token'):
            out = redact(f'https://x.test/a?{param}=SUPERSECRETVALUE')
            self.assertNotIn('SUPERSECRETVALUE', out, param)

    def test_authorization_header_is_removed(self):
        out = redact("{'Authorization': 'Bearer abcdef1234567890'}")
        self.assertNotIn('abcdef1234567890', out)

    def test_internal_auth_header_is_removed(self):
        out = redact("X-Internal-Auth: SOMELONGSECRETVALUE123")
        self.assertNotIn('SOMELONGSECRETVALUE123', out)


class RedactRealRequestsException(SimpleTestCase):
    """The actual 2026-08-06 shape: a requests exception carrying the URL."""

    def test_connection_error_message_is_scrubbed(self):
        with patch.dict(os.environ, {'SPORTMONKS_API_TOKEN': FAKE_TOKEN}):
            url = f'/v3/football/fixtures/between/2026-08-06/2026-08-20?api_token={FAKE_TOKEN}&include=participants'
            exc = requests.exceptions.ConnectionError(
                f"HTTPSConnectionPool(host='api.sportmonks.com', port=443): "
                f"Max retries exceeded with url: {url}"
            )
            out = redact_exception(exc)

        self.assertNotIn(FAKE_TOKEN, out)
        # The exception CLASS is what aids diagnosis, and it survives.
        self.assertIn('ConnectionError', out)
        self.assertIn('api.sportmonks.com', out)

    def test_redact_never_raises(self):
        class Hostile:
            def __str__(self):
                raise ValueError('nope')

        self.assertEqual(redact(Hostile()), REDACTED)


class LoggingFilterScrubsRecords(SimpleTestCase):
    """Defence in depth for call sites — and libraries — that forget."""

    def _capture(self, emit):
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.addFilter(RedactingFilter())
        logger = logging.getLogger('redaction_test')
        logger.handlers = [handler]
        logger.propagate = False
        logger.setLevel(logging.DEBUG)
        emit(logger)
        handler.flush()
        return stream.getvalue()

    def test_message_is_scrubbed(self):
        with patch.dict(os.environ, {'SPORTMONKS_API_TOKEN': FAKE_TOKEN}):
            out = self._capture(
                lambda log: log.error('calling ?api_token=%s' % FAKE_TOKEN))
        self.assertNotIn(FAKE_TOKEN, out)

    def test_args_are_scrubbed(self):
        with patch.dict(os.environ, {'SPORTMONKS_API_TOKEN': FAKE_TOKEN}):
            out = self._capture(lambda log: log.error('url=%s', FAKE_TOKEN))
        self.assertNotIn(FAKE_TOKEN, out)

    def test_traceback_text_is_scrubbed(self):
        """logger.exception() writes the traceback — result_evidence uses it."""
        def emit(log):
            try:
                raise requests.exceptions.ConnectionError(
                    f'failed for url ?api_token={FAKE_TOKEN}')
            except Exception:
                log.exception('batch failed')

        with patch.dict(os.environ, {'SPORTMONKS_API_TOKEN': FAKE_TOKEN}):
            out = self._capture(emit)
        self.assertNotIn(FAKE_TOKEN, out)


class ProviderCallSitesAreRedacted(SimpleTestCase):
    """The specific lines that leaked, pinned so they cannot regress."""

    def _source(self, rel):
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        return (root / rel).read_text(encoding='utf-8')

    def test_search_fixtures_does_not_print_raw_exception(self):
        src = self._source('core/api_views.py')
        self.assertNotIn('print(f"SportMonks API error: {str(e)}")', src)
        self.assertIn('redact_exception(e)', src)

    def test_no_http_body_echoes_a_raw_provider_exception(self):
        """core/api_views.py:946 returned str(e) to the CALLER."""
        src = self._source('core/api_views.py')
        self.assertNotIn("'error': str(e),", src)

    def test_scheduler_stage_failure_is_redacted(self):
        src = self._source('core/management/commands/run_scheduler.py')
        self.assertIn('redact_exception(e)', src)
        self.assertNotIn("f'❌ Error running {command_name}: {e}'", src)

    def test_logging_filter_is_registered_globally(self):
        src = self._source('smartbet/settings.py')
        self.assertIn('core.services.redaction.RedactingFilter', src)
        self.assertIn("'filters': ['redact_secrets']", src)


class NoRealTokenInTestEnvironment(SimpleTestCase):
    """The suite itself must not be able to print a production credential.

    If a real token is present while tests run, any provider failure prints it —
    which is exactly how the 2026-08-06 exposure happened. Tests must use fakes.
    """

    #: Shape of a real SportMonks token: long, opaque, alphanumeric.
    MIN_REAL_TOKEN_LEN = 40

    def test_no_production_shaped_token_is_readable(self):
        token = (os.environ.get('SPORTMONKS_API_TOKEN') or '').strip()
        if not token:
            return  # Nothing to leak.

        if token.upper().startswith('FAKE') or token.upper().startswith('TEST'):
            return  # Explicitly a fixture.

        self.assertLess(
            len(token), self.MIN_REAL_TOKEN_LEN,
            'A production-shaped SPORTMONKS_API_TOKEN is readable while the '
            'test suite runs. Any provider failure during tests will print it. '
            'Set a fake token for test runs (see docs/SECRET_ROTATION.md).'
        )

    def test_redaction_covers_the_token_even_if_present(self):
        """Belt and braces: whatever is set, redact() removes it."""
        token = (os.environ.get('SPORTMONKS_API_TOKEN') or '').strip()
        if len(token) < 8:
            return
        out = redact(f'?api_token={token}&x=1')
        self.assertNotIn(token, out)
