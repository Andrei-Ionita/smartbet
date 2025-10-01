'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Calendar, Clock, TrendingUp, Target, Info } from 'lucide-react'
import { Match } from '@/lib/types'

interface MatchCardProps {
  match: Match
}

export default function MatchCard({ match }: MatchCardProps) {
  const [showDetails, setShowDetails] = useState(false)

  const getStatusColor = () => {
    if (match.prediction.isRecommended) return 'border-success-500 bg-success-50'
    if (match.prediction.confidence > 0.6) return 'border-warning-500 bg-warning-50'
    return 'border-danger-500 bg-danger-50'
  }

  const getStatusBadge = () => {
    if (match.prediction.isRecommended) {
      return <span className="badge-success">✅ Recommended</span>
    }
    if (match.prediction.confidence > 0.6) {
      return <span className="badge-warning">⚠️ High Confidence</span>
    }
    return <span className="badge-danger">❌ Low Confidence</span>
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

  return (
    <div className={`card border-l-4 ${getStatusColor()} transition-all duration-200 hover:shadow-md`}>
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-4">
        <div className="flex items-center space-x-3 mb-2 md:mb-0">
          <span className="text-2xl">{getLeagueFlag(match.league)}</span>
          <div>
            <h3 className="text-lg font-semibold text-gray-900">
              {match.homeTeam} vs {match.awayTeam}
            </h3>
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
        
        <div className="flex items-center space-x-2">
          {getStatusBadge()}
          <Link
            href={`/match/${match.id}`}
            className="text-primary-600 hover:text-primary-700 text-sm font-medium"
          >
            View Details →
          </Link>
        </div>
      </div>

      {/* Prediction Summary */}
      <div className="grid md:grid-cols-4 gap-4 mb-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-gray-900">
            {match.prediction.outcome}
          </div>
          <div className="text-sm text-gray-600">Predicted Outcome</div>
        </div>
        
        <div className="text-center">
          <div className="text-2xl font-bold text-primary-600">
            {(match.prediction.confidence * 100).toFixed(1)}%
          </div>
          <div className="text-sm text-gray-600">Confidence</div>
        </div>
        
        <div className="text-center">
          <div className={`text-2xl font-bold ${
            match.prediction.expectedValue > 0 ? 'text-success-600' : 'text-danger-600'
          }`}>
            {(match.prediction.expectedValue * 100).toFixed(1)}%
          </div>
          <div className="text-sm text-gray-600">Expected Value</div>
        </div>
        
        <div className="text-center">
          <div className="text-2xl font-bold text-warning-600">
            {match.prediction.odds[match.prediction.outcome.toLowerCase() as keyof typeof match.prediction.odds].toFixed(2)}
          </div>
          <div className="text-sm text-gray-600">Odds</div>
        </div>
      </div>

      {/* Quick Explanation */}
      <div className="mb-4">
        <div className="flex items-center space-x-2 mb-2">
          <Info className="h-4 w-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700">Quick Analysis</span>
        </div>
        <p className="text-sm text-gray-600">{match.prediction.explanation}</p>
      </div>

      {/* SHAP Features Preview */}
      <div className="mb-4">
        <div className="flex items-center space-x-2 mb-2">
          <Target className="h-4 w-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700">Key Factors</span>
        </div>
        <div className="grid md:grid-cols-2 gap-2">
          {match.prediction.shapFeatures.slice(0, 2).map((feature, index) => (
            <div key={index} className="text-sm text-gray-600">
              <span className="font-medium">{feature.feature}:</span> {feature.description}
            </div>
          ))}
        </div>
      </div>

      {/* Expandable Details */}
      <button
        onClick={() => setShowDetails(!showDetails)}
        className="w-full text-left text-sm text-primary-600 hover:text-primary-700 font-medium"
      >
        {showDetails ? 'Hide' : 'Show'} detailed analysis
      </button>

      {showDetails && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          {/* All SHAP Features */}
          <div className="mb-4">
            <h4 className="font-medium text-gray-900 mb-2">All Influencing Factors</h4>
            <div className="space-y-2">
              {match.prediction.shapFeatures.map((feature, index) => (
                <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                  <span className="text-sm font-medium">{feature.feature}</span>
                  <span className="text-sm text-gray-600">{feature.description}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Probability Distribution */}
          <div className="mb-4">
            <h4 className="font-medium text-gray-900 mb-2">Probability Distribution</h4>
            <div className="grid grid-cols-3 gap-2">
              <div className="text-center p-2 bg-gray-50 rounded">
                <div className="text-sm font-medium">Home</div>
                <div className="text-lg font-bold text-gray-900">
                  {(match.prediction.probabilities.home * 100).toFixed(1)}%
                </div>
              </div>
              <div className="text-center p-2 bg-gray-50 rounded">
                <div className="text-sm font-medium">Draw</div>
                <div className="text-lg font-bold text-gray-900">
                  {(match.prediction.probabilities.draw * 100).toFixed(1)}%
                </div>
              </div>
              <div className="text-center p-2 bg-gray-50 rounded">
                <div className="text-sm font-medium">Away</div>
                <div className="text-lg font-bold text-gray-900">
                  {(match.prediction.probabilities.away * 100).toFixed(1)}%
                </div>
              </div>
            </div>
          </div>

          {/* All Odds */}
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Market Odds</h4>
            <div className="grid grid-cols-3 gap-2">
              <div className="text-center p-2 bg-gray-50 rounded">
                <div className="text-sm font-medium">Home</div>
                <div className="text-lg font-bold text-gray-900">
                  {match.prediction.odds.home.toFixed(2)}
                </div>
              </div>
              <div className="text-center p-2 bg-gray-50 rounded">
                <div className="text-sm font-medium">Draw</div>
                <div className="text-lg font-bold text-gray-900">
                  {match.prediction.odds.draw.toFixed(2)}
                </div>
              </div>
              <div className="text-center p-2 bg-gray-50 rounded">
                <div className="text-sm font-medium">Away</div>
                <div className="text-lg font-bold text-gray-900">
                  {match.prediction.odds.away.toFixed(2)}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
} 