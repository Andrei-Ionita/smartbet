'use client'

import { useEffect, useRef, useState } from 'react'
import { Calendar, Database, Lock, Search, Trophy, X } from 'lucide-react'
import FixtureDecisionWorkspace, {
  type FixtureDecisionFixture,
} from '../components/FixtureDecisionWorkspace'
import LoadingSpinner from '../components/LoadingSpinner'
import RetryButton from '../components/RetryButton'
import ErrorBoundary from '../components/ErrorBoundary'
import { useLanguage } from '../contexts/LanguageContext'
import { track } from '../lib/analytics'
import { EXPLORE_LEAGUE_OPTIONS, SEARCHABLE_COMPETITION_COUNT } from '../lib/coverage'

interface SearchResult {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
}

type SearchState = 'idle' | 'loading' | 'ok' | 'empty' | 'timeout' | 'provider_error'

export default function ExploreContent() {
  const { language } = useLanguage()
  const ro = language === 'ro'
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedLeague, setSelectedLeague] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searchState, setSearchState] = useState<SearchState>('idle')
  const [browseMode, setBrowseMode] = useState(true)
  const [selectedFixture, setSelectedFixture] = useState<FixtureDecisionFixture | null>(null)
  const [fixtureLoadedAt, setFixtureLoadedAt] = useState<string | null>(null)
  const [isLoadingFixture, setIsLoadingFixture] = useState(false)
  const [fixtureError, setFixtureError] = useState<string | null>(null)
  const [commitments, setCommitments] = useState<Map<number, { proofUrl: string }>>(new Map())
  const requestSeq = useRef(0)
  const inFlight = useRef<AbortController | null>(null)

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    fetch(`${apiUrl}/api/proof/claims/?limit=200`)
      .then((response) => response.ok ? response.json() : null)
      .then((data) => {
        if (!Array.isArray(data?.claims)) return
        const next = new Map<number, { proofUrl: string }>()
        for (const claim of data.claims) {
          if (!claim.superseded && typeof claim.fixture_id === 'number' && claim.proof_url) {
            next.set(claim.fixture_id, { proofUrl: claim.proof_url })
          }
        }
        setCommitments(next)
      })
      .catch(() => {})
  }, [])

  useEffect(() => () => inFlight.current?.abort(), [])

  useEffect(() => {
    if (!selectedFixture && !isLoadingFixture && !fixtureError) return
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && !isLoadingFixture) closeFixture()
    }
    window.addEventListener('keydown', closeOnEscape)
    return () => window.removeEventListener('keydown', closeOnEscape)
  }, [selectedFixture, isLoadingFixture, fixtureError]) // eslint-disable-line react-hooks/exhaustive-deps

  const runQuery = async (params: URLSearchParams, nextBrowseMode: boolean) => {
    inFlight.current?.abort()
    const controller = new AbortController()
    inFlight.current = controller
    const seq = ++requestSeq.current
    const isCurrent = () => seq === requestSeq.current

    setSearchState('loading')
    try {
      const response = await fetch(`/api/search?${params}`, { signal: controller.signal })
      const data = await response.json().catch(() => ({}))
      if (!isCurrent()) return
      if (!response.ok) {
        setSearchResults([])
        setSearchState(data?.status === 'timeout' || response.status === 504 ? 'timeout' : 'provider_error')
        return
      }
      const results = Array.isArray(data.results) ? data.results : []
      setSearchResults(results)
      setSearchState(results.length ? 'ok' : 'empty')
      if (!nextBrowseMode) {
        track('explore_search', { surface: 'explore', has_results: results.length > 0 })
      }
    } catch (error) {
      if ((error as Error)?.name === 'AbortError' || !isCurrent()) return
      setSearchResults([])
      setSearchState('provider_error')
    }
  }

  const performQuery = async () => {
    const hasQuery = Boolean(searchQuery.trim())
    const nextBrowseMode = !hasQuery
    setBrowseMode(nextBrowseMode)
    const params = new URLSearchParams({ limit: hasQuery ? '20' : '30' })
    if (hasQuery) params.set('q', searchQuery.trim())
    else params.set('mode', 'browse')
    if (selectedLeague) params.set('league', selectedLeague)
    await runQuery(params, nextBrowseMode)
  }

  useEffect(() => {
    const timeoutId = window.setTimeout(performQuery, 450)
    return () => window.clearTimeout(timeoutId)
  }, [searchQuery, selectedLeague]) // eslint-disable-line react-hooks/exhaustive-deps

  const openFixture = async (fixtureId: number) => {
    setFixtureError(null)
    setSelectedFixture(null)
    setIsLoadingFixture(true)
    try {
      const response = await fetch(`/api/fixture/${fixtureId}`)
      const data = await response.json().catch(() => ({}))
      if (!response.ok || !data.fixture?.intelligence) {
        throw new Error(data.error || `HTTP ${response.status}`)
      }
      setSelectedFixture(data.fixture)
      setFixtureLoadedAt(data.lastUpdated || data.fixture.intelligence.generated_at)
    } catch (error) {
      console.error('Fixture intelligence load failed:', error)
      setFixtureError(ro
        ? 'Spațiul de decizie pentru acest meci nu a putut fi încărcat. Încearcă din nou.'
        : 'This fixture decision workspace could not be loaded. Please try again.')
    } finally {
      setIsLoadingFixture(false)
    }
  }

  const closeFixture = () => {
    if (isLoadingFixture) return
    setSelectedFixture(null)
    setFixtureError(null)
  }

  const formatKickoff = (value: string) => new Date(value).toLocaleString(ro ? 'ro-RO' : 'en-GB', {
    weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  })

  const stateMessage = () => {
    if (searchState === 'timeout') return ro
      ? 'Furnizorul de meciuri nu a răspuns la timp.'
      : 'The fixture provider did not respond in time.'
    if (searchState === 'provider_error') return ro
      ? 'Căutarea meciurilor nu este disponibilă momentan.'
      : 'Fixture search is unavailable right now.'
    if (searchState === 'empty') return ro
      ? 'Nu există meciuri care corespund în următoarele 14 zile.'
      : 'No matching fixtures are scheduled in the next 14 days.'
    return ''
  }

  const modalOpen = isLoadingFixture || selectedFixture !== null || fixtureError !== null

  return (
    <ErrorBoundary>
      <main className="min-h-screen bg-[radial-gradient(circle_at_top,_#eff6ff,_#f8fafc_42%,_#f8fafc)]">
        <div className="mx-auto max-w-7xl px-4 py-10 md:px-6">
          <header className="mx-auto mb-10 max-w-4xl text-center">
            <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-950 text-white shadow-xl shadow-blue-900/10">
              <Database className="h-8 w-8" />
            </div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
              {ro ? 'INTELIGENȚĂ PENTRU ORICE MECI' : 'INTELLIGENCE FOR ANY FIXTURE'}
            </p>
            <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-950 md:text-5xl">
              {ro ? 'Explorează. Evaluează. Stabilește prețul tău.' : 'Explore. Evaluate. Set your own price.'}
            </h1>
            <p className="mx-auto mt-4 max-w-3xl text-base leading-relaxed text-slate-600 md:text-lg">
              {ro
                ? 'Caută orice meci acoperit și compară modelul furnizorului, piața fără marjă, cotele verificate și necunoscutele înainte să iei o decizie.'
                : 'Search any covered fixture and compare the provider model, margin-removed market view, verified prices and unknowns before making a decision.'}
            </p>
          </header>

          <section className="mb-8 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:p-7">
            <form onSubmit={(event) => { event.preventDefault(); performQuery() }} className="grid gap-4 md:grid-cols-[1fr_280px_auto]">
              <label className="relative">
                <span className="sr-only">{ro ? 'Caută echipă' : 'Search team'}</span>
                <Search className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
                <input
                  value={searchQuery}
                  onChange={(event) => setSearchQuery(event.target.value)}
                  placeholder={ro ? 'Caută o echipă, ligă sau țară' : 'Search a team, league or country'}
                  aria-label={ro ? 'Caută meciuri' : 'Search fixtures'}
                  className="min-h-[52px] w-full rounded-xl border border-slate-300 bg-white pl-12 pr-4 text-slate-950 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </label>
              <label>
                <span className="sr-only">{ro ? 'Filtrează după ligă' : 'Filter by league'}</span>
                <select
                  value={selectedLeague}
                  onChange={(event) => setSelectedLeague(event.target.value)}
                  aria-label={ro ? 'Filtrează după ligă' : 'Filter by league'}
                  className="min-h-[52px] w-full rounded-xl border border-slate-300 bg-white px-4 text-slate-950 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                >
                  {EXPLORE_LEAGUE_OPTIONS.map((league) => (
                    <option key={league.id} value={league.id}>{league.name}</option>
                  ))}
                </select>
              </label>
              <button type="submit" className="min-h-[52px] rounded-xl bg-blue-600 px-6 font-semibold text-white transition hover:bg-blue-700 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600">
                {ro ? 'Analizează' : 'Explore'}
              </button>
            </form>
            <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-600">
              <span className="rounded-full bg-slate-100 px-3 py-1.5">{SEARCHABLE_COMPETITION_COUNT} {ro ? 'competiții indexate' : 'indexed competitions'}</span>
              <span className="rounded-full bg-slate-100 px-3 py-1.5">{ro ? 'Următoarele 14 zile' : 'Next 14 days'}</span>
              <span className="rounded-full bg-blue-50 px-3 py-1.5 font-semibold text-blue-700">{ro ? 'Date complete la deschiderea meciului' : 'Full intelligence loads on demand'}</span>
            </div>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:p-7">
            <div className="mb-5 flex items-center justify-between gap-4">
              <div className="flex items-center gap-2">
                <Trophy className="h-5 w-5 text-blue-600" />
                <h2 className="text-xl font-bold text-slate-950">
                  {browseMode ? (ro ? 'Meciuri următoare' : 'Upcoming fixtures') : (ro ? 'Rezultatele căutării' : 'Search results')}
                </h2>
              </div>
              {searchState === 'ok' && <span className="text-sm text-slate-500">{searchResults.length} {ro ? 'meciuri' : 'fixtures'}</span>}
            </div>

            {searchState === 'loading' ? (
              <LoadingSpinner size="lg" text={ro ? 'Se încarcă meciurile…' : 'Loading fixtures…'} />
            ) : searchResults.length ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                {searchResults.map((fixture) => (
                  <button
                    key={fixture.fixture_id}
                    type="button"
                    onClick={() => openFixture(fixture.fixture_id)}
                    aria-label={`Open fixture intelligence for ${fixture.home_team} versus ${fixture.away_team}`}
                    className="group rounded-2xl border border-slate-200 bg-white p-5 text-left transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-lg focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
                  >
                    <div className="flex items-start justify-between gap-3 text-xs">
                      <span className="rounded-full bg-blue-50 px-2.5 py-1 font-semibold text-blue-700">{fixture.league}</span>
                      <span className="flex items-center gap-1 text-right text-slate-500"><Calendar className="h-3.5 w-3.5" />{formatKickoff(fixture.kickoff)}</span>
                    </div>
                    <div className="mt-6 space-y-2 text-lg font-bold text-slate-950">
                      <p>{fixture.home_team}</p>
                      <p>{fixture.away_team}</p>
                    </div>
                    {commitments.has(fixture.fixture_id) && (
                      <span className="mt-4 inline-flex items-center gap-1 rounded-full border border-indigo-200 bg-indigo-50 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wide text-indigo-800">
                        <Lock className="h-3 w-3" /> {ro ? 'Angajament public' : 'Public commitment'}
                      </span>
                    )}
                    <div className="mt-5 border-t border-slate-100 pt-4 text-sm font-semibold text-blue-700 group-hover:text-blue-900">
                      {ro ? 'Deschide spațiul de decizie →' : 'Open decision workspace →'}
                    </div>
                  </button>
                ))}
              </div>
            ) : searchState === 'empty' ? (
              <EmptyState title={ro ? 'Niciun meci găsit' : 'No fixtures found'} body={stateMessage()} />
            ) : searchState === 'timeout' || searchState === 'provider_error' ? (
              <div className="rounded-xl border border-amber-200 bg-amber-50 p-8 text-center">
                <h3 className="font-bold text-amber-950">{ro ? 'Căutarea nu a reușit' : 'Search could not complete'}</h3>
                <p className="mt-2 text-sm text-amber-800">{stateMessage()}</p>
                <div className="mt-4"><RetryButton onRetry={performQuery} /></div>
              </div>
            ) : null}
          </section>

          <section className="mt-8 grid gap-4 md:grid-cols-3">
            {[
              [ro ? '1. Găsește meciul' : '1. Find the fixture', ro ? 'Caută sau filtrează fără să încarci mii de cote pentru fiecare card.' : 'Search or filter without loading thousands of prices for every card.'],
              [ro ? '2. Compară perspectivele' : '2. Compare the views', ro ? 'Vezi separat probabilitățile furnizorului și piața fără marjă.' : 'See provider probabilities and the margin-removed market view separately.'],
              [ro ? '3. Stabilește prețul tău' : '3. Set your own price', ro ? 'Introdu propria probabilitate și calculează cota minimă pe care ai accepta-o.' : 'Enter your own probability and calculate the minimum odds you would accept.'],
            ].map(([title, body]) => (
              <div key={title} className="rounded-2xl border border-slate-200 bg-white p-5">
                <h3 className="font-bold text-slate-950">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{body}</p>
              </div>
            ))}
          </section>
        </div>

        {modalOpen && (
          <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-950/70 p-3 backdrop-blur-sm md:p-6" onClick={closeFixture}>
            <div role="dialog" aria-modal="true" aria-label="Fixture decision workspace" className="relative mx-auto min-h-[200px] max-w-6xl rounded-2xl bg-slate-50 p-4 shadow-2xl md:p-7" onClick={(event) => event.stopPropagation()}>
              <button type="button" onClick={closeFixture} disabled={isLoadingFixture} aria-label={ro ? 'Închide' : 'Close'} className="absolute right-3 top-3 z-10 flex h-11 w-11 items-center justify-center rounded-full bg-white text-slate-600 shadow-sm hover:bg-slate-100 disabled:opacity-40">
                <X className="h-5 w-5" />
              </button>
              {isLoadingFixture ? (
                <div className="py-20"><LoadingSpinner size="lg" text={ro ? 'Construim spațiul de decizie…' : 'Building the decision workspace…'} /></div>
              ) : fixtureError ? (
                <div role="alert" className="py-16 text-center">
                  <p className="font-semibold text-slate-950">{fixtureError}</p>
                  <button type="button" onClick={closeFixture} className="mt-5 min-h-[44px] rounded-xl border border-slate-300 bg-white px-5 font-semibold text-slate-700">{ro ? 'Închide' : 'Close'}</button>
                </div>
              ) : selectedFixture && (
                <FixtureDecisionWorkspace
                  fixture={selectedFixture}
                  lastUpdated={fixtureLoadedAt}
                  proofUrl={commitments.get(selectedFixture.fixture_id)?.proofUrl ?? null}
                  showFullPageLink
                />
              )}
            </div>
          </div>
        )}
      </main>
    </ErrorBoundary>
  )
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 p-10 text-center">
      <Search className="mx-auto h-10 w-10 text-slate-300" />
      <h3 className="mt-4 font-bold text-slate-950">{title}</h3>
      <p className="mt-2 text-sm text-slate-600">{body}</p>
    </div>
  )
}
