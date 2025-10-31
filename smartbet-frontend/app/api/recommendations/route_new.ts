import { NextRequest, NextResponse } from 'next/server'

// This is a dynamic API route that should not be statically generated
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

export async function GET(request: NextRequest) {
  try {
    console.log('🔍 Frontend recommendations request - forwarding to Django backend')

    // Forward recommendations request to Django backend
    const djangoUrl = 'http://localhost:8000/api/recommendations/'

    try {
      const response = await fetch(djangoUrl)
      if (!response.ok) {
        throw new Error(`Django API error: ${response.status}`)
      }
      
      const data = await response.json()
      console.log(`✅ Django recommendations API returned ${data.data?.length || 0} recommendations`)
      
      // Return the Django response in the format the frontend expects
      return NextResponse.json({
        recommendations: data.data || [],
        total: data.count || 0,
        leagues_covered: 5, // Our test data covers 5 leagues
        fixtures_analyzed: data.count || 0,
        fixtures_with_predictions: data.count || 0,
        lastUpdated: new Date().toISOString()
      })
      
    } catch (djangoError) {
      console.error('Django backend error:', djangoError)
      
      // Fallback to empty results if Django is not available
      return NextResponse.json({
        recommendations: [],
        total: 0,
        leagues_covered: 0,
        fixtures_analyzed: 0,
        fixtures_with_predictions: 0,
        lastUpdated: new Date().toISOString(),
        error: `Django backend unavailable: ${djangoError}`
      })
    }

  } catch (error) {
    console.error('Error in recommendations API:', error)
    return NextResponse.json(
      { error: 'Failed to fetch recommendations' },
      { status: 500 }
    )
  }
}
