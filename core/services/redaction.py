"""
Scrub secrets out of anything on its way to a human.

WHY THIS EXISTS
---------------
On 2026-08-06 a backend test run printed this to stdout:

    SportMonks API error: HTTPSConnectionPool(host='api.sportmonks.com', ...
    url: /v3/football/fixtures/between/...?api_token=<REAL TOKEN>&include=...

Nobody wrote a line that printed the token. `requests` puts the FULLY RESOLVED
request URL into its exception message, and SportMonks authenticates with the
token as a query parameter, so `str(exc)` contains the credential. Every
`print(f"...{e}")` around a provider call is therefore a credential disclosure
waiting for the provider to go down — and it disclosed to CI logs, to anyone
reading terminal output over a shoulder, and (at core/api_views.py:946) into an
HTTP response body.

The lesson is that the leak was not in the printing code. It was in the shape of
the URL, which means fixing one print statement fixes nothing. Redact at every
boundary where text reaches a human instead.

WHAT IS SCRUBBED
----------------
1. The live VALUES of known secret environment variables, wherever they appear
   and however they got there. This catches a token embedded in a URL, a repr,
   a traceback, or a dict dump.
2. Credential-shaped query parameters (`api_token=`, `token=`, `api_key=`,
   `key=`, `secret=`, `password=`, `signature=`), even when the value is not one
   we know — a token from a provider we have not registered here still goes.
3. Authorization headers and bearer tokens.

Rule 1 is exact-match and cannot over-redact. Rules 2 and 3 are structural and
deliberately aggressive: over-redacting a URL in a log line costs nothing,
under-redacting one costs a credential.
"""
import logging
import os
import re

REDACTED = '[REDACTED]'

#: Environment variables whose VALUES must never be emitted.
SECRET_ENV_VARS = (
    'SPORTMONKS_API_TOKEN',
    'SPORTMONKS_TOKEN',
    'INTERNAL_API_SECRET',
    'RECOMMENDATION_INGEST_SECRET',
    'MARKETING_WEBHOOK_SECRET',
    'POLAR_ACCESS_TOKEN',
    'POLAR_WEBHOOK_SECRET',
    'DJANGO_SECRET_KEY',
    'SECRET_KEY',
    'DATABASE_URL',
)

#: Query parameters that carry a credential.
_CREDENTIAL_PARAMS = (
    'api_token', 'apitoken', 'token', 'api_key', 'apikey', 'key',
    'secret', 'password', 'passwd', 'pwd', 'signature', 'sig',
    'access_token', 'auth',
)

_PARAM_RE = re.compile(
    r'(?i)\b(' + '|'.join(_CREDENTIAL_PARAMS) + r')=([^&\s\'"<>\\\]}),;]+)'
)

# The VALUE group deliberately eats to the closing quote or end of line rather
# than stopping at the first space. `Authorization: Bearer <token>` has the
# credential AFTER a word, so a space-terminated match redacts "Bearer" and
# leaves the token — which is how this rule failed its own test first time.
_HEADER_RE = re.compile(
    r'(?i)(authorization|x-internal-auth|x-signature|x-api-key)'
    r'(["\']?\s*[:=]\s*["\']?)([^\r\n\'"]+)'
)

_BEARER_RE = re.compile(r'(?i)\b(bearer|token)\s+([A-Za-z0-9._\-]{8,})')

#: Below this length a "secret" is probably a placeholder like "x" or "test",
#: and blanket-replacing it would mangle unrelated text.
_MIN_SECRET_LEN = 8


def _live_secret_values():
    """Current values of the secret env vars, longest first.

    Longest first matters: if two secrets share a prefix, replacing the shorter
    one first would leave the remainder of the longer one exposed.
    """
    values = []
    for name in SECRET_ENV_VARS:
        value = (os.environ.get(name) or '').strip()
        if len(value) >= _MIN_SECRET_LEN:
            values.append(value)
    return sorted(set(values), key=len, reverse=True)


def redact(value):
    """Return `value` as a string with every known credential removed.

    Safe to call on anything — exceptions, URLs, dicts, None. Never raises: a
    redaction helper that can throw would turn a logging path into an outage.
    """
    try:
        text = value if isinstance(value, str) else str(value)
    except Exception:  # pragma: no cover - str() on a hostile __str__
        return REDACTED

    for secret in _live_secret_values():
        if secret in text:
            text = text.replace(secret, REDACTED)

    text = _PARAM_RE.sub(lambda m: f'{m.group(1)}={REDACTED}', text)
    text = _HEADER_RE.sub(lambda m: f'{m.group(1)}{m.group(2)}{REDACTED}', text)
    text = _BEARER_RE.sub(lambda m: f'{m.group(1)} {REDACTED}', text)
    return text


def redact_exception(exc):
    """Render an exception for humans without its credentials.

    Use this instead of `str(exc)` anywhere near a provider call. Keeps the
    exception CLASS, which is the part that actually aids diagnosis — a
    ConnectionError and a 401 need different responses, and neither needs the
    token to be legible.
    """
    return f'{type(exc).__name__}: {redact(exc)}'


class RedactingFilter:
    """Logging filter that scrubs every record before it is emitted.

    Defence in depth. Call sites should use `redact()` deliberately; this
    catches the ones that forget, including third-party libraries logging their
    own request URLs.
    """

    def filter(self, record):  # noqa: A003 - logging API
        try:
            if isinstance(record.msg, str):
                record.msg = redact(record.msg)
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: redact(v) for k, v in record.args.items()}
                else:
                    record.args = tuple(redact(a) for a in record.args)
            # `logger.exception()` is the dangerous case, and it needs care:
            # a filter runs BEFORE any formatter, so `exc_text` is still None
            # here and the traceback has not been rendered yet. Redacting only
            # `exc_text` therefore scrubbed nothing at all — the formatter went
            # on to render `exc_info` afterwards, token and all.
            #
            # So render it ourselves, redact that, and cache it in `exc_text`.
            # logging.Formatter uses a populated `exc_text` verbatim and skips
            # re-rendering, so our scrubbed copy is what gets emitted.
            if getattr(record, 'exc_text', None):
                record.exc_text = redact(record.exc_text)
            elif record.exc_info:
                record.exc_text = redact(
                    logging.Formatter().formatException(record.exc_info))
        except Exception:  # pragma: no cover - never break logging
            pass
        return True
