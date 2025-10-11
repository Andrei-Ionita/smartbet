'use client'

import { useState, useEffect } from 'react'
import { 
  Trophy, 
  TrendingUp, 
  Target, 
  DollarSign,
  CheckCircle,
  XCircle,
  Clock,
  BarChart3,
  Award,
  Shield,
  Zap,
  Activity
} from 'lucide-react'
import useSWR from 'swr'

const fetcher = (url: string) => fetch(url).then(res => res.json())

interface PerformanceData {
  overall: {
    total_predictions: number
    correct_predictions: number
    accuracy_percent: number
    total_profit_loss: number
    roi_percent: number
    average_confidence: number
  }
  by_outcome: {
    [key: string]: {
      total: number
      correct: number
      accuracy_percent: number
    }
  }
  by_confidence_level: {
    [key: string]: {
      total: number
      correct: number
      accuracy_percent: number
      roi_percent: number
    }
  }
  by_league: Array<{
    league: string
    total: number
    correct: number
    accuracy_percent: number
  }>
  recent_predictions: Array<{
    fixture_id: number
    home_team: string
    away_team: string
    league: string
    kickoff: string
    predicted_outcome: string
    actual_outcome: string
    confidence: number
    was_correct: boolean
    profit_loss: number
    score: string
  }>
}

