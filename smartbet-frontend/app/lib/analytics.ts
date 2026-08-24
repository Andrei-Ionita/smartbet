/**
 * Minimal product analytics.
 *
 * This is the only analytics boundary. It emits to BetGlitch's privacy-minimal
 * Django event endpoint and to an optional browser provider, while silently
 * doing nothing if any destination is unavailable.
 *
 * When a provider is chosen later, wire it in ONE place — here.
 *
 * Privacy: no search text, fixture id, stake, bankroll value, selection,
 * account id, email, query string or persistent device id is sent. A random
 * session UUID lives only in sessionStorage and is secret-key hashed by Django.
 */

export type AnalyticsEvent =
  | 'page_viewed'
  | 'page_dwell'
  | 'home_primary_cta'          // "Explore live signals" in the hero
  | 'home_verified_record_cta'  // "View verified record" in the hero
  | 'registration_started'
  | 'registration_completed'
  | 'first_login'
  | 'onboarding_action'         // which of the three first-session actions
  | 'explore_search'
  | 'fixture_opened'
  | 'research_shared'
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
  /** Coarse page dwell bucket. This is not labelled as active time. */
  duration_bucket?: 'under_10s' | '10_to_30s' | '30_to_120s' | '2_to_5m' | 'over_5m'
}

type Win = Window & {
  gtag?: (command: string, event: string, props?: Record<string, unknown>) => void
  plausible?: (event: string, opts?: { props?: Record<string, unknown> }) => void
}

const SESSION_KEY = 'betglitch_product_session'

function sessionId(): string | null {
  try {
    const existing = window.sessionStorage.getItem(SESSION_KEY)
    if (existing) return existing
    const created = window.crypto.randomUUID()
    window.sessionStorage.setItem(SESSION_KEY, created)
    return created
  } catch {
    return null
  }
}

function normalizedSurface(surface?: string): string | undefined {
  if (!surface) return undefined
  const path = surface.split('?')[0].split('#')[0]
  if (path.startsWith('/prediction/')) return '/prediction/:slug'
  if (path.startsWith('/proof/claim/')) return '/proof/claim/:id'
  if (path.startsWith('/proof/preview/')) return '/proof/preview/:id/:state'
  if (/^\/proof\/[^/]+$/.test(path)) return '/proof/:id'
  return path.slice(0, 120)
}

function sendToEvidenceStore(event: AnalyticsEvent, props: Props): void {
  if (process.env.NEXT_PUBLIC_PRODUCT_ANALYTICS_ENABLED === 'false') return
  if (window.navigator.doNotTrack === '1') return
  const session_id = sessionId()
  if (!session_id) return

  void fetch('/api/product-events/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'omit',
    keepalive: true,
    body: JSON.stringify({
      event_name: event,
      session_id,
      surface: normalizedSurface(props.surface),
      action: props.action,
      has_results: props.has_results,
      duration_bucket: props.duration_bucket,
    }),
  }).catch(() => {
    // Measurement must never interrupt the product.
  })
}

export function track(event: AnalyticsEvent, props: Props = {}): void {
  if (typeof window === 'undefined') return

  try {
    const w = window as Win
    const safeProps = { ...props, surface: normalizedSurface(props.surface) }
    sendToEvidenceStore(event, safeProps)
    if (typeof w.gtag === 'function') {
      w.gtag('event', event, safeProps)
    }
    if (typeof w.plausible === 'function') {
      w.plausible(event, { props: safeProps as Record<string, unknown> })
    }
    if (process.env.NODE_ENV === 'development') {
      // eslint-disable-next-line no-console
      console.debug('[analytics]', event, safeProps)
    }
  } catch {
    // Analytics must never break a user flow.
  }
}

export default track
