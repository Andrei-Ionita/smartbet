import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

export async function GET(request: NextRequest) {
  const api = (process.env.DJANGO_API_URL
    || process.env.NEXT_PUBLIC_API_URL
    || 'https://api.betglitch.com').replace(/\/$/, '')
  const incoming = new URL(request.url)
  const params = new URLSearchParams()
  for (const key of ['category', 'source_key', 'state']) {
    const value = incoming.searchParams.get(key)
    if (value) params.set(key, value)
  }

  try {
    const response = await fetch(
      `${api}/api/results/selections/${params.size ? `?${params}` : ''}`,
      { cache: 'no-store', signal: AbortSignal.timeout(8000) },
    )
    const body = await response.json().catch(() => ({}))
    return NextResponse.json(body, {
      status: response.status,
      headers: {
        'Cache-Control': 'public, max-age=0, s-maxage=60, stale-while-revalidate=120',
      },
    })
  } catch {
    return NextResponse.json(
      { success: false, selections: [], error: 'Results are temporarily unavailable.' },
      { status: 503, headers: { 'Cache-Control': 'no-store' } },
    )
  }
}
