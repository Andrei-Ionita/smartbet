'use client'

import Link from 'next/link'
import { ArrowRight, CheckCircle2, Clock3, FlaskConical, ShieldAlert } from 'lucide-react'
import type { Lang } from '../lib/terminology'
import type { StrategyDefinition } from '../lib/strategyLibrary'
import { useStrategyFits, type StrategyFit } from '../lib/useStrategyFits'

const COPY = {
  en: {
    eyebrow: 'Live strategy scan',
    title: 'Up to 5 current research fits',
    intro: 'These are the strongest upcoming fixtures that currently pass this strategy version’s registered price, freshness, data and value checks.',
    boundary: 'A research fit is not a published BetGlitch pick, is not counted in the verified record and can disappear if the price or evidence changes.',
    emptyTitle: 'No fixture passes every check right now',
    emptyBody: 'That is a valid result. BetGlitch will not fill five places with weaker fixtures just to make this page look busy.',
    unavailableTitle: 'The live scan is temporarily unavailable',
    unavailableBody: 'The strategy explanation and lab record remain available. We will not show stale candidates as if they were current.',
    loading: 'Checking current fixtures against the registered rules…',
    rank: 'Current fit',
    selection: 'Market and selection',
    price: 'Verified price',
    breakEven: 'Break-even',
    model: 'Model estimate',
    modelRange: 'Score-model range',
    fairOdds: 'Model fair odds',
    marketNoVig: 'Market view without margin',
    coverage: 'Score coverage',
    pointEstimateNote: 'The model estimate is raw output, not a calibrated probability.',
    boundedEstimateNote: 'The range reflects the enumerated score distribution; unmodelled score tails remain uncertainty.',
    books: (count: number) => `${count} bookmaker${count === 1 ? '' : 's'} checked`,
    captured: 'Price captured',
    why: 'Why it entered the list',
    rulePass: 'Passed every registered rule for this strategy version',
    freshPrice: 'Fresh, traceable price confirmed across bookmakers',
    exactSettlement: 'Exact line settlement evaluated across the score distribution',
    completeVectors: 'Complete model and market-price vectors were available',
    threshold: 'Cleared the strategy’s conservative value threshold',
    caveat: 'Experimental strategy',
    caveatBody: 'This strategy has not earned validated status. Treat the numbers as decision context, not a promise or instruction to bet.',
    inspect: 'Open full fixture analysis',
    more: (count: number) => `${count} other qualified ${count === 1 ? 'fixture is' : 'fixtures are'} omitted by the five-place limit.`,
  },
  ro: {
    eyebrow: 'Scanare live a strategiei',
    title: 'Până la 5 potriviri actuale pentru cercetare',
    intro: 'Acestea sunt cele mai solide meciuri viitoare care trec acum verificările înregistrate de preț, prospețime, date și valoare ale acestei versiuni.',
    boundary: 'O potrivire pentru cercetare nu este o selecție publicată BetGlitch, nu intră în istoricul verificat și poate dispărea dacă prețul sau dovezile se schimbă.',
    emptyTitle: 'Niciun meci nu trece acum toate verificările',
    emptyBody: 'Acesta este un rezultat valid. BetGlitch nu va umple cinci locuri cu meciuri mai slabe doar pentru ca pagina să pară ocupată.',
    unavailableTitle: 'Scanarea live este temporar indisponibilă',
    unavailableBody: 'Explicația strategiei și istoricul laboratorului rămân disponibile. Nu afișăm candidați vechi ca și cum ar fi actuali.',
    loading: 'Verificăm meciurile actuale folosind regulile înregistrate…',
    rank: 'Potrivire actuală',
    selection: 'Piață și selecție',
    price: 'Cotă verificată',
    breakEven: 'Prag de rentabilitate',
    model: 'Estimarea modelului',
    modelRange: 'Intervalul modelului de scor',
    fairOdds: 'Cota echitabilă a modelului',
    marketNoVig: 'Viziunea pieței fără marjă',
    coverage: 'Acoperirea scorurilor',
    pointEstimateNote: 'Estimarea este rezultatul brut al modelului, nu o probabilitate calibrată.',
    boundedEstimateNote: 'Intervalul reflectă distribuția scorurilor enumerate; scorurile din afara ei rămân o sursă de incertitudine.',
    books: (count: number) => `${count} ${count === 1 ? 'operator verificat' : 'operatori verificați'}`,
    captured: 'Cotă capturată',
    why: 'De ce a intrat în listă',
    rulePass: 'A trecut toate regulile înregistrate pentru această versiune',
    freshPrice: 'Cotă recentă și trasabilă, confirmată la mai mulți operatori',
    exactSettlement: 'Decontarea exactă a liniei a fost evaluată în distribuția scorurilor',
    completeVectors: 'Au fost disponibili vectorii compleți ai modelului și prețurilor',
    threshold: 'A depășit pragul conservator de valoare al strategiei',
    caveat: 'Strategie experimentală',
    caveatBody: 'Această strategie nu a obținut statutul validat. Folosește cifrele drept context pentru decizie, nu ca promisiune sau instrucțiune de pariere.',
    inspect: 'Deschide analiza completă',
    more: (count: number) => `Alte ${count} ${count === 1 ? 'meci calificat este omis' : 'meciuri calificate sunt omise'} din cauza limitei de cinci locuri.`,
  },
} as const

