import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

export async function GET() {
  const api = process.env.DJANGO_API_URL
    || process.env.NEXT_PUBLIC_API_URL
    || 'https://api.betglitch.com'

  try {
    const response = await fetch(`${api}/api/transparency/strategies/`, {
      cache: 'no-store',
      signal: AbortSignal.timeout(12000),
    })
    if (!response.ok) throw new Error(`strategy evidence API ${response.status}`)
    const body = await response.json()
    return NextResponse.json(body, {
      headers: { 'Cache-Control': 'public, max-age=60, stale-while-revalidate=300' },
    })
  } catch (error) {
    console.error('strategy evidence unavailable:', error)
    return NextResponse.json(
      { success: false, data: null, error: 'Strategy evidence is temporarily unavailable.' },
      { status: 503 },
    )
  }
}
