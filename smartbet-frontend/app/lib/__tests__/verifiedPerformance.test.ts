import { afterEach, describe, expect, it, vi } from 'vitest'
import { readFileSync } from 'fs'
import { join } from 'path'

const root = join(__dirname, '..', '..', '..')
const SOURCE = readFileSync(join(root, 'app/api/performance/route.ts'), 'utf-8')

function mockLedger(performance: unknown, ok = true) {
  vi.stubGlobal('fetch', vi.fn(async () => ({
    ok, status: ok ? 200 : 503,
    json: async () => ({ performance }),
  })))
}

afterEach(() => vi.unstubAllGlobals())

describe('the immutable public-selection ledger is the sole authority', () => {
  it('never uses claims, prediction feeds or child processes', () => {
    expect(SOURCE).toContain('/api/results/selections/')
    expect(SOURCE).not.toContain('/api/proof/claims/')
    expect(SOURCE).not.toContain('recommended-predictions')
    expect(SOURCE).not.toContain('child_process')
  })

  it('preserves the canonical settled count and ROI', async () => {
    mockLedger({
      overall: { published: 133, settled: 78, won: 22, lost: 53,
        half_won: 3, profit_units: -21.2, roi_percent: -27.18 },
      by_strategy: [{ key: 'asian-handicap-score-distribution', settled: 8 }],
    })
    const { GET } = await import('../../api/performance/route')
    const body = await (await GET()).json()
    expect(body.data.overall.total_predictions).toBe(78)
    expect(body.data.overall.roi_percent).toBe(-27.18)
    expect(body.data.cohorts.by_strategy).toHaveLength(1)
    expect(body.source).toBe('immutable_public_selection_ledger')
  })

  it('reports null values from an empty but valid ledger', async () => {
    mockLedger({ overall: { published: 0, settled: 0, win_rate: null, roi_percent: null } })
    const { GET } = await import('../../api/performance/route')
    const body = await (await GET()).json()
    expect(body.data.overall.total_predictions).toBe(0)
    expect(body.data.overall.roi_percent).toBeNull()
  })

  it('fails loudly if the ledger is unavailable', async () => {
    mockLedger({}, false)
    const { GET } = await import('../../api/performance/route')
    const response = await GET()
    expect(response.status).toBe(503)
    expect((await response.json()).data).toBeNull()
  })
})
