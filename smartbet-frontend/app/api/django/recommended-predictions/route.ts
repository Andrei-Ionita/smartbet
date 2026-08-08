import { NextRequest, NextResponse } from 'next/server'

// This is a dynamic API route that should not be statically generated
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

/**
 * Public payload for /monitoring — an ALLOWLIST, same principle as
 * app/lib/publicRecommendation.ts.
 *
 * This proxy used to pass the raw Django row through and even attached an
 * `odds` field by string-matching the predicted outcome against the 1X2
 * board — the exact wrong-market defect class behind the 2026-07-29 pricing
 * incident. A public reviewer (2026-08-08) then found Over 2.5 rows quoting
 * 11.00 and per-row P/L that contradicted the verified record's own "legacy
 * prices cannot support price-dependent performance" rule.
 *
 * The monitoring page is OPERATIONAL coverage over the full internal
 * universe, legacy included. Correctness against final scores is a fact that
 * survives unverified pricing; money and prices are not. So the payload
 * carries grading facts and counts — never odds, P/L, ROI, EV or bookmaker.
 */
const toMonitoringRow = (item: any) => ({
  fixture_id: item.fixture_id,
  home_team: item.home_team,
  away_team: item.away_team,
  league: item.league,
  kickoff: item.kickoff,
  predicted_outcome: item.predicted_outcome,
  predicted_outcome_raw: item.predicted_outcome_raw,
  confidence: item.confidence,
  actual_outcome: item.actual_outcome,
  actual_outcome_raw: item.actual_outcome_raw,
  actual_score_home: item.actual_score_home,
  actual_score_away: item.actual_score_away,
  match_status: item.match_status,
  was_correct: item.was_correct,
  prediction_logged_at: item.prediction_logged_at,
  result_logged_at: item.result_logged_at,
  is_completed: item.is_completed,
})

const toMonitoringSummary = (summary: any) => {
  if (!summary) return null
  const total = summary.total_recommended ?? 0
  const completed = summary.completed ?? 0
  const pending = summary.pending ?? 0
  return {
    total_recommended: total,
    completed,
    pending,
    // The rows that reconcile 317 = 296 + 13 + 8.
    //
    // These 8 are NOT ungraded. Django's `completed` counts rows that are
    // graded AND not audit-excluded, so the gap is exactly the quarantined
    // set: rows graded against a final score but held out of the audit
    // universe. Labelling them "postponed, abandoned or ungraded" — as this
    // first attempted — was itself wrong, and a reviewer caught the table
    // showing 178 + 126 = 304 graded rows against a summary claiming 296.
    audit_excluded: Math.max(0, total - completed - pending),
    // Graded rows including the quarantined ones, so the table and the
    // headline can be read against each other without arithmetic.
    graded: Math.max(0, total - pending),
  }
}

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const includePending = searchParams.get('include_pending') || 'true'

    // Get Django backend URL from environment variable or use default
    const djangoBaseUrl = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : 'https://smartbet-backend-production.up.railway.app')
    // Explicitly pass a large limit to ensure we get ALL records (overrides backend default)
    const djangoUrl = `${djangoBaseUrl}/api/recommended-predictions/?limit=1000&include_pending=${includePending}`

    try {
      const response = await fetch(djangoUrl, {
        headers: {
          'Content-Type': 'application/json',
        },
        cache: 'no-store', // Always fetch fresh data
      })

      if (!response.ok) {
        let errorMessage = `Django API error: ${response.status} ${response.statusText}`
        try {
          const errorData = await response.json()
          if (errorData.error) {
            errorMessage = `${errorMessage} - Details: ${errorData.error}`
          }
        } catch (e) {
          // Ignore json parsing error if response is not json
        }
        throw new Error(errorMessage)
      }

      const data = await response.json()

      return NextResponse.json({
        success: data.success !== false,
        count: data.count || 0,
        data: Array.isArray(data.data) ? data.data.map(toMonitoringRow) : [],
        summary: toMonitoringSummary(data.summary),
      })

    } catch (djangoError) {
      console.error('❌ Django backend error:', djangoError)

      // Return error response
      return NextResponse.json(
        {
          success: false,
          error: `Django backend unavailable: ${djangoError instanceof Error ? djangoError.message : String(djangoError)}`,
          data: [],
          summary: null,
          count: 0,
        },
        { status: 503 }
      )
    }

  } catch (error) {
    console.error('❌ Error in recommended-predictions API:', error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch recommended predictions',
        data: [],
        summary: null,
        count: 0,
      },
      { status: 500 }
    )
  }
}
