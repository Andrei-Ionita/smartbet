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

  it('shows no more than five qualified current research fits without calling them picks', () => {
    const detail = read('app/strategies/[slug]/StrategyDetailContent.tsx')
    const component = read('app/components/StrategyCurrentFits.tsx')
    const route = read('app/api/strategy-fits/[strategyKey]/route.ts')

    expect(detail).toContain('<StrategyCurrentFits')
    expect(component).toContain('Up to 5 current research fits')
    expect(component).toContain('No fixture passes every check right now')
    expect(component).toContain('is not a published BetGlitch pick')
    expect(component).toContain('not a calibrated probability')
    expect(route).toContain('/current-fits/')
    expect(route).not.toContain('/api/internal/strategies-lab/')
  })

  it('places distinct live strategy fits inside the five-fixture homepage stream', () => {
    const home = read('app/page.tsx')
    const component = read('app/components/HomepageDecisionBoard.tsx')
    const route = read('app/api/homepage-strategy-fits/route.ts')

    expect(home).toContain('<HomepageDecisionBoard')
    expect(component).toContain('Five fixtures worth a closer look')
    expect(component).toContain('none are published picks')
    expect(component).toContain('rankedItems.length >= 5')
    expect(component).toContain('usedIds.has(item.fixtureId)')
    expect(route).toContain('/api/transparency/strategies/current-fits/')
    expect(route).not.toContain('/api/internal/strategies-lab/')
  })

  it('is reachable through navigation, footer and sitemap', () => {
    expect(read('components/Navigation.tsx')).toContain("href: '/strategies'")
    expect(read('components/Footer.tsx')).toContain('href="/strategies"')
    expect(read('app/sitemap.ts')).toContain("'/strategies'")
  })
})
