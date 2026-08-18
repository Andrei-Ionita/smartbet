import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..', '..')
const read = (path: string) => readFileSync(join(ROOT, path), 'utf8')

describe('homepage decision board', () => {
  const home = read('app/page.tsx')
  const board = read('app/components/HomepageDecisionBoard.tsx')
  const route = read('app/api/recommendations/route.ts')
  const engine = read('app/api/recommendations/engine.ts')

  it('replaces the homogeneous shortlist and separate strategy wall', () => {
    expect(home).toContain('<HomepageDecisionBoard')
    expect(home).not.toContain('<ModelShortlistCard')
    expect(home).not.toContain('<HomepageStrategyFits')
  })

  it('states three different evidence claims and their boundaries', () => {
    expect(board).toContain('Price watchlist')
    expect(board).toContain('Strategy opportunities')
    expect(board).toContain('Strong signals')
    expect(board).toContain('no verified price edge')
    expect(board).toContain('not evidence that the strategy is profitable')
    expect(board).toContain('not evidence that the available odds are valuable')
  })

  it('shows no more than six distinct research cards', () => {
    expect(board).toContain('valueWatchlist.slice(0, 2)')
    expect(board).toContain('.slice(0, 2)')
    expect(board).toContain('!usedIds.has(item.fixture_id)')
  })

  it('classifies price evidence before crossing the public boundary', () => {
    expect(engine).toContain('candidate.value_signal_aligned')
    expect(engine).toContain('price_watchlist: priceWatchlist')
    expect(route).toContain('rawDecisionBoard.price_watchlist')
    expect(route).toContain('toPublicModelShortlist')
  })

  it('does not fill an empty price lane with ordinary favourites', () => {
    expect(board).toContain('We will not fill this lane with ordinary favourites.')
  })
})
