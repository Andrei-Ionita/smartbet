import { NextRequest, NextResponse } from 'next/server'

// This is a dynamic API route that should not be statically generated
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const limit = searchParams.get('limit') || '50'
    const includePending = searchParams.get('include_pending') || 'true'
    const version = searchParams.get('version') || 'v2'

    // Get Django backend URL from environment variable or use default
    const djangoBaseUrl = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : 'https://smartbet-backend-production.up.railway.app')
    const djangoUrl = `${djangoBaseUrl}/api/recommended-predictions/?limit=${limit}&include_pending=${includePending}&version=${version}`

    console.log(`🔍 Fetching recommended predictions from Django: ${djangoUrl}`)

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
      console.log(`✅ Django API returned ${data.count || 0} recommended predictions`)

      // Transform Django response to match frontend expectations
      const transformedData = {
        ...data,
        confidence_threshold: 55, // Default threshold used by Django
        fixtures_analyzed: data.count || 0,
        data: data.data.map((item: any) => {
          // Get the odds for the predicted outcome
          let outcomeOdds = null
          if (item.predicted_outcome === 'Home' || item.predicted_outcome === 'home') {
            outcomeOdds = item.odds_home
          } else if (item.predicted_outcome === 'Draw' || item.predicted_outcome === 'draw') {
            outcomeOdds = item.odds_draw
          } else if (item.predicted_outcome === 'Away' || item.predicted_outcome === 'away') {
            outcomeOdds = item.odds_away
          }

          return {
            ...item,
            // Map Django fields to frontend expected fields
            // Django returns 0-100 percentages, frontend expects 0-100 for display
            confidence: item.confidence,
            ev: item.expected_value,
            odds: outcomeOdds,
            score: item.confidence,
            explanation: item.explanation || 'No explanation available',
            probabilities: item.probabilities ? {
              home: item.probabilities.home,
              draw: item.probabilities.draw,
              away: item.probabilities.away
            } : undefined,
            odds_data: {
              home: item.odds_home,
              draw: item.odds_draw,
              away: item.odds_away,
              bookmaker: item.bookmaker || 'Unknown'
            },
            ensemble_info: {
              model_count: item.model_count || 0,
              consensus: item.consensus || 0,
              variance: item.variance || 0,
              strategy: 'ensemble'
            }
          }
        })
      }

      return NextResponse.json(transformedData)

    } catch (djangoError) {
      console.error('❌ Django backend error:', djangoError)

      // Return error response
      return NextResponse.json(
        {
          success: false,
          error: `Django backend unavailable (Target: ${djangoUrl}): ${djangoError instanceof Error ? djangoError.message : String(djangoError)}`,
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

