'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, TrendingUp, Target, BarChart3, Calendar, Clock } from 'lucide-react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { Match } from '@/lib/types'
import { getMatchById } from '@/lib/mockData'

export default function MatchDetailPage() {
  const params = useParams()
  const router = useRouter()
  const [match, setMatch] = useState<Match | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const matchId = params.matchId as string
    const foundMatch = getMatchById(matchId)
    setMatch(foundMatch || null)
    setLoading(false)
  }, [params.matchId])

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="card text-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading match details...</p>
        </div>
      </div>
    )
  }

  if (!match) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="card text-center py-12">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Match Not Found</h2>
          <p className="text-gray-600 mb-6">The requested match could not be found.</p>
          <button
            onClick={() => router.back()}
            className="btn-primary"
          >
            Go Back
          </button>
        </div>
      </div>
    )
  }

  const getLeagueFlag = (league: string) => {
    const flags: { [key: string]: string } = {
      'Premier League': '🏴󠁧󠁢󠁥󠁮󠁧󠁿',
      'La Liga': '🇪🇸',
      'Serie A': '🇮🇹',
      'Bundesliga': '🇩🇪',
      'Ligue 1': '🇫🇷'
    }
    return flags[league] || '⚽'
  }

  const getStatusColor = () => {
    if (match.prediction.isRecommended) return 'border-success-500 bg-success-50'
    if (match.prediction.confidence > 0.6) return 'border-warning-500 bg-warning-50'
    return 'border-danger-500 bg-danger-50'
  }

  const getStatusBadge = () => {
    if (match.prediction.isRecommended) {
      return <span className="badge-success">✅ Recommended Bet</span>
    }
    if (match.prediction.confidence > 0.6) {
      return <span className="badge-warning">⚠️ High Confidence</span>
    }
    return <span className="badge-danger">❌ Low Confidence</span>
  }

  // Prepare data for pie chart
  const pieData = [
    { name: 'Home Win', value: match.prediction.probabilities.home * 100, color: '#3b82f6' },
    { name: 'Draw', value: match.prediction.probabilities.draw * 100, color: '#f59e0b' },
    { name: 'Away Win', value: match.prediction.probabilities.away * 100, color: '#ef4444' }
  ]

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => router.back()}
          className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 mb-4"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Predictions</span>
        </button>
        
        <div className={`card border-l-4 ${getStatusColor()}`}>
          <div className="flex flex-col md:flex-row md:items-center md:justify-between">
            <div className="flex items-center space-x-3 mb-4 md:mb-0">
              <span className="text-3xl">{getLeagueFlag(match.league)}</span>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">
                  {match.homeTeam} vs {match.awayTeam}
                </h1>
                <div className="flex items-center space-x-4 text-sm text-gray-600">
                  <div className="flex items-center space-x-1">
                    <Calendar className="h-4 w-4" />
                    <span>{new Date(match.date).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Clock className="h-4 w-4" />
                    <span>{match.time}</span>
                  </div>
                </div>
              </div>
            </div>
            {getStatusBadge()}
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Left Column - Prediction Summary */}
        <div className="space-y-6">
          {/* Main Prediction */}
          <div className="card">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Prediction Summary</h2>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <div className="text-3xl font-bold text-gray-900 mb-1">
                  {match.prediction.outcome}
                </div>
                <div className="text-sm text-gray-600">Predicted Outcome</div>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <div className="text-3xl font-bold text-primary-600 mb-1">
                  {(match.prediction.confidence * 100).toFixed(1)}%
                </div>
                <div className="text-sm text-gray-600">Confidence</div>
              </div>
            </div>
          </div>

          {/* Expected Value & Odds */}
          <div className="card">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Value Analysis</h2>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <div className={`text-3xl font-bold mb-1 ${
                  match.prediction.expectedValue > 0 ? 'text-success-600' : 'text-danger-600'
                }`}>
                  {(match.prediction.expectedValue * 100).toFixed(1)}%
                </div>
                <div className="text-sm text-gray-600">Expected Value</div>
              </div>
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <div className="text-3xl font-bold text-warning-600 mb-1">
                  {match.prediction.odds[match.prediction.outcome.toLowerCase() as keyof typeof match.prediction.odds].toFixed(2)}
                </div>
                <div className="text-sm text-gray-600">Recommended Odds</div>
              </div>
            </div>
            
            <div className="grid grid-cols-3 gap-2">
              <div className="text-center p-2 bg-gray-50 rounded">
                <div className="text-sm font-medium">Home</div>
                <div className="text-lg font-bold">{match.prediction.odds.home.toFixed(2)}</div>
              </div>
              <div className="text-center p-2 bg-gray-50 rounded">
                <div className="text-sm font-medium">Draw</div>
                <div className="text-lg font-bold">{match.prediction.odds.draw.toFixed(2)}</div>
              </div>
              <div className="text-center p-2 bg-gray-50 rounded">
                <div className="text-sm font-medium">Away</div>
                <div className="text-lg font-bold">{match.prediction.odds.away.toFixed(2)}</div>
              </div>
            </div>
          </div>

          {/* SHAP Features */}
          <div className="card">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
              <Target className="h-5 w-5 mr-2" />
              Key Influencing Factors
            </h2>
            <div className="space-y-3">
              {match.prediction.shapFeatures.map((feature, index) => (
                <div key={index} className="p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-medium text-gray-900">{feature.feature}</span>
                    <span className="text-sm text-gray-600">
                      Impact: {(feature.impact * 100).toFixed(1)}%
                    </span>
                  </div>
                  <p className="text-sm text-gray-600">{feature.description}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column - Charts & Analysis */}
        <div className="space-y-6">
          {/* Probability Distribution Chart */}
          <div className="card">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
              <BarChart3 className="h-5 w-5 mr-2" />
              Probability Distribution
            </h2>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    formatter={(value: number) => [`${value.toFixed(1)}%`, 'Probability']}
                    labelFormatter={(label) => `${label}`}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-3 gap-2 mt-4">
              {pieData.map((item, index) => (
                <div key={index} className="flex items-center space-x-2">
                  <div 
                    className="w-3 h-3 rounded-full" 
                    style={{ backgroundColor: item.color }}
                  ></div>
                  <span className="text-sm text-gray-600">{item.name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Detailed Explanation */}
          <div className="card">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
              <TrendingUp className="h-5 w-5 mr-2" />
              Detailed Analysis
            </h2>
            <p className="text-gray-700 leading-relaxed mb-4">
              {match.prediction.explanation}
            </p>
            
            <div className="space-y-3">
              <div className="p-3 bg-blue-50 rounded-lg">
                <h4 className="font-medium text-blue-900 mb-1">Model Performance</h4>
                <p className="text-sm text-blue-700">
                  This prediction is based on our {match.league} model which has been trained on historical data 
                  and market patterns specific to this league.
                </p>
              </div>
              
              {match.prediction.isRecommended && (
                <div className="p-3 bg-success-50 rounded-lg">
                  <h4 className="font-medium text-success-900 mb-1">Betting Recommendation</h4>
                  <p className="text-sm text-success-700">
                    This match meets our criteria for a recommended bet with high confidence 
                    and positive expected value.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Risk Assessment */}
          <div className="card">
            <h2 className="text-xl font-bold text-gray-900 mb-4">Risk Assessment</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <span className="text-sm font-medium">Confidence Level</span>
                <span className={`text-sm font-medium ${
                  match.prediction.confidence > 0.7 ? 'text-success-600' :
                  match.prediction.confidence > 0.5 ? 'text-warning-600' : 'text-danger-600'
                }`}>
                  {match.prediction.confidence > 0.7 ? 'High' :
                   match.prediction.confidence > 0.5 ? 'Medium' : 'Low'}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <span className="text-sm font-medium">Expected Value</span>
                <span className={`text-sm font-medium ${
                  match.prediction.expectedValue > 0 ? 'text-success-600' : 'text-danger-600'
                }`}>
                  {match.prediction.expectedValue > 0 ? 'Positive' : 'Negative'}
                </span>
              </div>
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                <span className="text-sm font-medium">Market Efficiency</span>
                <span className="text-sm font-medium text-gray-600">Standard</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
} 