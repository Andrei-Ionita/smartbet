import { describe, expect, it } from 'vitest'
import { readFileSync } from 'fs'
import { join } from 'path'

import {
  RANKING_POLICY, RANKING_POLICY_CANONICAL, RANKING_VERSION,
} from '../rankingPolicy'

const root = join(__dirname, '..', '..', '..')
const read = (p: string) => readFileSync(join(root, p), 'utf-8').replace(/\r\n/g, '\n')

const ENGINE = read('app/api/recommendations/engine.ts')
const STRATEGY = read('app/lib/providerStrategy.ts')

describe('the declared policy mirrors the engine', () => {
  it('confidence floor matches engine.ts', () => {
    expect(ENGINE).toContain(
      `const CONFIDENCE_FLOOR = ${RANKING_POLICY.confidenceFloor}`)
  })

  it('minimum gaps match engine.ts', () => {
    expect(ENGINE).toContain(
      `outcome === 'draw' ? ${RANKING_POLICY.minimumGap.draw} : ${RANKING_POLICY.minimumGap.other}`)
  })

  it('uses the provider-native strategy at the selection boundary', () => {
    expect(ENGINE).toContain('evaluateValueStrategy')
    expect(ENGINE).toContain('compareGemStrategy')
    expect(ENGINE).toContain('VALUE_STRATEGY_POLICY.maximumSelections')
  })

  it('declares every material quality, value and price gate', () => {
    for (const key of [
      'requirePredictableFixture', 'rejectedLeaguePredictability',
      'requireActiveAlignedValueBet', 'minimumFairOddsBuffer',
      'requireCorrectScoreAgreement', 'requireDoubleChanceSupport',
      'minimumBookmakers', 'maximumRelativePriceSpread',
      'maximumPriceAgeHours', 'maximumSelections',
    ]) {
      expect(STRATEGY).toContain(key)
    }
  })

  it('only makes 1x2 eligible while all markets continue in evidence', () => {
    expect([...RANKING_POLICY.markets]).toEqual(['1x2'])
    expect(ENGINE).toContain("m.market_type === '1x2'")
  })
})

describe('the version is derived, not declared', () => {
  it('has the documented shape', () => {
    expect(RANKING_VERSION).toMatch(/^rank-v\d+-[0-9a-f]{16}$/)
  })

  it('is stable across runs for an unchanged policy', () => {
    expect(RANKING_VERSION).toBe(RANKING_VERSION)
  })

  it('canonicalises keys so formatting cannot change the version', () => {
    expect(RANKING_POLICY_CANONICAL.indexOf('"confidenceFloor"'))
      .toBeLessThan(RANKING_POLICY_CANONICAL.indexOf('"markets"'))
  })

  it('covers every ranking-relevant parameter', () => {
    for (const key of [
      'confidenceFloor', 'minimumGap', 'fixturePredictableRequired',
      'rejectedLeaguePredictability', 'rejectedPredictivePower',
      'activeAlignedValueBetRequired', 'minimumFairOddsBuffer',
      'correctScoreAgreementRequired', 'doubleChanceSupportRequired',
      'maximumCrossMarketContradictions',
      'minimumBookmakers', 'maximumRelativePriceSpread',
      'maximumPriceAgeHours', 'maximumSelections', 'markets', 'selection',
      'gemProbabilitySource', 'gemPayoutSource', 'gemPrimaryRanking',
    ]) {
      expect(RANKING_POLICY_CANONICAL).toContain(`"${key}"`)
    }
  })
})

describe('the version reaches the record', () => {
  it('the engine sends it with every run', () => {
    expect(ENGINE).toContain('ranking_version: RANKING_VERSION')
  })

  it('the proof page shows which rule produced the selection', () => {
    const proof = read('app/proof/_shared/ProofPageBody.tsx')
    expect(proof).toContain('label="Ranking version"')
  })

  it('the methodology page publishes the parameters themselves', () => {
    const page = read('app/methodology/page.tsx')
    expect(page).toContain('RANKING_VERSION')
    expect(page).toContain('Confidence floor')
    expect(page).toContain('Selection rule')
    expect(page).toContain('not a guarantee')
  })
})
