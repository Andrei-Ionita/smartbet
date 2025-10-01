'use client'

import { useState, useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { Filter, TrendingUp, Calendar, Clock } from 'lucide-react'
import { Match, leagues } from '@/lib/mockData'
import { getMatchesByLeague, getRecommendedMatches } from '@/lib/mockData'
import MatchCard from '@/components/MatchCard'

export default function PredictionsPage() {
  const searchParams = useSearchParams()
  const [matches, setMatches] = useState<Match[]>([])
  const [filteredMatches, setFilteredMatches] = useState<Match[]>([])
  const [selectedLeague, setSelectedLeague] = useState('')
  const [showOnlyRecommended, setShowOnlyRecommended] = useState(false)

  useEffect(() => {
    // Get initial league from URL params
    const leagueParam = searchParams.get('league')
    if (leagueParam) {
      setSelectedLeague(leagueParam)
      setMatches(getMatchesByLeague(leagueParam))
    } else {
      setMatches(getRecommendedMatches())
    }
  }, [searchParams])

  useEffect(() => {
    let filtered = matches

    if (showOnlyRecommended) {
      filtered = filtered.filter(match => match.prediction.isRecommended)
    }

    setFilteredMatches(filtered)
  }, [matches, showOnlyRecommended])

  const handleLeagueChange = (league: string) => {
    setSelectedLeague(league)
    if (league === '') {
      setMatches(getRecommendedMatches())
    } else {
      setMatches(getMatchesByLeague(league))
    }
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Match Predictions
        </h1>
        <p className="text-gray-600">
          AI-powered predictions with confidence scores and expected value analysis
        </p>
      </div>

      {/* Filters */}
      <div className="card mb-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center space-x-4">
            <Filter className="h-5 w-5 text-gray-500" />
            <span className="font-medium text-gray-900">Filters:</span>
          </div>
          
          <div className="flex flex-col sm:flex-row gap-4">
            {/* League Filter */}
            <div className="flex items-center space-x-2">
              <label htmlFor="league-filter" className="text-sm font-medium text-gray-700">
                League:
              </label>
              <select
                id="league-filter"
                value={selectedLeague}
                onChange={(e) => handleLeagueChange(e.target.value)}
                className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                <option value="">All Leagues</option>
                {leagues.map((league) => (
                  <option key={league.id} value={league.name}>
                    {league.flag} {league.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Recommended Filter */}
            <div className="flex items-center space-x-2">
              <input
                type="checkbox"
                id="recommended-filter"
                checked={showOnlyRecommended}
                onChange={(e) => setShowOnlyRecommended(e.target.checked)}
                className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
              />
              <label htmlFor="recommended-filter" className="text-sm font-medium text-gray-700">
                Show only recommended bets
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid md:grid-cols-4 gap-4 mb-6">
        <div className="card text-center">
          <div className="text-2xl font-bold text-gray-900">{filteredMatches.length}</div>
          <div className="text-sm text-gray-600">Total Matches</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold text-success-600">
            {filteredMatches.filter(m => m.prediction.isRecommended).length}
          </div>
          <div className="text-sm text-gray-600">Recommended</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold text-primary-600">
            {filteredMatches.length > 0 
              ? (filteredMatches.filter(m => m.prediction.isRecommended).length / filteredMatches.length * 100).toFixed(1)
              : 0}%
          </div>
          <div className="text-sm text-gray-600">Recommendation Rate</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold text-warning-600">
            {filteredMatches.length > 0 
              ? (filteredMatches.reduce((sum, m) => sum + m.prediction.expectedValue, 0) / filteredMatches.length * 100).toFixed(1)
              : 0}%
          </div>
          <div className="text-sm text-gray-600">Avg Expected Value</div>
        </div>
      </div>

      {/* Matches List */}
      <div className="space-y-4">
        {filteredMatches.length === 0 ? (
          <div className="card text-center py-12">
            <TrendingUp className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No matches found</h3>
            <p className="text-gray-600">
              {showOnlyRecommended 
                ? 'No recommended bets available for the selected criteria.'
                : 'No matches available for the selected league.'
              }
            </p>
          </div>
        ) : (
          filteredMatches.map((match) => (
            <MatchCard key={match.id} match={match} />
          ))
        )}
      </div>

      {/* Legend */}
      <div className="mt-8 card">
        <h3 className="font-medium text-gray-900 mb-4">Legend</h3>
        <div className="grid md:grid-cols-2 gap-4 text-sm">
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-success-500 rounded-full"></div>
            <span>Recommended bet (Confidence > 65% & EV > 0%)</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-warning-500 rounded-full"></div>
            <span>High confidence but low value</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-danger-500 rounded-full"></div>
            <span>Low confidence prediction</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-3 h-3 bg-gray-500 rounded-full"></div>
            <span>Experimental model (Premier League)</span>
          </div>
        </div>
      </div>
    </div>
  )
} 