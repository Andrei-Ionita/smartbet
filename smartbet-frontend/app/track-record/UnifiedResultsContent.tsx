'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, Clock3, FlaskConical, Gem, Home, Info, Trophy } from 'lucide-react'

import { useLanguage } from '../contexts/LanguageContext'
import { STRATEGIES } from '../lib/strategyLibrary'

type Category = 'overview' | 'homepage' | 'strategy' | 'gems' | 'pending'
type ResultStatus = 'PENDING' | 'WON' | 'HALF_WON' | 'PUSH' | 'HALF_LOST' | 'LOST' | 'VOID' | 'CANCELLED'

interface SelectionRow {
  selection_id: string; category: 'homepage' | 'strategy'; source_key: string
  fixture_id: number; home_team: string; away_team: string; league: string
  kickoff: string; market_type: string; predicted_outcome: string; odds: number
  bookmaker: string | null; published_at: string; integrity_ok: boolean
  status: ResultStatus; unit_profit: number | null; actual_score_home: number | null
  actual_score_away: number | null; counts_towards_record: boolean
}

interface GemRow {
  claim_id: string; fixture_id: number; home_team: string; away_team: string
  league: string; kickoff: string; market_type: string; predicted_outcome: string
  odds: number; bookmaker: string | null; published_at: string
  claim_state: 'PENDING' | 'WON' | 'LOST' | 'VOID' | 'CANCELLED'
  integrity_ok: boolean; superseded: boolean; proof_url: string
  counts_towards_verified_record: boolean
  result: { actual_score_home: number | null; actual_score_away: number | null } | null
}

interface Row {
  id: string; category: 'homepage' | 'strategy' | 'gems'; sourceKey: string
  fixtureId: number; homeTeam: string; awayTeam: string; league: string
  kickoff: string; market: string; selection: string; odds: number
  bookmaker: string | null; publishedAt: string; status: ResultStatus
  unitProfit: number | null; homeScore: number | null; awayScore: number | null
  counted: boolean; detailUrl: string | null
}

