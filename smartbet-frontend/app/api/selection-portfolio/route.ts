import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export async function GET(request: NextRequest) {
  const api = (process.env.DJANGO_API_URL || process.env.NEXT_PUBLIC_API_URL || 'https://api.betglitch.com').replace(/\/$/, '')
  const results = new URL(request.url).searchParams.get('view') === 'results'
  try {
    const response = await fetch(`${api}/api/selection-portfolio/${results ? '?view=results' : ''}`, {
      cache: 'no-store', signal: AbortSignal.timeout(8000),
    })
    const body = await response.json()
    return NextResponse.json(body, { status: response.status, headers: {
      'Cache-Control': response.ok ? 'public, max-age=0, s-maxage=30' : 'no-store',
    } })
  } catch {
    return NextResponse.json({ success: false, error: 'Selection board unavailable' }, { status: 503 })
  }
}
