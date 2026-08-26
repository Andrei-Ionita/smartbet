'use client'

import Link from 'next/link'
import { ArrowLeft, ArrowRight, Calculator, CheckCircle2, FlaskConical, Info, ShieldAlert, Target } from 'lucide-react'
import StrategyEvidenceBadge from '../../components/StrategyEvidenceBadge'
import StrategyCurrentFits from '../../components/StrategyCurrentFits'
import { useLanguage } from '../../contexts/LanguageContext'
import { STRATEGIES, type StrategyDefinition } from '../../lib/strategyLibrary'
import { useStrategyEvidence } from '../../lib/useStrategyEvidence'

const COPY = {
  en: {
    back: 'All strategies', hypothesis: 'Strategy hypothesis', mechanics: 'How it works', useful: 'When the idea may be useful', risks: 'Where it can fail', settlement: 'Settlement', example: 'Worked example', breakEven: 'Price check', evidence: 'Current lab evidence', evidenceBody: 'This counter contains forward-settled decisions from this exact strategy version. Every current selection displayed above is frozen before kickoff and remains in Strategy Results.', boundaryTitle: 'What this page is—and is not', boundaryBody: 'This page explains a market hypothesis and may show current tracked selections. A selection is not a promise of profit, personalized advice or proof that the strategy works.', inspect: 'Inspect live fixtures', methodology: 'Read the testing methodology', results: 'Open Strategy Results', related: 'Continue learning',
  },
  ro: {
    back: 'Toate strategiile', hypothesis: 'Ipoteza strategiei', mechanics: 'Cum funcționează', useful: 'Când poate fi utilă ideea', risks: 'Unde poate eșua', settlement: 'Decontare', example: 'Exemplu explicat', breakEven: 'Verificarea prețului', evidence: 'Dovezi curente din laborator', evidenceBody: 'Contorul include decizii forward încheiate din această versiune exactă. Fiecare selecție actuală afișată mai sus este blocată înainte de start și rămâne în Rezultatele Strategiilor.', boundaryTitle: 'Ce este și ce nu este această pagină', boundaryBody: 'Pagina explică o ipoteză de piață și poate afișa selecții actuale urmărite. O selecție nu este o promisiune de profit, un sfat personalizat sau dovada că strategia funcționează.', inspect: 'Analizează meciurile curente', methodology: 'Citește metodologia de testare', results: 'Deschide Rezultatele Strategiilor', related: 'Continuă să înveți',
  },
}

