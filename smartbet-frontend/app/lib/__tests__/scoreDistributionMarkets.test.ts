import { describe, expect, it } from 'vitest'
import {
  buildAsianGoalLineResearchCandidates,
  buildTeamTotalResearchCandidates,
} from '../scoreDistributionMarkets'
import type { SportMonksOdd } from '../oddsSelection'

const odd = (input: Partial<SportMonksOdd>): SportMonksOdd => ({
  id: 1,
  fixture_id: 10,
  market_id: 7,
  market_description: 'Goal Line',
  label: 'Over',
  name: 'Over',
  total: '1.5',
  value: '2.00',
  bookmaker_id: 2,
  bookmaker: { id: 2, name: 'Book A' },
  latest_bookmaker_update: '2026-08-15 10:00:00',
  stopped: false,
  suspended: false,
  ...input,
})

const distribution = [{
  type_id: 240,
  predictions: { scores: { '2-0': 60, '1-0': 20, '0-0': 20 } },
}]

describe('score-distribution market research', () => {
  it('prices a whole/half Asian goal line with exact settlement', () => {
    const candidate = buildAsianGoalLineResearchCandidates(
      distribution, [odd({})],
    )[0]

    expect(candidate.strategy_key).toBe('asian-goal-line-score-distribution')
    expect(candidate.label).toBe('Over 1.5')
    expect(candidate.expected_return_lower).toBeCloseTo(0.2)
    expect(candidate.expected_return_upper).toBeCloseTo(0.2)
  })

  it('settles a quarter goal line as two equal half stakes', () => {
    const candidate = buildAsianGoalLineResearchCandidates(
      [{ type_id: 240, predictions: { scores: { '2-0': 100 } } }],
      [odd({ total: '2.0, 2.5' })],
    )[0]

    expect(candidate.handicap).toBe(2.25)
    expect(candidate.expected_return_lower).toBeCloseTo(-0.5)
  })

  it('derives home team totals without assigning invented Other scores', () => {
    const candidate = buildTeamTotalResearchCandidates(
      distribution,
      [odd({
        market_id: 86,
        market_description: 'Team Total Goals',
        label: '1',
        total: 'Over 1.5',
      })],
      { homeTeam: 'Alpha', awayTeam: 'Beta' },
    )[0]

    expect(candidate.strategy_key).toBe('team-total-score-distribution')
    expect(candidate.label).toBe('Alpha Over 1.5')
    expect(candidate.expected_return_lower).toBeCloseTo(0.2)
  })

  it('keeps an unknown losing-team goal count as conservative bounds', () => {
    const candidate = buildTeamTotalResearchCandidates(
      [{ type_id: 240, predictions: { scores: { Other_1: 100 } } }],
      [odd({
        market_id: 86,
        market_description: 'Team Total Goals',
        label: '2',
        total: 'Over 3.5',
      })],
    )[0]

    expect(candidate.expected_return_lower).toBe(-1)
    expect(candidate.expected_return_upper).toBe(1)
    expect(candidate.robust_positive_edge).toBe(false)
  })
})
