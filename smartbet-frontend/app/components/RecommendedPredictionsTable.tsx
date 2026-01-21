'use client'

import { useState, useEffect } from 'react'
import { RefreshCw, CheckCircle2, XCircle, Clock, TrendingUp, TrendingDown, Award, Lock, ExternalLink } from 'lucide-react'

interface RecommendedPrediction {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  predicted_outcome: string
  predicted_outcome_raw: string
  confidence: number
  expected_value: number | null
  odds_home: number | null
  odds_draw: number | null
  odds_away: number | null
  bookmaker: string | null
  actual_outcome: string | null
  actual_outcome_raw: string | null
  actual_score_home: number | null
  actual_score_away: number | null
  match_status: string | null
  was_correct: boolean | null
  profit_loss_10: number | null
  roi_percent: number | null
  probabilities: {
    home: number
    draw: number
    away: number
  }
  model_count: number
  consensus: number | null
  variance: number | null
  prediction_logged_at: string
  result_logged_at: string | null
  is_completed: boolean
}

interface Summary {
  total_recommended: number
  completed: number
  pending: number
  correct: number
  incorrect: number
  accuracy: number | null
  total_profit_loss: number
  average_roi: number | null
  implied_baseline: number | null
  edge_vs_market: number | null
  baseline_comparison?: {
    our_accuracy: number | null
    market_implied: number | null
    edge: number | null
    sample_size: number
    explanation: string | null
  }
}