const COPY = {
  en: {
    eyebrow: 'Results', title: 'Every selection. Every outcome.',
    intro: 'Homepage selections, named strategies and Hidden Gems each keep their own complete record. Nothing is blended into a more flattering denominator.',
    resetTitle: 'A clean record from 26 August 2026',
    resetBody: 'Tracking starts when the refactored public-selection ledger went live. Earlier fixtures and the old prediction archive are excluded because they were not recorded to the same reliable standard.',
    tabs: { overview: 'Overview', homepage: 'Homepage', strategy: 'Strategies', gems: 'Hidden Gems', pending: 'Pending' },
    overviewTitle: 'Three standards, three separate records',
    overviewBody: 'Compare each selection category on its own terms. Homepage and strategy selections measure usefulness; Gems retain the strictest qualification standard.',
    homepageTitle: 'Homepage selections', homepageBody: 'The rolling selections displayed on the homepage, frozen with their price before kickoff.',
    strategyTitle: 'Strategy selections', strategyBody: 'Up to five qualifying fixtures per named, versioned strategy. Experimental status remains visible.',
    gemsTitle: 'Hidden Gems', gemsBody: 'Only selections that passed every current Gem gate and entered the independently verifiable claim record.',
    pendingTitle: 'Published and awaiting a result', pendingBody: 'Pending selections remain visible until confirmed provider evidence can settle them.',
    published: 'Published', settled: 'Settled', record: 'Record', hitRate: 'Hit rate', returned: 'Flat-stake return', roi: 'ROI', averageOdds: 'Average odds',
    noRows: 'No selections have entered this record yet.', noPending: 'No published selection is waiting for settlement.',
    recordedOdds: 'Recorded odds', publishedAt: 'Published', proof: 'Open proof', fixture: 'Analyse fixture',
    policy: 'One $10 flat stake per settled selection. Voids and cancellations remain visible but do not enter ROI. Past performance does not guarantee future results.',
    early: (n: number) => `Only ${n} settled selections. This is too little evidence to claim an edge.`,
    recordRules: 'How this record works', methodology: 'Methodology', verification: 'Technical verification', unavailable: 'Results are temporarily unavailable.',
  },
  ro: {
    eyebrow: 'Rezultate', title: 'Fiecare selecție. Fiecare rezultat.',
    intro: 'Selecțiile de pe prima pagină, strategiile și Hidden Gems păstrează fiecare un istoric complet separat. Nimic nu este combinat într-un numitor mai favorabil.',
    resetTitle: 'Un istoric curat începând cu 26 august 2026',
    resetBody: 'Monitorizarea începe odată cu lansarea registrului refăcut pentru selecțiile publice. Meciurile anterioare și vechea arhivă de predicții sunt excluse deoarece nu au fost înregistrate după același standard riguros.',
    tabs: { overview: 'Prezentare', homepage: 'Prima pagină', strategy: 'Strategii', gems: 'Hidden Gems', pending: 'În așteptare' },
    overviewTitle: 'Trei standarde, trei istorice separate',
    overviewBody: 'Compară fiecare categorie în propriul context. Selecțiile de pe prima pagină și strategiile măsoară utilitatea; Gems păstrează standardul cel mai strict.',
    homepageTitle: 'Selecțiile de pe prima pagină', homepageBody: 'Selecțiile active afișate pe prima pagină, blocate împreună cu cota înainte de start.',
    strategyTitle: 'Selecțiile strategiilor', strategyBody: 'Până la cinci meciuri eligibile pentru fiecare strategie denumită și versionată. Statutul experimental rămâne vizibil.',
    gemsTitle: 'Hidden Gems', gemsBody: 'Doar selecțiile care au trecut toate filtrele Gem și au intrat în istoricul verificabil independent.',
    pendingTitle: 'Publicate și în așteptarea rezultatului', pendingBody: 'Selecțiile în așteptare rămân vizibile până când dovezile confirmate permit evaluarea.',
    published: 'Publicate', settled: 'Încheiate', record: 'Bilanț', hitRate: 'Rată de reușită', returned: 'Rezultat la miză fixă', roi: 'ROI', averageOdds: 'Cotă medie',
    noRows: 'Nicio selecție nu a intrat încă în acest istoric.', noPending: 'Nicio selecție publicată nu așteaptă evaluarea.',
    recordedOdds: 'Cotă înregistrată', publishedAt: 'Publicată', proof: 'Deschide dovada', fixture: 'Analizează meciul',
    policy: 'O miză fixă de 10 $ pentru fiecare selecție încheiată. Selecțiile void și anulate rămân vizibile, dar nu intră în ROI. Rezultatele anterioare nu garantează rezultate viitoare.',
    early: (n: number) => `Doar ${n} selecții încheiate. Sunt prea puține dovezi pentru a afirma existența unui avantaj.`,
    recordRules: 'Cum funcționează acest istoric', methodology: 'Metodologie', verification: 'Verificare tehnică', unavailable: 'Rezultatele sunt temporar indisponibile.',
  },
} as const

const getJson = async (url: string) => {
  const response = await fetch(url, { cache: 'no-store' })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(String(response.status))
  return body
}

function slug(value: string) {
  return value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'fixture'
}

function fixtureUrl(row: Row) {
  return `/prediction/${slug(row.league || 'league')}/${slug(`${row.homeTeam}-vs-${row.awayTeam}`)}-${row.kickoff.slice(0, 10)}-${row.fixtureId}`
}

function strategyLabel(key: string, language: 'en' | 'ro') {
  return STRATEGIES.find(item => item.strategyKey === key)?.copy[language].name ?? key.replace(/-/g, ' ')
}

function summarize(rows: Row[]) {
  const counted = rows.filter(row => row.counted)
  const wins = counted.filter(row => row.status === 'WON' || row.status === 'HALF_WON').length
  const losses = counted.filter(row => row.status === 'LOST' || row.status === 'HALF_LOST').length
  const pushes = counted.filter(row => row.status === 'PUSH').length
  const profit = counted.reduce((total, row) => total + (row.unitProfit ?? 0) * 10, 0)
  const decisive = wins + losses
  return {
    published: rows.length, settled: counted.length, wins, losses, pushes,
    profit: Math.round(profit * 100) / 100,
    roi: counted.length ? Math.round((profit / (counted.length * 10)) * 1000) / 10 : null,
    hitRate: decisive ? Math.round((wins / decisive) * 1000) / 10 : null,
    averageOdds: counted.length ? Math.round((counted.reduce((n, row) => n + row.odds, 0) / counted.length) * 100) / 100 : null,
  }
}

