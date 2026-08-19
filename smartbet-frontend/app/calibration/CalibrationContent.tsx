'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Archive, CheckCircle2, Clock3, Database, Gauge, ShieldCheck } from 'lucide-react'

import { useLanguage } from '../contexts/LanguageContext'

type Lang = 'en' | 'ro'
type MetricSet = {
  brier_score: number | null
  log_loss: number | null
  top_choice_accuracy?: number | null
  expected_calibration_error?: number | null
}
type CalibrationBin = {
  lower: number
  upper: number
  forecast_count: number
  fixture_count: number
  mean_forecast: number
  observed_frequency: number | null
  wilson_95: [number, number] | null
  status: 'visible' | 'collecting'
}
type MarketSummary = {
  market: string
  fixture_count: number
  evidence_level: string
  minimum_for_metrics: number
  metrics_visible: boolean
  provider: MetricSet
  uniform_baseline: MetricSet
  calibration_bins: CalibrationBin[]
}
type Report = {
  methodology_version: string
  evaluation_horizon_hours: number
  minimum_public_fixtures: number
  coverage: {
    fixture_market_universe: number
    eligible_decisions: number
    evaluated_market_decisions: number
    evaluated_fixtures: number
  }
  markets: MarketSummary[]
}

const COPY = {
  en: {
    eyebrow: 'Public probability evidence',
    title: 'Are the probabilities honest?',
    intro: 'Every complete pre-match probability vector is preserved, paired with a confirmed result and scored under one fixed rule. Small samples are shown as evidence—not promoted as conclusions.',
    horizon: (hours: number) => `Latest vector ≥ ${hours}h before kickoff`,
    confirmed: 'Confirmed full-time results only',
    complete: 'Complete outcome vectors',
    loading: 'Loading public evidence…',
    unavailable: 'Evidence unavailable',
    unavailableBody: 'The calibration evidence service is temporarily unavailable.',
    observed: 'Observed fixture-markets', eligible: 'Eligible decisions', evaluated: 'Evaluated decisions', fixtures: 'Independent fixtures',
    marketHeading: 'Evidence by market',
    marketBody: (minimum: number) => `Lower Brier score and log loss are better. They measure probability quality, not profit. Metrics unlock after ${minimum} confirmed fixtures in that market.`,
    collecting: 'Collecting', confirmedFixtures: 'confirmed fixtures', required: 'required',
    lockedBody: 'The rows remain public, but summary scores stay locked because the sample is too small to interpret responsibly.',
    brier: 'Brier score ↓', naive: 'uniform baseline', accuracy: 'Top-choice accuracy', logLoss: 'Log loss ↓', calibrationError: 'Calibration error ↓',
    reliability: 'Reliability by probability band',
    reliabilityBody: 'A trustworthy 60% forecast should occur about 60% of the time. Sparse bands remain hidden.',
    band: 'Forecast band', forecasts: 'Forecasts', mean: 'Mean forecast', observedFrequency: 'Observed', range: '95% range',
    denominatorTitle: 'The denominator is fixed before seeing the result',
    denominatorBody: 'For each fixture and market, the evaluator chooses the nearest complete vector that existed at least one hour before kickoff. Later snapshots and repeated scans cannot add extra decisions. A corrected result leaves evaluation until the new score is independently confirmed.',
    method: 'Method', methodology: 'ranking methodology',
    limits: 'Interpretation limits',
    notes: [
      'One fixture-market decision is selected at the fixed pre-kickoff horizon; repeated observations do not increase the sample.',
      'Only complete probability vectors paired with confirmed, scoreable full-time results are evaluated.',
      'Markets from the same fixture share one scoreline and are not independent observations.',
      'These are probability-quality diagnostics, not evidence of betting profitability.',
    ],
    archiveCta: 'Inspect every underlying decision',
    marketLabels: { '1x2': 'Match result', btts: 'Both teams to score', 'over_under_2.5': 'Over / under 2.5' } as Record<string, string>,
  },
  ro: {
    eyebrow: 'Dovezi publice despre probabilități',
    title: 'Sunt probabilitățile corecte?',
    intro: 'Păstrăm fiecare vector complet de probabilități înregistrat înaintea meciului, îl asociem cu un rezultat confirmat și îl evaluăm după o singură regulă fixă. Eșantioanele mici sunt prezentate ca dovezi, nu ca verdict.',
    horizon: (hours: number) => `Ultimul vector ≥ ${hours}h înainte de start`,
    confirmed: 'Doar rezultate finale confirmate',
    complete: 'Vectori compleți pentru toate rezultatele',
    loading: 'Se încarcă dovezile publice…',
    unavailable: 'Dovezile sunt indisponibile',
    unavailableBody: 'Serviciul de calibrare este temporar indisponibil.',
    observed: 'Perechi meci–piață observate', eligible: 'Decizii eligibile', evaluated: 'Decizii evaluate', fixtures: 'Meciuri independente',
    marketHeading: 'Dovezi pentru fiecare piață',
    marketBody: (minimum: number) => `Un scor Brier și o pierdere logaritmică mai mici sunt mai bune. Acestea măsoară calitatea probabilităților, nu profitul. Indicatorii se activează după ${minimum} de meciuri confirmate pe piața respectivă.`,
    collecting: 'În colectare', confirmedFixtures: 'meciuri confirmate', required: 'necesare',
    lockedBody: 'Rândurile rămân publice, dar indicatorii agregați sunt ascunși deoarece eșantionul este prea mic pentru o interpretare responsabilă.',
    brier: 'Scor Brier ↓', naive: 'referință uniformă', accuracy: 'Acuratețea opțiunii principale', logLoss: 'Pierdere logaritmică ↓', calibrationError: 'Eroare de calibrare ↓',
    reliability: 'Fiabilitate pe intervale de probabilitate',
    reliabilityBody: 'O estimare corectă de 60% ar trebui să se confirme în aproximativ 60% dintre cazuri. Intervalele cu puține date rămân ascunse.',
    band: 'Interval estimat', forecasts: 'Estimări', mean: 'Media estimată', observedFrequency: 'Frecvență observată', range: 'Interval 95%',
    denominatorTitle: 'Numitorul este fixat înainte să cunoaștem rezultatul',
    denominatorBody: 'Pentru fiecare meci și piață, evaluatorul alege cel mai apropiat vector complet existent cu cel puțin o oră înainte de start. Snapshoturile ulterioare și scanările repetate nu pot adăuga decizii suplimentare. Un rezultat corectat iese temporar din evaluare până când noul scor este confirmat independent.',
    method: 'Metodă', methodology: 'metodologia de clasificare',
    limits: 'Limite de interpretare',
    notes: [
      'Este aleasă o singură decizie meci–piață la orizontul fix de dinaintea meciului; observațiile repetate nu măresc eșantionul.',
      'Sunt evaluate doar vectorii compleți de probabilități asociați cu rezultate finale confirmate și evaluabile.',
      'Piețele aceluiași meci folosesc același scor final și nu sunt observații independente.',
      'Aceștia sunt indicatori ai calității probabilităților, nu dovezi ale profitabilității pariurilor.',
    ],
    archiveCta: 'Verifică fiecare decizie din arhivă',
    marketLabels: { '1x2': 'Rezultatul meciului', btts: 'Ambele echipe marchează', 'over_under_2.5': 'Peste / sub 2,5 goluri' } as Record<string, string>,
  },
} as const

