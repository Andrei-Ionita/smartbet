"""
Transparency & Accuracy Tracking Views
Public endpoints showing SmartBet's real performance
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
import logging
import os
from datetime import timedelta

from core.models import PredictionLog, PublishedClaim
from core.services.accuracy_calculator import AccuracyCalculator
from core.services import claim_publication, public_universe

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def calibration_evidence(request):
    """Public probability-quality report from append-only pre-match evidence."""
    from core.services import calibration_evidence as evidence

    report = evidence.build_report()
    report['generated_at'] = timezone.now().isoformat()
    return Response({'success': True, 'data': report})


@api_view(['GET'])
@permission_classes([AllowAny])
def prediction_evidence_archive(request):
    """Paginated public archive behind the calibration report.

    This includes pending and provisional decisions as well as evaluated ones,
    so an unsettled fixture cannot disappear merely because it is inconvenient.
    """
    from core.services import calibration_evidence as evidence

    try:
        page = max(1, int(request.query_params.get('page', 1)))
        page_size = min(100, max(1, int(request.query_params.get('page_size', 25))))
    except (TypeError, ValueError):
        return Response({
            'success': False,
            'error': 'page and page_size must be positive integers',
        }, status=400)

    market = request.query_params.get('market', '').strip()
    state = request.query_params.get('state', '').strip()
    league = request.query_params.get('league', '').strip().casefold()
    if market and market not in evidence.SUPPORTED_MARKETS:
        return Response({'success': False, 'error': 'unsupported market'}, status=400)
    allowed_states = {
        'pending_result', 'awaiting_confirmation', 'unscoreable_result', 'evaluated',
    }
    if state and state not in allowed_states:
        return Response({'success': False, 'error': 'unsupported state'}, status=400)

    decisions, coverage = evidence.collect_decisions()
    if market:
        decisions = [row for row in decisions if row['market'] == market]
    if state:
        decisions = [row for row in decisions if row['state'] == state]
    if league:
        decisions = [row for row in decisions if league in row['league'].casefold()]

    total = len(decisions)
    start = (page - 1) * page_size
    rows = decisions[start:start + page_size]
    return Response({
        'success': True,
        'methodology_version': 'calibration-evidence-v1',
        'evaluation_horizon_hours': evidence.EVALUATION_HORIZON_HOURS,
        'coverage': coverage,
        'filters': {
            'market': market or None,
            'state': state or None,
            'league': request.query_params.get('league') or None,
        },
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total': total,
            'pages': (total + page_size - 1) // page_size,
        },
        'decisions': [evidence.serialize_decision(row) for row in rows],
    })


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def public_accuracy_dashboard(request):
    """
    Public accuracy dashboard - complete transparency.
    
    GET /api/transparency/dashboard/
    
    Returns comprehensive accuracy metrics visible to all users.
    """
    try:
        calculator = AccuracyCalculator()
        stats = calculator.get_comprehensive_stats()
        
        # Add metadata
        stats['last_updated'] = timezone.now().isoformat()
        stats['methodology'] = {
            'what_we_track': 'Eligible settled public commitments only',
            'selection_criteria': 'Automatic publication gate: recommended snapshot, verified fresh price with complete provenance, coherent timestamps, and at least six hours before kickoff',
            'frequency': 'Publication runs automatically; it is not a daily top-N list',
            'data_source': 'Real match results from SportMonks API',
            'verification': "Match outcomes are settled using third-party sports data. BetGlitch does not manually alter a published claim's result to improve the record.",
            'price_audit': 'Prices are recorded with their exact market, line, bookmaker and capture time, creating a complete audit trail for every published quote.',
            'timestamp_proof': 'Every published claim is timestamped before kickoff.',
            'integrity': 'Each published claim is stored as an immutable snapshot and protected by a SHA-256 integrity hash. Corrections are recorded separately rather than rewriting the original claim.',
            'honesty': 'We show both wins and losses - complete transparency',
            'summary': 'Every public commitment is frozen before kickoff and remains visible with its result — win or lose.',
            'pricing_standard': (
                'Verified public record begins %s. Earlier predictions are '
                'preserved and classified as legacy data, but are excluded from '
                'public performance reporting because their original price '
                'snapshots cannot be reconstructed to the current verification '
                'standard.'
            ) % public_universe.PRICING_INTEGRITY_CUTOFF.date().isoformat(),
        }
        stats['transparency_note'] = 'Live signals are not performance. Only eligible settled public commitments count, and losses remain visible.'
        
        return Response({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def accuracy_summary(request):
    """
    Quick accuracy summary for display on homepage.
    
    GET /api/transparency/summary/
    """
    try:
        calculator = AccuracyCalculator()
        overall = calculator.get_overall_accuracy()
        roi = calculator.get_roi_simulation(stake_per_bet=10.0)
        
        # Get recent performance (last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent = [
            c for c in public_universe.resolved_claims()
            if c.kickoff >= seven_days_ago
        ]

        recent_total = len(recent)
        recent_correct = sum(
            1 for c in recent if c.result_status == PublishedClaim.STATUS_WON
        )
        recent_accuracy = (recent_correct / recent_total * 100) if recent_total > 0 else 0
        
        return Response({
            'success': True,
            'summary': {
                'all_time_accuracy': overall['overall']['accuracy_percent'],
                'total_predictions': overall['overall']['total_predictions'],
                'recent_7_days': {
                    'accuracy': round(recent_accuracy, 1),
                    'total': recent_total
                },
                'roi': {
                    'percent': roi['roi_percent'],
                    'total_bets': roi['total_bets'],
                    'profit_loss': roi['total_profit_loss']
                },
                'methodology': {
                    'what_we_track': 'Eligible settled public commitments only',
                    'criteria': 'Verified fresh price, complete provenance, coherent timestamps and publication before kickoff',
                    'frequency': 'Automatic publication under the current policy version',
                    'verification': 'Results fetched from SportMonks API',
                    'transparency': 'Every published claim is timestamped before kickoff.'
                }
            },
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def league_accuracy(request):
    """
    Accuracy breakdown by league.
    
    GET /api/transparency/leagues/
    """
    try:
        calculator = AccuracyCalculator()
        leagues = calculator.get_accuracy_by_league()
        
        return Response({
            'success': True,
            'leagues': leagues,
            'total_leagues': len(leagues)
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def recent_predictions_with_results(request):
    """
    Get recent predictions with their actual outcomes.
    
    GET /api/transparency/recent/
    Query params:
    - limit: Number of predictions (default 50)
    - show_all: Include pending or only completed (default false)
    """
    try:
        limit = request.GET.get('limit', None)
        show_all = request.GET.get('show_all', 'false').lower() == 'true'
        
        queryset = PredictionLog.objects.filter(is_recommended=True)
        
        if not show_all:
            queryset = queryset.filter(actual_outcome__isnull=False)
        
        queryset = queryset.order_by('-kickoff')
        
        if limit is not None:
            predictions = queryset[:int(limit)]
        else:
            predictions = queryset
        
        results = []
        for pred in predictions:
            results.append({
                'fixture_id': pred.fixture_id,
                'home_team': pred.home_team,
                'away_team': pred.away_team,
                'league': pred.league,
                'kickoff': pred.kickoff.isoformat(),
                'predicted_outcome': pred.predicted_outcome,
                'confidence': round(float(pred.confidence) * 100, 1),
                'expected_value': round(float(pred.expected_value or 0) * 100, 1),
                'odds': {
                    'home': pred.odds_home,
                    'draw': pred.odds_draw,
                    'away': pred.odds_away
                },
                'actual_outcome': pred.actual_outcome,
                'actual_score': f"{pred.actual_score_home}-{pred.actual_score_away}" if pred.actual_score_home is not None else None,
                'was_correct': pred.was_correct,
                'profit_loss': float(pred.profit_loss_10) if pred.profit_loss_10 else None,
                'prediction_logged_at': pred.prediction_logged_at.isoformat(),
                'status': pred.match_status or ('Pending' if not pred.actual_outcome else 'Completed'),
                # Read-only. Lets the page label each row honestly: this log
                # contains rows recorded BEFORE the pricing-integrity cutoff,
                # which are excluded from the verified record. Without this the
                # table reads as the record itself.
                'pricing_integrity_status': pred.pricing_integrity_status,
            })
        
        return Response({
            'success': True,
            'predictions': results,
            'count': len(results)
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def quick_stats(request):
    """
    Quick stats for daily monitoring.
    
    GET /api/transparency/quick-stats/
    """
    try:
        completed = PredictionLog.objects.filter(
            actual_outcome__isnull=False,
            is_recommended=True
        )
        
        total = completed.count()
        correct = completed.filter(was_correct=True).count()
        accuracy = (correct / total * 100) if total > 0 else 0
        
        # Last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        recent = completed.filter(kickoff__gte=week_ago)
        recent_total = recent.count()
        recent_correct = recent.filter(was_correct=True).count()
        recent_accuracy = (recent_correct / recent_total * 100) if recent_total > 0 else 0
        
        # Pending
        pending = PredictionLog.objects.filter(
            actual_outcome__isnull=True,
            is_recommended=True
        ).count()
        
        return Response({
            'success': True,
            'all_time': {
                'total': total,
                'correct': correct,
                'accuracy': round(accuracy, 1)
            },
            'last_7_days': {
                'total': recent_total,
                'correct': recent_correct,
                'accuracy': round(recent_accuracy, 1)
            },
            'pending': pending,
            'milestone_progress': {
                'next_milestone': 50 if total < 50 else 100 if total < 100 else 250,
                'current': total,
                'percentage': round((total / (50 if total < 50 else 100 if total < 100 else 250)) * 100, 1)
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=500)


# `trigger_result_update` was removed on 2026-08-03.
#
# It was AllowAny + csrf_exempt and ran
# ResultUpdaterService().update_all_pending_results(max_predictions=50)
# against production for any anonymous caller, returning str(e) on failure.
# Result updating is the scheduler's job — run_scheduler runs update_results
# and then settle_published_claims, in that order. For manual operation use
# `python manage.py update_results --max N`.


# Public message shown when a fixture has no immutable published claim.
UNPUBLISHED_PROOF_MESSAGE = (
    'This prediction has not been published as an immutable BetGlitch claim.'
)


def _record_block():
    roi = AccuracyCalculator().get_roi_simulation(stake_per_bet=10.0)
    return {
        'wins': roi['wins'],
        'losses': roi['losses'],
        'roi_percent': roi['roi_percent'],
        'total_bets': roi['total_bets'],
        # The public record counts only pricing-verified results; it restarts
        # at the pricing-integrity cutoff.
        'verified_record_only': True,
    }


def _serialize_claim_anchor(claim):
    """The external timestamp covering this claim, or None.

    A claim published in the last hour may legitimately have no anchor yet:
    stamping happens on the next scheduler pass. Returning None rather than
    omitting the key keeps "not anchored" a visible state instead of an
    ambiguous absence.
    """
    entry = (
        claim.anchor_entries
        .select_related('anchor')
        .order_by('anchor__created_at')
        .first()
    )
    if entry is None:
        return None

    anchor = entry.anchor
    return {
        'digest': anchor.digest,
        'status': anchor.status,
        'bitcoin_block_height': anchor.bitcoin_block_height,
        'anchored_at': anchor.created_at.isoformat() if anchor.created_at else None,
        'confirmed_at': anchor.confirmed_at.isoformat() if anchor.confirmed_at else None,
        'calendars': anchor.calendars,
        # The hash AS ANCHORED. If this ever differs from claim_hash above,
        # the claim was altered after it was timestamped.
        'claim_hash_at_anchor': entry.claim_hash,
        'matches_current_hash': entry.claim_hash == claim.claim_hash,
        'proof_url': f'/api/proof/anchors/{anchor.digest}/proof/',
        'detail_url': f'/api/proof/anchors/{anchor.digest}/',
    }


def _serialize_claim(claim):
    """Public payload for an immutable claim. Reads ONLY frozen claim fields."""
    prov = claim.odds_provenance or {}
    conf = claim.confidence or 0.0
    confidence_pct = round(conf * 100, 1) if conf <= 1 else round(conf, 1)

    result = {'status': claim.result_status, 'resolved': claim.is_resolved}
    settlement = getattr(claim, 'result', None)
    if settlement is not None:
        result.update({
            'actual_score_home': settlement.actual_score_home,
            'actual_score_away': settlement.actual_score_away,
            'settled_at': settlement.settled_at.isoformat(),
            'result_source': settlement.result_source,
        })
        # Convenience for card rendering, derived from the RECORDED status —
        # never read from the mutable prediction. None for VOID/CANCELLED, which
        # are neither a win nor a loss.
        if claim.is_resolved:
            result['was_correct'] = (
                settlement.status == PublishedClaim.STATUS_WON
            )

    integrity_ok = claim.verify_integrity()
    return {
        'found': True,
        'published': True,
        'state': 'published',
        'claim_id': str(claim.claim_id),
        'claim_hash': claim.claim_hash,
        'claim_hash_version': claim.claim_hash_version,
        # A tampered claim must never render as valid.
        'integrity_ok': integrity_ok,
        'integrity_error': None if integrity_ok else (
            'This claim failed its integrity check and is excluded from our '
            'public record.'
        ),
        'integrity': {
            'algorithm': 'SHA-256',
            'canonicalization': 'UTF-8 JSON with keys sorted and compact separators',
            # Publish the exact input to the digest. A self-hosted green tick is
            # not independent verification if a reader cannot recompute it.
            'canonical_payload': claim.canonical_payload(),
        },
        'pricing_integrity_status': claim.pricing_integrity_status,
        'superseded': claim.is_superseded,
        # External timestamp, or None when not yet anchored. The proof page
        # renders this state directly, so it must be present on THIS payload
        # too — the claims-list serializer having it is not enough.
        'anchor': _serialize_claim_anchor(claim),
        # Versions the public card's Open Graph image URL. Next's own image hash
        # is derived from the module contents, so it does NOT change when
        # settlement changes the data — without this a crawler would keep the
        # PENDING image forever.
        'card_cache_version': claim.card_cache_version,
        'pick': {
            'home_team': claim.home_team,
            'away_team': claim.away_team,
            'league': claim.league,
            'market_type': claim.market_type,
            'predicted_outcome': claim.predicted_outcome,
            'odds': claim.odds,
            # Labelled accurately: a provider-derived model score, NOT a
            # calibrated probability (2026-07-29 audit, finding F3).
            'model_score_percent': confidence_pct,
            # Kept for existing consumers; same value, clearer name above.
            'confidence': confidence_pct,
            'bookmaker': prov.get('odds_bookmaker_name'),
            'odds_market': prov.get('odds_market_description'),
            'odds_line': prov.get('odds_line'),
            'odds_captured_at': (
                claim.odds_captured_at.isoformat() if claim.odds_captured_at else None
            ),
            'price_age_hours_at_publication':
                claim_publication.price_age_hours_at_publication(claim),
            # WHICH ranking policy produced this selection. Published so a
            # record spanning changes to the logic can be split by rule
            # instead of blended into one meaningless average.
            'ranking_version': claim.model_version,
            'kickoff': claim.kickoff.isoformat(),
            'prediction_logged_at': claim.prediction_generated_at.isoformat(),
            'published_at': claim.published_at.isoformat(),
        # How stale the recorded price was when we committed to it. A reader
        # should never have to subtract two timestamps to find that out.
        'price_age_hours_at_publication':
            claim_publication.price_age_hours_at_publication(claim),
            'odds_provenance': prov,
        },
        'result': result,
        'record': _record_block(),
        'note': (
            'Published before kickoff. The result will be shown here after '
            'settlement\u2014win or lose.'
        ),
    }


def proof_card_data(request, fixture_id):
    """
    GET /api/proof/<fixture_id>/ — PUBLIC proof payload.

    Serves the immutable PublishedClaim and NOTHING ELSE. When no claim exists
    the response is an explicit unpublished state.

    It must never fall back to PredictionLog: that row is mutable — the
    pipeline overwrites odds, confidence and the selection on every re-run —
    so serving it publicly would present a changeable value under
    "logged before kickoff" language. Staff previews live at
    /api/proof/<id>/preview/ and are never exposed here.
    """
    claim = (
        PublishedClaim.objects.filter(fixture_id=fixture_id)
        .select_related('prediction')
        .order_by('-published_at')
        .first()
    )

    if claim is None:
        return JsonResponse({
            'found': True,
            'published': False,
            'state': 'unpublished',
            'message': UNPUBLISHED_PROOF_MESSAGE,
            'record': _record_block(),
        }, status=200)

    return JsonResponse(_serialize_claim(claim))


def _serialize_claim_row(claim):
    """One row of the public published-claims list.

    Reads ONLY frozen PublishedClaim fields plus the separate, insert-only
    PublishedClaimResult. It must never reach into PredictionLog: that row is
    rewritten on every pipeline run, so serving any of it here would put a
    mutable value inside a list the product presents as immutable.

    Deliberately narrower than `_serialize_claim`: no staff preview data, no
    correction_reason free text, no raw provenance blob — only what the public
    published-picks section renders.
    """
    prov = claim.odds_provenance or {}
    conf = claim.confidence or 0.0
    settlement = getattr(claim, 'result', None)

    result = None
    if settlement is not None:
        result = {
            'status': settlement.status,
            'settled_at': settlement.settled_at.isoformat(),
            'actual_score_home': settlement.actual_score_home,
            'actual_score_away': settlement.actual_score_away,
            'result_source': settlement.result_source,
        }

    integrity_ok = claim.verify_integrity()
    superseded = claim.is_superseded
    price_age = claim_publication.price_age_hours_at_publication(claim)
    price_fresh = public_universe.claim_has_fresh_price(claim)
    return {
        'claim_id': str(claim.claim_id),
        'fixture_id': claim.fixture_id,
        'home_team': claim.home_team,
        'away_team': claim.away_team,
        'league': claim.league,
        'kickoff': claim.kickoff.isoformat(),
        'market_type': claim.market_type,
        'predicted_outcome': claim.predicted_outcome,
        # A provider-derived model score, NOT a calibrated probability.
        'model_score_percent': round(conf * 100, 1) if conf <= 1 else round(conf, 1),
        'odds': claim.odds,
        'bookmaker': prov.get('odds_bookmaker_name'),
        'odds_captured_at': (
            claim.odds_captured_at.isoformat() if claim.odds_captured_at else None
        ),
        'published_at': claim.published_at.isoformat(),
        'price_age_hours_at_publication': price_age,
        'price_fresh_at_publication': price_fresh,
        'ranking_version': claim.model_version,
        # PENDING until a settlement row exists. Derived from the recorded
        # result, never from the mutable prediction's outcome fields.
        'claim_state': settlement.status if settlement else PublishedClaim.STATUS_PENDING,
        'pricing_integrity_status': claim.pricing_integrity_status,
        'claim_hash': claim.claim_hash,
        'claim_hash_version': claim.claim_hash_version,
        'integrity_ok': integrity_ok,
        'superseded': superseded,
        'supersedes': str(claim.supersedes_id) if claim.supersedes_id else None,
        'is_correction': claim.supersedes_id is not None,
        'proof_url': f'/proof/claim/{claim.claim_id}',
        'result': result,
        # Only a settled row counts towards public performance. Stated per row
        # so a consumer cannot infer it from presence in the list.
        'counts_towards_verified_record': bool(
            settlement
            and settlement.status in (
                PublishedClaim.STATUS_WON, PublishedClaim.STATUS_LOST
            )
            and integrity_ok
            and price_fresh
            and not superseded
        ),
        # External timestamp, if this claim has been anchored. `None` means
        # not anchored — never omitted and never implied, because an absent
        # anchor is exactly the thing a reader must be able to see.
        'anchor': _serialize_claim_anchor(claim),
    }


# A page big enough that the current record fits in one request, small enough
# that a crawler cannot ask for the whole table at once.
CLAIMS_PAGE_DEFAULT = 50
CLAIMS_PAGE_MAX = 200


@api_view(['GET'])
@permission_classes([AllowAny])
def published_claims_list(request):
    """
    GET /api/proof/claims/ — the PUBLIC list of immutable published claims.

    PublishedClaim (+ its separate PublishedClaimResult) is the sole authority.
    There is deliberately no fallback to PredictionLog, PredictionSnapshot, the
    transparency prediction feed or live recommendations: the public
    published-picks surface previously derived itself from the transparency
    feed, which could show predictions that were never published and omit
    claims that were.

    Nothing is filtered out by outcome. Losses, voids, cancellations and
    corrections stay visible — a record that quietly drops its losses is not a
    record. Ordering is deterministic: newest publication first, claim_id
    breaking ties so pagination can never repeat or skip a row.

    Pagination: ?limit= (default 50, max 200) and ?offset=.
    """
    try:
        try:
            limit = int(request.GET.get('limit', CLAIMS_PAGE_DEFAULT))
            offset = int(request.GET.get('offset', 0))
        except (TypeError, ValueError):
            return Response(
                {'success': False, 'error': 'limit and offset must be integers'},
                status=400,
            )
        limit = max(1, min(limit, CLAIMS_PAGE_MAX))
        offset = max(0, offset)

        qs = (
            PublishedClaim.objects
            .select_related('result')
            .order_by('-published_at', 'claim_id')
        )
        total = qs.count()
        rows = [_serialize_claim_row(c) for c in qs[offset:offset + limit]]

        return Response({
            'success': True,
            'count': total,
            'limit': limit,
            'offset': offset,
            'claims': rows,
        })
    except Exception:
        # Controlled failure: a stack trace here would leak model and path
        # detail on a public endpoint.
        logger.exception('published_claims_list failed')
        return Response(
            {'success': False, 'error': 'Published claims are temporarily unavailable.'},
            status=503,
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def proof_by_claim(request, claim_id):
    """
    GET /api/proof/claim/<claim_uuid>/ — the STABLE public proof identity.

    A fixture may eventually carry several claims (different markets), so the
    claim UUID — not the fixture id — is the canonical public identifier.
    Reads exclusively from PublishedClaim.
    """
    claim = (
        PublishedClaim.objects.filter(claim_id=claim_id)
        .select_related('prediction', 'result')
        .first()
    )
    if claim is None:
        return Response({
            'found': False,
            'published': False,
            'state': 'unpublished',
            'message': UNPUBLISHED_PROOF_MESSAGE,
        }, status=404)
    return Response(_serialize_claim(claim))


def _snapshot_list_for(pred):
    """Every snapshot for this fixture, newest first, with publishability."""
    from core.models import PredictionSnapshot

    snaps = list(
        PredictionSnapshot.objects.filter(fixture_id=pred.fixture_id)
        .order_by('-prediction_generated_at')
    )
    if not snaps:
        return []
    newest = snaps[0].prediction_generated_at
    return [_serialize_snapshot(s, newest_generated_at=newest) for s in snaps]


def _serialize_snapshot(snapshot, newest_generated_at=None):
    """Staff-facing view of one immutable snapshot and its publishability."""
    from core.services import claim_publication

    prov = snapshot.odds_provenance or {}
    conf = snapshot.confidence or 0.0
    blockers = claim_publication.check_snapshot_publication_eligibility(snapshot)
    existing = snapshot.published_claims.filter(superseded_by__isnull=True).first()

    return {
        'snapshot_id': str(snapshot.snapshot_id),
        'prediction_run_id': snapshot.prediction_run_id,
        'prediction_generated_at': snapshot.prediction_generated_at.isoformat(),
        'snapshot_created_at': snapshot.snapshot_created_at.isoformat(),
        'market_type': snapshot.market_type,
        'predicted_outcome': snapshot.predicted_outcome,
        'model_score_percent': round(conf * 100, 1) if conf <= 1 else round(conf, 1),
        'odds': snapshot.odds,
        'bookmaker': prov.get('odds_bookmaker_name'),
        'odds_market': prov.get('odds_market_description'),
        'odds_line': prov.get('odds_line'),
        'odds_captured_at': (
            snapshot.odds_captured_at.isoformat() if snapshot.odds_captured_at else None
        ),
        'model_version': snapshot.model_version,
        'kickoff': snapshot.kickoff.isoformat(),
        'pricing_integrity_status': snapshot.pricing_integrity_status,
        'integrity_ok': snapshot.verify_integrity(),
        'is_recommended': snapshot.is_recommended,
        'is_superseded': snapshot.is_superseded,
        'publication_blockers': blockers,
        'publishable': not blockers,
        # So the founder can see they are not looking at the freshest state.
        'is_newest': (
            newest_generated_at is None
            or snapshot.prediction_generated_at >= newest_generated_at
        ),
        'newer_snapshot_exists': (
            newest_generated_at is not None
            and snapshot.prediction_generated_at < newest_generated_at
        ),
        'already_published_claim_id': str(existing.claim_id) if existing else None,
        'publish_endpoint': f'/api/proof/snapshot/{snapshot.snapshot_id}/publish/',
    }


# Ordering bands for the publication queue, by hours to kickoff. This is a
# PRACTICAL SHARING WINDOW, not a ranking: it says nothing about which pick is
# better, only which is most useful to publish now. Ranking on historical ROI is
# deliberately absent — the historical sample is contaminated (2026-07-29 audit)
# and the gem selector is not built.
# A recorded price older than this may no longer be obtainable by the time an
# audience sees the card.
#
# This was "informational only — never a hard filter", which was defensible
# while a human read the warning before publishing. Auto-publication removed
# that human, and on 2026-08-08 it committed prices up to 150 hours old. The
# same threshold is now the hard eligibility gate, and it is DERIVED from it so
# the warning shown to staff can never drift from the rule actually enforced.
STALE_ODDS_WARNING_MINUTES = int(
    claim_publication.MAX_PRICE_AGE_AT_PUBLICATION.total_seconds() / 60
)

PUBLICATION_QUEUE_BANDS = (
    (6, 24, 0, '6-24h — ideal sharing window'),
    (24, 48, 1, '24-48h'),
    (2, 6, 2, '2-6h — close to kickoff'),
    (48, 10 ** 6, 3, 'further out'),
    (0, 2, 4, 'under 2h — very late'),
)


def _queue_band(hours_to_kickoff):
    for low, high, order, label in PUBLICATION_QUEUE_BANDS:
        if low <= hours_to_kickoff < high:
            return order, label
    return 9, 'unknown'


@api_view(['GET'])
@permission_classes([IsAdminUser])
def publication_queue(request):
    """
    GET /api/proof/queue/ — STAFF ONLY.

    Every verified snapshot that is currently publishable, ordered by how useful
    it is to publish NOW.

    This is NOT the gem selector. Nothing here is ranked by historical
    performance and nothing is claimed to be statistically proven — the
    historical sample is contaminated and the selector is not built. Nothing is
    ever published automatically.
    """
    from core.models import PredictionSnapshot
    from core.services import claim_publication

    now = timezone.now()
    candidates = (
        PredictionSnapshot.objects
        .filter(
            pricing_integrity_status=PredictionLog.PRICING_VERIFIED,
            is_audit_excluded=False,
            is_recommended=True,
            kickoff__gt=now,
        )
        .filter(superseded_by__isnull=True)
        .filter(published_claims__isnull=True)      # not already published
        .select_related('prediction')
        .order_by('kickoff')
    )

    # Newest generation time per fixture, so a row can say whether it is stale.
    latest_by_fixture = {}
    for fid, generated in (
        PredictionSnapshot.objects
        .filter(fixture_id__in=[c.fixture_id for c in candidates])
        .values_list('fixture_id', 'prediction_generated_at')
    ):
        if fid not in latest_by_fixture or generated > latest_by_fixture[fid]:
            latest_by_fixture[fid] = generated

    rows = []
    for snap in candidates:
        if not snap.verify_integrity():
            continue
        blockers = claim_publication.check_snapshot_publication_eligibility(
            snap, now=now
        )
        if blockers:
            continue

        hours = (snap.kickoff - now).total_seconds() / 3600.0
        order, band = _queue_band(hours)
        prov = snap.odds_provenance or {}
        conf = snap.confidence or 0.0

        # ── Freshness ─────────────────────────────────────────────────────
        odds_age_minutes = None
        if snap.odds_captured_at:
            odds_age_minutes = round(
                (now - snap.odds_captured_at).total_seconds() / 60.0, 1
            )

        latest = latest_by_fixture.get(snap.fixture_id)
        newer_exists = bool(
            latest and latest > snap.prediction_generated_at
        )

        warnings = []
        if odds_age_minutes is not None and odds_age_minutes > STALE_ODDS_WARNING_MINUTES:
            warnings.append(
                f'recorded price is {round(odds_age_minutes / 60)}h old — it may '
                'no longer be obtainable'
            )
        if newer_exists:
            warnings.append(
                'a newer snapshot exists for this fixture; publishing this one '
                'freezes the older prediction'
            )

        rows.append({
            '_order': order,
            '_hours': hours,
            '_odds_age': odds_age_minutes if odds_age_minutes is not None else 10 ** 9,
            '_generated': snap.prediction_generated_at,
            'odds_age_minutes': odds_age_minutes,
            'newer_snapshot_exists': newer_exists,
            'latest_snapshot_generated_at': latest.isoformat() if latest else None,
            'publication_window': band,
            'warnings': warnings,
            'snapshot_id': str(snap.snapshot_id),
            'fixture_id': snap.fixture_id,
            'fixture': f'{snap.home_team} vs {snap.away_team}',
            'league': snap.league,
            'kickoff': snap.kickoff.isoformat(),
            'hours_to_kickoff': round(hours, 1),
            'window': band,
            'market_type': snap.market_type,
            'predicted_outcome': snap.predicted_outcome,
            'model_score_percent': round(conf * 100, 1) if conf <= 1 else round(conf, 1),
            'odds': snap.odds,
            'bookmaker': prov.get('odds_bookmaker_name'),
            'odds_market': prov.get('odds_market_description'),
            'odds_captured_at': (
                snap.odds_captured_at.isoformat() if snap.odds_captured_at else None
            ),
            'prediction_generated_at': snap.prediction_generated_at.isoformat(),
            'prediction_run_id': snap.prediction_run_id,
            'model_version': snap.model_version,
            'publication_blockers': [],
            'preview_url': f'/api/proof/{snap.fixture_id}/preview/',
            'publish_endpoint': f'/api/proof/snapshot/{snap.snapshot_id}/publish/',
        })

    # Within a band: fresher odds first, then the newer snapshot. This is a
    # practical freshness ordering, NOT a statistical score of any kind.
    rows.sort(key=lambda r: (r['_order'], r['_odds_age'], -r['_generated'].timestamp()))
    for r in rows:
        for key in ('_order', '_hours', '_odds_age', '_generated'):
            r.pop(key)

    return Response({
        'count': len(rows),
        'generated_at': now.isoformat(),
        'note': (
            'Publishable verified snapshots, grouped by sharing window and then '
            'by price freshness. Not a statistical score of any kind — no '
            'historical performance is used, and nothing is published '
            'automatically.'
        ),
        'candidates': rows,
    })


@api_view(['POST'])
@permission_classes([IsAdminUser])
def publish_snapshot_view(request, snapshot_id):
    """
    POST /api/proof/snapshot/<snapshot_uuid>/publish/ — STAFF ONLY.

    The PRIMARY publication route. Freezes one explicitly chosen immutable
    snapshot into a public claim. Publication is never automatic and never
    silently picks "latest".
    """
    from core.services import claim_publication

    try:
        claim = claim_publication.publish_prediction_claim(
            snapshot_id, published_by=request.user
        )
    except claim_publication.PublicationError as exc:
        status_code = 404 if exc.reason == 'snapshot_not_found' else 400
        return Response({
            'success': False, 'reason': exc.reason, 'detail': exc.detail,
        }, status=status_code)

    app_url = os.environ.get('APP_URL', 'https://www.betglitch.com').rstrip('/')
    return Response({
        'success': True,
        'claim_id': str(claim.claim_id),
        'claim_hash': claim.claim_hash,
        'claim_hash_version': claim.claim_hash_version,
        'source_snapshot_id': str(claim.snapshot_id),
        'proof_url': f'{app_url}/proof/claim/{claim.claim_id}',
        'published_at': claim.published_at.isoformat(),
        'frozen': {
            'fixture_id': claim.fixture_id,
            'market_type': claim.market_type,
            'predicted_outcome': claim.predicted_outcome,
            'odds': claim.odds,
            'confidence': claim.confidence,
            'prediction_generated_at': claim.prediction_generated_at.isoformat(),
        },
    }, status=201)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def publish_claim_view(request, prediction_id):
    """
    POST /api/proof/<prediction_id>/publish/ — STAFF ONLY.

    Explicitly freezes a verified prediction into an immutable public claim.
    Publication is never automatic: becoming pricing-verified does not publish
    anything. POST only — a GET can never create a claim.

    Delegates entirely to `claim_publication.publish_prediction_claim`, the one
    authoritative service the future gem selector will also call.
    """
    from core.services import claim_publication

    try:
        # Compatibility: resolves to ONE unambiguous eligible snapshot, and
        # refuses when several candidates exist.
        claim = claim_publication.publish_for_prediction(
            prediction_id, published_by=request.user
        )
    except claim_publication.PublicationError as exc:
        status_code = 404 if exc.reason == 'prediction_not_found' else 400
        return Response({
            'success': False,
            'reason': exc.reason,
            'detail': exc.detail,
        }, status=status_code)

    app_url = os.environ.get('APP_URL', 'https://www.betglitch.com').rstrip('/')
    return Response({
        'success': True,
        'claim_id': str(claim.claim_id),
        'claim_hash': claim.claim_hash,
        'claim_hash_version': claim.claim_hash_version,
        'proof_url': f'{app_url}/proof/claim/{claim.claim_id}',
        'legacy_fixture_url': f'{app_url}/proof/{claim.fixture_id}',
        'source_snapshot_id': str(claim.snapshot_id) if claim.snapshot_id else None,
        'published_at': claim.published_at.isoformat(),
        'frozen': {
            'fixture_id': claim.fixture_id,
            'market_type': claim.market_type,
            'predicted_outcome': claim.predicted_outcome,
            'odds': claim.odds,
            'confidence': claim.confidence,
        },
    }, status=201)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def proof_preview(request, fixture_id):
    """
    GET /api/proof/<fixture_id>/preview/ — STAFF ONLY.

    Renders the CURRENT, MUTABLE prediction so the team can preview a pick
    before it is published. Deliberately separate from the public proof URL,
    and explicitly labelled: none of this is an immutable claim, and it carries
    no "logged before kickoff" guarantee.
    """
    try:
        pred = PredictionLog.objects.get(fixture_id=fixture_id, is_recommended=True)
    except PredictionLog.DoesNotExist:
        return Response({'found': False}, status=404)

    conf = pred.confidence or 0.0
    return Response({
        'found': True,
        'published': False,
        'state': 'staff_preview',
        'warning': (
            'MUTABLE PREVIEW — these values come from the live prediction and '
            'can change on any pipeline re-run. Not an immutable claim.'
        ),
        'pricing_integrity_status': pred.pricing_integrity_status,
        'pick': {
            'home_team': pred.home_team,
            'away_team': pred.away_team,
            'league': pred.league,
            'market_type': pred.market_type,
            'predicted_outcome': pred.predicted_outcome,
            'odds': pred.odds,
            'confidence': round(conf * 100, 1) if conf <= 1 else round(conf, 1),
            'kickoff': pred.kickoff.isoformat(),
            'prediction_logged_at': pred.prediction_logged_at.isoformat(),
            'odds_provenance': pred.odds_provenance,
        },
        'provenance_problems': public_universe.missing_provenance_fields(
            pred.odds_provenance, pred.market_type
        ),
        # Publishability is a property of an immutable SNAPSHOT, never of this
        # mutable row — see the `snapshots` list below.
        # The precise field set that publication would freeze.
        'will_freeze': {
            'fixture_id': pred.fixture_id,
            'home_team': pred.home_team,
            'away_team': pred.away_team,
            'league': pred.league,
            'kickoff': pred.kickoff.isoformat() if pred.kickoff else None,
            'market_type': pred.market_type,
            'predicted_outcome': pred.predicted_outcome,
            'confidence': pred.confidence,
            'odds': pred.odds,
            'bookmaker': (pred.odds_provenance or {}).get('odds_bookmaker_name'),
            'odds_market': (pred.odds_provenance or {}).get('odds_market_description'),
            'odds_line': (pred.odds_provenance or {}).get('odds_line'),
            'odds_captured_at': (pred.odds_provenance or {}).get('odds_captured_at'),
            'prediction_generated_at': pred.prediction_logged_at.isoformat(),
            'prediction_run_id': pred.prediction_run_id,
        },
        'publish_endpoint': f'/api/proof/{pred.pk}/publish/',
        # ── The immutable snapshots available to publish ───────────────────
        # The founder must choose one EXPLICITLY. "Latest" is labelled, never
        # auto-selected.
        'snapshots': _snapshot_list_for(pred),
    })



# ── Independent anchoring ────────────────────────────────────────────────────
# These endpoints exist so that verifying BetGlitch does not require trusting
# BetGlitch. A reader rebuilds the manifest from /api/proof/claims/, recomputes
# the SHA-256, downloads the .ots proof, and checks it with the standard `ots`
# tool against their own Bitcoin node. Nothing here needs our cooperation
# beyond serving bytes we have already committed to.

def _serialize_anchor(anchor, include_manifest=False):
    row = {
        'digest': anchor.digest,
        'manifest_version': anchor.manifest_version,
        'claim_count': anchor.claim_count,
        'calendars': anchor.calendars,
        'status': anchor.status,
        'bitcoin_block_height': anchor.bitcoin_block_height,
        'created_at': anchor.created_at.isoformat() if anchor.created_at else None,
        'confirmed_at': anchor.confirmed_at.isoformat() if anchor.confirmed_at else None,
        'proof_url': f'/api/proof/anchors/{anchor.digest}/proof/',
        'detail_url': f'/api/proof/anchors/{anchor.digest}/',
    }
    if include_manifest:
        row['manifest'] = anchor.manifest
    return row


@api_view(['GET'])
@permission_classes([AllowAny])
def anchors_list(request):
    """GET /api/proof/anchors/ — every external timestamp, newest first."""
    from core.models import ClaimAnchor

    try:
        try:
            limit = int(request.GET.get('limit', 50))
            offset = int(request.GET.get('offset', 0))
        except (TypeError, ValueError):
            return Response(
                {'success': False, 'error': 'limit and offset must be integers'},
                status=400,
            )
        limit = max(1, min(limit, 200))
        offset = max(0, offset)

        qs = ClaimAnchor.objects.order_by('-created_at', 'digest')
        total = qs.count()
        return Response({
            'success': True,
            'count': total,
            'limit': limit,
            'offset': offset,
            'how_to_verify': (
                'Rebuild the manifest from /api/proof/claims/ as '
                '"<claim_id>:<claim_hash>" lines sorted by claim_id, prefixed '
                'by the manifest_version line and newline-terminated. Its '
                'SHA-256 must equal `digest`. Then run: ots verify --digest '
                '<digest> proof.ots'
            ),
            'anchors': [_serialize_anchor(a) for a in qs[offset:offset + limit]],
        })
    except Exception:
        logger.exception('anchors_list failed')
        return Response(
            {'success': False, 'error': 'Anchors are temporarily unavailable.'},
            status=503,
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def anchor_detail(request, digest):
    """GET /api/proof/anchors/<digest>/ — one anchor, with its full manifest."""
    from core.models import ClaimAnchor

    anchor = ClaimAnchor.objects.filter(digest=digest).first()
    if anchor is None:
        return Response({'success': False, 'error': 'Anchor not found'}, status=404)

    payload = _serialize_anchor(anchor, include_manifest=True)
    payload['claims'] = list(
        anchor.entries.values_list('claim__claim_id', flat=True)
    )
    payload['claims'] = [str(c) for c in payload['claims']]
    return Response({'success': True, 'anchor': payload})


@api_view(['GET'])
@permission_classes([AllowAny])
def anchor_proof(request, digest):
    """GET /api/proof/anchors/<digest>/proof/ — the raw .ots proof bytes."""
    from django.http import HttpResponse

    from core.models import ClaimAnchor

    anchor = ClaimAnchor.objects.filter(digest=digest).first()
    if anchor is None or not anchor.ots_proof:
        return Response({'success': False, 'error': 'Proof not found'}, status=404)

    response = HttpResponse(
        bytes(anchor.ots_proof), content_type='application/octet-stream')
    response['Content-Disposition'] = (
        f'attachment; filename="betglitch-{anchor.digest[:16]}.ots"')
    return response
