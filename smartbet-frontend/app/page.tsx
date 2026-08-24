'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  AlertCircle,
  ArrowRight,
  BarChart3,
  Database,
  FlaskConical,
  Lock,
  Search,
  ScrollText,
} from 'lucide-react'
import Image from 'next/image'
import GemCard from './components/GemCard'
import HomepageDecisionBoard from './components/HomepageDecisionBoard'
import RecommendationCardSkeleton from './components/RecommendationCardSkeleton'
import ErrorBoundary from './components/ErrorBoundary'
import RetryButton from './components/RetryButton'
import { StatusBadge } from './components/StatusBadge'
import { getCopy } from './lib/terminology'
import { SEARCHABLE_COMPETITION_COUNT } from './lib/coverage'
import { track } from './lib/analytics'
import { useLanguage } from './contexts/LanguageContext'
import { ModelShortlistItem, Recommendation } from '../src/types/recommendation'
import useSWR from 'swr'

const fetcher = (url: string) => fetch(url).then(res => res.json())

/**
 * Representative coverage, not the full competition wall. The old grid made the
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

/** Single source of truth — never hardcode a coverage number on a page. */
const TOTAL_LEAGUES = SEARCHABLE_COMPETITION_COUNT

const LEARNING_ICONS = [ScrollText, Database, BarChart3, FlaskConical]

