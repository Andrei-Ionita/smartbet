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

  it('keeps education, lab evidence and tracked selections explicitly separate', () => {
    const library = read('app/strategies/StrategiesContent.tsx')
    const detail = read('app/strategies/[slug]/StrategyDetailContent.tsx')
    expect(library).toContain('Understand the strategy first')
    expect(library).toContain('Every displayed selection now remains in the separate Strategy Results record')
    expect(detail).toContain('may show current tracked selections')
    expect(detail).toContain('Every current selection displayed above is frozen before kickoff')
  })

  it('uses only the narrow public evidence API', () => {
    const route = read('app/api/strategy-lab/route.ts')
    expect(route).toContain('/api/transparency/strategies/')
    expect(route).not.toContain('/api/internal/strategies-lab/')
  })

  it('shows no more than five frozen current selections without exposing model internals', () => {
    const detail = read('app/strategies/[slug]/StrategyDetailContent.tsx')
    const component = read('app/components/StrategyCurrentFits.tsx')
    const route = read('app/api/results-selections/route.ts')

    expect(detail).toContain('<StrategyCurrentFits')
    expect(component).toContain('Up to 5 fixtures, frozen and tracked')
    expect(component).toContain('.slice(0, 5)')
    expect(component).toContain('category=strategy&source_key=')
    expect(component).toContain('Every result remains permanently visible in Strategy Results')
    expect(component).not.toContain('Model estimate')
    expect(route).toContain('/api/results/selections/')
    expect(route).not.toContain('/api/internal/')
  })

  it('keeps homepage and strategy selections in separate public records', () => {
    const home = read('app/page.tsx')
    const component = read('app/components/HomepageSelections.tsx')
    const results = read('app/track-record/UnifiedResultsContent.tsx')

    expect(home).toContain('<HomepageSelections')
    expect(component).toContain('category=homepage&state=pending')
    expect(component).not.toContain('Strategy match')
    expect(results).toContain("category: 'homepage' | 'strategy'")
    expect(results).toContain("row.category === 'strategy'")
  })

  it('is reachable through navigation, footer and sitemap', () => {
    expect(read('components/Navigation.tsx')).toContain("href: '/strategies'")
    expect(read('components/Footer.tsx')).toContain('href="/strategies"')
    expect(read('app/sitemap.ts')).toContain("'/strategies'")
  })
})
