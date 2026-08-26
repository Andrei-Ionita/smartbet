'use client'

import Link from 'next/link'
import useSWR from 'swr'
import { ArrowRight, BadgeDollarSign, CheckCircle2, Clock3, SearchCheck } from 'lucide-react'

import type { Lang } from '../lib/terminology'

type Reason = 'potential_value' | 'strong_signal'

interface TrackedSelection {
  selection_id: string
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  predicted_outcome: string
  odds: number
  bookmaker: string | null
  bookmaker_count: number
  reason_code: Reason
}

interface LiveCandidate {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  leading_selection: string
  verified_price: number
  bookmaker?: string | null
  bookmakers_checked?: number
}

interface DisplaySelection {
  id: string
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  predicted_outcome: string
  odds: number
  bookmaker: string | null
  bookmaker_count: number
  reason_code: Reason
  tracked: boolean
}

const COPY = {
  en: {
    eyebrow: 'Today’s selection board',
    heading: 'Up to five clear fixtures to investigate',
    supporting: 'One clear selection per fixture. Frozen selections enter Results; current candidates remain visible while the next publication check runs.',
    boundary: 'These are BetGlitch selections for decision support—not guarantees or instructions to bet.',
    value: 'Potential value', strong: 'Strong model signal',
    tracked: 'Tracked in Results', candidate: 'Current candidate',
    selection: 'Selection', recordedPrice: 'Recorded odds', currentPrice: 'Current odds', books: 'books checked',
    recorded: 'Frozen before kickoff', awaiting: 'Awaiting the next tracking check',
    analyse: 'Analyse fixture', results: 'Open complete Results',
    loading: 'Loading today’s fixtures…',
    emptyTitle: 'No current fixture passes the board checks',
    emptyBody: 'The next qualifying fixture will appear automatically after a fresh scan.',
    unavailable: 'Today’s selection board is temporarily unavailable.',
  },
  ro: {
    eyebrow: 'Panoul selecțiilor de astăzi',
    heading: 'Până la cinci meciuri clare de analizat',
    supporting: 'O selecție clară pe meci. Selecțiile blocate intră în Rezultate; candidații actuali rămân vizibili până la următoarea verificare de publicare.',
    boundary: 'Acestea sunt selecții BetGlitch pentru sprijinirea deciziei, nu garanții sau instrucțiuni de pariere.',
    value: 'Valoare potențială', strong: 'Semnal puternic',
    tracked: 'Urmărită în Rezultate', candidate: 'Candidat actual',
    selection: 'Selecție', recordedPrice: 'Cotă înregistrată', currentPrice: 'Cotă actuală', books: 'operatori verificați',
    recorded: 'Blocată înainte de start', awaiting: 'Așteaptă următoarea verificare de urmărire',
    analyse: 'Analizează meciul', results: 'Deschide toate Rezultatele',
    loading: 'Încărcăm meciurile de astăzi…',
    emptyTitle: 'Niciun meci actual nu trece verificările panoului',
    emptyBody: 'Următorul meci eligibil va apărea automat după o scanare nouă.',
    unavailable: 'Panoul selecțiilor de astăzi este temporar indisponibil.',
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

function fixtureHref(item: DisplaySelection) {
  return `/prediction/${slug(item.league || 'league')}/${slug(`${item.home_team}-vs-${item.away_team}`)}-${item.kickoff.slice(0, 10)}-${item.fixture_id}`
}

function kickoffTime(value: string) {
  const normalized = value.includes('T') ? value : `${value.replace(' ', 'T')}Z`
  return Date.parse(normalized)
}

function trackedRows(payload: unknown): DisplaySelection[] {
  const body = payload as { selections?: TrackedSelection[] } | undefined
  return (Array.isArray(body?.selections) ? body.selections : []).map(item => ({
    id: `tracked:${item.selection_id}`,
    fixture_id: item.fixture_id,
    home_team: item.home_team,
    away_team: item.away_team,
    league: item.league,
    kickoff: item.kickoff,
    predicted_outcome: item.predicted_outcome,
    odds: Number(item.odds),
    bookmaker: item.bookmaker,
    bookmaker_count: item.bookmaker_count,
    reason_code: item.reason_code,
    tracked: true,
  }))
}

function candidateRows(payload: unknown): DisplaySelection[] {
  const body = payload as { decision_board?: { price_watchlist?: LiveCandidate[]; strong_signals?: LiveCandidate[] } } | undefined
  const board = body?.decision_board
  const lanes: Array<[Reason, LiveCandidate[]]> = [
    ['potential_value', Array.isArray(board?.price_watchlist) ? board.price_watchlist : []],
    ['strong_signal', Array.isArray(board?.strong_signals) ? board.strong_signals : []],
  ]
  return lanes.flatMap(([reason, rows]) => rows.map(item => ({
    id: `candidate:${reason}:${item.fixture_id}`,
    fixture_id: item.fixture_id,
    home_team: item.home_team,
    away_team: item.away_team,
    league: item.league,
    kickoff: item.kickoff,
    predicted_outcome: item.leading_selection,
    odds: Number(item.verified_price),
    bookmaker: item.bookmaker ?? null,
    bookmaker_count: Number(item.bookmakers_checked ?? 0),
    reason_code: reason,
    tracked: false,
  })))
}

export default function HomepageSelections({ language }: { language: Lang }) {
  const c = COPY[language]
  const trackedFeed = useSWR(
    '/api/results-selections?category=homepage&state=pending', fetcher,
    { refreshInterval: 120_000, revalidateOnFocus: true, errorRetryCount: 2 },
  )
  const candidateFeed = useSWR(
    '/api/recommendations/', fetcher,
    { refreshInterval: 120_000, revalidateOnFocus: true, errorRetryCount: 2 },
  )

  const now = Date.now()
  const seen = new Set<number>()
  const selections = [...trackedRows(trackedFeed.data), ...candidateRows(candidateFeed.data)]
    .filter(item => Number.isFinite(item.odds) && item.odds > 1 && kickoffTime(item.kickoff) > now)
    .filter(item => {
      if (seen.has(item.fixture_id)) return false
      seen.add(item.fixture_id)
      return true
    })
    .slice(0, 5)
  const loading = selections.length === 0 && (trackedFeed.isLoading || candidateFeed.isLoading)
  const unavailable = selections.length === 0 && Boolean(trackedFeed.error && candidateFeed.error)

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

      {loading ? (
        <div role="status" className="mt-6 rounded-2xl border border-slate-200 bg-white p-8 text-center text-slate-600">{c.loading}</div>
      ) : unavailable ? (
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
              <article key={item.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex flex-wrap gap-2">
                    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-black uppercase tracking-wide ${value ? 'bg-emerald-50 text-emerald-800' : 'bg-blue-50 text-blue-800'}`}>
                      <Icon className="h-3.5 w-3.5" /> {value ? c.value : c.strong}
                    </span>
                    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-black uppercase tracking-wide ${item.tracked ? 'bg-slate-950 text-white' : 'bg-amber-50 text-amber-900'}`}>
                      {item.tracked ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Clock3 className="h-3.5 w-3.5" />}
                      {item.tracked ? c.tracked : c.candidate}
                    </span>
                  </div>
                  <span className="text-sm font-black text-slate-400">#{index + 1}</span>
                </div>
                <p className="mt-4 text-[11px] font-bold uppercase tracking-wide text-slate-500">{item.league}</p>
                <h3 className="mt-1 text-xl font-black text-slate-950">{item.home_team} <span className="font-medium text-slate-400">vs</span> {item.away_team}</h3>
                <dl className="mt-5 grid grid-cols-2 gap-3 text-sm">
                  <div className="rounded-xl bg-slate-50 p-3"><dt className="text-slate-500">{c.selection}</dt><dd className="mt-1 font-black text-slate-950">{item.predicted_outcome}</dd></div>
                  <div className="rounded-xl bg-slate-50 p-3"><dt className="text-slate-500">{item.tracked ? c.recordedPrice : c.currentPrice}</dt><dd className="mt-1 font-black text-slate-950">{item.odds.toFixed(2)}</dd></div>
                </dl>
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
                  <span className={`inline-flex items-center gap-1.5 text-xs font-semibold ${item.tracked ? 'text-emerald-800' : 'text-amber-900'}`}>
                    {item.tracked ? <CheckCircle2 className="h-4 w-4" /> : <Clock3 className="h-4 w-4" />}
                    {item.tracked ? c.recorded : c.awaiting}{item.bookmaker_count > 0 ? ` · ${item.bookmaker_count} ${c.books}` : ''}
                  </span>
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
