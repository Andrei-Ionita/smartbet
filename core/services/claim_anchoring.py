"""
Independent, externally timestamped anchoring of published claims.

WHY THIS EXISTS
---------------
A skeptical public reviewer (2026-08-08) made a correct and uncomfortable
point: a SHA-256 hash that BetGlitch computes, over content BetGlitch serves,
from a database BetGlitch controls, proves tamper-EVIDENCE and nothing more.
Nothing in it stops us replacing a claim and recomputing its hash. For a
product whose whole pitch is "you should not have to trust us", that gap was
the single biggest credibility hole.

This module closes it by handing the timestamp to someone who is not us.

    manifest text  ->  SHA-256 digest  ->  OpenTimestamps calendars  ->  Bitcoin

OpenTimestamps is used because it needs no account, no API key and no
commercial relationship: the digest is submitted to independent public
calendar servers, which aggregate it into a Bitcoin transaction. Once the
attestation upgrades, the proof says "this exact digest existed before block
N" — a fact anchored in a public chain that BetGlitch cannot rewrite, verified
with the standard `ots` tool against anyone's Bitcoin node.

TIMING IS THE WHOLE POINT
-------------------------
Anchoring must happen AT PUBLICATION, never on a nightly sweep. A digest
stamped the morning after proves only that the record existed after the match
finished, which is worth nothing. The scheduler therefore anchors immediately
after auto-publication, while every claim in the batch is still hours from
kickoff.

WHAT A THIRD PARTY CAN CHECK
----------------------------
The manifest is derived ONLY from fields the public claims API already serves
(claim_id + claim_hash), in a documented canonical form. Anyone can rebuild it
from /api/proof/claims/, recompute the digest, and confirm it matches the
digest inside the timestamp proof. No BetGlitch-private input is involved.
"""
import hashlib
import logging
import os

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# Public OpenTimestamps calendars. Several, deliberately: a single calendar is
# a single point of trust and of failure, and the proof is stronger when
# independent operators attest to the same digest.
DEFAULT_CALENDARS = (
    'https://a.pool.opentimestamps.org',
    'https://b.pool.opentimestamps.org',
    'https://alice.btc.calendar.opentimestamps.org',
)

CALENDAR_TIMEOUT = 20

MANIFEST_VERSION = 'betglitch-claim-anchor-v1'


class AnchoringUnavailable(Exception):
    """Anchoring could not be performed. Never fatal to publication."""


def build_manifest(pairs):
    """The canonical text a digest is taken over.

    `pairs` is an iterable of (claim_id, claim_hash). Format, frozen as v1:

        betglitch-claim-anchor-v1
        <claim_id>:<claim_hash>
        <claim_id>:<claim_hash>
        ...

    Sorted by claim_id, newline-separated, trailing newline, UTF-8. Sorting is
    what makes the digest independent of insertion order, so a third party
    rebuilding it from the public API gets byte-identical text.
    """
    lines = sorted(f'{claim_id}:{claim_hash}' for claim_id, claim_hash in pairs)
    return MANIFEST_VERSION + '\n' + '\n'.join(lines) + '\n'


def compute_digest(manifest):
    """SHA-256 of the manifest text, as hex."""
    return hashlib.sha256(manifest.encode('utf-8')).hexdigest()


def _calendars():
    configured = os.environ.get('OTS_CALENDARS', '').strip()
    if configured:
        return tuple(u.strip() for u in configured.split(',') if u.strip())
    return DEFAULT_CALENDARS


def stamp_digest(digest_hex, calendars=None, timeout=CALENDAR_TIMEOUT):
    """Submit a digest to the OpenTimestamps calendars.

    Returns (ots_proof_bytes, accepted_calendar_urls). Raises
    AnchoringUnavailable when no calendar accepted, so the caller records a
    failed attempt rather than a proof that does not exist.

    The digest is nonced before it leaves this process — standard OTS practice,
    so a calendar operator learns nothing about what was stamped.
    """
    try:
        from opentimestamps.calendar import RemoteCalendar
        from opentimestamps.core.op import OpAppend, OpSHA256
        from opentimestamps.core.serialize import BytesSerializationContext
        from opentimestamps.core.timestamp import (DetachedTimestampFile,
                                                   Timestamp)
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise AnchoringUnavailable(f'opentimestamps not installed: {exc}')

    digest = bytes.fromhex(digest_hex)
    if len(digest) != 32:
        raise AnchoringUnavailable('digest must be 32 bytes of SHA-256')

    timestamp = Timestamp(digest)
    nonced = timestamp.ops.add(OpAppend(os.urandom(16)))
    leaf = nonced.ops.add(OpSHA256())

    accepted = []
    for url in (calendars or _calendars()):
        try:
            result = RemoteCalendar(url).submit(leaf.msg, timeout=timeout)
            leaf.merge(result)
            accepted.append(url)
        except Exception as exc:
            # One unreachable calendar is normal; log and keep going.
            logger.warning('OTS calendar %s rejected the digest: %s', url, exc)

    if not accepted:
        raise AnchoringUnavailable('no OpenTimestamps calendar accepted the digest')

    detached = DetachedTimestampFile(OpSHA256(), timestamp)
    ctx = BytesSerializationContext()
    detached.serialize(ctx)
    return ctx.getbytes(), accepted


