import { describe, expect, it } from 'vitest'

import {
  buildFixtureIntelligence,
  buildIntelligenceMarket,
  calculatePersonalPrice,
  formatFixtureForm,
  type IntelligenceOutcomeInput,
} from '../fixtureIntelligence'

const capturedAt = '2026-08-09T10:00:00Z'

const outcome = (
  key: string,
  probability: number | null,
  odds: number | null,
  extra: Partial<IntelligenceOutcomeInput> = {},
): IntelligenceOutcomeInput => ({
  key,
  label: key,
  provider_probability: probability,
  odds,
  bookmaker: odds ? 'Verified Book' : null,
  odds_provenance: odds ? {
    odds,
    odds_bookmaker_name: 'Verified Book',
    odds_bookmaker_id: 7,
    odds_market_id: 1,
    odds_market_description: 'Test market',
    odds_line: null,
    odds_label: key,
    odds_captured_at: capturedAt,
    odds_selection_policy: 'lower_median_v1',
    odds_bookmaker_count: 3,
    odds_min: odds - 0.1,
    odds_max: odds + 0.2,
    odds_fixture_id: 99,
    odds_entry_id: 101,
  } : null,
  price_status: odds ? 'verified' : 'unavailable',
  odds_unavailable_reason: odds ? undefined : 'no_verified_quote',
  ...extra,
})

describe('fixture intelligence market construction', () => {
  it('keeps provider, raw implied and margin-removed probabilities separate', () => {
    const market = buildIntelligenceMarket({
      key: '1x2',
      label: 'Match result',
      probability_kind: 'distribution',
      outcomes: [
        outcome('home', 0.55, 2),
        outcome('draw', 0.25, 4),
        outcome('away', 0.2, 4),
      ],
    }, new Date('2026-08-09T12:00:00Z'))

    expect(market.price_board_complete).toBe(true)
    expect(market.bookmaker_margin).toBeCloseTo(0)
    expect(market.outcomes.map((item) => item.implied_probability)).toEqual([0.5, 0.25, 0.25])
    expect(market.outcomes.map((item) => item.market_probability)).toEqual([0.5, 0.25, 0.25])
    expect(market.outcomes[0].provider_market_difference).toBeCloseTo(0.05)
    expect(market.provider_leader).toBe('home')
    expect(market.market_leader).toBe('home')
    expect(market.leader_agreement).toBe(true)
    expect(market.outcomes[0].price_age_hours).toBe(2)
    expect(market.outcomes[0].bookmaker_count).toBe(3)
  })

  it('removes overround only when the mutually exclusive board is complete', () => {
    const complete = buildIntelligenceMarket({
      key: '1x2',
      label: 'Match result',
      probability_kind: 'distribution',
      outcomes: [outcome('home', 0.5, 1.9), outcome('draw', 0.27, 3.6), outcome('away', 0.23, 4.2)],
    })
    expect(complete.bookmaker_margin).toBeGreaterThan(0)
    expect(complete.outcomes.reduce((sum, item) => sum + (item.market_probability ?? 0), 0)).toBeCloseTo(1)

    const incomplete = buildIntelligenceMarket({
      key: '1x2',
      label: 'Match result',
      probability_kind: 'distribution',
      outcomes: [outcome('home', 0.5, 1.9), outcome('draw', 0.27, null), outcome('away', 0.23, 4.2)],
    })
    expect(incomplete.price_board_complete).toBe(false)
    expect(incomplete.bookmaker_margin).toBeNull()
    expect(incomplete.outcomes.every((item) => item.market_probability === null)).toBe(true)
  })

  it('never normalises overlapping Double Chance outcomes', () => {
    const market = buildIntelligenceMarket({
      key: 'double_chance',
      label: 'Double chance',
      probability_kind: 'overlapping',
      outcomes: [outcome('1x', 0.75, 1.3), outcome('12', 0.8, 1.2), outcome('x2', 0.45, 1.8)],
    })
    expect(market.price_board_complete).toBe(false)
    expect(market.bookmaker_margin).toBeNull()
    expect(market.outcomes.every((item) => item.market_probability === null)).toBe(true)
  })

  it('states the canonical-board and non-verdict limitations', () => {
    const intelligence = buildFixtureIntelligence([{
      key: '1x2',
      label: 'Match result',
      probability_kind: 'distribution',
      outcomes: [outcome('home', 0.5, 2), outcome('draw', 0.25, 4), outcome('away', 0.25, 4)],
    }])
    expect(intelligence.data_quality.verified_prices).toBe(3)
    expect(intelligence.data_quality.complete_price_boards).toBe(1)
    expect(intelligence.data_quality.limitations).toContain(
      'canonical_board_not_single_bookmaker',
    )
    expect(intelligence.data_quality.limitations.at(-1)).toBe('reference_views_not_value_verdict')
  })
})

describe('personal fair-price calculator', () => {
  it('turns the user probability into a fair price and break-even comparison', () => {
    const result = calculatePersonalPrice(55, 2)
    expect(result?.personal_fair_odds).toBeCloseTo(1.81818)
    expect(result?.break_even_probability).toBe(0.5)
    expect(result?.probability_cushion).toBeCloseTo(0.05)
    expect(result?.price_advantage).toBeCloseTo(0.1)
    expect(result?.assessment).toBe('above_personal_price')
  })

  it('does not manufacture an assessment when no price exists', () => {
    expect(calculatePersonalPrice(55, null)?.assessment).toBe('no_price')
  })

  it('rejects impossible endpoint probabilities', () => {
    expect(calculatePersonalPrice(0, 2)).toBeNull()
    expect(calculatePersonalPrice(100, 2)).toBeNull()
    expect(calculatePersonalPrice(Number.NaN, 2)).toBeNull()
  })
})

describe('provider form normalization', () => {
  it('accepts the compact provider string', () => {
    expect(formatFixtureForm('WWDLW')).toBe('W W D L W')
  })

  it('accepts the ordered record array returned by live fixtures', () => {
    expect(formatFixtureForm([
      { fixture_id: 1, form: 'W', sort_order: 1 },
      { fixture_id: 2, form: 'L', sort_order: 2 },
    ])).toBe('W L')
  })

  it('fails closed for malformed data', () => {
    expect(formatFixtureForm([{ form: 7 }, null, 'W'])).toBeNull()
    expect(formatFixtureForm(undefined)).toBeNull()
  })
})
