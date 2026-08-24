'use client'

import { useEffect } from 'react'
import { usePathname } from 'next/navigation'

import { track } from '../lib/analytics'

function dwellBucket(milliseconds: number) {
  const seconds = milliseconds / 1000
  if (seconds < 10) return 'under_10s' as const
  if (seconds < 30) return '10_to_30s' as const
  if (seconds < 120) return '30_to_120s' as const
  if (seconds < 300) return '2_to_5m' as const
  return 'over_5m' as const
}

/** Records route reach and coarse dwell time without persistent identity. */
export default function ProductAnalytics() {
  const pathname = usePathname()

  useEffect(() => {
    if (!pathname) return
    const startedAt = Date.now()
    let dwellSent = false
    track('page_viewed', { surface: pathname })

    const sendDwell = () => {
      if (dwellSent) return
      dwellSent = true
      track('page_dwell', {
        surface: pathname,
        duration_bucket: dwellBucket(Date.now() - startedAt),
      })
    }
    const onVisibilityChange = () => {
      if (document.visibilityState === 'hidden') sendDwell()
    }

    document.addEventListener('visibilitychange', onVisibilityChange)
    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange)
      sendDwell()
    }
  }, [pathname])

  return null
}