export default function HomePage() {
  const router = useRouter()
  const { language } = useLanguage()
  const copy = getCopy(language)
  const [fixtureQuery, setFixtureQuery] = useState('')

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

  const handleViewDetails = (fixtureId: number) => {
    track('fixture_opened', { surface: 'homepage' })
    router.push(`/explore?fixture=${fixtureId}`)
  }

  const gems: Recommendation[] = data?.featured_gems ?? data?.recommendations ?? []
  const shortlist: ModelShortlistItem[] = data?.model_shortlist ?? []
  const valueWatchlist: ModelShortlistItem[] = data?.decision_board?.price_watchlist ?? []
  const strongSignals: ModelShortlistItem[] = data?.decision_board?.strong_signals ?? shortlist
  const shortlistStatus = data?.model_shortlist_status ?? 'pending_refresh'
  const scan = {
    fixtures: data?.gem_scan?.fixtures_scanned ?? data?.fixtures_analyzed ?? 0,
    predictions: data?.gem_scan?.fixtures_with_predictions ?? data?.fixtures_with_predictions ?? 0,
    signalPriceReady: data?.gem_scan?.gate_funnel?.signal_and_price_ready ?? 0,
    qualified: data?.gem_scan?.qualified_fixtures ?? gems.length,
    shown: data?.gem_scan?.displayed_gems ?? gems.length,
    status: data?.gem_scan?.status ?? 'warming',
  }

  const searchFixture = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const query = fixtureQuery.trim()
    track('home_primary_cta', { surface: query ? 'homepage_search' : 'homepage_browse' })
    router.push(query ? `/explore?q=${encodeURIComponent(query)}` : '/explore')
  }
  const rejectionLabels: Record<string, string> = {
    signal_or_verified_price: copy.home.diagnosticsSignalPrice,
    reliability: copy.home.diagnosticsReliability,
    provider_value: copy.home.diagnosticsProviderValue,
    cross_market_consensus: copy.home.diagnosticsConsensus,
    price_quality: copy.home.diagnosticsPriceQuality,
  }
  const rejectionBreakdown: Array<{ code: string; fixtures_affected: number }> =
    Array.isArray(data?.gem_scan?.rejection_breakdown)
      ? data.gem_scan.rejection_breakdown
      : []

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="mx-auto max-w-6xl px-4 py-10 sm:py-14">

        {/* ── 1. Hero ─────────────────────────────────────────────────────
            One job: say what this is, show why it can be trusted, and give
            exactly one obvious first click. */}
        <header className="mx-auto max-w-3xl text-center">
          <div className="relative mx-auto mb-4 h-16 w-16 sm:h-20 sm:w-20">
            <Image
              src="/images/logo-final-v6.png"
              alt=""
              fill
              priority
              className="object-contain drop-shadow"
            />
          </div>

          <p className="mb-3 inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-3 py-1 text-xs font-bold uppercase tracking-widest text-blue-700">
            {copy.hero.eyebrow}
          </p>

          <h1 className="text-3xl font-bold leading-tight tracking-tight text-gray-900 sm:text-4xl md:text-5xl">
            {copy.hero.headline}
          </h1>

          <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-gray-600 sm:text-lg">
            {copy.hero.supporting}
          </p>

          <form onSubmit={searchFixture} className="mx-auto mt-6 grid max-w-2xl gap-3 sm:grid-cols-[1fr_auto]">
            <label className="relative text-left">
              <span className="sr-only">{copy.home.searchLabel}</span>
              <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" aria-hidden="true" />
              <input
                type="search"
                value={fixtureQuery}
                onChange={(event) => setFixtureQuery(event.target.value)}
                placeholder={copy.home.searchPlaceholder}
                className="min-h-[52px] w-full rounded-xl border border-slate-300 bg-white pl-12 pr-4 text-slate-950 shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
              />
            </label>
            <button
              type="submit"
              className="group inline-flex min-h-[52px] items-center justify-center gap-2 rounded-xl bg-blue-600 px-7 py-3 font-semibold text-white shadow-lg transition-colors hover:bg-blue-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
            >
              {copy.home.searchCta}
              <ArrowRight className="h-5 w-5 transition-transform group-hover:translate-x-0.5" />
            </button>
          </form>
        </header>

        {/* 2. One compact board, with evidence lanes that cannot masquerade as
            one another. Value, strategy fit and model consensus are different
            claims and therefore get different cards and caveats. */}
        <HomepageDecisionBoard
          language={language}
          valueWatchlist={valueWatchlist}
          strongSignals={strongSignals}
          status={shortlistStatus}
          recommendationsLoading={isLoading}
          recommendationsError={Boolean(error)}
        />

        {/* The qualification denominator stays visible even when zero Gems
            survive. Hiding the funnel on empty days made a strict scan look
            indistinguishable from a broken one. */}
        {!isLoading && !error && scan.status === 'current' && (
          <section aria-labelledby="qualification-ledger-heading" className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">{copy.home.diagnosticsHeading}</p>
                <h2 id="qualification-ledger-heading" className="mt-1 text-xl font-black text-slate-950">{copy.home.scanLedgerHeading}</h2>
                <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{copy.home.scanLedgerBody}</p>
              </div>
              {data?.lastUpdated && (
                <time dateTime={data.lastUpdated} className="shrink-0 text-xs text-slate-500">
                  {new Date(data.lastUpdated).toLocaleString(language === 'ro' ? 'ro-RO' : 'en-GB')}
                </time>
              )}
            </div>

            <dl className="mt-5 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-slate-200 bg-slate-200 sm:grid-cols-4">
              {[
                [scan.fixtures, copy.home.scanFixtures],
                [scan.predictions, copy.home.scanPredictions],
                [scan.signalPriceReady, copy.home.scanSignalPrice],
                [scan.qualified, copy.home.scanQualified],
              ].map(([value, label], index) => (
                <div key={String(label)} className="relative bg-slate-50 px-4 py-4 text-center">
                  {index > 0 && <span aria-hidden className="absolute -left-2 top-1/2 z-10 hidden -translate-y-1/2 rounded-full bg-slate-900 px-1.5 py-0.5 text-[10px] text-white sm:block">→</span>}
                  <dt className="text-xs leading-tight text-slate-500">{label}</dt>
                  <dd className="mt-1 text-2xl font-black text-slate-950">{value}</dd>
                </div>
              ))}
            </dl>

            {rejectionBreakdown.length > 0 && scan.predictions > 0 && (
              <details className="mt-4 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                <summary className="cursor-pointer text-sm font-bold text-slate-800">{copy.home.diagnosticsHeading}</summary>
                <p className="mt-3 text-xs leading-relaxed text-slate-500">{copy.home.diagnosticsBody}</p>
                <dl className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
                  {rejectionBreakdown.map((item) => (
                    <div key={item.code} className="rounded-lg bg-white px-3 py-3">
                      <dt className="text-xs leading-snug text-slate-600">{rejectionLabels[item.code] ?? item.code}</dt>
                      <dd className="mt-1 text-lg font-black text-slate-950">
                        {item.fixtures_affected}{' '}
                        <span className="text-xs font-normal text-slate-500">{copy.home.diagnosticsAffected}</span>
                      </dd>
                    </div>
                  ))}
                </dl>
              </details>
            )}
          </section>
        )}

        {/* 3. Qualified Gems from the latest scan. */}
        <section aria-labelledby="gems-heading" className={gems.length > 0 || isLoading || error ? 'mt-16 sm:mt-20' : 'mt-8'}>
          {(isLoading || error || gems.length > 0) && (
          <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <div className="mb-2">
                <StatusBadge status="live" size="sm" lang={language} />
              </div>
              <h2
                id="gems-heading"
                className="text-2xl font-bold text-gray-900 sm:text-3xl"
              >
                {copy.home.gemsHeading}
              </h2>
              <p className="mt-1 max-w-2xl text-sm text-gray-600">
                {copy.home.gemsSupporting}
              </p>
              <p className="mt-2 max-w-2xl text-sm font-semibold text-gray-800">
                {copy.home.gemsLimit}
              </p>
            </div>
            <Link
              href="/explore"
              onClick={() => track('home_primary_cta', { surface: 'gems_section' })}
              className="shrink-0 text-sm font-semibold text-blue-700 underline-offset-4 hover:underline"
            >
              {copy.home.browseAll} →
            </Link>
          </div>
          )}

          {isLoading && (
            <div className="grid gap-4 sm:gap-6 lg:grid-cols-3">
              {Array.from({ length: 3 }).map((_, i) => (
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

          {!isLoading && !error && gems.length > 0 && (
            <div className="grid gap-4 sm:gap-6 lg:grid-cols-3">
              {gems.map((recommendation: Recommendation, index: number) => (
                <GemCard
                  key={recommendation.fixture_id}
                  recommendation={recommendation}
                  language={language}
                  displayRank={index + 1}
                  onViewDetails={handleViewDetails}
                  lastUpdated={data?.lastUpdated ?? null}
                />
              ))}
            </div>
          )}

          {!isLoading && !error && gems.length === 0 && (
            <div className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-3">
                <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-100">
                  <Lock className="h-4 w-4 text-slate-500" />
                </span>
                <div>
                  <h2 id="gems-heading" className="font-bold text-slate-950">{copy.home.noGemsHeading}</h2>
                  <p className="mt-1 text-sm leading-5 text-slate-600">
                    {copy.home.noGemsBody}
                  </p>
                </div>
              </div>
              <Link href="/explore" className="shrink-0 text-sm font-semibold text-blue-700 underline-offset-4 hover:underline">
                {copy.home.browseAll} →
              </Link>
            </div>
          )}
        </section>

        {/* Coverage stays close to the live football content. */}
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

        {/* Detailed public evidence belongs below the product experience. */}
        <section aria-labelledby="learning-heading" className="mt-16 sm:mt-20">
          <p className="text-xs font-bold uppercase tracking-widest text-blue-700">{copy.home.learningEyebrow}</p>
          <h2 id="learning-heading" className="mt-2 text-2xl font-bold text-gray-900 sm:text-3xl">{copy.home.learningHeading}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-gray-600">{copy.home.learningSupporting}</p>
          <div className="mt-6 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {copy.home.learningLinks.map((item, index) => {
              const Icon = LEARNING_ICONS[index] ?? BarChart3
              return (
                <Link key={item.href} href={item.href} className="group rounded-2xl border border-gray-200 bg-white p-6 transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md">
                  <Icon className="h-6 w-6 text-blue-700" aria-hidden="true" />
                  <h3 className="mt-4 font-bold text-gray-950">{item.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-gray-600">{index === 0 && hasVerifiedResults ? `${settledCount} ${copy.home.settledLabel.toLowerCase()}. ` : ''}{item.body}</p>
                  <span className="mt-4 inline-flex items-center gap-2 text-sm font-bold text-blue-700">{item.cta}<ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" /></span>
                </Link>
              )
            })}
          </div>
          <div className="mt-5 flex flex-col gap-4 rounded-2xl border border-indigo-200 bg-indigo-50/60 p-5 sm:flex-row sm:items-center sm:justify-between">
            <div className="max-w-3xl"><h3 className="font-bold text-indigo-950">{copy.home.differenceHeading}</h3><p className="mt-1 text-sm leading-6 text-indigo-900">{copy.home.differenceBody}</p></div>
            <Link href="/track-record#published-picks" className="shrink-0 text-sm font-bold text-indigo-800 underline-offset-4 hover:underline">{copy.home.openRecord} →</Link>
          </div>
        </section>

        {/* Final CTA. */}
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
              href="/track-record"
              onClick={() => track('home_verified_record_cta', { surface: 'homepage_final' })}
              className="inline-flex min-h-[48px] items-center justify-center rounded-xl bg-white px-7 py-3 font-semibold text-gray-900 transition-colors hover:bg-gray-100"
            >
              {copy.home.openRecord}
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

        {/* ── 9. Responsible use ──────────────────────────────────────── */}
        <p className="mt-12 border-t border-gray-200 pt-8 text-center text-xs leading-relaxed text-gray-500">
          {copy.responsibleUse}
        </p>
      </div>
    </div>
  )
}
