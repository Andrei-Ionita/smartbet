"""
HMAC authentication for server-to-server recommendation ingest.

`POST /api/log-recommendations/` writes to PredictionLog AND appends immutable
PredictionSnapshots. Before this module it was `@csrf_exempt` with no
authentication, which meant an anonymous caller could:

* create prediction rows and snapshots;
* **overwrite every field of any existing row** (the view keys on fixture_id
  and setattr()s the whole payload over it);
* craft `odds_provenance` that satisfies `public_universe.status_for`, so an
  injected row classified as ``verified`` and entered the publication queue as
  apparently sound evidence.

Only trusted server-side code may call it. The secret is server-only and must
never reach a browser: no NEXT_PUBLIC_ prefix, no client bundle, no response
body, no log line.

Contract
--------
Headers::

    X-BetGlitch-Timestamp     unix seconds, integer
    X-BetGlitch-Request-ID    unique per logical request; stable across retries
    X-BetGlitch-Signature     hex HMAC-SHA256

Signed input::

    <timestamp>.<request_id>.<sha256(raw_request_body)>

Comparison is constant-time. Failures return one opaque code — never which
header was wrong, which secret matched, or any exception text.
"""
import hashlib
import hmac
import logging
import os
import time

logger = logging.getLogger(__name__)

TIMESTAMP_HEADER = 'HTTP_X_BETGLITCH_TIMESTAMP'
REQUEST_ID_HEADER = 'HTTP_X_BETGLITCH_REQUEST_ID'
SIGNATURE_HEADER = 'HTTP_X_BETGLITCH_SIGNATURE'

# How far a signed request may be from our clock, either direction. Small
# enough that a captured envelope is useless within minutes; large enough to
# tolerate ordinary clock skew between two Railway services.
REPLAY_WINDOW_SECONDS = 300

MAX_REQUEST_ID_LENGTH = 64


class IngestAuthError(Exception):
    """Authentication failed. `reason` is for logs only, never for the client."""

    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _secrets():
    """Configured secrets, current first.

    Two names so a rotation can run without downtime: the backend accepts both
    while the caller signs only with CURRENT. Remove PREVIOUS once the caller
    is confirmed deployed. RECOMMENDATION_INGEST_SECRET is accepted as the
    single-secret form.
    """
    names = (
        'RECOMMENDATION_INGEST_SECRET_CURRENT',
        'RECOMMENDATION_INGEST_SECRET',
        'RECOMMENDATION_INGEST_SECRET_PREVIOUS',
    )
    out = []
    for name in names:
        raw = (os.environ.get(name) or '').strip()
        if raw:
            out.append(raw)
    return out


def is_configured() -> bool:
    return bool(_secrets())


def canonical_input(timestamp: str, request_id: str, raw_body: bytes) -> str:
    body_hash = hashlib.sha256(raw_body or b'').hexdigest()
    return f'{timestamp}.{request_id}.{body_hash}'


def sign(secret: str, timestamp: str, request_id: str, raw_body: bytes) -> str:
    return hmac.new(
        secret.encode('utf-8'),
        canonical_input(timestamp, request_id, raw_body).encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()


def verify(request, *, now=None) -> str:
    """Verify a signed ingest request. Returns the request id, or raises.

    Fails closed: with no secret configured, production rejects ingestion
    rather than falling back to anonymous access.
    """
    secrets = _secrets()
    if not secrets:
        raise IngestAuthError('ingest secret is not configured')

    timestamp = request.META.get(TIMESTAMP_HEADER, '')
    request_id = request.META.get(REQUEST_ID_HEADER, '')
    signature = request.META.get(SIGNATURE_HEADER, '')

    if not timestamp or not request_id or not signature:
        raise IngestAuthError('missing signature headers')

    if len(request_id) > MAX_REQUEST_ID_LENGTH or not request_id.isalnum():
        raise IngestAuthError('malformed request id')

    try:
        sent_at = int(timestamp)
    except (TypeError, ValueError):
        raise IngestAuthError('malformed timestamp')

    current = int(now if now is not None else time.time())
    if abs(current - sent_at) > REPLAY_WINDOW_SECONDS:
        raise IngestAuthError('timestamp outside the replay window')

    raw_body = request.body or b''

    # Constant-time against every accepted secret, and do not short-circuit on
    # the first match — the loop must not leak which secret was in use.
    matched = False
    for secret in secrets:
        expected = sign(secret, timestamp, request_id, raw_body)
        if hmac.compare_digest(expected, signature):
            matched = True

    if not matched:
        raise IngestAuthError('signature mismatch')

    return request_id
