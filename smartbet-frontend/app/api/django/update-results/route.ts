import { NextRequest, NextResponse } from 'next/server'

// This is a dynamic API route that should not be statically generated
export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

export async function POST(request: NextRequest) {
  try {
    // Get Django backend URL from environment variable or use default
    const djangoBaseUrl = process.env.NEXT_PUBLIC_API_URL || 'https://smartbet-backend-production.up.railway.app'
    const djangoUrl = `${djangoBaseUrl}/api/update-fixture-results/`

    console.log(`🔄 Triggering fixture result updates from Django: ${djangoUrl}`)

    try {
      const response = await fetch(djangoUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        cache: 'no-store', // Always fetch fresh data
      })

      if (!response.ok) {
        throw new Error(`Django API error: ${response.status} ${response.statusText}`)
      }

      const data = await response.json()
      console.log(`✅ Result update completed:`, data)

      return NextResponse.json(data)

    } catch (djangoError) {
      console.error('❌ Django backend error:', djangoError)

      // Return error response
      return NextResponse.json(
        {
          success: false,
          error: `Django backend unavailable: ${djangoError instanceof Error ? djangoError.message : String(djangoError)}`,
          updated_count: 0,
        },
        { status: 503 }
      )
    }

  } catch (error) {
    console.error('❌ Error in update-results API:', error)
    return NextResponse.json(
      {
        success: false,
        error: error instanceof Error ? error.message : 'Failed to update fixture results',
        updated_count: 0,
      },
      { status: 500 }
    )
  }
}

