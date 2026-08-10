'use client'

import Link from 'next/link'
import EmailCapture from './EmailCapture'
import { useLanguage } from '../contexts/LanguageContext'
import { getCopy } from '../lib/terminology'

interface ProofCapturePanelProps {
  source: string
  title?: string
  description?: string
  leagueInterest?: string
}

export default function ProofCapturePanel({
  source,
  title,
  description,
  leagueInterest = '',
}: ProofCapturePanelProps) {
  const { language } = useLanguage()
  const rec = getCopy(language).record

  return (
    <div className="rounded-3xl border border-blue-200 bg-gradient-to-br from-blue-50 via-white to-emerald-50 p-6 shadow-sm">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
        <div className="max-w-xl">
          <p className="mb-2 text-sm font-semibold uppercase tracking-[0.2em] text-blue-600">
            {rec.capturePanelEyebrow}
          </p>
          <h3 className="text-2xl font-bold text-gray-900">
            {title ?? rec.captureDefaultTitle}
          </h3>
          <p className="mt-3 text-sm leading-6 text-gray-600">
            {description ?? rec.captureDefaultBody}
          </p>
          {/* Both links used to point at bare /track-record with different
              labels, so "review the track record" and "see the verified
              record" delivered the same screen — the same duplicate-destination
              problem the onboarding panel had. They now address the two
              anchored sections they name. */}
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            <Link
              href="/track-record#published-picks"
              className="font-semibold text-blue-700 hover:text-blue-900"
            >
              {rec.capturePanelSeePublished}
            </Link>
            <Link
              href="/track-record#results"
              className="font-semibold text-emerald-700 hover:text-emerald-900"
            >
              {rec.capturePanelSeeVerified}
            </Link>
          </div>
        </div>
        <div className="w-full max-w-md">
          <EmailCapture
            source={source}
            leagueInterest={leagueInterest}
            interests={['weekly_picks', 'track_record', 'premium_launch']}
            title={rec.captureTitle}
            description={rec.captureBody}
          />
        </div>
      </div>
    </div>
  )
}
