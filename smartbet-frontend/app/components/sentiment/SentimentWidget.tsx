'use client'

import { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, Users, MessageSquare, AlertTriangle, Info, Target, BarChart3 } from 'lucide-react'

interface SentimentData {
  home_mentions: number
  away_mentions: number
  total_mentions: number
  home_sentiment_score: number
  away_sentiment_score: number
  public_attention_ratio: number
  top_keywords: string[]
  data_sources: string[]
}

interface TrapAnalysis {
  trap_score: number
  trap_level: string
  alert_message: string
  recommendation: string
  confidence_divergence: number
  is_high_risk: boolean
}

interface SentimentWidgetProps {
  matchId: number
  homeTeam: string
  awayTeam: string
  league: string
  className?: string
}

export default function SentimentWidget({ matchId, homeTeam, awayTeam, league, className = '' }: SentimentWidgetProps) {
  const [sentimentData, setSentimentData] = useState<SentimentData | null>(null)
  const [trapAnalysis, setTrapAnalysis] = useState<TrapAnalysis | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchSentimentData()
  }, [matchId])

  const fetchSentimentData = async () => {
    try {
      setLoading(true)
      setError(null)

      console.log(`🔍 Fetching sentiment data for match ${matchId}: ${homeTeam} vs ${awayTeam}`)
      
      // Fetch REAL sentiment data from Django backend
      const response = await fetch(`http://localhost:8000/api/sentiment/${matchId}/`)
      
      if (!response.ok) {
        throw new Error(`API request failed: ${response.status}`)
      }
      
      const data = await response.json()
      
      console.log(`📊 Received sentiment data for ${matchId}:`, data)
      
      if (!data.success || !data.data) {
        throw new Error('No sentiment data available for this match')
      }

      setSentimentData(data.data.sentiment)
      setTrapAnalysis(data.data.trap_analysis)
    } catch (err) {
      setError('Failed to load sentiment data')
      console.error('Error fetching sentiment data:', err)
    } finally {
      setLoading(false)
    }
  }

  const getTrapColor = (level: string) => {
    switch (level) {
      case 'extreme': return 'text-red-700 bg-red-100 border-red-200'
      case 'high': return 'text-orange-700 bg-orange-100 border-orange-200'
      case 'medium': return 'text-yellow-700 bg-yellow-100 border-yellow-200'
      case 'low': return 'text-green-700 bg-green-100 border-green-200'
      default: return 'text-gray-700 bg-gray-100 border-gray-200'
    }
  }

  const getTrapIcon = (level: string) => {
    switch (level) {
      case 'extreme': return '🚨'
      case 'high': return '⚠️'
      case 'medium': return '⚡'
      case 'low': return '✅'
      default: return 'ℹ️'
    }
  }

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

  if (loading) {
    return (
      <div className={`bg-white rounded-xl border border-gray-200 p-6 ${className}`}>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="space-y-3">
            <div className="h-3 bg-gray-200 rounded w-full"></div>
            <div className="h-3 bg-gray-200 rounded w-2/3"></div>
          </div>
        </div>
      </div>
    )
  }

  if (error || !sentimentData || !trapAnalysis) {
    return (
      <div className={`bg-white rounded-xl border border-gray-200 p-6 ${className}`}>
        <div className="flex items-center gap-2 text-gray-500 mb-2">
          <MessageSquare className="h-5 w-5" />
          <span className="font-medium">Public Sentiment Analysis</span>
        </div>
        <p className="text-sm text-gray-600">
          {error || 'No sentiment data available for this match'}
        </p>
      </div>
    )
  }

  const homeMentionRatio = sentimentData.total_mentions > 0 
    ? (sentimentData.home_mentions / sentimentData.total_mentions) * 100 
    : 0
  const awayMentionRatio = sentimentData.total_mentions > 0 
    ? (sentimentData.away_mentions / sentimentData.total_mentions) * 100 
    : 0

  console.log(`🎯 Displaying sentiment for ${homeTeam} vs ${awayTeam}:`, {
    totalMentions: sentimentData.total_mentions,
    homeMentions: sentimentData.home_mentions,
    awayMentions: sentimentData.away_mentions,
    trapLevel: trapAnalysis.trap_level,
    trapScore: trapAnalysis.trap_score
  })

  return (
    <div className={`bg-white rounded-xl border border-gray-200 p-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <MessageSquare className="h-5 w-5 text-blue-600" />
        <span className="font-semibold text-gray-900">Public Sentiment Analysis</span>
        <div className="ml-auto flex items-center gap-1">
          <Users className="h-4 w-4 text-gray-400" />
          <span className="text-sm text-gray-500">{sentimentData.total_mentions} mentions</span>
        </div>
      </div>

      {/* Trap Alert */}
      {trapAnalysis.trap_level !== 'low' && (
        <div className={`rounded-lg border p-4 mb-4 ${getTrapColor(trapAnalysis.trap_level)}`}>
          <div className="flex items-start gap-3">
            <span className="text-lg">{getTrapIcon(trapAnalysis.trap_level)}</span>
            <div className="flex-1">
              <div className="font-medium mb-1">{trapAnalysis.alert_message}</div>
              <div className="text-sm opacity-90">{trapAnalysis.recommendation}</div>
            </div>
          </div>
        </div>
      )}

      {/* Sentiment Breakdown */}
      <div className="space-y-4">
        {/* Team Mentions */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Public Attention</span>
            <span className="text-xs text-gray-500">
              {Math.round(sentimentData.public_attention_ratio * 100)}% engagement
            </span>
          </div>
          
          <div className="flex gap-2">
            {/* Home Team Bar */}
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                {getSentimentIcon(sentimentData.home_sentiment_score)}
                <span className="text-sm font-medium text-gray-700">{homeTeam}</span>
                <span className={`text-sm font-medium ${getSentimentColor(sentimentData.home_sentiment_score)}`}>
                  {sentimentData.home_sentiment_score > 0 ? '+' : ''}{(sentimentData.home_sentiment_score * 100).toFixed(0)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${homeMentionRatio}%` }}
                ></div>
              </div>
              <div className="text-xs text-gray-500 mt-1">{sentimentData.home_mentions} mentions</div>
            </div>

            {/* Away Team Bar */}
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                {getSentimentIcon(sentimentData.away_sentiment_score)}
                <span className="text-sm font-medium text-gray-700">{awayTeam}</span>
                <span className={`text-sm font-medium ${getSentimentColor(sentimentData.away_sentiment_score)}`}>
                  {sentimentData.away_sentiment_score > 0 ? '+' : ''}{(sentimentData.away_sentiment_score * 100).toFixed(0)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-purple-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${awayMentionRatio}%` }}
                ></div>
              </div>
              <div className="text-xs text-gray-500 mt-1">{sentimentData.away_mentions} mentions</div>
            </div>
          </div>
        </div>

        {/* Top Keywords */}
        {sentimentData.top_keywords.length > 0 && (
          <div>
            <div className="text-sm font-medium text-gray-700 mb-2">Key Topics</div>
            <div className="flex flex-wrap gap-2">
              {sentimentData.top_keywords.slice(0, 5).map((keyword, index) => (
                <span 
                  key={index}
                  className="px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs"
                >
                  {keyword}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Data Sources */}
        <div>
          <div className="text-sm font-medium text-gray-700 mb-2">Data Sources</div>
          <div className="flex flex-wrap gap-2">
            {sentimentData.data_sources.map((source, index) => (
              <span 
                key={index}
                className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs"
              >
                {source}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
        <div className="flex items-start gap-2">
          <Info className="h-4 w-4 text-yellow-600 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-yellow-800">
            <strong>Educational Context Only:</strong> Sentiment analysis provides insight into public opinion but should not be used to adjust betting decisions. Our predictions are based on statistical models and historical data.
          </div>
        </div>
      </div>
    </div>
  )
}
