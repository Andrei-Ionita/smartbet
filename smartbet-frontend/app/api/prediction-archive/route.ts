import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

export async function GET(request: NextRequest) {
  const api = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const query = request.nextUrl.searchParams.toString()
  try {
    const response = await fetch(
      `${api}/api/transparency/prediction-archive/${query ? `?${query}` : ''}`,
      { cache: 'no-store' },
    )
    const body = await response.json()
    return NextResponse.json(body, { status: response.status })
  } catch (error) {
    console.error('prediction archive unavailable:', error)
    return NextResponse.json(
      { success: false, error: 'Prediction evidence archive is temporarily unavailable.' },
      { status: 503 },
    )
  }
}
