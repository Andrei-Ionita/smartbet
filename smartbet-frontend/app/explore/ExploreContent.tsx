'use client'

import { useEffect, useRef, useState } from 'react'
import { Search, Filter, Calendar, Trophy, TrendingUp, Lock } from 'lucide-react'
import RecommendationCard from '../components/RecommendationCard'
import LoadingSpinner from '../components/LoadingSpinner'
import { useLanguage } from '../contexts/LanguageContext'
import ErrorBoundary from '../components/ErrorBoundary'
import RetryButton from '../components/RetryButton'
import { StatusBadge } from '../components/StatusBadge'
import { getCopy } from '../lib/terminology'
import { track } from '../lib/analytics'
import { canPublishPrice, priceUnavailableLabel, type CanonicalPriceFields } from '../lib/marketPricing'
import { EXPLORE_LEAGUE_OPTIONS, SEARCHABLE_COMPETITION_COUNT } from '../lib/coverage'

interface SearchResult {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
}

interface FixtureAnalysis {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  predictions: {
    home: number
    draw: number
    away: number
  }
  predicted_outcome: 'home' | 'draw' | 'away'
  prediction_confidence: number
  odds_data?: {
    home: number | null
    draw: number | null
    away: number | null
    bookmaker: string
    home_bookmaker?: string | null
    draw_bookmaker?: string | null
    away_bookmaker?: string | null
  }
  ev_analysis: {
    home: number | null
    draw: number | null
    away: number | null
    best_bet: 'home' | 'draw' | 'away' | null
    best_ev: number | null
  }
  prediction_strength: string
  ensemble_info?: {
    model_count: number
    consensus: number
    variance: number
    strategy: string
  }
  debug_info?: {
    consensus?: string
    variance?: string | number
    confidence_score?: number
    prediction_agreement?: string
    model_consensus?: {
      home: number
      draw: number
      away: number
      variance: number
    }
  }
  prediction_info?: {
    source: string
    confidence_level: string
    reliability_score: number
    data_quality: string
  }
  market_indicators?: {
    market_favorite: string
    market_implied_prob: string
    bookmaker_margin: string
    volume_estimate: string
    ai_vs_market: string
    value_opportunity: string
    odds_efficiency: string
  }
  signal_quality?: 'Strong' | 'Good' | 'Moderate' | 'Weak'
  teams_data?: any // Relaxed type for Explore page to avoid full mock requirement
  // Multi-market support
  best_market?: CanonicalPriceFields & {
    type: '1x2' | 'btts' | 'over_under_2.5' | 'double_chance'
    name: string
    display_name?: string
    predicted_outcome: string
    probability: number
    probability_gap: number
    odds: number | null
    expected_value: number | null
    market_score: number
    bookmaker?: string
  }
  all_markets?: Array<CanonicalPriceFields & {
    type: '1x2' | 'btts' | 'over_under_2.5' | 'double_chance'
    name: string
    predicted_outcome: string
    probability: number
    odds: number | null
    expected_value: number | null
    market_score: number
    bookmaker?: string
    is_recommended?: boolean
  }>
}

/**
 * The filter options now come from app/lib/coverage.ts, which is the single
 * source of truth for every coverage number the product displays. This list
 * used to be defined here and counted inline as `LEAGUES.length - 1` = 30,
 * while /about hardcoded "27 leagues" — two numbers, one click apart.
 */
const LEAGUES = EXPLORE_LEAGUE_OPTIONS

/** Distinct outcomes a search can have. "empty" is not an error. */
type SearchState = 'idle' | 'loading' | 'ok' | 'empty' | 'timeout' | 'provider_error'

