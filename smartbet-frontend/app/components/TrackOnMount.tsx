'use client'

/**
 * Fires one analytics event when a server-rendered page mounts.
 *
 * The proof pages are server components — they cannot call `track` directly.
 * This renders nothing and exists purely so a static page can still report that
 * it was opened.
 */
import { useEffect } from 'react'
import { track, type AnalyticsEvent } from '../lib/analytics'

export default function TrackOnMount({
  event,
  surface,
}: {
  event: AnalyticsEvent
  surface?: string
}) {
  useEffect(() => {
    track(event, surface ? { surface } : {})
  }, [event, surface])

  return null
}
