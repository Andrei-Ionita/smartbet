'use client'

import Link from 'next/link'
import { ArrowLeft, CheckCircle2, Clock3, Hash, ShieldCheck } from 'lucide-react'

import ShareResearchButton from '../../../components/ShareResearchButton'
import TrackOnMount from '../../../components/TrackOnMount'
import { useLanguage } from '../../../contexts/LanguageContext'
import { STRATEGIES } from '../../../lib/strategyLibrary'

export interface PublicSelectionReceipt {
  selection_id: string
  receipt_url: string
  category: 'homepage' | 'strategy'
  source_key: string
  source_version: string
  reason_code: string
  explanation: { title: string; why_selected: string; evidence: string; risk: string }
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  market_type: string
  predicted_outcome: string
  line: number | null
  odds: number
  bookmaker: string | null
  bookmaker_count: number
  odds_captured_at: string
  published_at: string
  selection_hash: string
  integrity_ok: boolean
  status: 'PENDING' | 'WON' | 'HALF_WON' | 'PUSH' | 'HALF_LOST' | 'LOST' | 'VOID' | 'CANCELLED'
  unit_profit: number | null
  actual_score_home: number | null
  actual_score_away: number | null
  settled_at: string | null
  closing_price: {
    odds: number
    bookmaker: string | null
    bookmaker_count: number
    odds_captured_at: string
    closing_line_value_percent: number
    evidence_hash: string
  } | null
}

function slug(value: string) {
  return value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'fixture'
}

