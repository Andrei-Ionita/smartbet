'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import {
  Archive,
  ArrowRight,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  LockKeyhole,
  Search,
  Sparkles,
  Trophy,
  XCircle,
} from 'lucide-react'

import ProofCapturePanel from '../components/ProofCapturePanel'
import { StatusBadge, statusFromClaim } from '../components/StatusBadge'
import { useLanguage } from '../contexts/LanguageContext'
import {
  CURRENT_STRATEGY_VERSION,
  FLAT_STAKE,
  partitionStrategyClaims,
  summarizeStrategyRecord,
} from '../lib/currentStrategyRecord'
import { VALUE_STRATEGY_POLICY } from '../lib/providerStrategy'
import { getCopy } from '../lib/terminology'

interface PublishedClaimRow {
  claim_id: string
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  market_type: string
  predicted_outcome: string
  model_score_percent: number
  odds: number
  bookmaker: string | null
  odds_captured_at: string | null
  published_at: string
  price_age_hours_at_publication: number | null
  price_fresh_at_publication: boolean
  ranking_version: string | null
  claim_state: 'PENDING' | 'WON' | 'LOST' | 'VOID' | 'CANCELLED'
  pricing_integrity_status: string
  claim_hash: string
  claim_hash_version: string
  integrity_ok: boolean
  superseded: boolean
  supersedes: string | null
  is_correction: boolean
  proof_url: string
  result: {
    status: string
    settled_at: string
    actual_score_home: number | null
    actual_score_away: number | null
    result_source: string
  } | null
  counts_towards_verified_record: boolean
}

function exclusionReason(claim: PublishedClaimRow, lang?: string) {
  const copy = getCopy(lang).record
  if (claim.superseded) return copy.publishedExcludedSuperseded
  if (!claim.integrity_ok) return copy.publishedExcludedIntegrity
  if (claim.claim_state === 'VOID') return copy.publishedExcludedVoid
  if (claim.claim_state === 'CANCELLED') return copy.publishedExcludedCancelled
  if (!claim.price_fresh_at_publication) {
    return claim.price_age_hours_at_publication === null
      ? copy.publishedExcludedMissingPrice
      : copy.publishedExcludedStalePrice(claim.price_age_hours_at_publication.toFixed(1))
  }
  return copy.publishedExcludedGeneric
}

function PublishedPickRow({
  claim,
  language,
  historical = false,
}: {
  claim: PublishedClaimRow
  language: string
  historical?: boolean
}) {
  const rec = getCopy(language).record
  const redesign = getCopy(language).recordRedesign
  const formatDate = (date: string) =>
    new Date(date).toLocaleDateString(language === 'ro' ? 'ro-RO' : 'en-GB', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    })
  const score = claim.result &&
    claim.result.actual_score_home !== null &&
    claim.result.actual_score_away !== null
    ? `${claim.result.actual_score_home}–${claim.result.actual_score_away}`
    : null

  return (
    <li className="py-5 first:pt-0 last:pb-0">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge
              status={statusFromClaim(claim.claim_state, claim.result?.status ?? null)}
              size="sm"
              lang={language}
            />
            {historical && (
              <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-600">
                {redesign.historicalVersionLabel}
              </span>
            )}
          </div>
          <h3 className="mt-3 text-base font-bold text-gray-950">
            {claim.home_team} <span className="font-normal text-gray-400">vs</span>{' '}
            {claim.away_team}
          </h3>
          <p className="mt-1 text-sm text-gray-600">
            {claim.league} · {claim.market_type} / {claim.predicted_outcome}
          </p>
          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-gray-600">
            <span>
              {rec.publishedOddsLabel}: <strong>{claim.odds.toFixed(2)}</strong>
              {claim.bookmaker ? ` · ${claim.bookmaker}` : ''}
            </span>
            <span>{rec.publishedAtLabel}: {formatDate(claim.published_at)}</span>
            {score && <span className="font-semibold text-gray-900">{score}</span>}
          </div>
          <p className="mt-2 flex items-start gap-2 text-sm text-gray-600">
            {claim.counts_towards_verified_record ? (
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
            ) : claim.claim_state === 'PENDING' ? (
              <Clock3 className="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
            ) : (
              <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" />
            )}
            <span>
              {claim.counts_towards_verified_record
                ? rec.publishedCountedIn
                : claim.claim_state === 'PENDING'
                  ? rec.publishedNotCounted
                  : exclusionReason(claim, language)}
            </span>
          </p>
        </div>

        <Link
          href={claim.proof_url}
          className="inline-flex min-h-11 shrink-0 items-center gap-2 self-start rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-800 hover:bg-gray-50"
        >
          {rec.publishedProofLink}
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

      <details className="mt-3 text-xs text-gray-600">
        <summary className="cursor-pointer font-semibold text-gray-700">
          {language === 'ro' ? 'Detalii de verificare' : 'Verification details'}
        </summary>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2 rounded-lg bg-gray-50 p-3">
          {claim.price_age_hours_at_publication !== null && (
            <span>
              {rec.publishedPriceAgeLabel}:{' '}
              {claim.price_age_hours_at_publication < 1
                ? `${Math.round(claim.price_age_hours_at_publication * 60)}m`
                : `${claim.price_age_hours_at_publication.toFixed(1)}h`}
            </span>
          )}
          <span className="break-all font-mono">
            {rec.publishedVersionLabel}: {claim.ranking_version ?? 'unreported'}
          </span>
        </div>
      </details>
    </li>
  )
}

