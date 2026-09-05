import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
const ROOT = join(__dirname, '..', '..', '..')
const read = (path: string) => readFileSync(join(ROOT, path), 'utf8')

describe('published homepage portfolio', () => {
  it('uses the server-published list without combining or reranking live feeds', () => {
    const home = read('app/components/HomepageSelections.tsx')
    expect(home).toContain('data.homepage.map')
    expect(home).not.toContain('curateFive')
    expect(home).not.toContain('/api/recommendations/')
    expect(home).not.toContain('/api/homepage-strategy-fits')
  })
  it('keeps full-width rows and a path to each market', () => {
    const home = read('app/components/HomepageSelections.tsx')
    expect(home).toContain('mt-6 space-y-3')
    expect(home).toContain('href="/markets"')
    expect(home).not.toContain('xl:grid-cols-5')
  })
  it('shows the evidence limits and a receipt on every card', () => {
    const card = read('app/components/PortfolioCard.tsx')
    expect(card).toContain('negative conservative value')
    expect(card).toContain('probability is unavailable')
    expect(card).toContain('href={item.receipt_url}')
    expect(card).toContain('href={market.strategy_url}')
    expect(card).toContain('published_proof_opened')
  })
})
