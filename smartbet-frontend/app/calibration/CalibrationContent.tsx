'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { AlertTriangle, Archive, CheckCircle2, ChevronLeft, ChevronRight, Clock3, Database, Gauge, ShieldCheck } from 'lucide-react'

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
  gap: number | null
  wilson_95: [number, number] | null
  status: 'visible' | 'collecting'
}

type MarketSummary = {
  market: string
  label: string
  fixture_count: number
  evidence_level: string
  minimum_for_metrics: number
  metrics_visible: boolean
  provider: MetricSet
  uniform_baseline: MetricSet
  market_baseline: MetricSet & { fixture_count: number; metrics_visible: boolean }
  calibration_bins: CalibrationBin[]
}

type Report = {
  methodology_version: string
  evaluation_horizon_hours: number
  minimum_public_fixtures: number
  minimum_public_bin_forecasts: number
  generated_at: string
  coverage: {
    fixture_market_universe: number
    eligible_decisions: number
    evaluated_market_decisions: number
    evaluated_fixtures: number
    decision_states: Record<string, number>
    excluded_before_evaluation: Record<string, number>
  }
  markets: MarketSummary[]
  notes: string[]
}

type Decision = {
  fixture_id: number
  fixture: string
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
  provider_model_version: string
  pipeline_version: string
  result: { home_score: number | null; away_score: number | null; confirmed: boolean } | null
}

type ArchiveResponse = {
  success: boolean
  pagination: { page: number; page_size: number; total: number; pages: number }
  decisions: Decision[]
}

const MARKET_OPTIONS = [
  ['', 'All markets'],
  ['1x2', 'Match result'],
  ['btts', 'Both teams score'],
  ['over_under_2.5', 'Over / under 2.5'],
  ['double_chance', 'Double chance'],
]

const STATE_OPTIONS = [
  ['', 'Every state'],
  ['evaluated', 'Evaluated'],
  ['pending_result', 'Pending result'],
  ['awaiting_confirmation', 'Awaiting confirmation'],
  ['unscoreable_result', 'Unscoreable'],
]

function percent(value: number | null | undefined) {
  return value === null || value === undefined ? '—' : `${(value * 100).toFixed(1)}%`
}

function score(value: number | null | undefined) {
  return value === null || value === undefined ? '—' : value.toFixed(3)
}

function stateLabel(value: string) {
  return ({
    evaluated: 'Evaluated',
    pending_result: 'Pending result',
    awaiting_confirmation: 'Confirming result',
    unscoreable_result: 'Not scoreable',
  } as Record<string, string>)[value] || value
}

function MetricCard({ market }: { market: MarketSummary }) {
  const progress = Math.min(100, (market.fixture_count / market.minimum_for_metrics) * 100)
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{market.market}</p>
          <h3 className="mt-1 text-lg font-bold text-slate-950">{market.label}</h3>
        </div>
        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${market.metrics_visible ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-900'}`}>
          {market.metrics_visible ? market.evidence_level : 'Collecting'}
        </span>
      </div>

      {!market.metrics_visible ? (
        <div className="mt-5">
          <div className="flex justify-between text-sm text-slate-700">
            <span>{market.fixture_count} confirmed fixtures</span>
            <span>{market.minimum_for_metrics} required</span>
          </div>
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-amber-400" style={{ width: `${progress}%` }} />
          </div>
          <p className="mt-4 text-sm leading-relaxed text-slate-600">
            The rows are public below. Summary scores remain locked because this sample is too small to interpret responsibly.
          </p>
        </div>
      ) : (
        <div className="mt-5 grid grid-cols-2 gap-3">
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Brier score ↓</p>
            <p className="mt-1 text-xl font-bold text-slate-950">{score(market.provider.brier_score)}</p>
            <p className="text-xs text-slate-500">naive {score(market.uniform_baseline.brier_score)}</p>
          </div>
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Top-choice accuracy</p>
            <p className="mt-1 text-xl font-bold text-slate-950">{percent(market.provider.top_choice_accuracy)}</p>
            <p className="text-xs text-slate-500">n = {market.fixture_count}</p>
          </div>
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Log loss ↓</p>
            <p className="mt-1 text-xl font-bold text-slate-950">{score(market.provider.log_loss)}</p>
          </div>
          <div className="rounded-xl bg-slate-50 p-3">
            <p className="text-xs text-slate-500">Calibration error ↓</p>
            <p className="mt-1 text-xl font-bold text-slate-950">{percent(market.provider.expected_calibration_error)}</p>
          </div>
        </div>
      )}
    </article>
  )
}

