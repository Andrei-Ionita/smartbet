'use client'

import Link from 'next/link'
import { useState } from 'react'
import { ArrowRight, BarChart3, BookOpen, FlaskConical, Goal, Scale, ShieldAlert, TimerReset } from 'lucide-react'
import { useLanguage } from '../contexts/LanguageContext'
import { STRATEGIES, type StrategyCategory } from '../lib/strategyLibrary'
import { useStrategyEvidence } from '../lib/useStrategyEvidence'
import StrategyEvidenceBadge from '../components/StrategyEvidenceBadge'

const ICONS = { handicaps: Scale, goals: Goal, results: BarChart3, specialists: TimerReset }

const COPY = {
  en: {
    eyebrow: 'Learn first. Test second. Claim last.',
    title: 'Football strategies, without the certainty theatre.',
    intro: 'Explore how popular football betting strategies work, what must be true for them to have value, and where they fail. BetGlitch tests the same ideas in the background—but an idea is never presented as proof.',
    educational: 'Education, not picks',
    educationalBody: 'These pages explain markets and hypotheses. They do not tell you what to bet or imply that a strategy is profitable.',
    evidence: 'Evidence stays attached',
    evidenceBody: 'Each card shows the live forward-testing status. Historical backtests can eliminate weak ideas, but only forward evidence can support one.',
    disciplined: 'One decision per fixture',
    disciplinedBody: 'The lab avoids manufacturing a sample from many correlated lines on the same match.',
    all: 'All strategies', handicaps: 'Handicaps', goals: 'Goals', results: 'Results', specialists: 'Specialist markets',
    explore: 'Explore strategy',
    levels: { beginner: 'Beginner', intermediate: 'Intermediate', advanced: 'Advanced' },
    pathwayTitle: 'Three surfaces. Three different promises.',
    libraryTitle: 'Strategies', libraryBody: 'Learn the mechanics, pricing logic and risks.',
    labTitle: 'Lab evidence', labBody: 'See whether the hypothesis has enough forward observations.',
    gemsTitle: 'Gems', gemsBody: 'Only qualified opportunities may become public recommendations.',
    warning: 'No strategy removes risk. Higher odds are not automatically better value, and a higher hit rate is not automatically more profitable.',
  },
  ro: {
    eyebrow: 'Întâi înveți. Apoi testezi. Abia la final concluzionezi.',
    title: 'Strategii de fotbal, fără spectacolul certitudinii.',
    intro: 'Înțelege cum funcționează strategiile populare, ce trebuie să fie adevărat pentru a avea valoare și unde pot eșua. BetGlitch testează aceleași idei în fundal, dar o ipoteză nu este prezentată niciodată drept dovadă.',
    educational: 'Educație, nu selecții',
    educationalBody: 'Aceste pagini explică piețe și ipoteze. Nu îți spun ce să pariezi și nu sugerează că o strategie este profitabilă.',
    evidence: 'Dovezile rămân atașate',
    evidenceBody: 'Fiecare card arată starea testării forward. Backtesturile pot elimina idei slabe, dar doar dovezile viitoare pot susține una.',
    disciplined: 'O decizie pe meci',
    disciplinedBody: 'Laboratorul nu construiește artificial un eșantion din linii corelate ale aceluiași meci.',
    all: 'Toate strategiile', handicaps: 'Handicapuri', goals: 'Goluri', results: 'Rezultate', specialists: 'Piețe specializate',
    explore: 'Descoperă strategia',
    levels: { beginner: 'Începător', intermediate: 'Intermediar', advanced: 'Avansat' },
    pathwayTitle: 'Trei zone. Trei promisiuni diferite.',
    libraryTitle: 'Strategii', libraryBody: 'Învață mecanica, logica prețului și riscurile.',
    labTitle: 'Dovezi din laborator', labBody: 'Vezi dacă ipoteza are suficiente observații forward.',
    gemsTitle: 'Gems', gemsBody: 'Doar oportunitățile calificate pot deveni recomandări publice.',
    warning: 'Nicio strategie nu elimină riscul. Cotele mai mari nu înseamnă automat valoare, iar o rată mai mare de reușită nu garantează profit.',
  },
}

