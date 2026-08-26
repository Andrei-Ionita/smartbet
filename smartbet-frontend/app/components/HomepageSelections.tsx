'use client'

import Link from 'next/link'
import useSWR from 'swr'
import {
  ArrowRight,
  BadgeDollarSign,
  CheckCircle2,
  Clock3,
  FlaskConical,
  SearchCheck,
} from 'lucide-react'

import { STRATEGIES } from '../lib/strategyLibrary'
import type { Lang } from '../lib/terminology'
import type { StrategyFit } from '../lib/useStrategyFits'

type Reason = 'potential_value' | 'strategy_match' | 'strong_signal'

interface TrackedSelection {
  selection_id: string
  category: 'homepage' | 'strategy'
  source_key: string
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  market_type: string
  predicted_outcome: string
  odds: number
  bookmaker_count: number
  reason_code: Reason
}

interface LiveSignal {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  leading_selection: string
  verified_price: number
  bookmakers_checked?: number
}

interface StrategyHighlight {
  strategy_key: string
  fit: StrategyFit
}

interface DisplaySelection {
  id: string
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  market: string
  predicted_outcome: string
  odds: number
  bookmaker_count: number
  reason_code: Reason
  tracked: boolean
  strategy_key: string | null
  strategy_name: string | null
}

const COPY = {
  en: {
    eyebrow: 'Today’s football selections',
    heading: 'Five fixtures worth a closer look',
    supporting: 'A varied shortlist from current value, strategy and model evidence. Each card tells you exactly why the fixture is here.',
    boundary: 'One selection per fixture. Frozen selections enter Results; current candidates do not count until they are recorded before kickoff.',
    value: 'Potential value', strategy: 'Strategy match', strong: 'Strong signal',
    tracked: 'Tracked in Results', candidate: 'Current candidate',
    selection: 'Selection', odds: 'Odds', books: 'books',
    analyse: 'Analyse fixture', results: 'Open complete Results',
    loading: 'Building today’s varied fixture list…',
    partial: 'Some current evidence is temporarily unavailable; the valid selections we do have remain visible.',
    emptyTitle: 'No current fixture passes the board checks',
    emptyBody: 'The next qualifying fixture will appear automatically after a fresh scan.',
    unavailable: 'Today’s selection board is temporarily unavailable.',
  },
  ro: {
    eyebrow: 'Selecțiile de fotbal de astăzi',
    heading: 'Cinci meciuri care merită analizate',
    supporting: 'O listă variată bazată pe valoare, strategii și semnalele actuale ale modelului. Fiecare card explică exact de ce apare meciul.',
    boundary: 'O selecție pe meci. Selecțiile blocate intră în Rezultate; candidații actuali nu sunt numărați până când nu sunt înregistrați înainte de start.',
    value: 'Valoare potențială', strategy: 'Potrivire de strategie', strong: 'Semnal puternic',
    tracked: 'Urmărită în Rezultate', candidate: 'Candidat actual',
    selection: 'Selecție', odds: 'Cotă', books: 'operatori',
    analyse: 'Analizează meciul', results: 'Deschide toate Rezultatele',
    loading: 'Construim lista variată de meciuri de astăzi…',
    partial: 'Unele dovezi actuale sunt temporar indisponibile; selecțiile valide disponibile rămân vizibile.',
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

function strategyName(strategyKey: string, language: Lang) {
  return STRATEGIES.find(item => item.strategyKey === strategyKey)?.copy[language].shortName
    ?? strategyKey.split('-').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
}

function marketLabel(value: string) {
  const known: Record<string, string> = {
    '1x2': '1X2',
    btts: 'BTTS',
    asian_handicap: 'Asian handicap',
    asian_goal_line: 'Asian totals',
    team_total: 'Team total',
    correct_score: 'Correct score',
    double_chance: 'Double chance',
  }
  if (known[value.toLowerCase()]) return known[value.toLowerCase()]
  const total = value.match(/^over_under_(\d+)_(\d+)$/i)
  if (total) return `O/U ${total[1]}.${total[2]}`
  return value.replace(/_/g, ' ')
}

function selectionLabel(value: string) {
  return /^(home|away|draw|yes|no|over|under)$/i.test(value)
    ? value.charAt(0).toUpperCase() + value.slice(1).toLowerCase()
    : value
}

function trackedRows(payload: unknown, language: Lang): DisplaySelection[] {
  const body = payload as { selections?: TrackedSelection[] } | undefined
  return (Array.isArray(body?.selections) ? body.selections : []).map(item => ({
    id: `tracked:${item.selection_id}`,
    fixture_id: item.fixture_id,
    home_team: item.home_team,
    away_team: item.away_team,
    league: item.league,
    kickoff: item.kickoff,
    market: item.market_type,
    predicted_outcome: item.predicted_outcome,
    odds: Number(item.odds),
    bookmaker_count: Number(item.bookmaker_count ?? 0),
    reason_code: item.reason_code,
    tracked: true,
    strategy_key: item.category === 'strategy' ? item.source_key : null,
    strategy_name: item.category === 'strategy' ? strategyName(item.source_key, language) : null,
  }))
}

function liveSignalRows(payload: unknown): DisplaySelection[] {
  const body = payload as { decision_board?: { price_watchlist?: LiveSignal[]; strong_signals?: LiveSignal[] } } | undefined
  const board = body?.decision_board
  const lanes: Array<['potential_value' | 'strong_signal', LiveSignal[]]> = [
    ['potential_value', Array.isArray(board?.price_watchlist) ? board.price_watchlist : []],
    ['strong_signal', Array.isArray(board?.strong_signals) ? board.strong_signals : []],
  ]
  return lanes.flatMap(([reason, rows]) => rows.map(item => ({
    id: `signal:${reason}:${item.fixture_id}`,
    fixture_id: item.fixture_id,
    home_team: item.home_team,
    away_team: item.away_team,
    league: item.league,
    kickoff: item.kickoff,
    market: '1X2',
    predicted_outcome: item.leading_selection,
    odds: Number(item.verified_price),
    bookmaker_count: Number(item.bookmakers_checked ?? 0),
    reason_code: reason,
    tracked: false,
    strategy_key: null,
    strategy_name: null,
  })))
}

function liveStrategyRows(payload: unknown, language: Lang): DisplaySelection[] {
  const body = payload as { data?: { highlights?: StrategyHighlight[] }; highlights?: StrategyHighlight[] } | undefined
  const highlights = body?.data?.highlights ?? body?.highlights ?? []
  return (Array.isArray(highlights) ? highlights : []).map(item => ({
    id: `strategy:${item.strategy_key}:${item.fit.fixture_id}`,
    fixture_id: item.fit.fixture_id,
    home_team: item.fit.home_team,
    away_team: item.fit.away_team,
    league: item.fit.league,
    kickoff: item.fit.kickoff,
    market: item.fit.market,
    predicted_outcome: item.fit.selection,
    odds: Number(item.fit.odds),
    bookmaker_count: Number(item.fit.bookmaker_count ?? 0),
    reason_code: 'strategy_match' as const,
    tracked: false,
    strategy_key: item.strategy_key,
    strategy_name: strategyName(item.strategy_key, language),
  }))
}

function curateFive(rows: DisplaySelection[]) {
  const valid = rows.filter(item => Number.isFinite(item.odds) && item.odds > 1 && kickoffTime(item.kickoff) > Date.now())
  const values = valid.filter(item => item.reason_code === 'potential_value')
  const strategies = valid.filter(item => item.reason_code === 'strategy_match')
  const strong = valid.filter(item => item.reason_code === 'strong_signal')
  const selected: DisplaySelection[] = []
  const fixtures = new Set<number>()
  const strategyKeys = new Set<string>()

  const add = (item?: DisplaySelection) => {
    if (!item || selected.length >= 5 || fixtures.has(item.fixture_id)) return false
    if (item.strategy_key && strategyKeys.has(item.strategy_key)) return false
    selected.push(item)
    fixtures.add(item.fixture_id)
    if (item.strategy_key) strategyKeys.add(item.strategy_key)
    return true
  }
  const addFirst = (pool: DisplaySelection[]) => add(pool.find(item => !fixtures.has(item.fixture_id)
    && (!item.strategy_key || !strategyKeys.has(item.strategy_key))))

  addFirst(values)
  addFirst(strategies)
  addFirst(strong)
  addFirst(strategies)
  addFirst(strategies)
  for (const item of [...values, ...strong, ...strategies]) add(item)
  return selected
}

export default function HomepageSelections({ language }: { language: Lang }) {
  const c = COPY[language]
  const homepageTracked = useSWR('/api/results-selections?category=homepage&state=pending', fetcher, { refreshInterval: 120_000, revalidateOnFocus: true, errorRetryCount: 2 })
  const strategyTracked = useSWR('/api/results-selections?category=strategy&state=pending', fetcher, { refreshInterval: 120_000, revalidateOnFocus: true, errorRetryCount: 2 })
  const signals = useSWR('/api/recommendations/', fetcher, { refreshInterval: 120_000, revalidateOnFocus: true, errorRetryCount: 2 })
  const strategyFits = useSWR('/api/homepage-strategy-fits', fetcher, { refreshInterval: 120_000, revalidateOnFocus: true, errorRetryCount: 2 })

  const trackedHomepage = trackedRows(homepageTracked.data, language)
  const trackedStrategies = trackedRows(strategyTracked.data, language)
  const liveSignals = liveSignalRows(signals.data)
  const liveStrategies = liveStrategyRows(strategyFits.data, language)
  const selections = curateFive([
    ...trackedHomepage,
    ...trackedStrategies,
    ...liveSignals,
    ...liveStrategies,
  ])
  const feeds = [homepageTracked, strategyTracked, signals, strategyFits]
  const loading = selections.length === 0 && feeds.some(feed => feed.isLoading)
  const unavailable = selections.length === 0 && feeds.every(feed => Boolean(feed.error))
  const partial = selections.length > 0 && feeds.some(feed => Boolean(feed.error))

  return (
    <section aria-labelledby="homepage-selections-heading" className="mt-12 sm:mt-16">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-blue-700">{c.eyebrow}</p>
          <h2 id="homepage-selections-heading" className="mt-2 text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">{c.heading}</h2>
          <p className="mt-3 max-w-3xl leading-7 text-slate-600">{c.supporting}</p>
          <p className="mt-2 max-w-4xl text-sm font-semibold text-slate-800">{c.boundary}</p>
        </div>
        <Link href="/track-record" className="shrink-0 font-bold text-blue-700 hover:underline">
          {c.results} <ArrowRight className="inline h-4 w-4" />
        </Link>
      </div>

      {partial && <p className="mt-5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">{c.partial}</p>}
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
        <div className="-mx-4 mt-6 overflow-x-auto px-4 pb-3 [scrollbar-width:thin]">
          <div className="grid min-w-max auto-cols-[82vw] grid-flow-col gap-4 sm:auto-cols-[320px] xl:min-w-0 xl:auto-cols-auto xl:grid-flow-row xl:grid-cols-5">
            {selections.map((item, index) => {
              const reason = item.reason_code
              const config = reason === 'potential_value'
                ? { Icon: BadgeDollarSign, label: c.value, color: 'bg-emerald-50 text-emerald-800' }
                : reason === 'strategy_match'
                  ? { Icon: FlaskConical, label: c.strategy, color: 'bg-violet-50 text-violet-800' }
                  : { Icon: SearchCheck, label: c.strong, color: 'bg-blue-50 text-blue-800' }
              return (
                <article key={item.id} className="flex min-h-[360px] flex-col rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-md">
                  <div className="flex items-start justify-between gap-2">
                    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[10px] font-black uppercase tracking-wide ${config.color}`}>
                      <config.Icon className="h-3.5 w-3.5" /> {config.label}
                    </span>
                    <span className="text-sm font-black text-slate-400">#{index + 1}</span>
                  </div>
                  {item.strategy_name && <p className="mt-3 text-xs font-black text-violet-800">{item.strategy_name}</p>}
                  <p className={`${item.strategy_name ? 'mt-1' : 'mt-4'} text-[10px] font-bold uppercase tracking-wide text-slate-500`}>{item.league}</p>
                  <h3 className="mt-1 text-lg font-black leading-snug text-slate-950">{item.home_team} <span className="font-medium text-slate-400">vs</span> {item.away_team}</h3>
                  <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
                    <div className="col-span-2 rounded-xl bg-slate-50 p-3"><dt className="text-slate-500">{c.selection}</dt><dd className="mt-1 font-black text-slate-950">{selectionLabel(item.predicted_outcome)}</dd></div>
                    <div className="rounded-xl bg-slate-50 p-3"><dt className="text-slate-500">{c.odds}</dt><dd className="mt-1 font-black text-slate-950">{item.odds.toFixed(2)}</dd></div>
                    <div className="min-w-0 rounded-xl bg-slate-50 p-3"><dt className="break-words text-slate-500">{marketLabel(item.market)}</dt><dd className="mt-1 font-black text-slate-950">{item.bookmaker_count || '—'} {item.bookmaker_count ? c.books : ''}</dd></div>
                  </dl>
                  <div className="mt-auto pt-4">
                    <p className={`flex items-center gap-1.5 text-xs font-semibold ${item.tracked ? 'text-emerald-800' : 'text-amber-900'}`}>
                      {item.tracked ? <CheckCircle2 className="h-4 w-4" /> : <Clock3 className="h-4 w-4" />}
                      {item.tracked ? c.tracked : c.candidate}
                    </p>
                    <Link href={fixtureHref(item)} className="mt-3 inline-flex min-h-[42px] w-full items-center justify-center gap-2 rounded-xl bg-slate-950 px-3 text-sm font-bold text-white hover:bg-slate-800">
                      {c.analyse}<ArrowRight className="h-4 w-4" />
                    </Link>
                  </div>
                </article>
              )
            })}
          </div>
        </div>
      )}
    </section>
  )
}
