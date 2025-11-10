import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const session_id = searchParams.get('session_id') || ''
    const league = searchParams.get('league') || ''
    const limit = searchParams.get('limit') || '10'
    
    // Get Django backend URL from environment variable or use default
    const djangoBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    
    // Build Django URL with query params
    const params = new URLSearchParams()
    if (session_id) params.append('session_id', session_id)
    if (league) params.append('league', league)
    params.append('limit', limit)
    
    const djangoUrl = `${djangoBaseUrl}/api/recommendations/?${params.toString()}`
    
    console.log(`🔍 Fetching FUTURE recommendations from Django: ${djangoUrl}`)
    
    try {
      const response = await fetch(djangoUrl, {
        headers: {
          'Content-Type': 'application/json',
        },
        cache: 'no-store', // Always fetch fresh data
      })
      
      if (!response.ok) {
        throw new Error(`Django API error: ${response.status} ${response.statusText}`)
      }
      
      const data = await response.json()
      console.log(`✅ Django API returned ${data.count || 0} future recommendations`)
      
      // Transform Django response to match frontend expectations
      const transformedData = {
        ...data,
        confidence_threshold: 55, // Default threshold used by Django
        fixtures_analyzed: data.count || 0,
        // Transform recommendations array
        data: data.recommendations ? data.recommendations.map((item: any) => {
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
            // Note: Django /api/recommendations/ already returns values in correct format (0-1 decimals)
            ev: item.expected_value,
            odds: outcomeOdds,
            score: item.confidence * 100, // Convert to percentage for score
            explanation: item.explanation || item.notes || 'No explanation available',
            probabilities: item.probabilities,
            odds_data: {
              home: item.odds_home,
              draw: item.odds_draw,
              away: item.odds_away,
              bookmaker: item.bookmaker || 'Unknown'
            },
            ensemble_info: item.ensemble_info || {
              model_count: item.model_count || 0,
              consensus: item.consensus || 0,
              variance: item.variance || 0,
              strategy: 'ensemble'
            }
          }
        }) : []
      }
      
      return NextResponse.json(transformedData)
      
    } catch (djangoError) {
      console.error('❌ Django backend error:', djangoError)
      
      // Return error response
      return NextResponse.json(
        {
          success: false,
          error: `Django backend unavailable: ${djangoError instanceof Error ? djangoError.message : String(djangoError)}`,
          data: [],
          count: 0,
        },
        { status: 503 }
      )
    }
    
  } catch (error) {
    console.error('❌ Error in recommendations API:', error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to fetch recommendations',
        data: [],
        count: 0,
      },
      { status: 500 }
    )
  }
}

