import { describe, it, expect } from 'vitest'
import { readFileSync } from 'fs'
import { join } from 'path'

import {
  RANKING_POLICY, RANKING_POLICY_CANONICAL, RANKING_VERSION,
} from '../rankingPolicy'

/**
 * The declared policy must MIRROR the engine, or the version is a lie.
 *
 * A reviewer (2026-08-08) noted that BetGlitch calls publication a "fixed,
 * pre-registered rule" while the About page admits the selection logic keeps
 * changing — with nothing identifying which rule produced a given commitment.
 * Stamping a version fixes that only if the declared parameters actually match
 * the code. These tests are that link: change a threshold in the engine
 * without updating the policy and this suite fails.
 */

const root = join(__dirname, '..', '..', '..')
const read = (p: string) => readFileSync(join(root, p), 'utf-8').replace(/\r\n/g, '\n')

const ENGINE = read('app/api/recommendations/engine.ts')
const HEURISTICS = read('app/lib/heuristics.ts')

describe('the declared policy mirrors the engine', () => {
  it('confidence floor matches engine.ts', () => {
    expect(ENGINE).toContain(
      `const CONFIDENCE_FLOOR = ${RANKING_POLICY.confidenceFloor}`)
  })

  it('minimum market score matches engine.ts', () => {
    expect(ENGINE).toContain(
      `bestMarket.market_score < ${RANKING_POLICY.minimumMarketScore}`)
  })

  it('minimum gaps match engine.ts', () => {
    expect(ENGINE).toContain(
      `outcome === 'draw' ? ${RANKING_POLICY.minimumGap.draw} : ${RANKING_POLICY.minimumGap.other}`)
  })

  it('market score weights match heuristics.ts', () => {
    const { gap, expectedValue, confidence } = RANKING_POLICY.marketScore.weights
    expect(HEURISTICS).toContain(
      `(normalizedGap * ${gap}) + (normalizedEV * ${expectedValue}) + (normalizedConf * ${confidence})`)
  })

  it('form recency weights match heuristics.ts', () => {
    // Compared as NUMBERS: heuristics.ts writes 0.30 where the policy writes
    // 0.3, and a string compare would fail on formatting while passing on a
    // genuinely changed weight — exactly backwards.
    const declared = HEURISTICS.match(/const weights = \[([^\]]+)\]/)
    expect(declared, 'weights array not found in heuristics.ts').toBeTruthy()
    const actual = declared![1].split(',').map((n) => parseFloat(n.trim()))
    expect(actual).toEqual([...RANKING_POLICY.formMomentum.recencyWeights])
  })

  it('every market named in the policy is scored by the engine', () => {
    for (const market of RANKING_POLICY.markets) {
      expect(ENGINE).toContain(market)
    }
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
    // Sorted keys at every level: `confidenceFloor` must precede `markets`.
    expect(RANKING_POLICY_CANONICAL.indexOf('"confidenceFloor"'))
      .toBeLessThan(RANKING_POLICY_CANONICAL.indexOf('"markets"'))
  })

  it('covers every ranking-relevant parameter', () => {
    for (const key of [
      'confidenceFloor', 'minimumGap', 'minimumMarketScore', 'marketScore',
      'formMomentum', 'markets', 'selection',
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
    // And does not oversell what the parameters achieve.
    expect(page).toContain('0.554')
    expect(page).toContain('not a probability')
  })
})
