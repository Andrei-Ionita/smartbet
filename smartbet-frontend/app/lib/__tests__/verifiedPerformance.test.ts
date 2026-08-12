import { describe, it, expect, vi, afterEach } from 'vitest'
import { readFileSync } from 'fs'
import { join } from 'path'
import { CURRENT_STRATEGY_VERSION } from '../currentStrategyRecord'

/**
 * The homepage must never announce zero settled results when results exist.
 *
 * /api/performance shelled out to `python .../get_performance_stats.py` from
 * the Next.js container — an alpine node image with no Python, no Django and
 * no database. It failed on every request since deployment, and four surfaces
 * read it while treating "no data" as zero. On 2026-08-09, with six
 * commitments settled (two won, four lost), the homepage still said "Building
 * the verified record from zero": the product was hiding its own first
 * results.
 *
 * It now derives from /api/proof/claims/, the documented sole authority.
 */

const root = join(__dirname, '..', '..', '..')
/** Comments stripped: the header quotes the removed call to explain it. */
const SOURCE = readFileSync(join(root, 'app/api/performance/route.ts'), 'utf-8')
  .replace(/\r\n/g, '\n')
  .replace(/\/\*[\s\S]*?\*\//g, '')
  .replace(/(^|[^:])\/\/.*$/gm, '$1')

const claim = (state: string, extra: Record<string, unknown> = {}) => ({
  claim_state: state,
  integrity_ok: true,
  ranking_version: CURRENT_STRATEGY_VERSION,
  counts_towards_verified_record: state === 'WON' || state === 'LOST',
  ...extra,
})

function mockClaims(claims: unknown[], ok = true) {
  vi.stubGlobal('fetch', vi.fn(async () => ({
    ok,
    status: ok ? 200 : 503,
    json: async () => ({ claims }),
  })))
}

afterEach(() => vi.unstubAllGlobals())

describe('it never shells out from the web container', () => {
  it('executes no child process', () => {
    expect(SOURCE).not.toContain('child_process')
    expect(SOURCE).not.toContain('exec(')
    expect(SOURCE).not.toContain('get_performance_stats')
  })

  it('reads the claims authority, not the prediction feed', () => {
    expect(SOURCE).toContain('/api/proof/claims/')
    expect(SOURCE).not.toContain('recommended-predictions')
  })
})

describe('settled counts come from real claim states', () => {
  it('excludes every earlier strategy version from the homepage record', async () => {
    mockClaims([
      claim('WON'),
      claim('WON', { ranking_version: 'retired-strategy' }),
    ])
    const { GET } = await import('../../api/performance/route')
    const body = await (await GET()).json()

    expect(body.data.overall.total_predictions).toBe(1)
    expect(body.source).toBe('current_strategy_published_claims')
    expect(body.ranking_version).toBe(CURRENT_STRATEGY_VERSION)
  })

  it('counts wins and losses, excluding pending', async () => {
    mockClaims([
      claim('WON'), claim('WON'), claim('LOST'),
      claim('PENDING'), claim('PENDING'),
    ])
    const { GET } = await import('../../api/performance/route')
    const body = await (await GET()).json()

    expect(body.success).toBe(true)
    expect(body.data.overall.total_predictions).toBe(3)
    expect(body.data.overall.won).toBe(2)
    expect(body.data.overall.lost).toBe(1)
    expect(body.data.overall.pending).toBe(2)
  })

  it('excludes void and cancelled from the win rate', async () => {
    mockClaims([claim('WON'), claim('LOST'), claim('VOID'), claim('CANCELLED')])
    const { GET } = await import('../../api/performance/route')
    const body = await (await GET()).json()

    expect(body.data.overall.total_predictions).toBe(2)
    expect(body.data.overall.void_or_cancelled).toBe(2)
    expect(body.data.overall.win_rate).toBe(50)
  })

  it('ignores a claim that failed its integrity check', async () => {
    mockClaims([claim('WON'), claim('WON', { integrity_ok: false })])
    const { GET } = await import('../../api/performance/route')
    const body = await (await GET()).json()
    expect(body.data.overall.total_predictions).toBe(1)
  })

  it('reports null, not zero, when nothing has settled', async () => {
    // "No verified results yet" and "a 0% win rate" are different claims.
    mockClaims([claim('PENDING')])
    const { GET } = await import('../../api/performance/route')
    const body = await (await GET()).json()

    expect(body.data.overall.total_predictions).toBe(0)
    expect(body.data.overall.win_rate).toBeNull()
  })

  it('publishes no ROI or profit figure', async () => {
    mockClaims([claim('WON'), claim('LOST')])
    const { GET } = await import('../../api/performance/route')
    const body = await (await GET()).json()

    const keys = Object.keys(body.data.overall)
    expect(keys).not.toContain('roi_percent')
    expect(keys).not.toContain('total_profit_loss')
  })
})

describe('failure is loud, never silently zero', () => {
  it('returns 503 rather than an empty record', async () => {
    mockClaims([], false)
    const { GET } = await import('../../api/performance/route')
    const response = await GET()

    expect(response.status).toBe(503)
    expect((await response.json()).data).toBeNull()
  })
})
