'use client'

import Link from 'next/link'
import { useEffect } from 'react'
import { track } from '@/app/lib/analytics'
import { Check, ShieldCheck } from 'lucide-react'

import { useLanguage } from '@/app/contexts/LanguageContext'
import { getCopy } from '@/app/lib/terminology'

/**
 * Public-beta information page, served at /pricing while payments are disabled.
 *
 * Option A was chosen over a redirect: /pricing is in the sitemap, is linked
 * from published blog posts, and may already be indexed — a visitor arriving
 * with a pricing intent deserves a straight answer ("it's free right now")
 * rather than a silent bounce to the homepage.
 *
 * The old pricing table is NOT reachable from here or from any direct URL.
 * It makes no promise about future prices or launch dates, because none have
 * been decided.
 */
export default function BetaContent() {
  const { t, language } = useLanguage()
  const copy = getCopy(language)

  useEffect(() => {
    track('beta_page_viewed', { surface: 'pricing' })
  }, [])

  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <div className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-sm font-semibold text-blue-800">
        <ShieldCheck className="h-4 w-4" />
        {t('beta.badge')}
      </div>

      <h1 className="mt-6 text-3xl font-bold text-gray-900 sm:text-4xl">
        {t('beta.heading')}
      </h1>

      <p className="mt-5 text-lg leading-relaxed text-gray-700">
        {copy.beta.primary}
      </p>

      <p className="mt-3 text-lg leading-relaxed text-gray-700">
        {t('beta.supporting')}
      </p>

      <div className="mt-10 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-bold text-gray-900">{t('beta.meansTitle')}</h2>
        <ul className="mt-4 space-y-3 text-gray-700">
          {[
            t('beta.m1'),
            t('beta.m2'),
            t('beta.m3'),
            t('beta.m4'),
          ].map((line) => (
            <li key={line} className="flex gap-3">
              <Check className="mt-0.5 h-5 w-5 shrink-0 text-green-600" />
              <span>{line}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          href="/register"
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
        >
          {t('beta.createAccount')}
        </Link>
        <Link
          href="/track-record"
          className="rounded-lg border border-gray-300 px-5 py-2.5 text-sm font-semibold text-gray-800 hover:bg-gray-50"
        >
          {t('beta.seeRecord')}
        </Link>
      </div>

      <p className="mt-6 text-sm text-gray-600">{t('beta.account')}</p>

      <p className="mt-10 border-t border-gray-200 pt-6 text-xs leading-relaxed text-gray-500">
        BetGlitch publishes data-driven analysis for informational purposes. It
        is not betting advice, and no outcome is guaranteed. Please read our{' '}
        <Link href="/responsible-gambling" className="underline">
          responsible gambling
        </Link>{' '}
        guidance,{' '}
        <Link href="/terms" className="underline">
          terms
        </Link>{' '}
        and{' '}
        <Link href="/disclaimer" className="underline">
          disclaimer
        </Link>
        .
      </p>
    </div>
  )
}
