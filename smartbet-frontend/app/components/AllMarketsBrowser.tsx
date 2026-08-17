'use client'

import { useMemo, useState } from 'react'
import { ChevronDown, Search, ShieldCheck } from 'lucide-react'
import type {
  FixtureMarketCatalogue,
  MarketCatalogueCategory,
  MarketConsiderationStatus,
} from '../lib/marketCatalogue'

interface AllMarketsBrowserProps {
  catalogue?: FixtureMarketCatalogue | null
  asianHandicapResearch?: {
    status: 'shadow'
    candidates_evaluated: number
    robust_edge_bounds: number
  } | null
  ro: boolean
}

type CategoryFilter = 'all' | MarketCatalogueCategory

const CATEGORY_LABELS: Record<CategoryFilter, { en: string; ro: string }> = {
  all: { en: 'All', ro: 'Toate' },
  popular: { en: 'Popular', ro: 'Populare' },
  handicaps: { en: 'Handicaps', ro: 'Handicapuri' },
  goals: { en: 'Goals', ro: 'Goluri' },
  team: { en: 'Team', ro: 'Echipă' },
  halves: { en: 'Halves & time', ro: 'Reprize și timp' },
  scores: { en: 'Scores', ro: 'Scoruri' },
  cards_corners: { en: 'Cards & corners', ro: 'Cartonașe și cornere' },
  specials: { en: 'Specials', ro: 'Speciale' },
}

const STATUS_COPY: Record<MarketConsiderationStatus, { en: string; ro: string; className: string }> = {
  modelled: {
    en: 'Model + prices',
    ro: 'Model + cote',
    className: 'bg-emerald-50 text-emerald-700',
  },
  shadow: {
    en: 'Shadow evaluation',
    ro: 'Evaluare în umbră',
    className: 'bg-violet-50 text-violet-700',
  },
  prices_only: {
    en: 'Prices only',
    ro: 'Doar cote',
    className: 'bg-slate-100 text-slate-600',
  },
}

const CATEGORY_ORDER: CategoryFilter[] = [
  'all', 'popular', 'handicaps', 'goals', 'team', 'halves', 'scores', 'cards_corners', 'specials',
]