function statusText(status: ResultStatus, ro: boolean) {
  const en = { PENDING: 'Pending', WON: 'Won', HALF_WON: 'Half won', PUSH: 'Push', HALF_LOST: 'Half lost', LOST: 'Lost', VOID: 'Void', CANCELLED: 'Cancelled' }
  const romanian = { PENDING: 'În așteptare', WON: 'Câștigat', HALF_WON: 'Jumătate câștig', PUSH: 'Miză returnată', HALF_LOST: 'Jumătate pierdere', LOST: 'Pierdut', VOID: 'Void', CANCELLED: 'Anulat' }
  return (ro ? romanian : en)[status]
}

function statusStyle(status: ResultStatus) {
  if (status === 'WON' || status === 'HALF_WON') return 'bg-emerald-50 text-emerald-800'
  if (status === 'LOST' || status === 'HALF_LOST') return 'bg-red-50 text-red-800'
  if (status === 'PENDING') return 'bg-amber-50 text-amber-800'
  return 'bg-slate-100 text-slate-700'
}

function Metrics({ rows, language }: { rows: Row[]; language: 'en' | 'ro' }) {
  const c = COPY[language]
  const value = summarize(rows)
  const profit = `${value.profit > 0 ? '+' : value.profit < 0 ? '−' : ''}$${Math.abs(value.profit).toFixed(2)}`
  const metrics = [
    [c.published, value.published], [c.settled, value.settled],
    [c.record, `${value.wins}W–${value.losses}L${value.pushes ? `–${value.pushes}P` : ''}`],
    [c.hitRate, value.hitRate === null ? '—' : `${value.hitRate}%`],
    [c.averageOdds, value.averageOdds === null ? '—' : value.averageOdds.toFixed(2)],
    [c.returned, value.settled ? profit : '—'],
  ]
  return <><div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-6">{metrics.map(([label, metric]) => <div key={String(label)} className="rounded-xl border border-slate-200 bg-slate-50 p-4"><p className="text-[11px] font-bold uppercase tracking-wide text-slate-500">{label}</p><p className="mt-2 text-2xl font-black text-slate-950">{metric}</p></div>)}</div>{value.settled > 0 && <p className="mt-3 text-sm font-semibold text-slate-600">{c.roi}: {value.roi! > 0 ? '+' : ''}{value.roi}%</p>}{value.settled > 0 && value.settled < 30 && <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950">{c.early(value.settled)}</p>}</>
}

