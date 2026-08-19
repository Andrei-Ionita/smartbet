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

  it('labels three different evidence claims inside one ranked stream', () => {
    expect(board).toContain('Potential value')
    expect(board).toContain('Strategy match')
    expect(board).toContain('Strong model signal')
    expect(board).toContain('a match does not prove profitability')
    expect(board).toContain('the available price has no verified edge')
  })

  it('shows no more than five distinct research cards', () => {
    expect(board).toContain('rankedItems.length >= 5')
    expect(board).toContain('usedIds.has(item.fixtureId)')
    expect(board).toContain('one card per fixture')
  })

  it('classifies price evidence before crossing the public boundary', () => {
    expect(engine).toContain('candidate.value_signal_aligned')
    expect(engine).toContain('price_watchlist: priceWatchlist')
    expect(route).toContain('rawDecisionBoard.price_watchlist')
    expect(route).toContain('toPublicModelShortlist')
  })

  it('does not mislabel model-only signals as value', () => {
    expect(board).toContain("add({ kind: 'strong'")
    expect(board).toContain('Potential value first')
  })
})