export default function AllMarketsBrowser({ catalogue, asianHandicapResearch, ro }: AllMarketsBrowserProps) {
  const [query, setQuery] = useState('')
  const [category, setCategory] = useState<CategoryFilter>('all')

  const categories = useMemo(() => {
    const available = new Set(catalogue?.markets.map((market) => market.category) ?? [])
    return CATEGORY_ORDER.filter((item) => item === 'all' || available.has(item))
  }, [catalogue])

  const markets = useMemo(() => {
    const needle = query.trim().toLowerCase()
    return (catalogue?.markets ?? []).filter((market) => {
      if (category !== 'all' && market.category !== category) return false
      if (!needle) return true
      return market.name.toLowerCase().includes(needle) || market.lines.some((line) =>
        line.selections.some((selection) => selection.label.toLowerCase().includes(needle)))
    })
  }, [catalogue, category, query])

  const scoreDistributionResearch = useMemo(() => {
    const ids = new Set(catalogue?.markets.map((market) => market.market_id) ?? [])
    const families = [
      ids.has(6) || ids.has(104) ? (ro ? 'Handicap asiatic' : 'Asian Handicap') : null,
      ids.has(7) || ids.has(105) ? (ro ? 'Linii asiatice de goluri' : 'Asian goal lines') : null,
      ids.has(86) ? (ro ? 'Total goluri pe echipă' : 'Team totals') : null,
    ]
    return families.filter((family): family is string => Boolean(family))
  }, [catalogue, ro])

  if (!catalogue?.markets.length) return null

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:p-7">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-600">
            {ro ? 'TOATE PIEȚELE DISPONIBILE' : 'ALL AVAILABLE MARKETS'}
          </p>
          <h3 className="mt-1 text-xl font-bold text-slate-950">
            {ro ? 'Explorează fiecare piață oferită pentru acest meci' : 'Explore every market offered for this fixture'}
          </h3>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-600">
            {ro
              ? 'Cotele sunt grupate pe piață și linie. O piață vizibilă nu este automat o recomandare; eticheta arată dacă are model, este evaluată în umbră sau are doar cote.'
              : 'Prices are grouped by market and line. Visibility is not a recommendation; each badge shows whether the market has model coverage, is under shadow evaluation, or is price-only.'}
          </p>
        </div>
        <div className="grid shrink-0 grid-cols-3 gap-2 text-center text-xs">
          <SummaryMetric value={catalogue.market_count} label={ro ? 'piețe' : 'markets'} />
          <SummaryMetric value={catalogue.selection_count} label={ro ? 'selecții' : 'selections'} />
          <SummaryMetric value={catalogue.bookmaker_count} label={ro ? 'case' : 'books'} />
        </div>
      </div>

      <div className="mt-5 rounded-xl border border-blue-100 bg-blue-50/60 p-4 text-xs leading-relaxed text-blue-950">
        <div className="flex items-start gap-2">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-blue-700" />
          <p>
            {ro
              ? `${catalogue.modelled_market_count} piețe au acoperire de model, iar ${catalogue.shadow_market_count} sunt urmărite pentru validare.${asianHandicapResearch ? ` Motorul a evaluat ${asianHandicapResearch.candidates_evaluated} linii Asian Handicap pentru acest meci.` : ''} Numai strategiile care trec testele de probabilitate, preț, decontare și performanță pot deveni Gems.`
              : `${catalogue.modelled_market_count} markets have model coverage and ${catalogue.shadow_market_count} are tracked for validation.${asianHandicapResearch ? ` The engine evaluated ${asianHandicapResearch.candidates_evaluated} Asian Handicap lines for this fixture.` : ''} Only strategies that pass probability, price, settlement and performance tests can become Gems.`}
          </p>
        </div>
      </div>

      {scoreDistributionResearch.length > 0 && (
        <div className="mt-3 rounded-xl border border-violet-200 bg-violet-50/60 p-4">
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-violet-700 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide text-white">
              {ro ? 'Laborator de strategii · colectăm dovezi' : 'Strategies Lab · collecting evidence'}
            </span>
            {scoreDistributionResearch.map((family) => (
              <span key={family} className="rounded-full bg-white px-2.5 py-1 text-xs font-semibold text-violet-800 ring-1 ring-violet-200">
                {family}
              </span>
            ))}
          </div>
          <p className="mt-2 text-xs leading-relaxed text-violet-950">
            {ro
              ? 'Modelul de scor testează fiecare linie la o cotă înregistrată înainte de start, inclusiv decontarea corectă a liniilor sfert. Acestea sunt strategii de cercetare, nu recomandări; vor deveni eligibile numai după un eșantion forward suficient și verificări statistice.'
              : 'The score model tests each line at a price recorded before kickoff, including correct quarter-line settlement. These are research strategies, not recommendations; they become eligible only after enough forward evidence and statistical checks.'}
          </p>
        </div>
      )}

      <div className="mt-5 flex flex-col gap-3">
        <label className="relative block">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder={ro ? 'Caută piață sau selecție' : 'Search market or selection'}
            className="min-h-[44px] w-full rounded-xl border border-slate-300 bg-white pl-10 pr-3 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
          />
        </label>
        <div className="flex gap-2 overflow-x-auto pb-1" aria-label={ro ? 'Categorii de piețe' : 'Market categories'}>
          {categories.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setCategory(item)}
              className={`whitespace-nowrap rounded-full px-3 py-1.5 text-xs font-semibold transition ${
                category === item ? 'bg-slate-950 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {ro ? CATEGORY_LABELS[item].ro : CATEGORY_LABELS[item].en}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-5 space-y-3">
        {markets.map((market, index) => {
          const status = STATUS_COPY[market.consideration_status]
          return (
            <details key={market.market_id} className="group overflow-hidden rounded-xl border border-slate-200" open={index === 0 && !query}>
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 bg-slate-50 px-4 py-3 hover:bg-slate-100">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold text-slate-950">{market.name}</span>
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${status.className}`}>
                      {ro ? status.ro : status.en}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {market.selection_count} {ro ? 'selecții' : 'selections'} · {market.bookmaker_count} {ro ? 'case' : 'books'}
                  </p>
                </div>
                <ChevronDown className="h-4 w-4 shrink-0 text-slate-500 transition group-open:rotate-180" />
              </summary>
              <div className="space-y-4 p-4">
                {market.lines.map((line) => (
                  <div key={line.key}>
                    {line.label && <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{line.label}</p>}
                    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                      {line.selections.map((selection) => (
                        <div key={selection.key} className="rounded-lg border border-slate-200 bg-white p-3">
                          <div className="flex items-start justify-between gap-3">
                            <p className="min-w-0 font-medium text-slate-900">{selection.label}</p>
                            <p className="shrink-0 text-lg font-bold text-slate-950">{selection.reference_price.toFixed(2)}</p>
                          </div>
                          <div className="mt-2 flex items-end justify-between gap-3 text-xs text-slate-500">
                            <span className="truncate">{selection.bookmaker}</span>
                            <span className="shrink-0">
                              {selection.bookmaker_count} {ro ? 'case' : 'books'} · {selection.price_min.toFixed(2)}–{selection.price_max.toFixed(2)}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </details>
          )
        })}

        {!markets.length && (
          <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center text-sm text-slate-500">
            {ro ? 'Nicio piață nu corespunde căutării.' : 'No markets match this search.'}
          </div>
        )}
      </div>
    </section>
  )
}

function SummaryMetric({ value, label }: { value: number; label: string }) {
  return (
    <div className="min-w-[74px] rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
      <p className="text-lg font-bold text-slate-950">{value}</p>
      <p className="text-slate-500">{label}</p>
    </div>
  )
}
