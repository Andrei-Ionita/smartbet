"""Public, privacy-minimal product-event ingestion.

GET is an intentionally side-effect-free readiness probe. It lets monitoring
distinguish "the collector is deployed and traffic is genuinely zero" from
"the route is missing" without writing a fake production event.
"""

import json
import os
import time
import uuid
from urllib.parse import urlsplit

from django.conf import settings
from django.core.cache import cache
from django.core.signing import salted_hmac
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import ProductEvent


MAX_BODY_BYTES = 4096
MAX_EVENTS_PER_SESSION_PER_MINUTE = 60
MAX_EVENTS_GLOBALLY_PER_MINUTE = 10_000
ACTION_ALLOWLIST = {'', 'explore', 'proof', 'record'}


def _clean_surface(value) -> str:
    """Keep a normalized product route, never a URL or query string."""
    text = str(value or '').strip()
    if not text:
        return ''
    if '://' in text:
        text = urlsplit(text).path
    path = text.split('?', 1)[0].split('#', 1)[0]
    if path.startswith('/prediction/'):
        return '/prediction/:slug'
    if path.startswith('/proof/claim/'):
        return '/proof/claim/:id'
    if path.startswith('/proof/preview/'):
        return '/proof/preview/:id/:state'
    if path.startswith('/proof/') and path.count('/') == 2:
        return '/proof/:id'
    return path[:120]


def _allowed_origin_hosts(request):
    hosts = {request.get_host().lower(), 'www.betglitch.com', 'betglitch.com'}
    for value in (
        os.getenv('FRONTEND_URL', ''),
        *os.getenv('CORS_ALLOWED_ORIGINS', '').split(','),
    ):
        parsed = urlsplit(value.strip())
        if parsed.netloc:
            hosts.add(parsed.netloc.lower())
    if settings.DEBUG:
        hosts.update({'localhost:3000', '127.0.0.1:3000'})
    return hosts


def _origin_allowed(request) -> bool:
    origin = request.headers.get('Origin', '').strip()
    if not origin:
        return settings.DEBUG
    parsed = urlsplit(origin)
    return (
        parsed.scheme in {'http', 'https'}
        and parsed.netloc.lower() in _allowed_origin_hosts(request)
    )


def _rate_limited(request, session_hash: str) -> bool:
    """Short-lived abuse control without retaining or trusting an IP address."""
    bucket = int(time.time() // 60)

    for key, limit in (
        (f'product-event:session:{session_hash}:{bucket}', MAX_EVENTS_PER_SESSION_PER_MINUTE),
        (f'product-event:global:{bucket}', MAX_EVENTS_GLOBALLY_PER_MINUTE),
    ):
        if cache.add(key, 1, timeout=75):
            continue
        try:
            if cache.incr(key) > limit:
                return True
        except ValueError:
            cache.set(key, 1, timeout=75)
    return False


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def product_events(request):
    if request.method == 'GET':
        return JsonResponse({
            'status': 'ready',
            'event_ingestion': True,
            'privacy_mode': 'session_scoped_pseudonymous',
        })

    if not _origin_allowed(request):
        return JsonResponse({'success': False, 'error': 'Origin not allowed'}, status=403)
    if len(request.body) > MAX_BODY_BYTES:
        return JsonResponse({'success': False, 'error': 'Payload too large'}, status=413)

    try:
        data = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    if not isinstance(data, dict):
        return JsonResponse({'success': False, 'error': 'JSON object required'}, status=400)

    event_name = str(data.get('event_name') or '').strip()[:50]
    if event_name not in {value for value, _ in ProductEvent.EVENT_CHOICES}:
        return JsonResponse({'success': False, 'error': 'Unsupported event_name'}, status=400)

    try:
        session_id = str(uuid.UUID(str(data.get('session_id', ''))))
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({'success': False, 'error': 'Invalid session_id'}, status=400)
    session_hash = salted_hmac(
        'product-intelligence-session', session_id, algorithm='sha256',
    ).hexdigest()
    if _rate_limited(request, session_hash):
        return JsonResponse({'success': False, 'error': 'Rate limit exceeded'}, status=429)

    duration_bucket = str(data.get('duration_bucket') or '').strip()[:20]
    valid_buckets = {value for value, _ in ProductEvent.DURATION_BUCKET_CHOICES}
    if duration_bucket and duration_bucket not in valid_buckets:
        return JsonResponse({'success': False, 'error': 'Invalid duration_bucket'}, status=400)

    has_results = data.get('has_results')
    if has_results is not None and not isinstance(has_results, bool):
        return JsonResponse({'success': False, 'error': 'has_results must be boolean'}, status=400)

    action = str(data.get('action') or '').strip()[:80]
    if action not in ACTION_ALLOWLIST:
        return JsonResponse({'success': False, 'error': 'Unsupported action'}, status=400)

    event = ProductEvent.objects.create(
        session_hash=session_hash,
        event_name=event_name,
        surface=_clean_surface(data.get('surface')),
        action=action,
        has_results=has_results,
        duration_bucket=duration_bucket,
    )
    return JsonResponse({'success': True, 'event_id': event.pk}, status=201)
