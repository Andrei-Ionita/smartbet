import { describe, expect, it } from 'vitest'

import {
  compareGemStrategy,
  crossMarketConsensus,
  evaluateValueStrategy,
  fixturePredictability,
  gemMetrics,
  leagueMarketPerformance,
  nativeValueBet,
} from '../providerStrategy'

const performance = {
  data: [
    { type_id: 241, data: { fulltime_result: -1.01 } },
    { type_id: 242, data: { fulltime_result: 0.58 } },
    { type_id: 243, data: { fulltime_result: 'high' } },
    { type_id: 244, data: { fulltime_result: 'up' } },
    { type_id: 245, data: { fulltime_result: -0.94 } },
  ],
}

const predictions = [
  {
    type_id: 33,
    predictions: {
      bet: '1', bookmaker: 'example', odd: 2.0, fair_odd: 1.80,
      stake: 0.8, is_value: true,
    },
  },
  {
    type_id: 240,
    predictions: {
      scores: { '1-0': 30, '2-0': 20, '1-1': 20, '0-1': 10, Other_1: 12, Other_X: 5, Other_2: 3 },
    },
  },
  {
    type_id: 239,
    predictions: { draw_home: 70, draw_away: 45, home_away: 60 },
  },
]

const provenance = {
  odds: 1.90,
  odds_market_id: 1,
  odds_market_description: 'Fulltime Result',
  odds_line: null,
  odds_label: 'Home',
  odds_bookmaker_id: 2,
  odds_bookmaker_name: 'Book',
  odds_bookmaker_count: 5,
  odds_min: 1.84,
  odds_max: 1.98,
  odds_captured_at: '2026-08-09 10:00:00',
  odds_fixture_id: 123,
  odds_entry_id: 456,
  odds_selection_policy: 'lower_median_v1',
}

describe('provider metadata', () => {
  it('finds predictable in the relation-array shape', () => {
    expect(fixturePredictability([
      { type_id: 35, values: { neutral: false } },
      { type_id: 37072, values: { predictable: true } },
    ])).toBe(true)
  })

  it('does not turn missing metadata into positive evidence', () => {
    expect(fixturePredictability([{ values: { computable: true } }])).toBeNull()
  })
})

describe('native provider signals', () => {
  it('parses value-bet direction and requires the active flag separately', () => {
    expect(nativeValueBet(predictions)).toEqual({
      active: true,
      outcome: 'home',
      fairOdds: 1.8,
      offeredOdds: 2,
      bookmaker: 'example',
      stake: 0.8,
    })
    expect(nativeValueBet([{
      type: { developer_name: 'VALUEBET' },
      predictions: { bet: 'x', odd: 3.2, fair_odd: 3.0, is_value: false },
    }])?.active).toBe(false)
  })

  it('parses league metrics by semantic type id and market', () => {
    expect(leagueMarketPerformance(performance, '1x2')).toEqual({
      marketKey: 'fulltime_result',
      historicalLogLoss: -1.01,
      hitRatio: 0.58,
      predictability: 'high',
      predictivePower: 'up',
      currentLogLoss: -0.94,
    })
  })

  it('derives independent cross-market support without inventing a score', () => {
    const result = crossMarketConsensus(predictions, 'home')
    expect(result.correctScoreOutcome).toBe('home')
    expect(result.correctScoreVector?.home).toBeCloseTo(0.62)
    expect(result.leadingDoubleChance).toBe('1x')
    expect(result.doubleChanceSupportsSelection).toBe(true)
  })
})

describe('value strategy', () => {
  const base = {
    market: '1x2' as const,
    predictedOutcome: 'Home',
    metadata: [{ type_id: 37072, values: { predictable: true } }],
    predictions,
    leaguePerformancePayload: performance,
    odds: 1.90,
    oddsProvenance: provenance,
    evaluatedAt: new Date('2026-08-09T12:00:00Z'),
  }

  it('accepts only mutually confirming, current evidence', () => {
    const result = evaluateValueStrategy(base)
    expect(result.eligible).toBe(true)
    expect(result.rejectionReasons).toEqual([])
    expect(result.fairOddsBuffer).toBeCloseTo(1.9 / 1.8 - 1)
    expect(gemMetrics(result).providerBaselineOdds).toBe(1.8)
    expect(gemMetrics(result).verifiedOdds).toBeCloseTo(1.9)
    expect(gemMetrics(result).providerImpliedProbability).toBeCloseTo(1 / 1.8)
  })

  it('balances probability and payout instead of favouring the biggest price', () => {
    const safer = evaluateValueStrategy({
      ...base,
      odds: 1.68,
      predictions: predictions.map((row) => row.type_id === 33
        ? { ...row, predictions: { ...row.predictions, fair_odd: 1.6, odd: 1.68 } }
        : row),
      oddsProvenance: { ...provenance, odds: 1.68, odds_min: 1.64, odds_max: 1.72 },
    })
    const longer = evaluateValueStrategy({
      ...base,
      odds: 3.3,
      predictions: predictions.map((row) => row.type_id === 33
        ? { ...row, predictions: { ...row.predictions, fair_odd: 3, odd: 3.3 } }
        : row),
      oddsProvenance: { ...provenance, odds: 3.3, odds_min: 3.2, odds_max: 3.4 },
    })

    expect(safer.eligible).toBe(true)
    expect(longer.eligible).toBe(true)
    expect(gemMetrics(longer).verifiedPriceAdvantage)
      .toBeGreaterThan(gemMetrics(safer).verifiedPriceAdvantage ?? 0)
    expect(gemMetrics(safer).probabilityPayoutBalance)
      .toBeGreaterThan(gemMetrics(longer).probabilityPayoutBalance ?? 0)
    expect(compareGemStrategy(safer, longer)).toBeLessThan(0)
  })

  it('rejects a value bet pointing at the other team', () => {
    const result = evaluateValueStrategy({
      ...base,
      predictions: [{
        type_id: 33,
        predictions: { bet: '2', odd: 2, fair_odd: 1.8, is_value: true },
      }],
    })
    expect(result.eligible).toBe(false)
    expect(result.rejectionReasons).toContain('provider_value_bet_not_aligned')
  })

  it('rejects missing league evidence, stale prices and thin books', () => {
    const result = evaluateValueStrategy({
      ...base,
      leaguePerformancePayload: [],
      oddsProvenance: {
        ...provenance,
        odds_bookmaker_count: 1,
        odds_captured_at: '2026-08-08 00:00:00',
      },
    })
    expect(result.eligible).toBe(false)
    expect(result.rejectionReasons).toEqual(expect.arrayContaining([
      'league_predictability_missing',
      'league_predictive_power_missing',
      'insufficient_bookmaker_coverage',
      'price_stale_or_timestamp_missing',
    ]))
  })

  it('does not let an unrelated value bet qualify BTTS or totals', () => {
    const result = evaluateValueStrategy({ ...base, market: 'btts' })
    expect(result.eligible).toBe(false)
    expect(result.rejectionReasons).toContain('market_not_value_strategy')
  })
})
