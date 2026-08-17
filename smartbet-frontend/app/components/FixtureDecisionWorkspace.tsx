'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Calculator,
  CheckCircle2,
  Clock3,
  Database,
  Scale,
} from 'lucide-react'
import { useLanguage } from '../contexts/LanguageContext'
import { canPublishPrice } from '../lib/marketPricing'
import {
  calculatePersonalPrice,
  formatFixtureForm,
  type FixtureIntelligence,
  type IntelligenceLimitation,
  type IntelligenceMarket,
  type IntelligenceOutcome,
} from '../lib/fixtureIntelligence'
import { generateMatchSlug } from '../../src/utils/seo-helpers'
import FixtureContextTimelinePanel from './FixtureContextTimelinePanel'
import AllMarketsBrowser from './AllMarketsBrowser'
import type { FixtureContextTimeline } from '../lib/fixtureTimeline'
import type { FixtureMarketCatalogue } from '../lib/marketCatalogue'

export interface FixtureDecisionFixture {
  fixture_id: number
  home_team: string
  away_team: string
  league_id?: number | null
  league: string
  kickoff: string
  intelligence: FixtureIntelligence
  market_catalogue?: FixtureMarketCatalogue | null
  teams_data?: {
    home?: { form?: unknown }
    away?: { form?: unknown }
  }
  context_timeline?: FixtureContextTimeline | null
}

interface FixtureDecisionWorkspaceProps {
  fixture: FixtureDecisionFixture
  lastUpdated?: string | null
  proofUrl?: string | null
  showFullPageLink?: boolean
}

const pct = (value: number | null, digits = 1): string =>
  value === null ? '—' : `${(value * 100).toFixed(digits)}%`

const decimal = (value: number | null, digits = 2): string =>
  value === null ? '—' : value.toFixed(digits)

const limitationCopy = (limitation: IntelligenceLimitation, ro: boolean): string => {
  const copy: Record<IntelligenceLimitation, { en: string; ro: string }> = {
    provider_probabilities_incomplete: {
      en: 'Model probabilities are unavailable for one or more markets.',
      ro: 'Probabilitățile modelului nu sunt disponibile pentru una sau mai multe piețe.',
    },
    verified_price_board_incomplete: {
      en: 'A complete verified price board is unavailable for one or more markets.',
      ro: 'Un panou complet de prețuri verificate nu este disponibil pentru una sau mai multe piețe.',
    },
    canonical_board_not_single_bookmaker: {
      en: 'The market view normalises BetGlitch canonical quotes; it is not one bookmaker’s complete board.',
      ro: 'Perspectiva pieței normalizează cotele canonice BetGlitch; nu reprezintă panoul complet al unei singure case.',
    },
    reference_views_not_value_verdict: {
      en: 'Model and market probabilities are separate reference views, not a BetGlitch value verdict.',
      ro: 'Probabilitățile modelului și ale pieței sunt perspective distincte, nu un verdict BetGlitch despre valoare.',
    },
  }
  return ro ? copy[limitation].ro : copy[limitation].en
}

