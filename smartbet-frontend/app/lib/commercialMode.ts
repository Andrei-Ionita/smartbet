/**
 * THE single commercial-mode switch.
 *
 * BetGlitch is presented as a free public beta while the company, billing setup
 * and payment-provider approval are being completed. Every pricing link,
 * upgrade CTA, premium lock and checkout path derives from this one value —
 * nothing may hardcode its own commerce check.
 *
 * Re-enabling payments is ONE configuration change (see
 * docs/audit/public-beta-subscription-audit.md and the reactivation checklist).
 * No subscription code is deleted; it is dormant.
 *
 * Server and browser share the same effective value: the variable is
 * NEXT_PUBLIC_ so it is inlined at build time and readable in both.
 *
 * FAIL CLOSED: anything other than the exact string 'commercial' means payments
 * are OFF. A typo, an unset variable or a stray value all resolve to the beta.
 */
export type CommercialMode = 'public_beta' | 'commercial'

export const COMMERCIAL_MODE: CommercialMode =
  process.env.NEXT_PUBLIC_COMMERCIAL_MODE === 'commercial'
    ? 'commercial'
    : 'public_beta'

/** True only when payments are deliberately enabled. */
export const PAYMENTS_ENABLED = COMMERCIAL_MODE === 'commercial'

/** True while BetGlitch is a free public beta. */
export const IS_PUBLIC_BETA = !PAYMENTS_ENABLED

/**
 * Public-beta entitlement.
 *
 * Deliberately NOT "pretend everyone is Pro" — no user is given fake paid
 * status, and `UserProfile.tier` keeps its real value. During the beta we
 * simply do not apply paid entitlement checks.
 */
export function hasBetaAccess(isAuthenticated: boolean): boolean {
  return IS_PUBLIC_BETA ? isAuthenticated : false
}

/**
 * Should a paid-feature gate apply at all?
 * During the beta, no feature is withheld behind a subscription.
 */
export function shouldGateOnSubscription(): boolean {
  return PAYMENTS_ENABLED
}

/** The API error returned by any commerce endpoint while payments are off. */
export const PAYMENTS_DISABLED_ERROR = {
  code: 'payments_disabled',
  detail: 'BetGlitch is currently operating as a free public beta.',
} as const

// ── Public beta copy ────────────────────────────────────────────────────────
// Kept here so every surface says the same thing, and so it disappears in one
// place when payments return.
export const BETA_COPY = {
  primary:
    'BetGlitch is currently in public beta. Access is free while we build and '
    + 'validate the verified public record.',
  supporting:
    'Every published pick is locked before kickoff and remains visible after '
    + 'settlement—win or lose.',
  account:
    'Create a free account to explore the beta and follow the public results '
    + 'as it develops.',
  badge: 'Public Beta — free',
} as const
