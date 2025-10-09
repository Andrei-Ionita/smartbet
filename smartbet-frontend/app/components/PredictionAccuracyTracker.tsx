'use client'

import { useState, useEffect } from 'react'
import { 
  Target, 
  TrendingUp, 
  TrendingDown, 
  CheckCircle, 
  XCircle,
  BarChart3,
  Calendar,
  Trophy,
  RefreshCw
} from 'lucide-react'

interface PredictionResult {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  predicted_outcome: 'home' | 'draw' | 'away'
  prediction_confidence: number
  actual_result?: 'home' | 'draw' | 'away'
  is_correct?: boolean
  odds_used?: number
  profit_loss?: number
}

interface AccuracyStats {
  total_predictions: number
  correct_predictions: number
  accuracy_percentage: number
  total_profit_loss: number
  average_confidence: number
  best_streak: number
  current_streak: number
}

export default function PredictionAccuracyTracker() {
  const [predictions, setPredictions] = useState<PredictionResult[]>([])
  const [stats, setStats] = useState<AccuracyStats | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newResult, setNewResult] = useState<Partial<PredictionResult>>({})

  // Load predictions from localStorage
  useEffect(() => {
    const savedPredictions = localStorage.getItem('prediction_results')
    if (savedPredictions) {
      const parsed = JSON.parse(savedPredictions)
      setPredictions(parsed)
      calculateStats(parsed)
    }
    setIsLoading(false)
  }, [])

  const calculateStats = (predictionList: PredictionResult[]) => {
    const total = predictionList.length
    const correct = predictionList.filter(p => p.is_correct).length
    const accuracy = total > 0 ? (correct / total) * 100 : 0
    const totalPL = predictionList.reduce((sum, p) => sum + (p.profit_loss || 0), 0)
    const avgConfidence = total > 0 ? predictionList.reduce((sum, p) => sum + p.prediction_confidence, 0) / total : 0
    
    // Calculate streaks
    let currentStreak = 0
    let bestStreak = 0
    let tempStreak = 0
    
    for (let i = predictionList.length - 1; i >= 0; i--) {
      if (predictionList[i].is_correct) {
        currentStreak = i === predictionList.length - 1 ? 1 : currentStreak + 1
        tempStreak++
      } else {
        if (tempStreak > bestStreak) bestStreak = tempStreak
        tempStreak = 0
        if (i !== predictionList.length - 1) currentStreak = 0
      }
    }
    if (tempStreak > bestStreak) bestStreak = tempStreak

    setStats({
      total_predictions: total,
      correct_predictions: correct,
      accuracy_percentage: accuracy,
      total_profit_loss: totalPL,
      average_confidence: avgConfidence,
      best_streak: bestStreak,
      current_streak: currentStreak
    })
  }

  const addPredictionResult = (result: PredictionResult) => {
    const updated = [...predictions, result]
    setPredictions(updated)
    calculateStats(updated)
    localStorage.setItem('prediction_results', JSON.stringify(updated))
    setShowAddForm(false)
    setNewResult({})
  }

  const deletePrediction = (fixtureId: number) => {
    const updated = predictions.filter(p => p.fixture_id !== fixtureId)
    setPredictions(updated)
    calculateStats(updated)
    localStorage.setItem('prediction_results', JSON.stringify(updated))
  }

  const exportData = () => {
    const dataStr = JSON.stringify(predictions, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'prediction_accuracy_data.json'
    link.click()
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-200">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-20 bg-gray-200 rounded-xl"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-200">
        <div className="flex justify-between items-center mb-4">
          <div className="flex items-center gap-3">
            <Target className="h-6 w-6 text-primary-600" />
            <h2 className="text-xl font-bold text-gray-900">Prediction Accuracy Tracker</h2>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowAddForm(!showAddForm)}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              Add Result
            </button>
            <button
              onClick={exportData}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Export
            </button>
          </div>
        </div>

        {/* Stats Overview */}
        {stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-blue-50 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 className="h-5 w-5 text-blue-600" />
                <span className="text-sm font-medium text-blue-700">Total Predictions</span>
              </div>
              <div className="text-2xl font-bold text-blue-900">{stats.total_predictions}</div>
            </div>

            <div className="bg-green-50 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle className="h-5 w-5 text-green-600" />
                <span className="text-sm font-medium text-green-700">Accuracy</span>
              </div>
              <div className="text-2xl font-bold text-green-900">
                {stats.accuracy_percentage.toFixed(1)}%
              </div>
            </div>

            <div className={`rounded-xl p-4 ${stats.total_profit_loss >= 0 ? 'bg-green-50' : 'bg-red-50'}`}>
              <div className="flex items-center gap-2 mb-2">
                <Trophy className={`h-5 w-5 ${stats.total_profit_loss >= 0 ? 'text-green-600' : 'text-red-600'}`} />
                <span className={`text-sm font-medium ${stats.total_profit_loss >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                  P&L
                </span>
              </div>
              <div className={`text-2xl font-bold ${stats.total_profit_loss >= 0 ? 'text-green-900' : 'text-red-900'}`}>
                {stats.total_profit_loss >= 0 ? '+' : ''}${stats.total_profit_loss.toFixed(2)}
              </div>
            </div>

            <div className="bg-purple-50 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <TrendingUp className="h-5 w-5 text-purple-600" />
                <span className="text-sm font-medium text-purple-700">Current Streak</span>
              </div>
              <div className="text-2xl font-bold text-purple-900">{stats.current_streak}</div>
            </div>
          </div>
        )}
      </div>

      {/* Add Result Form */}
      {showAddForm && (
        <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Add Prediction Result</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Fixture ID</label>
              <input
                type="number"
                value={newResult.fixture_id || ''}
                onChange={(e) => setNewResult({...newResult, fixture_id: parseInt(e.target.value)})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Home Team</label>
              <input
                type="text"
                value={newResult.home_team || ''}
                onChange={(e) => setNewResult({...newResult, home_team: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Away Team</label>
              <input
                type="text"
                value={newResult.away_team || ''}
                onChange={(e) => setNewResult({...newResult, away_team: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Predicted Outcome</label>
              <select
                value={newResult.predicted_outcome || ''}
                onChange={(e) => setNewResult({...newResult, predicted_outcome: e.target.value as any})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">Select outcome</option>
                <option value="home">Home Win</option>
                <option value="draw">Draw</option>
                <option value="away">Away Win</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Actual Result</label>
              <select
                value={newResult.actual_result || ''}
                onChange={(e) => setNewResult({...newResult, actual_result: e.target.value as any})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                <option value="">Select result</option>
                <option value="home">Home Win</option>
                <option value="draw">Draw</option>
                <option value="away">Away Win</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Confidence %</label>
              <input
                type="number"
                min="0"
                max="100"
                value={newResult.prediction_confidence || ''}
                onChange={(e) => setNewResult({...newResult, prediction_confidence: parseInt(e.target.value)})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              />
            </div>
          </div>
          <div className="flex justify-end gap-3 mt-4">
            <button
              onClick={() => setShowAddForm(false)}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => {
                if (newResult.fixture_id && newResult.home_team && newResult.away_team && 
                    newResult.predicted_outcome && newResult.actual_result && newResult.prediction_confidence) {
                  const isCorrect = newResult.predicted_outcome === newResult.actual_result
                  addPredictionResult({
                    ...newResult as PredictionResult,
                    is_correct: isCorrect,
                    league: 'Unknown',
                    kickoff: new Date().toISOString()
                  })
                }
              }}
              className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              Add Result
            </button>
          </div>
        </div>
      )}

      {/* Recent Predictions */}
      <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Predictions</h3>
        {predictions.length === 0 ? (
          <div className="text-center py-8">
            <Target className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <p className="text-gray-500">No predictions tracked yet. Add your first result above!</p>
          </div>
        ) : (
          <div className="space-y-3">
            {predictions.slice(-10).reverse().map((prediction, index) => (
              <div
                key={prediction.fixture_id}
                className={`p-4 rounded-xl border ${
                  prediction.is_correct 
                    ? 'bg-green-50 border-green-200' 
                    : 'bg-red-50 border-red-200'
                }`}
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      {prediction.is_correct ? (
                        <CheckCircle className="h-4 w-4 text-green-600" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-600" />
                      )}
                      <span className="font-medium text-gray-900">
                        {prediction.home_team} vs {prediction.away_team}
                      </span>
                      <span className="text-sm text-gray-500">
                        ({prediction.league})
                      </span>
                    </div>
                    <div className="text-sm text-gray-600">
                      Predicted: <span className="font-medium">{prediction.predicted_outcome}</span> 
                      ({prediction.prediction_confidence}% confidence) → 
                      Actual: <span className="font-medium">{prediction.actual_result}</span>
                    </div>
                  </div>
                  <button
                    onClick={() => deletePrediction(prediction.fixture_id)}
                    className="text-gray-400 hover:text-red-600 transition-colors"
                  >
                    <XCircle className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
