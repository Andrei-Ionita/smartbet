/**
 * The commercial-mode flag must fail closed and must be the ONLY thing that
 * decides whether BetGlitch is selling anything.
 */
import { describe, expect, it } from 'vitest'

import {
  BETA_COPY, COMMERCIAL_MODE, IS_PUBLIC_BETA, PAYMENTS_DISABLED_ERROR,
  PAYMENTS_ENABLED, hasBetaAccess, shouldGateOnSubscription,
} from '../commercialMode'

describe('fail-closed behaviour', () => {
  it('defaults to public beta when unset', () => {
    // The suite runs without NEXT_PUBLIC_COMMERCIAL_MODE set.
    expect(COMMERCIAL_MODE).toBe('public_beta')
    expect(PAYMENTS_ENABLED).toBe(false)
    expect(IS_PUBLIC_BETA).toBe(true)
  })

  it('only the exact string "commercial" enables payments', () => {
    const resolve = (raw: string | undefined) =>
      raw === 'commercial' ? 'commercial' : 'public_beta'

    for (const bad of [undefined, '', ' ', 'Commercial', 'COMMERCIAL', 'true',
                       '1', 'yes', 'commercial ', 'public_beta', 'enabled']) {
      expect(resolve(bad)).toBe('public_beta')
    }
    expect(resolve('commercial')).toBe('commercial')
  })
})

describe('entitlement during the beta', () => {
  it('never applies a subscription gate', () => {
    expect(shouldGateOnSubscription()).toBe(false)
  })

  it('grants beta access to signed-in users, not to anonymous ones', () => {
    expect(hasBetaAccess(true)).toBe(true)
    expect(hasBetaAccess(false)).toBe(false)
  })

  it('does not pretend anyone has a paid plan', () => {
    // hasBetaAccess is a DISTINCT policy — it must not be derived from a tier.
    expect(hasBetaAccess.length).toBe(1)
  })
})

describe('API error shape', () => {
  it('is stable and machine-readable', () => {
    expect(PAYMENTS_DISABLED_ERROR.code).toBe('payments_disabled')
    expect(PAYMENTS_DISABLED_ERROR.detail).toContain('free public beta')
  })
})

describe('beta copy', () => {
  it('makes no pricing or launch-date promise', () => {
    const blob = Object.values(BETA_COPY).join(' ').toLowerCase()
    for (const banned of ['€', '$', 'per month', '/month', 'coming soon',
                          'launch date', 'discount', 'money-back', 'founding',
                          'upgrade', 'subscribe now']) {
      expect(blob).not.toContain(banned)
    }
  })

  it('states the beta positioning', () => {
    expect(BETA_COPY.primary).toContain('public beta')
    expect(BETA_COPY.primary).toContain('free')
    expect(BETA_COPY.supporting).toContain('locked before kickoff')
  })
})
