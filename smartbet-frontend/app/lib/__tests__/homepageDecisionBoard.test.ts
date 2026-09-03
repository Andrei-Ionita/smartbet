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

  it('separates recorded validation selections from current candidates without claiming a public record', () => {
    expect(selections).toContain('Recorded selections support engine validation')
    expect(selections).toContain('the public performance history is paused until the engine rules are locked')
    expect(selections).toContain('Recorded for validation')
    expect(selections).toContain('Current candidate')
    expect(selections).toContain('No public performance claim is being made')
    expect(selections).not.toContain('permanently tracked')
  })

  it('restores five rich full-width rows mixing value, strategies and signals', () => {
    expect(selections).toContain('Five fixtures worth a closer look')
    expect(selections).toContain("reason_code === 'potential_value'")
    expect(selections).toContain("reason_code === 'strategy_match'")
    expect(selections).toContain("reason_code === 'strong_signal'")
    expect(selections).toContain('Potential value')
    expect(selections).toContain('Strategy match')
    expect(selections).toContain('Strong signal')
    expect(selections).toContain('mt-6 space-y-3')
    expect(selections).toContain('lg:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.9fr)_auto]')
    expect(selections).not.toContain('xl:grid-cols-5')
    expect(selections).not.toContain('overflow-x-auto')
  })

  it('restores strategy explanations and richer evidence on each row', () => {
    expect(selections).toContain('Understand strategy')
    expect(selections).toContain('strategyHref(item.strategy_key)')
    expect(selections).toContain('bookmakers checked')
    expect(selections).toContain('The selection and displayed price were frozen before kickoff')
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

  it('opens permanent fixture pages and gates the historical record', () => {
    expect(selections).toContain("return `/prediction/${slug(")
    expect(selections).toContain('PUBLIC_RESULTS_VISIBLE && <Link href="/track-record"')
    expect(selections).toContain('href="/track-record"')
    expect(selections).not.toContain('href={`/explore?fixture=')
  })
})