export default function FixtureDecisionWorkspace({
  fixture,
  lastUpdated,
  proofUrl,
  showFullPageLink = false,
}: FixtureDecisionWorkspaceProps) {
  const { language } = useLanguage()
  const ro = language === 'ro'
  const markets = fixture.intelligence?.markets ?? []
  const firstMarketKey = markets[0]?.key ?? '1x2'
  const [activeMarketKey, setActiveMarketKey] = useState(firstMarketKey)
  const activeMarket = markets.find((market) => market.key === activeMarketKey) ?? markets[0]
  const [selectedOutcomeKey, setSelectedOutcomeKey] = useState(activeMarket?.outcomes[0]?.key ?? '')
  const [personalProbability, setPersonalProbability] = useState('')

  useEffect(() => {
    const nextMarket = markets[0]
    setActiveMarketKey(nextMarket?.key ?? '1x2')
    setSelectedOutcomeKey(nextMarket?.outcomes[0]?.key ?? '')
    setPersonalProbability('')
  }, [fixture.fixture_id]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!activeMarket?.outcomes.some((outcome) => outcome.key === selectedOutcomeKey)) {
      setSelectedOutcomeKey(activeMarket?.outcomes[0]?.key ?? '')
      setPersonalProbability('')
    }
  }, [activeMarket, selectedOutcomeKey])

  const selectedOutcome = activeMarket?.outcomes.find(
    (outcome) => outcome.key === selectedOutcomeKey,
  ) ?? activeMarket?.outcomes[0]

  const personalPrice = useMemo(
    () => calculatePersonalPrice(Number(personalProbability), selectedOutcome?.odds ?? null),
    [personalProbability, selectedOutcome?.odds],
  )

  if (!activeMarket) {
    return (
      <div className="rounded-2xl border border-amber-200 bg-amber-50 p-6 text-sm text-amber-900">
        {ro
          ? 'Modelul nu are încă suficiente date pentru această analiză.'
          : 'The model does not have enough data for this analysis yet.'}
      </div>
    )
  }

  const freshness = fixture.intelligence.data_quality.freshest_price_age_hours
  const updated = lastUpdated ? new Date(lastUpdated) : new Date(fixture.intelligence.generated_at)
  const matchSlug = generateMatchSlug(
    fixture.home_team,
    fixture.away_team,
    fixture.kickoff,
    fixture.fixture_id,
    fixture.league,
  )

  const changeMarket = (market: IntelligenceMarket) => {
    setActiveMarketKey(market.key)
    setSelectedOutcomeKey(market.outcomes[0]?.key ?? '')
    setPersonalProbability('')
  }

  return (
    <div className="space-y-6">
      <section className="overflow-hidden rounded-2xl border border-slate-200 bg-slate-950 text-white shadow-sm">
        <div className="bg-[radial-gradient(circle_at_top_right,_rgba(37,99,235,0.35),_transparent_42%)] p-6 md:p-8">
          <div className="flex flex-col gap-5 md:flex-row md:items-start md:justify-between">
            <div>
              <div className="mb-3 flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-blue-200">
                <span>{fixture.league}</span>
                <span aria-hidden>·</span>
                <span>{new Date(fixture.kickoff).toLocaleString(ro ? 'ro-RO' : 'en-GB', {
                  weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
                })}</span>
              </div>
              <h2 className="text-2xl font-bold tracking-tight md:text-3xl">
                {fixture.home_team} <span className="font-normal text-slate-400">vs</span> {fixture.away_team}
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-300">
                {ro
                  ? 'Spațiu de analiză pentru preț, model și incertitudine. Nicio valoare de aici nu este automat o recomandare BetGlitch.'
                  : 'A workspace for price, model and uncertainty. Nothing here automatically becomes a BetGlitch recommendation.'}
              </p>
            </div>
            <div className="flex flex-wrap gap-2 md:max-w-xs md:justify-end">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-sky-400/40 bg-sky-400/10 px-3 py-1.5 text-xs font-semibold text-sky-100">
                <Activity className="h-3.5 w-3.5" /> {ro ? 'ANALIZĂ LIVE' : 'LIVE ANALYSIS'}
              </span>
              {proofUrl && (
                <a href={proofUrl} className="inline-flex items-center gap-1.5 rounded-full border border-indigo-300/40 bg-indigo-300/10 px-3 py-1.5 text-xs font-semibold text-indigo-100 hover:bg-indigo-300/20">
                  <CheckCircle2 className="h-3.5 w-3.5" /> {ro ? 'VEZI SELECȚIA BLOCATĂ' : 'VIEW LOCKED PICK'}
                </a>
              )}
            </div>
          </div>

          {proofUrl && (
            <p className="mt-4 max-w-3xl rounded-xl border border-indigo-300/30 bg-indigo-300/10 p-3 text-xs leading-relaxed text-indigo-100">
              {ro
                ? 'Analiza live se poate schimba. Această selecție a fost publicată și blocată înainte de start; nu poate fi modificată sau ștearsă.'
                : 'Live analysis may change. This published pick was locked before kickoff and cannot be edited or removed.'}
            </p>
          )}

          <div className="mt-6 grid gap-3 sm:grid-cols-3">
            <Metric
              icon={<Database className="h-4 w-4" />}
              label={ro ? 'Piețe cu date de model' : 'Markets with model data'}
              value={`${fixture.intelligence.data_quality.provider_markets_available}/${markets.length}`}
            />
            <Metric
              icon={<Scale className="h-4 w-4" />}
              label={ro ? 'Panouri complete de preț' : 'Complete price boards'}
              value={`${fixture.intelligence.data_quality.complete_price_boards}/${markets.filter((market) => market.probability_kind === 'distribution').length}`}
            />
            <Metric
              icon={<Clock3 className="h-4 w-4" />}
              label={ro ? 'Cel mai proaspăt preț' : 'Freshest verified price'}
              value={freshness === null ? (ro ? 'Indisponibil' : 'Unavailable') : freshness < 1 ? '< 1h' : `${freshness.toFixed(1)}h`}
            />
          </div>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:p-7">
        <div className="mb-5">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-600">
            {ro ? 'PREȚ ȘI PROBABILITATE' : 'PRICE AND PROBABILITY'}
          </p>
          <h3 className="mt-1 text-xl font-bold text-slate-950">
            {ro ? 'Compară două perspective distincte' : 'Compare two distinct reference views'}
          </h3>
          <p className="mt-2 max-w-3xl text-sm leading-relaxed text-slate-600">
            {ro
              ? 'Modelul de predicție și piața fără marjă sunt afișate separat. Diferența dintre ele nu este o dovadă de valoare.'
              : 'The prediction model and the margin-removed market view are shown separately. Their difference is not proof of value.'}
          </p>
        </div>

        <div className="mb-5 flex gap-2 overflow-x-auto pb-1" role="tablist" aria-label={ro ? 'Piețe' : 'Markets'}>
          {markets.map((market) => (
            <button
              key={market.key}
              type="button"
              role="tab"
              aria-selected={market.key === activeMarket.key}
              onClick={() => changeMarket(market)}
              className={`whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold transition ${
                market.key === activeMarket.key
                  ? 'bg-slate-950 text-white'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {market.label}
            </button>
          ))}
        </div>

        <div className="mb-4 flex flex-wrap items-center gap-2 text-xs">
          <span className={`rounded-full px-2.5 py-1 font-semibold ${activeMarket.price_board_complete ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-800'}`}>
            {activeMarket.price_board_complete
              ? ro ? 'Panou de preț complet' : 'Complete verified board'
              : ro ? 'Panou de preț incomplet' : 'Incomplete verified board'}
          </span>
          {activeMarket.bookmaker_margin !== null && (
            <span className="rounded-full bg-slate-100 px-2.5 py-1 font-medium text-slate-600">
              {ro ? 'Marjă observată' : 'Observed margin'}: {pct(activeMarket.bookmaker_margin)}
            </span>
          )}
          {activeMarket.leader_agreement !== null && (
            <span className={`rounded-full px-2.5 py-1 font-semibold ${activeMarket.leader_agreement ? 'bg-blue-50 text-blue-700' : 'bg-violet-50 text-violet-700'}`}>
              {activeMarket.leader_agreement
                ? ro ? 'Modelul și piața au același lider' : 'Model and market share the same leader'
                : ro ? 'Modelul și piața au lideri diferiți' : 'Model and market have different leaders'}
            </span>
          )}
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-semibold">{ro ? 'Rezultat' : 'Outcome'}</th>
                <th className="px-4 py-3 font-semibold">{ro ? 'Model de predicție' : 'Prediction model'}</th>
                <th className="px-4 py-3 font-semibold">{ro ? 'Piață fără marjă' : 'Market view'}</th>
                <th className="px-4 py-3 font-semibold">{ro ? 'Preț verificat' : 'Verified price'}</th>
                <th className="px-4 py-3 font-semibold">{ro ? 'Acoperire' : 'Coverage'}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {activeMarket.outcomes.map((outcome) => (
                <OutcomeRow key={outcome.key} outcome={outcome} ro={ro} />
              ))}
            </tbody>
          </table>
        </div>

        {activeMarket.probability_kind === 'overlapping' && (
          <p className="mt-3 text-xs leading-relaxed text-slate-500">
            {ro
              ? 'Rezultatele Double Chance se suprapun; de aceea procentele de piață nu sunt normalizate ca o distribuție.'
              : 'Double Chance outcomes overlap, so their market prices are not normalised into a probability distribution.'}
          </p>
        )}
      </section>

      <AllMarketsBrowser
        catalogue={fixture.market_catalogue}
        ro={ro}
      />

      <FixtureContextTimelinePanel
        timeline={fixture.context_timeline}
        homeTeam={fixture.home_team}
        awayTeam={fixture.away_team}
        ro={ro}
      />

      <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-2xl border border-blue-200 bg-blue-50/60 p-5 md:p-7">
          <div className="flex items-start gap-3">
            <div className="rounded-xl bg-blue-600 p-2.5 text-white"><Calculator className="h-5 w-5" /></div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-blue-700">
                {ro ? 'PREȚUL TĂU' : 'YOUR PRICE'}
              </p>
              <h3 className="mt-1 text-xl font-bold text-slate-950">
                {ro ? 'Transformă opinia ta în cote corecte' : 'Turn your own view into fair odds'}
              </h3>
            </div>
          </div>

          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <label className="text-sm font-semibold text-slate-700">
              {ro ? 'Selecție' : 'Selection'}
              <select
                value={selectedOutcome?.key ?? ''}
                onChange={(event) => setSelectedOutcomeKey(event.target.value)}
                className="mt-2 min-h-[46px] w-full rounded-xl border border-slate-300 bg-white px-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              >
                {activeMarket.outcomes.map((outcome) => (
                  <option key={outcome.key} value={outcome.key}>{outcome.label}</option>
                ))}
              </select>
            </label>
            <label className="text-sm font-semibold text-slate-700">
              {ro ? 'Probabilitatea ta (%)' : 'Your probability (%)'}
              <input
                type="number"
                min="0.1"
                max="99.9"
                step="0.1"
                inputMode="decimal"
                value={personalProbability}
                onChange={(event) => setPersonalProbability(event.target.value)}
                placeholder="e.g. 54"
                className="mt-2 min-h-[46px] w-full rounded-xl border border-slate-300 bg-white px-3 text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
              />
            </label>
          </div>

          {personalPrice ? (
            <div className="mt-5 grid gap-3 sm:grid-cols-3">
              <CalculatorMetric label={ro ? 'Cota ta corectă' : 'Your fair odds'} value={decimal(personalPrice.personal_fair_odds)} />
              <CalculatorMetric label={ro ? 'Prag de rentabilitate' : 'Market break-even'} value={pct(personalPrice.break_even_probability)} />
              <CalculatorMetric
                label={ro ? 'Diferență față de prag' : 'Probability cushion'}
                value={personalPrice.probability_cushion === null ? '—' : `${personalPrice.probability_cushion >= 0 ? '+' : ''}${pct(personalPrice.probability_cushion)}`}
                tone={personalPrice.assessment === 'above_personal_price' ? 'positive' : 'neutral'}
              />
              <div className={`sm:col-span-3 rounded-xl border p-4 text-sm leading-relaxed ${personalPrice.assessment === 'above_personal_price' ? 'border-emerald-200 bg-emerald-50 text-emerald-900' : personalPrice.assessment === 'below_personal_price' ? 'border-slate-200 bg-white text-slate-700' : 'border-amber-200 bg-amber-50 text-amber-900'}`}>
                {personalPrice.assessment === 'above_personal_price'
                  ? ro
                    ? 'Conform probabilității introduse de tine, prețul verificat este peste cota ta minimă. Aceasta este concluzia ta, nu o estimare BetGlitch.'
                    : 'Using your probability, the verified price is above your minimum fair price. This is your conclusion, not a BetGlitch estimate.'
                  : personalPrice.assessment === 'below_personal_price'
                    ? ro
                      ? 'Conform probabilității introduse de tine, prețul verificat este sub cota ta minimă.'
                      : 'Using your probability, the verified price is below your minimum fair price.'
                    : ro ? 'Nu există un preț verificat pentru comparație.' : 'There is no verified price to compare.'}
              </div>
            </div>
          ) : (
            <p className="mt-4 text-sm text-slate-600">
              {ro
                ? 'Introdu o probabilitate între 0 și 100 pentru a calcula cota minimă acceptabilă.'
                : 'Enter a probability between 0 and 100 to calculate your minimum acceptable odds.'}
            </p>
          )}
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-5 md:p-7">
          <div className="flex items-center gap-2 text-amber-700">
            <AlertTriangle className="h-5 w-5" />
            <h3 className="font-bold text-slate-950">{ro ? 'Riscuri și necunoscute' : 'Risks and unknowns'}</h3>
          </div>
          <ul className="mt-4 space-y-3 text-sm leading-relaxed text-slate-600">
            {fixture.intelligence.data_quality.limitations.map((limitation) => (
              <li key={limitation} className="flex gap-2">
                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />
                <span>{limitationCopy(limitation, ro)}</span>
              </li>
            ))}
            <li className="flex gap-2">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />
              <span>{ro ? 'Acoperirea contextului diferă între competiții; valorile lipsă rămân marcate ca indisponibile.' : 'Context coverage varies by competition; missing values remain explicitly unavailable.'}</span>
            </li>
          </ul>

          <div className="mt-5 rounded-xl bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{ro ? 'Forma disponibilă' : 'Available form'}</p>
            <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="font-semibold text-slate-900">{fixture.home_team}</p>
                <p className="mt-1 text-slate-600">{formatFixtureForm(fixture.teams_data?.home?.form) ?? (ro ? 'Nu a fost furnizată' : 'Not supplied')}</p>
              </div>
              <div>
                <p className="font-semibold text-slate-900">{fixture.away_team}</p>
                <p className="mt-1 text-slate-600">{formatFixtureForm(fixture.teams_data?.away?.form) ?? (ro ? 'Nu a fost furnizată' : 'Not supplied')}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div className="flex flex-col gap-3 rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs leading-relaxed text-slate-500 sm:flex-row sm:items-center sm:justify-between">
        <p>
          {ro ? 'Analiză calculată' : 'Analysis computed'} {Number.isNaN(updated.getTime()) ? '—' : updated.toLocaleString(ro ? 'ro-RO' : 'en-GB')}.{' '}
          {ro ? 'Date informative, nu instrucțiuni de pariere.' : 'Informational evidence, not an instruction to bet.'}
        </p>
        {showFullPageLink && (
          <Link href={matchSlug} className="inline-flex min-h-[40px] items-center gap-1.5 font-semibold text-blue-700 hover:text-blue-900">
            {ro ? 'Deschide spațiul complet' : 'Open full workspace'} <ArrowRight className="h-4 w-4" />
          </Link>
        )}
      </div>
    </div>
  )
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-3 backdrop-blur-sm">
      <div className="flex items-center gap-1.5 text-xs text-slate-300">{icon}{label}</div>
      <div className="mt-1 text-lg font-bold text-white">{value}</div>
    </div>
  )
}

function OutcomeRow({ outcome, ro }: { outcome: IntelligenceOutcome; ro: boolean }) {
  const verified = canPublishPrice(outcome)
  return (
    <tr>
      <td className="px-4 py-4 font-semibold text-slate-950">{outcome.label}</td>
      <td className="px-4 py-4 text-slate-700">{pct(outcome.provider_probability)}</td>
      <td className="px-4 py-4 text-slate-700">{pct(outcome.market_probability)}</td>
      <td className="px-4 py-4">
        {verified ? (
          <div>
            <div className="font-bold text-slate-950">{outcome.odds?.toFixed(2)}</div>
            <div className="text-xs text-slate-500">{outcome.bookmaker ?? (ro ? 'Casă necunoscută' : 'Unknown bookmaker')}</div>
          </div>
        ) : <span className="text-slate-400">{ro ? 'Indisponibil' : 'Unavailable'}</span>}
      </td>
      <td className="px-4 py-4 text-xs text-slate-500">
        {verified ? (
          <>
            <div>{outcome.bookmaker_count ?? '—'} {ro ? 'case' : 'books'}</div>
            {outcome.price_min !== null && outcome.price_max !== null && (
              <div>{outcome.price_min.toFixed(2)}–{outcome.price_max.toFixed(2)}</div>
            )}
          </>
        ) : '—'}
      </td>
    </tr>
  )
}

function CalculatorMetric({
  label,
  value,
  tone = 'neutral',
}: {
  label: string
  value: string
  tone?: 'neutral' | 'positive'
}) {
  return (
    <div className="rounded-xl border border-blue-100 bg-white p-4">
      <p className="text-xs font-medium text-slate-500">{label}</p>
      <p className={`mt-1 text-xl font-bold ${tone === 'positive' ? 'text-emerald-700' : 'text-slate-950'}`}>{value}</p>
    </div>
  )
}
