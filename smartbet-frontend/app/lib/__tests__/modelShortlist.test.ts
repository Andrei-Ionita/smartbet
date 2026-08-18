import { describe, expect, it } from 'vitest'

import {
  buildModelShortlistCandidate,
  compareModelShortlist,
  toPublicModelShortlistItem,
} from '../modelShortlist'
import type { StrategyEvaluation } from '../providerStrategy'

const evaluation = (overrides: Partial<StrategyEvaluation> = {}): StrategyEvaluation => ({
  eligible: false,
  rejectionReasons: ['provider_value_bet_missing'],
  fixturePredictable: true,
  leaguePerformance: {
    marketKey: 'fulltime_result', historicalLogLoss: null, hitRatio: null,
    predictability: null, predictivePower: null, currentLogLoss: null,
  },
  valueBet: null,
  crossMarket: {
    correctScoreOutcome: 'home', correctScoreVector: null,
    doubleChanceSupportsSelection: null, leadingDoubleChance: null,
  },
  fairOddsBuffer: null,
  relativePriceSpread: 0.10,
  priceAgeHours: 2,
  ...overrides,
})

const provenance = {
  odds: 1.9, odds_market_id: 1, odds_market_description: 'Fulltime Result',
  odds_line: null, odds_label: 'Home', odds_bookmaker_id: 2,
  odds_bookmaker_name: 'Book', odds_bookmaker_count: 3,
  odds_min: 1.84, odds_max: 1.96, odds_captured_at: '2026-08-18 10:00:00',
  odds_fixture_id: 1, odds_entry_id: 2, odds_selection_policy: 'lower_median_v1',
}

const input = (strategyEvaluation = evaluation()) => ({
  fixtureId: 1, homeTeam: 'Home', awayTeam: 'Away', league: 'League',
  kickoff: '2099-08-18 20:00:00', predictedOutcome: 'Home',
  signalStrength: 0.62, signalGap: 0.14, odds: 1.9,
  oddsProvenance: provenance, strategyEvaluation,
})

describe('model shortlist', () => {
  it('admits a clear, predictable signal with a current multi-bookmaker price', () => {
    const candidate = buildModelShortlistCandidate(input())
    expect(candidate).not.toBeNull()
    const publicItem = toPublicModelShortlistItem(candidate!)
    expect(publicItem.leading_selection).toBe('Home')
    expect(publicItem.why_shortlisted.join(' ')).toContain('3 bookmakers')
    expect(publicItem.why_not_gem.join(' ')).toContain('model-versus-price')
    expect(JSON.stringify(publicItem)).not.toContain('strategy_evaluation')
  })

  it('rejects thin prices, weak separation and two explicit contradictions', () => {
    expect(buildModelShortlistCandidate({
      ...input(), signalGap: 0.04,
    })).toBeNull()
    expect(buildModelShortlistCandidate({
      ...input(), oddsProvenance: { ...provenance, odds_bookmaker_count: 1 },
    })).toBeNull()
    expect(buildModelShortlistCandidate(input(evaluation({
      crossMarket: {
        correctScoreOutcome: 'away', correctScoreVector: null,
        doubleChanceSupportsSelection: false, leadingDoubleChance: 'x2',
      },
    })))).toBeNull()
  })

  it('ranks aligned value evidence and supporting models before raw signal size', () => {
    const plain = buildModelShortlistCandidate(input())!
    const aligned = buildModelShortlistCandidate(input(evaluation({
      valueBet: {
        active: true, outcome: 'home', fairOdds: 1.8,
        offeredOdds: 1.9, bookmaker: 'Book', stake: null,
      },
    })))!
    expect(compareModelShortlist(aligned, plain)).toBeLessThan(0)
  })
})