export default function StrategyDetailContent({ strategy }: { strategy: StrategyDefinition }) {
  const { language } = useLanguage()
  const c = COPY[language]
  const s = strategy.copy[language]
  const { evidence, available, loading } = useStrategyEvidence()
  const related = STRATEGIES.filter((item) => item.category === strategy.category && item.slug !== strategy.slug).slice(0, 3)

  return (
    <article className="mx-auto max-w-5xl pb-12">
      <Link href="/strategies" className="inline-flex min-h-[44px] items-center gap-2 text-sm font-bold text-gray-600 hover:text-blue-700"><ArrowLeft className="h-4 w-4" />{c.back}</Link>

      <header className="mt-4 overflow-hidden rounded-3xl border border-slate-800 bg-slate-950 p-7 text-white shadow-xl sm:p-10">
        <div className="flex flex-wrap items-center gap-3"><span className="rounded-full bg-blue-500/15 px-3 py-1 text-xs font-bold uppercase tracking-wider text-blue-200">{strategy.marketLabel}</span><span className="rounded-full border border-white/15 px-3 py-1 text-xs text-slate-300">{strategy.complexity}</span></div>
        <h1 className="mt-5 text-4xl font-black tracking-tight sm:text-5xl">{s.name}</h1>
        <p className="mt-5 max-w-3xl text-lg leading-8 text-slate-300">{s.summary}</p>
        <div className="mt-7 max-w-xl rounded-2xl border border-white/10 bg-white/[0.06] p-5"><StrategyEvidenceBadge evidence={evidence[strategy.strategyKey]} language={language} loading={loading} available={available} showProgress /></div>
      </header>

      <section className="mt-8 rounded-2xl border border-blue-200 bg-blue-50 p-6 sm:p-8">
        <div className="flex items-start gap-4"><Target className="mt-1 h-6 w-6 shrink-0 text-blue-700" /><div><h2 className="text-sm font-black uppercase tracking-wider text-blue-900">{c.hypothesis}</h2><p className="mt-3 text-base leading-7 text-blue-950">{s.thesis}</p></div></div>
      </section>

      <StrategyCurrentFits strategy={strategy} language={language} />

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        <section className="rounded-2xl border border-gray-200 bg-white p-6"><h2 className="flex items-center gap-2 text-lg font-black text-gray-950"><Info className="h-5 w-5 text-blue-700" />{c.mechanics}</h2><ul className="mt-4 space-y-3">{s.mechanics.map((item) => <li key={item} className="flex gap-3 text-sm leading-6 text-gray-700"><CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-blue-600" />{item}</li>)}</ul></section>
        <section className="rounded-2xl border border-gray-200 bg-white p-6"><h2 className="flex items-center gap-2 text-lg font-black text-gray-950"><Target className="h-5 w-5 text-emerald-700" />{c.useful}</h2><ul className="mt-4 space-y-3">{s.usefulWhen.map((item) => <li key={item} className="flex gap-3 text-sm leading-6 text-gray-700"><CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-emerald-600" />{item}</li>)}</ul></section>
      </div>

      <section className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 p-6"><h2 className="flex items-center gap-2 text-lg font-black text-rose-950"><ShieldAlert className="h-5 w-5" />{c.risks}</h2><ul className="mt-4 grid gap-3 md:grid-cols-3">{s.risks.map((item) => <li key={item} className="rounded-xl bg-white/70 p-4 text-sm leading-6 text-rose-950">{item}</li>)}</ul></section>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <section className="rounded-2xl border border-gray-200 bg-white p-6"><h2 className="text-sm font-black uppercase tracking-wider text-gray-900">{c.settlement}</h2><p className="mt-3 text-sm leading-6 text-gray-700">{s.settlement}</p></section>
        <section className="rounded-2xl border border-gray-200 bg-white p-6"><h2 className="text-sm font-black uppercase tracking-wider text-gray-900">{c.example}</h2><p className="mt-3 text-sm leading-6 text-gray-700">{s.example}</p></section>
        <section className="rounded-2xl border border-gray-200 bg-white p-6"><h2 className="flex items-center gap-2 text-sm font-black uppercase tracking-wider text-gray-900"><Calculator className="h-4 w-4 text-blue-700" />{c.breakEven}</h2><p className="mt-3 text-sm leading-6 text-gray-700">{s.breakEvenExample}</p></section>
      </div>

      <section className="mt-6 rounded-2xl border border-violet-200 bg-violet-50 p-6 sm:p-8"><div className="flex items-start gap-4"><FlaskConical className="mt-1 h-6 w-6 shrink-0 text-violet-700" /><div><h2 className="text-lg font-black text-violet-950">{c.evidence}</h2><p className="mt-2 text-sm leading-6 text-violet-900">{c.evidenceBody}</p><div className="mt-4 flex flex-wrap gap-4"><Link href="/track-record?category=strategy" className="inline-flex min-h-[44px] items-center gap-2 font-bold text-violet-800 hover:text-violet-950">{c.results}<ArrowRight className="h-4 w-4" /></Link><Link href="/methodology" className="inline-flex min-h-[44px] items-center gap-2 font-bold text-violet-800 hover:text-violet-950">{c.methodology}<ArrowRight className="h-4 w-4" /></Link></div></div></div></section>

      <section className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-6"><h2 className="font-black text-amber-950">{c.boundaryTitle}</h2><p className="mt-2 text-sm leading-6 text-amber-900">{c.boundaryBody}</p></section>

      <div className="mt-8 flex flex-wrap gap-3"><Link href="/explore" className="inline-flex min-h-[48px] items-center gap-2 rounded-xl bg-blue-700 px-5 py-3 font-bold text-white hover:bg-blue-800">{c.inspect}<ArrowRight className="h-4 w-4" /></Link><Link href="/strategies" className="inline-flex min-h-[48px] items-center rounded-xl border border-gray-300 bg-white px-5 py-3 font-bold text-gray-800 hover:bg-gray-50">{c.back}</Link></div>

      {related.length > 0 && <section className="mt-12 border-t border-gray-200 pt-8"><h2 className="text-2xl font-black text-gray-950">{c.related}</h2><div className="mt-5 grid gap-4 md:grid-cols-3">{related.map((item) => <Link key={item.slug} href={`/strategies/${item.slug}`} className="group rounded-xl border border-gray-200 bg-white p-5 hover:border-blue-300"><p className="text-xs font-bold uppercase tracking-wider text-blue-700">{item.marketLabel}</p><h3 className="mt-2 font-black text-gray-950">{item.copy[language].shortName}</h3><span className="mt-4 inline-flex items-center gap-2 text-sm font-bold text-blue-700">{c.back === 'All strategies' ? 'Read' : 'Citește'}<ArrowRight className="h-4 w-4 transition group-hover:translate-x-1" /></span></Link>)}</div></section>}
    </article>
  )
}
