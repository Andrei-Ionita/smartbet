'use client'

import Link from 'next/link'
import { ArrowRight, CheckCircle2 } from 'lucide-react'
import { track } from '../lib/analytics'
import { formatPercent, portfolioFixtureHref, selectionName, type PortfolioMarket, type PortfolioSelection } from '../lib/selectionPortfolio'
import type { Lang } from '../lib/terminology'

export default function PortfolioCard({ item, market, rank, language }: {
  item: PortfolioSelection; market?: PortfolioMarket; rank: number; language: Lang
}) {
  const ro = language === 'ro'
  const e = item.evidence
  const time = (value: string) => new Date(value).toLocaleString(ro ? 'ro-RO' : 'en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
  const specialist = e.probability_method === 'score_distribution_stress'
  const metrics = [
    [ro ? 'Cotă actuală' : 'Current odds', item.current_odds.toFixed(2)],
    [ro ? 'Estimarea modelului' : 'Model estimate', formatPercent(e.model_probability)],
    [ro ? 'Piața fără marjă' : 'Market without margin', formatPercent(e.market_probability)],
    [ro ? 'EV model' : 'Model EV', formatPercent(e.model_ev, true)],
    [ro ? 'EV conservator' : 'Conservative EV', formatPercent(e.conservative_ev, true)],
  ]
  return <article className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
    <div className="flex items-start gap-4">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-950 text-sm font-black text-white">{rank}</span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap justify-between gap-2 text-xs">
          <span className="rounded-full bg-blue-50 px-3 py-1 font-bold text-blue-800">{market?.name[language] ?? item.market_type} · {e.evidence_label === 'price_edge' ? (ro ? 'Diferență de preț' : 'Price edge') : (ro ? 'În evaluare' : 'Under evaluation')}</span>
          <time className="text-slate-500" dateTime={item.kickoff}>{time(item.kickoff)}</time>
        </div>
        <div className="mt-3 flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
          <div><p className="text-xs text-slate-500">{item.league}</p><h3 className="text-xl font-black text-slate-950">{item.home_team} <span className="font-normal text-slate-400">vs</span> {item.away_team}</h3><p className="mt-1 font-bold text-blue-800">{selectionName(item.predicted_outcome, item.market_type, language)}</p></div>
          <div className="flex flex-wrap gap-3 text-sm font-bold">
            <Link onClick={() => track('fixture_opened', { surface: 'selection_board' })} href={portfolioFixtureHref(item)} className="inline-flex items-center gap-2 rounded-xl bg-slate-950 px-4 py-3 text-white">{ro ? 'Analizează meciul' : 'Analyse fixture'} <ArrowRight size={16} /></Link>
            {market && <Link href={market.strategy_url} className="self-center text-blue-700 hover:underline">{ro ? 'Înțelege strategia' : 'Understand strategy'}</Link>}
          </div>
        </div>
        <dl className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-3 xl:grid-cols-5">{metrics.map(([label, value]) => <div key={label} className="rounded-xl bg-slate-50 p-3"><dt className="text-xs text-slate-500">{label}</dt><dd className="mt-1 text-lg font-black text-slate-950">{value}</dd></div>)}</dl>
        <p className="mt-3 text-sm text-slate-700">{ro ? 'De ce apare: modelul estimează un randament pozitiv la cota verificată. Ordinea folosește estimarea conservatoare, acoperirea cotelor și ora de start.' : 'Why it appears: the model estimates a positive return at the checked price. Ranking uses the conservative estimate, price coverage and kickoff.'}</p>
        <p className="mt-2 text-xs text-slate-500">{item.current_bookmaker_count ?? item.bookmaker_count} {ro ? 'operatori verificați' : 'bookmakers checked'} · {ro ? 'Preț verificat' : 'Price checked'} {time(item.current_price_at)} · {ro ? 'Eșantion de calibrare' : 'Calibration sample'}: {specialist ? '—' : e.calibration_count}</p>
        <div className="mt-3 rounded-xl bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-950">
          {specialist
            ? (ro ? 'Liniile asiatice pot include rambursări și jumătăți de miză. EV-ul include aceste decontări; probabilitatea simplă de câștig nu este disponibilă. Testul conservator scade 10 puncte procentuale din EV-ul modelului.' : 'Asian lines can include refunds and split stakes. EV includes these settlements; a simple win probability is unavailable. The conservative stress test subtracts 10 percentage points from model EV.')
            : (ro ? 'EV-ul este o estimare, nu ROI realizat. O valoare conservatoare negativă înseamnă că avantajul nu rezistă încă incertitudinii.' : 'EV is an estimate of return. A negative conservative value means the apparent edge does not yet survive uncertainty.')}
          {' '}{e.context.lineups !== 'confirmed' ? (ro ? 'Echipele de start nu sunt confirmate în dovezile disponibile.' : 'Lineups are not confirmed in the available evidence.') : (ro ? 'Echipele de start sunt confirmate.' : 'Lineups are confirmed.')}
        </div>
        <details className="mt-3 text-xs text-slate-600"><summary className="cursor-pointer font-semibold">{ro ? 'Context și selecția înregistrată' : 'Context and recorded selection'}</summary>
          <p className="mt-2">{ro ? 'Formă recentă' : 'Recent form'}: {e.context.form_available ? `${e.context.home_form} / ${e.context.away_form}` : (ro ? 'indisponibilă' : 'unavailable')} · {ro ? 'Absențe raportate' : 'Reported absences'}: {e.context.absence_count ?? '—'}</p>
          <p className="mt-2">{ro ? 'Cotă înregistrată pentru Results' : 'Recorded odds for Results'}: {item.odds.toFixed(2)} · {time(item.published_at)}</p>
          <p>{ro ? 'Contextul explică riscurile; nu adăugăm bonusuri numerice pentru aceeași informație deja folosită de model.' : 'Context explains risks; information already used by the model receives no extra numerical bonus.'}</p>
        </details>
        <Link onClick={() => track('published_proof_opened', { surface: 'selection_board' })} href={item.receipt_url} className="mt-3 inline-flex items-center gap-2 text-xs font-bold text-emerald-800 hover:underline"><CheckCircle2 size={15} />{ro ? 'Selecție înregistrată înainte de start · verifică dovada' : 'Recorded before kickoff · inspect receipt'}</Link>
      </div>
    </div>
  </article>
}
