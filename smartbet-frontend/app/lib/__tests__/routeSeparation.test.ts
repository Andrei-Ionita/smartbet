/**
 * Transport contract for the two recommendation routes.
 *
 * These invoke the REAL handlers with a mocked engine, so they test what the
 * routes actually do rather than what their source looks like. The engine is
 * mocked because it makes live SportMonks calls; everything the routes decide —
 * auth, serialization, status codes, cache headers, method rejection — is real.
 *
 * The property that matters most is negative: the public handler has no path,
 * under any header, that reaches the internal payload.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const INTERNAL_FIXTURE = {
  fixture_id: 1, home_team: 'A', away_team: 'B',
  home_id: 10, away_id: 11, season_id: 99,
  league: 'L', kickoff: '2026-08-12 18:45:00',
  predicted_outcome: 'Btts yes',
  confidence: 0.66,
  expected_value: 0.2,
  ev: 0.2,
  odds: 1.8,
  odds_provenance: { odds_market_id: 14, odds_bookmaker_name: 'X' },
  probabilities: {}, odds_data: {}, teams_data: {},
  explanation: 'Highest-ranked outcome: BTTS — Btts yes',
  best_market: {
    type: 'btts', name: 'BTTS', display_name: 'Both Teams To Score',
    predicted_outcome: 'Btts yes', probability: 0.66, probability_gap: 0.3,
    odds: 1.8, expected_value: 0.2, market_score: 0.41,
    original_probability: 0.62, original_ev: 0.419,
    odds_provenance: { odds_market_id: 14 },
  },
  all_markets: [{
    type: 'btts', name: 'BTTS', predicted_outcome: 'Btts yes',
    probability: 0.66, odds: 1.8, expected_value: 0.2,
    market_score: 0.41, is_recommended: true,
  }],
  enhancement_data: {
    value_zone: { zone: 'trap', warning: 'Extreme EV detected - likely odds error, proceed with caution' },
    adjustments_applied: true,
  },
  debug_info: { confidence_score: 0.62, variance: 'Low', value_zone: 'trap' },
  revenue_vs_risk_score: 0.4,
  signal_quality: 'Strong',
  is_recommended: true,
}

const OK_PAYLOAD = {
  ok: true as const,
  recommendations: [INTERNAL_FIXTURE],
  envelope: {
    total: 1, leagues_covered: 27, fixtures_analyzed: 10,
    fixtures_with_predictions: 5,
    lastUpdated: '2026-08-06T09:00:00.000Z', message: 'Success',
  },
  confidenceThreshold: 55,
}

const buildRecommendationPayload = vi.fn()
vi.mock('@/app/api/recommendations/engine', () => ({
  get buildRecommendationPayload() { return buildRecommendationPayload },
}))
vi.mock('../../api/recommendations/engine', () => ({
  get buildRecommendationPayload() { return buildRecommendationPayload },
}))

const SECRET = 'test-internal-secret-value-1234567890'

beforeEach(() => {
  buildRecommendationPayload.mockReset()
  buildRecommendationPayload.mockResolvedValue(OK_PAYLOAD)
  process.env.INTERNAL_API_SECRET = SECRET
})

afterEach(() => {
  delete process.env.INTERNAL_API_SECRET
  vi.resetModules()
})

const req = (headers: Record<string, string> = {}) =>
  new Request('https://www.betglitch.com/api/x', { headers }) as any

/** Comments legitimately name what they forbid; scan rendered code only. */
const stripComments = (src: string) =>
  src
    .replace(/\r\n/g, '\n')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .split('\n')
    .map((l) => l.replace(/\/\/.*$/, ''))
    .join('\n')

/** Every key path in an object graph, at every depth. */
function allKeys(node: unknown, acc: string[] = []): string[] {
  if (Array.isArray(node)) node.forEach((v) => allKeys(v, acc))
  else if (node && typeof node === 'object') {
    for (const [k, v] of Object.entries(node as Record<string, unknown>)) {
      acc.push(k)
      allKeys(v, acc)
    }
  }
  return acc
}

const FORBIDDEN_PUBLIC = [
  /^ev$/i, /expected_value/i, /original_ev/i, /adjusted_ev/i, /market_score/i,
  /value_zone/i, /trap/i, /\bedge\b/i, /form_multiplier/i, /shadow/i,
  /activation/i, /calibrat/i, /debug_info/i, /enhancement_data/i,
  /signal_quality/i, /revenue_vs_risk/i, /confidence_threshold/i,
  /is_recommended/i, /original_probability/i, /variance/i,
]