function percent(value: number | null | undefined) {
  return value === null || value === undefined ? '—' : `${(value * 100).toFixed(1)}%`
}
function score(value: number | null | undefined) {
  return value === null || value === undefined ? '—' : value.toFixed(3)
}

function MetricCard({ market, language }: { market: MarketSummary; language: Lang }) {
  const c = COPY[language]
  const progress = Math.min(100, (market.fixture_count / market.minimum_for_metrics) * 100)
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div><p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{market.market}</p><h3 className="mt-1 text-lg font-bold text-slate-950">{c.marketLabels[market.market] ?? market.market}</h3></div>
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${market.metrics_visible ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-900'}`}>{market.metrics_visible ? market.evidence_level : c.collecting}</span>
      </div>
      {!market.metrics_visible ? (
        <div className="mt-5">
          <div className="flex justify-between text-sm text-slate-700"><span>{market.fixture_count} {c.confirmedFixtures}</span><span>{market.minimum_for_metrics} {c.required}</span></div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-amber-400" style={{ width: `${progress}%` }} /></div>
          <p className="mt-4 text-sm leading-relaxed text-slate-600">{c.lockedBody}</p>
        </div>
      ) : (
        <div className="mt-5 grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">{c.brier}</p><p className="mt-1 text-xl font-bold text-slate-950">{score(market.provider.brier_score)}</p><p className="text-xs text-slate-500">{c.naive} {score(market.uniform_baseline.brier_score)}</p></div>
          <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">{c.accuracy}</p><p className="mt-1 text-xl font-bold text-slate-950">{percent(market.provider.top_choice_accuracy)}</p><p className="text-xs text-slate-500">n = {market.fixture_count}</p></div>
          <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">{c.logLoss}</p><p className="mt-1 text-xl font-bold text-slate-950">{score(market.provider.log_loss)}</p></div>
          <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">{c.calibrationError}</p><p className="mt-1 text-xl font-bold text-slate-950">{percent(market.provider.expected_calibration_error)}</p></div>
        </div>
      )}
    </article>
  )
}

