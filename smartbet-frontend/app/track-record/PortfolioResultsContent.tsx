'use client'

import Link from 'next/link'
import { useState } from 'react'
import useSWR from 'swr'
import { useLanguage } from '../contexts/LanguageContext'
import { portfolioFetcher, portfolioFixtureHref, marketName, selectionName, type PortfolioSelection } from '../lib/selectionPortfolio'

interface Summary {
  key?: string; published: number; pending: number; settled: number; won: number; lost: number
  half_won: number; half_lost: number; push: number; profit_units: number
  roi_percent: number | null; average_odds: number | null
}
interface Report { overall: Summary; by_market: Summary[] }
interface Response { version: string; selections: PortfolioSelection[]; performance: Report; homepage_performance: Report }
const STATUS: Record<string, [string, string]> = { PENDING: ['Pending', 'În așteptare'], WON: ['Won', 'Câștigat'], LOST: ['Lost', 'Pierdut'], HALF_WON: ['Half won', 'Jumătate câștig'], HALF_LOST: ['Half lost', 'Jumătate pierdere'], PUSH: ['Stake returned', 'Miză returnată'], VOID: ['Void', 'Anulat'], CANCELLED: ['Cancelled', 'Anulat'] }

export default function PortfolioResultsContent() {
  const { language } = useLanguage()
  const ro = language === 'ro'
  const { data, error, isLoading } = useSWR<Response>('/api/selection-portfolio?view=results', portfolioFetcher)
  const [scope, setScope] = useState('all')
  const [market, setMarket] = useState('all')
  const [state, setState] = useState('all')
  const [limit, setLimit] = useState(30)
  const report = scope === 'homepage' ? data?.homepage_performance : data?.performance
  const summary = report?.overall
  const rows = (data?.selections ?? []).filter(row => (scope !== 'homepage' || row.homepage)
    && (market === 'all' || market === row.market_type) && (state === 'all' || (state === 'pending' ? row.status === 'PENDING' : row.status !== 'PENDING')))
  return <main className="mx-auto max-w-7xl px-4 py-10 sm:px-8">
    <h1 className="text-4xl font-black">{ro ? 'Selecții publicate. Rezultate urmărite.' : 'Published selections. Tracked outcomes.'}</h1>
    <p className="mt-3 max-w-3xl leading-7 text-slate-600">{ro ? 'Acest istoric începe cu noul motor pentru toate piețele. Selecțiile primei pagini sunt un subset al acelorași înregistrări. Fiecare pariu este numărat o singură dată în total.' : 'This record starts with the new market selection engine. Homepage selections are a subset of the same records. Each bet counts once in the overall total.'}</p>
    <p className="mt-2 text-sm text-slate-500">{ro ? 'Același meci poate avea selecții în piețe diferite; acestea sunt corelate. Versiunile anterioare nu intră în acest istoric.' : 'One fixture can have selections in different markets; these are correlated. Earlier engine versions are outside this record.'}</p>
    <div className="mt-6 flex flex-wrap gap-2">{[['all', ro ? 'Toate piețele' : 'All markets'], ['homepage', ro ? 'Prima pagină' : 'Homepage subset']].map(([key, label]) => <button key={key} onClick={() => { setScope(key); setLimit(30) }} aria-pressed={scope === key} className={`rounded-full border px-5 py-2 font-bold ${scope === key ? 'bg-slate-950 text-white' : 'bg-white text-slate-700'}`}>{label}</button>)}</div>
    {isLoading ? <p role="status" className="mt-6">{ro ? 'Încărcăm istoricul…' : 'Loading record…'}</p> : error ? <p role="alert" className="mt-6">{ro ? 'Istoricul este temporar indisponibil.' : 'The record is temporarily unavailable.'}</p> : summary && <>
      <dl className="mt-6 grid grid-cols-3 gap-3">{[[ro ? 'Publicate' : 'Published', summary.published], [ro ? 'În așteptare' : 'Pending', summary.pending], [ro ? 'Decontate' : 'Settled', summary.settled]].map(([label, value]) => <div key={String(label)} className="rounded-xl border border-slate-200 bg-white p-5"><dt className="text-sm text-slate-500">{label}</dt><dd className="mt-1 text-3xl font-black">{value}</dd></div>)}</dl>
      <p className="mt-4 rounded-xl bg-amber-50 p-4 text-sm text-amber-950">{summary.settled < 30 ? (ro ? `Primele rezultate: ${summary.settled} selecții decontate. Rezumatul performanței apare la 30; fiecare rezultat individual este vizibil mai jos.` : `Early record: ${summary.settled} settled selections. The performance summary opens at 30; every individual result is visible below.`) : (ro ? 'Eșantion în dezvoltare. 30 de rezultate nu demonstrează un avantaj; compară fiecare piață și urmărește evoluția.' : 'Developing sample. Thirty results do not establish an edge; compare each market and follow the record over time.')}</p>
      {summary.settled >= 30 && <div className="mt-4 flex flex-wrap gap-8 rounded-xl bg-slate-50 p-5"><p>ROI <strong>{summary.roi_percent?.toFixed(1) ?? '—'}%</strong></p><p>{ro ? 'Profit' : 'Profit'} <strong>{summary.profit_units > 0 ? '+' : ''}{summary.profit_units.toFixed(2)}u</strong></p><p>{ro ? 'Cotă medie' : 'Average odds'} <strong>{summary.average_odds?.toFixed(2) ?? '—'}</strong></p></div>}
      <p className="mt-3 text-xs text-slate-500">{ro ? 'O unitate mizată pe selecție. ROI = profit net / total mizat. Rambursările sunt decontate la 0u; anulările sunt excluse din miză. Cotele originale rămân fixe.' : 'One unit staked per selection. ROI = net profit / total stake. Pushes settle at 0u; voids and cancellations are excluded from stake. Original odds stay fixed.'}</p>
      <h2 className="mt-8 text-2xl font-black">{ro ? 'Rezultate pe piață' : 'Results by market'}</h2>
      <div className="mt-3 overflow-x-auto"><table className="w-full min-w-[650px] text-left text-sm"><thead><tr className="border-b text-slate-500"><th className="p-3">{ro ? 'Piață' : 'Market'}</th><th>{ro ? 'Decontate' : 'Settled'}</th><th>{ro ? 'Câștig / pierdere' : 'Won / lost'}</th><th>{ro ? 'Jumătăți / rambursări' : 'Halves / pushes'}</th><th>ROI</th><th>{ro ? 'Acuratețe*' : 'Accuracy*'}</th></tr></thead><tbody>{report?.by_market.map(m => <tr className="border-b" key={m.key}><td className="p-3 font-semibold">{marketName(m.key ?? '', language)}</td><td>{m.settled}</td><td>{m.won} / {m.lost}</td><td>{m.half_won} / {m.half_lost} / {m.push}</td><td>{m.settled >= 30 ? `${m.roi_percent?.toFixed(1)}%` : '—'}</td><td>{m.settled >= 30 && !m.half_won && !m.half_lost && !m.push && m.won + m.lost ? `${(100 * m.won / (m.won + m.lost)).toFixed(1)}%` : '—'}</td></tr>)}</tbody></table></div>
      <p className="mt-2 text-xs text-slate-500">{ro ? '*Rata câștigurilor integrale în piețe fără rambursări sau jumătăți. Eșantioanele sub 30 sunt încă în colectare.' : '*Full-win rate for markets without pushes or partial settlements. Samples below 30 are still collecting.'}</p>
      <div className="mt-8 flex flex-wrap gap-3"><select aria-label={ro ? 'Filtrează piața' : 'Filter market'} value={market} onChange={e => { setMarket(e.target.value); setLimit(30) }} className="rounded-xl border p-3"><option value="all">{ro ? 'Toate piețele' : 'All markets'}</option>{data?.performance.by_market.map(m => <option key={m.key} value={m.key}>{marketName(m.key ?? '', language)}</option>)}</select><select aria-label={ro ? 'Filtrează rezultatul' : 'Filter result'} value={state} onChange={e => { setState(e.target.value); setLimit(30) }} className="rounded-xl border p-3"><option value="all">{ro ? 'Toate rezultatele' : 'All results'}</option><option value="pending">{ro ? 'În așteptare' : 'Pending'}</option><option value="settled">{ro ? 'Încheiate' : 'Completed'}</option></select></div>
      <div className="mt-4 space-y-3">{rows.slice(0, limit).map(row => <article key={row.selection_id} className="flex flex-wrap items-center justify-between gap-4 rounded-xl border bg-white p-5"><div><Link className="font-bold text-slate-950 hover:underline" href={portfolioFixtureHref(row)}>{row.home_team} vs {row.away_team}</Link><p className="mt-1 text-sm text-slate-600">{marketName(row.market_type, language)} · {selectionName(row.predicted_outcome, row.market_type, language)} @ {row.odds.toFixed(2)}</p></div><div className="text-sm"><strong>{STATUS[row.status]?.[ro ? 1 : 0] ?? row.status}</strong><span className="ml-3">{row.unit_profit === null ? '—' : `${row.unit_profit > 0 ? '+' : ''}${row.unit_profit.toFixed(2)}u`}</span><Link href={row.receipt_url} className="ml-4 font-bold text-blue-700 hover:underline">{ro ? 'Dovadă →' : 'Receipt →'}</Link></div></article>)}</div>
      {!rows.length && <p className="mt-5 rounded-xl bg-slate-50 p-5">{ro ? 'Nicio selecție pentru aceste filtre încă.' : 'No selections match these filters yet.'}</p>}
      {rows.length > limit && <button onClick={() => setLimit(limit + 30)} className="mt-4 rounded-xl border px-5 py-3">{ro ? 'Arată mai multe' : 'Show more'}</button>}
    </>}
  </main>
}
