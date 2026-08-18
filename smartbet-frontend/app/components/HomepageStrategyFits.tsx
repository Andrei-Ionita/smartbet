'use client'

import Link from 'next/link'
import useSWR from 'swr'
import { ArrowRight, FlaskConical, ShieldAlert } from 'lucide-react'

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
    eyebrow: 'Strategies in action',
    heading: 'Three live ideas from the research lab',
    supporting: 'Each card is the strongest current fit from a different registered strategy. Use it to discover a market and investigate the fixture—not as an instruction to bet.',
    boundary: 'Experimental research fits · not published picks · not counted in Results',
    strategy: 'Strategy', experimental: 'Experimental', selection: 'Market view', price: 'Verified price', breakEven: 'Break-even', model: 'Model view',
    modelRange: 'Model range', inspect: 'Inspect fixture', learn: 'Learn the strategy',
    loading: 'Checking the latest strategy scans…',
    emptyHeading: 'No strategy fit is current right now',
    emptyBody: 'The lab will leave this area empty instead of weakening its registered checks. The strategy library remains available for learning.',
    unavailableHeading: 'The live strategy view is temporarily unavailable',
    unavailableBody: 'No stale fit will be presented as current. You can still explore how each strategy works and where it can fail.',
    allStrategies: 'Explore all strategies',
  },
  ro: {
    eyebrow: 'Strategii în acțiune',
    heading: 'Trei idei live din laboratorul de cercetare',
    supporting: 'Fiecare card este cea mai solidă potrivire actuală dintr-o strategie înregistrată diferită. Folosește-l ca să descoperi o piață și să analizezi meciul, nu ca instrucțiune de pariere.',
    boundary: 'Potriviri experimentale · nu sunt selecții publicate · nu intră în Rezultate',
    strategy: 'Strategie', experimental: 'Experimental', selection: 'Viziunea pieței', price: 'Cotă verificată', breakEven: 'Prag', model: 'Viziunea modelului',
    modelRange: 'Intervalul modelului', inspect: 'Analizează meciul', learn: 'Înțelege strategia',
    loading: 'Verificăm cele mai recente scanări ale strategiilor…',
    emptyHeading: 'Nicio strategie nu are acum o potrivire actuală',
    emptyBody: 'Laboratorul lasă această zonă goală în loc să slăbească verificările înregistrate. Biblioteca de strategii rămâne disponibilă pentru învățare.',
    unavailableHeading: 'Vizualizarea live a strategiilor este temporar indisponibilă',
    unavailableBody: 'Nu afișăm o potrivire veche drept actuală. Poți explora în continuare cum funcționează fiecare strategie și unde poate eșua.',
    allStrategies: 'Explorează toate strategiile',
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

function fixtureHref(fit: StrategyFit) {
  const date = fit.kickoff.slice(0, 10)
  return `/prediction/${slug(fit.league || 'league')}/${slug(`${fit.home_team}-vs-${fit.away_team}`)}-${date}-${fit.fixture_id}`
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

export default function HomepageStrategyFits({ language }: { language: Lang }) {
  const c = COPY[language]
  const { data, error, isLoading } = useSWR('/api/homepage-strategy-fits', fetcher, {
    refreshInterval: 120000,
    revalidateOnFocus: true,
    errorRetryCount: 2,
  })
  const highlights: StrategyHighlight[] = data?.data?.highlights ?? []

  return (
    <section aria-labelledby="strategy-fits-heading" className="mt-16 sm:mt-20">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-violet-700">{c.eyebrow}</p>
          <h2 id="strategy-fits-heading" className="mt-2 text-2xl font-black text-slate-950 sm:text-3xl">{c.heading}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{c.supporting}</p>
          <p className="mt-2 text-sm font-bold text-slate-900">{c.boundary}</p>
        </div>
        <Link href="/strategies" className="shrink-0 text-sm font-bold text-violet-700 underline-offset-4 hover:underline">{c.allStrategies} →</Link>
      </div>

      {isLoading && <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600" role="status">{c.loading}</div>}

      {!isLoading && error && (
        <div className="mt-6 flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-5">
          <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" />
          <div><h3 className="font-black text-amber-950">{c.unavailableHeading}</h3><p className="mt-1 text-sm leading-6 text-amber-900">{c.unavailableBody}</p></div>
        </div>
      )}

      {!isLoading && !error && highlights.length === 0 && (
        <div className="mt-6 rounded-2xl border border-dashed border-violet-200 bg-white p-7 text-center">
          <FlaskConical className="mx-auto h-6 w-6 text-violet-600" />
          <h3 className="mt-3 font-black text-slate-950">{c.emptyHeading}</h3>
          <p className="mx-auto mt-2 max-w-2xl text-sm leading-6 text-slate-600">{c.emptyBody}</p>
        </div>
      )}

      {!isLoading && !error && highlights.length > 0 && (
        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          {highlights.map(({ strategy_key, fit }) => {
            const strategy = STRATEGIES.find((item) => item.strategyKey === strategy_key)
            if (!strategy) return null
            const bounded = fit.probability.kind === 'bounded_score_distribution'
            return (
              <article key={`${strategy_key}:${fit.fixture_id}`} className="flex h-full flex-col rounded-2xl border border-violet-200 bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-black uppercase tracking-wider text-violet-700">{c.strategy}</p>
                    <h3 className="mt-1 font-black text-slate-950">{strategy.copy[language].shortName}</h3>
                  </div>
                  <span className="rounded-full bg-violet-50 px-2.5 py-1 text-[11px] font-bold text-violet-800">{c.experimental}</span>
                </div>
                <p className="mt-4 text-xs font-semibold text-slate-500">{fit.league} · {new Date(fit.kickoff).toLocaleString(language === 'ro' ? 'ro-RO' : 'en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</p>
                <p className="mt-1 text-lg font-black leading-snug text-slate-950">{fit.home_team} <span className="font-medium text-slate-400">vs</span> {fit.away_team}</p>

                <dl className="mt-4 grid grid-cols-2 gap-2 text-sm">
                  <div className="col-span-2 rounded-xl bg-violet-50 p-3"><dt className="text-xs text-violet-700">{c.selection}</dt><dd className="mt-1 font-black text-violet-950">{fit.selection}</dd></div>
                  <div className="rounded-xl bg-emerald-50 p-3"><dt className="text-xs text-emerald-700">{c.price}</dt><dd className="mt-1 text-lg font-black text-emerald-950">{fit.odds.toFixed(2)}</dd></div>
                  <div className="rounded-xl bg-slate-50 p-3"><dt className="text-xs text-slate-500">{c.breakEven}</dt><dd className="mt-1 text-lg font-black text-slate-950">{fit.break_even_probability_percent}%</dd></div>
                  <div className="col-span-2 rounded-xl bg-blue-50 p-3"><dt className="text-xs text-blue-700">{bounded ? c.modelRange : c.model}</dt><dd className="mt-1 font-black text-blue-950">{modelLabel(fit)}</dd></div>
                </dl>

                <div className="mt-auto grid gap-2 pt-5 sm:grid-cols-2 lg:grid-cols-1 xl:grid-cols-2">
                  <Link href={fixtureHref(fit)} className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-slate-950 px-3 text-sm font-bold text-white hover:bg-slate-800">{c.inspect}<ArrowRight className="h-4 w-4" /></Link>
                  <Link href={`/strategies/${strategy.slug}`} className="inline-flex min-h-[44px] items-center justify-center rounded-xl border border-slate-300 px-3 text-sm font-bold text-slate-800 hover:bg-slate-50">{c.learn}</Link>
                </div>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
