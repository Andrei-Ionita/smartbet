'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Database,
  Gauge,
  RefreshCw,
  ShieldCheck,
  XCircle,
} from 'lucide-react'

import { useLanguage } from '../contexts/LanguageContext'

type Lang = 'en' | 'ro'

type Coverage = {
  fixture_market_universe: number
  eligible_decisions: number
  evaluated_market_decisions: number
  evaluated_fixtures: number
  decision_states: Record<string, number>
  excluded_before_evaluation: Record<string, number>
}

type CalibrationReport = {
  methodology_version: string
  evaluation_horizon_hours: number
  generated_at: string
  coverage: Coverage
}

type Decision = {
  fixture_id: number
  fixture: string
  home_team: string
  away_team: string
  league: string
  kickoff: string
  market: string
  market_label: string
  observed_at: string
  hours_to_kickoff: number
  probabilities: Record<string, number>
  predicted_outcome: string
  actual_outcome: string | null
  correct: boolean | null
  state: string
  result: {
    home_score: number | null
    away_score: number | null
    confirmed: boolean
  } | null
}

type ArchiveResponse = {
  success: boolean
  methodology_version: string
  evaluation_horizon_hours: number
  pagination: {
    page: number
    page_size: number
    total: number
    pages: number
  }
  decisions: Decision[]
}

const COPY = {
  en: {
    loading: 'Loading the public evidence archive…',
    errorTitle: 'Research evidence is temporarily unavailable',
    errorBody: 'The archive could not be loaded. The previous evidence remains stored; please try again.',
    retry: 'Try again',
    boundaryTitle: 'Research evidence — not a betting performance record',
    boundaryBody: 'Every row is one fixed pre-match probability vector selected under the same rule. It measures what the signal got right and wrong; it is not a published pick and does not support a profit or ROI claim.',
    resultsLink: 'Open the verified Gem record',
    calibrationLink: 'Inspect probability calibration',
    eligible: 'Eligible pre-match decisions',
    evaluated: 'Evaluated decisions',
    awaiting: 'Awaiting a result',
    fixtures: 'Independent completed fixtures',
    coverageTitle: 'The record is growing from a fixed denominator',
    coverageBody: (evaluated: number, eligible: number, unscoreable: number) => `${evaluated} of ${eligible} eligible decisions currently have a confirmed, scoreable result. ${unscoreable} cannot currently be scored. Pending rows remain visible and will be evaluated automatically.`,
    archiveTitle: 'Every eligible pre-match decision',
    archiveBody: 'The nearest complete probability vector recorded at least one hour before kickoff is preserved. Repeated scans cannot add extra decisions for the same fixture and market.',
    allMarkets: 'All markets',
    allStates: 'Every state',
    market1x2: 'Match result',
    marketBtts: 'Both teams to score',
    marketTotals: 'Over / under 2.5',
    marketDc: 'Double chance',
    evaluatedState: 'Evaluated',
    pendingState: 'Pending result',
    confirmingState: 'Confirming result',
    unscoreableState: 'Not scoreable',
    refresh: 'Refresh',
    noRows: 'No decisions match these filters.',
    observed: 'recorded',
    beforeKickoff: 'before kickoff',
    leadingOutcome: 'Leading outcome',
    correct: 'Correct',
    incorrect: 'Incorrect',
    result: 'Final score',
    decisions: 'decisions',
    page: 'page',
    of: 'of',
    previous: 'Previous archive page',
    next: 'Next archive page',
    method: 'Evaluation rule',
    methodBody: 'One decision per fixture and market, chosen before the result is known. This archive evaluates signal quality only. Verified prices and returns belong exclusively to published Gems.',
    outcomes: {
      home: 'Home', draw: 'Draw', away: 'Away', yes: 'Yes', no: 'No',
      over: 'Over 2.5', under: 'Under 2.5', '1x': 'Home or draw',
      x2: 'Draw or away', '12': 'Home or away',
    } as Record<string, string>,
  },
  ro: {
    loading: 'Se încarcă arhiva publică de dovezi…',
    errorTitle: 'Dovezile de cercetare sunt temporar indisponibile',
    errorBody: 'Arhiva nu a putut fi încărcată. Dovezile existente rămân stocate; încearcă din nou.',
    retry: 'Încearcă din nou',
    boundaryTitle: 'Dovezi de cercetare — nu un istoric al performanței la pariuri',
    boundaryBody: 'Fiecare rând reprezintă un singur vector de probabilități fixat înaintea meciului, ales după aceeași regulă. Arată ce a estimat corect sau greșit semnalul; nu este o selecție publicată și nu susține afirmații despre profit sau ROI.',
    resultsLink: 'Deschide istoricul verificat al Gem-urilor',
    calibrationLink: 'Verifică calibrarea probabilităților',
    eligible: 'Decizii eligibile înainte de meci',
    evaluated: 'Decizii evaluate',
    awaiting: 'În așteptarea rezultatului',
    fixtures: 'Meciuri încheiate independente',
    coverageTitle: 'Istoricul crește pornind de la un numitor fix',
    coverageBody: (evaluated: number, eligible: number, unscoreable: number) => `${evaluated} dintre cele ${eligible} decizii eligibile au acum un rezultat confirmat și evaluabil. ${unscoreable} nu pot fi evaluate momentan. Rândurile în așteptare rămân vizibile și vor fi evaluate automat.`,
    archiveTitle: 'Toate deciziile eligibile de dinaintea meciului',
    archiveBody: 'Păstrăm cel mai apropiat vector complet de probabilități înregistrat cu cel puțin o oră înainte de start. Scanările repetate nu pot adăuga decizii suplimentare pentru același meci și aceeași piață.',
    allMarkets: 'Toate piețele',
    allStates: 'Toate stările',
    market1x2: 'Rezultatul meciului',
    marketBtts: 'Ambele echipe marchează',
    marketTotals: 'Peste / sub 2,5 goluri',
    marketDc: 'Șansă dublă',
    evaluatedState: 'Evaluată',
    pendingState: 'Rezultat în așteptare',
    confirmingState: 'Rezultat în confirmare',
    unscoreableState: 'Nu poate fi evaluată',
    refresh: 'Actualizează',
    noRows: 'Nicio decizie nu corespunde acestor filtre.',
    observed: 'înregistrată',
    beforeKickoff: 'înainte de start',
    leadingOutcome: 'Rezultat principal',
    correct: 'Corect',
    incorrect: 'Greșit',
    result: 'Scor final',
    decisions: 'decizii',
    page: 'pagina',
    of: 'din',
    previous: 'Pagina anterioară a arhivei',
    next: 'Pagina următoare a arhivei',
    method: 'Regula de evaluare',
    methodBody: 'O singură decizie pentru fiecare meci și piață, aleasă înainte ca rezultatul să fie cunoscut. Această arhivă evaluează doar calitatea semnalului. Cotele verificate și randamentul apar exclusiv la Gem-urile publicate.',
    outcomes: {
      home: 'Gazde', draw: 'Egal', away: 'Oaspeți', yes: 'Da', no: 'Nu',
      over: 'Peste 2,5', under: 'Sub 2,5', '1x': 'Gazde sau egal',
      x2: 'Egal sau oaspeți', '12': 'Gazde sau oaspeți',
    } as Record<string, string>,
  },
} as const