function CalibrationTable({ market, language }: { market: MarketSummary; language: Lang }) {
  const c = COPY[language]
  if (!market.calibration_bins.length) return null
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-5 py-4"><h3 className="font-bold text-slate-950">{c.marketLabels[market.market] ?? market.market}</h3><p className="mt-1 text-xs text-slate-500">{c.reliabilityBody}</p></div>
      <div className="overflow-x-auto"><table className="min-w-full text-left text-sm"><thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500"><tr><th className="px-5 py-3">{c.band}</th><th className="px-5 py-3">{c.forecasts}</th><th className="px-5 py-3">{c.mean}</th><th className="px-5 py-3">{c.observedFrequency}</th><th className="px-5 py-3">{c.range}</th></tr></thead>
        <tbody className="divide-y divide-slate-100">{market.calibration_bins.map(bin => <tr key={`${bin.lower}-${bin.upper}`}><td className="px-5 py-3 font-medium text-slate-900">{percent(bin.lower)}–{percent(bin.upper)}</td><td className="px-5 py-3 text-slate-600">{bin.forecast_count} ({bin.fixture_count})</td><td className="px-5 py-3 text-slate-900">{percent(bin.mean_forecast)}</td><td className="px-5 py-3 text-slate-900">{bin.status === 'visible' ? percent(bin.observed_frequency) : c.collecting}</td><td className="px-5 py-3 text-slate-600">{bin.wilson_95 ? `${percent(bin.wilson_95[0])}–${percent(bin.wilson_95[1])}` : '—'}</td></tr>)}</tbody></table></div>
    </div>
  )
}

