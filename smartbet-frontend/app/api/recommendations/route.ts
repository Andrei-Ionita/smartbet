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

import { buildRecommendationPayload } from './engine'
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

export async function GET() {
  try {
    const result = await buildRecommendationPayload()

    if (!result.ok) {
      return NextResponse.json(result.body, {
        status: result.status,
        headers: PUBLIC_CACHE_HEADERS,
      })
    }

    const publicGems = toPublicRecommendationList(result.recommendations)
    // Unvalidated Strategies Lab diagnostics remain on the separately
    // authenticated internal route, never in public recommendation JSON.
    const { market_research: _privateResearch, ...publicEnvelope } = result.envelope

    return NextResponse.json(
      {
        featured_gems: publicGems,
        recommendations: toPublicRecommendationList(result.recommendations),
        ...publicEnvelope,
      },
      { headers: PUBLIC_CACHE_HEADERS },
    )
  } catch (error) {
    // Never echo the error. A provider failure from `fetch` can carry the
    // request URL, and SportMonks authenticates by query parameter, so the
    // message can contain the live token.
    console.error('Error in recommendations API:', error)
    return NextResponse.json({ error: 'Failed' }, { status: 500 })
  }
}
