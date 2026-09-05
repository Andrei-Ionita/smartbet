'use client'

import Link from 'next/link'
import PortfolioCard from './PortfolioCard'
import { useSelectionPortfolio } from '../lib/selectionPortfolio'
import type { Lang } from '../lib/terminology'

export default function HomepageSelections({ language }: { language: Lang }) {
  const { data, error, isLoading } = useSelectionPortfolio()
  const ro = language === 'ro'
  return <section aria-labelledby="homepage-selections-heading" className="mt-12 sm:mt-16">
    <p className="text-xs font-black uppercase tracking-[0.18em] text-blue-700">{ro ? 'Selecțiile de astăzi' : 'Today’s selections'}</p>
    <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
      <h2 id="homepage-selections-heading" className="text-3xl font-black tracking-tight text-slate-950 sm:text-4xl">{ro ? 'Până la cinci meciuri. Din toate piețele.' : 'Up to five fixtures. Across every supported market.'}</h2>
      <Link href="/markets" className="font-bold text-blue-700 hover:underline">{ro ? 'Vezi selecțiile fiecărei piețe →' : 'Browse selections by market →'}</Link>
    </div>
    <p className="mt-3 max-w-3xl text-slate-600">{ro ? 'Aceleași selecții și cote înregistrate ca în paginile piețelor. Un singur meci pe rând, ordonat după estimarea conservatoare a randamentului.' : 'The same recorded selections and prices as the market pages. One fixture per row, ranked by the conservative return estimate.'}</p>
    {isLoading ? <p role="status" className="mt-6">{ro ? 'Încărcăm selecțiile…' : 'Loading selections…'}</p> : error || data?.status !== 'ready' ? <p role="status" className="mt-6 rounded-xl bg-amber-50 p-5 text-amber-950">{ro ? 'Selecțiile se actualizează. Revino după următoarea scanare.' : 'Selections are awaiting a fresh scan.'}</p> : data.homepage.length === 0 ? <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6"><p>{ro ? 'Niciun meci nu trece verificările actuale.' : 'No fixture passes the current checks.'}</p><Link className="mt-2 inline-block text-blue-700" href="/markets">{ro ? 'Vezi acoperirea și motivele →' : 'See coverage and reasons →'}</Link></div> : <div className="mt-6 space-y-3">{data.homepage.map((item, index) => <PortfolioCard key={item.selection_id} item={item} rank={index + 1} market={data.markets.find(m => m.key === item.market_type)} language={language} />)}</div>}
    {data?.status === 'ready' && <div className="mt-5 flex flex-wrap justify-between gap-3 rounded-xl bg-slate-100 px-4 py-3 text-sm text-slate-700"><span>{data.scan.fixtures_evaluated ?? 0} {ro ? 'meciuri evaluate' : 'fixtures evaluated'} · {data.scan.published_on_board ?? 0} {ro ? 'selecții în piețe' : 'market selections'}</span><Link className="font-bold text-blue-700" href="/track-record">{ro ? 'Urmărește rezultatele →' : 'Follow the results →'}</Link></div>}
  </section>
}
