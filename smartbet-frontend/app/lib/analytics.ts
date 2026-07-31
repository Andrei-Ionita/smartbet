/**
 * Minimal product analytics.
 *
 * There is deliberately NO analytics platform in this codebase yet, and this
 * phase is not the place to add one. This module is a thin, dependency-free
 * seam: it emits to whatever provider happens to be present on `window`
 * (gtag or plausible) and silently does nothing otherwise.
 *
 * When a provider is chosen later, wire it in ONE place — here.
 *
 * Privacy: events carry the product surface and nothing else. No stake sizes,
 * no bankroll figures, no selections a user is considering, no identifiers.
 * BetGlitch does not need a record of what anyone was thinking of betting on.
 */

export type AnalyticsEvent =
  | 'home_primary_cta'          // "Explore live signals" in the hero
  | 'home_verified_record_cta'  // "View verified record" in the hero
  | 'registration_started'
  | 'registration_completed'
  | 'first_login'
  | 'onboarding_action'         // which of the three first-session actions
  | 'explore_search'
  | 'fixture_opened'
  | 'published_proof_opened'
  | 'dashboard_visited'
  | 'beta_page_viewed'

/** Only these keys may travel with an event. Keeps payloads reviewable. */
type Props = {
  /** Which surface the event fired from, e.g. 'homepage' | 'dashboard'. */
  surface?: string
  /** For onboarding_action: which of the three actions. */
  action?: string
  /** Whether a search returned anything — not WHAT was searched. */
  has_results?: boolean
}

type Win = Window & {
  gtag?: (command: string, event: string, props?: Record<string, unknown>) => void
  plausible?: (event: string, opts?: { props?: Record<string, unknown> }) => void
}

export function track(event: AnalyticsEvent, props: Props = {}): void {
  if (typeof window === 'undefined') return

  try {
    const w = window as Win
    if (typeof w.gtag === 'function') {
      w.gtag('event', event, props)
    }
    if (typeof w.plausible === 'function') {
      w.plausible(event, { props: props as Record<string, unknown> })
    }
    if (process.env.NODE_ENV === 'development') {
      // eslint-disable-next-line no-console
      console.debug('[analytics]', event, props)
    }
  } catch {
    // Analytics must never break a user flow.
  }
}

export default track