function slug(value: string) {
  return value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'fixture'
}

function fixtureHref(fit: StrategyFit) {
  const date = fit.kickoff.slice(0, 10)
  return `/prediction/${slug(fit.league || 'league')}/${slug(`${fit.home_team}-vs-${fit.away_team}`)}-${date}-${fit.fixture_id}`
}

function FitCard({ fit, language }: { fit: StrategyFit; language: Lang }) {
  const c = COPY[language]
  const probability = fit.probability
  const date = new Intl.DateTimeFormat(language === 'ro' ? 'ro-RO' : 'en-GB', {
    dateStyle: 'medium', timeStyle: 'short',
  }).format(new Date(fit.kickoff))
  const captured = new Intl.DateTimeFormat(language === 'ro' ? 'ro-RO' : 'en-GB', {
    dateStyle: 'medium', timeStyle: 'short',
  }).format(new Date(fit.price_captured_at))
  const specialist = probability.kind === 'bounded_score_distribution'

  return (
    <article className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 bg-slate-50 px-5 py-4 sm:px-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-black uppercase tracking-wider text-blue-700">{c.rank} #{fit.rank}</p>
            <h3 className="mt-1 text-lg font-black text-slate-950">{fit.home_team} <span className="font-medium text-slate-500">vs</span> {fit.away_team}</h3>
            <p className="mt-1 text-sm text-slate-600">{fit.league || '—'} · {date}</p>
          </div>
          <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-800">{c.rulePass}</span>
        </div>
      </div>

      <div className="p-5 sm:p-6">
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-xl bg-blue-50 p-3"><p className="text-xs font-bold uppercase tracking-wide text-blue-700">{c.selection}</p><p className="mt-1 font-black text-blue-950">{fit.selection}</p></div>
          <div className="rounded-xl bg-emerald-50 p-3"><p className="text-xs font-bold uppercase tracking-wide text-emerald-700">{c.price}</p><p className="mt-1 text-xl font-black text-emerald-950">{fit.odds.toFixed(2)}</p><p className="text-xs text-emerald-800">{fit.bookmaker} · {c.books(fit.bookmaker_count)}</p></div>
          <div className="rounded-xl bg-violet-50 p-3"><p className="text-xs font-bold uppercase tracking-wide text-violet-700">{specialist ? c.modelRange : c.model}</p><p className="mt-1 text-xl font-black text-violet-950">{specialist ? `${probability.model_probability_low_percent}%–${probability.model_probability_high_percent}%` : `${probability.model_probability_percent}%`}</p>{probability.model_fair_odds != null && <p className="text-xs text-violet-800">{c.fairOdds}: {probability.model_fair_odds.toFixed(2)}</p>}</div>
          <div className="rounded-xl bg-amber-50 p-3"><p className="text-xs font-bold uppercase tracking-wide text-amber-700">{c.breakEven}</p><p className="mt-1 text-xl font-black text-amber-950">{fit.break_even_probability_percent}%</p>{probability.market_no_vig_probability_percent != null && <p className="text-xs text-amber-800">{c.marketNoVig}: {probability.market_no_vig_probability_percent}%</p>}{probability.score_distribution_coverage_percent != null && <p className="text-xs text-amber-800">{c.coverage}: {probability.score_distribution_coverage_percent}%</p>}</div>
        </div>
        <p className="mt-3 text-xs leading-5 text-slate-500">{specialist ? c.boundedEstimateNote : c.pointEstimateNote}</p>

        <div className="mt-5 grid gap-5 lg:grid-cols-[1fr_auto] lg:items-end">
          <div>
            <h4 className="text-sm font-black text-slate-900">{c.why}</h4>
            <ul className="mt-2 grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
              <li className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />{c.freshPrice}</li>
              <li className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />{specialist ? c.exactSettlement : c.completeVectors}</li>
              <li className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />{c.threshold}</li>
              <li className="flex gap-2"><Clock3 className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />{c.captured}: {captured}</li>
            </ul>
          </div>
          <Link href={fixtureHref(fit)} className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-bold text-white hover:bg-slate-800">{c.inspect}<ArrowRight className="h-4 w-4" /></Link>
        </div>
      </div>
    </article>
  )
}

