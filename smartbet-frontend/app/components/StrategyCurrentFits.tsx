'use client'

import Link from 'next/link'
import useSWR from 'swr'
import { ArrowRight, CheckCircle2, FlaskConical, ShieldAlert } from 'lucide-react'

import type { Lang } from '../lib/terminology'
import type { StrategyDefinition } from '../lib/strategyLibrary'
import { PUBLIC_RESULTS_VISIBLE } from '../lib/publicResultsMode'

interface StrategySelection {
  selection_id: string
  receipt_url: string
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  predicted_outcome: string
  odds: number
  bookmaker_count: number
}

const COPY = {
  en: {
    eyebrow: 'Current strategy selections', title: 'Up to 5 current validation fixtures',
    intro: 'Each fixture passed this strategy version’s registered rules. Its selection and displayed price were recorded before kickoff.',
    boundary: 'Selections are recorded for engine validation, but public performance history is paused until the engine rules are locked. These are not guarantees or instructions to bet.',
    loading: 'Loading current validation selections…', unavailable: 'Current strategy selections are temporarily unavailable.',
    emptyTitle: 'No validation selection is active right now', emptyBody: 'No fixture passed every rule in the latest scan. The next qualifying selection will be recorded automatically.',
    selection: 'Selection', price: 'Recorded odds', recorded: 'Recorded before kickoff', checked: 'bookmakers checked',
    analyse: 'Analyse fixture', receipt: 'Inspect receipt', results: 'Open Strategy Results', experimental: 'Experimental strategy',
    experimentalBody: 'This hypothesis is being tested privately. No public performance conclusion is presented during engine validation.',
  },
  ro: {
    eyebrow: 'Selecțiile actuale ale strategiei', title: 'Până la 5 meciuri actuale pentru validare',
    intro: 'Fiecare meci a trecut regulile înregistrate ale acestei versiuni. Selecția și cota afișată au fost înregistrate înainte de start.',
    boundary: 'Selecțiile sunt înregistrate pentru validarea motorului, dar istoricul public este suspendat până când regulile sunt blocate. Acestea nu sunt garanții sau instrucțiuni de pariere.',
    loading: 'Încărcăm selecțiile actuale pentru validare…', unavailable: 'Selecțiile actuale ale strategiei sunt temporar indisponibile.',
    emptyTitle: 'Nu există acum o selecție activă pentru validare', emptyBody: 'Niciun meci nu a trecut toate regulile la ultima scanare. Următoarea selecție eligibilă va fi înregistrată automat.',
    selection: 'Selecție', price: 'Cotă înregistrată', recorded: 'Înregistrată înainte de start', checked: 'operatori verificați',
    analyse: 'Analizează meciul', receipt: 'Verifică recipisa', results: 'Deschide Rezultatele Strategiei', experimental: 'Strategie experimentală',
    experimentalBody: 'Această ipoteză este testată în mod privat. În timpul validării motorului nu prezentăm nicio concluzie publică de performanță.',
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

function fixtureHref(item: StrategySelection) {
  return `/prediction/${slug(item.league || 'league')}/${slug(`${item.home_team}-vs-${item.away_team}`)}-${item.kickoff.slice(0, 10)}-${item.fixture_id}`
}

export default function StrategyCurrentFits({ strategy, language }: { strategy: StrategyDefinition; language: Lang }) {
  const c = COPY[language]
  const { data, error, isLoading } = useSWR(
    `/api/results-selections?category=strategy&source_key=${encodeURIComponent(strategy.strategyKey)}&state=pending`,
    fetcher,
    { refreshInterval: 120_000, revalidateOnFocus: true, errorRetryCount: 2 },
  )
  const now = Date.now()
  const selections: StrategySelection[] = (Array.isArray(data?.selections) ? data.selections : [])
    .filter((item: StrategySelection) => Date.parse(item.kickoff) > now)
    .sort((a: StrategySelection, b: StrategySelection) => Date.parse(a.kickoff) - Date.parse(b.kickoff))
    .slice(0, 5)
  const locale = language === 'ro' ? 'ro-RO' : 'en-GB'

  return (
    <section className="mt-8 rounded-3xl border border-slate-200 bg-slate-100/70 p-5 sm:p-8" aria-labelledby="current-strategy-fits">
      <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-4">
          <FlaskConical className="mt-1 h-7 w-7 shrink-0 text-blue-700" />
          <div>
            <p className="text-xs font-black uppercase tracking-[0.16em] text-blue-700">{c.eyebrow}</p>
            <h2 id="current-strategy-fits" className="mt-1 text-2xl font-black text-slate-950">{c.title}</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">{c.intro}</p>
            <p className="mt-2 max-w-3xl text-sm font-semibold leading-6 text-slate-950">{c.boundary}</p>
          </div>
        </div>
        {PUBLIC_RESULTS_VISIBLE && <Link href="/track-record?category=strategy" className="inline-flex shrink-0 items-center gap-2 font-bold text-blue-700 hover:underline">
          {c.results}<ArrowRight className="h-4 w-4" />
        </Link>}
      </div>

      {isLoading ? (
        <div role="status" className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600">{c.loading}</div>
      ) : error ? (
        <div role="alert" className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-amber-950">{c.unavailable}</div>
      ) : selections.length === 0 ? (
        <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-white p-7 text-center">
          <h3 className="font-black text-slate-950">{c.emptyTitle}</h3>
          <p className="mx-auto mt-2 max-w-2xl text-sm leading-6 text-slate-600">{c.emptyBody}</p>
        </div>
      ) : (
        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          {selections.map((item) => (
            <article key={item.selection_id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
              <p className="text-[11px] font-black uppercase tracking-wide text-blue-700">{item.league}</p>
              <h3 className="mt-1 text-lg font-black text-slate-950">{item.home_team} <span className="font-medium text-slate-400">vs</span> {item.away_team}</h3>
              <p className="mt-1 text-sm text-slate-600">{new Intl.DateTimeFormat(locale, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(item.kickoff))}</p>
              <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-xl bg-blue-50 p-3"><dt className="text-blue-700">{c.selection}</dt><dd className="mt-1 font-black text-blue-950">{item.predicted_outcome}</dd></div>
                <div className="rounded-xl bg-emerald-50 p-3"><dt className="text-emerald-700">{c.price}</dt><dd className="mt-1 text-xl font-black text-emerald-950">{item.odds.toFixed(2)}</dd></div>
              </dl>
              <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-800"><CheckCircle2 className="h-4 w-4" />{c.recorded} · {item.bookmaker_count} {c.checked}</span>
                <span className="flex flex-wrap gap-3">{PUBLIC_RESULTS_VISIBLE && <Link href={item.receipt_url} className="font-bold text-blue-700 hover:underline">{c.receipt} →</Link>}<Link href={fixtureHref(item)} className="font-bold text-blue-700 hover:underline">{c.analyse} →</Link></span>
              </div>
            </article>
          ))}
        </div>
      )}

      <div className="mt-6 flex gap-3 rounded-2xl border border-violet-200 bg-violet-50 p-4">
        <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-violet-700" />
        <div><p className="text-sm font-black text-violet-950">{c.experimental}</p><p className="mt-1 text-sm leading-6 text-violet-900">{c.experimentalBody}</p></div>
      </div>
    </section>
  )
}
