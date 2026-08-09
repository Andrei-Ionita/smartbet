'use client'

import { ArrowRight, Check, Clock3, Gem, ShieldCheck, Users } from 'lucide-react'

import type { Lang } from '../lib/terminology'
import type { Recommendation } from '../../src/types/recommendation'

const WORDS = {
  en: {
    qualified: 'Qualified Gem', selection: 'Selected outcome', verifiedPrice: 'Verified price',
    providerChance: 'Provider implied chance', priceAdvantage: 'Above provider baseline',
    leagueEvidence: 'League evidence', books: 'bookmakers checked', fresh: 'price age',
    checks: 'Why it qualified', predictable: 'Fixture marked predictable',
    consensus: 'Correct-score and double-chance signals agree',
    price: 'Fresh multi-bookmaker price passed dispersion checks',
    disclaimer: 'Provider estimate, not a guaranteed outcome or staking instruction.',
    details: 'See fixture context', hours: 'h', unknown: 'Not available',
    updated: 'Gem scan updated',
  },
  ro: {
    qualified: 'Gem calificat', selection: 'Rezultat selectat', verifiedPrice: 'Preț verificat',
    providerChance: 'Șansa implicită a furnizorului', priceAdvantage: 'Peste baza furnizorului',
    leagueEvidence: 'Dovezi din ligă', books: 'case verificate', fresh: 'vechimea prețului',
    checks: 'De ce s-a calificat', predictable: 'Meci marcat ca predictibil',
    consensus: 'Semnalele scor-corect și șansă-dublă sunt aliniate',
    price: 'Preț recent din mai multe case, cu dispersie acceptată',
    disclaimer: 'Estimare a furnizorului, nu rezultat garantat sau instrucțiune de miză.',
    details: 'Vezi contextul meciului', hours: 'h', unknown: 'Indisponibil',
    updated: 'Scanarea Gem actualizată',
  },
} as const

const titleCase = (value: string | null | undefined) =>
  value ? value.charAt(0).toUpperCase() + value.slice(1) : '—'

const percent = (value: number | null | undefined, digits = 0) =>
  typeof value === 'number' && Number.isFinite(value)
    ? `${(value * 100).toFixed(digits)}%`
    : '—'

function kickoffLabel(value: string, language: Lang) {
  const normalized = value.includes('T') ? value : value.replace(' ', 'T') + 'Z'
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(language === 'ro' ? 'ro-RO' : 'en-GB', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  }).format(date)
}

export default function GemCard({
  recommendation,
  language,
  displayRank,
  onViewDetails,
  lastUpdated,
}: {
  recommendation: Recommendation
  language: Lang
  displayRank: number
  onViewDetails: (fixtureId: number) => void
  lastUpdated?: string | null
}) {
  const w = WORDS[language]
  const gem = recommendation.gem
  const rank = gem?.rank ?? displayRank

  return (
    <article className="flex h-full flex-col overflow-hidden rounded-2xl border border-emerald-200 bg-white shadow-sm">
      <div className="border-b border-emerald-100 bg-gradient-to-r from-emerald-50 to-blue-50 p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 text-sm font-bold text-emerald-800">
            <Gem className="h-4 w-4" aria-hidden="true" />
            {w.qualified} #{rank}
          </div>
          <span className="text-xs text-gray-600">{kickoffLabel(recommendation.kickoff, language)}</span>
        </div>
        <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-gray-500">
          {recommendation.league}
        </p>
        <h3 className="mt-1 text-lg font-bold leading-snug text-gray-950">
          {recommendation.home_team} <span className="font-normal text-gray-400">vs</span>{' '}
          {recommendation.away_team}
        </h3>
      </div>

      <div className="flex flex-1 flex-col p-5">
        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-gray-950 p-3 text-white">
            <p className="text-xs text-gray-300">{w.selection}</p>
            <p className="mt-1 font-bold">{recommendation.predicted_outcome}</p>
          </div>
          <div className="rounded-xl border border-gray-200 p-3">
            <p className="text-xs text-gray-500">{w.verifiedPrice}</p>
            <p className="mt-1 text-lg font-bold text-gray-950">
              {recommendation.odds?.toFixed(2) ?? '—'}
            </p>
            <p className="truncate text-xs text-gray-500">{recommendation.bookmaker ?? '—'}</p>
          </div>
        </div>

        <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 border-y border-gray-100 py-4 text-sm">
          <div>
            <dt className="text-xs text-gray-500">{w.providerChance}</dt>
            <dd className="mt-0.5 font-bold text-gray-900">{percent(gem?.provider_implied_chance)}</dd>
          </div>
          <div>
            <dt className="text-xs text-gray-500">{w.priceAdvantage}</dt>
            <dd className="mt-0.5 font-bold text-emerald-700">
              {gem?.verified_price_advantage != null ? `+${percent(gem.verified_price_advantage, 1)}` : '—'}
            </dd>
          </div>
          <div>
            <dt className="text-xs text-gray-500">{w.leagueEvidence}</dt>
            <dd className="mt-0.5 font-semibold text-gray-900">{titleCase(gem?.league_predictability)}</dd>
          </div>
          <div>
            <dt className="flex items-center gap-1 text-xs text-gray-500"><Users className="h-3 w-3" /> {w.books}</dt>
            <dd className="mt-0.5 font-semibold text-gray-900">{gem?.bookmakers_checked ?? '—'}</dd>
          </div>
        </dl>

        <div className="mt-4">
          <p className="flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-gray-700">
            <ShieldCheck className="h-4 w-4 text-emerald-600" /> {w.checks}
          </p>
          <ul className="mt-2 space-y-2 text-xs leading-relaxed text-gray-600">
            {[w.predictable, w.consensus, w.price].map((item) => (
              <li key={item} className="flex gap-2">
                <Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="mt-4 flex items-center gap-1.5 text-xs text-gray-500">
          <Clock3 className="h-3.5 w-3.5" />
          {w.fresh}: {gem?.price_age_hours != null ? `${gem.price_age_hours.toFixed(1)}${w.hours}` : w.unknown}
        </p>
        {lastUpdated && (
          <p className="mt-1 text-xs text-gray-500">
            {w.updated}: {kickoffLabel(lastUpdated, language)}
          </p>
        )}
        <p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-900">
          {w.disclaimer}
        </p>

        <button
          type="button"
          onClick={() => onViewDetails(recommendation.fixture_id)}
          className="mt-4 inline-flex min-h-[42px] items-center justify-center gap-2 rounded-xl border border-gray-300 px-4 text-sm font-semibold text-gray-800 hover:bg-gray-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gray-900"
        >
          {w.details} <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </article>
  )
}
