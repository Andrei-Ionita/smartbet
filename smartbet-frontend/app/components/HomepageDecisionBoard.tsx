'use client'

import Link from 'next/link'
import useSWR from 'swr'
import {
  ArrowRight,
  BadgeDollarSign,
  FlaskConical,
  SearchCheck,
  ShieldAlert,
} from 'lucide-react'

import type { ModelShortlistItem } from '../../src/types/recommendation'
import type { Lang } from '../lib/terminology'
import { STRATEGIES } from '../lib/strategyLibrary'
import type { StrategyFit } from '../lib/useStrategyFits'

interface StrategyHighlight {
  strategy_key: string
  version: string
  market: string
  evidence_status: string
  generated_at: string
  fit: StrategyFit
}

type SignalKind = 'value' | 'strong'
type RankedItem =
  | { kind: SignalKind; fixtureId: number; signal: ModelShortlistItem }
  | { kind: 'strategy'; fixtureId: number; highlight: StrategyHighlight }

const COPY = {
  en: {
    eyebrow: 'Today’s football research',
    heading: 'Five fixtures worth a closer look',
    supporting: 'Ranked starting points from today’s scan. The badge tells you exactly why each fixture is here.',
    boundary: 'Potential value first, then strategy matches, then model-only signals · one card per fixture · none are published picks',
    valueBadge: 'Potential value',
    strategyBadge: 'Strategy match',
    strongBadge: 'Strong model signal',
    processing: 'Building today’s ranked fixture list.',
    strategyLoading: 'Strategy matches are still being checked.',
    partiallyUnavailable: 'Some research sources are temporarily unavailable. Available current evidence is still shown.',
    unavailable: 'Today’s research list is temporarily unavailable.',
    empty: 'No current fixture has enough evidence to enter today’s ranked list.',
    leading: 'Leading outcome',
    signalRank: 'Signal strength',
    verifiedPrice: 'Verified odds',
    marketView: 'Market view',
    modelView: 'Model view',
    inspect: 'Analyse fixture',
    learn: 'Understand strategy',
    valueReason: 'The model and verified market price disagree enough to merit a closer look.',
    valueCaveat: 'Positive price evidence, but this fixture did not pass every stricter Gem test.',
    strongReason: 'The model separates one outcome clearly from the alternatives.',
    strongCaveat: 'The signal is clear, but the available price has no verified edge.',
    strategyReason: 'This fixture currently matches a registered market strategy.',
    strategyCaveat: 'The strategy remains experimental; a match does not prove profitability.',
    exploreAll: 'Explore all fixtures',
  },
  ro: {
    eyebrow: 'Analiza de fotbal de astăzi',
    heading: 'Cinci meciuri care merită analizate',
    supporting: 'Puncte de pornire ordonate din scanarea de astăzi. Eticheta arată exact de ce apare fiecare meci.',
    boundary: 'Întâi valoarea potențială, apoi strategiile și semnalele modelului · un card per meci · nu sunt selecții publicate',
    valueBadge: 'Valoare potențială',
    strategyBadge: 'Potrivire de strategie',
    strongBadge: 'Semnal puternic al modelului',
    processing: 'Construim lista ordonată de astăzi.',
    strategyLoading: 'Potrivirile strategiilor sunt încă verificate.',
    partiallyUnavailable: 'Unele surse de analiză sunt temporar indisponibile. Dovezile actuale disponibile rămân afișate.',
    unavailable: 'Lista de analiză de astăzi este temporar indisponibilă.',
    empty: 'Niciun meci actual nu are suficiente dovezi pentru lista de astăzi.',
    leading: 'Rezultat principal',
    signalRank: 'Puterea semnalului',
    verifiedPrice: 'Cotă verificată',
    marketView: 'Viziunea pieței',
    modelView: 'Viziunea modelului',
    inspect: 'Analizează meciul',
    learn: 'Înțelege strategia',
    valueReason: 'Modelul și prețul verificat diferă suficient pentru a merita o analiză atentă.',
    valueCaveat: 'Dovadă pozitivă de preț, dar meciul nu a trecut toate filtrele Gem.',
    strongReason: 'Modelul separă clar un rezultat de alternative.',
    strongCaveat: 'Semnalul este clar, dar prețul disponibil nu are un avantaj verificat.',
    strategyReason: 'Meciul se potrivește acum unei strategii de piață înregistrate.',
    strategyCaveat: 'Strategia este experimentală; potrivirea nu dovedește profitabilitatea.',
    exploreAll: 'Explorează toate meciurile',
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

function strategyFixtureHref(fit: StrategyFit) {
  const date = fit.kickoff.slice(0, 10)
  return `/prediction/${slug(fit.league || 'league')}/${slug(`${fit.home_team}-vs-${fit.away_team}`)}-${date}-${fit.fixture_id}`
}

function kickoffLabel(value: string, language: Lang) {
  const normalized = value.includes('T') ? value : `${value.replace(' ', 'T')}Z`
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(language === 'ro' ? 'ro-RO' : 'en-GB', {
    day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  }).format(date)
}

function modelLabel(fit: StrategyFit) {
  const probability = fit.probability
  if (probability.kind === 'bounded_score_distribution') {
    return `${probability.model_probability_low_percent ?? '—'}%–${probability.model_probability_high_percent ?? '—'}%`
  }
  return probability.model_probability_percent == null
    ? '—'
    : `${probability.model_probability_percent}%`
}

function ReasonBadge({ kind, language }: { kind: RankedItem['kind']; language: Lang }) {
  const c = COPY[language]
  const config = {
    value: {
      icon: BadgeDollarSign,
      label: c.valueBadge,
      style: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    },
    strategy: {
      icon: FlaskConical,
      label: c.strategyBadge,
      style: 'border-violet-200 bg-violet-50 text-violet-800',
    },
    strong: {
      icon: SearchCheck,
      label: c.strongBadge,
      style: 'border-blue-200 bg-blue-50 text-blue-800',
    },
  }[kind]
  const Icon = config.icon
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-black uppercase tracking-wide ${config.style}`}>
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      {config.label}
    </span>
  )
}

function Rank({ value }: { value: number }) {
  return (
    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-950 text-sm font-black text-white">
      {value}
    </span>
  )
}

function SignalRow({
  item,
  language,
  kind,
  rank,
}: {
  item: ModelShortlistItem
  language: Lang
  kind: SignalKind
  rank: number
}) {
  const c = COPY[language]
  const value = kind === 'value'
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-blue-200 hover:shadow-md sm:p-5">
      <div className="flex items-start gap-3 sm:gap-4">
        <Rank value={rank} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <ReasonBadge kind={kind} language={language} />
            <span className="text-xs text-slate-500">{kickoffLabel(item.kickoff, language)}</span>
          </div>
          <div className="mt-3 grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(310px,0.85fr)_auto] lg:items-center">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">{item.league}</p>
              <h3 className="mt-1 text-lg font-black leading-snug text-slate-950">
                {item.home_team} <span className="font-medium text-slate-400">vs</span> {item.away_team}
              </h3>
              <p className="mt-2 text-sm leading-5 text-slate-600">{value ? c.valueReason : c.strongReason}</p>
            </div>
            <dl className="grid grid-cols-3 gap-2 text-xs">
              <div className="rounded-xl bg-slate-50 p-2.5"><dt className="text-slate-500">{c.leading}</dt><dd className="mt-1 font-black text-slate-950">{item.leading_selection}</dd></div>
              <div className="rounded-xl bg-slate-50 p-2.5"><dt className="text-slate-500">{c.signalRank}</dt><dd className="mt-1 font-black text-slate-950">{Math.round(item.signal_strength * 100)}/100</dd></div>
              <div className="rounded-xl bg-slate-50 p-2.5"><dt className="text-slate-500">{c.verifiedPrice}</dt><dd className="mt-1 font-black text-slate-950">{item.verified_price.toFixed(2)}</dd></div>
            </dl>
            <Link href={`/explore?fixture=${item.fixture_id}`} className="inline-flex min-h-[44px] shrink-0 items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 text-sm font-bold text-white hover:bg-slate-800">
              {c.inspect}<ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <p className={`mt-3 rounded-lg px-3 py-2 text-xs leading-5 ${value ? 'bg-emerald-50 text-emerald-950' : 'bg-blue-50 text-blue-950'}`}>
            {value ? c.valueCaveat : c.strongCaveat}
          </p>
        </div>
      </div>
    </article>
  )
}

function StrategyRow({
  highlight,
  language,
  rank,
}: {
  highlight: StrategyHighlight
  language: Lang
  rank: number
}) {
  const c = COPY[language]
  const strategy = STRATEGIES.find(item => item.strategyKey === highlight.strategy_key)
  if (!strategy) return null
  const fit = highlight.fit
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:border-violet-200 hover:shadow-md sm:p-5">
      <div className="flex items-start gap-3 sm:gap-4">
        <Rank value={rank} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <ReasonBadge kind="strategy" language={language} />
              <span className="text-xs font-bold text-violet-800">{strategy.copy[language].shortName}</span>
            </div>
            <span className="text-xs text-slate-500">{kickoffLabel(fit.kickoff, language)}</span>
          </div>
          <div className="mt-3 grid gap-4 lg:grid-cols-[minmax(0,1.15fr)_minmax(310px,0.85fr)_auto] lg:items-center">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">{fit.league}</p>
              <h3 className="mt-1 text-lg font-black leading-snug text-slate-950">
                {fit.home_team} <span className="font-medium text-slate-400">vs</span> {fit.away_team}
              </h3>
              <p className="mt-2 text-sm leading-5 text-slate-600">{c.strategyReason}</p>
            </div>
            <dl className="grid grid-cols-3 gap-2 text-xs">
              <div className="rounded-xl bg-violet-50 p-2.5"><dt className="text-violet-700">{c.marketView}</dt><dd className="mt-1 font-black text-violet-950">{fit.selection}</dd></div>
              <div className="rounded-xl bg-slate-50 p-2.5"><dt className="text-slate-500">{c.verifiedPrice}</dt><dd className="mt-1 font-black text-slate-950">{fit.odds.toFixed(2)}</dd></div>
              <div className="rounded-xl bg-blue-50 p-2.5"><dt className="text-blue-700">{c.modelView}</dt><dd className="mt-1 font-black text-blue-950">{modelLabel(fit)}</dd></div>
            </dl>
            <div className="grid shrink-0 gap-2">
              <Link href={strategyFixtureHref(fit)} className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 text-sm font-bold text-white hover:bg-slate-800">{c.inspect}<ArrowRight className="h-4 w-4" /></Link>
              <Link href={`/strategies/${strategy.slug}`} className="text-center text-xs font-bold text-violet-800 underline-offset-4 hover:underline">{c.learn}</Link>
            </div>
          </div>
          <p className="mt-3 rounded-lg bg-violet-50 px-3 py-2 text-xs leading-5 text-violet-950">{c.strategyCaveat}</p>
        </div>
      </div>
    </article>
  )
}

export default function HomepageDecisionBoard({
  language,
  valueWatchlist,
  strongSignals,
  status,
  recommendationsLoading,
  recommendationsError,
}: {
  language: Lang
  valueWatchlist: ModelShortlistItem[]
  strongSignals: ModelShortlistItem[]
  status: string
  recommendationsLoading: boolean
  recommendationsError: boolean
}) {
  const c = COPY[language]
  const { data, error: strategyError, isLoading: strategiesLoading } = useSWR(
    '/api/homepage-strategy-fits', fetcher, {
      refreshInterval: 120000,
      revalidateOnFocus: true,
      errorRetryCount: 2,
    },
  )

  const rankedItems: RankedItem[] = []
  const usedIds = new Set<number>()
  const add = (item: RankedItem) => {
    if (rankedItems.length >= 5 || usedIds.has(item.fixtureId)) return
    rankedItems.push(item)
    usedIds.add(item.fixtureId)
  }
  const recommendationsReady = status === 'ready'
    && !recommendationsLoading
    && !recommendationsError
  const strategiesReady = !strategiesLoading && !strategyError
  const allHighlights: StrategyHighlight[] = data?.data?.highlights
    ?? data?.highlights
    ?? []

  if (recommendationsReady) {
    valueWatchlist.forEach(signal => add({ kind: 'value', fixtureId: signal.fixture_id, signal }))
  }
  if (strategiesReady) {
    allHighlights.forEach(highlight => add({
      kind: 'strategy',
      fixtureId: highlight.fit.fixture_id,
      highlight,
    }))
  }
  if (recommendationsReady) {
    strongSignals.forEach(signal => add({ kind: 'strong', fixtureId: signal.fixture_id, signal }))
  }

  const allSourcesUnavailable = rankedItems.length === 0
    && (recommendationsError || status === 'delayed')
    && Boolean(strategyError)
  const partiallyUnavailable = rankedItems.length > 0
    && (recommendationsError || status === 'delayed' || Boolean(strategyError))
  const loading = rankedItems.length === 0
    && (recommendationsLoading || strategiesLoading || status === 'pending_refresh')

  return (
    <section aria-labelledby="decision-board-heading" className="mt-12 sm:mt-16">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-blue-700">{c.eyebrow}</p>
          <h2 id="decision-board-heading" className="mt-2 text-2xl font-black text-slate-950 sm:text-3xl">{c.heading}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{c.supporting}</p>
          <p className="mt-2 max-w-4xl text-xs font-semibold leading-5 text-slate-700">{c.boundary}</p>
        </div>
        <Link href="/explore" className="shrink-0 text-sm font-bold text-blue-700 underline-offset-4 hover:underline">{c.exploreAll} →</Link>
      </div>

      {partiallyUnavailable && (
        <p className="mt-5 flex items-start gap-2 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">
          <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />{c.partiallyUnavailable}
        </p>
      )}
      {strategiesLoading && rankedItems.length > 0 && (
        <p className="mt-4 text-xs text-slate-500">{c.strategyLoading}</p>
      )}

      <div className="mt-6 space-y-3">
        {rankedItems.map((item, index) => item.kind === 'strategy'
          ? <StrategyRow key={`strategy:${item.fixtureId}`} highlight={item.highlight} language={language} rank={index + 1} />
          : <SignalRow key={`${item.kind}:${item.fixtureId}`} item={item.signal} language={language} kind={item.kind} rank={index + 1} />)}
      </div>

      {loading && (
        <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-600">{c.processing}</div>
      )}
      {allSourcesUnavailable && (
        <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-6 text-center text-sm text-amber-950">{c.unavailable}</div>
      )}
      {!loading && !allSourcesUnavailable && rankedItems.length === 0 && (
        <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-white p-6 text-center text-sm text-slate-600">{c.empty}</div>
      )}
    </section>
  )
}
