'use client'

import { useState } from 'react'
import { Check, Share2 } from 'lucide-react'

import { track } from '../lib/analytics'

export default function ShareResearchButton({
  href,
  title,
  language,
  surface = 'fixture_research',
  className = '',
}: {
  href: string
  title: string
  language: 'en' | 'ro'
  surface?: string
  className?: string
}) {
  const [copied, setCopied] = useState(false)
  const label = copied
    ? (language === 'ro' ? 'Link copiat' : 'Link copied')
    : (language === 'ro' ? 'Distribuie' : 'Share')

  const share = async () => {
    const url = new URL(href, window.location.origin).toString()
    try {
      if (navigator.share) {
        await navigator.share({ title, url })
      } else {
        await navigator.clipboard.writeText(url)
        setCopied(true)
        window.setTimeout(() => setCopied(false), 2200)
      }
      track('research_shared', { surface })
    } catch (error) {
      if ((error as Error)?.name !== 'AbortError') {
        setCopied(false)
      }
    }
  }

  return (
    <button
      type="button"
      onClick={share}
      className={`inline-flex min-h-[40px] items-center justify-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 text-xs font-bold text-slate-700 transition hover:bg-slate-50 ${className}`}
      aria-label={`${label}: ${title}`}
    >
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-700" /> : <Share2 className="h-3.5 w-3.5" />}
      {label}
    </button>
  )
}