export default function SelectionReceiptContent({ selection }: { selection: PublicSelectionReceipt }) {
  const { language } = useLanguage()
  const ro = language === 'ro'
  const pending = selection.status === 'PENDING'
  const fixtureUrl = `/prediction/${slug(selection.league || 'league')}/${slug(`${selection.home_team}-vs-${selection.away_team}`)}-${selection.kickoff.slice(0, 10)}-${selection.fixture_id}`
  const date = (value: string) => new Date(value).toLocaleString(ro ? 'ro-RO' : 'en-GB', {
    day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
  const status = ro ? {
    PENDING: 'În așteptare', WON: 'Câștigat', HALF_WON: 'Jumătate câștig',
    PUSH: 'Miză returnată', HALF_LOST: 'Jumătate pierdere', LOST: 'Pierdut',
    VOID: 'Void', CANCELLED: 'Anulat',
  }[selection.status] : {
    PENDING: 'Pending', WON: 'Won', HALF_WON: 'Half won', PUSH: 'Push',
    HALF_LOST: 'Half lost', LOST: 'Lost', VOID: 'Void', CANCELLED: 'Cancelled',
  }[selection.status]
  const strategy = STRATEGIES.find(item => item.strategyKey === selection.source_key)
  const strategyUrl = selection.category === 'strategy' && strategy
    ? `/strategies/${strategy.slug}` : null
  const explanation = !ro ? selection.explanation : selection.reason_code === 'strategy_match' ? {
    title: 'Potrivire de strategie',
    why_selected: `Meciul a trecut regulile blocate ale strategiei ${strategy?.copy.ro.name ?? selection.source_key}, versiunea ${selection.source_version || 'înregistrată'}.`,
    evidence: `${selection.predicted_outcome} la cota ${selection.odds.toFixed(2)}, verificată la ${selection.bookmaker_count} operatori.`,
    risk: 'Strategia este experimentală și eșantionul este încă în formare. Potrivirea regulilor nu este o garanție sau o instrucțiune de pariere.',
  } : selection.reason_code === 'potential_value' ? {
    title: 'Valoare potențială',
    why_selected: 'Modelul de preț și cota înregistrată au susținut același rezultat, cu o diferență suficientă pentru investigație.',
    evidence: `${selection.bookmaker_count} cote verificate; selecția și prețul au fost blocate înainte de start.`,
    risk: 'O diferență între model și piață nu dovedește că modelul are dreptate. Cotele și informațiile despre echipe se pot schimba.',
  } : {
    title: 'Semnal puternic al modelului',
    why_selected: 'Modelul a separat clar acest rezultat de alternative, iar piața a oferit un preț de referință utilizabil.',
    evidence: `${selection.bookmaker_count} cote verificate și blocate înainte de start.`,
    risk: 'Puterea semnalului nu este o probabilitate calibrată și nu dovedește singură că prețul oferă valoare.',
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-10">
      <TrackOnMount event="published_proof_opened" surface="selection_receipt" />
      <article className="mx-auto max-w-4xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
        <header className="border-b border-slate-200 bg-slate-950 px-5 py-7 text-white sm:px-8">
          <Link href="/track-record" className="inline-flex items-center gap-2 text-sm font-bold text-blue-200 hover:text-white">
            <ArrowLeft className="h-4 w-4" /> {ro ? 'Toate rezultatele' : 'All results'}
          </Link>
          <div className="mt-6 flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.18em] text-blue-300">
                {ro ? 'RECIPISĂ PUBLICĂ IMUABILĂ' : 'IMMUTABLE PUBLIC RECEIPT'}
              </p>
              <h1 className="mt-3 text-3xl font-black tracking-tight sm:text-4xl">
                {selection.home_team} <span className="text-slate-400">vs</span> {selection.away_team}
              </h1>
              <p className="mt-2 text-slate-300">{selection.league} · {date(selection.kickoff)}</p>
            </div>
            <ShareResearchButton
              href={selection.receipt_url}
              title={`${selection.home_team} vs ${selection.away_team}`}
              language={ro ? 'ro' : 'en'}
              surface="selection_receipt"
              className="border-slate-600 bg-slate-900 text-white hover:bg-slate-800"
            />
          </div>
        </header>

        <div className="p-5 sm:p-8">
          <div className={`rounded-2xl border p-5 ${pending ? 'border-amber-200 bg-amber-50 text-amber-950' : 'border-emerald-200 bg-emerald-50 text-emerald-950'}`}>
            <div className="flex items-start gap-3">
              {pending ? <Clock3 className="mt-0.5 h-5 w-5" /> : <CheckCircle2 className="mt-0.5 h-5 w-5" />}
              <div>
                <p className="font-black">{status}</p>
                <p className="mt-1 text-sm leading-6">
                  {pending
                    ? (ro ? 'Selecția a fost publicată înainte de start. Este în așteptarea unui rezultat confirmat și nu intră încă în performanță.' : 'This selection was published before kickoff. It is awaiting a confirmed result and does not yet count as performance.')
                    : (ro ? 'Rezultatul a fost evaluat din scorul confirmat, folosind selecția și cota blocate mai jos.' : 'The result was graded from the confirmed score using the frozen selection and price below.')}
                </p>
              </div>
            </div>
          </div>

          <dl className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {[
              [ro ? 'Selecție' : 'Selection', selection.predicted_outcome],
              [ro ? 'Piață' : 'Market', selection.market_type],
              [ro ? 'Cotă înregistrată' : 'Recorded odds', selection.odds.toFixed(2)],
              [ro ? 'Case verificate' : 'Books checked', String(selection.bookmaker_count)],
            ].map(([label, value]) => (
              <div key={label} className="rounded-xl bg-slate-50 p-4">
                <dt className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</dt>
                <dd className="mt-2 font-black text-slate-950">{value}</dd>
              </div>
            ))}
          </dl>

          <section className="mt-6 grid gap-3 lg:grid-cols-3">
            <div className="rounded-2xl border border-blue-200 bg-blue-50 p-5"><p className="text-xs font-black uppercase tracking-wide text-blue-700">{ro ? 'De ce a fost selectat' : 'Why it was selected'}</p><h2 className="mt-2 font-black text-blue-950">{explanation.title}</h2><p className="mt-2 text-sm leading-6 text-blue-900">{explanation.why_selected}</p></div>
            <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5"><p className="text-xs font-black uppercase tracking-wide text-emerald-700">{ro ? 'Dovezi înregistrate' : 'Evidence recorded'}</p><p className="mt-2 text-sm leading-6 text-emerald-950">{explanation.evidence}</p></div>
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-5"><p className="text-xs font-black uppercase tracking-wide text-amber-800">{ro ? 'Ce poate fi greșit' : 'What could make it wrong'}</p><p className="mt-2 text-sm leading-6 text-amber-950">{explanation.risk}</p></div>
          </section>

          {!pending && selection.actual_score_home !== null && selection.actual_score_away !== null && (
            <section className="mt-6 rounded-2xl border border-slate-200 p-5">
              <h2 className="font-black text-slate-950">{ro ? 'Rezultat confirmat' : 'Confirmed result'}</h2>
              <p className="mt-2 text-3xl font-black">{selection.actual_score_home}–{selection.actual_score_away}</p>
              {selection.unit_profit !== null && <p className="mt-2 text-sm text-slate-600">{ro ? 'Rezultat la o unitate' : 'One-unit return'}: {selection.unit_profit > 0 ? '+' : ''}{selection.unit_profit.toFixed(2)}u</p>}
            </section>
          )}

          {selection.closing_price && (
            <section className="mt-6 rounded-2xl border border-violet-200 bg-violet-50 p-5">
              <h2 className="font-black text-violet-950">
                {ro ? 'Comparație cu prețul de închidere' : 'Closing-price comparison'}
              </h2>
              <p className="mt-2 text-sm leading-6 text-violet-900">
                {ro ? 'Cota publicată' : 'Published odds'} {selection.odds.toFixed(2)} ·{' '}
                {ro ? 'cota de închidere' : 'closing odds'} {selection.closing_price.odds.toFixed(2)} ·{' '}
                CLV {selection.closing_price.closing_line_value_percent > 0 ? '+' : ''}
                {selection.closing_price.closing_line_value_percent.toFixed(2)}%
              </p>
              <p className="mt-1 text-xs text-violet-700">
                {ro ? 'Cea mai apropiată cotă verificată înainte de start, capturată la' : 'Closest verified pre-kickoff quote, captured'}{' '}
                {date(selection.closing_price.odds_captured_at)}.
              </p>
            </section>
          )}

          <section className="mt-6 rounded-2xl border border-blue-200 bg-blue-50 p-5">
            <div className="flex items-start gap-3">
              <ShieldCheck className="mt-0.5 h-5 w-5 text-blue-700" />
              <div>
                <h2 className="font-black text-blue-950">{ro ? 'Ce dovedește această recipisă' : 'What this receipt proves'}</h2>
                <p className="mt-2 text-sm leading-6 text-blue-900">
                  {ro ? 'Meciul, piața, selecția, cota și ora publicării au fost înghețate înainte de start. Rezultatul este adăugat separat și selecția originală nu poate fi rescrisă.' : 'The fixture, market, selection, odds and publication time were frozen before kickoff. Settlement is appended separately and the original selection cannot be rewritten.'}
                </p>
              </div>
            </div>
          </section>

          <dl className="mt-6 space-y-3 text-sm text-slate-600">
            <div><dt className="inline font-bold text-slate-900">{ro ? 'Publicată' : 'Published'}: </dt><dd className="inline">{date(selection.published_at)}</dd></div>
            <div><dt className="inline font-bold text-slate-900">{ro ? 'Cotă capturată' : 'Price captured'}: </dt><dd className="inline">{date(selection.odds_captured_at)}{selection.bookmaker ? ` · ${selection.bookmaker}` : ''}</dd></div>
            <div className="flex items-start gap-2"><Hash className="mt-0.5 h-4 w-4 shrink-0" /><div><dt className="font-bold text-slate-900">SHA-256</dt><dd className="mt-1 break-all font-mono text-xs">{selection.selection_hash}</dd></div></div>
          </dl>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link href={fixtureUrl} className="inline-flex min-h-11 items-center rounded-xl bg-blue-600 px-5 text-sm font-black text-white hover:bg-blue-700">
              {ro ? 'Analizează meciul' : 'Analyse fixture'} →
            </Link>
            <Link href="/methodology" className="inline-flex min-h-11 items-center rounded-xl border border-slate-300 px-5 text-sm font-black text-slate-800 hover:bg-slate-50">
              {ro ? 'Metodologie' : 'Methodology'}
            </Link>
            {strategyUrl && <Link href={strategyUrl} className="inline-flex min-h-11 items-center rounded-xl border border-violet-300 px-5 text-sm font-black text-violet-800 hover:bg-violet-50">{ro ? 'Explicația strategiei' : 'Strategy explanation'}</Link>}
          </div>
        </div>
      </article>
    </main>
  )
}
