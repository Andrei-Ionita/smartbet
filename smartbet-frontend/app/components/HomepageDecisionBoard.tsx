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

const COPY = {
  en: {
    eyebrow: 'Today’s decision board',
    heading: 'Different evidence, clearly separated',
    supporting: 'A fixture appears for one specific reason: a price disagreement, a registered strategy fit, or a clear model signal. None of these research cards is a published pick.',
    boundary: 'Up to six current research starting points · no duplicated fixtures · Hidden Gems remain separate',
    valueTitle: 'Price watchlist',
    valueBody: 'The price model supports the same outcome, and the verified odds are meaningfully above its baseline.',
    valueEmpty: 'No verified price disagreement is current. We will not fill this lane with ordinary favourites.',
    strategyTitle: 'Strategy opportunities',
    strategyBody: 'Current fixtures that fit a registered market hypothesis. These strategies remain experimental.',
    strategyEmpty: 'No distinct strategy fit is current after removing fixtures already shown elsewhere.',
    strategyUnavailable: 'The live strategy scan is temporarily unavailable. No stale fit is displayed.',
    strongTitle: 'Strong signals — no verified price edge',
    strongBody: 'Clear model separation and supporting evidence. This lane ranks consensus, not price value.',
    strongEmpty: 'No distinct strong signal is current after removing fixtures already shown elsewhere.',
    processing: 'The first compatible decision-board scan is still processing.',
    strategyLoading: 'Checking the latest registered strategy fits.',
    unavailable: 'The current research snapshot is temporarily unavailable.',
    priceModel: 'Price model aligned',
    clearSignal: 'Clear signal · no verified edge',
    experimental: 'Experimental strategy fit',
    leading: 'Leading signal',
    signalRank: 'Signal rank',
    verifiedPrice: 'Verified price',
    marketView: 'Market view',
    breakEven: 'Break-even',
    modelView: 'Model view',
    inspect: 'Investigate fixture',
    learn: 'Learn strategy',
    valueCaveat: 'It still failed at least one stricter Gem qualification gate.',
    strongCaveat: 'This is consensus context—not evidence that the available odds are valuable.',
    strategyCaveat: 'A research fit is not evidence that the strategy is profitable.',
    exploreAll: 'Explore all fixtures',
  },
  ro: {
    eyebrow: 'Panoul decizional de astăzi',
    heading: 'Dovezi diferite, separate clar',
    supporting: 'Un meci apare dintr-un singur motiv: o diferență de preț, potrivirea cu o strategie înregistrată sau un semnal clar al modelului. Niciun card de cercetare nu este o selecție publicată.',
    boundary: 'Până la șase puncte de pornire actuale · fără meciuri duplicate · Hidden Gems rămân separate',
    valueTitle: 'Lista diferențelor de preț',
    valueBody: 'Modelul de preț susține același rezultat, iar cota verificată este semnificativ peste referința sa.',
    valueEmpty: 'Nu există acum o diferență de preț verificată. Nu umplem această zonă cu favorite obișnuite.',
    strategyTitle: 'Oportunități de strategie',
    strategyBody: 'Meciuri actuale care se potrivesc unei ipoteze de piață înregistrate. Strategiile sunt încă experimentale.',
    strategyEmpty: 'Nu există acum o potrivire distinctă după eliminarea meciurilor deja afișate.',
    strategyUnavailable: 'Scanarea live a strategiilor este temporar indisponibilă. Nu afișăm potriviri vechi.',
    strongTitle: 'Semnale puternice — fără avantaj de preț verificat',
    strongBody: 'Separare clară în model și dovezi suplimentare. Această zonă ordonează consensul, nu valoarea cotei.',
    strongEmpty: 'Nu există acum un semnal distinct după eliminarea meciurilor deja afișate.',
    processing: 'Prima scanare compatibilă a panoului decizional este încă în procesare.',
    strategyLoading: 'Verificăm cele mai recente potriviri ale strategiilor înregistrate.',
    unavailable: 'Snapshotul actual de cercetare este temporar indisponibil.',
    priceModel: 'Modelul de preț este aliniat',
    clearSignal: 'Semnal clar · fără avantaj verificat',
    experimental: 'Potrivire experimentală',
    leading: 'Semnal principal',
    signalRank: 'Rangul semnalului',
    verifiedPrice: 'Cotă verificată',
    marketView: 'Viziunea pieței',
    breakEven: 'Prag',
    modelView: 'Viziunea modelului',
    inspect: 'Analizează meciul',
    learn: 'Înțelege strategia',
    valueCaveat: 'Meciul nu a trecut cel puțin un filtru Gem mai strict.',
    strongCaveat: 'Acesta este context de consens, nu dovadă că prețul disponibil are valoare.',
    strategyCaveat: 'O potrivire de cercetare nu dovedește că strategia este profitabilă.',
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

function Lane({
  icon: Icon,
  title,
  body,
  tone,
  children,
}: {
  icon: typeof BadgeDollarSign
  title: string
  body: string
  tone: 'emerald' | 'violet' | 'blue'
  children: React.ReactNode
}) {
  const styles = {
    emerald: 'border-emerald-200 bg-emerald-50/50 text-emerald-800',
    violet: 'border-violet-200 bg-violet-50/50 text-violet-800',
    blue: 'border-blue-200 bg-blue-50/50 text-blue-800',
  }[tone]
  return (
    <section className={`rounded-3xl border p-4 sm:p-5 ${styles}`}>
      <div className="flex items-start gap-3">
        <span className="rounded-xl bg-white p-2 shadow-sm"><Icon className="h-5 w-5" aria-hidden="true" /></span>
        <div>
          <h3 className="font-black text-slate-950">{title}</h3>
          <p className="mt-1 text-xs leading-5 text-slate-600">{body}</p>
        </div>
      </div>
      <div className="mt-4 space-y-3">{children}</div>
    </section>
  )
}

function EmptyLane({ children }: { children: React.ReactNode }) {
  return <p className="rounded-2xl border border-dashed border-slate-300 bg-white/80 p-4 text-sm leading-6 text-slate-600">{children}</p>
}

function SignalCard({
  item,
  language,
  kind,
}: {
  item: ModelShortlistItem
  language: Lang
  kind: 'value' | 'strong'
}) {
  const c = COPY[language]
  const value = kind === 'value'
  return (
    <article className="rounded-2xl border border-white bg-white p-4 text-slate-950 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <p className={`text-[11px] font-black uppercase tracking-wider ${value ? 'text-emerald-700' : 'text-blue-700'}`}>
          {value ? c.priceModel : c.clearSignal}
        </p>
        <span className="shrink-0 text-[11px] text-slate-500">{kickoffLabel(item.kickoff, language)}</span>
      </div>
      <p className="mt-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{item.league}</p>
      <h4 className="mt-1 font-black leading-snug">{item.home_team} <span className="font-medium text-slate-400">vs</span> {item.away_team}</h4>
      <dl className="mt-3 grid grid-cols-3 gap-1.5 text-xs">
        <div className="rounded-lg bg-slate-50 p-2"><dt className="text-slate-500">{c.leading}</dt><dd className="mt-1 font-black">{item.leading_selection}</dd></div>
        <div className="rounded-lg bg-slate-50 p-2"><dt className="text-slate-500">{c.signalRank}</dt><dd className="mt-1 font-black">{Math.round(item.signal_strength * 100)}/100</dd></div>
        <div className="rounded-lg bg-slate-50 p-2"><dt className="text-slate-500">{c.verifiedPrice}</dt><dd className="mt-1 font-black">{item.verified_price.toFixed(2)}</dd></div>
      </dl>
      <p className={`mt-3 rounded-lg px-3 py-2 text-xs leading-5 ${value ? 'bg-emerald-50 text-emerald-950' : 'bg-amber-50 text-amber-950'}`}>
        {value ? c.valueCaveat : c.strongCaveat}
      </p>
      <Link href={`/explore?fixture=${item.fixture_id}`} className="mt-3 inline-flex min-h-[40px] w-full items-center justify-center gap-2 rounded-xl border border-slate-300 px-3 text-sm font-bold text-slate-800 hover:bg-slate-50">
        {c.inspect}<ArrowRight className="h-4 w-4" />
      </Link>
    </article>
  )
}

function StrategyCard({ highlight, language }: { highlight: StrategyHighlight; language: Lang }) {
  const c = COPY[language]
  const strategy = STRATEGIES.find(item => item.strategyKey === highlight.strategy_key)
  if (!strategy) return null
  const fit = highlight.fit
  return (
    <article className="rounded-2xl border border-white bg-white p-4 text-slate-950 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-black uppercase tracking-wider text-violet-700">{c.experimental}</p>
          <p className="mt-1 text-sm font-black">{strategy.copy[language].shortName}</p>
        </div>
        <span className="shrink-0 text-[11px] text-slate-500">{kickoffLabel(fit.kickoff, language)}</span>
      </div>
      <p className="mt-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{fit.league}</p>
      <h4 className="mt-1 font-black leading-snug">{fit.home_team} <span className="font-medium text-slate-400">vs</span> {fit.away_team}</h4>
      <dl className="mt-3 grid grid-cols-2 gap-1.5 text-xs">
        <div className="col-span-2 rounded-lg bg-violet-50 p-2"><dt className="text-violet-700">{c.marketView}</dt><dd className="mt-1 font-black text-violet-950">{fit.selection}</dd></div>
        <div className="rounded-lg bg-slate-50 p-2"><dt className="text-slate-500">{c.verifiedPrice}</dt><dd className="mt-1 font-black">{fit.odds.toFixed(2)}</dd></div>
        <div className="rounded-lg bg-slate-50 p-2"><dt className="text-slate-500">{c.breakEven}</dt><dd className="mt-1 font-black">{fit.break_even_probability_percent}%</dd></div>
        <div className="col-span-2 rounded-lg bg-blue-50 p-2"><dt className="text-blue-700">{c.modelView}</dt><dd className="mt-1 font-black text-blue-950">{modelLabel(fit)}</dd></div>
      </dl>
      <p className="mt-3 rounded-lg bg-violet-50 px-3 py-2 text-xs leading-5 text-violet-950">{c.strategyCaveat}</p>
      <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
        <Link href={strategyFixtureHref(fit)} className="inline-flex min-h-[40px] items-center justify-center gap-2 rounded-xl bg-slate-950 px-3 text-xs font-bold text-white hover:bg-slate-800">{c.inspect}<ArrowRight className="h-4 w-4" /></Link>
        <Link href={`/strategies/${strategy.slug}`} className="inline-flex min-h-[40px] items-center justify-center rounded-xl border border-slate-300 px-3 text-xs font-bold text-slate-800 hover:bg-slate-50">{c.learn}</Link>
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
  const values = valueWatchlist.slice(0, 2)
  const valueIds = new Set(values.map(item => item.fixture_id))
  const allHighlights: StrategyHighlight[] = data?.data?.highlights ?? []
  const strategies = allHighlights
    .filter(item => !valueIds.has(item.fit.fixture_id))
    .slice(0, 2)
  const usedIds = new Set([
    ...values.map(item => item.fixture_id),
    ...strategies.map(item => item.fit.fixture_id),
  ])
  const signals = strongSignals
    .filter(item => !usedIds.has(item.fixture_id))
    .slice(0, 2)
  const waiting = status !== 'ready'
  const waitingMessage = status === 'delayed' ? c.unavailable : c.processing

  return (
    <section aria-labelledby="decision-board-heading" className="mt-16 sm:mt-20">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-blue-700">{c.eyebrow}</p>
          <h2 id="decision-board-heading" className="mt-2 text-2xl font-black text-slate-950 sm:text-3xl">{c.heading}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{c.supporting}</p>
          <p className="mt-2 text-sm font-bold text-slate-900">{c.boundary}</p>
        </div>
        <Link href="/explore" className="shrink-0 text-sm font-bold text-blue-700 underline-offset-4 hover:underline">{c.exploreAll} →</Link>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <Lane icon={BadgeDollarSign} title={c.valueTitle} body={c.valueBody} tone="emerald">
          {recommendationsLoading && <EmptyLane>{c.processing}</EmptyLane>}
          {!recommendationsLoading && recommendationsError && <EmptyLane>{c.unavailable}</EmptyLane>}
          {!recommendationsLoading && !recommendationsError && waiting && <EmptyLane>{waitingMessage}</EmptyLane>}
          {!recommendationsLoading && !recommendationsError && !waiting && values.length === 0 && <EmptyLane>{c.valueEmpty}</EmptyLane>}
          {!recommendationsLoading && !recommendationsError && !waiting && values.map(item => <SignalCard key={item.fixture_id} item={item} language={language} kind="value" />)}
        </Lane>

        <Lane icon={FlaskConical} title={c.strategyTitle} body={c.strategyBody} tone="violet">
          {strategiesLoading && <EmptyLane>{c.strategyLoading}</EmptyLane>}
          {!strategiesLoading && strategyError && <EmptyLane><span className="flex gap-2"><ShieldAlert className="mt-0.5 h-4 w-4 shrink-0" />{c.strategyUnavailable}</span></EmptyLane>}
          {!strategiesLoading && !strategyError && strategies.length === 0 && <EmptyLane>{c.strategyEmpty}</EmptyLane>}
          {!strategiesLoading && !strategyError && strategies.map(item => <StrategyCard key={`${item.strategy_key}:${item.fit.fixture_id}`} highlight={item} language={language} />)}
        </Lane>

        <Lane icon={SearchCheck} title={c.strongTitle} body={c.strongBody} tone="blue">
          {recommendationsLoading && <EmptyLane>{c.processing}</EmptyLane>}
          {!recommendationsLoading && recommendationsError && <EmptyLane>{c.unavailable}</EmptyLane>}
          {!recommendationsLoading && !recommendationsError && waiting && <EmptyLane>{waitingMessage}</EmptyLane>}
          {!recommendationsLoading && !recommendationsError && !waiting && signals.length === 0 && <EmptyLane>{c.strongEmpty}</EmptyLane>}
          {!recommendationsLoading && !recommendationsError && !waiting && signals.map(item => <SignalCard key={item.fixture_id} item={item} language={language} kind="strong" />)}
        </Lane>
      </div>
    </section>
  )
}
