'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { useSelectionPortfolio } from '../lib/selectionPortfolio'
import type { Lang } from '../lib/terminology'
import PortfolioCard from './PortfolioCard'

const REJECTIONS: Record<string, [string, string]> = {
  unsupported_market: ['Settlement not supported', 'Decontare indisponibilă'],
  stale_price: ['Price needs refreshing', 'Cota necesită actualizare'],
  kickoff_window: ['Outside the 1–72 hour window', 'În afara intervalului de 1–72 ore'],
  odds_range: ['Outside the price range', 'În afara intervalului de cote'],
  bookmaker_coverage: ['Too few bookmakers', 'Prea puțini operatori'],
  price_disagreement: ['Bookmaker prices disagree too much', 'Cotele operatorilor diferă prea mult'],
  incomplete_evidence: ['Incomplete model or price evidence', 'Dovezi incomplete despre model sau preț'],
  incomplete_probability_vector: ['Incomplete probabilities', 'Probabilități incomplete'],
  market_baseline_missing: ['Market comparison unavailable', 'Comparație cu piața indisponibilă'],
  model_edge_too_small: ['Model EV below the research threshold', 'EV model sub pragul de cercetare'],
  model_edge_outlier: ['Unusually large edge needs verification', 'Avantaj neobișnuit de mare, necesită verificare'],
  specialist_evidence: ['Specialist model evidence incomplete', 'Dovezi incomplete pentru modelul specializat'],
  fixture_unpredictable: ['Insufficient fixture reliability', 'Fiabilitate insuficientă pentru meci'],
  already_published_other_terms: ['A different selection is already recorded', 'O altă selecție este deja înregistrată'],
}

export default function MarketSelections({ language, strategySlug }: { language: Lang; strategySlug?: string }) {
  const { data, isLoading, error } = useSelectionPortfolio()
  const [chosen, setChosen] = useState('')
  const ro = language === 'ro'
  useEffect(() => { setChosen(new URLSearchParams(window.location.search).get('market') ?? '') }, [])
  const market = strategySlug ? data?.markets.find(m => m.strategy_url === `/strategies/${strategySlug}`)
    : data?.markets.find(m => m.key === chosen) ?? data?.markets.find(m => m.selections.length > 0) ?? data?.markets[0]
  return <section className="mt-8">
    <div className="flex flex-wrap items-end justify-between gap-4"><div><h2 className="text-2xl font-black text-slate-950">{ro ? 'Până la cinci selecții pentru fiecare piață' : 'Up to five selections per market'}</h2><p className="mt-2 max-w-3xl text-slate-600">{ro ? 'Ambele direcții și liniile disponibile concurează pentru fiecare loc. Fiecare selecție afișată are o cotă înregistrată și un rezultat urmărit.' : 'Both sides and available lines compete for each place. Every displayed selection has recorded odds and a tracked outcome.'}</p></div><Link href="/track-record" className="text-sm font-bold text-blue-700">{ro ? 'Vezi rezultatele →' : 'See results →'}</Link></div>
    {isLoading ? <p role="status" className="mt-6">{ro ? 'Încărcăm piețele…' : 'Loading markets…'}</p> : error || data?.status !== 'ready' ? <p role="status" className="mt-6 rounded-xl bg-amber-50 p-5">{ro ? 'Așteptăm o scanare actualizată.' : 'Waiting for a fresh scan.'}</p> : <>
      {!strategySlug && <div aria-label={ro ? 'Alege piața' : 'Choose market'} className="mt-6 flex flex-wrap gap-2">{data.markets.map(m => <button type="button" key={m.key} aria-pressed={market?.key === m.key} onClick={() => { setChosen(m.key); window.history.replaceState(null, '', `?market=${encodeURIComponent(m.key)}`) }} className={`rounded-full border px-4 py-2 text-sm font-semibold ${market?.key === m.key ? 'border-slate-950 bg-slate-950 text-white' : 'border-slate-200 bg-white text-slate-700'}`}>{m.name[language]} <span className="ml-1 opacity-70">{m.selections.length}</span></button>)}</div>}
      {market && <div className="mt-6"><div className="mb-4 flex flex-wrap justify-between gap-2"><h3 className="text-xl font-bold">{market.name[language]}</h3><Link href={market.strategy_url} className="text-sm text-blue-700 hover:underline">{ro ? 'Cum funcționează această piață →' : 'How this market works →'}</Link></div>{market.selections.length ? <div className="space-y-3">{market.selections.map((item, i) => <PortfolioCard key={item.selection_id} item={item} market={market} rank={i + 1} language={language} />)}</div> : <div className="rounded-xl border border-dashed border-slate-300 p-6"><p className="font-semibold">{ro ? 'Nicio selecție eligibilă în această piață acum.' : 'No qualifying selection in this market right now.'}</p><p className="mt-1 text-sm text-slate-600">{market.evaluated} {ro ? 'candidați evaluați. Locurile sunt ocupate numai când datele și cotele trec verificările.' : 'candidates evaluated. Places fill when the data and prices pass the checks.'}</p></div>}</div>}
      {!strategySlug && <details className="mt-8 rounded-xl border border-slate-200 bg-slate-50 p-5"><summary className="cursor-pointer font-bold">{ro ? 'Ce a verificat ultima scanare' : 'What the latest scan checked'}</summary><p className="mt-3 text-sm">{data.scan.fixtures_evaluated ?? 0} {ro ? 'meciuri' : 'fixtures'} · {data.scan.candidates_evaluated ?? 0} {ro ? 'candidați' : 'candidates'} · {data.scan.eligible_candidates ?? 0} {ro ? 'eligibili' : 'eligible'}</p><ul className="mt-3 space-y-1 text-sm text-slate-600">{Object.entries(data.scan.rejections ?? {}).map(([key, count]) => <li key={key}>{REJECTIONS[key]?.[ro ? 1 : 0] ?? (ro ? 'Alte verificări ale datelor' : 'Other data checks')}: {count}</li>)}</ul><p className="mt-4 text-sm text-slate-600">{ro ? 'Primul marcator, cornerele, cartonașele și pariurile pe jucători necesită modele sau date suplimentare de decontare. Nu sunt eligibile încă.' : 'First scorer, corners, cards and player props need additional models or settlement data. They are not eligible yet.'}</p></details>}
    </>}
  </section>
}