export default function StrategyCurrentFits({ strategy, language }: { strategy: StrategyDefinition; language: Lang }) {
  const c = COPY[language]
  const { report, loading, unavailable } = useStrategyFits(strategy.strategyKey)
  const omitted = Math.max(0, (report?.eligible_fixture_count ?? 0) - (report?.fits.length ?? 0))

  return (
    <section className="mt-8 rounded-3xl border border-slate-200 bg-slate-100/70 p-5 sm:p-8" aria-labelledby="current-strategy-fits">
      <div className="flex items-start gap-4">
        <FlaskConical className="mt-1 h-7 w-7 shrink-0 text-blue-700" />
        <div>
          <p className="text-xs font-black uppercase tracking-[0.16em] text-blue-700">{c.eyebrow}</p>
          <h2 id="current-strategy-fits" className="mt-1 text-2xl font-black text-slate-950">{c.title}</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">{c.intro}</p>
          <p className="mt-2 max-w-3xl text-sm font-semibold leading-6 text-slate-950">{c.boundary}</p>
        </div>
      </div>

      {loading && <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600" role="status">{c.loading}</div>}

      {!loading && unavailable && <div className="mt-6 flex gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-5"><ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-700" /><div><h3 className="font-black text-amber-950">{c.unavailableTitle}</h3><p className="mt-1 text-sm leading-6 text-amber-900">{c.unavailableBody}</p></div></div>}

      {!loading && !unavailable && report?.fits.length === 0 && <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-white p-7 text-center"><h3 className="font-black text-slate-950">{c.emptyTitle}</h3><p className="mx-auto mt-2 max-w-2xl text-sm leading-6 text-slate-600">{c.emptyBody}</p></div>}

      {!loading && !unavailable && report && report.fits.length > 0 && <div className="mt-6 space-y-4">{report.fits.map((fit) => <FitCard key={`${fit.fixture_id}:${fit.side}:${fit.line}`} fit={fit} language={language} />)}{omitted > 0 && <p className="text-center text-xs font-semibold text-slate-500">{c.more(omitted)}</p>}</div>}

      <div className="mt-6 flex gap-3 rounded-2xl border border-violet-200 bg-violet-50 p-4"><ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-violet-700" /><div><p className="text-sm font-black text-violet-950">{c.caveat}</p><p className="mt-1 text-sm leading-6 text-violet-900">{c.caveatBody}</p></div></div>
    </section>
  )
}
