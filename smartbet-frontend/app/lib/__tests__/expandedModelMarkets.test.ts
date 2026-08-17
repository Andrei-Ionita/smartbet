import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { buildExpandedModelCandidates } from '../expandedModelMarkets'
import type { SportMonksOdd } from '../oddsSelection'

const quote = (input: Partial<SportMonksOdd>): SportMonksOdd => ({
  id: 1,
  fixture_id: 77,
  bookmaker_id: 2,
  bookmaker: { id: 2, name: 'Book A' },
  latest_bookmaker_update: '2026-08-15 10:00:00',
  value: '2.00',
  stopped: false,
  suspended: false,
  ...input,
})

describe('expanded model market candidates', () => {
  it('keeps full-time, half-time and first-goal probability models separate', () => {
    const service = readFileSync(resolve(process.cwd(), 'src/services/fixtureService.ts'), 'utf8')
    expect(service).toMatch(/x12Predictions\s*=\s*predictions\.filter\(\(p: any\) => p\.type_id === 237\)/)
    expect(service).not.toContain('[233, 237, 238]')
  })

  it('prices the exact 3.5 goal line and keeps it in shadow', () => {
    const candidates = buildExpandedModelCandidates(
      [{ type_id: 236, predictions: { yes: 62, no: 38 } }],
      [quote({ market_id: 7, market_description: 'Goal Line', total: '3.5', label: 'Over', value: '2.10' })],
    )
    const candidate = candidates.find((item) => item.market_type === 'over_under_3.5')

    expect(candidate?.predicted_outcome).toBe('Over 3.5')
    expect(candidate?.odds).toBe(2.10)
    expect(candidate?.expected_value).toBeCloseTo(0.302)
    expect(candidate?.validation_status).toBe('shadow')
  })

  it('maps a named half-time/full-time outcome to the canonical market', () => {
    const candidates = buildExpandedModelCandidates(
      [{
        type_id: 232,
        predictions: {
          home_home: 55, home_draw: 5, home_away: 2,
          draw_home: 10, draw_draw: 8, draw_away: 4,
          away_home: 6, away_draw: 3, away_away: 7,
        },
      }],
      [quote({
        market_id: 29,
        market_description: 'Half Time/Full Time',
        label: 'Alpha FC - Alpha FC',
        value: '2.25',
      })],
      { homeTeam: 'Alpha FC', awayTeam: 'Beta FC' },
    )
    const candidate = candidates.find((item) => item.market_type === 'half_time_full_time')

    expect(candidate?.canonical_outcome).toBe('home_home')
    expect(candidate?.odds).toBe(2.25)
  })

  it('ignores aggregate correct-score buckets and prices an exact score only', () => {
    const candidates = buildExpandedModelCandidates(
      [{ type_id: 240, predictions: { scores: { '1-0': 18, '1-1': 15, Other_1: 30 } } }],
      [quote({ market_id: 57, market_description: 'Correct Score', label: '1', name: '1-0', value: '6.00' })],
    )
    const candidate = candidates.find((item) => item.market_type === 'correct_score')

    expect(candidate?.canonical_outcome).toBe('1-0')
    expect(candidate?.probability).toBe(0.18)
    expect(candidate?.odds).toBe(6)
  })
})
