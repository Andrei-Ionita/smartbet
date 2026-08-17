import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { STRATEGIES } from '../strategyLibrary'

const ROOT = join(__dirname, '..', '..', '..')
const read = (path: string) => readFileSync(join(ROOT, path), 'utf8')

describe('public strategy library', () => {
  it('maps every registered lab strategy to one unique educational page', () => {
    expect(STRATEGIES).toHaveLength(12)
    expect(new Set(STRATEGIES.map((item) => item.slug)).size).toBe(12)
    expect(new Set(STRATEGIES.map((item) => item.strategyKey)).size).toBe(12)
    expect(STRATEGIES.map((item) => item.strategyKey)).toEqual(expect.arrayContaining([
      'asian-handicap-score-distribution',
      'asian-goal-line-score-distribution',
      'team-total-score-distribution',
      'correct-score-value',
    ]))
  })

  it('gives both languages mechanics, risk, settlement and price education', () => {
    for (const strategy of STRATEGIES) {
      for (const language of ['en', 'ro'] as const) {
        const copy = strategy.copy[language]
        expect(copy.mechanics.length).toBeGreaterThanOrEqual(3)
        expect(copy.risks.length).toBeGreaterThanOrEqual(3)
        expect(copy.settlement.length).toBeGreaterThan(20)
        expect(copy.breakEvenExample.length).toBeGreaterThan(20)
      }
    }
  })

  it('keeps education, lab evidence and recommendations explicitly separate', () => {
    const library = read('app/strategies/StrategiesContent.tsx')
    const detail = read('app/strategies/[slug]/StrategyDetailContent.tsx')
    expect(library).toContain('Education, not picks')
    expect(library).toContain('Historical backtests can eliminate weak ideas')
    expect(detail).toContain('It is not a current pick')
    expect(detail).toContain('retrospective results cannot qualify a strategy')
  })

  it('uses only the narrow public evidence API', () => {
    const route = read('app/api/strategy-lab/route.ts')
    expect(route).toContain('/api/transparency/strategies/')
    expect(route).not.toContain('/api/internal/strategies-lab/')
  })

  it('is reachable through navigation, footer and sitemap', () => {
    expect(read('components/Navigation.tsx')).toContain("href: '/strategies'")
    expect(read('components/Footer.tsx')).toContain('href="/strategies"')
    expect(read('app/sitemap.ts')).toContain("'/strategies'")
  })
})
