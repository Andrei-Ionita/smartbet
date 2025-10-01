'use client'

import { useState } from 'react'
import { Play, Target, TrendingUp, BarChart3 } from 'lucide-react'
import { leagues } from '@/lib/mockData'
import { SandboxPrediction } from '@/lib/types'

export default function SandboxPage() {
  const [formData, setFormData] = useState({
    homeTeam: '',
    awayTeam: '',
    league: ''
  })
  const [prediction, setPrediction] = useState<SandboxPrediction | null>(null)
  const [loading, setLoading] = useState(false)

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const generateMockPrediction = (homeTeam: string, awayTeam: string, league: string): SandboxPrediction => {
    // Generate realistic mock prediction
    const outcomes: ('Home' | 'Draw' | 'Away')[] = ['Home', 'Draw', 'Away']
    const outcome = outcomes[Math.floor(Math.random() * outcomes.length)]
    const confidence = 0.5 + Math.random() * 0.4 // 50-90% confidence
    const ev = (Math.random() - 0.3) * 0.4 // -12% to +28% EV

    const odds = {
      home: 1.8 + Math.random() * 1.2,
      draw: 3.0 + Math.random() * 1.0,
      away: 2.0 + Math.random() * 1.5
    }

    const probabilities = {
      home: outcome === 'Home' ? confidence : 0.25 + Math.random() * 0.3,
      draw: outcome === 'Draw' ? confidence : 0.25 + Math.random() * 0.3,
      away: outcome === 'Away' ? confidence : 0.25 + Math.random() * 0.3
    }

    // Normalize probabilities
    const total = probabilities.home + probabilities.draw + probabilities.away
    probabilities.home /= total
    probabilities.draw /= total
    probabilities.away /= total

    const explanations = {
      Home: `${homeTeam} has shown strong home form and recent head-to-head dominance against ${awayTeam}.`,
      Draw: `Both ${homeTeam} and ${awayTeam} are evenly matched with similar recent form, likely ending in a draw.`,
      Away: `${awayTeam} has been in excellent form and should capitalize on ${homeTeam}'s recent weaknesses.`
    }

    const shapFeatures = [
      {
        feature: 'Recent Form',
        impact: 0.25 + Math.random() * 0.2,
        description: `${outcome === 'Home' ? homeTeam : awayTeam} has won ${3 + Math.floor(Math.random() * 3)} of last 5 matches`
      },
      {
        feature: 'Home Advantage',
        impact: outcome === 'Home' ? 0.18 : -0.12,
        description: outcome === 'Home' ? 'Strong home record this season' : 'Away team adapts well to hostile environments'
      },
      {
        feature: 'Head-to-Head',
        impact: 0.15 + Math.random() * 0.1,
        description: `${outcome === 'Home' ? homeTeam : awayTeam} won ${2 + Math.floor(Math.random() * 3)} of last 4 meetings`
      },
      {
        feature: 'Injury Impact',
        impact: Math.random() > 0.5 ? 0.08 : -0.08,
        description: Math.random() > 0.5 ? 'Key player missing for opposition' : 'Full squad available'
      }
    ]

    return {
      match: { homeTeam, awayTeam, league },
      prediction: {
        outcome,
        confidence,
        expectedValue: ev,
        odds,
        probabilities,
        explanation: explanations[outcome],
        shapFeatures,
        isRecommended: confidence > 0.65 && ev > 0
      }
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.homeTeam || !formData.awayTeam || !formData.league) {
      alert('Please fill in all fields')
      return
    }

    setLoading(true)
    
    // Simulate API call delay
    setTimeout(() => {
      const mockPrediction = generateMockPrediction(
        formData.homeTeam,
        formData.awayTeam,
        formData.league
      )
      setPrediction(mockPrediction)
      setLoading(false)
    }, 1500)
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
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Prediction Sandbox
        </h1>
        <p className="text-gray-600">
          Test our AI prediction system with any match combination. 
          Enter team names and league to see how our models would predict the outcome.
        </p>
      </div>

      <div className="grid lg:grid-cols-2 gap-8">
        {/* Input Form */}
        <div className="card">
          <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
            <Play className="h-5 w-5 mr-2" />
            Match Input
          </h2>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="homeTeam" className="block text-sm font-medium text-gray-700 mb-2">
                Home Team
              </label>
              <input
                type="text"
                id="homeTeam"
                value={formData.homeTeam}
                onChange={(e) => handleInputChange('homeTeam', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="e.g., Arsenal"
                required
              />
            </div>

            <div>
              <label htmlFor="awayTeam" className="block text-sm font-medium text-gray-700 mb-2">
                Away Team
              </label>
              <input
                type="text"
                id="awayTeam"
                value={formData.awayTeam}
                onChange={(e) => handleInputChange('awayTeam', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="e.g., Chelsea"
                required
              />
            </div>

            <div>
              <label htmlFor="league" className="block text-sm font-medium text-gray-700 mb-2">
                League
              </label>
              <select
                id="league"
                value={formData.league}
                onChange={(e) => handleInputChange('league', e.target.value)}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500"
                required
              >
                <option value="">Select a league</option>
                {leagues.map((league) => (
                  <option key={league.id} value={league.name}>
                    {getLeagueFlag(league.name)} {league.name}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Generating Prediction...
                </div>
              ) : (
                'Generate Prediction'
              )}
            </button>
          </form>

          {/* Quick Examples */}
          <div className="mt-6 pt-6 border-t border-gray-200">
            <h3 className="text-sm font-medium text-gray-900 mb-3">Quick Examples</h3>
            <div className="space-y-2">
              {[
                { home: 'Real Madrid', away: 'Barcelona', league: 'La Liga' },
                { home: 'Bayern Munich', away: 'Dortmund', league: 'Bundesliga' },
                { home: 'Juventus', away: 'AC Milan', league: 'Serie A' }
              ].map((example, index) => (
                <button
                  key={index}
                  onClick={() => setFormData({
                    homeTeam: example.home,
                    awayTeam: example.away,
                    league: example.league
                  })}
                  className="block w-full text-left text-sm text-primary-600 hover:text-primary-700 p-2 rounded hover:bg-primary-50"
                >
                  {example.home} vs {example.away} ({example.league})
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Prediction Results */}
        <div className="card">
          <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center">
            <TrendingUp className="h-5 w-5 mr-2" />
            Prediction Results
          </h2>

          {!prediction ? (
            <div className="text-center py-12 text-gray-500">
              <BarChart3 className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>Enter match details to generate a prediction</p>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Match Info */}
              <div className="text-center p-4 bg-gray-50 rounded-lg">
                <div className="text-2xl mb-2">{getLeagueFlag(prediction.match.league)}</div>
                <h3 className="text-lg font-semibold text-gray-900">
                  {prediction.match.homeTeam} vs {prediction.match.awayTeam}
                </h3>
                <p className="text-sm text-gray-600">{prediction.match.league}</p>
              </div>

              {/* Prediction Summary */}
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-gray-900 mb-1">
                    {prediction.prediction.outcome}
                  </div>
                  <div className="text-sm text-gray-600">Predicted Outcome</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-primary-600 mb-1">
                    {(prediction.prediction.confidence * 100).toFixed(1)}%
                  </div>
                  <div className="text-sm text-gray-600">Confidence</div>
                </div>
              </div>

              {/* Value Analysis */}
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className={`text-2xl font-bold mb-1 ${
                    prediction.prediction.expectedValue > 0 ? 'text-success-600' : 'text-danger-600'
                  }`}>
                    {(prediction.prediction.expectedValue * 100).toFixed(1)}%
                  </div>
                  <div className="text-sm text-gray-600">Expected Value</div>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <div className="text-2xl font-bold text-warning-600 mb-1">
                    {prediction.prediction.odds[prediction.prediction.outcome.toLowerCase() as keyof typeof prediction.prediction.odds].toFixed(2)}
                  </div>
                  <div className="text-sm text-gray-600">Recommended Odds</div>
                </div>
              </div>

              {/* Recommendation */}
              {prediction.prediction.isRecommended && (
                <div className="p-4 bg-success-50 rounded-lg">
                  <div className="flex items-center">
                    <div className="w-2 h-2 bg-success-500 rounded-full mr-2"></div>
                    <span className="font-medium text-success-900">Recommended Bet</span>
                  </div>
                  <p className="text-sm text-success-700 mt-1">
                    High confidence with positive expected value
                  </p>
                </div>
              )}

              {/* Explanation */}
              <div>
                <h4 className="font-medium text-gray-900 mb-2 flex items-center">
                  <Target className="h-4 w-4 mr-2" />
                  Analysis
                </h4>
                <p className="text-sm text-gray-600">{prediction.prediction.explanation}</p>
              </div>

              {/* Key Factors */}
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Key Factors</h4>
                <div className="space-y-2">
                  {prediction.prediction.shapFeatures.map((feature, index) => (
                    <div key={index} className="text-sm text-gray-600">
                      <span className="font-medium">{feature.feature}:</span> {feature.description}
                    </div>
                  ))}
                </div>
              </div>

              {/* Disclaimer */}
              <div className="p-3 bg-warning-50 rounded-lg">
                <p className="text-xs text-warning-800">
                  ⚠️ This is a simulation using mock data. Real predictions will be available 
                  when the season resumes with live match data and updated models.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
} 