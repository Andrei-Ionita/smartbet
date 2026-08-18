/**
 * PUBLIC recommendations endpoint.
 *
 * This file contains no authentication branch and no access to the internal
 * payload shape beyond what it deliberately serializes away. The raw internal
 * object — expected value, pre-adjustment EV, value-zone classification, score
 * components — is reachable only through /api/internal/recommendations, which
 * is a different route with its own fail-closed auth.
 *
 * The two used to be ONE route that branched on an `X-Internal-Auth` header.
 * That was correct but fragile in two specific ways:
 *
 *   1. A single misread condition anywhere in a 1000-line handler could serve
 *      internal fields on the public URL. Now a leak would require editing this
 *      file to call the wrong serializer — a visible change, not a subtle one.
 *
 *   2. One URL returning two different bodies is a cache-poisoning shape. Any
 *      intermediary keying on path alone could store the internal response and
 *      replay it to the public. `Vary: X-Internal-Auth` would nominally fix
 *      that, but it relies on every hop honouring it. Separate paths do not.
 */
import { NextResponse } from 'next/server'

import { loadCachedGemFeed } from '@/app/lib/gemFeedSnapshot'
import {
  MODEL_SHORTLIST_POLICY,
  toPublicModelShortlist,
} from '@/app/lib/modelShortlist'
import { toPublicRecommendationList } from '@/app/lib/publicRecommendation'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

/**
 * Signals move as prices move, so a stale response is a wrong response — but
 * this body is public and identical for every caller, so a short shared cache
 * is safe and useful. Stated explicitly rather than left to Next's defaults,
 * so the contrast with the internal route's `no-store` is visible rather than
 * inferred.
 */
const PUBLIC_CACHE_HEADERS = {
  // The signal set only meaningfully changes when a scheduler run lands
  // (hourly), so a 5-minute shared cache serves virtually every visitor from
  // the edge instead of paying the ~40s engine computation. SWR keeps a
  // stale-but-instant response flowing while the edge revalidates.
  'Cache-Control': 'public, max-age=0, s-maxage=300, stale-while-revalidate=600',
} as const

const MAX_FEED_AGE_SECONDS = 3 * 60 * 60

const numberOrZero = (value: unknown) =>
  Number.isFinite(Number(value)) ? Number(value) : 0

const kickoffIsFuture = (value: unknown, now = Date.now()) => {
  if (typeof value !== 'string') return false
  const normalized = value.includes('T') ? value : `${value.replace(' ', 'T')}Z`
  const kickoff = Date.parse(normalized)
  return Number.isFinite(kickoff) && kickoff > now
}

function publicBody(snapshot: Awaited<ReturnType<typeof loadCachedGemFeed>>) {
  const feed = snapshot.feed || {}
  const ageSeconds = numberOrZero(snapshot.age_seconds)
  const stale = !snapshot.available || !snapshot.feed || ageSeconds > MAX_FEED_AGE_SECONDS
  const rawRecommendations = Array.isArray(feed.recommendations)
    ? feed.recommendations
    : []
  const currentRecommendations = stale
    ? []
    : rawRecommendations.filter((rec: Record<string, any>) => kickoffIsFuture(rec.kickoff))
  const publicGems = toPublicRecommendationList(currentRecommendations)
  const rawShortlist = Array.isArray(feed.model_shortlist)
    ? feed.model_shortlist
    : []
  const shortlistGenerated = feed.model_shortlist_generated === true ||
    Array.isArray(feed.model_shortlist)
  const shortlistStatus = stale
    ? 'delayed'
    : shortlistGenerated ? 'ready' : 'pending_refresh'
  const currentShortlist = stale
    ? []
    : rawShortlist.filter((item: Record<string, any>) => kickoffIsFuture(item.kickoff))
  const publicShortlist = toPublicModelShortlist(currentShortlist)
  const rawScan = feed.gem_scan && typeof feed.gem_scan === 'object'
    ? feed.gem_scan as Record<string, unknown>
    : {}

  return {
    featured_gems: publicGems,
    recommendations: toPublicRecommendationList(currentRecommendations),
    model_shortlist: publicShortlist,
    model_shortlist_limit: MODEL_SHORTLIST_POLICY.maximumSelections,
    model_shortlist_status: shortlistStatus,
    model_shortlist_message: shortlistStatus === 'ready'
      ? (publicShortlist.length
          ? 'The current scan produced a model shortlist.'
          : 'The current scan completed and no fixture qualified for the model shortlist.')
      : shortlistStatus === 'delayed'
        ? 'The model shortlist is hidden until a fresh scan completes.'
        : 'This snapshot predates the model shortlist; the first compatible scan is pending.',
    total: publicGems.length,
    leagues_covered: numberOrZero(feed.leagues_covered),
    fixtures_analyzed: numberOrZero(feed.fixtures_analyzed),
    fixtures_with_predictions: numberOrZero(feed.fixtures_with_predictions),
    gem_scan: {
      fixtures_scanned: numberOrZero(rawScan.fixtures_scanned),
      fixtures_with_predictions: numberOrZero(rawScan.fixtures_with_predictions),
      qualified_fixtures: numberOrZero(rawScan.qualified_fixtures),
      displayed_gems: publicGems.length,
      maximum_gems: numberOrZero(rawScan.maximum_gems),
      status: !snapshot.available || !snapshot.feed
        ? 'warming'
        : stale ? 'delayed' : 'current',
    },
    lastUpdated: typeof feed.lastUpdated === 'string' ? feed.lastUpdated : null,
    ranking_version: typeof feed.ranking_version === 'string'
      ? feed.ranking_version
      : null,
    feed_status: {
      source: 'hourly_snapshot',
      age_seconds: ageSeconds,
      stale,
      snapshot_refreshed_at: typeof snapshot.refreshed_at === 'string'
        ? snapshot.refreshed_at
        : null,
      schema_version: typeof feed.feed_schema_version === 'string'
        ? feed.feed_schema_version
        : null,
    },
    message: !snapshot.available || !snapshot.feed
      ? 'The first Gem scan is warming up.'
      : stale
        ? 'The latest Gem scan is delayed; no stale fixtures are displayed.'
        : 'Success',
  }
}

export async function GET() {
  try {
    const snapshot = await loadCachedGemFeed()
    return NextResponse.json(publicBody(snapshot), { headers: PUBLIC_CACHE_HEADERS })
  } catch (error) {
    // Never echo the error. A provider failure from `fetch` can carry the
    // request URL, and SportMonks authenticates by query parameter, so the
    // message can contain the live token.
    console.error('Error reading Gem feed snapshot:', error)
    return NextResponse.json(
      {
        ...publicBody({ available: false, feed: null, age_seconds: 0 }),
        message: 'The Gem feed is temporarily unavailable.',
      },
      { status: 503, headers: { 'Cache-Control': 'no-store' } },
    )
  }
}
