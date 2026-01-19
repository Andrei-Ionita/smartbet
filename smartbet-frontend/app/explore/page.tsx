'use client'

import { useState, useEffect } from 'react'
import { Search, Filter, Calendar, Trophy, TrendingUp } from 'lucide-react'
import RecommendationCard from '../components/RecommendationCard'
import LoadingSpinner from '../components/LoadingSpinner'
import { useLanguage } from '../contexts/LanguageContext'
import ErrorBoundary from '../components/ErrorBoundary'
import RetryButton from '../components/RetryButton'

interface SearchResult {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  has_predictions: boolean
  has_odds: boolean
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
    confidence_interval?: {
      point_estimate: number
      lower_bound: number
      upper_bound: number
      interval_width: number
      interpretation: string
    }
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
  best_market?: {
    type: '1x2' | 'btts' | 'over_under_2.5' | 'double_chance'
    name: string
    display_name: string
    predicted_outcome: string
    probability: number
    probability_gap: number
    odds: number
    expected_value: number
    market_score: number
  }
  all_markets?: Array<{
    type: '1x2' | 'btts' | 'over_under_2.5' | 'double_chance'
    name: string
    predicted_outcome: string
    probability: number
    odds: number
    expected_value: number
    market_score: number
    is_recommended?: boolean
  }>
}

const LEAGUES = [
  { id: '', name: 'All Leagues' },
  { id: '8', name: 'Premier League' },
  { id: '9', name: 'Championship' },
  { id: '24', name: 'FA Cup' },
  { id: '27', name: 'Carabao Cup' },
  { id: '72', name: 'Eredivisie' },
  { id: '82', name: 'Bundesliga' },
  { id: '181', name: 'Admiral Bundesliga' },
  { id: '208', name: 'Pro League' },
  { id: '244', name: '1. HNL' },
  { id: '271', name: 'Superliga' },
  { id: '301', name: 'Ligue 1' },
  { id: '384', name: 'Serie A' },
  { id: '387', name: 'Serie B' },
  { id: '390', name: 'Coppa Italia' },
  { id: '444', name: 'Eliteserien' },
  { id: '453', name: 'Ekstraklasa' },
  { id: '462', name: 'Liga Portugal' },
  { id: '486', name: 'Russian Premier League' },
  { id: '501', name: 'Premiership' },
  { id: '564', name: 'La Liga' },
  { id: '567', name: 'La Liga 2' },
  { id: '570', name: 'Copa Del Rey' },
  { id: '573', name: 'Allsvenskan' },
  { id: '591', name: 'Super League' },
  { id: '600', name: 'Super Lig' },
  { id: '609', name: 'Premier League (Additional)' },
  { id: '1371', name: 'UEFA Europa League Play-offs' },
]