def unanchored_claims():
    """Published claims with no anchor entry yet, oldest first.

    Superseded claims are still anchored: the point of the record is that
    nothing disappears, and a correction's own claim is anchored in its turn.
    """
    from core.models import PublishedClaim

    return (
        PublishedClaim.objects
        .filter(anchor_entries__isnull=True)
        .order_by('published_at', 'claim_id')
    )


@transaction.atomic
def anchor_pending_claims(now=None, calendars=None, limit=500):
    """Stamp every not-yet-anchored claim in ONE batch digest.

    Returns the created ClaimAnchor, or None when there is nothing to anchor.
    Idempotent by construction: a claim already carrying an anchor entry is
    never restamped.
    """
    from core.models import ClaimAnchor, ClaimAnchorEntry

    now = now or timezone.now()
    claims = list(unanchored_claims()[:limit])
    if not claims:
        return None

    manifest = build_manifest((str(c.claim_id), c.claim_hash) for c in claims)
    digest = compute_digest(manifest)

    existing = ClaimAnchor.objects.filter(digest=digest).first()
    if existing is not None:
        # Same set of claims already stamped (a retried run). Link and stop.
        for claim in claims:
            ClaimAnchorEntry.objects.get_or_create(
                anchor=existing, claim=claim,
                defaults={'claim_hash': claim.claim_hash},
            )
        return existing

    proof, accepted = stamp_digest(digest, calendars=calendars)

    anchor = ClaimAnchor.objects.create(
        digest=digest,
        manifest=manifest,
        manifest_version=MANIFEST_VERSION,
        claim_count=len(claims),
        calendars=list(accepted),
        ots_proof=proof,
        status=ClaimAnchor.STATUS_PENDING,
        created_at=now,
    )
    for claim in claims:
        ClaimAnchorEntry.objects.create(
            anchor=anchor, claim=claim, claim_hash=claim.claim_hash,
        )

    logger.info('Anchored %s claims as digest %s via %s',
                len(claims), digest, ', '.join(accepted))
    return anchor


def upgrade_anchor(anchor, timeout=CALENDAR_TIMEOUT):
    """Try to replace pending calendar attestations with Bitcoin ones.

    Calendars aggregate submissions and only commit to Bitcoin periodically, so
    a fresh anchor stays PENDING for a few hours. Returns True when the proof
    gained a Bitcoin attestation.
    """
    from core.models import ClaimAnchor

    try:
        from opentimestamps.core.notary import (BitcoinBlockHeaderAttestation,
                                                PendingAttestation)
        from opentimestamps.core.serialize import (BytesDeserializationContext,
                                                   BytesSerializationContext)
        from opentimestamps.core.timestamp import DetachedTimestampFile
        from opentimestamps.calendar import RemoteCalendar
    except ImportError as exc:  # pragma: no cover
        raise AnchoringUnavailable(f'opentimestamps not installed: {exc}')

    if not anchor.ots_proof:
        return False

    ctx = BytesDeserializationContext(bytes(anchor.ots_proof))
    detached = DetachedTimestampFile.deserialize(ctx)

    def walk(ts):
        yield ts
        for sub in ts.ops.values():
            yield from walk(sub)

    changed = False
    for sub in list(walk(detached.timestamp)):
        for att in list(sub.attestations):
            if not isinstance(att, PendingAttestation):
                continue
            url = att.uri.decode() if isinstance(att.uri, bytes) else att.uri
            try:
                upgraded = RemoteCalendar(url).get_timestamp(sub.msg, timeout=timeout)
            except Exception as exc:
                logger.info('anchor %s not upgradable at %s yet: %s',
                            anchor.digest, url, exc)
                continue
            sub.merge(upgraded)
            changed = True

    height = None
    for sub in walk(detached.timestamp):
        for att in sub.attestations:
            if isinstance(att, BitcoinBlockHeaderAttestation):
                height = min(height, att.height) if height else att.height

    if changed:
        out = BytesSerializationContext()
        detached.serialize(out)
        anchor.ots_proof = out.getbytes()

    if height is not None:
        anchor.status = ClaimAnchor.STATUS_CONFIRMED
        anchor.bitcoin_block_height = height
        anchor.confirmed_at = timezone.now()

    if changed or height is not None:
        anchor.save(update_fields=[
            'ots_proof', 'status', 'bitcoin_block_height', 'confirmed_at',
        ])

    return height is not None
