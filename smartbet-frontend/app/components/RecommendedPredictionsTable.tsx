'use client'

import { useState, useEffect } from 'react'
import { RefreshCw, CheckCircle2, XCircle, Clock, TrendingUp, TrendingDown, Award } from 'lucide-react'

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
}

export default function RecommendedPredictionsTable() {
  const [predictions, setPredictions] = useState<RecommendedPrediction[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [includePending, setIncludePending] = useState(true)

  const fetchPredictions = async () => {
    try {
      setIsRefreshing(true)
      setError(null)
      
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
            onClick={fetchPredictions}
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
      )}

      {/* Controls */}
      <div className="bg-white rounded-xl p-4 shadow-lg border border-gray-200 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={includePending}
              onChange={(e) => setIncludePending(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm font-medium text-gray-700">Include Pending Matches</span>
          </label>
        </div>
        
        <button
          onClick={fetchPredictions}
          disabled={isRefreshing}
          className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
          {isRefreshing ? 'Refreshing...' : 'Refresh'}
        </button>
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
                      <div className="text-sm font-medium text-gray-900">{pred.home_team}</div>
                      <div className="text-sm text-gray-500">vs {pred.away_team}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{pred.league}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`inline-flex px-3 py-1 rounded-full text-xs font-medium ${getOutcomeColor(pred.predicted_outcome)}`}>
                        {pred.predicted_outcome}
                      </span>
                      {pred.expected_value !== null && (
                        <div className="text-xs text-gray-500 mt-1">EV: {pred.expected_value}%</div>
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
                        <span className="text-sm text-gray-900">{pred.confidence}%</span>
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

