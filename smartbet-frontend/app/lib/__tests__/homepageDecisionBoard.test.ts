import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..', '..')
const read = (path: string) => readFileSync(join(ROOT, path), 'utf8')

describe('homepage tracked selections', () => {
  const home = read('app/page.tsx')
  const selections = read('app/components/HomepageSelections.tsx')
  const route = read('app/api/results-selections/route.ts')
  const engine = read('app/api/recommendations/engine.ts')

  it('replaces the technical decision board with one clear public selection stream', () => {
    expect(home).toContain('<HomepageSelections')
    expect(home).not.toContain('<HomepageDecisionBoard')
    expect(home).not.toContain('<ModelShortlistCard')
    expect(home).not.toContain('<HomepageStrategyFits')
  })

  it('states that selections are frozen and permanently tracked', () => {
    expect(selections).toContain('frozen before kickoff')
    expect(selections).toContain('Every outcome remains in Results')
    expect(selections).toContain('not guarantees or instructions to bet')
  })

  it('shows at most five active selections with one reason per card', () => {
    expect(selections).toContain('.slice(0, 5)')
    expect(selections).toContain("reason_code === 'potential_value'")
    expect(selections).toContain('Potential value')
    expect(selections).toContain('Strong model signal')
    expect(selections).not.toContain('Strategy match')
  })

  it('reads only the frozen homepage record', () => {
    expect(selections).toContain('/api/results-selections?category=homepage&state=pending')
    expect(route).toContain('/api/results/selections/')
    expect(route).not.toContain('/api/internal/')
  })

  it('keeps price classification inside the selection engine', () => {
    expect(engine).toContain('candidate.value_signal_aligned')
    expect(engine).toContain('price_watchlist: priceWatchlist')
  })

  it('opens permanent fixture pages and the complete homepage record', () => {
    expect(selections).toContain("return `/prediction/${slug(")
    expect(selections).toContain('/track-record?category=homepage')
    expect(selections).not.toContain('href={`/explore?fixture=')
  })
})
