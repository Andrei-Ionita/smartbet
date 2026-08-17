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
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from core.services.scheduler_health import get_heartbeat
from core.services.strategy_lab import build_report


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