function CalibrationTable({ market }: { market: MarketSummary }) {
  if (!market.calibration_bins.length) return null
  return (
    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
      <div className="border-b border-slate-200 px-5 py-4">
        <h3 className="font-bold text-slate-950">{market.label} reliability</h3>
        <p className="mt-1 text-xs text-slate-500">A trustworthy 60% forecast should occur about 60% of the time. Sparse bands stay hidden.</p>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-5 py-3">Forecast band</th>
              <th className="px-5 py-3">Forecasts</th>
              <th className="px-5 py-3">Mean forecast</th>
              <th className="px-5 py-3">Observed</th>
              <th className="px-5 py-3">95% range</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {market.calibration_bins.map((bin) => (
              <tr key={`${bin.lower}-${bin.upper}`}>
                <td className="px-5 py-3 font-medium text-slate-900">{percent(bin.lower)}–{percent(bin.upper)}</td>
                <td className="px-5 py-3 text-slate-600">{bin.forecast_count} ({bin.fixture_count} fixtures)</td>
                <td className="px-5 py-3 text-slate-900">{percent(bin.mean_forecast)}</td>
                <td className="px-5 py-3 text-slate-900">{bin.status === 'visible' ? percent(bin.observed_frequency) : 'Collecting'}</td>
                <td className="px-5 py-3 text-slate-600">{bin.wilson_95 ? `${percent(bin.wilson_95[0])}–${percent(bin.wilson_95[1])}` : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function CalibrationContent() {
  const [report, setReport] = useState<Report | null>(null)
  const [archive, setArchive] = useState<ArchiveResponse | null>(null)
  const [error, setError] = useState('')
  const [market, setMarket] = useState('')
  const [state, setState] = useState('')
  const [page, setPage] = useState(1)

  useEffect(() => {
    fetch('/api/calibration', { cache: 'no-store' })
      .then(async (response) => {
        const body = await response.json()
        if (!response.ok || !body.success) throw new Error(body.error || 'Unavailable')
        setReport(body.data)
      })
      .catch(() => setError('The calibration evidence service is temporarily unavailable.'))
  }, [])

  useEffect(() => {
    const params = new URLSearchParams({ page: String(page), page_size: '20' })
    if (market) params.set('market', market)
    if (state) params.set('state', state)
    fetch(`/api/prediction-archive?${params}`, { cache: 'no-store' })
      .then(async (response) => {
        const body = await response.json()
        if (!response.ok || !body.success) throw new Error(body.error || 'Unavailable')
        setArchive(body)
      })
      .catch(() => setError('The prediction archive is temporarily unavailable.'))
  }, [market, state, page])

  const visibleCalibration = useMemo(
    () => report?.markets.filter((item) => item.calibration_bins.length > 0) || [],
    [report],
  )

  if (error && !report) {
    return (
      <main className="min-h-screen bg-slate-50 px-4 py-16">
        <div className="mx-auto max-w-xl rounded-2xl border border-red-200 bg-white p-8 text-center">
          <AlertTriangle className="mx-auto h-8 w-8 text-red-500" />
          <h1 className="mt-3 text-xl font-bold text-slate-950">Evidence unavailable</h1>
          <p className="mt-2 text-slate-600">{error}</p>
        </div>
      </main>
    )
  }

  return (
    <main className="min-h-screen bg-slate-50">
      <section className="border-b border-slate-200 bg-slate-950 px-4 py-14 text-white">
        <div className="mx-auto max-w-6xl">
          <div className="flex items-center gap-2 text-sm font-semibold text-cyan-300">
            <ShieldCheck className="h-4 w-4" /> Public probability evidence
          </div>
          <h1 className="mt-4 max-w-3xl text-4xl font-bold tracking-tight sm:text-5xl">
            Are the probabilities honest?
          </h1>
          <p className="mt-5 max-w-3xl text-lg leading-relaxed text-slate-300">
            Every complete pre-match probability vector is preserved, paired with a confirmed result and scored under one fixed rule. Small samples are shown as evidence—not promoted as conclusions.
          </p>
          <div className="mt-7 flex flex-wrap gap-3 text-sm">
            <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5">Latest vector ≥ {report?.evaluation_horizon_hours ?? 1}h before kickoff</span>
            <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5">Confirmed full-time results only</span>
            <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1.5">Complete outcome vectors</span>
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-6xl px-4 py-10">
        {!report ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center text-slate-600">Loading public evidence…</div>
        ) : (
          <>
            <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                { label: 'Observed fixture-markets', value: report.coverage.fixture_market_universe, icon: Database },
                { label: 'Eligible decisions', value: report.coverage.eligible_decisions, icon: Gauge },
                { label: 'Evaluated decisions', value: report.coverage.evaluated_market_decisions, icon: CheckCircle2 },
                { label: 'Independent fixtures', value: report.coverage.evaluated_fixtures, icon: Archive },
              ].map(({ label, value, icon: Icon }) => (
                <div key={label} className="rounded-2xl border border-slate-200 bg-white p-5">
                  <Icon className="h-5 w-5 text-cyan-700" />
                  <p className="mt-4 text-3xl font-bold text-slate-950">{value}</p>
                  <p className="mt-1 text-sm text-slate-600">{label}</p>
                </div>
              ))}
            </section>

            <section className="mt-10">
              <div className="max-w-3xl">
                <h2 className="text-2xl font-bold text-slate-950">Evidence by market</h2>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">
                  Lower Brier score and log loss are better. They measure probability quality, not profit. Metrics unlock after {report.minimum_public_fixtures} confirmed fixtures in that market.
                </p>
              </div>
              <div className="mt-5 grid gap-4 lg:grid-cols-3">
                {report.markets.map((item) => <MetricCard key={item.market} market={item} />)}
              </div>
            </section>

            {visibleCalibration.length > 0 && (
              <section className="mt-10 space-y-5">
                <h2 className="text-2xl font-bold text-slate-950">Reliability by probability band</h2>
                {visibleCalibration.map((item) => <CalibrationTable key={item.market} market={item} />)}
              </section>
            )}

            <section className="mt-10 rounded-2xl border border-blue-200 bg-blue-50 p-6">
              <div className="flex gap-3">
                <Clock3 className="mt-0.5 h-5 w-5 shrink-0 text-blue-700" />
                <div>
                  <h2 className="font-bold text-blue-950">The denominator is fixed before seeing the result</h2>
                  <p className="mt-2 text-sm leading-relaxed text-blue-950">
                    For each fixture and market, the evaluator chooses the nearest complete vector that existed at least one hour before kickoff. Later snapshots, repeated sweeps and the separate outcome rows cannot add extra decisions. A corrected result temporarily leaves evaluation until the new score is independently confirmed.
                  </p>
                  <p className="mt-3 text-sm text-blue-900">
                    Method: <code className="font-semibold">{report.methodology_version}</code> ·{' '}
                    <Link href="/methodology" className="font-semibold underline underline-offset-2">ranking methodology</Link>
                  </p>
                </div>
              </div>
            </section>
          </>
        )}

        <section className="mt-12" id="archive">
          <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
            <div>
              <h2 className="text-2xl font-bold text-slate-950">Prediction evidence archive</h2>
              <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-600">
                The selected pre-match vector remains visible whether the result is pending, won, lost or cannot be scored. Use the filters to inspect the denominator yourself.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <select value={market} onChange={(event) => { setMarket(event.target.value); setPage(1) }} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800">
                {MARKET_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
              <select value={state} onChange={(event) => { setState(event.target.value); setPage(1) }} className="rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-800">
                {STATE_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
              </select>
            </div>
          </div>

          <div className="mt-5 overflow-hidden rounded-2xl border border-slate-200 bg-white">
            {!archive ? (
              <div className="p-8 text-center text-sm text-slate-500">Loading archive…</div>
            ) : archive.decisions.length === 0 ? (
              <div className="p-8 text-center text-sm text-slate-500">No decisions match these filters yet.</div>
            ) : (
              <div className="divide-y divide-slate-100">
                {archive.decisions.map((decision) => (
                  <article key={`${decision.fixture_id}-${decision.market}`} className="p-5">
                    <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="font-bold text-slate-950">{decision.fixture}</h3>
                          <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium text-slate-700">{decision.market_label}</span>
                          <span className={`rounded-full px-2 py-1 text-xs font-semibold ${decision.state === 'evaluated' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-900'}`}>{stateLabel(decision.state)}</span>
                        </div>
                        <p className="mt-1 text-xs text-slate-500">{decision.league} · {new Date(decision.kickoff).toLocaleString()} · observed {decision.hours_to_kickoff.toFixed(1)}h before kickoff</p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        {Object.entries(decision.probabilities).map(([outcome, probability]) => (
                          <span key={outcome} className={`rounded-lg border px-2.5 py-1.5 text-xs ${outcome === decision.predicted_outcome ? 'border-cyan-300 bg-cyan-50 font-bold text-cyan-900' : 'border-slate-200 text-slate-600'}`}>
                            {outcome.split('_').join(' ')} {percent(probability)}
                          </span>
                        ))}
                        {decision.result && (
                          <span className="ml-1 text-sm font-semibold text-slate-800">
                            {decision.result.home_score}–{decision.result.away_score}
                          </span>
                        )}
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </div>

          {archive && archive.pagination.pages > 1 && (
            <div className="mt-4 flex items-center justify-between text-sm text-slate-600">
              <span>{archive.pagination.total} decisions · page {archive.pagination.page} of {archive.pagination.pages}</span>
              <div className="flex gap-2">
                <button disabled={page <= 1} onClick={() => setPage((value) => value - 1)} className="rounded-lg border border-slate-300 bg-white p-2 disabled:opacity-40" aria-label="Previous archive page"><ChevronLeft className="h-4 w-4" /></button>
                <button disabled={page >= archive.pagination.pages} onClick={() => setPage((value) => value + 1)} className="rounded-lg border border-slate-300 bg-white p-2 disabled:opacity-40" aria-label="Next archive page"><ChevronRight className="h-4 w-4" /></button>
              </div>
            </div>
          )}
        </section>

        <section className="mt-10 rounded-2xl border border-slate-200 bg-white p-6">
          <h2 className="font-bold text-slate-950">Interpretation limits</h2>
          <ul className="mt-3 space-y-2 text-sm leading-relaxed text-slate-600">
            {report?.notes.map((note) => <li key={note}>• {note}</li>)}
          </ul>
        </section>
      </div>
    </main>
  )
}
