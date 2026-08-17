/** Read the latest worker-produced Gem scan from the Django database. */

export interface CachedGemFeed {
  available: boolean
  generated_at?: string | null
  refreshed_at?: string | null
  age_seconds?: number | null
  recommendation_count?: number
  ranking_version?: string | null
  feed?: Record<string, any> | null
}

const backendBase = () => {
  const configured =
    process.env.DJANGO_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    (process.env.NODE_ENV === 'production'
      ? 'https://api.betglitch.com'
      : 'http://localhost:8000')
  return configured.replace(/\/$/, '')
}

export async function loadCachedGemFeed(): Promise<CachedGemFeed> {
  const secret = process.env.INTERNAL_API_SECRET || ''
  if (!secret) throw new Error('Gem feed cache is not configured')

  const response = await fetch(`${backendBase()}/api/internal/gem-feed/`, {
    cache: 'no-store',
    headers: { 'X-Internal-Auth': secret },
    signal: AbortSignal.timeout(5000),
  })

  if (!response.ok) {
    // Do not include response text: even an internal failure should not become
    // part of a public error, log line or provider-credential disclosure.
    throw new Error(`Gem feed cache unavailable (${response.status})`)
  }
  return response.json()
}