function ResultsList({ rows, language, empty }: { rows: Row[]; language: 'en' | 'ro'; empty: string }) {
  const c = COPY[language]
  const format = (value: string) => new Date(value).toLocaleString(language === 'ro' ? 'ro-RO' : 'en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  if (!rows.length) return <p className="mt-6 rounded-xl bg-slate-50 p-6 text-center text-slate-600">{empty}</p>
  return <ul className="mt-6 divide-y divide-slate-200">{rows.map(row => {
    const score = row.homeScore !== null && row.awayScore !== null ? `${row.homeScore}–${row.awayScore}` : null
    const source = row.category === 'homepage' ? c.tabs.homepage : row.category === 'gems' ? c.tabs.gems : strategyLabel(row.sourceKey, language)
    return <li key={row.id} className="py-5 first:pt-0 last:pb-0"><div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between"><div><div className="flex flex-wrap items-center gap-2"><span className={`rounded-full px-2.5 py-1 text-xs font-black ${statusStyle(row.status)}`}>{statusText(row.status, language === 'ro')}</span><span className="rounded-full bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-800">{source}</span></div><h3 className="mt-3 text-lg font-black text-slate-950">{row.homeTeam} <span className="font-medium text-slate-400">vs</span> {row.awayTeam}</h3><p className="mt-1 text-sm text-slate-600">{row.league} · {row.market} / <strong>{row.selection}</strong></p><div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-600"><span>{c.recordedOdds}: <strong>{row.odds.toFixed(2)}</strong>{row.bookmaker ? ` · ${row.bookmaker}` : ''}</span><span>{c.publishedAt}: {format(row.publishedAt)}</span>{score && <span className="font-black text-slate-950">{score}</span>}</div></div><div className="flex flex-wrap gap-2">{row.detailUrl && <Link href={row.detailUrl} className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-300 px-4 text-sm font-bold text-slate-800">{c.proof}<ArrowRight className="h-4 w-4" /></Link>}<Link href={fixtureUrl(row)} className="inline-flex min-h-11 items-center rounded-xl bg-slate-950 px-4 text-sm font-bold text-white">{c.fixture} →</Link></div></div></li>
  })}</ul>
}

export default function UnifiedResultsContent() {
  const { language } = useLanguage()
  const lang = language === 'ro' ? 'ro' : 'en'
  const c = COPY[lang]
  const [category, setCategory] = useState<Category>('overview')
  const [selections, setSelections] = useState<SelectionRow[] | null>(null)
  const [claims, setClaims] = useState<GemRow[] | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get('category') as Category | null
    if (requested && ['overview', 'homepage', 'strategy', 'gems', 'pending'].includes(requested)) setCategory(requested)
  }, [])
  useEffect(() => {
    Promise.all([getJson('/api/results-selections'), getJson('/api/published-claims')]).then(([a, b]) => {
      setSelections(Array.isArray(a.selections) ? a.selections : [])
      setClaims(Array.isArray(b.claims) ? b.claims : [])
    }).catch(() => setError(true))
  }, [])

  const rows = useMemo<Row[]>(() => {
    const selected = (selections ?? []).map(row => ({ id: row.selection_id, category: row.category, sourceKey: row.source_key, fixtureId: row.fixture_id, homeTeam: row.home_team, awayTeam: row.away_team, league: row.league, kickoff: row.kickoff, market: row.market_type, selection: row.predicted_outcome, odds: row.odds, bookmaker: row.bookmaker, publishedAt: row.published_at, status: row.status, unitProfit: row.unit_profit, homeScore: row.actual_score_home, awayScore: row.actual_score_away, counted: row.counts_towards_record, detailUrl: null } satisfies Row))
    const gems = (claims ?? []).filter(row => !row.superseded).map(row => ({ id: row.claim_id, category: 'gems' as const, sourceKey: 'gems', fixtureId: row.fixture_id, homeTeam: row.home_team, awayTeam: row.away_team, league: row.league, kickoff: row.kickoff, market: row.market_type, selection: row.predicted_outcome, odds: row.odds, bookmaker: row.bookmaker, publishedAt: row.published_at, status: row.claim_state as ResultStatus, unitProfit: row.claim_state === 'WON' ? row.odds - 1 : row.claim_state === 'LOST' ? -1 : row.claim_state === 'VOID' || row.claim_state === 'CANCELLED' ? 0 : null, homeScore: row.result?.actual_score_home ?? null, awayScore: row.result?.actual_score_away ?? null, counted: row.counts_towards_verified_record, detailUrl: row.proof_url } satisfies Row))
    return [...selected, ...gems].sort((a, b) => Date.parse(b.publishedAt) - Date.parse(a.publishedAt))
  }, [selections, claims])

  const sections = {
    homepage: { title: c.homepageTitle, body: c.homepageBody, rows: rows.filter(row => row.category === 'homepage') },
    strategy: { title: c.strategyTitle, body: c.strategyBody, rows: rows.filter(row => row.category === 'strategy') },
    gems: { title: c.gemsTitle, body: c.gemsBody, rows: rows.filter(row => row.category === 'gems') },
  }
  const active = category === 'homepage' || category === 'strategy' || category === 'gems' ? sections[category] : null
  const pending = rows.filter(row => row.status === 'PENDING')
  const tabs: Array<{ key: Category; icon: typeof Home }> = [{ key: 'overview', icon: Trophy }, { key: 'homepage', icon: Home }, { key: 'strategy', icon: FlaskConical }, { key: 'gems', icon: Gem }, { key: 'pending', icon: Clock3 }]

  return <div className="min-h-screen bg-slate-50"><header className="border-b border-slate-200 bg-white"><div className="mx-auto max-w-7xl px-4 py-10 sm:px-6"><p className="text-xs font-black uppercase tracking-[0.2em] text-blue-700">{c.eyebrow}</p><h1 className="mt-3 text-4xl font-black tracking-tight text-slate-950 sm:text-5xl">{c.title}</h1><p className="mt-4 max-w-3xl text-lg leading-8 text-slate-600">{c.intro}</p><div className="mt-6 max-w-3xl rounded-2xl border border-blue-200 bg-blue-50 px-5 py-4"><p className="font-black text-blue-950">{c.resetTitle}</p><p className="mt-1 text-sm leading-6 text-blue-900">{c.resetBody}</p></div></div></header><main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 sm:py-12"><nav aria-label={c.eyebrow} className="flex gap-2 overflow-x-auto rounded-2xl border border-slate-200 bg-white p-2">{tabs.map(tab => { const Icon = tab.icon; const on = category === tab.key; return <button key={tab.key} type="button" onClick={() => setCategory(tab.key)} className={`inline-flex min-h-11 shrink-0 items-center gap-2 rounded-xl px-4 text-sm font-black ${on ? 'bg-slate-950 text-white' : 'text-slate-600 hover:bg-slate-100'}`}><Icon className="h-4 w-4" />{c.tabs[tab.key]}</button> })}</nav>
    {error ? <div role="alert" className="mt-8 rounded-2xl border border-amber-200 bg-amber-50 p-6 text-amber-950">{c.unavailable}</div> : selections === null || claims === null ? <div role="status" className="mt-8 grid animate-pulse gap-4 md:grid-cols-3">{[1, 2, 3].map(n => <div key={n} className="h-52 rounded-2xl bg-slate-200" />)}</div> : category === 'overview' ? <section className="mt-8"><h2 className="text-2xl font-black text-slate-950">{c.overviewTitle}</h2><p className="mt-2 max-w-3xl text-slate-600">{c.overviewBody}</p><div className="mt-6 grid gap-5 lg:grid-cols-3">{(['homepage', 'strategy', 'gems'] as const).map(key => { const item = sections[key]; const value = summarize(item.rows); return <button key={key} type="button" onClick={() => setCategory(key)} className="rounded-2xl border border-slate-200 bg-white p-6 text-left shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md"><h3 className="text-xl font-black text-slate-950">{item.title}</h3><p className="mt-2 min-h-[3rem] text-sm leading-6 text-slate-600">{item.body}</p><dl className="mt-5 grid grid-cols-3 gap-2 text-sm"><div><dt className="text-slate-500">{c.published}</dt><dd className="mt-1 text-2xl font-black">{value.published}</dd></div><div><dt className="text-slate-500">{c.settled}</dt><dd className="mt-1 text-2xl font-black">{value.settled}</dd></div><div><dt className="text-slate-500">{c.roi}</dt><dd className="mt-1 text-2xl font-black">{value.roi === null ? '—' : `${value.roi > 0 ? '+' : ''}${value.roi}%`}</dd></div></dl><span className="mt-5 inline-flex items-center gap-2 font-bold text-blue-700">{c.tabs[key]} <ArrowRight className="h-4 w-4" /></span></button> })}</div></section> : category === 'pending' ? <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 sm:p-7"><h2 className="text-2xl font-black text-slate-950">{c.pendingTitle}</h2><p className="mt-2 max-w-3xl text-slate-600">{c.pendingBody}</p><ResultsList rows={pending} language={lang} empty={c.noPending} /></section> : active ? <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 sm:p-7"><h2 className="text-2xl font-black text-slate-950">{active.title}</h2><p className="mt-2 max-w-3xl text-slate-600">{active.body}</p><Metrics rows={active.rows} language={lang} /><ResultsList rows={active.rows} language={lang} empty={c.noRows} /></section> : null}
    <section className="mt-8 rounded-2xl border border-blue-100 bg-blue-50 p-5 sm:p-6"><div className="flex items-start gap-3"><Info className="mt-0.5 h-5 w-5 text-blue-700" /><div><h2 className="font-black text-blue-950">{c.recordRules}</h2><p className="mt-2 text-sm leading-6 text-blue-900">{c.policy}</p><div className="mt-3 flex flex-wrap gap-4 text-sm font-bold"><Link href="/methodology" className="text-blue-800 hover:underline">{c.methodology} →</Link><Link href="/proof/anchors" className="text-blue-800 hover:underline">{c.verification} →</Link></div></div></div></section></main></div>
}
