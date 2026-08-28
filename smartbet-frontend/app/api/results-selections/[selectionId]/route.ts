import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

export async function GET(
  _request: Request,
  { params }: { params: { selectionId: string } },
) {
  const api = (process.env.DJANGO_API_URL
    || process.env.NEXT_PUBLIC_API_URL
    || 'https://api.betglitch.com').replace(/\/$/, '')

  if (!/^[0-9a-f-]{36}$/i.test(params.selectionId)) {
    return NextResponse.json(
      { success: false, error: 'Invalid selection receipt.' },
      { status: 400, headers: { 'Cache-Control': 'no-store' } },
    )
  }

  try {
    const response = await fetch(
      `${api}/api/results/selections/${params.selectionId}/`,
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
      { success: false, error: 'Selection receipt is temporarily unavailable.' },
      { status: 503, headers: { 'Cache-Control': 'no-store' } },
    )
  }
}
