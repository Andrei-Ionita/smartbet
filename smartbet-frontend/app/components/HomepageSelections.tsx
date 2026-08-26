'use client'

import Link from 'next/link'
import useSWR from 'swr'
import { ArrowRight, BadgeDollarSign, CheckCircle2, SearchCheck } from 'lucide-react'

import type { Lang } from '../lib/terminology'

interface TrackedSelection {
  selection_id: string
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  market_type: string
  predicted_outcome: string
  odds: number
  bookmaker: string | null
  bookmaker_count: number
  published_at: string
  reason_code: 'potential_value' | 'strong_signal'
  status: string
}

const COPY = {
  en: {
    eyebrow: 'Today’s selections',
    heading: 'Five clear fixtures, permanently tracked',
    supporting: 'One selection per fixture, frozen before kickoff with its displayed price. Every outcome remains in Results.',
    boundary: 'These are BetGlitch selections, not guarantees or instructions to bet.',
    value: 'Potential value', strong: 'Strong model signal',
    selection: 'Selection', price: 'Recorded odds', books: 'books checked',
    analyse: 'Analyse fixture', results: 'Open complete Results',
    loading: 'Loading today’s frozen selections…',
    emptyTitle: 'No tracked selection is active right now',
    emptyBody: 'The next qualifying selections will appear automatically and will be recorded before kickoff.',
    unavailable: 'Today’s selections are temporarily unavailable.',
  },
  ro: {
    eyebrow: 'Selecțiile de astăzi',
    heading: 'Cinci meciuri clare, urmărite permanent',
    supporting: 'O singură selecție pe meci, blocată înainte de start împreună cu cota afișată. Fiecare rezultat rămâne în Rezultate.',
    boundary: 'Acestea sunt selecții BetGlitch, nu garanții sau instrucțiuni de pariere.',
    value: 'Valoare potențială', strong: 'Semnal puternic',
    selection: 'Selecție', price: 'Cotă înregistrată', books: 'case verificate',
    analyse: 'Analizează meciul', results: 'Deschide toate Rezultatele',
    loading: 'Încărcăm selecțiile blocate de astăzi…',
    emptyTitle: 'Nu există acum o selecție activă urmărită',
    emptyBody: 'Următoarele selecții eligibile vor apărea automat și vor fi înregistrate înainte de start.',
    unavailable: 'Selecțiile de astăzi sunt temporar indisponibile.',
  },
} as const

const fetcher = async (url: string) => {
  const response = await fetch(url)
  if (!response.ok) throw new Error(String(response.status))
  return response.json()
}

function slug(value: string) {
  return value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'fixture'
}

function fixtureHref(item: TrackedSelection) {
  return `/prediction/${slug(item.league || 'league')}/${slug(`${item.home_team}-vs-${item.away_team}`)}-${item.kickoff.slice(0, 10)}-${item.fixture_id}`
}

export default function HomepageSelections({ language }: { language: Lang }) {
  const c = COPY[language]
  const { data, error, isLoading } = useSWR(
    '/api/results-selections?category=homepage&state=pending',
    fetcher,
    { refreshInterval: 120_000, revalidateOnFocus: true, errorRetryCount: 2 },
  )
  const now = Date.now()
  const selections: TrackedSelection[] = (Array.isArray(data?.selections) ? data.selections : [])
    .filter((item: TrackedSelection) => Date.parse(item.kickoff) > now)
    .sort((a: TrackedSelection, b: TrackedSelection) => Date.parse(a.kickoff) - Date.parse(b.kickoff))
    .slice(0, 5)

  return (
    <section aria-labelledby="homepage-selections-heading" className="mt-12 sm:mt-16">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-blue-700">{c.eyebrow}</p>
          <h2 id="homepage-selections-heading" className="mt-2 text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">{c.heading}</h2>
          <p className="mt-3 max-w-3xl leading-7 text-slate-600">{c.supporting}</p>
          <p className="mt-2 text-sm font-semibold text-slate-800">{c.boundary}</p>
        </div>
        <Link href="/track-record?category=homepage" className="shrink-0 font-bold text-blue-700 hover:underline">
          {c.results} <ArrowRight className="inline h-4 w-4" />
        </Link>
      </div>

      {isLoading ? (
        <div role="status" className="mt-6 rounded-2xl border border-slate-200 bg-white p-8 text-center text-slate-600">{c.loading}</div>
      ) : error ? (
        <div role="alert" className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-6 text-amber-950">{c.unavailable}</div>
      ) : selections.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-dashed border-blue-300 bg-blue-50/60 p-7 text-center">
          <h3 className="font-black text-slate-950">{c.emptyTitle}</h3>
          <p className="mt-2 text-sm text-slate-600">{c.emptyBody}</p>
        </div>
      ) : (
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          {selections.map((item, index) => {
            const value = item.reason_code === 'potential_value'
            const Icon = value ? BadgeDollarSign : SearchCheck
            return (
              <article key={item.selection_id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-black uppercase tracking-wide ${value ? 'bg-emerald-50 text-emerald-800' : 'bg-blue-50 text-blue-800'}`}>
                    <Icon className="h-3.5 w-3.5" /> {value ? c.value : c.strong}
                  </span>
                  <span className="text-sm font-black text-slate-400">#{index + 1}</span>
                </div>
                <p className="mt-4 text-[11px] font-bold uppercase tracking-wide text-slate-500">{item.league}</p>
                <h3 className="mt-1 text-xl font-black text-slate-950">{item.home_team} <span className="font-medium text-slate-400">vs</span> {item.away_team}</h3>
                <dl className="mt-5 grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-xl bg-slate-50 p-3"><dt className="text-slate-500">{c.selection}</dt><dd className="mt-1 font-black text-slate-950">{item.predicted_outcome}</dd></div>
                  <div className="rounded-xl bg-slate-50 p-3"><dt className="text-slate-500">{c.price}</dt><dd className="mt-1 font-black text-slate-950">{item.odds.toFixed(2)}</dd></div>
                </dl>
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
                  <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-800"><CheckCircle2 className="h-4 w-4" />{item.bookmaker_count} {c.books}</span>
                  <Link href={fixtureHref(item)} className="font-bold text-blue-700 hover:underline">{c.analyse} →</Link>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
