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
import { PUBLIC_RESULTS_VISIBLE } from '../lib/publicResultsMode'

type Reason = 'potential_value' | 'strategy_match' | 'strong_signal'

interface TrackedSelection {
  selection_id: string
  receipt_url: string
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
  receipt_url: string | null
}

const COPY = {
  en: {
    eyebrow: 'Today’s football selections',
    heading: 'Five fixtures worth a closer look',
    supporting: 'A varied shortlist from current value, strategy and model evidence. Each card tells you exactly why the fixture is here.',
    boundary: 'One selection per fixture. Recorded selections support engine validation; the public performance history is paused until the engine rules are locked.',
    value: 'Potential value', strategy: 'Strategy match', strong: 'Strong signal',
    tracked: 'Recorded for validation', candidate: 'Current candidate',
    selection: 'Selection', odds: 'Verified odds', market: 'Market', books: 'bookmakers checked',
    valueReason: 'The model and the verified market price disagree enough to merit a closer look.',
    strategyReason: 'This fixture matches the registered rules of a named market strategy.',
    strongReason: 'The model separates one outcome clearly from the alternatives.',
    trackedCaveat: 'The selection and displayed price were frozen before kickoff for internal engine validation. No public performance claim is being made.',
    candidateCaveat: 'This is a current research candidate. It is not a performance claim or an instruction to bet.',
    analyse: 'Analyse fixture', learn: 'Understand strategy', receipt: 'Inspect receipt', results: 'Open complete Results',
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
    boundary: 'O selecție pe meci. Selecțiile înregistrate susțin validarea motorului; istoricul public este suspendat până când regulile motorului sunt blocate.',
    value: 'Valoare potențială', strategy: 'Potrivire de strategie', strong: 'Semnal puternic',
    tracked: 'Înregistrată pentru validare', candidate: 'Candidat actual',
    selection: 'Selecție', odds: 'Cotă verificată', market: 'Piață', books: 'operatori verificați',
    valueReason: 'Modelul și cota verificată diferă suficient pentru ca meciul să merite o analiză atentă.',
    strategyReason: 'Meciul corespunde regulilor înregistrate ale unei strategii de piață denumite.',
    strongReason: 'Modelul separă clar un rezultat de alternative.',
    trackedCaveat: 'Selecția și cota afișată au fost blocate înainte de start pentru validarea internă a motorului. Nu reprezintă o afirmație publică de performanță.',
    candidateCaveat: 'Acesta este un candidat actual pentru cercetare. Nu reprezintă o afirmație de performanță sau o recomandare de pariere.',
    analyse: 'Analizează meciul', learn: 'Înțelege strategia', receipt: 'Verifică recipisa', results: 'Deschide toate Rezultatele',
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

function strategyHref(strategyKey: string) {
  const strategy = STRATEGIES.find(item => item.strategyKey === strategyKey)
  return strategy ? `/strategies/${strategy.slug}` : '/strategies'
}

function kickoffLabel(value: string, language: Lang) {
  const date = new Date(value.includes('T') ? value : `${value.replace(' ', 'T')}Z`)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(language === 'ro' ? 'ro-RO' : 'en-GB', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  }).format(date)
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
    receipt_url: item.receipt_url,
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
    receipt_url: null,
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
    receipt_url: null,
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
        {PUBLIC_RESULTS_VISIBLE && <Link href="/track-record" className="shrink-0 font-bold text-blue-700 hover:underline">
          {c.results} <ArrowRight className="inline h-4 w-4" />
        </Link>}
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
        <div className="mt-6 space-y-3">
          {selections.map((item, index) => {
            const reason = item.reason_code
            const config = reason === 'potential_value'
              ? { Icon: BadgeDollarSign, label: c.value, color: 'border-emerald-200 bg-emerald-50 text-emerald-800', panel: 'bg-emerald-50 text-emerald-950', explanation: c.valueReason }
              : reason === 'strategy_match'
                ? { Icon: FlaskConical, label: c.strategy, color: 'border-violet-200 bg-violet-50 text-violet-800', panel: 'bg-violet-50 text-violet-950', explanation: c.strategyReason }
                : { Icon: SearchCheck, label: c.strong, color: 'border-blue-200 bg-blue-50 text-blue-800', panel: 'bg-blue-50 text-blue-950', explanation: c.strongReason }
            return (
              <article key={item.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-blue-200 hover:shadow-md sm:p-5">
                <div className="flex items-start gap-3 sm:gap-4">
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-950 text-sm font-black text-white">{index + 1}</span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-black uppercase tracking-wide ${config.color}`}>
                          <config.Icon className="h-3.5 w-3.5" /> {config.label}
                        </span>
                        {item.strategy_name && <span className="text-xs font-bold text-violet-800">{item.strategy_name}</span>}
                        <span className={`inline-flex items-center gap-1 text-xs font-semibold ${item.tracked ? 'text-emerald-800' : 'text-amber-900'}`}>
                          {item.tracked ? <CheckCircle2 className="h-4 w-4" /> : <Clock3 className="h-4 w-4" />}
                          {item.tracked ? c.tracked : c.candidate}
                        </span>
                      </div>
                      <time dateTime={item.kickoff} className="text-xs text-slate-500">{kickoffLabel(item.kickoff, language)}</time>
                    </div>

                    <div className="mt-3 grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.9fr)_auto] lg:items-center">
                      <div>
                        <p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">{item.league}</p>
                        <h3 className="mt-1 text-lg font-black leading-snug text-slate-950">{item.home_team} <span className="font-medium text-slate-400">vs</span> {item.away_team}</h3>
                        <p className="mt-2 text-sm leading-5 text-slate-600">{config.explanation}</p>
                      </div>
                      <dl className="grid grid-cols-3 gap-2 text-xs">
                        <div className="rounded-xl bg-slate-50 p-2.5"><dt className="text-slate-500">{c.selection}</dt><dd className="mt-1 font-black text-slate-950">{selectionLabel(item.predicted_outcome)}</dd></div>
                        <div className="rounded-xl bg-slate-50 p-2.5"><dt className="text-slate-500">{c.odds}</dt><dd className="mt-1 font-black text-slate-950">{item.odds.toFixed(2)}</dd></div>
                        <div className="rounded-xl bg-slate-50 p-2.5"><dt className="text-slate-500">{c.market}</dt><dd className="mt-1 font-black text-slate-950">{marketLabel(item.market)}{item.bookmaker_count > 0 ? ` · ${item.bookmaker_count} ${c.books}` : ''}</dd></div>
                      </dl>
                      <div className="grid shrink-0 gap-2">
                        <Link href={fixtureHref(item)} className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 text-sm font-bold text-white hover:bg-slate-800">
                          {c.analyse}<ArrowRight className="h-4 w-4" />
                        </Link>
                        {PUBLIC_RESULTS_VISIBLE && item.receipt_url && <Link href={item.receipt_url} className="text-center text-xs font-bold text-blue-800 underline-offset-4 hover:underline">{c.receipt}</Link>}
                        {item.strategy_key && (
                          <Link href={strategyHref(item.strategy_key)} className="text-center text-xs font-bold text-violet-800 underline-offset-4 hover:underline">{c.learn}</Link>
                        )}
                      </div>
                    </div>
                    <p className={`mt-3 rounded-lg px-3 py-2 text-xs leading-5 ${config.panel}`}>{item.tracked ? c.trackedCaveat : c.candidateCaveat}</p>
                  </div>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
