/**
 * INTERNAL recommendations feed — server-to-server only, never a browser.
 *
 * WHY IT EXISTS
 * -------------
 * The public route serves an allowlisted DTO with no expected value, no
 * pre-adjustment EV, no value-zone classification and no score components,
 * because none of those are defensible publicly: they derive from a signal
 * score that is a relative ranking rather than a calibrated probability.
 *
 * The scheduler needs exactly those fields. `recommendation_ingest` writes
 * `expected_value` and `raw_expected_value` onto every PredictionLog row, so
 * serving it the public payload would record a null EV against every
 * prediction — silently, with a 200 OK and a well-formed body.
 *
 * So the raw payload lives here, behind the same fail-closed shared secret the
 * evidence feed uses, on a DIFFERENT PATH from the public route. The path
 * separation is the point: one URL returning two bodies depending on a header
 * is a cache-poisoning shape, and `Vary` only helps if every intermediary
 * honours it.
 *
 * SECURITY
 * --------
 *   * Fail closed. INTERNAL_API_SECRET unset -> 503, never "allow everyone".
 *   * Wrong or missing credential -> 401.
 *   * GET only. Everything else -> 405.
 *   * `no-store` so no cache, CDN or Next route cache can retain this body.
 *   * No secret, digest, URL or stack trace in any response.
 *
 * The variable has no NEXT_PUBLIC_ prefix, so Next cannot inline it into a
 * browser bundle.
 */
import { NextRequest, NextResponse } from 'next/server'

import { buildRecommendationPayload } from '@/app/api/recommendations/engine'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

/**
 * Sensitive server-to-server body. `private` alone is not enough — it permits a
 * browser cache; `no-store` forbids writing it anywhere at all.
 */
const NO_STORE_HEADERS = {
  'Cache-Control': 'private, no-store, max-age=0, must-revalidate',
  'Pragma': 'no-cache',
  'Expires': '0',
  // Defence in depth. Path separation is the real protection, but if any hop
  // ever keys on something other than the path, make the credential part of it.
  'Vary': 'X-Internal-Auth',
} as const

const json = (body: unknown, status: number) =>
  NextResponse.json(body, { status, headers: NO_STORE_HEADERS })

/** Fail-closed auth. Returns a response to send, or null when authorised. */
function authorize(request: NextRequest): NextResponse | null {
  const expected = process.env.INTERNAL_API_SECRET || ''
  if (!expected) {
    // 503, not 500: the service is unconfigured, not broken. An unset secret
    // must never be read as "no authentication required".
    return json(
      { success: false, error: 'internal recommendations feed is not configured' },
      503,
    )
  }
  if (request.headers.get('x-internal-auth') !== expected) {
    return json({ success: false, error: 'unauthorized' }, 401)
  }
  return null
}

export async function GET(request: NextRequest) {
  const denied = authorize(request)
  if (denied) return denied

  try {
    const result = await buildRecommendationPayload()

    if (!result.ok) {
      return json(result.body, result.status)
    }

    return json(
      {
        recommendations: result.recommendations,
        confidence_threshold: result.confidenceThreshold,
        ...result.envelope,
      },
      200,
    )
  } catch (error) {
    // Log server-side, return nothing diagnostic. A `fetch` failure message can
    // contain the provider request URL, and SportMonks authenticates by query
    // parameter — so echoing the error would disclose the token to the caller.
    console.error('internal recommendations feed failed:', error)
    return json({ success: false, error: 'internal error' }, 500)
  }
}

/*
 * Explicit method rejection.
 *
 * Without these, Next answers an unmatched method with 405 anyway — but it does
 * so without our cache headers, and a route that only *happens* to reject
 * writes is a weaker statement than one that refuses them by name. This feed is
 * strictly read-only: nothing here may create, update or ingest anything.
 */
const methodNotAllowed = () =>
  json({ success: false, error: 'method not allowed' }, 405)

export const POST = methodNotAllowed
export const PUT = methodNotAllowed
export const PATCH = methodNotAllowed
export const DELETE = methodNotAllowed
