"""
Internal, staff-only operational endpoints.

Kept in their own module so the boundary is obvious: nothing here is public,
and nothing here may be linked from a public page. Operational detail — run
counts, failure codes, provider diagnostics — tells an attacker how the system
behaves and when it is idle, so it is gated on `is_staff`.

The project sets no DEFAULT_PERMISSION_CLASSES, which means DRF's default of
AllowAny applies to any view that does not say otherwise. Every view in this
module therefore states its permission explicitly.
"""
import hmac
import os

from django.utils import timezone
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.services import gem_feed_cache
from core.services.scheduler_health import get_heartbeat
from core.services.strategy_lab import build_report


def _private_response(body, status=200):
    response = Response(body, status=status)
    response['Cache-Control'] = 'private, no-store, max-age=0, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    response['Vary'] = 'X-Internal-Auth'
    return response


@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def gem_feed_snapshot(request):
    """Return the worker-produced Gem feed to the frontend server only."""
    expected = os.environ.get('INTERNAL_API_SECRET', '')
    provided = request.headers.get('X-Internal-Auth', '')

    if not expected:
        return _private_response(
            {'available': False, 'error': 'not configured'}, status=503,
        )
    if not provided or not hmac.compare_digest(provided, expected):
        return _private_response(
            {'available': False, 'error': 'unauthorized'}, status=401,
        )

    snapshot = gem_feed_cache.latest()
    if snapshot is None:
        return _private_response({'available': False, 'feed': None})

    age_seconds = max(
        0,
        int((timezone.now() - snapshot.generated_at).total_seconds()),
    )
    return _private_response({
        'available': True,
        'generated_at': snapshot.generated_at,
        'refreshed_at': snapshot.refreshed_at,
        'age_seconds': age_seconds,
        'recommendation_count': snapshot.recommendation_count,
        'ranking_version': snapshot.ranking_version,
        'feed': snapshot.payload,
    })


@api_view(['GET'])
# SessionAuthentication as well as JWT so a signed-in staff user can open this
# in a browser straight from /admin, which is how it will actually be used.
@authentication_classes([JWTAuthentication, SessionAuthentication])
@permission_classes([IsAdminUser])
def scheduler_health(request):
    """
    GET /api/internal/scheduler-health/  — staff only.

    Reports whether the background worker is alive. Anonymous and non-staff
    users get 401/403 and learn nothing about scheduler state.
    """
    hb = get_heartbeat()

    return Response({
        'health': hb.health(),
        'status': hb.status,
        'last_run_started_at': hb.last_run_started_at,
        'last_run_completed_at': hb.last_run_completed_at,
        'last_success_at': hb.last_success_at,
        'last_failure_at': hb.last_failure_at,
        'last_duration_seconds': hb.last_duration_seconds,
        'interval_minutes': hb.interval_minutes,
        # Deltas from the most recent completed cycle.
        'snapshots_created': hb.snapshots_created,
        'results_updated': hb.results_updated,
        'claims_settled': hb.claims_settled,
        # Short code only. The traceback lives in the logs against run_id.
        'last_failure_code': hb.last_failure_code,
        'run_id': hb.run_id,
        'version': hb.version,
    })


@api_view(['GET'])
@authentication_classes([JWTAuthentication, SessionAuthentication])
@permission_classes([IsAdminUser])
def strategies_lab(request):
    """Private research report. It is intentionally absent from public URLs/UI."""
    return Response(build_report())
