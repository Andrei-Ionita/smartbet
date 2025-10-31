import { NextRequest, NextResponse } from 'next/server'

// This is a dynamic API route that should not be statically generated
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const limit = searchParams.get('limit') || '50'
    const includePending = searchParams.get('include_pending') || 'true'
    
    // Get Django backend URL from environment variable or use default
    const djangoBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    const djangoUrl = `${djangoBaseUrl}/api/recommended-predictions/?limit=${limit}&include_pending=${includePending}`
    
    console.log(`🔍 Fetching recommended predictions from Django: ${djangoUrl}`)
    
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
      console.log(`✅ Django API returned ${data.count || 0} recommended predictions`)
      
      return NextResponse.json(data)
      
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

