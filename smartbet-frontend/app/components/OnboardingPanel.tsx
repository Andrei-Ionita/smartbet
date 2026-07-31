'use client'

/**
 * First-session orientation.
 *
 * One compact panel, three actions, dismissible — deliberately not a multi-step
 * modal maze. A new account holder has just handed over an email address; the
 * least the product can do is say what to click next rather than dropping them
 * into disconnected widgets.
 *
 * Dismissal persists in localStorage, so a returning user is never interrupted
 * twice. The flag is set at registration, not at first render, so an existing
 * user who has been signing in for months never sees this.
 */
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { ArrowRight, X } from 'lucide-react'
import { getCopy } from '../lib/terminology'
import { track } from '../lib/analytics'
import { useLanguage } from '../contexts/LanguageContext'

const STORAGE_KEY = 'betglitch_onboarding'

/** Called on successful registration so the next dashboard visit orients. */
export function markOnboardingPending() {
  try {
    localStorage.setItem(STORAGE_KEY, 'pending')
  } catch {
    // Private-browsing storage failures must not break registration.
  }
}

export function isOnboardingPending(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'pending'
  } catch {
    return false
  }
}

export default function OnboardingPanel() {
  const { language } = useLanguage()
  const copy = getCopy(language)
  // Never render on the server pass — localStorage is the source of truth and
  // a mismatch would flash the panel for every returning user.
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    setVisible(isOnboardingPending())
  }, [])

  const dismiss = () => {
    try {
      localStorage.setItem(STORAGE_KEY, 'dismissed')
    } catch {
      // Ignore — the panel still closes for this session.
    }
    setVisible(false)
  }

  if (!visible) return null

  return (
    <section
      aria-labelledby="onboarding-heading"
      className="relative mb-8 rounded-2xl border border-blue-200 bg-white p-6"
    >
      <button
        onClick={dismiss}
        aria-label={copy.onboarding.dismiss}
        className="absolute right-3 top-3 inline-flex h-11 w-11 items-center justify-center rounded-lg text-gray-400 transition-colors hover:bg-gray-100 hover:text-gray-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-900"
      >
        <X className="h-5 w-5" />
      </button>

      <p className="text-xs font-bold uppercase tracking-widest text-blue-700">
        {copy.hero.eyebrow}
      </p>
      <h2
        id="onboarding-heading"
        className="mt-2 pr-12 text-xl font-bold text-gray-900"
      >
        {copy.onboarding.heading}
      </h2>
      <p className="mt-1 text-sm text-gray-600">{copy.onboarding.body}</p>

      <ul className="mt-5 grid gap-3 md:grid-cols-3">
        {copy.onboarding.actions.map((action, i) => (
          <li
            key={action.id}
            className="flex flex-col rounded-xl border border-gray-200 p-4"
          >
            <span className="text-xs font-bold tracking-widest text-gray-400">
              {String(i + 1).padStart(2, '0')}
            </span>
            <h3 className="mt-1 font-semibold text-gray-900">{action.title}</h3>
            <p className="mt-1 flex-1 text-sm leading-relaxed text-gray-600">
              {action.body}
            </p>
            <Link
              href={action.href}
              onClick={() =>
                track('onboarding_action', {
                  surface: 'dashboard',
                  action: action.id,
                })
              }
              className={`mt-4 inline-flex min-h-[44px] items-center justify-center gap-1.5 rounded-lg px-4 py-2 text-sm font-semibold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-900 ${
                i === 0
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'border border-gray-300 text-gray-700 hover:bg-gray-50'
              }`}
            >
              {action.cta}
              {i === 0 && <ArrowRight className="h-4 w-4" />}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  )
}
