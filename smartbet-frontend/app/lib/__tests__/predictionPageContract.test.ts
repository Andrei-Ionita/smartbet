import { describe, expect, it } from 'vitest'
import { readFileSync } from 'fs'
import { join } from 'path'

const root = join(__dirname, '..', '..')
const read = (path: string) => readFileSync(join(root, path), 'utf-8').replace(/\r\n/g, '\n')

const pageSource = read('prediction/[...slug]/page.tsx')
const contentSource = read('prediction/[...slug]/PredictionContent.tsx')
const exploreSource = read('explore/ExploreContent.tsx')
const workspaceSource = read('components/FixtureDecisionWorkspace.tsx')

describe('fixture pages are decision workspaces, not recommendation cards', () => {
  it('requires the truthful fixture-intelligence contract', () => {
    expect(pageSource).toContain('data?.fixture?.intelligence')
    expect(pageSource).toContain('<PredictionContent fixture={fixture}')
    expect(contentSource).toContain('<FixtureDecisionWorkspace fixture={fixture}')
  })

  it('does not map fixture research into a Recommendation', () => {
    expect(pageSource).not.toContain('Recommendation')
    expect(contentSource).not.toContain('RecommendationCard')
    expect(contentSource).not.toContain('signal score')
    expect(contentSource).not.toContain('expected_value')
  })

  it('metadata describes the actual research product', () => {
    expect(pageSource).toContain('odds, probabilities & context')
    expect(pageSource).toContain('margin-removed market views')
    expect(pageSource).not.toMatch(/highest-ranked outcome|signal score/i)
  })

  it('keeps Gems and Explore components separate', () => {
    expect(exploreSource).toContain('FixtureDecisionWorkspace')
    expect(exploreSource).not.toContain('RecommendationCard')
    expect(workspaceSource).not.toContain('GemCard')
  })
})

describe('live fixture intelligence carries visible freshness', () => {
  const callSites = [
    { source: exploreSource, label: 'Explore' },
    { source: contentSource, label: 'fixture page' },
  ]

  it.each(callSites)('$label passes lastUpdated to the workspace', ({ source }) => {
    const match = source.match(/<FixtureDecisionWorkspace[\s\S]*?\/>/)
    expect(match).toBeTruthy()
    expect(match![0]).toContain('lastUpdated=')
  })

  it('the server page preserves the service computation timestamp', () => {
    expect(pageSource).toContain('lastUpdated={data.lastUpdated}')
  })

  it('the workspace renders computation and price freshness', () => {
    expect(workspaceSource).toContain('Analysis computed')
    expect(workspaceSource).toContain('Freshest verified price')
    expect(workspaceSource).toContain('price_age_hours')
  })
})

describe('public decision copy respects model ownership', () => {
  it('names the provider view and does not claim BetGlitch AI', () => {
    for (const source of [pageSource, contentSource, workspaceSource, exploreSource]) {
      expect(source).not.toMatch(/AI[- ]powered|our AI|BetGlitch AI/i)
    }
    expect(workspaceSource).toContain('Provider model')
    expect(workspaceSource).toContain('not proof of value')
  })
})
