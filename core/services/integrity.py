"""
Shared canonical hashing, used by BOTH PredictionSnapshot and PublishedClaim.

One implementation, two callers — each supplies its own payload dict and its own
schema version. This exists so the snapshot layer gains tamper detection without
duplicating the claim-hash logic.

Canonical form:
  * deterministic field ordering (sorted JSON keys);
  * UTC microsecond ISO-8601 timestamps;
  * decimals normalised through Decimal, so 1.80 and 1.8 hash identically;
  * explicit schema version inside the payload.
"""
import hashlib
import json
from datetime import timezone as dt_timezone
from decimal import Decimal, InvalidOperation


def norm_dt(value):
    """UTC microsecond ISO-8601, or None."""
    if value is None:
        return None
    if not hasattr(value, 'astimezone'):
        return str(value)
    return value.astimezone(dt_timezone.utc).isoformat(timespec='microseconds')


def norm_num(value):
    """Stable decimal string, so 1.80 and 1.8 serialise identically."""
    if value is None or value == '':
        return None
    try:
        return format(Decimal(str(value)).normalize(), 'f')
    except (InvalidOperation, ValueError):
        return str(value)


def canonical_sha256(payload):
    """SHA-256 over the canonical serialisation of `payload`."""
    blob = json.dumps(
        payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
    )
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()
