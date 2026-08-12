import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

/** Same-origin, read-only bridge to the immutable public claims authority. */
export async function GET() {
  const api = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  try {
    const response = await fetch(`${api}/api/proof/claims/?limit=200`, {
      cache: 'no-store',
    })
    if (!response.ok) throw new Error(`claims API ${response.status}`)

    const body = await response.json()
    if (!body?.success || !Array.isArray(body?.claims)) {
      throw new Error('invalid claims response')
    }

    return NextResponse.json(body, {
      headers: { 'Cache-Control': 'no-store' },
    })
  } catch (error) {
    console.error('published claims proxy failed:', error)
    return NextResponse.json(
      { success: false, error: 'Published picks are temporarily unavailable.' },
      { status: 503, headers: { 'Cache-Control': 'no-store' } },
    )
  }
}
