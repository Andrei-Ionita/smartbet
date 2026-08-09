import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { join } from 'path'

/**
 * The /prediction page must present ONE signal.
 *
 * A first-visitor review (2026-08-08) caught the page headlining the fixture's
 * 1X2 outcome ("Home — 50") while the price and the "Best market" chip came
 * from best_market ("BTTS Yes — 52"). Two markets rendered as one signal reads
 * as unreliable data — because it is. These tests pin the fix: every headline
 * field (outcome, score, market name) leads with best_market and only falls
 * back to the 1X2 fields when no best market exists.
 */

const root = join(__dirname, '..', '..')
const read = (p: string) => readFileSync(join(root, p), 'utf-8').replace(/\r\n/g, '\n')

const pageSource = read('prediction/[...slug]/page.tsx')
const contentSource = read('prediction/[...slug]/PredictionContent.tsx')

describe('prediction page: best_market is THE signal', () => {
  it('the mapper takes the headline outcome from best_market first', () => {
    expect(pageSource).toContain('fixture.best_market?.predicted_outcome ?? outcome1x2')
  })

  it('the mapper takes confidence from best_market.probability when present', () => {
    expect(pageSource).toMatch(
      /confidence:\s*fixture\.best_market\n?\s*\?\s*fixture\.best_market\.probability/,
    )
  })

  it('metadata leads with best_market for outcome, score and market name', () => {
    expect(pageSource).toContain('bestMarket?.predicted_outcome')
    expect(pageSource).toMatch(/bestMarket\n?\s*\?\s*bestMarket\.probability/)
    expect(pageSource).toContain("bestMarket?.display_name ?? 'Match Result'")
  })

  it('the mapper never spreads market_indicators through to the card', () => {
    expect(pageSource).toContain('market_indicators: undefined')
  })

  it('page copy carries no betting-tips framing', () => {
    for (const source of [pageSource, contentSource]) {
      expect(source).not.toMatch(/betting tips/i)
      expect(source).not.toMatch(/AI[- ]powered/i)
    }
  })
})

describe('live signals carry a visible computation timestamp', () => {
  /**
   * The same review read a legitimate hourly update as "the data changed under
   * me". A live signal without a timestamp cannot be distinguished from
   * unstable data — every card surface must pass lastUpdated.
   */
  const cardCallSites = [
    { file: 'page.tsx', tag: 'GemCard' },
    { file: 'explore/ExploreContent.tsx', tag: 'RecommendationCard' },
    { file: 'prediction/[...slug]/PredictionContent.tsx', tag: 'RecommendationCard' },
  ]

  it.each(cardCallSites)('$file passes lastUpdated to $tag', ({ file, tag }) => {
    const source = read(file)
    const match = source.match(new RegExp(`<${tag}[\\s\\n][\\s\\S]*?\\/>`))
    expect(match, `${file} renders <${tag}>`).toBeTruthy()
    expect(match![0]).toContain('lastUpdated=')
  })

  it('the server page stamps request time (the engine computes on request)', () => {
    expect(pageSource).toContain('lastUpdated={new Date().toISOString()}')
  })

  it('the card renders the timestamp in both languages', () => {
    const card = read('components/RecommendationCard.tsx')
    expect(card).toContain('Signal updated: ')
    expect(card).toContain('Semnal actualizat: ')
  })
})

describe('no surface generates "AI analysis"', () => {
  it('the analysis loading state says what actually happens — a signal is computed', () => {
    const translations = read('locales/translations.ts')
    expect(translations).not.toMatch(/AI analysis|analiza AI/i)
    const explore = read('explore/ExploreContent.tsx')
    expect(explore).not.toMatch(/AI Analysis/i)
  })
})
