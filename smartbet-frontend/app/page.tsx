'use client'

import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  AlertCircle,
  ArrowRight,
  BarChart3,
  Calculator,
  Lock,
  ScrollText,
} from 'lucide-react'
import Image from 'next/image'
import RecommendationCard from './components/RecommendationCard'
import EmptyState from './components/EmptyState'
import RecommendationCardSkeleton from './components/RecommendationCardSkeleton'
import ErrorBoundary from './components/ErrorBoundary'
import RetryButton from './components/RetryButton'
import EmailCapture from './components/EmailCapture'
import { StatusBadge } from './components/StatusBadge'
import { getCopy } from './lib/terminology'
import { track } from './lib/analytics'
import { useLanguage } from './contexts/LanguageContext'
import { Recommendation } from '../src/types/recommendation'
import useSWR from 'swr'

const fetcher = (url: string) => fetch(url).then(res => res.json())

/**
 * Representative coverage, not the full 26-league wall. The old grid made the
 * homepage scroll for a screen and a half to say something one sentence says
 * better — and every card carried an internal deployment-state chip that meant
 * nothing to a visitor.
 */
const FEATURED_LEAGUES = [
  { name: 'Premier League', country: 'England' },
  { name: 'La Liga', country: 'Spain' },
  { name: 'Bundesliga', country: 'Germany' },
  { name: 'Serie A', country: 'Italy' },
  { name: 'Ligue 1', country: 'France' },
  { name: 'Eredivisie', country: 'Netherlands' },
]

const TOTAL_LEAGUES = 27

const BENEFIT_ICONS = [BarChart3, ScrollText, Calculator]

