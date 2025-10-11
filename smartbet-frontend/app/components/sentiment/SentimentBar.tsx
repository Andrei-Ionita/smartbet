'use client'

import { TrendingUp, TrendingDown, BarChart3 } from 'lucide-react'

interface SentimentBarProps {
  homeTeam: string
  awayTeam: string
  homeSentimentScore: number
  awaySentimentScore: number
  homeMentions: number
  awayMentions: number
  totalMentions: number
  className?: string
}

export default function SentimentBar({
  homeTeam,
  awayTeam,
  homeSentimentScore,
  awaySentimentScore,
  homeMentions,
  awayMentions,
  totalMentions,
  className = ''
}: SentimentBarProps) {

  const getSentimentIcon = (score: number) => {
    if (score > 0.1) return <TrendingUp className="h-4 w-4 text-green-600" />
    if (score < -0.1) return <TrendingDown className="h-4 w-4 text-red-600" />
    return <BarChart3 className="h-4 w-4 text-gray-600" />
  }

  const getSentimentColor = (score: number) => {
    if (score > 0.1) return 'text-green-600'
    if (score < -0.1) return 'text-red-600'
    return 'text-gray-600'
  }

  const getSentimentIntensity = (score: number) => {
    const absScore = Math.abs(score)
    if (absScore > 0.3) return 'Very Strong'
    if (absScore > 0.2) return 'Strong'
    if (absScore > 0.1) return 'Moderate'
    return 'Neutral'
  }

  const homeMentionRatio = totalMentions > 0 ? (homeMentions / totalMentions) * 100 : 0
  const awayMentionRatio = totalMentions > 0 ? (awayMentions / totalMentions) * 100 : 0

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-700">Public Sentiment</span>
        <span className="text-xs text-gray-500">{totalMentions} total mentions</span>
      </div>

      {/* Home Team */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {getSentimentIcon(homeSentimentScore)}
            <span className="text-sm font-medium text-gray-700">{homeTeam}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-sm font-medium ${getSentimentColor(homeSentimentScore)}`}>
              {homeSentimentScore > 0 ? '+' : ''}{(homeSentimentScore * 100).toFixed(0)}%
            </span>
            <span className="text-xs text-gray-500">
              ({getSentimentIntensity(homeSentimentScore)})
            </span>
          </div>
        </div>
        
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div 
            className="bg-blue-500 h-3 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${homeMentionRatio}%` }}
          ></div>
        </div>
        
        <div className="flex justify-between text-xs text-gray-500">
          <span>{homeMentions} mentions</span>
          <span>{homeMentionRatio.toFixed(1)}% of total</span>
        </div>
      </div>

      {/* Away Team */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {getSentimentIcon(awaySentimentScore)}
            <span className="text-sm font-medium text-gray-700">{awayTeam}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-sm font-medium ${getSentimentColor(awaySentimentScore)}`}>
              {awaySentimentScore > 0 ? '+' : ''}{(awaySentimentScore * 100).toFixed(0)}%
            </span>
            <span className="text-xs text-gray-500">
              ({getSentimentIntensity(awaySentimentScore)})
            </span>
          </div>
        </div>
        
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div 
            className="bg-purple-500 h-3 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${awayMentionRatio}%` }}
          ></div>
        </div>
        
        <div className="flex justify-between text-xs text-gray-500">
          <span>{awayMentions} mentions</span>
          <span>{awayMentionRatio.toFixed(1)}% of total</span>
        </div>
      </div>

      {/* Sentiment Legend */}
      <div className="pt-2 border-t border-gray-100">
        <div className="flex items-center gap-4 text-xs text-gray-600">
          <div className="flex items-center gap-1">
            <TrendingUp className="h-3 w-3 text-green-600" />
            <span>Positive</span>
          </div>
          <div className="flex items-center gap-1">
            <BarChart3 className="h-3 w-3 text-gray-600" />
            <span>Neutral</span>
          </div>
          <div className="flex items-center gap-1">
            <TrendingDown className="h-3 w-3 text-red-600" />
            <span>Negative</span>
          </div>
        </div>
      </div>
    </div>
  )
}
