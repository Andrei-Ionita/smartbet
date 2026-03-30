export interface MarketingEventPayload {
  eventName: 'email_subscribed' | 'welcome_sequence_started' | 'weekly_picks_sent' | 'email_clicked' | 'pricing_viewed' | 'paid_converted'
  source?: string
  page?: string
  metadata?: Record<string, unknown>
  subscriberId?: number | null
}

export interface SubscriberCaptureContext {
  landingPage?: string
  utmSource?: string
  utmMedium?: string
  utmCampaign?: string
  language?: string
}

const getApiUrl = () => process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export function getSubscriberId(): number | null {
  if (typeof window === 'undefined') {
    return null
  }

  const raw = window.localStorage.getItem('smartbet_subscriber_id')
  if (!raw) {
    return null
  }

  const parsed = Number(raw)
  return Number.isFinite(parsed) ? parsed : null
}

export function storeSubscriberId(subscriberId: number | null | undefined) {
  if (typeof window === 'undefined' || !subscriberId) {
    return
  }

  window.localStorage.setItem('smartbet_subscriber_id', String(subscriberId))
}

export function getSubscriberCaptureContext(overrides: SubscriberCaptureContext = {}) {
  if (typeof window === 'undefined') {
    return {
      landing_page: overrides.landingPage || '',
      utm_source: overrides.utmSource || '',
      utm_medium: overrides.utmMedium || '',
      utm_campaign: overrides.utmCampaign || '',
      language: overrides.language || 'en',
    }
  }

  const params = new URLSearchParams(window.location.search)
  return {
    landing_page: overrides.landingPage || window.location.pathname,
    utm_source: overrides.utmSource || params.get('utm_source') || '',
    utm_medium: overrides.utmMedium || params.get('utm_medium') || '',
    utm_campaign: overrides.utmCampaign || params.get('utm_campaign') || '',
    language: overrides.language || document.documentElement.lang || navigator.language || 'en',
  }
}

export async function trackMarketingEvent(payload: MarketingEventPayload) {
  if (typeof window === 'undefined') {
    return
  }

  const body = {
    event_name: payload.eventName,
    source: payload.source || '',
    page: payload.page || window.location.pathname,
    subscriber_id: payload.subscriberId ?? getSubscriberId(),
    metadata: payload.metadata || {},
  }

  try {
    await fetch(`${getApiUrl()}/api/marketing/events/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      keepalive: true,
    })
  } catch (error) {
    console.error('Failed to track marketing event:', error)
  }
}
