/**
 * HMAC signing for server-to-server recommendation ingest.
 *
 * SERVER ONLY. This module imports `node:crypto` and reads a non-public
 * environment variable, so importing it from a client component is a build
 * error rather than a silent leak — which is the point.
 *
 * The secret must never be named NEXT_PUBLIC_*: that prefix inlines the value
 * into the client bundle at build time, which would publish it to every
 * visitor.
 *
 * Contract (must match core/services/ingest_auth.py):
 *
 *   X-BetGlitch-Timestamp   unix seconds
 *   X-BetGlitch-Request-ID  unique per logical request, stable across retries
 *   X-BetGlitch-Signature   hex HMAC-SHA256 over
 *                           `<timestamp>.<request_id>.<sha256(body)>`
 */
import { createHash, createHmac, randomUUID } from 'node:crypto'

export type IngestHeaders = Record<string, string>

/** Present only when the secret is configured. Callers must fail closed. */
export function isIngestConfigured(): boolean {
  return Boolean(
    process.env.RECOMMENDATION_INGEST_SECRET_CURRENT ||
      process.env.RECOMMENDATION_INGEST_SECRET,
  )
}

/**
 * Sign a raw JSON body. Returns null when no secret is configured, so the
 * caller skips the request rather than sending one that will be rejected.
 *
 * `requestId` is accepted so a retry can reuse it: the backend treats the same
 * id with the same body as an idempotent retry and the same id with a
 * different body as a replay.
 */
export function signIngestRequest(
  rawBody: string,
  requestId: string = randomUUID().replace(/-/g, ''),
): IngestHeaders | null {
  const secret =
    process.env.RECOMMENDATION_INGEST_SECRET_CURRENT ||
    process.env.RECOMMENDATION_INGEST_SECRET

  if (!secret) return null

  const timestamp = String(Math.floor(Date.now() / 1000))
  const bodyHash = createHash('sha256').update(rawBody, 'utf8').digest('hex')
  const signature = createHmac('sha256', secret)
    .update(`${timestamp}.${requestId}.${bodyHash}`, 'utf8')
    .digest('hex')

  return {
    'Content-Type': 'application/json',
    'X-BetGlitch-Timestamp': timestamp,
    'X-BetGlitch-Request-ID': requestId,
    'X-BetGlitch-Signature': signature,
  }
}