describe('PUBLIC /api/recommendations', () => {
  it('returns the allowlisted DTO and no internal field, at any depth', async () => {
    const { GET } = await import('../../api/recommendations/route')
    const res = await GET()
    const body = await res.json()

    expect(res.status).toBe(200)
    const keys = allKeys(body)
    for (const rule of FORBIDDEN_PUBLIC) {
      const hits = keys.filter((k) => rule.test(k))
      expect(hits, `forbidden key(s) ${hits.join(',')} for ${rule}`).toEqual([])
    }
  })

  it('leaks no forbidden STRING either', async () => {
    const { GET } = await import('../../api/recommendations/route')
    const raw = JSON.stringify(await (await GET()).json())
    expect(raw).not.toMatch(/Extreme EV detected/i)
    expect(raw).not.toMatch(/proceed with caution/i)
    expect(raw).not.toMatch(/\btrap\b/i)
  })

  it('keeps what the interface needs', async () => {
    const { GET } = await import('../../api/recommendations/route')
    const body = await (await GET()).json()
    const rec = body.recommendations[0]
    expect(rec.fixture_id).toBe(1)
    expect(rec.confidence).toBe(0.66)
    expect(rec.odds).toBe(1.8)
    expect(rec.best_market.probability_gap).toBe(0.3)
    expect(body.total).toBe(1)
  })

  it('ignores X-Internal-Auth entirely — no header can widen the response', async () => {
    const { GET } = await import('../../api/recommendations/route')
    // The public handler takes no argument, so a header cannot even be read.
    expect(GET.length).toBe(0)

    const body = await (await GET()).json()
    expect(JSON.stringify(body)).not.toContain('original_ev')
  })

  it('declares an explicit public cache policy', async () => {
    const { GET } = await import('../../api/recommendations/route')
    const cc = (await GET()).headers.get('cache-control') || ''
    expect(cc).toContain('public')
    expect(cc).toContain('s-maxage=60')
    expect(cc).not.toContain('no-store')
  })

  it('never imports the raw payload path', async () => {
    const { readFileSync } = await import('node:fs')
    const { join } = await import('node:path')
    const src = readFileSync(
      join(__dirname, '..', '..', 'api', 'recommendations', 'route.ts'), 'utf8')
    // It must serialize; it must not have an auth branch.
    expect(src).toContain('toPublicRecommendationList')
    expect(src).not.toContain('INTERNAL_API_SECRET')
    expect(src).not.toContain('x-internal-auth')
    expect(src).not.toContain('confidence_threshold')
  })

  it('does not echo the error when the engine throws', async () => {
    buildRecommendationPayload.mockRejectedValue(
      new Error('connect failed for ?api_token=SUPERSECRET&x=1'))
    const { GET } = await import('../../api/recommendations/route')
    const res = await GET()
    const body = await res.json()
    expect(res.status).toBe(500)
    expect(JSON.stringify(body)).not.toContain('SUPERSECRET')
    expect(body).toEqual({ error: 'Failed' })
  })
})

describe('INTERNAL /api/internal/recommendations', () => {
  const load = () => import('../../api/internal/recommendations/route')

  it('401s with no credential', async () => {
    const { GET } = await load()
    const res = await GET(req())
    expect(res.status).toBe(401)
    expect(await res.json()).toEqual({ success: false, error: 'unauthorized' })
  })

  it('401s with the wrong credential', async () => {
    const { GET } = await load()
    const res = await GET(req({ 'x-internal-auth': 'wrong' }))
    expect(res.status).toBe(401)
  })

  it('fails CLOSED with 503 when the secret is unset', async () => {
    delete process.env.INTERNAL_API_SECRET
    const { GET } = await load()
    const res = await GET(req({ 'x-internal-auth': 'anything' }))
    expect(res.status).toBe(503)
    // An unset secret must never mean "allow everyone": no payload at all.
    const body = await res.json()
    expect(body.recommendations).toBeUndefined()
    expect(body.success).toBe(false)
    // And the engine must not even have been invoked.
    expect(buildRecommendationPayload).not.toHaveBeenCalled()
  })

  it('returns the ingestion fields with the right credential', async () => {
    const { GET } = await load()
    const res = await GET(req({ 'x-internal-auth': SECRET }))
    expect(res.status).toBe(200)
    const body = await res.json()
    const rec = body.recommendations[0]
    expect(rec.expected_value).toBe(0.2)
    expect(rec.ev).toBe(0.2)
    expect(rec.best_market.original_ev).toBe(0.419)
    expect(rec.best_market.market_score).toBe(0.41)
    expect(rec.best_market.type).toBe('btts')
    expect(body.confidence_threshold).toBe(55)
  })

  it('sets no-store so nothing can cache it', async () => {
    const { GET } = await load()
    const res = await GET(req({ 'x-internal-auth': SECRET }))
    const cc = res.headers.get('cache-control') || ''
    expect(cc).toContain('no-store')
    expect(cc).toContain('private')
    expect(res.headers.get('pragma')).toBe('no-cache')
    expect(res.headers.get('vary')).toContain('X-Internal-Auth')
  })

  it('applies no-store to the 401 too', async () => {
    const { GET } = await load()
    const res = await GET(req())
    expect(res.headers.get('cache-control') || '').toContain('no-store')
  })

  it.each(['POST', 'PUT', 'PATCH', 'DELETE'])('rejects %s with 405', async (method) => {
    const mod: any = await load()
    const res = await mod[method](req({ 'x-internal-auth': SECRET }))
    expect(res.status).toBe(405)
  })

  it('returns a controlled failure without the provider error text', async () => {
    buildRecommendationPayload.mockRejectedValue(
      new Error('HTTPSConnectionPool ... ?api_token=SUPERSECRET'))
    const { GET } = await load()
    const res = await GET(req({ 'x-internal-auth': SECRET }))
    expect(res.status).toBe(500)
    const raw = JSON.stringify(await res.json())
    expect(raw).not.toContain('SUPERSECRET')
    expect(raw).not.toContain('api_token')
  })

  it('reads the secret from a server-only variable', async () => {
    const { readFileSync } = await import('node:fs')
    const { join } = await import('node:path')
    const src = stripComments(readFileSync(
      join(__dirname, '..', '..', 'api', 'internal', 'recommendations', 'route.ts'),
      'utf8'))
    expect(src).toContain('process.env.INTERNAL_API_SECRET')
    expect(src).not.toMatch(/NEXT_PUBLIC_/)
  })
})

describe('the engine owns no publication decision', () => {
  it('contains no auth branch of its own', async () => {
    const { readFileSync } = await import('node:fs')
    const { join } = await import('node:path')
    const src = stripComments(readFileSync(
      join(__dirname, '..', '..', 'api', 'recommendations', 'engine.ts'), 'utf8'))
    expect(src).not.toContain('INTERNAL_API_SECRET')
    expect(src).not.toContain('x-internal-auth')
    expect(src).not.toContain('toPublicRecommendationList')
  })
})
