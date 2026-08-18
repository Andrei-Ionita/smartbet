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
import GemCard from './components/GemCard'
import ModelShortlistCard from './components/ModelShortlistCard'
import EmptyState from './components/EmptyState'
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

  const gems: Recommendation[] = data?.featured_gems ?? data?.recommendations ?? []
  const shortlist: ModelShortlistItem[] = data?.model_shortlist ?? []
  const scan = {
    fixtures: data?.gem_scan?.fixtures_scanned ?? data?.fixtures_analyzed ?? 0,
    predictions: data?.gem_scan?.fixtures_with_predictions ?? data?.fixtures_with_predictions ?? 0,
    qualified: data?.gem_scan?.qualified_fixtures ?? gems.length,
    shown: data?.gem_scan?.displayed_gems ?? gems.length,
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

          {/* Three commitments in one quiet line. Deliberately NOT badges:
              these are rules the architecture enforces, and rules read best
              as a plain sentence. */}
          <p className="mt-5 text-xs uppercase tracking-wide text-gray-500">
            {copy.hero.trustLine}
          </p>

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

        {/* 2. Daily research shortlist; technically separate from Gems. */}
        <section aria-labelledby="shortlist-heading" className="mt-16 sm:mt-20">
          <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="mb-2 text-xs font-bold uppercase tracking-widest text-blue-700">
                {copy.home.shortlistEyebrow}
              </p>
              <h2 id="shortlist-heading" className="text-2xl font-bold text-gray-900 sm:text-3xl">
                {copy.home.shortlistHeading}
              </h2>
              <p className="mt-1 max-w-2xl text-sm leading-relaxed text-gray-600">
                {copy.home.shortlistSupporting}
              </p>
              <p className="mt-2 max-w-2xl text-sm font-semibold text-gray-800">
                {copy.home.shortlistDistinction}
              </p>
            </div>
            <Link
              href="/explore"
              onClick={() => track('home_primary_cta', { surface: 'model_shortlist' })}
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

          {!isLoading && !error && shortlist.length > 0 && (
            <div className="grid gap-4 sm:gap-6 lg:grid-cols-2">
              {shortlist.map((item, index) => (
                <ModelShortlistCard
                  key={item.fixture_id}
                  item={item}
                  language={language}
                  displayRank={index + 1}
                  onViewDetails={handleViewDetails}
                />
              ))}
            </div>
          )}

          {!isLoading && !error && shortlist.length === 0 && (
            <div className="rounded-2xl border border-dashed border-blue-200 bg-white p-7 text-center">
              <h3 className="font-bold text-gray-950">{copy.home.noShortlistHeading}</h3>
              <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-gray-600">
                {copy.home.noShortlistBody}
              </p>
            </div>
          )}
        </section>

        {/* 3. Qualified Gems from the latest scan. */}
        <section aria-labelledby="gems-heading" className="mt-16 sm:mt-20">
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

          {!isLoading && !error && (
            <>
              <dl className="mb-4 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-gray-200 bg-gray-200 sm:grid-cols-4">
                {[
                  [scan.fixtures, copy.home.scanFixtures],
                  [scan.predictions, copy.home.scanPredictions],
                  [scan.qualified, copy.home.scanQualified],
                  [scan.shown, copy.home.scanShown],
                ].map(([value, label]) => (
                  <div key={String(label)} className="bg-white px-4 py-4 text-center">
                    <dt className="text-xs leading-tight text-gray-500">{label}</dt>
                    <dd className="mt-1 text-2xl font-bold text-gray-950">{value}</dd>
                  </div>
                ))}
              </dl>

              {rejectionBreakdown.length > 0 && scan.predictions > 0 && (
                <details className="mb-6 rounded-xl border border-slate-200 bg-white px-4 py-3">
                  <summary className="cursor-pointer text-sm font-semibold text-slate-800">
                    {copy.home.diagnosticsHeading}
                  </summary>
                  <p className="mt-3 text-xs leading-relaxed text-slate-500">
                    {copy.home.diagnosticsBody}
                  </p>
                  <dl className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-5">
                    {rejectionBreakdown.map((item) => (
                      <div key={item.code} className="rounded-lg bg-slate-50 px-3 py-3">
                        <dt className="text-xs leading-snug text-slate-600">
                          {rejectionLabels[item.code] ?? item.code}
                        </dt>
                        <dd className="mt-1 text-lg font-bold text-slate-950">
                          {item.fixtures_affected}{' '}
                          <span className="text-xs font-normal text-slate-500">
                            {copy.home.diagnosticsAffected}
                          </span>
                        </dd>
                      </div>
                    ))}
                  </dl>
                </details>
              )}
            </>
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
            <div className="rounded-2xl border border-dashed border-gray-300 bg-white p-8 text-center sm:p-10">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-gray-100">
                <Lock className="h-5 w-5 text-gray-500" />
              </div>
              <h3 className="mt-4 text-lg font-bold text-gray-950">{copy.home.noGemsHeading}</h3>
              <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-gray-600">
                {scan.fixtures} {copy.home.scanFixtures}; {scan.predictions} {copy.home.scanPredictions}.{' '}
                {copy.home.noGemsBody}
              </p>
              <div className="mt-5 flex flex-col justify-center gap-3 sm:flex-row">
                <Link href="/explore" className="font-semibold text-blue-700 underline underline-offset-4">
                  {copy.home.browseAll}
                </Link>
                <Link href="/methodology" className="font-semibold text-blue-700 underline underline-offset-4">
                  {copy.home.methodologyCta}
                </Link>
              </div>
            </div>
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
          {/* Five stages now, so the grid steps 1 → 2 → 3 → 5 across
              breakpoints instead of assuming three. The last two stages —
              Measure and Improve — are why the triad was retired: the old flow
              ended at the result, which reads as a static prediction engine. */}
          <ol className="mt-6 grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
            {copy.workflow.map((step, i) => (
              <li
                key={step.id}
                className="rounded-2xl border border-gray-200 bg-white p-5"
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

        {/* ── 3b. The difference, as a contrast a visitor can read in three
            seconds: everyone else's pipeline stops at the result; ours loops
            back into evaluation. ── */}
        <section aria-labelledby="difference-contrast-heading" className="mt-16 sm:mt-20">
          <h2
            id="difference-contrast-heading"
            className="text-2xl font-bold text-gray-900 sm:text-3xl"
          >
            {copy.home.differenceContrastHeading}
          </h2>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-gray-200 bg-white p-6">
              <p className="text-xs font-bold uppercase tracking-widest text-gray-400">
                {copy.home.differenceOthersLabel}
              </p>
              <p className="mt-4 flex flex-wrap items-center gap-2 text-sm font-semibold text-gray-500">
                {copy.home.differenceOthersFlow.map((step, i) => (
                  <span key={step} className="flex items-center gap-2">
                    {i > 0 && <ArrowRight aria-hidden className="h-4 w-4 text-gray-300" />}
                    <span>{step}</span>
                  </span>
                ))}
              </p>
            </div>
            <div className="rounded-2xl border border-blue-200 bg-blue-50/50 p-6">
              <p className="text-xs font-bold uppercase tracking-widest text-blue-700">
                {copy.home.differenceUsLabel}
              </p>
              <p className="mt-4 flex flex-wrap items-center gap-2 text-sm font-semibold text-gray-800">
                {copy.home.differenceUsFlow.map((step, i) => (
                  <span key={step} className="flex items-center gap-2">
                    {i > 0 && <ArrowRight aria-hidden className="h-4 w-4 text-blue-300" />}
                    <span>{step}</span>
                  </span>
                ))}
              </p>
            </div>
          </div>

          {/* Product rules. Plain bordered cells, no icons, no colour — they
              should look like constraints, because they are. */}
          <div className="mt-6 rounded-2xl border border-gray-200 bg-white p-6">
            <p className="text-xs font-bold uppercase tracking-widest text-gray-400">
              {copy.home.rulesHeading}
            </p>
            <ul className="mt-4 grid gap-3 text-sm font-medium text-gray-800 sm:grid-cols-2 lg:grid-cols-4">
              {copy.home.rules.map((rule) => (
                <li key={rule} className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
                  {rule}
                </li>
              ))}
            </ul>
          </div>
        </section>

        {/* ── 4. Signal vs published proof ────────────────────────────────
            The single most important idea in the product, given its own
            section and shown with the real badges rather than described. */}
        <section
          aria-labelledby="difference-heading"
          className="mt-16 rounded-2xl border border-indigo-200 bg-indigo-50/60 p-6 sm:mt-20 sm:p-8"
        >
          <div className="flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
            <div className="max-w-2xl">
              <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-100 text-indigo-700">
                <Lock className="h-5 w-5" aria-hidden="true" />
              </div>
              <h2 id="difference-heading" className="mt-4 text-2xl font-bold text-gray-900 sm:text-3xl">
                {copy.home.differenceHeading}
              </h2>
              <p className="mt-3 text-base leading-relaxed text-gray-700">
                {copy.home.differenceBody}
              </p>
            </div>
            <Link
              href="/track-record#published-picks"
              className="inline-flex min-h-[44px] shrink-0 items-center justify-center gap-2 rounded-lg bg-gray-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-gray-700"
            >
              {copy.home.openRecord}
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
        </section>

        {/* ── 4b. The three counters, side by side ─────────────────────────
            This strip exists to make "many live signals, 1 commitment,
            0 verified results" read as the NORMAL shape of the funnel rather
            than a contradiction. Each stage links to where it lives. */}
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
              <EmptyState state="no_verified_results" lang={language} />
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

        {/* ── 7b. Continuous improvement — stated without claiming success.
            The honest tense is future-conditional: the record exists to find
            out whether the filtering helps, not to celebrate that it does. ── */}
        <section aria-labelledby="improvement-heading" className="mt-16 sm:mt-20">
          <h2
            id="improvement-heading"
            className="text-2xl font-bold text-gray-900 sm:text-3xl"
          >
            {copy.home.improvementHeading}
          </h2>
          <p className="mt-4 max-w-3xl text-sm leading-relaxed text-gray-600 sm:text-base">
            {copy.home.improvementBody}
          </p>
        </section>

        {/* ── 7c. The manifesto. One authored text shared with About — the
            philosophy must not be paraphrased per-page or it drifts. ── */}
        <section
          aria-labelledby="manifesto-heading"
          className="mt-16 rounded-2xl border border-gray-200 bg-white p-8 sm:mt-20 sm:p-10"
        >
          <h2
            id="manifesto-heading"
            className="max-w-3xl text-xl font-bold leading-snug text-gray-900 sm:text-2xl"
          >
            {copy.manifesto.heading}
          </h2>
          <div className="mt-5 max-w-3xl space-y-4">
            {copy.manifesto.paragraphs.map((paragraph) => (
              <p key={paragraph.slice(0, 24)} className="text-sm leading-relaxed text-gray-600 sm:text-base">
                {paragraph}
              </p>
            ))}
          </div>
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
