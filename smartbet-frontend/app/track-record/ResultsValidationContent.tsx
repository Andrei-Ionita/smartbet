'use client'

import Link from 'next/link'
import { ArrowRight, FlaskConical, LockKeyhole, Search, ShieldCheck } from 'lucide-react'

import { useLanguage } from '../contexts/LanguageContext'

const COPY = {
  en: {
    eyebrow: 'Engine validation in progress',
    title: 'The public results record has not started yet.',
    body: 'We are validating the selection engine before asking anyone to judge its performance. During this phase, BetGlitch will not display a historical fixture record, win rate or ROI.',
    retainedTitle: 'Evidence is still being recorded',
    retainedBody: 'Selections, prices and outcomes continue to be stored internally so defects can be found without choosing only favourable examples. Existing immutable receipts remain valid, but the earlier experimental record is not presented as evidence for the current engine.',
    startTitle: 'The public record will begin with locked rules',
    startBody: 'Before it opens, we will publish the exact engine version, qualification rules and start time. Every eligible selection from that point will remain in the record, including losses.',
    explore: 'Explore current fixtures',
    methodology: 'Read the methodology',
  },
  ro: {
    eyebrow: 'Motorul este în curs de validare',
    title: 'Istoricul public de rezultate nu a început încă.',
    body: 'Validăm motorul de selecție înainte de a cere cuiva să îi evalueze performanța. În această etapă, BetGlitch nu va afișa un istoric al meciurilor, rata de reușită sau ROI.',
    retainedTitle: 'Dovezile sunt în continuare înregistrate',
    retainedBody: 'Selecțiile, cotele și rezultatele continuă să fie stocate intern pentru a putea identifica problemele fără a alege doar exemple favorabile. Recipisele imuabile deja emise rămân valide, dar istoricul experimental anterior nu este prezentat ca dovadă pentru motorul actual.',
    startTitle: 'Istoricul public va începe cu reguli blocate',
    startBody: 'Înainte de lansare, vom publica versiunea exactă a motorului, regulile de calificare și momentul de început. Fiecare selecție eligibilă ulterioară va rămâne în istoric, inclusiv pierderile.',
    explore: 'Explorează meciurile actuale',
    methodology: 'Citește metodologia',
  },
} as const

export default function ResultsValidationContent() {
  const { language } = useLanguage()
  const c = COPY[language === 'ro' ? 'ro' : 'en']

  return (
    <main className="min-h-[70vh] bg-slate-50">
      <div className="mx-auto max-w-5xl px-4 py-14 sm:px-6 sm:py-20">
        <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
          <div className="border-b border-blue-100 bg-blue-50 px-6 py-10 sm:px-10">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-700 text-white">
              <FlaskConical className="h-6 w-6" />
            </div>
            <p className="mt-6 text-xs font-black uppercase tracking-[0.2em] text-blue-700">{c.eyebrow}</p>
            <h1 className="mt-3 max-w-3xl text-4xl font-black tracking-tight text-slate-950 sm:text-5xl">{c.title}</h1>
            <p className="mt-5 max-w-3xl text-lg leading-8 text-slate-700">{c.body}</p>
          </div>

          <div className="grid gap-5 p-6 sm:p-10 lg:grid-cols-2">
            <article className="rounded-2xl border border-slate-200 bg-slate-50 p-6">
              <ShieldCheck className="h-6 w-6 text-emerald-700" />
              <h2 className="mt-4 text-xl font-black text-slate-950">{c.retainedTitle}</h2>
              <p className="mt-2 text-sm leading-7 text-slate-700">{c.retainedBody}</p>
            </article>
            <article className="rounded-2xl border border-slate-200 bg-slate-50 p-6">
              <LockKeyhole className="h-6 w-6 text-violet-700" />
              <h2 className="mt-4 text-xl font-black text-slate-950">{c.startTitle}</h2>
              <p className="mt-2 text-sm leading-7 text-slate-700">{c.startBody}</p>
            </article>
          </div>

          <div className="flex flex-col gap-3 border-t border-slate-200 px-6 py-6 sm:flex-row sm:px-10">
            <Link href="/explore" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl bg-slate-950 px-5 py-3 font-bold text-white hover:bg-slate-800">
              <Search className="h-4 w-4" />{c.explore}<ArrowRight className="h-4 w-4" />
            </Link>
            <Link href="/methodology" className="inline-flex min-h-12 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-5 py-3 font-bold text-slate-800 hover:bg-slate-50">
              {c.methodology}<ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </section>
      </div>
    </main>
  )
}