export default function CalibrationContent() {
  const { language } = useLanguage()
  const lang: Lang = language === 'ro' ? 'ro' : 'en'
  const c = COPY[lang]
  const [report, setReport] = useState<Report | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    fetch('/api/calibration', { cache: 'no-store' }).then(async response => {
      const body = await response.json()
      if (!response.ok || !body.success) throw new Error('unavailable')
      setReport(body.data)
    }).catch(() => setError(true))
  }, [])

  const visibleCalibration = useMemo(() => report?.markets.filter(item => item.calibration_bins.length > 0) || [], [report])
  if (error && !report) return <main className="min-h-screen bg-slate-50 px-4 py-16"><div className="mx-auto max-w-xl rounded-2xl border border-red-200 bg-white p-8 text-center"><AlertTriangle className="mx-auto h-8 w-8 text-red-500" /><h1 className="mt-3 text-xl font-bold text-slate-950">{c.unavailable}</h1><p className="mt-2 text-slate-600">{c.unavailableBody}</p></div></main>

  return (
    <main className="min-h-screen bg-slate-50">
      <section className="border-b border-slate-200 bg-slate-950 px-4 py-14 text-white"><div className="mx-auto max-w-6xl"><div className="flex items-center gap-2 text-sm font-semibold text-cyan-300"><ShieldCheck className="h-4 w-4" />{c.eyebrow}</div><h1 className="mt-4 max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl">{c.title}</h1><p className="mt-5 max-w-3xl text-lg leading-relaxed text-slate-300">{c.intro}</p><div className="mt-7 flex flex-wrap gap-3 text-sm"><span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5">{c.horizon(report?.evaluation_horizon_hours ?? 1)}</span><span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5">{c.confirmed}</span><span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5">{c.complete}</span></div></div></section>
      <div className="mx-auto max-w-6xl px-4 py-10">
        {!report ? <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-slate-600">{c.loading}</div> : <>
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{[
            [c.observed, report.coverage.fixture_market_universe, Database], [c.eligible, report.coverage.eligible_decisions, Gauge], [c.evaluated, report.coverage.evaluated_market_decisions, CheckCircle2], [c.fixtures, report.coverage.evaluated_fixtures, Archive],
          ].map(([label, value, Icon]) => { const MetricIcon = Icon as typeof Database; return <div key={String(label)} className="rounded-2xl border border-slate-200 bg-white p-5"><MetricIcon className="h-5 w-5 text-cyan-700" /><p className="mt-4 text-3xl font-bold text-slate-950">{String(value)}</p><p className="mt-1 text-sm text-slate-600">{String(label)}</p></div> })}</section>
          <section className="mt-10"><h2 className="text-2xl font-bold text-slate-950">{c.marketHeading}</h2><p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-600">{c.marketBody(report.minimum_public_fixtures)}</p><div className="mt-5 grid gap-4 lg:grid-cols-3">{report.markets.map(item => <MetricCard key={item.market} market={item} language={lang} />)}</div></section>
          {visibleCalibration.length > 0 && <section className="mt-10 space-y-5"><h2 className="text-2xl font-bold text-slate-950">{c.reliability}</h2>{visibleCalibration.map(item => <CalibrationTable key={item.market} market={item} language={lang} />)}</section>}
          <section className="mt-10 rounded-2xl border border-blue-200 bg-blue-50 p-6"><div className="flex gap-3"><Clock3 className="mt-0.5 h-5 w-5 shrink-0 text-blue-700" /><div><h2 className="font-bold text-blue-950">{c.denominatorTitle}</h2><p className="mt-2 text-sm leading-relaxed text-blue-950">{c.denominatorBody}</p><p className="mt-3 text-sm text-blue-900">{c.method}: <code className="font-semibold">{report.methodology_version}</code> · <Link href="/methodology" className="font-semibold underline underline-offset-2">{c.methodology}</Link></p></div></div></section>
        </>}
        <section className="mt-10 rounded-2xl border border-slate-200 bg-white p-6"><h2 className="font-bold text-slate-950">{c.limits}</h2><ul className="mt-3 space-y-2 text-sm leading-relaxed text-slate-600">{c.notes.map(note => <li key={note}>• {note}</li>)}</ul><Link href="/monitoring" className="mt-5 inline-flex font-semibold text-blue-700 underline underline-offset-2">{c.archiveCta} →</Link></section>
      </div>
    </main>
  )
}