export default function HomePage() {
  const router = useRouter()
  const { language } = useLanguage()
  const copy = getCopy(language)

  const enhancedFetcher = async (url: string) => {
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return response.json()
  }

  const getSessionId = () => {
    if (typeof window !== 'undefined') {
      return localStorage.getItem('smartbet_session_id') || ''
    }
    return ''
  }

  const sessionId = getSessionId()
  const apiUrl = sessionId
    ? `/api/recommendations/?session_id=${sessionId}`
    : '/api/recommendations/'

  const { data, error, isLoading, mutate } = useSWR(apiUrl, enhancedFetcher, {
    refreshInterval: 60000,
    revalidateOnFocus: true,
    errorRetryCount: 3,
    errorRetryInterval: 2000,
    shouldRetryOnError: true,
  })

  const { data: performanceData } = useSWR('/api/performance', fetcher, {
    refreshInterval: 120000,
  })

  const settledCount = performanceData?.data?.overall?.total_predictions ?? 0
  const hasVerifiedResults = settledCount > 0

  const goExplore = () => {
    track('home_primary_cta', { surface: 'homepage' })
    router.push('/explore')
  }

  const goVerifiedRecord = () => {
    track('home_verified_record_cta', { surface: 'homepage' })
    router.push('/track-record')
  }

  const handleViewDetails = (fixtureId: number) => {
    track('fixture_opened', { surface: 'homepage' })
    router.push(`/explore?fixture=${fixtureId}`)
  }

  const signals: Recommendation[] = data?.recommendations ?? []

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="mx-auto max-w-6xl px-4 py-10 sm:py-14">

        {/* ── 1. Hero ─────────────────────────────────────────────────────
            One job: say what this is, show why it can be trusted, and give
            exactly one obvious first click. */}
        <header className="mx-auto max-w-3xl text-center">
          <div className="relative mx-auto mb-6 h-20 w-20 sm:h-24 sm:w-24">
            <Image
              src="/images/logo-final-v6.png"
              alt=""
              fill
              priority
              className="object-contain drop-shadow"
            />
          </div>

          <p className="mb-4 inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-bold uppercase tracking-widest text-blue-700">
            {copy.hero.eyebrow}
          </p>

          <h1 className="text-3xl font-bold leading-tight tracking-tight text-gray-900 sm:text-4xl md:text-5xl">
            {copy.hero.headline}
          </h1>

          <p className="mx-auto mt-5 max-w-2xl text-base leading-relaxed text-gray-600 sm:text-lg">
            {copy.hero.supporting}
          </p>

          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <button
              onClick={goExplore}
              className="group inline-flex min-h-[48px] items-center justify-center gap-2 rounded-xl bg-blue-600 px-7 py-3 font-semibold text-white shadow-lg transition-colors hover:bg-blue-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
            >
              {copy.hero.primaryCta}
              <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-0.5" />
            </button>
            <button
              onClick={goVerifiedRecord}
              className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-xl border border-gray-300 bg-white px-7 py-3 font-semibold text-gray-800 transition-colors hover:bg-gray-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-900"
            >
              {copy.hero.secondaryCta}
            </button>
          </div>

          {/* Verified-record status. At zero settled picks this states the
              honest position instead of rendering 0%, which reads as
              break-even performance rather than "no data yet". */}
          <button
            onClick={goVerifiedRecord}
            className="mx-auto mt-6 flex items-center gap-2 rounded-full border border-gray-300 bg-white/70 px-4 py-2 text-sm text-gray-700 transition-colors hover:bg-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-900"
          >
            <ScrollText className="h-4 w-4 shrink-0 text-gray-500" />
            {hasVerifiedResults ? (
              <span>
                <strong className="font-semibold text-gray-900">
                  {settledCount}
                </strong>{' '}
                {copy.home.settledLabel.toLowerCase()}
              </span>
            ) : (
              <span>{copy.hero.zeroState}</span>
            )}
            <ArrowRight className="h-4 w-4 shrink-0 text-gray-400" />
          </button>
        </header>

        {/* ── 2. Current live signals ─────────────────────────────────── */}
        <section aria-labelledby="signals-heading" className="mt-16 sm:mt-20">
          <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="mb-2">
                <StatusBadge status="live" size="sm" />
              </div>
              <h2
                id="signals-heading"
                className="text-2xl font-bold text-gray-900 sm:text-3xl"
              >
                {copy.home.signalsHeading}
              </h2>
              <p className="mt-1 max-w-2xl text-sm text-gray-600">
                {copy.terms.liveSignal.definition}{' '}
                {copy.terms.liveSignal.notInRecord}
              </p>
            </div>
            <Link
              href="/explore"
              onClick={() => track('home_primary_cta', { surface: 'signals_section' })}
              className="shrink-0 text-sm font-semibold text-blue-700 underline-offset-4 hover:underline"
            >
              {copy.home.browseAll} →
            </Link>
          </div>

          {isLoading && (
            <div className="grid gap-4 sm:gap-6 lg:grid-cols-2">
              {Array.from({ length: 4 }).map((_, i) => (
                <RecommendationCardSkeleton key={i} />
              ))}
            </div>
          )}

          {error && (
            <ErrorBoundary>
              <div
                role="alert"
                className="rounded-2xl border border-amber-300 bg-amber-50 p-6 text-center sm:p-8"
              >
                <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-amber-100">
                  <AlertCircle className="h-6 w-6 text-amber-700" />
                </div>
                <h3 className="text-lg font-bold text-gray-900">
                  {copy.home.signalsError}
                </h3>
                <p className="mx-auto mt-2 max-w-md text-sm text-gray-600">
                  {copy.home.signalsErrorBody}
                </p>
                <div className="mt-6">
                  <RetryButton
                    onRetry={() => mutate()}
                    text={copy.home.tryAgain}
                    className="bg-gray-900 hover:bg-gray-700"
                  />
                </div>
              </div>
            </ErrorBoundary>
          )}

          {!isLoading && !error && signals.length > 0 && (
            <div className="grid gap-4 sm:gap-6 lg:grid-cols-2">
              {signals.map((recommendation: Recommendation) => (
                <RecommendationCard
                  key={recommendation.fixture_id}
                  recommendation={recommendation}
                  onViewDetails={handleViewDetails}
                />
              ))}
            </div>
          )}

          {!isLoading && !error && signals.length === 0 && (
            <EmptyState state="no_live_signals" />
          )}
        </section>

        {/* ── 3. How BetGlitch works ──────────────────────────────────────
            Numbered because the order is real: a pick cannot be verified
            before it is published, or published before it exists. */}
        <section aria-labelledby="how-heading" className="mt-16 sm:mt-20">
          <h2
            id="how-heading"
            className="text-2xl font-bold text-gray-900 sm:text-3xl"
          >
            {copy.home.howHeading}
          </h2>
          <ol className="mt-6 grid gap-4 md:grid-cols-3">
            {copy.workflow.map((step, i) => (
              <li
                key={step.id}
                className="rounded-2xl border border-gray-200 bg-white p-6"
              >
                <span className="text-xs font-bold tracking-widest text-gray-400">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <h3 className="mt-2 text-lg font-bold text-gray-900">
                  {step.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-600">
                  {step.body}
                </p>
              </li>
            ))}
          </ol>
        </section>

        {/* ── 4. Signal vs published proof ────────────────────────────────
            The single most important idea in the product, given its own
            section and shown with the real badges rather than described. */}
        <section
          aria-labelledby="difference-heading"
          className="mt-16 rounded-2xl border border-gray-200 bg-white p-6 sm:mt-20 sm:p-8"
        >
          <h2
            id="difference-heading"
            className="text-2xl font-bold text-gray-900 sm:text-3xl"
          >
            {copy.home.differenceHeading}
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-gray-600">
            {copy.home.differenceBody}
          </p>

          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border-2 border-dashed border-sky-300 bg-sky-50/50 p-5">
              <StatusBadge status="live" size="sm" />
              <h3 className="mt-3 font-bold text-gray-900">
                {copy.terms.liveSignal.label}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-gray-700">
                {copy.terms.liveSignal.mutability}
              </p>
              <p className="mt-3 text-sm font-medium text-sky-900">
                {copy.home.notInPerformance}
              </p>
            </div>

            <div className="rounded-xl border-2 border-indigo-400 bg-indigo-50/50 p-5">
              <StatusBadge status="published_pending" size="sm" />
              <h3 className="mt-3 font-bold text-gray-900">
                {copy.terms.publishedPick.label}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-gray-700">
                {copy.home.frozenIntro}
              </p>
              <ul className="mt-2 flex flex-wrap gap-1.5">
                {copy.terms.publishedPick.frozenFields.map((f) => (
                  <li
                    key={f}
                    className="inline-flex items-center gap-1 rounded border border-indigo-200 bg-white px-2 py-0.5 text-xs font-medium text-indigo-900"
                  >
                    <Lock className="h-3 w-3" aria-hidden="true" />
                    {f}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* ── 5. Verified record ──────────────────────────────────────── */}
        <section aria-labelledby="record-heading" className="mt-16 sm:mt-20">
          <h2
            id="record-heading"
            className="text-2xl font-bold text-gray-900 sm:text-3xl"
          >
            {copy.terms.verifiedRecord.label}
          </h2>
          <p className="mt-2 max-w-2xl text-sm text-gray-600">
            {copy.terms.verifiedRecord.definition}{' '}
            {copy.terms.verifiedRecord.scope}
          </p>

          <div className="mt-6">
            {hasVerifiedResults ? (
              <div className="rounded-2xl border border-gray-200 bg-white p-6 text-center">
                <p className="text-sm text-gray-600">
                  {copy.home.settledLabel}
                </p>
                <p className="mt-1 text-4xl font-bold text-gray-900">
                  {settledCount}
                </p>
                <Link
                  href="/track-record"
                  onClick={() =>
                    track('home_verified_record_cta', { surface: 'record_section' })
                  }
                  className="mt-4 inline-flex min-h-[44px] items-center justify-center rounded-lg bg-gray-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-gray-700"
                >
                  {copy.home.openRecord}
                </Link>
              </div>
            ) : (
              <EmptyState state="no_verified_results" />
            )}
          </div>
        </section>

        {/* ── 6. What you can do here ─────────────────────────────────── */}
        <section aria-labelledby="benefits-heading" className="mt-16 sm:mt-20">
          <h2
            id="benefits-heading"
            className="text-2xl font-bold text-gray-900 sm:text-3xl"
          >
            {copy.home.benefitsHeading}
          </h2>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {copy.home.benefits.map((benefit, i) => {
              const Icon = BENEFIT_ICONS[i] ?? BarChart3
              return (
                <div
                  key={benefit.title}
                  className="rounded-2xl border border-gray-200 bg-white p-6"
                >
                  <Icon className="h-6 w-6 text-blue-600" aria-hidden="true" />
                  <h3 className="mt-3 font-bold text-gray-900">
                    {benefit.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-gray-600">
                    {benefit.body}
                  </p>
                </div>
              )
            })}
          </div>
        </section>

        {/* ── 7. Coverage ─────────────────────────────────────────────── */}
        <section aria-labelledby="coverage-heading" className="mt-16 sm:mt-20">
          <h2
            id="coverage-heading"
            className="text-2xl font-bold text-gray-900 sm:text-3xl"
          >
            {copy.home.coverageHeading}
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            {TOTAL_LEAGUES} {copy.home.coverageBody}
          </p>
          <ul className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
            {FEATURED_LEAGUES.map((league) => (
              <li
                key={league.name}
                className="rounded-xl border border-gray-200 bg-white px-4 py-3"
              >
                <div className="text-sm font-semibold text-gray-900">
                  {league.name}
                </div>
                <div className="text-xs text-gray-500">{league.country}</div>
              </li>
            ))}
          </ul>
          <Link
            href="/explore"
            className="mt-4 inline-block text-sm font-semibold text-blue-700 underline-offset-4 hover:underline"
          >
            {copy.home.viewAllLeagues} →
          </Link>
        </section>

        {/* ── 8. Final CTA ────────────────────────────────────────────── */}
        <section className="mt-16 rounded-2xl bg-gray-900 p-8 text-center sm:mt-20 sm:p-10">
          <p className="text-xs font-bold uppercase tracking-widest text-blue-300">
            {copy.hero.eyebrow}
          </p>
          <h2 className="mt-3 text-2xl font-bold text-white sm:text-3xl">
            {copy.home.finalHeading}
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-gray-300">
            {copy.home.finalBody}
          </p>
          <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
            <Link
              href="/register"
              onClick={() => track('registration_started', { surface: 'homepage' })}
              className="inline-flex min-h-[48px] items-center justify-center rounded-xl bg-white px-7 py-3 font-semibold text-gray-900 transition-colors hover:bg-gray-100"
            >
              {copy.home.createAccount}
            </Link>
            <button
              onClick={goExplore}
              className="inline-flex min-h-[48px] items-center justify-center gap-2 rounded-xl border border-gray-600 px-7 py-3 font-semibold text-white transition-colors hover:bg-gray-800"
            >
              {copy.hero.primaryCta}
              <ArrowRight className="h-5 w-5" />
            </button>
          </div>
        </section>

        <div className="mt-12">
          <EmailCapture variant="hero" source="homepage" />
        </div>

        {/* ── 9. Responsible use ──────────────────────────────────────── */}
        <p className="mt-12 border-t border-gray-200 pt-8 text-center text-xs leading-relaxed text-gray-500">
          {copy.responsibleUse}
        </p>
      </div>
    </div>
  )
}
