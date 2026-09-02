import { describe, expect, it } from 'vitest'
import { buildAsianHandicapResearchCandidates } from '../asianHandicapResearch'
import type { SportMonksOdd } from '../oddsSelection'

const ah = (input: Partial<SportMonksOdd>): SportMonksOdd => ({
  id: 1,
  fixture_id: 10,
  market_id: 6,
  market_description: 'Asian Handicap',
  label: 'Home',
  handicap: '-1.5',
  value: '2.00',
  bookmaker_id: 2,
  bookmaker: { id: 2, name: 'Book A' },
  latest_bookmaker_update: '2026-08-15 10:00:00',
  stopped: false,
  suspended: false,
  ...input,
})

describe('Asian handicap shadow research', () => {
  it('calculates a conservative settlement-aware edge from score probabilities', () => {
    const candidates = buildAsianHandicapResearchCandidates(
      [{ type_id: 240, predictions: { scores: { '2-0': 60, '1-0': 20, '0-0': 20 } } }],
      [ah({})],
      { homeTeam: 'Alpha', awayTeam: 'Beta' },
    )
    const candidate = candidates[0]

    expect(candidate.label).toBe('Alpha -1.5')
    expect(candidate.expected_return_lower).toBeCloseTo(0.2)
    expect(candidate.expected_return_upper).toBeCloseTo(0.2)
    expect(candidate.robust_positive_edge).toBe(true)
    expect(candidate.validation_status).toBe('shadow')
    expect(candidate.price_provenance).toMatchObject({
      market_id: 6,
      odds_entry_id: 1,
      bookmaker_id: 2,
      bookmaker_name: 'Book A',
    })
  })

  it('settles quarter lines as two half stakes', () => {
    const candidates = buildAsianHandicapResearchCandidates(
      [{ type_id: 240, predictions: { scores: { '2-0': 60, '1-0': 20, '0-0': 20 } } }],
      [ah({ handicap: '-1.25' })],
    )

    // -1.25 splits into -1.0 and -1.5: a one-goal win is a half loss.
    expect(candidates[0].expected_return_lower).toBeCloseTo(0.3)
  })

  it('keeps unknown winning margins as bounds instead of inventing a score', () => {
    const candidates = buildAsianHandicapResearchCandidates(
      [{ type_id: 240, predictions: { scores: { Other_1: 100 } } }],
      [ah({ handicap: '-2.5' })],
    )

    expect(candidates[0].expected_return_lower).toBe(-1)
    expect(candidates[0].expected_return_upper).toBe(1)
    expect(candidates[0].robust_positive_edge).toBe(false)
  })

  it('rejects anonymous, stale-shape and suspended quotes', () => {
    const prediction = [{ type_id: 240, predictions: { scores: { '1-0': 100 } } }]
    const candidates = buildAsianHandicapResearchCandidates(prediction, [
      ah({ bookmaker: null }),
      ah({ latest_bookmaker_update: null }),
      ah({ suspended: true }),
    ])
    expect(candidates).toEqual([])
  })

  it('rejects overflowing score mass instead of manufacturing impossible EV', () => {
    const candidates = buildAsianHandicapResearchCandidates(
      [{ type_id: 240, predictions: { scores: { '2-0': 80, '1-0': 60 } } }],
      [ah({})],
    )

    expect(candidates).toEqual([])
  })

  it('normalises only small provider rounding differences', () => {
    const candidate = buildAsianHandicapResearchCandidates(
      [{ type_id: 240, predictions: { scores: { '2-0': 60, '1-0': 20, '0-0': 21 } } }],
      [ah({})],
    )[0]

    expect(candidate.model_mass).toBeCloseTo(1.01)
    expect(candidate.expected_return_lower).toBeLessThanOrEqual(candidate.odds - 1)
  })
})