export default function RecommendedPredictionsTable() {
  const [predictions, setPredictions] = useState<RecommendedPrediction[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [includePending, setIncludePending] = useState(true)

  const fetchPredictions = async (forceUpdate = false) => {
    try {
      setIsRefreshing(true)
      setError(null)

      // First, trigger result updates for pending fixtures (optional, only on manual refresh or when forced)
      if (forceUpdate || isLoading) {
        try {
          console.log('🔄 Triggering fixture result updates...')
          const updateResponse = await fetch('/api/django/update-results', { method: 'POST' })
          const updateData = await updateResponse.json()
          if (updateData.updated_count > 0) {
            console.log(`✅ Updated ${updateData.updated_count} fixture results`)
          }
        } catch (updateErr) {
          console.warn('⚠️ Could not update results, continuing anyway:', updateErr)
          // Don't fail the whole operation if update fails
        }
      }

      // Call Django API through Next.js API route
      const response = await fetch(`/api/django/recommended-predictions?include_pending=${includePending}`)
      const data = await response.json()

      if (data.success) {
        setPredictions(data.data || [])
        setSummary(data.summary || null)
      } else {
        setError(data.error || 'Failed to fetch predictions')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred')
      console.error('Error fetching recommended predictions:', err)
    } finally {
      setIsLoading(false)
      setIsRefreshing(false)
    }
  }

  useEffect(() => {
    fetchPredictions()

    // Auto-refresh every 2 minutes to catch new results
    const refreshInterval = setInterval(() => {
      console.log('🔄 Auto-refreshing predictions...')
      fetchPredictions()
    }, 120000) // 2 minutes

    return () => clearInterval(refreshInterval)
  }, [includePending])

  // Refresh when tab becomes visible
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        console.log('👁️ Tab became visible, refreshing predictions...')
        fetchPredictions()
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange)
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange)
  }, [includePending])

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  // Calculate time before kickoff when prediction was logged
  const getLoggedBeforeKickoff = (loggedAt: string, kickoff: string) => {
    const loggedDate = new Date(loggedAt)
    const kickoffDate = new Date(kickoff)
    const diffMs = kickoffDate.getTime() - loggedDate.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    const diffMins = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60))

    if (diffHours >= 24) {
      const days = Math.floor(diffHours / 24)
      return `${days}d ${diffHours % 24}h before`
    } else if (diffHours >= 1) {
      return `${diffHours}h ${diffMins}m before`
    } else if (diffMins >= 0) {
      return `${diffMins}m before`
    } else {
      return 'After kickoff'
    }
  }

  // Check if prediction is locked (after kickoff)
  const isLocked = (kickoff: string) => {
    return new Date(kickoff) < new Date()
  }

  // Generate FlashScore search URL for match
  const getExternalMatchUrl = (homeTeam: string, awayTeam: string) => {
    const searchTerm = encodeURIComponent(`${homeTeam} ${awayTeam}`)
    return `https://www.flashscore.com/search/?q=${searchTerm}`
  }

  const getOutcomeColor = (outcome: string) => {
    switch (outcome?.toLowerCase()) {
      case 'home':
        return 'bg-blue-100 text-blue-800'
      case 'draw':
        return 'bg-gray-100 text-gray-800'
      case 'away':
        return 'bg-purple-100 text-purple-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getCorrectnessBadge = (wasCorrect: boolean | null, isCompleted: boolean) => {
    if (!isCompleted) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
          <Clock className="h-3 w-3" />
          Pending
        </span>
      )
    }

    if (wasCorrect === true) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
          <CheckCircle2 className="h-3 w-3" />
          Correct
        </span>
      )
    } else if (wasCorrect === false) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
          <XCircle className="h-3 w-3" />
          Incorrect
        </span>
      )
    }

    return null
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-200">
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-8 w-8 text-primary-600 animate-spin" />
          <span className="ml-3 text-gray-600">Loading recommended predictions...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-lg border border-red-200">
        <div className="text-center py-12">
          <XCircle className="h-12 w-12 text-red-500 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Error Loading Predictions</h3>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => fetchPredictions(true)}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      {summary && (
        <>
          <div className="grid md:grid-cols-4 gap-4">
            <div className="bg-white rounded-xl p-4 shadow-lg border border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Recommended</p>
                  <p className="text-2xl font-bold text-gray-900">{summary.total_recommended}</p>
                </div>
                <Award className="h-8 w-8 text-primary-600" />
              </div>
            </div>

            <div className="bg-white rounded-xl p-4 shadow-lg border border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Completed</p>
                  <p className="text-2xl font-bold text-gray-900">{summary.completed}</p>
                  {summary.pending > 0 && (
                    <p className="text-xs text-yellow-600 mt-1">{summary.pending} pending</p>
                  )}
                </div>
                <CheckCircle2 className="h-8 w-8 text-blue-600" />
              </div>
            </div>

            <div className="bg-white rounded-xl p-4 shadow-lg border border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Accuracy</p>
                  <p className={`text-2xl font-bold ${summary.accuracy && summary.accuracy >= 70 ? 'text-green-600' : summary.accuracy && summary.accuracy >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
                    {summary.accuracy !== null ? `${summary.accuracy}%` : 'N/A'}
                  </p>
                  {summary.accuracy !== null && (
                    <p className="text-xs text-gray-500 mt-1">
                      {summary.correct} correct, {summary.incorrect} incorrect
                    </p>
                  )}
                </div>
                <TrendingUp className={`h-8 w-8 ${summary.accuracy && summary.accuracy >= 70 ? 'text-green-600' : summary.accuracy && summary.accuracy >= 60 ? 'text-yellow-600' : 'text-red-600'}`} />
              </div>
            </div>

            <div className="bg-white rounded-xl p-4 shadow-lg border border-gray-200">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total P/L ($10 stakes)</p>
                  <p className={`text-2xl font-bold ${summary.total_profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    ${summary.total_profit_loss.toFixed(2)}
                  </p>
                  {summary.average_roi !== null && (
                    <p className="text-xs text-gray-500 mt-1">
                      Avg ROI: {summary.average_roi.toFixed(1)}%
                    </p>
                  )}
                </div>
                {summary.total_profit_loss >= 0 ? (
                  <TrendingUp className="h-8 w-8 text-green-600" />
                ) : (
                  <TrendingDown className="h-8 w-8 text-red-600" />
                )}
              </div>
            </div>
          </div>

          {/* Edge vs Market Comparison - THE KEY TRUST METRIC */}
          {summary.edge_vs_market !== null && summary.implied_baseline !== null && (
            <div className={`mt-4 rounded-xl p-5 shadow-lg border-2 ${summary.edge_vs_market >= 0 ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div className="flex items-center gap-4">
                  <div className={`w-16 h-16 rounded-full flex items-center justify-center ${summary.edge_vs_market >= 0 ? 'bg-green-100' : 'bg-red-100'}`}>
                    <span className={`text-2xl font-bold ${summary.edge_vs_market >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                      {summary.edge_vs_market >= 0 ? '+' : ''}{summary.edge_vs_market.toFixed(1)}%
                    </span>
                  </div>
                  <div>
                    <h3 className={`text-lg font-bold ${summary.edge_vs_market >= 0 ? 'text-green-800' : 'text-red-800'}`}>
                      Edge vs. Market
                    </h3>
                    <p className="text-sm text-gray-600">
                      Our accuracy: <strong>{summary.accuracy}%</strong> vs. implied by odds: <strong>{summary.implied_baseline}%</strong>
                    </p>
                  </div>
                </div>
                <div className="text-sm text-gray-500 max-w-md">
                  <p>
                    {summary.edge_vs_market >= 0
                      ? `✅ We beat the market expectation by ${summary.edge_vs_market.toFixed(1)} percentage points. This is real, verifiable edge.`
                      : `⚠️ Currently ${Math.abs(summary.edge_vs_market).toFixed(1)}pp below market expectations. Track record is still building.`
                    }
                  </p>
                </div>
              </div>
            </div>
          )}
        </>
      )}

      {/* Controls */}
      <div className="bg-white rounded-xl p-4 shadow-lg border border-gray-200 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex flex-col md:flex-row md:items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={includePending}
              onChange={(e) => setIncludePending(e.target.checked)}
              className="rounded text-primary-600 focus:ring-primary-500"
            />
            <span className="text-sm font-medium text-gray-700">Include Pending</span>
          </label>
        </div>

        <div className="flex items-center gap-3">

          <button
            onClick={() => fetchPredictions(true)}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Match</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">League</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Our Prediction</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Confidence</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actual Outcome</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Result</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">P/L</th>
                <th className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Kickoff</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {predictions.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-6 py-12 text-center text-gray-500">
                    No recommended predictions found. Make sure predictions are marked as recommended.
                  </td>
                </tr>
              ) : (
                predictions.map((pred) => (
                  <tr key={pred.fixture_id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-start gap-2">
                        {isLocked(pred.kickoff) && (
                          <Lock className="h-4 w-4 text-green-600 mt-0.5 flex-shrink-0" />
                        )}
                        <div>
                          <a
                            href={getExternalMatchUrl(pred.home_team, pred.away_team)}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-sm font-medium text-gray-900 hover:text-primary-600 hover:underline flex items-center gap-1"
                          >
                            {pred.home_team}
                            <ExternalLink className="h-3 w-3 opacity-50" />
                          </a>
                          <div className="text-sm text-gray-500">vs {pred.away_team}</div>
                          <div className="text-xs text-gray-400 mt-1" title={`Logged: ${new Date(pred.prediction_logged_at).toLocaleString()}`}>
                            🕐 {getLoggedBeforeKickoff(pred.prediction_logged_at, pred.kickoff)} kickoff
                          </div>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{pred.league}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-3 py-1 rounded-full text-xs font-medium ${getOutcomeColor(pred.predicted_outcome)}`}>
                        {pred.predicted_outcome}
                      </span>
                      {/* Odds with bookmaker */}
                      {(() => {
                        const outcome = pred.predicted_outcome?.toLowerCase()
                        const odds = outcome === 'home' ? pred.odds_home : outcome === 'draw' ? pred.odds_draw : pred.odds_away
                        return odds ? (
                          <div className="text-xs text-gray-500 mt-1">
                            @ {odds.toFixed(2)} {pred.bookmaker && <span className="text-gray-400">({pred.bookmaker})</span>}
                          </div>
                        ) : null
                      })()}
                      {pred.expected_value !== null && (
                        <div className="text-xs text-green-600 mt-0.5">EV: +{pred.expected_value.toFixed(1)}%</div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="flex items-center">
                        <div className="flex-1 bg-gray-200 rounded-full h-2 mr-2" style={{ width: '60px' }}>
                          <div
                            className="bg-primary-600 h-2 rounded-full"
                            style={{ width: `${pred.confidence}%` }}
                          ></div>
                        </div>
                        <span className="text-sm text-gray-900">{pred.confidence.toFixed(1)}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {pred.actual_outcome ? (
                        <>
                          <span className={`inline-flex px-3 py-1 rounded-full text-xs font-medium ${getOutcomeColor(pred.actual_outcome)}`}>
                            {pred.actual_outcome}
                          </span>
                          {pred.actual_score_home !== null && pred.actual_score_away !== null && (
                            <div className="text-xs text-gray-500 mt-1">
                              {pred.actual_score_home} - {pred.actual_score_away}
                            </div>
                          )}
                        </>
                      ) : (
                        <span className="text-sm text-gray-400">Pending</span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {getCorrectnessBadge(pred.was_correct, pred.is_completed)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {pred.profit_loss_10 !== null ? (
                        <span className={`text-sm font-medium ${pred.profit_loss_10 >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          ${pred.profit_loss_10 >= 0 ? '+' : ''}{pred.profit_loss_10.toFixed(2)}
                        </span>
                      ) : (
                        <span className="text-sm text-gray-400">-</span>
                      )}
                      {pred.roi_percent !== null && (
                        <div className={`text-xs ${pred.roi_percent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {pred.roi_percent >= 0 ? '+' : ''}{pred.roi_percent.toFixed(1)}% ROI
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{formatDate(pred.kickoff)}</div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

