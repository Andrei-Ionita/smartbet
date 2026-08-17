import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..', '..')
const read = (path: string) => readFileSync(join(ROOT, path), 'utf8')

describe('Strategies Lab stays shadow-only', () => {
  it('captures Asian Handicap candidates through the authenticated evidence feed', () => {
    const internal = read('app/api/internal/evidence/route.ts')
    expect(internal).toContain('buildAsianHandicapResearchCandidates')
    expect(internal).toContain("strategy_key: 'asian-handicap-score-distribution'")
    expect(internal).toContain('strategy_candidates: strategyCandidates')
    expect(internal).toContain('buildAsianGoalLineResearchCandidates')
    expect(internal).toContain('buildTeamTotalResearchCandidates')
    expect(internal).toContain("market: 'correct_score'")
  })

  it('does not expose lab candidates through public fixture JSON', () => {
    const fixture = read('src/services/fixtureService.ts')
    expect(fixture).not.toContain('asian_handicap_research')
    expect(fixture).not.toContain('buildAsianHandicapResearchCandidates')
  })

  it('reads only the worker snapshot for public recommendation JSON', () => {
    const route = read('app/api/recommendations/route.ts')
    expect(route).toContain('loadCachedGemFeed')
    expect(route).not.toContain('buildRecommendationPayload')
    expect(route).not.toContain('market_research')
    expect(route).not.toContain('result.envelope')
  })
})
