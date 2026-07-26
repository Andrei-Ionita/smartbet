'use client'

import { useState } from 'react'

const APP_URL = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'

export default function ShareProofButton({
  fixtureId,
  className = '',
}: {
  fixtureId: number | string
  className?: string
}) {
  const [copied, setCopied] = useState(false)
  const shareUrl = `${APP_URL}/proof/${fixtureId}`

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      // Clipboard blocked (e.g. non-secure context) — open the proof page instead.
      window.open(shareUrl, '_blank')
    }
  }

  return (
    <button
      type="button"
      onClick={copy}
      title="Copy a shareable proof card link"
      className={`inline-flex items-center gap-1.5 rounded-md border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900 ${className}`}
    >
      {copied ? '✓ Copied' : 'Share proof'}
    </button>
  )
}
