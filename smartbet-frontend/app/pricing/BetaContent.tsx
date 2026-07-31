'use client'

import Link from 'next/link'
import { Check, ShieldCheck } from 'lucide-react'

import { BETA_COPY } from '@/app/lib/commercialMode'

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
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <div className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-sm font-semibold text-blue-800">
        <ShieldCheck className="h-4 w-4" />
        {BETA_COPY.badge}
      </div>

      <h1 className="mt-6 text-3xl font-bold text-gray-900 sm:text-4xl">
        BetGlitch Public Beta — free while we build the verified public record
      </h1>

      <p className="mt-5 text-lg leading-relaxed text-gray-700">
        {BETA_COPY.primary}
      </p>

      <p className="mt-3 text-lg leading-relaxed text-gray-700">
        {BETA_COPY.supporting}
      </p>

      <div className="mt-10 rounded-2xl border border-gray-200 bg-white p-6 shadow-sm">
        <h2 className="text-lg font-bold text-gray-900">What this means today</h2>
        <ul className="mt-4 space-y-3 text-gray-700">
          {[
            'Access is currently free — there is nothing to buy.',
            'No payment method is required, and none is collected.',
            'Commercial plans may be introduced after we have validated the record.',
            'If that changes, beta users will be told before it does.',
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
          Create a free account
        </Link>
        <Link
          href="/track-record"
          className="rounded-lg border border-gray-300 px-5 py-2.5 text-sm font-semibold text-gray-800 hover:bg-gray-50"
        >
          See the verified record
        </Link>
      </div>

      <p className="mt-6 text-sm text-gray-600">{BETA_COPY.account}</p>

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
