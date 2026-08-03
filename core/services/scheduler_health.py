"""
Scheduler liveness recording and the lock that keeps runs from overlapping.

Settlement is entirely scheduler-driven — there is no public route that can
trigger it — so a dead worker is indistinguishable from a healthy one with
nothing to do: claims simply stay PENDING and nothing says why. This module is
the gauge that tells them apart.

It records *that* work happened and how much. It never decides what the work
is, never grades anything and never touches pricing integrity, snapshots,
publication or settlement rules.
"""
import logging
import uuid
from contextlib import contextmanager

from django.db import transaction
from django.utils import timezone

from core.models import (
    PredictionLog,
    PredictionSnapshot,
    PublishedClaimResult,
    SchedulerHeartbeat,
)

logger = logging.getLogger(__name__)


class SchedulerAlreadyRunning(RuntimeError):
    """Raised when a scheduler cycle is started while another still holds the lock."""

# A run still marked "running" after this long is treated as abandoned — the
# worker was killed mid-cycle and never got to write a terminal status. Without
# this a single hard crash would block every later run forever.
STALE_RUNNING_AFTER_MINUTES = 90


def _counts():
    """Table sizes used to derive per-run deltas.

    Deltas rather than parsing command output: the counts stay correct however
    the individual management commands choose to report themselves, and adding
    a task cannot silently break them.
    """
    return {
        'snapshots_created': PredictionSnapshot.objects.count(),
        'results_updated': PredictionLog.objects.filter(actual_outcome__isnull=False).count(),
        'claims_settled': PublishedClaimResult.objects.count(),
    }


def get_heartbeat() -> SchedulerHeartbeat:
    obj, _ = SchedulerHeartbeat.objects.get_or_create(key=SchedulerHeartbeat.SINGLETON_KEY)
    return obj


@contextmanager
def record_run(interval_minutes: int = 60, version: str = ''):
    """
    Wrap one scheduler cycle: take the lock, record start, record outcome.

    Raises `SchedulerAlreadyRunning` if another run holds the lock, so a manual
    invocation cannot interleave with the worker and write contradictory
    results for the same fixtures.

    The exception text is logged against `run_id` and never stored on the
    heartbeat — the heartbeat carries only a short, safe failure code.
    """
    run_id = str(uuid.uuid4())
    now = timezone.now()

    with transaction.atomic():
        # select_for_update makes the claim atomic on Postgres. On SQLite the
        # transaction itself serialises writers, which is enough here.
        hb = (
            SchedulerHeartbeat.objects
            .select_for_update()
            .filter(key=SchedulerHeartbeat.SINGLETON_KEY)
            .first()
        )
        if hb is None:
            hb = SchedulerHeartbeat.objects.create(key=SchedulerHeartbeat.SINGLETON_KEY)
            hb = (
                SchedulerHeartbeat.objects
                .select_for_update()
                .get(pk=hb.pk)
            )

        if hb.status == SchedulerHeartbeat.STATUS_RUNNING and hb.last_run_started_at:
            age_minutes = (now - hb.last_run_started_at).total_seconds() / 60
            if age_minutes < STALE_RUNNING_AFTER_MINUTES:
                raise SchedulerAlreadyRunning(
                    f'a scheduler run started {age_minutes:.0f} minutes ago is still in progress'
                )
            logger.warning(
                'scheduler run_id=%s taking over a run abandoned %.0f minutes ago',
                run_id, age_minutes,
            )

        hb.run_id = run_id
        hb.status = SchedulerHeartbeat.STATUS_RUNNING
        hb.last_run_started_at = now
        hb.interval_minutes = interval_minutes
        hb.version = version or hb.version
        hb.save(update_fields=[
            'run_id', 'status', 'last_run_started_at', 'interval_minutes',
            'version', 'updated_at',
        ])

    before = _counts()
    logger.info('scheduler run_id=%s started', run_id)

    try:
        yield run_id
    except Exception as exc:
        finished = timezone.now()
        # Full detail to the logs, correlated by run_id. Never to the heartbeat.
        logger.exception('scheduler run_id=%s failed', run_id)
        SchedulerHeartbeat.objects.filter(pk=hb.pk).update(
            status=SchedulerHeartbeat.STATUS_FAILED,
            last_run_completed_at=finished,
            last_failure_at=finished,
            last_failure_code=type(exc).__name__[:64],
            last_duration_seconds=(finished - now).total_seconds(),
            updated_at=finished,
        )
        raise
    else:
        finished = timezone.now()
        after = _counts()
        SchedulerHeartbeat.objects.filter(pk=hb.pk).update(
            status=SchedulerHeartbeat.STATUS_SUCCESS,
            last_run_completed_at=finished,
            last_success_at=finished,
            last_failure_code='',
            last_duration_seconds=(finished - now).total_seconds(),
            snapshots_created=max(0, after['snapshots_created'] - before['snapshots_created']),
            results_updated=max(0, after['results_updated'] - before['results_updated']),
            claims_settled=max(0, after['claims_settled'] - before['claims_settled']),
            updated_at=finished,
        )
        logger.info('scheduler run_id=%s completed in %.1fs',
                    run_id, (finished - now).total_seconds())