function percent(value: number) {
  return `${(value * 100).toFixed(1)}%`
}

function stateLabel(state: string, language: Lang) {
  const c = COPY[language]
  return ({
    evaluated: c.evaluatedState,
    pending_result: c.pendingState,
    awaiting_confirmation: c.confirmingState,
    unscoreable_result: c.unscoreableState,
  } as Record<string, string>)[state] || state
}

function marketLabel(market: string, language: Lang) {
  const c = COPY[language]
  return ({
    '1x2': c.market1x2,
    btts: c.marketBtts,
    'over_under_2.5': c.marketTotals,
    double_chance: c.marketDc,
  } as Record<string, string>)[market] || market
}

function statusClass(state: string) {
  if (state === 'evaluated') return 'bg-emerald-100 text-emerald-800'
  if (state === 'unscoreable_result') return 'bg-slate-200 text-slate-700'
  return 'bg-amber-100 text-amber-900'
}

export default function RecommendedPredictionsTable() {
  const { language } = useLanguage()
  const lang: Lang = language === 'ro' ? 'ro' : 'en'
  const c = COPY[lang]
  const [report, setReport] = useState<CalibrationReport | null>(null)
  const [archive, setArchive] = useState<ArchiveResponse | null>(null)
  const [market, setMarket] = useState('')
  const [state, setState] = useState('')
  const [page, setPage] = useState(1)
  const [reportError, setReportError] = useState(false)
  const [archiveError, setArchiveError] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    let active = true
    setReportError(false)
    fetch('/api/calibration', { cache: 'no-store' })
      .then(async response => {
        const body = await response.json()
        if (!response.ok || !body.success) throw new Error('unavailable')
        if (active) setReport(body.data)
      })
      .catch(() => { if (active) setReportError(true) })
    return () => { active = false }
  }, [refreshKey])

  useEffect(() => {
    let active = true
    setArchive(null)
    setArchiveError(false)
    const params = new URLSearchParams({ page: String(page), page_size: '25' })
    if (market) params.set('market', market)
    if (state) params.set('state', state)
    fetch(`/api/prediction-archive?${params}`, { cache: 'no-store' })
      .then(async response => {
        const body = await response.json()
        if (!response.ok || !body.success) throw new Error('unavailable')
        if (active) setArchive(body)
      })
      .catch(() => { if (active) setArchiveError(true) })
    return () => { active = false }
  }, [market, state, page, refreshKey])

  const marketOptions = useMemo(() => [
    ['', c.allMarkets],
    ['1x2', c.market1x2],
    ['btts', c.marketBtts],
    ['over_under_2.5', c.marketTotals],
    ['double_chance', c.marketDc],
  ], [c])
  const stateOptions = useMemo(() => [
    ['', c.allStates],
    ['evaluated', c.evaluatedState],
    ['pending_result', c.pendingState],
    ['awaiting_confirmation', c.confirmingState],
    ['unscoreable_result', c.unscoreableState],
  ], [c])

  if (reportError && archiveError && !report && !archive) {
    return (
      <div className="rounded-2xl border border-red-200 bg-white p-8 text-center">
        <AlertTriangle className="mx-auto h-9 w-9 text-red-500" />
        <h2 className="mt-3 text-xl font-bold text-slate-950">{c.errorTitle}</h2>
        <p className="mx-auto mt-2 max-w-xl text-sm text-slate-600">{c.errorBody}</p>
        <button onClick={() => setRefreshKey(value => value + 1)} className="mt-5 rounded-xl bg-blue-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-blue-700">{c.retry}</button>
      </div>
    )
  }

  const coverage = report?.coverage
  const evaluated = coverage?.decision_states.evaluated ?? 0
  const pending = coverage?.decision_states.pending_result ?? 0
  const unscoreable = coverage?.decision_states.unscoreable_result ?? 0

  return (
    <div className="space-y-7">
      <section className="rounded-2xl border border-blue-200 bg-blue-50 p-5">
        <div className="flex gap-3">
          <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-blue-700" />
          <div>
            <h2 className="font-bold text-blue-950">{c.boundaryTitle}</h2>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-blue-950">{c.boundaryBody}</p>
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 text-sm font-semibold">
              <Link href="/calibration" className="text-blue-800 underline underline-offset-2">{c.calibrationLink} →</Link>
              <Link href="/track-record" className="text-blue-800 underline underline-offset-2">{c.resultsLink} →</Link>
            </div>
          </div>
        </div>
      </section>

      {reportError && !coverage ? (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-center text-sm text-amber-950">{c.errorBody}</div>
      ) : !coverage ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-sm text-slate-600">
          <RefreshCw className="mx-auto mb-3 h-6 w-6 animate-spin text-blue-600" />{c.loading}
        </div>
      ) : (
        <>
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              [c.eligible, coverage.eligible_decisions, Database],
              [c.evaluated, evaluated, CheckCircle2],
              [c.awaiting, pending, Clock3],
              [c.fixtures, coverage.evaluated_fixtures, Gauge],
            ].map(([label, value, Icon]) => {
              const MetricIcon = Icon as typeof Database
              return (
                <article key={String(label)} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
                  <MetricIcon className="h-5 w-5 text-blue-700" />
                  <p className="mt-4 text-3xl font-black text-slate-950">{String(value)}</p>
                  <p className="mt-1 text-sm text-slate-600">{String(label)}</p>
                </article>
              )
            })}
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-5">
            <h2 className="font-bold text-slate-950">{c.coverageTitle}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">{c.coverageBody(evaluated, coverage.eligible_decisions, unscoreable)}</p>
          </section>
        </>
      )}

      <section>
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <h2 className="text-2xl font-black text-slate-950">{c.archiveTitle}</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">{c.archiveBody}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <select value={market} onChange={event => { setMarket(event.target.value); setPage(1) }} className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm text-slate-800">
              {marketOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            <select value={state} onChange={event => { setState(event.target.value); setPage(1) }} className="min-h-11 rounded-xl border border-slate-300 bg-white px-3 text-sm text-slate-800">
              {stateOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
            <button onClick={() => setRefreshKey(value => value + 1)} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 bg-white px-3 text-sm font-bold text-slate-800 hover:bg-slate-50">
              <RefreshCw className="h-4 w-4" />{c.refresh}
            </button>
          </div>
        </div>

        <div className="mt-5 overflow-hidden rounded-2xl border border-slate-200 bg-white">
          {archiveError && !archive ? (
            <div className="p-10 text-center text-sm text-amber-900">{c.errorBody}</div>
          ) : !archive ? (
            <div className="p-10 text-center text-sm text-slate-500"><RefreshCw className="mx-auto mb-3 h-5 w-5 animate-spin text-blue-600" />{c.loading}</div>
          ) : archive.decisions.length === 0 ? (
            <div className="p-10 text-center text-sm text-slate-500">{c.noRows}</div>
          ) : (
            <div className="divide-y divide-slate-100">
              {archive.decisions.map(decision => (
                <article key={`${decision.fixture_id}:${decision.market}`} className="p-5">
                  <div className="flex flex-col justify-between gap-5 xl:flex-row xl:items-center">
                    <div className="min-w-0 xl:max-w-md">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${statusClass(decision.state)}`}>{stateLabel(decision.state, lang)}</span>
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-700">{marketLabel(decision.market, lang)}</span>
                      </div>
                      <h3 className="mt-3 font-black text-slate-950">{decision.home_team} <span className="font-medium text-slate-400">vs</span> {decision.away_team}</h3>
                      <p className="mt-1 text-xs leading-5 text-slate-500">
                        {decision.league} · {new Date(decision.kickoff).toLocaleString(lang === 'ro' ? 'ro-RO' : 'en-GB')} · {c.observed} {decision.hours_to_kickoff.toFixed(1)}h {c.beforeKickoff}
                      </p>
                    </div>

                    <div className="flex flex-1 flex-wrap items-center gap-2">
                      {Object.entries(decision.probabilities).map(([outcome, probability]) => (
                        <span key={outcome} className={`rounded-xl border px-3 py-2 text-xs ${outcome === decision.predicted_outcome ? 'border-blue-300 bg-blue-50 font-black text-blue-950' : 'border-slate-200 text-slate-600'}`}>
                          {c.outcomes[outcome] ?? outcome.split('_').join(' ')} {percent(probability)}
                        </span>
                      ))}
                    </div>

                    <div className="shrink-0 xl:text-right">
                      <p className="text-xs uppercase tracking-wide text-slate-500">{c.leadingOutcome}</p>
                      <p className="mt-1 font-black text-slate-950">{c.outcomes[decision.predicted_outcome] ?? decision.predicted_outcome}</p>
                      {decision.result && decision.result.home_score !== null && decision.result.away_score !== null && (
                        <p className="mt-2 text-sm text-slate-600">{c.result}: <strong className="text-slate-950">{decision.result.home_score}–{decision.result.away_score}</strong></p>
                      )}
                      {decision.correct === true && <p className="mt-1 inline-flex items-center gap-1 text-xs font-bold text-emerald-700"><CheckCircle2 className="h-3.5 w-3.5" />{c.correct}</p>}
                      {decision.correct === false && <p className="mt-1 inline-flex items-center gap-1 text-xs font-bold text-red-700"><XCircle className="h-3.5 w-3.5" />{c.incorrect}</p>}
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>

        {archive && archive.pagination.pages > 1 && (
          <div className="mt-4 flex items-center justify-between text-sm text-slate-600">
            <span>{archive.pagination.total} {c.decisions} · {c.page} {archive.pagination.page} {c.of} {archive.pagination.pages}</span>
            <div className="flex gap-2">
              <button disabled={page <= 1} onClick={() => setPage(value => value - 1)} className="rounded-lg border border-slate-300 bg-white p-2 disabled:opacity-40" aria-label={c.previous}><ChevronLeft className="h-4 w-4" /></button>
              <button disabled={page >= archive.pagination.pages} onClick={() => setPage(value => value + 1)} className="rounded-lg border border-slate-300 bg-white p-2 disabled:opacity-40" aria-label={c.next}><ChevronRight className="h-4 w-4" /></button>
            </div>
          </div>
        )}
      </section>

      <section className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
        <h2 className="font-bold text-slate-950">{c.method}</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">{c.methodBody}</p>
      </section>
    </div>
  )
}
