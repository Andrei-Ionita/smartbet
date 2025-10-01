'use client'

import { useState } from 'react'
import { Recommendation } from '../src/types/recommendation'
import { ChevronDown, ChevronUp, ExternalLink, TrendingUp, TrendingDown } from 'lucide-react'

interface RecommendationCardProps {
  recommendation: Recommendation
  onViewDetails: (fixtureId: number) => void
}

export default function RecommendationCard({ recommendation, onViewDetails }: RecommendationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)

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

  const getEVBadgeColor = () => {
    if (recommendation.ev === null) return 'hidden' // Hide EV badge when not available
    if (recommendation.ev > 0) return 'bg-green-100 text-green-800'
    return 'bg-gray-100 text-gray-600'
  }

  const getEVBadgeText = () => {
    if (recommendation.ev === null) return ''
    if (recommendation.ev > 0) return `EV +${(recommendation.ev * 100).toFixed(1)}%`
    return `EV ${(recommendation.ev * 100).toFixed(1)}%`
  }

  const getOutcomeColor = (outcome: string) => {
    switch (outcome) {
      case 'Home': return 'text-blue-600'
      case 'Draw': return 'text-gray-600'
      case 'Away': return 'text-purple-600'
      default: return 'text-gray-600'
    }
  }

  const getProbabilityGap = (probabilities: { home: number; draw: number; away: number }, predictedOutcome: string) => {
    const probs = [probabilities.home, probabilities.draw, probabilities.away]
    const sortedProbs = [...probs].sort((a, b) => b - a)
    const gap = sortedProbs[0] - sortedProbs[1]
    // Probabilities are already in percentage format, so no need to multiply by 100
    return gap
  }

  return (
    <div className="group bg-white/90 backdrop-blur-sm rounded-2xl border border-gray-200/50 p-6 hover:shadow-xl transition-all duration-300 hover:border-primary-300 hover:-translate-y-1">
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-sm font-medium text-primary-600 bg-primary-50 px-3 py-1 rounded-full">
              {recommendation.league}
            </span>
            <span className="text-xs bg-gray-100 text-gray-600 px-3 py-1 rounded-full font-medium">
              {formatKickoff(recommendation.kickoff)}
            </span>
          </div>
          <h3 className="text-xl font-bold text-gray-900 group-hover:text-primary-600 transition-colors">
            {recommendation.home_team} vs {recommendation.away_team}
          </h3>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-3 hover:bg-gray-100 rounded-xl transition-all duration-200 hover:scale-110"
          aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
        >
          {isExpanded ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
        </button>
      </div>

      {/* Prediction */}
      <div className="mb-6">
        <div className="flex items-center gap-4 mb-4">
          <span className={`text-lg font-bold px-4 py-2 rounded-xl ${getOutcomeColor(recommendation.predicted_outcome)} bg-gray-50`}>
            {recommendation.predicted_outcome}
          </span>
          <div className="flex-1 bg-gray-200 rounded-full h-4 shadow-inner">
            <div
              className="bg-gradient-to-r from-primary-500 to-blue-600 h-4 rounded-full transition-all duration-500 shadow-sm"
              style={{ width: `${recommendation.confidence > 1 ? recommendation.confidence : recommendation.confidence * 100}%` }}
              aria-label={`Confidence: ${recommendation.confidence > 1 ? Math.round(recommendation.confidence) : Math.round(recommendation.confidence * 100)}%`}
            />
          </div>
          <span className="text-lg font-bold text-gray-700 min-w-[3rem] text-right">
            {recommendation.confidence > 1 ? Math.round(recommendation.confidence) : Math.round(recommendation.confidence * 100)}%
          </span>
        </div>
        
        {/* EV Badge - Only show if EV is available */}
        {recommendation.ev !== null && (
          <div className="flex items-center gap-3 mb-4">
            <span className={`text-sm px-4 py-2 rounded-xl font-semibold ${getEVBadgeColor()}`}>
              {getEVBadgeText()}
            </span>
            <span className="text-sm text-gray-500 font-medium" title="EV = probability × odds − 1">
              Expected Value
            </span>
          </div>
        )}
      </div>

      {/* Explanation */}
      <p className="text-gray-600 mb-6 leading-relaxed">
        {recommendation.explanation}
      </p>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="border-t border-gray-200 pt-6 mb-6">
          <h4 className="text-lg font-bold text-gray-900 mb-4">Full Probability Breakdown</h4>
          <div className="grid grid-cols-3 gap-6">
            <div className="text-center bg-blue-50 rounded-xl p-4">
              <div className="text-sm text-gray-600 mb-2 font-medium">Home</div>
              <div className="text-2xl font-bold text-blue-600">
                {Math.round(recommendation.probabilities.home * 100)}%
              </div>
            </div>
            <div className="text-center bg-gray-50 rounded-xl p-4">
              <div className="text-sm text-gray-600 mb-2 font-medium">Draw</div>
              <div className="text-2xl font-bold text-gray-600">
                {Math.round(recommendation.probabilities.draw * 100)}%
              </div>
            </div>
            <div className="text-center bg-purple-50 rounded-xl p-4">
              <div className="text-sm text-gray-600 mb-2 font-medium">Away</div>
              <div className="text-2xl font-bold text-purple-600">
                {Math.round(recommendation.probabilities.away * 100)}%
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-between items-center">
        <button
          onClick={() => onViewDetails(recommendation.fixture_id)}
          className="group inline-flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-xl font-semibold transition-all duration-200 hover:scale-105"
        >
          View Details
          <ExternalLink className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
        </button>
        
        <div className="flex items-center gap-2 text-sm text-gray-500 bg-gray-50 px-3 py-2 rounded-lg">
          <TrendingUp className="h-4 w-4" />
          <span className="font-medium">Gap: {Math.round(getProbabilityGap(recommendation.probabilities, recommendation.predicted_outcome))}%</span>
        </div>
      </div>
    </div>
  )
}
