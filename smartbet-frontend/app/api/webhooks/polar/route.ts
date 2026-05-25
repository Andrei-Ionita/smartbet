/**
 * Polar.sh webhook receiver.
 *
 * Polar uses the Standard Webhooks spec (https://www.standardwebhooks.com/).
 * We verify the signature ourselves to avoid the @polar-sh/nextjs SDK, which
 * requires next@^15 (we're on 14).
 *
 * Signature scheme:
 *   - Headers `webhook-id`, `webhook-timestamp`, `webhook-signature` are sent.
 *   - Signed content is `${id}.${timestamp}.${rawBody}`.
 *   - HMAC-SHA256 with the secret (base64-decoded after stripping `whsec_`).
 *   - `webhook-signature` header is space-separated list of `v1,<base64>` pairs;
 *     any one match is sufficient.
 *
 * Required env:
 *   POLAR_WEBHOOK_SECRET   — starts with `whsec_`; base64-encoded HMAC key.
 *   DJANGO_API_URL         — backend base URL (e.g. https://api.betglitch.com).
 *   INTERNAL_API_SECRET    — shared secret the backend's upgrade-tier endpoint
 *                            checks via the X-Internal-Auth header.
 */
import { NextRequest, NextResponse } from 'next/server'
import crypto from 'crypto'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

// Reject events older than 5 minutes to neutralize replay attacks.
const MAX_AGE_SECONDS = 300

interface PolarPayload {
  type: string
  data: {
    id?: string
    customer?: { email?: string }
    [k: string]: unknown
  }
}

/**
 * Verify a Standard-Webhooks signature header against raw body.
 * Constant-time compare via crypto.timingSafeEqual.
 */
function verifySignature(opts: {
  webhookId: string
  webhookTimestamp: string
  body: string
  signatureHeader: string
  secret: string
}): boolean {
  const rawSecret = opts.secret.startsWith('whsec_')
    ? opts.secret.slice('whsec_'.length)
    : opts.secret
  let keyBuf: Buffer
  try {
    keyBuf = Buffer.from(rawSecret, 'base64')
  } catch {
    return false
  }
  if (keyBuf.length === 0) return false

  const signedContent = `${opts.webhookId}.${opts.webhookTimestamp}.${opts.body}`
  const expected = crypto
    .createHmac('sha256', keyBuf)
    .update(signedContent)
    .digest('base64')

  // header looks like: "v1,abc... v1,def..."
  const candidates = opts.signatureHeader.split(' ').filter(Boolean)
  for (const c of candidates) {
    const parts = c.split(',')
    if (parts.length !== 2 || parts[0] !== 'v1') continue
    try {
      const sigBuf = Buffer.from(parts[1], 'base64')
      const expBuf = Buffer.from(expected, 'base64')
      if (sigBuf.length === expBuf.length && crypto.timingSafeEqual(sigBuf, expBuf)) {
        return true
      }
    } catch {
      continue
    }
  }
  return false
}

async function callBackendUpgrade(payload: { email: string; tier: 'free' | 'pro'; subscription_id?: string }) {
  const base = process.env.DJANGO_API_URL || 'http://localhost:8000'
  const internalSecret = process.env.INTERNAL_API_SECRET || ''

  try {
    const res = await fetch(`${base}/api/auth/upgrade-tier/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Internal-Auth': internalSecret,
      },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const text = await res.text().catch(() => '<no body>')
      console.error(`[polar webhook] Django upgrade-tier ${res.status}: ${text}`)
    }
  } catch (err) {
    console.error('[polar webhook] Django upgrade-tier call threw:', err)
  }
}

export async function POST(request: NextRequest) {
  const secret = process.env.POLAR_WEBHOOK_SECRET
  if (!secret) {
    console.error('[polar webhook] POLAR_WEBHOOK_SECRET not set')
    return NextResponse.json({ error: 'webhook misconfigured' }, { status: 500 })
  }

  const webhookId = request.headers.get('webhook-id')
  const webhookTimestamp = request.headers.get('webhook-timestamp')
  const signatureHeader = request.headers.get('webhook-signature')
  if (!webhookId || !webhookTimestamp || !signatureHeader) {
    return NextResponse.json({ error: 'missing webhook headers' }, { status: 400 })
  }

  const tsNum = Number(webhookTimestamp)
  if (!Number.isFinite(tsNum)) {
    return NextResponse.json({ error: 'bad timestamp' }, { status: 400 })
  }
  const nowSec = Math.floor(Date.now() / 1000)
  if (Math.abs(nowSec - tsNum) > MAX_AGE_SECONDS) {
    return NextResponse.json({ error: 'timestamp out of tolerance' }, { status: 400 })
  }

  // Read raw body for signature verification (must match exactly what Polar signed).
  const body = await request.text()

  if (!verifySignature({ webhookId, webhookTimestamp, body, signatureHeader, secret })) {
    console.warn(`[polar webhook] Signature mismatch for webhook-id=${webhookId}`)
    return NextResponse.json({ error: 'signature mismatch' }, { status: 401 })
  }

  let payload: PolarPayload
  try {
    payload = JSON.parse(body)
  } catch {
    return NextResponse.json({ error: 'invalid JSON' }, { status: 400 })
  }

  const email = payload.data?.customer?.email
  const subscriptionId = typeof payload.data?.id === 'string' ? payload.data.id : undefined

  switch (payload.type) {
    case 'subscription.created':
    case 'subscription.updated':
    case 'subscription.active':
      if (email) {
        await callBackendUpgrade({ email, tier: 'pro', subscription_id: subscriptionId })
      }
      break

    case 'subscription.canceled':
    case 'subscription.revoked':
      if (email) {
        await callBackendUpgrade({ email, tier: 'free', subscription_id: subscriptionId })
      }
      break

    default:
      // Ack but don't act — Polar sends many event types we don't care about.
      console.log(`[polar webhook] Unhandled event: ${payload.type}`)
  }

  // Return 200 quickly so Polar doesn't retry — backend errors are logged but
  // not surfaced to Polar (it would just retry indefinitely otherwise).
  return NextResponse.json({ received: true })
}