export default function StrategiesContent() {
  const { language } = useLanguage()
  const c = COPY[language]
  const [category, setCategory] = useState<'all' | StrategyCategory>('all')
  const { evidence, available, loading } = useStrategyEvidence()
  const filtered = category === 'all' ? STRATEGIES : STRATEGIES.filter((item) => item.category === category)
  const filters: Array<'all' | StrategyCategory> = ['all', 'handicaps', 'goals', 'results', 'specialists']

  return (
    <div className="mx-auto max-w-7xl pb-10">
      <section className="relative overflow-hidden rounded-3xl border border-slate-800 bg-slate-950 px-6 py-12 text-white shadow-xl sm:px-10 lg:px-14 lg:py-16">
        <div className="absolute -right-24 -top-24 h-72 w-72 rounded-full bg-blue-600/20 blur-3xl" />
        <div className="absolute -bottom-32 left-1/3 h-72 w-72 rounded-full bg-emerald-500/10 blur-3xl" />
        <div className="relative max-w-3xl">
          <p className="text-sm font-bold uppercase tracking-[0.18em] text-blue-300">{c.eyebrow}</p>
          <h1 className="mt-4 text-4xl font-black tracking-tight sm:text-5xl">{c.title}</h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-300">{c.intro}</p>
        </div>
        <div className="relative mt-10 grid gap-4 md:grid-cols-3">
          {[
            [BookOpen, c.educational, c.educationalBody],
            [FlaskConical, c.evidence, c.evidenceBody],
            [ShieldAlert, c.disciplined, c.disciplinedBody],
          ].map(([Icon, title, body]) => {
            const CardIcon = Icon as typeof BookOpen
            return <div key={String(title)} className="rounded-2xl border border-white/10 bg-white/[0.06] p-5 backdrop-blur"><CardIcon className="h-5 w-5 text-blue-300" /><h2 className="mt-3 font-bold">{String(title)}</h2><p className="mt-2 text-sm leading-6 text-slate-300">{String(body)}</p></div>
          })}
        </div>
      </section>

      <section className="mt-10">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Strategy categories">
          {filters.map((item) => (
            <button key={item} onClick={() => setCategory(item)} aria-pressed={category === item} className={`min-h-[44px] rounded-full border px-4 py-2 text-sm font-bold transition ${category === item ? 'border-blue-700 bg-blue-700 text-white' : 'border-gray-200 bg-white text-gray-700 hover:border-blue-300 hover:text-blue-700'}`}>{c[item]}</button>
          ))}
        </div>

        <div className="mt-6 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((strategy) => {
            const Icon = ICONS[strategy.category]
            const copy = strategy.copy[language]
            return (
              <article key={strategy.slug} className="group flex min-h-[330px] flex-col rounded-2xl border border-gray-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-200 hover:shadow-lg">
                <div className="flex items-start justify-between gap-4">
                  <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-950 text-white"><Icon className="h-5 w-5" /></span>
                  <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-600">{c.levels[strategy.complexity]}</span>
                </div>
                <p className="mt-5 text-xs font-bold uppercase tracking-wider text-blue-700">{strategy.marketLabel}</p>
                <h2 className="mt-2 text-xl font-black text-gray-950">{copy.name}</h2>
                <p className="mt-3 flex-1 text-sm leading-6 text-gray-600">{copy.summary}</p>
                <div className="mt-5 border-t border-gray-100 pt-4"><StrategyEvidenceBadge evidence={evidence[strategy.strategyKey]} language={language} loading={loading} available={available} /></div>
                <Link href={`/strategies/${strategy.slug}`} className="mt-5 inline-flex min-h-[44px] items-center gap-2 font-bold text-blue-700 hover:text-blue-900">{c.explore}<ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" /></Link>
              </article>
            )
          })}
        </div>
      </section>

      <section className="mt-12 rounded-3xl border border-gray-200 bg-white p-6 sm:p-9">
        <h2 className="text-2xl font-black text-gray-950">{c.pathwayTitle}</h2>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {[[c.libraryTitle, c.libraryBody, '/strategies'], [c.labTitle, c.labBody, '/strategies'], [c.gemsTitle, c.gemsBody, '/']].map(([title, body, href], index) => (
            <Link key={title} href={href} className="rounded-2xl bg-gray-50 p-5 transition hover:bg-blue-50"><span className="text-xs font-black text-blue-700">0{index + 1}</span><h3 className="mt-2 font-black text-gray-950">{title}</h3><p className="mt-2 text-sm leading-6 text-gray-600">{body}</p></Link>
          ))}
        </div>
        <div className="mt-6 flex gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-950"><ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" /><p>{c.warning}</p></div>
      </section>
    </div>
  )
}