export default function TrackRecordPage() {
  const { data, error, isLoading } = useSWR('/api/performance', fetcher, {
    refreshInterval: 60000, // Refresh every 60 seconds
  })

  const stats: PerformanceData | null = data?.data || null

  const getAccuracyColor = (accuracy: number) => {
    if (accuracy >= 65) return 'text-green-600 bg-green-100'
    if (accuracy >= 55) return 'text-yellow-600 bg-yellow-100'
    return 'text-red-600 bg-red-100'
  }

  const getROIColor = (roi: number) => {
    if (roi > 10) return 'text-green-600'
    if (roi > 0) return 'text-yellow-600'
    return 'text-red-600'
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-3 mb-4">
            <Shield className="h-12 w-12 text-blue-600" />
            <h1 className="text-4xl md:text-5xl font-bold text-gray-900">
              Track Record
            </h1>
          </div>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            Transparent, verifiable performance tracking. Every prediction timestamped before matches start.
          </p>
          <div className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
            <Clock className="h-4 w-4" />
            <span>Updated in real-time as matches complete</span>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
            <XCircle className="h-12 w-12 text-red-600 mx-auto mb-4" />
            <p className="text-red-800 font-medium">Error loading performance data</p>
          </div>
        )}

        {/* No Data Yet */}
        {!isLoading && !error && stats && stats.overall.total_predictions === 0 && (
          <div className="bg-white rounded-2xl shadow-lg p-12 text-center">
            <Activity className="h-16 w-16 text-gray-400 mx-auto mb-6" />
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Track Record Coming Soon
            </h2>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto mb-6">
              We're starting to track all predictions with verifiable timestamps. 
              As matches complete over the next few days, you'll see our complete performance history here.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-3xl mx-auto mt-8">
              <div className="bg-blue-50 rounded-xl p-6">
                <CheckCircle className="h-8 w-8 text-blue-600 mx-auto mb-3" />
                <h3 className="font-semibold text-gray-900 mb-2">Predictions Logged</h3>
                <p className="text-sm text-gray-600">Timestamped before matches</p>
              </div>
              <div className="bg-purple-50 rounded-xl p-6">
                <Target className="h-8 w-8 text-purple-600 mx-auto mb-3" />
                <h3 className="font-semibold text-gray-900 mb-2">Results Tracked</h3>
                <p className="text-sm text-gray-600">Automatically collected</p>
              </div>
              <div className="bg-green-50 rounded-xl p-6">
                <BarChart3 className="h-8 w-8 text-green-600 mx-auto mb-3" />
                <h3 className="font-semibold text-gray-900 mb-2">Performance Calculated</h3>
                <p className="text-sm text-gray-600">Honest, transparent metrics</p>
              </div>
            </div>
          </div>
        )}

        {/* Data Available */}
        {!isLoading && !error && stats && stats.overall.total_predictions > 0 && (
          <div className="space-y-8">
            {/* Overall Stats - Hero Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white rounded-2xl shadow-lg p-6 border-2 border-blue-200">
                <div className="flex items-center justify-between mb-4">
                  <Trophy className="h-10 w-10 text-blue-600" />
                  <span className={`px-3 py-1 rounded-full text-sm font-bold ${getAccuracyColor(stats.overall.accuracy_percent)}`}>
                    {stats.overall.accuracy_percent}%
                  </span>
                </div>
                <h3 className="text-gray-600 text-sm font-medium mb-2">Overall Accuracy</h3>
                <p className="text-3xl font-bold text-gray-900">
                  {stats.overall.correct_predictions}/{stats.overall.total_predictions}
                </p>
                <p className="text-sm text-gray-500 mt-2">
                  {stats.overall.total_predictions} predictions tracked
                </p>
              </div>

              <div className="bg-white rounded-2xl shadow-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <DollarSign className="h-10 w-10 text-green-600" />
                  <span className={`text-2xl font-bold ${getROIColor(stats.overall.roi_percent)}`}>
                    {stats.overall.roi_percent > 0 ? '+' : ''}{stats.overall.roi_percent}%
                  </span>
                </div>
                <h3 className="text-gray-600 text-sm font-medium mb-2">Return on Investment</h3>
                <p className="text-3xl font-bold text-gray-900">
                  ${stats.overall.total_profit_loss > 0 ? '+' : ''}{stats.overall.total_profit_loss}
                </p>
                <p className="text-sm text-gray-500 mt-2">
                  Based on $10 stakes
                </p>
              </div>

              <div className="bg-white rounded-2xl shadow-lg p-6">
                <div className="flex items-center justify-between mb-4">
                  <Target className="h-10 w-10 text-purple-600" />
                  <Award className="h-8 w-8 text-purple-600" />
                </div>
                <h3 className="text-gray-600 text-sm font-medium mb-2">Avg Confidence</h3>
                <p className="text-3xl font-bold text-gray-900">
                  {stats.overall.average_confidence.toFixed(1)}%
                </p>
                <p className="text-sm text-gray-500 mt-2">
                  Prediction strength
                </p>
              </div>
            </div>

            {/* By Outcome */}
            <div className="bg-white rounded-2xl shadow-lg p-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-3">
                <BarChart3 className="h-7 w-7 text-blue-600" />
                Performance by Outcome
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {Object.entries(stats.by_outcome).map(([outcome, data]) => (
                  <div key={outcome} className="bg-gray-50 rounded-xl p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4 capitalize">{outcome} Predictions</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">Total:</span>
                        <span className="font-bold text-gray-900">{data.total}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">Correct:</span>
                        <span className="font-bold text-green-600">{data.correct}</span>
                      </div>
                      <div className="pt-3 border-t border-gray-200">
                        <div className="flex justify-between items-center">
                          <span className="text-gray-600 font-medium">Accuracy:</span>
                          <span className={`font-bold px-3 py-1 rounded-full ${getAccuracyColor(data.accuracy_percent)}`}>
                            {data.accuracy_percent}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* By Confidence Level */}
            <div className="bg-white rounded-2xl shadow-lg p-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-3">
                <Zap className="h-7 w-7 text-yellow-600" />
                Performance by Confidence Level
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {Object.entries(stats.by_confidence_level).map(([level, data]) => (
                  <div key={level} className="bg-gray-50 rounded-xl p-6">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4 capitalize">
                      {level === 'high' && '70%+ Confidence'}
                      {level === 'medium' && '60-70% Confidence'}
                      {level === 'low' && 'Below 60% Confidence'}
                    </h3>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">Accuracy:</span>
                        <span className={`font-bold px-3 py-1 rounded-full ${getAccuracyColor(data.accuracy_percent)}`}>
                          {data.accuracy_percent}%
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">ROI:</span>
                        <span className={`font-bold ${getROIColor(data.roi_percent)}`}>
                          {data.roi_percent > 0 ? '+' : ''}{data.roi_percent}%
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">Sample:</span>
                        <span className="font-medium text-gray-900">{data.total} predictions</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* By League */}
            {stats.by_league.length > 0 && (
              <div className="bg-white rounded-2xl shadow-lg p-8">
                <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-3">
                  <Trophy className="h-7 w-7 text-yellow-600" />
                  Top Performing Leagues
                </h2>
                <div className="space-y-4">
                  {stats.by_league.map((league, index) => (
                    <div key={index} className="flex items-center justify-between p-4 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
                      <div className="flex items-center gap-4">
                        <div className="text-2xl font-bold text-gray-400 w-8">#{index + 1}</div>
                        <div>
                          <h3 className="font-semibold text-gray-900">{league.league}</h3>
                          <p className="text-sm text-gray-600">{league.correct} correct out of {league.total} predictions</p>
                        </div>
                      </div>
                      <span className={`px-4 py-2 rounded-full font-bold ${getAccuracyColor(league.accuracy_percent)}`}>
                        {league.accuracy_percent}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recent Predictions */}
            {stats.recent_predictions.length > 0 && (
              <div className="bg-white rounded-2xl shadow-lg p-8">
                <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center gap-3">
                  <Activity className="h-7 w-7 text-blue-600" />
                  Recent Predictions
                </h2>
                <div className="space-y-4">
                  {stats.recent_predictions.map((pred, index) => (
                    <div key={index} className="p-4 bg-gray-50 rounded-xl">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-3 mb-2">
                            {pred.was_correct ? (
                              <CheckCircle className="h-6 w-6 text-green-600 flex-shrink-0" />
                            ) : (
                              <XCircle className="h-6 w-6 text-red-600 flex-shrink-0" />
                            )}
                            <div>
                              <h3 className="font-semibold text-gray-900">
                                {pred.home_team} vs {pred.away_team}
                              </h3>
                              <p className="text-sm text-gray-600">{pred.league}</p>
                            </div>
                          </div>
                          <div className="ml-9 grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                            <div>
                              <span className="text-gray-600">Predicted:</span>
                              <span className="ml-2 font-medium">{pred.predicted_outcome}</span>
                            </div>
                            <div>
                              <span className="text-gray-600">Actual:</span>
                              <span className="ml-2 font-medium">{pred.actual_outcome}</span>
                            </div>
                            <div>
                              <span className="text-gray-600">Score:</span>
                              <span className="ml-2 font-medium">{pred.score || 'N/A'}</span>
                            </div>
                            <div>
                              <span className="text-gray-600">Confidence:</span>
                              <span className="ml-2 font-medium">{pred.confidence}%</span>
                            </div>
                          </div>
                        </div>
                        <div className={`text-right ml-4 ${pred.profit_loss && pred.profit_loss > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          <div className="font-bold">
                            {pred.profit_loss && pred.profit_loss > 0 ? '+' : ''}${pred.profit_loss?.toFixed(2) || '0.00'}
                          </div>
                          <div className="text-xs text-gray-500">P/L</div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Trust Badge */}
            <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl shadow-lg p-8 text-white text-center">
              <Shield className="h-16 w-16 mx-auto mb-4 opacity-90" />
              <h2 className="text-2xl font-bold mb-4">100% Transparent Tracking</h2>
              <p className="text-blue-100 max-w-2xl mx-auto mb-6">
                Every prediction is timestamped before matches start and results are automatically collected. 
                We can't fake our results - what you see is what we predicted.
              </p>
              <div className="inline-flex items-center gap-2 bg-white/20 backdrop-blur-sm px-6 py-3 rounded-full">
                <CheckCircle className="h-5 w-5" />
                <span className="font-medium">Verifiable Track Record</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