export default function TrackRecordContent() {
  const { language } = useLanguage()
  const copy = getCopy(language)
  const rec = copy.record
  const redesign = copy.recordRedesign
  const [claims, setClaims] = useState<PublishedClaimRow[] | null>(null)
  const [claimsError, setClaimsError] = useState(false)

  const loadClaims = async () => {
    setClaimsError(false)
    try {
      const response = await fetch('/api/published-claims', {
        cache: 'no-store',
      })
      const data = await response.json()
      if (!response.ok || !data.success || !Array.isArray(data.claims)) {
        throw new Error('claims unavailable')
      }
      setClaims(data.claims as PublishedClaimRow[])
    } catch {
      setClaims(null)
      setClaimsError(true)
    }
  }

  useEffect(() => {
    loadClaims()
  }, [])

  useEffect(() => {
    const jumpToHash = () => {
      const id = decodeURIComponent(window.location.hash.replace('#', ''))
      if (!id) return
      document.getElementById(id)?.scrollIntoView({ block: 'start' })
    }
    const timer = window.setTimeout(jumpToHash, 100)
    window.addEventListener('hashchange', jumpToHash)
    return () => {
      window.clearTimeout(timer)
      window.removeEventListener('hashchange', jumpToHash)
    }
  }, [claims])

  const partitioned = useMemo(
    () => partitionStrategyClaims(claims ?? []),
    [claims],
  )
  const summary = useMemo(
    () => summarizeStrategyRecord(partitioned.current),
    [partitioned.current],
  )
  const roiLabel = summary.roiPercent === null
    ? null
    : `${summary.roiPercent > 0 ? '+' : ''}${summary.roiPercent.toFixed(1)}`
  const profitLabel = `${summary.profit > 0 ? '+' : summary.profit < 0 ? '−' : ''}$${Math.abs(summary.profit).toFixed(2)}`

  const journey = [
    { icon: Search, title: redesign.flowExploreTitle, body: redesign.flowExploreBody },
    { icon: Sparkles, title: redesign.flowGemTitle, body: redesign.flowGemBody },
    { icon: LockKeyhole, title: redesign.flowPublishTitle, body: redesign.flowPublishBody },
    { icon: ClipboardCheck, title: redesign.flowResultTitle, body: redesign.flowResultBody },
  ]

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-8 sm:py-10">
          <p className="text-xs font-bold uppercase tracking-[0.2em] text-blue-700">
            {redesign.eyebrow}
          </p>
          <div className="mt-3 flex items-start gap-3">
            <Trophy className="mt-1 h-8 w-8 shrink-0 text-blue-600" />
            <div>
              <h1 className="text-3xl font-bold tracking-tight text-gray-950 sm:text-4xl">
                {redesign.title}
              </h1>
              <p className="mt-3 max-w-3xl text-base leading-relaxed text-gray-600 sm:text-lg">
                {redesign.intro}
              </p>
            </div>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:py-12">
        <section aria-label={redesign.title} className="rounded-2xl border border-gray-200 bg-white p-5 sm:p-7">
          <div className="grid gap-4 md:grid-cols-4">
            {journey.map((step, index) => {
              const Icon = step.icon
              return (
                <div key={step.title} className="relative rounded-xl bg-slate-50 p-4">
                  <div className="flex items-center gap-3">
                    <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-100 text-blue-700">
                      <Icon className="h-5 w-5" />
                    </span>
                    <span className="text-xs font-bold text-gray-400">0{index + 1}</span>
                  </div>
                  <h2 className="mt-3 font-bold text-gray-950">{step.title}</h2>
                  <p className="mt-1 text-sm leading-relaxed text-gray-600">{step.body}</p>
                </div>
              )
            })}
          </div>
          <p className="mt-5 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm leading-relaxed text-blue-950">
            {redesign.boundary}
          </p>
        </section>

        <span id="verified-record" className="scroll-mt-24" aria-hidden="true" />
        <section
          id="results"
          aria-labelledby="results-heading"
          className="mt-8 scroll-mt-24 rounded-2xl border border-gray-200 bg-white p-5 sm:p-7"
        >
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 id="results-heading" className="text-2xl font-bold text-gray-950">
                {redesign.currentHeading}
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-gray-600">
                {redesign.currentBody}
              </p>
            </div>
            <span className="self-start rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-800">
              {redesign.currentVersionLabel}: Gen {VALUE_STRATEGY_POLICY.generation}
            </span>
          </div>

          {claimsError ? (
            <div role="alert" className="mt-6 rounded-xl border border-amber-300 bg-amber-50 p-5">
              <p className="text-sm text-gray-700">{rec.publishedError}</p>
              <button
                type="button"
                onClick={loadClaims}
                className="mt-3 min-h-11 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-800"
              >
                {rec.publishedRetry}
              </button>
            </div>
          ) : claims === null ? (
            <div role="status" className="mt-6 grid animate-pulse gap-3 sm:grid-cols-4">
              {[1, 2, 3, 4].map((item) => (
                <div key={item} className="h-28 rounded-xl bg-gray-100" />
              ))}
            </div>
          ) : partitioned.current.length === 0 ? (
            <div className="mt-6 rounded-2xl border border-dashed border-blue-300 bg-blue-50/60 p-6 sm:p-8">
              <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white text-blue-700 shadow-sm">
                <Sparkles className="h-5 w-5" />
              </div>
              <h3 className="mt-4 text-xl font-bold text-gray-950">{redesign.zeroHeading}</h3>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-gray-700">
                {redesign.zeroBody}
              </p>
              <div className="mt-5 flex flex-wrap gap-4">
                <Link href="/explore" className="font-semibold text-blue-700 hover:underline">
                  {redesign.zeroAction} →
                </Link>
                <Link href="/methodology" className="font-semibold text-gray-700 hover:underline">
                  {copy.home.methodologyCta} →
                </Link>
              </div>
            </div>
          ) : (
            <>
              <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
                {[
                  [redesign.summaryPublished, summary.published],
                  [redesign.summaryPending, summary.pending],
                  [redesign.summarySettled, summary.counted],
                  [redesign.summaryRecord, `${summary.won}W – ${summary.lost}L`],
                ].map(([label, value]) => (
                  <div key={String(label)} className="rounded-xl border border-gray-200 bg-slate-50 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</p>
                    <p className="mt-2 text-3xl font-bold text-gray-950">{value}</p>
                  </div>
                ))}
                <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-emerald-800">
                    {redesign.summaryReturn}
                  </p>
                  <p className="mt-2 text-3xl font-bold text-gray-950">
                    {summary.counted > 0 ? profitLabel : '—'}
                  </p>
                  <p className="mt-1 text-xs text-gray-600">
                    {summary.counted > 0 && roiLabel
                      ? redesign.summaryReturnDetail(summary.totalStaked, roiLabel)
                      : redesign.summaryReturnEmpty}
                  </p>
                </div>
              </div>

              {summary.counted > 0 && summary.counted < 30 && (
                <p className="mt-4 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm leading-relaxed text-amber-950">
                  {language === 'ro'
                    ? `Doar ${summary.counted} selecții încheiate: este prea puțin pentru a afirma că strategia are un avantaj.`
                    : `Only ${summary.counted} settled picks: this is too little evidence to claim the strategy has an edge.`}
                </p>
              )}
            </>
          )}
        </section>

        <span id="public-commitments" className="scroll-mt-24" aria-hidden="true" />
        <section
          id="published-picks"
          aria-labelledby="published-picks-heading"
          className="mt-8 scroll-mt-24 rounded-2xl border border-gray-200 bg-white p-5 sm:p-7"
        >
          <h2 id="published-picks-heading" className="text-xl font-bold text-gray-950">
            {redesign.currentPicksHeading}
          </h2>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-gray-600">
            {redesign.currentPicksBody}
          </p>

          {claims !== null && partitioned.current.length === 0 && (
            <p className="mt-5 rounded-xl bg-gray-50 p-4 text-sm text-gray-600">
              {redesign.currentPicksEmpty}
            </p>
          )}
          {partitioned.current.length > 0 && (
            <ul className="mt-6 divide-y divide-gray-200">
              {partitioned.current.map((claim) => (
                <PublishedPickRow key={claim.claim_id} claim={claim} language={language} />
              ))}
            </ul>
          )}
        </section>

        {partitioned.historical.length > 0 && (
          <section className="mt-8 rounded-2xl border border-gray-200 bg-white p-5 sm:p-7">
            <div className="flex items-start gap-3">
              <Archive className="mt-0.5 h-6 w-6 shrink-0 text-gray-500" />
              <div>
                <h2 className="text-xl font-bold text-gray-950">{redesign.historicalHeading}</h2>
                <p className="mt-2 max-w-3xl text-sm leading-relaxed text-gray-600">
                  {redesign.historicalBody}
                </p>
              </div>
            </div>
            <details className="mt-5 rounded-xl border border-gray-200 bg-slate-50 p-4">
              <summary className="cursor-pointer font-semibold text-gray-900">
                {redesign.historicalOpen} · {redesign.historicalSummary(partitioned.historical.length)}
              </summary>
              <ul className="mt-5 divide-y divide-gray-200 border-t border-gray-200 pt-5">
                {partitioned.historical.map((claim) => (
                  <PublishedPickRow
                    key={claim.claim_id}
                    claim={claim}
                    language={language}
                    historical
                  />
                ))}
              </ul>
            </details>
          </section>
        )}

        <div className="mt-8">
          <ProofCapturePanel
            source="track_record_page"
            title={rec.capturePanelTitle}
            description={rec.capturePanelBody}
          />
        </div>

        <p className="mx-auto mt-6 max-w-3xl text-center text-xs leading-relaxed text-gray-500">
          {rec.policyBody}
        </p>
        <p className="mt-3 text-center text-sm">
          <Link href="/proof/anchors" className="font-semibold text-blue-700 hover:underline">
            {language === 'ro'
              ? 'Detalii tehnice de verificare'
              : 'Technical verification details'}{' '}
            →
          </Link>
        </p>
        <span className="sr-only">{CURRENT_STRATEGY_VERSION} · ${FLAT_STAKE} flat stake</span>
      </main>
    </div>
  )
}
