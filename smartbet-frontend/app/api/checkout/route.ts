/**
 * Polar.sh checkout proxy.
 *
 * Receives ?productId=… from the CheckoutButton, creates a checkout session
 * via Polar's REST API, then 302s the user to Polar's hosted checkout page.
 *
 * We use the REST API directly instead of @polar-sh/nextjs because that SDK
 * pins next@^15, which conflicts with our next@14. The two operations we need
 * (create-checkout, verify-webhook) are simple enough that a custom handler
 * is clearer than dragging in the SDK + a framework upgrade.
 *
 * Required env:
 *   POLAR_ACCESS_TOKEN  — server-side, has write access to checkouts
 *   POLAR_SERVER        — "production" (default) or "sandbox"
 *   NEXT_PUBLIC_APP_URL — used as the success redirect target
 */
import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

function polarBaseUrl(): string {
  const server = (process.env.POLAR_SERVER || 'production').toLowerCase()
  return server === 'sandbox'
    ? 'https://sandbox-api.polar.sh'
    : 'https://api.polar.sh'
}

export async function GET(request: NextRequest) {
  const accessToken = process.env.POLAR_ACCESS_TOKEN
  if (!accessToken) {
    console.error('[checkout] POLAR_ACCESS_TOKEN not set')
    return NextResponse.json({ error: 'checkout misconfigured' }, { status: 500 })
  }

  const productId = request.nextUrl.searchParams.get('productId')
  if (!productId) {
    return NextResponse.json({ error: 'productId is required' }, { status: 400 })
  }

  const appUrl = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'
  const successUrl = `${appUrl}/dashboard?payment=success`

  try {
    const res = await fetch(`${polarBaseUrl()}/v1/checkouts/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        products: [productId],
        success_url: successUrl,
      }),
    })

    if (!res.ok) {
      const text = await res.text()
      console.error(`[checkout] Polar API ${res.status}: ${text}`)
      return NextResponse.json(
        { error: 'Could not create checkout session' },
        { status: 502 },
      )
    }

    const data = await res.json()
    const checkoutUrl = data?.url
    if (!checkoutUrl) {
      console.error('[checkout] Polar response missing url:', JSON.stringify(data))
      return NextResponse.json(
        { error: 'Unexpected response from payment provider' },
        { status: 502 },
      )
    }

    return NextResponse.redirect(checkoutUrl, 302)
  } catch (err) {
    console.error('[checkout] Polar call threw:', err)
    return NextResponse.json(
      { error: 'Payment provider unreachable' },
      { status: 502 },
    )
  }
}
