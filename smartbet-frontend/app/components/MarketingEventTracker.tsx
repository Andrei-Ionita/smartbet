'use client'

import { useEffect } from 'react'
import { trackMarketingEvent } from '@/src/lib/marketing'

interface MarketingEventTrackerProps {
  eventName: 'pricing_viewed' | 'paid_converted' | 'email_clicked' | 'weekly_picks_sent'
  source: string
  page?: string
  metadata?: Record<string, unknown>
}

export default function MarketingEventTracker({ eventName, source, page, metadata }: MarketingEventTrackerProps) {
  useEffect(() => {
    trackMarketingEvent({
      eventName,
      source,
      page,
      metadata,
    })
  }, [eventName, source, page, metadata])

  return null
}
