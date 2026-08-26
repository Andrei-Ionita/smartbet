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

  it('keeps one clear public selection stream on the homepage', () => {
    expect(home).toContain('<HomepageSelections')
    expect(home).not.toContain('<HomepageDecisionBoard')
    expect(home).not.toContain('<ModelShortlistCard')
    expect(home).not.toContain('<HomepageStrategyFits')
  })

  it('separates frozen selections from current candidates without overstating the record', () => {
    expect(selections).toContain('Frozen selections enter Results')
    expect(selections).toContain('current candidates do not count until they are recorded')
    expect(selections).toContain('Tracked in Results')
    expect(selections).toContain('Current candidate')
    expect(selections).not.toContain('permanently tracked')
  })

  it('restores a horizontal five-card mix of value, strategies and signals', () => {
    expect(selections).toContain('Five fixtures worth a closer look')
    expect(selections).toContain("reason_code === 'potential_value'")
    expect(selections).toContain("reason_code === 'strategy_match'")
    expect(selections).toContain("reason_code === 'strong_signal'")
    expect(selections).toContain('Potential value')
    expect(selections).toContain('Strategy match')
    expect(selections).toContain('Strong signal')
    expect(selections).toContain('xl:grid-cols-5')
    expect(selections).toContain('overflow-x-auto')
  })

  it('merges frozen records with both live evidence feeds', () => {
    expect(selections).toContain('/api/results-selections?category=homepage&state=pending')
    expect(selections).toContain('/api/results-selections?category=strategy&state=pending')
    expect(selections).toContain('/api/recommendations/')
    expect(selections).toContain('/api/homepage-strategy-fits')
    expect(route).toContain('/api/results/selections/')
    expect(route).not.toContain('/api/internal/')
  })

  it('deduplicates fixtures and strategy types while capping the board at five', () => {
    expect(selections).toContain('selected.length >= 5')
    expect(selections).toContain('fixtures.has(item.fixture_id)')
    expect(selections).toContain('strategyKeys.has(item.strategy_key)')
    expect(selections).toContain('addFirst(strategies)')
  })

  it('keeps price classification inside the selection engine', () => {
    expect(engine).toContain('candidate.value_signal_aligned')
    expect(engine).toContain('price_watchlist: priceWatchlist')
  })

  it('opens permanent fixture pages and the complete homepage record', () => {
    expect(selections).toContain("return `/prediction/${slug(")
    expect(selections).toContain('href="/track-record"')
    expect(selections).not.toContain('href={`/explore?fixture=')
  })
})
