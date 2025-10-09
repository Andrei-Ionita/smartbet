'use client'

import { useState, useEffect } from 'react'
import { Search, Filter, Calendar, Trophy, TrendingUp } from 'lucide-react'
import RecommendationCard from '../components/RecommendationCard'
import LoadingSpinner from '../components/LoadingSpinner'
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
  ensemble_info: {
    model_count: number
    consensus: number
    variance: number
    strategy: string
  }
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
  { id: '486', name: 'Premier League (Romanian)' },
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

  // Debounced search
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchQuery.trim()) {
        performSearch()
      } else {
        setSearchResults([])
        setSearchMessage('')
      }
    }, 500)

    return () => clearTimeout(timeoutId)
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

      const response = await fetch(`/api/search?${params}`)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const data = await response.json()
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

  const handleRetrySearch = () => {
    performSearch()
  }

  const [isLoadingFixture, setIsLoadingFixture] = useState(false)

  const handleFixtureSelect = async (fixtureId: number) => {
    setIsLoadingFixture(true)
    try {
      const response = await fetch(`/api/fixture/${fixtureId}`)
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      
      const data = await response.json()
      setSelectedFixture(data.fixture)
    } catch (error) {
      console.error('Error fetching fixture:', error)
      // You could show an error toast here
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
            Explore Fixtures
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Search for any upcoming match and get detailed AI predictions, odds analysis, and betting recommendations
          </p>
        </div>

        {/* Search Interface */}
        <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-8 shadow-lg border border-white/20 mb-8">
          <div className="flex flex-col md:flex-row gap-4 mb-6">
            <div className="flex-1 relative">
              <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
              <input
                type="text"
                placeholder="Search by team name (e.g., 'Manchester City', 'Barcelona', 'Bayern')"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-12 pr-4 py-4 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent text-lg"
              />
            </div>
            
            <div className="md:w-64">
              <select
                value={selectedLeague}
                onChange={(e) => setSelectedLeague(e.target.value)}
                className="w-full px-4 py-4 border border-gray-200 rounded-xl focus:ring-2 focus:ring-primary-500 focus:border-transparent text-lg"
              >
                {LEAGUES.map((league) => (
                  <option key={league.id} value={league.id}>
                    {league.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Filter className="h-4 w-4" />
            <span>Search across all 27 leagues • Real-time odds • AI predictions</span>
          </div>
        </div>

        {/* Search Results */}
        {searchQuery && (
          <div className="bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-lg border border-white/20 mb-8">
            <div className="flex items-center gap-2 mb-4">
              <Trophy className="h-5 w-5 text-primary-600" />
              <h2 className="text-xl font-bold text-gray-900">Search Results</h2>
            </div>

            {isSearching ? (
              <LoadingSpinner size="lg" text="Searching fixtures..." />
            ) : searchResults.length > 0 ? (
              <div className="space-y-3">
                {searchResults.map((result) => (
                  <div
                    key={result.fixture_id}
                    onClick={() => handleFixtureSelect(result.fixture_id)}
                    className="p-4 border border-gray-200 rounded-xl hover:border-primary-300 hover:bg-primary-50 cursor-pointer transition-all duration-200 hover:shadow-md"
                  >
                    <div className="flex justify-between items-center">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="text-sm font-medium text-primary-600 bg-primary-50 px-3 py-1 rounded-full">
                            {result.league}
                          </span>
                          <span className="text-xs bg-gray-100 text-gray-600 px-3 py-1 rounded-full font-medium">
                            {formatKickoff(result.kickoff)}
                          </span>
                          {result.has_predictions && (
                            <span className="text-xs bg-green-100 text-green-700 px-3 py-1 rounded-full font-medium">
                              AI Predictions
                            </span>
                          )}
                          {result.has_odds && (
                            <span className="text-xs bg-blue-100 text-blue-700 px-3 py-1 rounded-full font-medium">
                              Live Odds
                            </span>
                          )}
                        </div>
                        <h3 className="text-lg font-bold text-gray-900">
                          {result.home_team} vs {result.away_team}
                        </h3>
                      </div>
                      <div className="flex items-center gap-2">
                        <TrendingUp className="h-5 w-5 text-gray-400" />
                        <span className="text-sm text-gray-500">Analyze</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Search className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                <p className="text-gray-600 mb-4">
                  {searchMessage || 'No fixtures found matching your search'}
                </p>
                {searchMessage.includes('error') || searchMessage.includes('Error') || searchMessage.includes('HTTP') ? (
                  <RetryButton onRetry={handleRetrySearch} text="Retry Search" />
                ) : null}
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
                predicted_outcome: selectedFixture.predicted_outcome ? 
                  selectedFixture.predicted_outcome.charAt(0).toUpperCase() + selectedFixture.predicted_outcome.slice(1) as 'Home' | 'Draw' | 'Away' : 'Home',
                confidence: selectedFixture.prediction_confidence,
                odds: selectedFixture.odds_data ? 
                  (selectedFixture.ev_analysis.best_bet === 'home' ? selectedFixture.odds_data.home :
                   selectedFixture.ev_analysis.best_bet === 'draw' ? selectedFixture.odds_data.draw :
                   selectedFixture.ev_analysis.best_bet === 'away' ? selectedFixture.odds_data.away : null) : null,
                ev: selectedFixture.ev_analysis.best_ev,
                score: 0,
                explanation: (() => {
                  const outcome = selectedFixture.predicted_outcome ? 
                    selectedFixture.predicted_outcome.charAt(0).toUpperCase() + selectedFixture.predicted_outcome.slice(1) : 'Home'
                  const confidence = selectedFixture.prediction_confidence
                  const strength = selectedFixture.prediction_strength.toLowerCase()
                  const modelCount = selectedFixture.ensemble_info.model_count
                  
                  let explanation = `SmartBet AI predicts a ${outcome} win with ${confidence}% confidence using ${modelCount} AI models with ${strength} prediction strength.`
                  
                  // Add odds and EV information if available
                  if (selectedFixture.odds_data && selectedFixture.ev_analysis.best_ev) {
                    const bestBet = selectedFixture.ev_analysis.best_bet
                    const odds = bestBet === 'home' ? selectedFixture.odds_data.home :
                                bestBet === 'draw' ? selectedFixture.odds_data.draw :
                                selectedFixture.odds_data.away
                    const ev = selectedFixture.ev_analysis.best_ev
                    
                    if (odds && ev > 0) {
                      explanation += ` Best betting opportunity: ${bestBet} at ${odds.toFixed(2)} odds (+${Math.round(ev * 100)}% EV).`
                    }
                  }
                  
                  return explanation
                })(),
                probabilities: selectedFixture.predictions,
                odds_data: selectedFixture.odds_data,
                debug_info: {
                  total_predictions: 0,
                  valid_predictions: selectedFixture.ensemble_info.model_count,
                  strategy: selectedFixture.ensemble_info.strategy,
                  consensus: selectedFixture.ensemble_info.consensus,
                  variance: selectedFixture.ensemble_info.variance,
                  model_count: selectedFixture.ensemble_info.model_count
                }
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
