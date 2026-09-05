import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
const ROOT = join(__dirname, '..', '..', '..')
const read = (path: string) => readFileSync(join(ROOT, path), 'utf8')

describe('current portfolio Results', () => {
  const results = read('app/track-record/PortfolioResultsContent.tsx')
  it('treats homepage as a subset of one overall ledger', () => {
    expect(results).toContain('homepage_performance')
    expect(results).toContain('Each bet counts once')
    expect(results).not.toContain('/api/proof/claims')
  })
  it('shows individual results while waiting for a sample', () => {
    expect(results).toContain('summary.settled < 30')
    expect(results).toContain('every individual result is visible below')
    expect(results).toContain("LOST: ['Lost', 'Pierdut']")
    expect(results).toContain('row.unit_profit')
  })
  it('does not disguise Asian partial settlements as binary accuracy', () => {
    expect(results).toContain('!m.half_won && !m.half_lost && !m.push')
    expect(results).toContain('Full-win rate for markets without pushes or partial settlements')
  })
  it('offers market and status filters plus permanent receipt links', () => {
    expect(results).toContain('market === row.market_type')
    expect(results).toContain("row.status === 'PENDING'")
    expect(results).toContain('href={row.receipt_url}')
  })
})
