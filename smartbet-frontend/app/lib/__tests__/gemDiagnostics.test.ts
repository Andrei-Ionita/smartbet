import { describe, expect, it } from 'vitest'

import {
  categorizeGemRejectionReason,
  emptyGemRejectionCounts,
  publicGemRejectionBreakdown,
  recordGemRejection,
} from '../gemDiagnostics'

describe('Gem rejection diagnostics', () => {
  it.each([
    ['fixture_predictability_missing', 'reliability'],
    ['league_predictive_power_down', 'reliability'],
    ['provider_value_bet_inactive', 'provider_value'],
    ['correct_score_consensus_missing', 'cross_market_consensus'],
    ['double_chance_consensus_not_aligned', 'cross_market_consensus'],
    ['cross_market_consensus_contradiction', 'cross_market_consensus'],
    ['canonical_price_buffer_too_small', 'price_quality'],
    ['insufficient_bookmaker_coverage', 'price_quality'],
    ['price_dispersion_too_wide', 'price_quality'],
  ])('groups %s as %s', (reason, category) => {
    expect(categorizeGemRejectionReason(reason)).toBe(category)
  })

  it('counts one fixture once in each affected category', () => {
    const counts = emptyGemRejectionCounts()
    recordGemRejection(counts, [
      'provider_value_bet_missing',
      'provider_value_bet_inactive',
      'price_stale_or_timestamp_missing',
    ])
    recordGemRejection(counts, ['provider_value_bet_not_aligned'])

    expect(counts.provider_value).toBe(2)
    expect(counts.price_quality).toBe(1)
  })

  it('publishes only aggregate, non-negative categories', () => {
    const breakdown = publicGemRejectionBreakdown(-3, {
      ...emptyGemRejectionCounts(),
      reliability: 4,
    })

    expect(breakdown).toEqual([
      { code: 'signal_or_verified_price', fixtures_affected: 0 },
      { code: 'reliability', fixtures_affected: 4 },
      { code: 'provider_value', fixtures_affected: 0 },
      { code: 'cross_market_consensus', fixtures_affected: 0 },
      { code: 'price_quality', fixtures_affected: 0 },
    ])
  })
})
