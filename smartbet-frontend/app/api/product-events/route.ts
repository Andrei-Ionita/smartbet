import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

const backendUrl = () => (
  process.env.DJANGO_API_URL
  || process.env.NEXT_PUBLIC_API_URL
  || 'http://localhost:8000'
).replace(/\/$/, '')

const unavailable = () => NextResponse.json(
  { status: 'unavailable', event_ingestion: false },
  { status: 503, headers: { 'Cache-Control': 'no-store' } },
)

/** Same-origin readiness probe used by production monitoring. */
export async function GET() {
  try {
    const response = await fetch(`${backendUrl()}/api/product-events/`, {
      cache: 'no-store',
    })
    const body = await response.json()
    return NextResponse.json(body, {
      status: response.status,
      headers: { 'Cache-Control': 'no-store' },
    })
  } catch {
    return unavailable()
  }
}

/**
 * Proxies the tiny allowlisted event body without forwarding cookies, auth or
 * browser identity. The backend remains the single validation boundary.
 */
export async function POST(request: NextRequest) {
  const contentLength = Number(request.headers.get('content-length') || 0)
  if (contentLength > 4096) {
    return NextResponse.json(
      { success: false, error: 'Payload too large' },
      { status: 413, headers: { 'Cache-Control': 'no-store' } },
    )
  }

  try {
    const body = await request.text()
    if (new TextEncoder().encode(body).byteLength > 4096) {
      return NextResponse.json(
        { success: false, error: 'Payload too large' },
        { status: 413, headers: { 'Cache-Control': 'no-store' } },
      )
    }
    const origin = request.headers.get('origin') || new URL(request.url).origin
    const response = await fetch(`${backendUrl()}/api/product-events/`, {
      method: 'POST',
      cache: 'no-store',
      headers: {
        'Content-Type': 'application/json',
        Origin: origin,
      },
      body,
    })
    const responseBody = await response.json()
    return NextResponse.json(responseBody, {
      status: response.status,
      headers: { 'Cache-Control': 'no-store' },
    })
  } catch {
    return unavailable()
  }
}
