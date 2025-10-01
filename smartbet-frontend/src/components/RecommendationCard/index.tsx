'use client'

import { useState } from 'react'
import { Recommendation } from '@/types/recommendation'
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

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 hover:shadow-lg transition-all duration-200 hover:border-blue-200">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm text-gray-500">{recommendation.league}</span>
            <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
              {formatKickoff(recommendation.kickoff)}
            </span>
          </div>
          <h3 className="text-lg font-semibold text-gray-900">
            {recommendation.home_team} vs {recommendation.away_team}
          </h3>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
        >
          {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        </button>
      </div>

      {/* Prediction */}
      <div className="mb-4">
        <div className="flex items-center gap-3 mb-2">
          <span className={`font-medium ${getOutcomeColor(recommendation.predicted_outcome)}`}>
            {recommendation.predicted_outcome}
          </span>
          <div className="flex-1 bg-gray-200 rounded-full h-3">
            <div
              className="bg-gradient-to-r from-blue-500 to-blue-600 h-3 rounded-full transition-all duration-300"
              style={{ width: `${recommendation.confidence * 100}%` }}
              aria-label={`Confidence: ${Math.round(recommendation.confidence * 100)}%`}
            />
          </div>
          <span className="text-sm font-medium text-gray-600">
            {Math.round(recommendation.confidence * 100)}%
          </span>
        </div>
        
        {/* EV Badge - Only show if EV is available */}
        {recommendation.ev !== null && (
          <div className="flex items-center gap-2 mb-3">
            <span className={`text-xs px-3 py-1 rounded-full font-medium ${getEVBadgeColor()}`}>
              {getEVBadgeText()}
            </span>
            <span className="text-xs text-gray-500" title="EV = probability × odds − 1">
              Expected Value
            </span>
          </div>
        )}
      </div>

      {/* Explanation */}
      <p className="text-sm text-gray-600 mb-4">
        {recommendation.explanation}
      </p>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="border-t pt-4 mb-4">
          <h4 className="text-sm font-medium text-gray-900 mb-3">Full Probability Breakdown</h4>
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-sm text-gray-500 mb-1">Home</div>
              <div className="text-lg font-semibold text-blue-600">
                {Math.round(recommendation.probabilities.home * 100)}%
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-500 mb-1">Draw</div>
              <div className="text-lg font-semibold text-gray-600">
                {Math.round(recommendation.probabilities.draw * 100)}%
              </div>
            </div>
            <div className="text-center">
              <div className="text-sm text-gray-500 mb-1">Away</div>
              <div className="text-lg font-semibold text-purple-600">
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
          className="inline-flex items-center gap-2 text-blue-600 hover:text-blue-800 text-sm font-medium transition-colors"
        >
          View details
          <ExternalLink className="h-4 w-4" />
        </button>
        
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <TrendingUp className="h-3 w-3" />
          Score: {Math.round(recommendation.score * 100)}
        </div>
      </div>
    </div>
  )
}
