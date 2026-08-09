import { VALUE_STRATEGY_POLICY } from './providerStrategy'

/**
 * THE declared ranking policy, and a version derived from it.
 *
 * WHY
 * ---
 * A reviewer (2026-08-08) made a point that undermines the whole record:
 * BetGlitch calls publication a "fixed, pre-registered rule", but nothing
 * identified WHICH rule produced a given commitment. The About page even says
 * the selection logic keeps changing as we learn. So a record accumulated over
 * months would silently blend several different systems, and its aggregate
 * performance would mean nothing in particular.
 *
 * Every commitment must therefore name the exact ranking policy that produced
 * it. `model_version` on the snapshot and the claim carries this string, and
 * that field is already inside the integrity hash — so the policy stamp is
 * tamper-evident for free, with no migration and no rewriting of history.
 *
 * DERIVED, NOT DECLARED
 * ---------------------
 * The version is a hash of the parameters below, not a number someone
 * remembers to bump. Change a threshold and the version changes with it; forget
 * to update this file when the engine changes and the mismatch is a bug this
 * module cannot hide — which is why the values here must mirror the engine's
 * literals exactly. `rankingPolicy.test.ts` asserts that correspondence
 * against engine.ts and providerStrategy.ts.
 */

/**
 * The parameters that decide WHICH outcome BetGlitch surfaces.
 *
 * Only ranking-relevant values belong here. Cosmetic or transport concerns
 * must not be included, or the version would churn without the selection
 * behaviour having changed at all.
 */
export const RANKING_POLICY = {
  policy: 'betglitch-ranking',
  /** Bumped by hand only for a deliberate redesign, not for tuning. */
  generation: VALUE_STRATEGY_POLICY.generation,

  /** Markets eligible for a public value selection in this generation. */
  markets: VALUE_STRATEGY_POLICY.eligibleMarkets,

  /** A market qualifies only if its leading outcome clears this probability. */
  confidenceFloor: 0.55,

  /** Minimum probability gap to the next outcome, per market shape. */
  minimumGap: { draw: 0.15, other: 0.12 },

  /** Provider quality, native value and canonical-price gates. */
  fixturePredictableRequired: VALUE_STRATEGY_POLICY.requirePredictableFixture,
  allowedLeaguePredictability: VALUE_STRATEGY_POLICY.leaguePredictability,
  rejectedPredictivePower: VALUE_STRATEGY_POLICY.rejectedPredictivePower,
  activeAlignedValueBetRequired: VALUE_STRATEGY_POLICY.requireActiveAlignedValueBet,
  correctScoreAgreementRequired: VALUE_STRATEGY_POLICY.requireCorrectScoreAgreement,
  doubleChanceSupportRequired: VALUE_STRATEGY_POLICY.requireDoubleChanceSupport,
  minimumFairOddsBuffer: VALUE_STRATEGY_POLICY.minimumFairOddsBuffer,
  minimumBookmakers: VALUE_STRATEGY_POLICY.minimumBookmakers,
  maximumRelativePriceSpread: VALUE_STRATEGY_POLICY.maximumRelativePriceSpread,
  maximumPriceAgeHours: VALUE_STRATEGY_POLICY.maximumPriceAgeHours,
  maximumSelections: VALUE_STRATEGY_POLICY.maximumSelections,

  /** How eligible selections are ordered; no synthetic quality probability. */
  selection:
    'league predictability, predictive-power trend, fair-odds buffer, hit ratio, then price dispersion',
} as const

/**
 * Canonical JSON: keys sorted at every level, so an equivalent policy always
 * hashes identically regardless of how it was written.
 */
function canonicalise(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalise).join(',')}]`
  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>)
      .sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0))
      .map(([k, v]) => `${JSON.stringify(k)}:${canonicalise(v)}`)
    return `{${entries.join(',')}}`
  }
  return JSON.stringify(value)
}

/**
 * FNV-1a, 64-bit, via BigInt.
 *
 * Deliberately not node:crypto — this module is imported by both server
 * routes and a server-rendered page, and a dependency-free pure function
 * cannot break in any runtime. The hash only needs to be a stable, collision-
 * resistant-enough label for a config; it is not a security boundary. The
 * integrity guarantee comes from the claim hash that contains this string.
 */
function fnv1a32(input: string, offsetBasis: number): number {
  let hash = offsetBasis
  for (let i = 0; i < input.length; i++) {
    hash ^= input.charCodeAt(i)
    // Math.imul keeps the 32-bit multiply exact. BigInt would be cleaner but
    // needs an ES2020 target this project does not set.
    hash = Math.imul(hash, 16777619)
  }
  return hash >>> 0
}

/** Two independently seeded 32-bit passes, concatenated to a 16-char label. */
function fnv1a64(input: string): string {
  const a = fnv1a32(input, 0x811c9dc5)
  const b = fnv1a32(input, 0x01000193)
  return a.toString(16).padStart(8, '0') + b.toString(16).padStart(8, '0')
}

export const RANKING_POLICY_CANONICAL = canonicalise(RANKING_POLICY)

/**
 * e.g. `rank-v1-9f2ac1d0e3b47a55`. Stamped onto every snapshot and every
 * published claim, and shown on /methodology.
 */
export const RANKING_VERSION =
  `rank-v${RANKING_POLICY.generation}-${fnv1a64(RANKING_POLICY_CANONICAL)}`