export default function ExplorePage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedLeague, setSelectedLeague] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [selectedFixture, setSelectedFixture] = useState<FixtureAnalysis | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [searchMessage, setSearchMessage] = useState('')
  const [browseMode, setBrowseMode] = useState(false)

  // Debounced search or browse
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchQuery.trim()) {
        // Search mode: user typed a query
        setBrowseMode(false)
        performSearch()
      } else if (selectedLeague) {
        // Browse mode: league selected, no query
        setBrowseMode(true)
        performBrowse()
      } else {
        // Nothing selected
        setSearchResults([])
        setSearchMessage('')
        setBrowseMode(false)
      }
    }, 500)

    return () => clearTimeout(timeoutId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchQuery, selectedLeague])

  const performSearch = async () => {
    if (!searchQuery.trim()) return

    setIsSearching(true)
    try {
      const params = new URLSearchParams({
        q: searchQuery,
        limit: '20'
      })

      if (selectedLeague) {
        params.append('league', selectedLeague)
      }

      // Use Next.js API - queries SportMonks directly for real-time data
      const response = await fetch(`/api/search?${params}`)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      console.log('Search results:', data)
      setSearchResults(data.results || [])
      setSearchMessage(data.message || '')
    } catch (error) {
      console.error('Search error:', error)
      setSearchResults([])
      setSearchMessage(error instanceof Error ? error.message : 'Search failed')
    } finally {
      setIsSearching(false)
    }
  }

  const performBrowse = async () => {
    if (!selectedLeague) return

    setIsSearching(true)
    try {
      const params = new URLSearchParams({
        league: selectedLeague,
        limit: '30',
        mode: 'browse'
      })

      const response = await fetch(`/api/search?${params}`)

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const data = await response.json()
      console.log('Browse results:', data)
      setSearchResults(data.results || [])
      setSearchMessage(data.message || '')
    } catch (error) {
      console.error('Browse error:', error)
      setSearchResults([])
      setSearchMessage(error instanceof Error ? error.message : 'Failed to load fixtures')
    } finally {
      setIsSearching(false)
    }
  }

  const handleRetrySearch = () => {
    browseMode ? performBrowse() : performSearch()
  }

  const [isLoadingFixture, setIsLoadingFixture] = useState(false)

  const handleFixtureSelect = async (fixtureId: number) => {
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
      } else {
        console.error('No fixture data in response', data)
      }
    } catch (error) {
      console.error('Error fetching fixture:', error)
      alert(`Failed to load fixture: ${error}`)
    } finally {
      setIsLoadingFixture(false)
    }
  }

  const formatKickoff = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
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

  const { t } = useLanguage()

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

          <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-gray-900 via-primary-600 to-blue-600 bg-clip-text text-transparent mb-4">
            {t('explore.title')}
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
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
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={t('explore.search.placeholder')}
                  className="w-full pl-12 pr-4 py-4 rounded-xl border border-gray-200 focus:ring-2 focus:ring-primary-500 focus:border-transparent text-lg shadow-sm transition-all"
                />
              </div>
              <div className="relative min-w-[200px]">
                <Filter className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <select
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

          {/* Features Badges */}
          <div className="flex flex-wrap items-center justify-center gap-4 mt-6 text-sm text-gray-500">
            <span className="flex items-center gap-1.5 px-3 py-1 bg-gray-100 rounded-full">
              <Trophy className="h-3.5 w-3.5" />
              {t('explore.search.features.leagues')}
            </span>
            <span className="flex items-center gap-1.5 px-3 py-1 bg-gray-100 rounded-full">
              <TrendingUp className="h-3.5 w-3.5" />
              {t('explore.search.features.odds')}
            </span>
            <span className="flex items-center gap-1.5 px-3 py-1 bg-blue-50 text-blue-700 rounded-full font-medium">
              <div className="h-1.5 w-1.5 rounded-full bg-blue-600 animate-pulse"></div>
              {t('explore.search.features.predictions')}
            </span>
          </div>
        </div>
        {/* Search Results or Browse Results */}
        {(searchQuery || browseMode) && (
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-lg border border-white/20 mb-8">
            <div className="flex items-center gap-2 mb-4">
              <Trophy className="h-5 w-5 text-primary-600" />
              <h2 className="text-xl font-bold text-gray-900">
                {browseMode ? t('explore.browse.title') : 'Search Results'}
              </h2>
            </div>

            {isSearching ? (
              <LoadingSpinner size="lg" text="Searching fixtures..." />

            ) : searchResults.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-fadeIn">
                {searchResults.map((fixture) => (
                  <div
                    key={fixture.fixture_id}
                    onClick={() => handleFixtureSelect(fixture.fixture_id)}
                    className="bg-white rounded-xl p-6 shadow-sm border border-gray-100 hover:shadow-md hover:border-primary-100 transition-all cursor-pointer group"
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

                    <div className="flex items-center justify-center gap-2 pt-4 border-t border-gray-50">
                      {fixture.has_predictions ? (
                        <span className="text-xs font-medium text-green-600 flex items-center bg-green-50 px-2 py-1 rounded-full">
                          <span className="w-1.5 h-1.5 rounded-full bg-green-500 mr-1.5"></span>
                          {t('explore.search.features.predictions')}
                        </span>
                      ) : (
                        <span className="text-xs text-gray-400">Analysis Pending</span>
                      )}
                      {fixture.has_odds && (
                        <span className="text-xs font-medium text-blue-600 flex items-center bg-blue-50 px-2 py-1 rounded-full">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mr-1.5"></span>
                          {t('explore.search.features.odds')}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : searchMessage ? (
              <div className="text-center py-12 bg-white rounded-2xl border border-gray-100 shadow-sm">
                <div className="text-5xl mb-4">🔍</div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('explore.search.noResults')}</h3>
                <p className="text-gray-500 max-w-sm mx-auto">
                  {searchMessage === 'No matches found' ? t('explore.search.tryStandard') : searchMessage}
                </p>
              </div>
            ) : (
              <div className="text-center py-20 opacity-50">
                <Search className="h-12 w-12 mx-auto text-gray-300 mb-4" />
                <p className="text-gray-500 font-medium">{t('explore.search.initialState')}</p>
              </div>
            )}
          </div>
        )}

        {/* Selected Fixture Analysis */}
        {isLoadingFixture ? (
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-lg border border-white/20">
            <div className="flex items-center gap-2 mb-6">
              <Calendar className="h-5 w-5 text-primary-600" />
              <h2 className="text-xl font-bold text-gray-900">Loading Analysis...</h2>
            </div>
            <LoadingSpinner size="lg" text="Loading fixture analysis..." />
          </div>
        ) : selectedFixture && (
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-lg border border-white/20">
            <div className="flex items-center gap-2 mb-6">
              <Calendar className="h-5 w-5 text-primary-600" />
              <h2 className="text-xl font-bold text-gray-900">Fixture Analysis</h2>
            </div>

            <RecommendationCard
              recommendation={{
                fixture_id: selectedFixture.fixture_id,
                home_team: selectedFixture.home_team,
                away_team: selectedFixture.away_team,
                league: selectedFixture.league,
                kickoff: selectedFixture.kickoff,
                // Use best_market prediction when available, fallback to 1X2
                predicted_outcome: (selectedFixture.best_market?.predicted_outcome ||
                  (selectedFixture.predicted_outcome ?
                    selectedFixture.predicted_outcome.charAt(0).toUpperCase() + selectedFixture.predicted_outcome.slice(1) : 'Home')) as 'Home' | 'Draw' | 'Away',
                // Use best_market probability when available
                confidence: selectedFixture.best_market
                  ? selectedFixture.best_market.probability
                  : (selectedFixture.prediction_confidence || 0) / 100,
                // Use best_market odds when available
                odds: selectedFixture.best_market?.odds || (selectedFixture.odds_data ?
                  (selectedFixture.predicted_outcome === 'home' ? selectedFixture.odds_data?.home :
                    selectedFixture.predicted_outcome === 'draw' ? selectedFixture.odds_data?.draw :
                      selectedFixture.odds_data?.away) : null),
                // Use best_market expected_value when available
                ev: selectedFixture.best_market
                  ? selectedFixture.best_market.expected_value
                  : (selectedFixture.ev_analysis?.best_ev || 0) / 100,
                score: selectedFixture.best_market?.market_score || 0,
                explanation: (() => {
                  // Use best_market data when available
                  const bestMarket = selectedFixture.best_market
                  const outcome = bestMarket?.predicted_outcome ||
                    (selectedFixture.predicted_outcome ?
                      selectedFixture.predicted_outcome.charAt(0).toUpperCase() + selectedFixture.predicted_outcome.slice(1) : 'Home')
                  const confidence = bestMarket
                    ? (bestMarket.probability * 100)
                    : (selectedFixture.prediction_confidence || 0)
                  const ev = bestMarket
                    ? (bestMarket.expected_value * 100)
                    : (selectedFixture.ev_analysis?.best_ev || 0)
                  const odds = bestMarket?.odds || (selectedFixture.odds_data ?
                    (selectedFixture.predicted_outcome === 'home' ? selectedFixture.odds_data?.home :
                      selectedFixture.predicted_outcome === 'draw' ? selectedFixture.odds_data?.draw :
                        selectedFixture.odds_data?.away) : null)
                  const marketName = bestMarket?.display_name || 'Match Result'

                  let explanation = bestMarket
                    ? `Best bet: ${marketName} - ${outcome} (${confidence.toFixed(1)}% probability).`
                    : `SportMonks AI predicts a ${outcome} win with ${confidence.toFixed(1)}% confidence.`

                  // Add confidence context
                  if (confidence >= 70) {
                    explanation += ` This is a strong prediction with high confidence.`
                  } else if (confidence >= 60) {
                    explanation += ` This is a good prediction with solid confidence.`
                  } else if (confidence >= 50) {
                    explanation += ` This is a moderate prediction - the match could go either way.`
                  } else {
                    explanation += ` This is a close match with higher uncertainty.`
                  }

                  // Add odds and EV information if available
                  if (odds && ev) {
                    if (ev > 0) {
                      explanation += ` Odds: ${odds.toFixed(2)} with ${ev.toFixed(1)}% expected value.`

                      // Add value assessment
                      if (ev >= 20) {
                        explanation += ` Exceptional betting value detected!`
                      } else if (ev >= 15) {
                        explanation += ` Excellent value opportunity.`
                      } else if (ev >= 10) {
                        explanation += ` Good betting value.`
                      } else if (ev >= 5) {
                        explanation += ` Positive value present.`
                      } else {
                        explanation += ` Marginal value - consider smaller stakes.`
                      }
                    } else {
                      explanation += ` Current odds (${odds.toFixed(2)}) don't offer positive value.`
                    }
                  }

                  // Add recommendation summary
                  if (confidence >= 70 && ev >= 15) {
                    explanation += ` Premium betting opportunity!`
                  } else if (confidence >= 60 && ev >= 10) {
                    explanation += ` Strong betting recommendation.`
                  } else if (ev < 5 || confidence < 50) {
                    explanation += ` Proceed with caution and smaller stakes.`
                  }

                  return explanation
                })(),
                probabilities: selectedFixture.predictions ? {
                  home: selectedFixture.predictions.home / 100,
                  draw: selectedFixture.predictions.draw / 100,
                  away: selectedFixture.predictions.away / 100
                } : undefined,
                odds_data: selectedFixture.odds_data,
                bookmaker: selectedFixture.odds_data?.bookmaker || 'Unknown',
                ensemble_info: selectedFixture.ensemble_info,
                prediction_info: selectedFixture.prediction_info,
                market_indicators: selectedFixture.market_indicators,
                debug_info: selectedFixture.debug_info,
                signal_quality: selectedFixture.signal_quality,
                league_accuracy: null,
                teams_data: selectedFixture.teams_data,
                // Multi-market support
                best_market: selectedFixture.best_market,
                all_markets: selectedFixture.all_markets
              }}
              onViewDetails={handleViewDetails}
            />
          </div>
        )}

        {/* Help Section */}
        {!searchQuery && (
          <div className="bg-gradient-to-r from-primary-50 to-blue-50 rounded-2xl p-8 border border-primary-200">
            <h3 className="text-2xl font-bold text-gray-900 mb-4 text-center">How to Use the Explorer</h3>
            <div className="grid md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="bg-white w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
                  <Search className="h-8 w-8 text-primary-600" />
                </div>
                <h4 className="font-bold text-gray-900 mb-2">1. Search</h4>
                <p className="text-gray-600">Enter any team name to find upcoming fixtures</p>
              </div>
              <div className="text-center">
                <div className="bg-white w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
                  <TrendingUp className="h-8 w-8 text-primary-600" />
                </div>
                <h4 className="font-bold text-gray-900 mb-2">2. Analyze</h4>
                <p className="text-gray-600">Click on any fixture to see detailed AI predictions and odds</p>
              </div>
              <div className="text-center">
                <div className="bg-white w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
                  <Trophy className="h-8 w-8 text-primary-600" />
                </div>
                <h4 className="font-bold text-gray-900 mb-2">3. Bet Smart</h4>
                <p className="text-gray-600">Use EV analysis and prediction strength to make informed decisions</p>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