export default function ExploreContent() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedLeague, setSelectedLeague] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [selectedFixture, setSelectedFixture] = useState<FixtureAnalysis | null>(null)
  // When the open fixture's signal was computed. The engine computes on
  // request, so receipt time is the honest computation stamp.
  const [fixtureLoadedAt, setFixtureLoadedAt] = useState<string | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [searchState, setSearchState] = useState<SearchState>('idle')
  const [browseMode, setBrowseMode] = useState(false)

  // Fixtures that already carry a PUBLIC COMMITMENT, keyed by fixture id.
  //
  // One lookup against the sole claims authority (/api/proof/claims/), joined
  // by fixture_id — never a per-card request, never derived from the
  // prediction feed, and never a hardcoded fixture. A fixture can hold BOTH a
  // current live signal (mutable) and an earlier frozen commitment; this map
  // is what lets the UI state that plainly. Publication status and signal
  // quality are separate concepts: the badge is a factual marker, not a
  // quality tier, so uncommitted signals are not demoted by its absence.
  const [commitments, setCommitments] = useState<Map<number, { proofUrl: string }>>(new Map())

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    fetch(`${apiUrl}/api/proof/claims/?limit=200`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (!Array.isArray(data?.claims)) return
        const map = new Map<number, { proofUrl: string }>()
        for (const claim of data.claims) {
          if (claim.superseded) continue
          if (typeof claim.fixture_id === 'number' && claim.proof_url) {
            map.set(claim.fixture_id, { proofUrl: claim.proof_url })
          }
        }
        setCommitments(map)
      })
      // A failed lookup means no badges, never an error state: commitment
      // markers are additive context, not core signal data.
      .catch(() => {})
  }, [])

  // Request supersession.
  //
  // Typing "Barcelona" fires a request per debounce window. Without this, a slow
  // response for "Barc" could land after a fast one for "Barcelona" and replace
  // correct results with stale ones. Every request takes a sequence number; only
  // the newest may write state, and superseded requests are aborted outright so
  // they stop consuming a connection.
  const requestSeq = useRef(0)
  const inFlight = useRef<AbortController | null>(null)

  // Debounced search or browse
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchQuery.trim()) {
        // Search mode: user typed a query
        setBrowseMode(false)
        performSearch()
      } else {
        // Browse mode. With no league selected this shows what is on soonest
        // across every covered competition, rather than the empty panel that
        // used to make the product look like it had no content until the
        // visitor guessed a team name.
        setBrowseMode(true)
        performBrowse()
      }
    }, 500)

    return () => clearTimeout(timeoutId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery, selectedLeague])

  // Abort whatever is open when the page unmounts.
  useEffect(() => () => inFlight.current?.abort(), [])

  const runQuery = async (params: URLSearchParams, isBrowse: boolean) => {
    inFlight.current?.abort()
    const controller = new AbortController()
    inFlight.current = controller

    const seq = ++requestSeq.current
    const isCurrent = () => seq === requestSeq.current

    setIsSearching(true)
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

      const results = data.results || []
      setSearchResults(results)
      setSearchState(results.length > 0 ? 'ok' : 'empty')

      if (!isBrowse) {
        // Whether a search found anything — never what was searched for.
        track('explore_search', { surface: 'explore', has_results: results.length > 0 })
      }
    } catch (error) {
      // An aborted request was superseded on purpose; it is not a failure.
      if ((error as Error)?.name === 'AbortError' || !isCurrent()) return
      setSearchResults([])
      setSearchState('provider_error')
    } finally {
      if (isCurrent()) setIsSearching(false)
    }
  }

  const performSearch = async () => {
    if (!searchQuery.trim()) return
    const params = new URLSearchParams({ q: searchQuery, limit: '20' })
    if (selectedLeague) params.append('league', selectedLeague)
    await runQuery(params, false)
  }

  const performBrowse = async () => {
    const params = new URLSearchParams({ limit: '30', mode: 'browse' })
    if (selectedLeague) params.append('league', selectedLeague)
    await runQuery(params, true)
  }

  const handleRetrySearch = () => {
    browseMode ? performBrowse() : performSearch()
  }

  /** One bilingual line per distinct outcome. */
  const searchStateMessage = (): string => {
    const ro = language === 'ro'
    switch (searchState) {
      case 'empty':
        return browseMode
          ? selectedLeague
            ? ro ? 'Niciun meci programat în această competiție în următoarele 14 zile.'
              : 'No fixtures scheduled in this competition in the next 14 days.'
            : ro ? 'Niciun meci programat în următoarele 14 zile.'
              : 'No fixtures scheduled in the next 14 days.'
          : ro ? `Niciun meci găsit pentru „${searchQuery}” în următoarele 14 zile.`
            : `No fixtures found for “${searchQuery}” in the next 14 days.`
      case 'timeout':
        return ro
          ? 'Furnizorul de meciuri nu a răspuns la timp. Încearcă din nou.'
          : 'The fixture provider did not respond in time. Please try again.'
      case 'provider_error':
        return ro
          ? 'Căutarea meciurilor nu este disponibilă momentan. Niciun pontaj publicat nu este afectat.'
          : 'Fixture search is unavailable right now. No public commitment is affected.'
      case 'ok':
        return ro
          ? `${searchResults.length} meciuri afișate`
          : `${searchResults.length} fixtures shown`
      default:
        return ''
    }
  }

  const [isLoadingFixture, setIsLoadingFixture] = useState(false)
  const [fixtureError, setFixtureError] = useState<string | null>(null)

  const handleFixtureSelect = async (fixtureId: number) => {
    setFixtureError(null)
    setIsLoadingFixture(true)
    try {
      // Use Next.js API (fetches from SportMonks - can get ANY fixture)
      const response = await fetch(`/api/fixture/${fixtureId}`)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()

      // Next.js API returns in 'fixture' field
      if (data.fixture) {
        console.log('Fixture loaded successfully:', data.fixture.fixture_id)
        setSelectedFixture(data.fixture)
        setFixtureLoadedAt(new Date().toISOString())
      } else {
        console.error('No fixture data in response', data)
      }
    } catch (error) {
      // A blocking browser dialog was used here: it froze the whole tab until
      // dismissed and echoed the raw error. Surface it inline instead.
      console.error('Error fetching fixture:', error)
      setFixtureError('This fixture could not be loaded. Please try again.')
    } finally {
      setIsLoadingFixture(false)
    }
  }

  const formatKickoff = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString(language === 'ro' ? 'ro-RO' : 'en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    })
  }

  const handleViewDetails = (fixtureId: number) => {
    handleFixtureSelect(fixtureId)
  }

  const { t, language } = useLanguage()
  // Bilingual product vocabulary. The modal previously rendered the English
  // exports regardless of the active language, so a Romanian visitor met an
  // English definition of the very concept the badge above it was naming.
  const copy = getCopy(language)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    performSearch()
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="max-w-6xl mx-auto px-4 py-8">

        {/* Header */}
        <div className="text-center mb-12">
          <div className="relative inline-block mb-6">
            <div className="absolute -inset-4 bg-gradient-to-r from-primary-500 to-blue-600 rounded-full blur opacity-20"></div>
            <div className="relative bg-white p-6 rounded-full shadow-xl">
              <Search className="h-16 w-16 text-primary-600" />
            </div>
          </div>

          <div className="mb-3 flex justify-center">
            <StatusBadge status="live" size="sm" lang={language} />
          </div>
          <h1 className="mb-4 text-3xl font-bold text-gray-900 md:text-4xl">
            {t('explore.title')}
          </h1>
          <p className="mx-auto max-w-3xl text-base leading-relaxed text-gray-600 sm:text-lg">
            {t('explore.subtitle')}
          </p>
        </div>

        {/* Search Interface */}
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 shadow-lg border border-white/20 mb-8">
          <div className="space-y-4">
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  aria-label={t('explore.search.placeholder')}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={t('explore.search.placeholder')}
                  className="w-full pl-12 pr-4 py-4 rounded-xl border border-gray-200 focus:ring-2 focus:ring-primary-500 focus:border-transparent text-lg shadow-sm transition-all"
                />
              </div>
              <div className="relative min-w-[200px]">
                <Filter className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <select
                  aria-label="Filter by league"
                  value={selectedLeague}
                  onChange={(e) => setSelectedLeague(e.target.value)}
                  className="w-full pl-12 pr-10 py-4 rounded-xl border border-gray-200 focus:ring-2 focus:ring-primary-500 focus:border-transparent text-lg shadow-sm appearance-none bg-white transition-all cursor-pointer"
                >
                  {LEAGUES.map(league => (
                    <option key={league.id} value={league.id}>
                      {league.id === '' ? t('explore.search.allLeagues') : league.name}
                    </option>
                  ))}
                </select>
                <div className="absolute right-4 top-1/2 transform -translate-y-1/2 pointer-events-none">
                  <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
              {/* Loading indicator when searching/browsing */}
              {isSearching && (
                <div className="flex items-center justify-center px-4">
                  <LoadingSpinner size="sm" />
                </div>
              )}
            </div>
          </div>

          {/* What the search covers.
              These used to advertise "Real-time odds" and "AI predictions" on
              the search panel, which described the old behaviour of pulling both
              for every fixture in every league. The search returns fixtures; the
              model signal and its recorded price appear when one is opened. */}
          <div className="flex flex-wrap items-center justify-center gap-4 mt-6 text-sm text-gray-500">
            <span className="flex items-center gap-1.5 px-3 py-1 bg-gray-100 rounded-full">
              <Trophy className="h-3.5 w-3.5" />
              {language === 'ro'
                ? `${SEARCHABLE_COMPETITION_COUNT} competiții europene indexate`
                : `${SEARCHABLE_COMPETITION_COUNT} indexed European competitions`}
            </span>
            <span className="flex items-center gap-1.5 px-3 py-1 bg-gray-100 rounded-full">
              <Calendar className="h-3.5 w-3.5" />
              {language === 'ro' ? 'Următoarele 14 zile' : 'Next 14 days'}
            </span>
            <span className="flex items-center gap-1.5 px-3 py-1 bg-blue-50 text-blue-700 rounded-full font-medium">
              <TrendingUp className="h-3.5 w-3.5" />
              {language === 'ro'
                ? 'Deschide un meci pentru semnal și preț'
                : 'Open a fixture for its signal and price'}
            </span>
          </div>
        </div>
        {/* Search Results or Browse Results */}
        {(searchQuery || browseMode) && (
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-lg border border-white/20 mb-8">
            <div className="flex items-center gap-2 mb-4">
              <Trophy className="h-5 w-5 text-primary-600" />
              <h2 className="text-xl font-bold text-gray-900">
                {browseMode ? t('explore.browse.title') : t('explore.results')}
              </h2>
            </div>

            {isSearching ? (
              <LoadingSpinner size="lg" text={t('explore.search.loading')} />

            ) : searchResults.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-in fade-in duration-500">
                {searchResults.map((fixture) => (
                  // A div with an onClick is mouse-only: not focusable, not
                  // reachable by keyboard, and announced as plain text. This is
                  // the primary "inspect a signal" action, so it needs to be a
                  // real control.
                  <div
                    key={fixture.fixture_id}
                    onClick={() => handleFixtureSelect(fixture.fixture_id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        handleFixtureSelect(fixture.fixture_id)
                      }
                    }}
                    role="button"
                    tabIndex={0}
                    aria-label={`Open live signal for ${fixture.home_team} versus ${fixture.away_team}`}
                    className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md hover:border-primary-100 transition-all cursor-pointer group focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary-600"
                  >
                    <div className="flex justify-between items-start mb-4">
                      <div className="text-xs font-semibold text-primary-600 px-2 py-1 bg-primary-50 rounded-lg">
                        {fixture.league}
                      </div>
                      <div className="flex items-center text-xs text-gray-500">
                        <Calendar className="w-3 h-3 mr-1" />
                        {formatKickoff(fixture.kickoff)}
                      </div>
                    </div>

                    <div className="flex items-center justify-between gap-4 mb-4">
                      <div className="text-right flex-1">
                        <span className="font-bold text-gray-900 group-hover:text-primary-700 transition-colors">
                          {fixture.home_team}
                        </span>
                      </div>
                      <div className="px-2 text-gray-400 font-light text-sm">vs</div>
                      <div className="text-left flex-1">
                        <span className="font-bold text-gray-900 group-hover:text-primary-700 transition-colors">
                          {fixture.away_team}
                        </span>
                      </div>
                    </div>

                    {/* Factual commitment marker. Rendered ONLY when this
                        fixture has a frozen PublishedClaim — a state marker,
                        not a quality tier. */}
                    {commitments.has(fixture.fixture_id) && (
                      <div className="mb-3 flex flex-wrap items-center gap-2">
                        <span className="inline-flex items-center gap-1 rounded-md border-2 border-solid border-indigo-500 bg-indigo-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-indigo-900">
                          <Lock className="h-3 w-3" aria-hidden />
                          {language === 'ro' ? 'ANGAJAMENT PUBLIC' : 'PUBLIC COMMITMENT'}
                        </span>
                        <a
                          href={commitments.get(fixture.fixture_id)!.proofUrl}
                          onClick={(e) => e.stopPropagation()}
                          className="text-xs font-semibold text-indigo-700 underline-offset-2 hover:underline"
                        >
                          {language === 'ro' ? 'Vezi dovada' : 'View proof'}
                        </a>
                      </div>
                    )}

                    {/* No prediction or odds badges here.
                        Producing them meant pulling `predictions;odds` for every
                        fixture in every league — a fixture carries 900-2700 odds
                        entries — to render two dots. The model signal and its
                        canonical price load when the fixture is opened. */}
                    <div className="flex items-center justify-center pt-4 border-t border-gray-50">
                      <span className="text-xs font-medium text-primary-600">
                        {language === 'ro' ? 'Deschide semnalul live' : 'Open live signal'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : searchState === 'empty' ? (
              <div className="text-center py-12 bg-white rounded-2xl border border-gray-100 shadow-sm">
                <div className="text-5xl mb-4">🔍</div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('explore.search.noResults')}</h3>
                <p className="text-gray-500 max-w-sm mx-auto">{searchStateMessage()}</p>
              </div>
            ) : searchState === 'timeout' || searchState === 'provider_error' ? (
              // A provider failure is a different fact from "nothing matched",
              // and only one of the two is worth retrying.
              <div className="text-center py-12 bg-white rounded-2xl border border-amber-200 shadow-sm">
                <div className="text-5xl mb-4">⚠️</div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  {language === 'ro' ? 'Căutarea nu a reușit' : 'Search could not complete'}
                </h3>
                <p className="mx-auto mb-4 max-w-sm text-gray-500">{searchStateMessage()}</p>
                <RetryButton onRetry={handleRetrySearch} />
              </div>
            ) : (
              <div className="text-center py-20 opacity-50">
                <Search className="h-12 w-12 mx-auto text-gray-300 mb-4" />
                <p className="text-gray-500 font-medium">{t('explore.search.initialState')}</p>
              </div>
            )}
          </div>
        )}

        {/* Fixture Analysis Modal */}
        {(isLoadingFixture || selectedFixture || fixtureError) && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-300"
            onClick={() => {
              if (!isLoadingFixture) {
                setSelectedFixture(null);
                // clear any loading state if stuck
                setIsLoadingFixture(false);
              }
            }}
          >
            <div
              role="dialog"
              aria-modal="true"
              aria-label="Live signal detail"
              className="bg-white rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-2xl relative animate-in fade-in zoom-in-95 duration-300"
              onClick={e => e.stopPropagation()}
            >
              {/* Close Button */}
              <button
                onClick={() => setSelectedFixture(null)}
                aria-label="Close signal detail"
                className="absolute top-4 right-4 min-h-[44px] min-w-[44px] flex items-center justify-center bg-gray-100 hover:bg-gray-200 rounded-full transition-colors z-10"
                disabled={isLoadingFixture}
              >
                <svg className="w-6 h-6 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>

              <div className="p-6 md:p-8">
                {isLoadingFixture ? (
                  <div className="flex flex-col items-center justify-center py-12">
                    <LoadingSpinner size="lg" text={t('explore.analysis.loading')} />
                  </div>
                ) : fixtureError ? (
                  <div role="alert" className="py-10 text-center">
                    <p className="text-base font-semibold text-gray-900">{fixtureError}</p>
                    <button
                      onClick={() => setSelectedFixture(null)}
                      className="mt-4 min-h-[44px] rounded-lg border border-gray-300 px-4 text-sm font-medium text-gray-700 hover:bg-gray-50"
                    >
                      Close
                    </button>
                  </div>
                ) : selectedFixture && (
                  <>
                    <div className="flex items-center gap-3 mb-6 pr-8">
                      <div className="p-2 bg-primary-50 rounded-lg">
                        <Calendar className="h-6 w-6 text-primary-600" />
                      </div>
                      <div>
                        <h2 className="text-xl md:text-2xl font-bold text-gray-900 leading-tight">{t('explore.analysis.title')}</h2>
                        <p className="text-sm text-gray-500">{selectedFixture.home_team} vs {selectedFixture.away_team}</p>
                      </div>
                    </div>

                    {/* This modal is the surface where a visitor actually reads
                        a signal, and it previously carried no indication that
                        the numbers are mutable or outside the verified record.
                        Everything below is a live signal until BetGlitch
                        publishes it as an immutable claim. */}
                    <div className="mb-6 rounded-xl border border-sky-200 bg-sky-50 p-4">
                      <StatusBadge status="live" size="sm" lang={language} />
                      <p className="mt-2 text-sm leading-relaxed text-gray-700">
                        {copy.terms.liveSignal.mutability}{' '}
                        {copy.terms.liveSignal.notInRecord}
                      </p>
                      <p className="mt-2 text-sm leading-relaxed text-gray-700">
                        {copy.modelScoreNote}
                      </p>
                    </div>

                    {/* This fixture ALSO holds a frozen public commitment. Two
                        objects, stated as such: the live analysis above may
                        keep changing; the commitment below cannot. */}
                    {selectedFixture && commitments.has(selectedFixture.fixture_id) && (
                      <div className="mb-6 rounded-xl border-2 border-solid border-indigo-300 bg-indigo-50 p-4">
                        <span className="inline-flex items-center gap-1 rounded-md border-2 border-solid border-indigo-500 bg-white px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-indigo-900">
                          <Lock className="h-3 w-3" aria-hidden />
                          {language === 'ro' ? 'ANGAJAMENT PUBLIC' : 'PUBLIC COMMITMENT'}
                        </span>
                        <p className="mt-2 text-sm leading-relaxed text-gray-700">
                          {language === 'ro'
                            ? 'Semnalul live poate continua să se schimbe. Angajamentul public păstrează starea la care BetGlitch s-a angajat înainte de start.'
                            : 'The live signal may continue to change. The public commitment preserves the state BetGlitch committed to before kickoff.'}
                        </p>
                        <a
                          href={commitments.get(selectedFixture.fixture_id)!.proofUrl}
                          className="mt-2 inline-flex min-h-[44px] items-center text-sm font-semibold text-indigo-700 underline-offset-2 hover:underline"
                        >
                          {language === 'ro' ? 'Vezi dovada' : 'View proof'} →
                        </a>
                      </div>
                    )}

                    <RecommendationCard
                      lastUpdated={fixtureLoadedAt}
                      recommendation={{
                        fixture_id: selectedFixture.fixture_id,
                        home_team: selectedFixture.home_team,
                        away_team: selectedFixture.away_team,
                        league: selectedFixture.league,
                        kickoff: selectedFixture.kickoff,
                        predicted_outcome: (selectedFixture.best_market?.predicted_outcome ||
                          (selectedFixture.predicted_outcome ?
                            selectedFixture.predicted_outcome.charAt(0).toUpperCase() + selectedFixture.predicted_outcome.slice(1) : 'Home')) as 'Home' | 'Draw' | 'Away',
                        confidence: selectedFixture.best_market
                          ? selectedFixture.best_market.probability
                          : (selectedFixture.prediction_confidence || 0) / 100,
                        // Price and canonical status travel together; the card
                        // decides what to render from the status, not the number.
                        odds: selectedFixture.best_market?.odds ?? null,
                        price_status: selectedFixture.best_market?.price_status,
                        odds_provenance: selectedFixture.best_market?.odds_provenance ?? null,
                        odds_unavailable_reason: selectedFixture.best_market?.odds_unavailable_reason,
                        ev: selectedFixture.best_market?.expected_value ?? null,
                        score: selectedFixture.best_market?.market_score || 0,
                        explanation: (() => {
                          const bestMarket = selectedFixture.best_market
                          const outcome = bestMarket?.predicted_outcome ||
                            (selectedFixture.predicted_outcome ?
                              selectedFixture.predicted_outcome.charAt(0).toUpperCase() + selectedFixture.predicted_outcome.slice(1) : 'Home')
                          const confidence = bestMarket
                            ? (bestMarket.probability * 100)
                            : (selectedFixture.prediction_confidence || 0)
                          const marketName = bestMarket?.display_name || 'Match Result'

                          // The signal score is a ranking, so it is stated as
                          // "N / 100", never as "X% probability" or "X%
                          // confidence" — both of which read as the chance of
                          // the outcome occurring. The strength ladder that
                          // followed ("a strong prediction with high
                          // confidence") graded that ranking against a
                          // calibration standard that does not exist.
                          let explanation = bestMarket
                            ? `Highest-ranked outcome: ${marketName} — ${outcome}. Signal score ${Math.round(confidence)} / 100, a relative ranking among the available outcomes rather than a calibrated probability.`
                            : `Highest-ranked outcome: ${outcome}. Signal score ${Math.round(confidence)} / 100, a relative ranking rather than a calibrated probability.`

                          // Price status only. No numeric expected value: EV is
                          // computed from the uncalibrated signal score, so any
                          // figure reads as an assessment BetGlitch has not made.
                          const priced = canPublishPrice(bestMarket)

                          if (priced) {
                            const odds = bestMarket!.odds as number
                            explanation += ` Verified market price ${odds.toFixed(2)}, with complete provenance. Value not yet assessed.`
                          } else {
                            explanation += ` ${priceUnavailableLabel(language)} for this market, so value cannot be assessed.`
                          }

                          return explanation
                        })(),
                        probabilities: selectedFixture.predictions ? {
                          home: selectedFixture.predictions.home / 100,
                          draw: selectedFixture.predictions.draw / 100,
                          away: selectedFixture.predictions.away / 100
                        } : undefined,
                        odds_data: selectedFixture.odds_data,
                        bookmaker: (() => {
                          // 1. Try to find bookmaker for Best Market
                          if (selectedFixture.best_market?.bookmaker) {
                            return selectedFixture.best_market.bookmaker;
                          }

                          // 2. Use specific bookmaker for the predicted 1X2 outcome
                          if (selectedFixture.odds_data) {
                            const outcome = (selectedFixture.predicted_outcome || '').toLowerCase();

                            // If Best Market is 1X2 or missing, prioritize 1X2 outcome bookmakers
                            if (selectedFixture.best_market?.type === '1x2' || !selectedFixture.best_market) {
                              if (outcome === 'home' && selectedFixture.odds_data.home_bookmaker) return selectedFixture.odds_data.home_bookmaker;
                              if (outcome === 'draw' && selectedFixture.odds_data.draw_bookmaker) return selectedFixture.odds_data.draw_bookmaker;
                              if (outcome === 'away' && selectedFixture.odds_data.away_bookmaker) return selectedFixture.odds_data.away_bookmaker;
                            }
                          }

                          // 3. Fallback to generic bookmaker field (often contains the primary feed provider like Pinnacle/bet365)
                          if (selectedFixture.odds_data?.bookmaker && selectedFixture.odds_data.bookmaker !== 'Unique' && selectedFixture.odds_data.bookmaker !== 'Unknown') {
                            return selectedFixture.odds_data.bookmaker;
                          }

                          // 4. Ultimate fallback for O/U markets if odds exist -> assume main bookie
                          return selectedFixture.odds_data?.bookmaker || 'Unknown';
                        })(),
                        ensemble_info: selectedFixture.ensemble_info,
                        prediction_info: selectedFixture.prediction_info,
                        market_indicators: selectedFixture.market_indicators,
                        debug_info: selectedFixture.debug_info,
                        signal_quality: selectedFixture.signal_quality,
                        league_accuracy: null,
                        teams_data: selectedFixture.teams_data,
                        best_market: selectedFixture.best_market,
                        all_markets: selectedFixture.all_markets
                      }}
                      onViewDetails={handleViewDetails}
                    />
                  </>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Help Section */}
        {!searchQuery && (
          <div className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-2xl p-8 border border-primary-200">
            <h3 className="text-2xl font-bold text-gray-900 mb-4 text-center">{t('explore.howTo.title')}</h3>
            <div className="grid md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="bg-white w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
                  <Search className="h-8 w-8 text-primary-600" />
                </div>
                <h4 className="font-bold text-gray-900 mb-2">1. {t('explore.howTo.step1Title')}</h4>
                <p className="text-gray-600">{t('explore.howTo.step1Body')}</p>
              </div>
              <div className="text-center">
                <div className="bg-white w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
                  <TrendingUp className="h-8 w-8 text-primary-600" />
                </div>
                <h4 className="font-bold text-gray-900 mb-2">2. {t('explore.howTo.step2Title')}</h4>
                <p className="text-gray-600">{t('explore.howTo.step2Body')}</p>
              </div>
              <div className="text-center">
                <div className="bg-white w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
                  <Trophy className="h-8 w-8 text-primary-600" />
                </div>
                <h4 className="font-bold text-gray-900 mb-2">3. {t('explore.howTo.step3Title')}</h4>
                <p className="text-gray-600">{t('explore.howTo.step3Body')}</p>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
