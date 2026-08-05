/**
 * The activation boundary for the form heuristic.
 *
 * Repairing the parser on 2026-08-05 made a multiplier that had been stuck at
 * 1.0 for its whole production life suddenly real, which started applying an
 * unvalidated heuristic to public output. These tests pin the rule that a
 * correctness fix must not carry a behaviour change with it.
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { afterEach, describe, expect, it } from 'vitest'

import {
  formHeuristicActivationState,
  isFormHeuristicLive,
  pipelineVersion,
} from '../modelActivation'
import { calculateFormMomentum } from '../heuristics'
import { parseStandingForm } from '../providerForm'

const ROOT = join(__dirname, '..', '..', '..')
const read = (rel: string) => readFileSync(join(ROOT, rel), 'utf8')

const setFlag = (value: string | undefined) => {
  if (value === undefined) delete process.env.FORM_HEURISTIC_LIVE_ENABLED
  else process.env.FORM_HEURISTIC_LIVE_ENABLED = value
}

afterEach(() => setFlag(undefined))

describe('fails safe to disabled', () => {
  it.each([
    undefined, '', 'false', 'FALSE', 'TRUE', 'True', '1', 'yes', 'on',
    'enabled', ' true', 'true ', 'null',
  ])('%s -> disabled', (value) => {
    setFlag(value as string | undefined)
    expect(isFormHeuristicLive()).toBe(false)
    expect(formHeuristicActivationState()).toBe('shadow')
  })

  it('enables only on the exact string "true"', () => {
    setFlag('true')
    expect(isFormHeuristicLive()).toBe(true)
    expect(formHeuristicActivationState()).toBe('live')
  })
})

describe('the flag is server-only and not a browser control', () => {
  it('is never read through a NEXT_PUBLIC_ variable', () => {
    const src = read('app/lib/modelActivation.ts')
    expect(src).toContain('process.env.FORM_HEURISTIC_LIVE_ENABLED')
    expect(src).not.toContain('NEXT_PUBLIC_FORM_HEURISTIC')
    expect(src).not.toMatch(/NEXT_PUBLIC_[A-Z_]*(?:HEURISTIC|MODEL|ACTIVATION)/)
  })

  it('is only consulted from server routes, never a component', () => {
    for (const file of [
      'app/api/recommendations/route.ts',
      'app/api/internal/evidence/route.ts',
    ]) {
      expect(read(file)).toMatch(/modelActivation/)
    }
    // No client component may import it — a 'use client' file reading this
    // would ship the decision into the bundle.
    for (const file of [
      'app/components/RecommendationCard.tsx',
      'app/dashboard/page.tsx',
      'app/track-record/TrackRecordContent.tsx',
    ]) {
      expect(read(file)).not.toContain('modelActivation')
    }
  })
})

describe('public output uses Variant A while disabled', () => {
  const src = read('app/api/recommendations/route.ts')

  it('computes the shadow value but gates what reaches the public field', () => {
    expect(src).toContain('const shadowAdjustedProbability = Math.min(')
    expect(src).toContain('const adjustedProbability = isFormHeuristicLive()')
    expect(src).toContain('? shadowAdjustedProbability')
    expect(src).toContain(': bestMarket.probability')
  })

  it('still parses real form rather than disabling the parser', () => {
    expect(src).toContain('buildFormMap(standingsResults)')
    expect(src).toContain('calculateFormMomentum')
  })

  it('reproduces the pre-repair behaviour exactly when disabled', () => {
    setFlag(undefined)
    // A payload that genuinely moves the multiplier off 1.0.
    const parsed = parseStandingForm(
      ['W', 'W', 'W', 'W', 'W'].map((f, i) => ({ form: f, sort_order: i + 1 })),
    )
    const momentum = calculateFormMomentum(parsed.letters, true, true)
    expect(momentum.multiplier).not.toBe(1.0)

    const rawProbability = 0.62
    const shadow = Math.min(rawProbability * momentum.multiplier, 0.95)
    const publicValue = isFormHeuristicLive() ? shadow : rawProbability

    expect(shadow).not.toBeCloseTo(rawProbability, 5)
    // Public output equals the raw provider probability — identical to what
    // shipped while the broken parser forced the multiplier to 1.0.
    expect(publicValue).toBe(rawProbability)
  })

  it('applies the genuine value when explicitly enabled', () => {
    setFlag('true')
    const parsed = parseStandingForm(
      ['W', 'W', 'W', 'W', 'W'].map((f, i) => ({ form: f, sort_order: i + 1 })),
    )
    const momentum = calculateFormMomentum(parsed.letters, true, true)
    const rawProbability = 0.62
    const shadow = Math.min(rawProbability * momentum.multiplier, 0.95)

    expect(isFormHeuristicLive()).toBe(true)
    expect(shadow).toBeGreaterThan(rawProbability)
  })
})

describe('evidence keeps capturing Variant B while public is disabled', () => {
  const src = read('app/api/internal/evidence/route.ts')

  it('records the adjusted score regardless of activation', () => {
    expect(src).toContain('adjusted_score: isSelected && haveForm ? adjustedScore : null')
    expect(src).not.toContain('isFormHeuristicLive() ? adjustedScore')
  })

  it('stamps the activation state and a regime-specific pipeline version', () => {
    expect(src).toContain('pipeline_version: pipelineVersion()')
    expect(src).toContain('live_activation_state: formHeuristicActivationState()')
  })

  it('still refuses to fabricate a multiplier when form is missing', () => {
    expect(src).toContain('const haveForm = homeParsed.available || awayParsed.available')
    expect(src).toContain("? (haveForm ? '' : formReason)")
  })
})

describe('pipeline version distinguishes the three regimes', () => {
  it('shadow and live are separable, and neither is v1', () => {
    setFlag(undefined)
    expect(pipelineVersion()).toBe('evidence-v2-shadow')
    setFlag('true')
    expect(pipelineVersion()).toBe('evidence-v2-live')
    // evidence-v1 rows are the inert-parser era and must remain distinguishable.
    expect(pipelineVersion()).not.toBe('evidence-v1')
  })
})

describe('no unvalidated public claims were reintroduced', () => {
  it('keeps fair odds and BET/NO-BET out of the product', () => {
    for (const file of [
      'app/track-record/TrackRecordContent.tsx',
      'app/dashboard/page.tsx',
      'app/components/RecommendationCard.tsx',
    ]) {
      const src = read(file)
      expect(src).not.toMatch(/fair[_ ]odds/i)
      expect(src).not.toContain('NO_BET')
      expect(src).not.toContain('PRICE_QUALIFIES')
    }
  })

  it('keeps proprietary-model and proven-edge claims out of public copy', () => {
    for (const file of [
      'app/blog/posts/how-betglitch-works.ts',
      'app/blog/posts/value-betting-explained.ts',
      'app/blog/posts/transparent-track-records.ts',
      'app/about/page.tsx',
    ]) {
      const src = read(file)
      expect(src, file).not.toMatch(/multi-model/i)
      expect(src, file).not.toMatch(/consensus (forecast|probabilit|metric)/i)
      expect(src, file).not.toMatch(/proprietary (model|algorithm)/i)
      // Match the CLAIM, not the disclaimer. "not a calibrated probability"
      // is the correction we deliberately added and must survive.
      expect(src, file).not.toMatch(/(?:our|a|the)\s+calibrated probabilit/i)
      expect(src, file).not.toMatch(/(?<!not )proven edge/i)
      expect(src, file).not.toMatch(/mathematical edge/i)
      expect(src, file).not.toMatch(/our models?\s+(?:see|assign|agree)/i)
    }
  })
})

describe('the public response leaks no shadow or activation data', () => {
  const src = read('app/api/recommendations/route.ts')

  // The response object literal, from the push that builds a recommendation to
  // the end of the scoring stage. Anything emitted here reaches the browser.
  const responseBlock = src.slice(
    src.indexOf('allRecommendations.push({'),
    src.indexOf('scoredRecommendations.sort('),
  )

  it.each([
    'shadow_adjusted_probability',
    'form_multiplier',
    'form_inputs',
    'live_activation',
    'FORM_HEURISTIC_LIVE_ENABLED',
    'calibration_version',
    'calibrated_probability',
    'conservative_probability',
    'fair_odds',
    'minimum_acceptable_odds',
    'decision_status',
    'evidence_tier',
    'NO_BET',
    'PRICE_QUALIFIES',
    'INSUFFICIENT_CALIBRATION',
  ])('never emits %s', (field) => {
    expect(responseBlock).not.toContain(field)
  })

  it('emits no form_adjustment block at all', () => {
    expect(src).not.toContain('form_adjustment:')
    expect(responseBlock).not.toContain('home_form')
    expect(responseBlock).not.toContain('away_form')
  })

  it('does not leak activation state through adjustments_applied', () => {
    // This used to read `formMultiplier !== 1.0 || ...`, which reveals whether
    // the heuristic moved the number even without naming it.
    expect(src).toContain('adjustments_applied: valueZone.scorePenalty > 0')
    expect(src).not.toContain('adjustments_applied: formMultiplier !== 1.0')
  })

  it('still computes Variant B internally for parity', () => {
    // Containment must not become deletion — the parity path stays.
    expect(src).toContain('const shadowAdjustedProbability = Math.min(')
    expect(src).toContain('calculateFormMomentum')
  })

  it('keeps the public value on Variant A', () => {
    expect(src).toContain('const adjustedProbability = isFormHeuristicLive()')
    expect(src).toContain(': bestMarket.probability')
  })
})

describe('the internal evidence feed still carries Variant B', () => {
  const src = read('app/api/internal/evidence/route.ts')

  it.each([
    'form_multiplier',
    'form_inputs',
    'adjusted_score',
    'cap_applied',
    'variant_b_available',
    'variant_b_missing_reason',
    'live_activation_state',
  ])('emits %s', (field) => {
    expect(src).toContain(field)
  })

  it('remains authenticated and fail-closed', () => {
    expect(src).toContain("process.env.INTERNAL_API_SECRET")
    expect(src).toContain("request.headers.get('x-internal-auth')")
    expect(src).toContain('{ status: 401 }')
    expect(src).toContain('{ status: 503 }')
  })
})
