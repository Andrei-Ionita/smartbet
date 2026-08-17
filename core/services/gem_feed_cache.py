"""Persistence boundary for the latest successful Gem scan."""

from datetime import timezone as dt_timezone

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from core.models import GemFeedCache


class InvalidGemFeed(ValueError):
    pass


def _generated_at(payload, *, now):
    value = payload.get('lastUpdated')
    parsed = parse_datetime(value) if isinstance(value, str) else None
    if parsed is None:
        return now
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, dt_timezone.utc)
    return parsed


def validate_payload(payload):
    if not isinstance(payload, dict):
        raise InvalidGemFeed('Gem feed must be an object')
    recommendations = payload.get('recommendations')
    if not isinstance(recommendations, list):
        raise InvalidGemFeed('Gem feed recommendations must be a list')
    gem_scan = payload.get('gem_scan')
    if gem_scan is not None and not isinstance(gem_scan, dict):
        raise InvalidGemFeed('Gem feed scan summary must be an object')
    return recommendations


@transaction.atomic
def store(payload, *, now=None):
    """Atomically replace the singleton after a successful complete scan."""
    now = now or timezone.now()
    recommendations = validate_payload(payload)
    cache, _ = GemFeedCache.objects.update_or_create(
        key=GemFeedCache.CACHE_KEY,
        defaults={
            'payload': payload,
            'generated_at': _generated_at(payload, now=now),
            'ranking_version': payload.get('ranking_version'),
            'recommendation_count': len(recommendations),
        },
    )
    return cache


def latest():
    return GemFeedCache.objects.filter(key=GemFeedCache.CACHE_KEY).first()
