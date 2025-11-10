'use client'

import { useState } from 'react'
import { Recommendation } from '../../src/types/recommendation'
import { ChevronDown, ChevronUp, ExternalLink, TrendingUp, TrendingDown, Target, AlertTriangle, CheckCircle, Calculator } from 'lucide-react'
import BettingCalculatorModal from './BettingCalculatorModal'

interface RecommendationCardProps {
  recommendation: Recommendation
  onViewDetails: (fixtureId: number) => void
}

export default function RecommendationCard({ recommendation, onViewDetails }: RecommendationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isCalculatorOpen, setIsCalculatorOpen] = useState(false)

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
    const evPercent = recommendation.ev * 100
    if (evPercent > 0) return `EV +${evPercent.toFixed(1)}%`
    return `EV ${evPercent.toFixed(1)}%`
  }

  const getOutcomeColor = (outcome: string) => {
    switch (outcome) {
      case 'Home': return 'text-blue-600'
      case 'Draw': return 'text-gray-600'
      case 'Away': return 'text-purple-600'
      default: return 'text-gray-600'
    }
  }

  const getPredictionStrength = (probabilities: { home: number; draw: number; away: number }) => {
    const probs = [probabilities.home * 100, probabilities.draw * 100, probabilities.away * 100]
    const sortedProbs = [...probs].sort((a, b) => b - a)
    const gap = sortedProbs[0] - sortedProbs[1]
    
    // Convert gap to user-friendly strength indicator
    if (gap >= 30) return { label: 'Very Strong', color: 'text-green-700', bgColor: 'bg-green-100' }
    if (gap >= 20) return { label: 'Strong', color: 'text-blue-700', bgColor: 'bg-blue-100' }
    if (gap >= 10) return { label: 'Moderate', color: 'text-yellow-700', bgColor: 'bg-yellow-100' }
    return { label: 'Weak', color: 'text-red-700', bgColor: 'bg-red-100' }
  }

  // Calculate Kelly Criterion for optimal stake sizing
  const calculateKellyStake = (probability: number, odds: number, bankroll: number = 1000) => {
    if (!odds || odds <= 0 || !probability || probability <= 0) {
      return 0
    }
    
    const b = odds - 1 // Net odds received on the wager
    const p = probability // Probability of winning (already as decimal 0-1)
    const q = 1 - p // Probability of losing
    const kelly = (b * p - q) / b
    
    // Only return positive Kelly values (profitable bets)
    if (kelly <= 0) {
      return 0
    }
    
    // Apply Kelly fraction to bankroll with reasonable cap
    const kellyStake = kelly * bankroll
    
    // Cap at 40% of bankroll for safety, allowing more realistic variation
    return Math.min(kellyStake, bankroll * 0.40)
  }

  // Get risk level based on confidence and EV - adjusted for "best bets" context
  const getRiskLevel = () => {
    const confidence = recommendation.confidence * 100 // Convert to percentage
    const ev = (recommendation.ev || 0) * 100 // Convert to percentage
    
    // Since these are filtered "best bets" with high EV, adjust risk assessment
    // High EV + decent confidence = Good opportunity, not high risk
    if (confidence >= 70 && ev >= 15) return { level: 'Low Risk', color: 'text-green-600', bgColor: 'bg-green-100', icon: CheckCircle }
    if (confidence >= 60 && ev >= 10) return { level: 'Medium Risk', color: 'text-yellow-600', bgColor: 'bg-yellow-100', icon: AlertTriangle }
    if (confidence >= 55 && ev >= 5) return { level: 'Good Value', color: 'text-blue-600', bgColor: 'bg-blue-100', icon: CheckCircle }
    if (ev >= 20) return { level: 'High Value', color: 'text-green-600', bgColor: 'bg-green-100', icon: CheckCircle }
    if (ev >= 10) return { level: 'Good Value', color: 'text-blue-600', bgColor: 'bg-blue-100', icon: CheckCircle }
    return { level: 'Moderate Risk', color: 'text-orange-600', bgColor: 'bg-orange-100', icon: AlertTriangle }
  }

  // Visual probability bar component
  const ProbabilityBar = ({ label, percentage, color, isSelected }: { label: string; percentage: number; color: string; isSelected: boolean }) => (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className={`font-medium ${isSelected ? 'text-gray-900' : 'text-gray-600'}`}>{label}</span>
        <span className={`font-mono ${isSelected ? 'text-gray-900' : 'text-gray-600'}`}>{percentage.toFixed(1)}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div 
          className={`h-2 rounded-full transition-all duration-300 ${color} ${isSelected ? 'ring-2 ring-blue-400' : ''}`}
          style={{ width: `${percentage}%` }}
        ></div>
      </div>
    </div>
  );

  return (
    <div className="group bg-white/95 backdrop-blur-sm rounded-xl border border-gray-200/60 p-5 hover:shadow-lg transition-all duration-300 hover:border-primary-300 hover:-translate-y-1 h-full">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-medium text-primary-600 bg-primary-50 px-3 py-1 rounded-full">
              {recommendation.league}
            </span>
            <span className="text-xs bg-gray-100 text-gray-600 px-3 py-1 rounded-full font-medium">
              {formatKickoff(recommendation.kickoff)}
            </span>
          </div>
          <h3 className="text-lg font-bold text-gray-900 group-hover:text-primary-600 transition-colors leading-tight">
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
              style={{ width: `${recommendation.confidence * 100}%` }}
              aria-label={`Confidence: ${Math.round(recommendation.confidence * 100)}%`}
            />
          </div>
          <span className="text-lg font-bold text-gray-700 min-w-[3rem] text-right">
            {Math.round(recommendation.confidence * 100)}%
          </span>
        </div>
        
        {/* Key Betting Metrics */}
        <div className="mb-4">
          <div className="flex items-center justify-between p-4 bg-gradient-to-r from-green-50 to-blue-50 rounded-xl border border-green-200 mb-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">+{((recommendation.ev || 0) * 100).toFixed(1)}%</div>
              <div className="text-xs text-green-700">Expected Value</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{Math.round(recommendation.confidence * 100)}%</div>
              <div className="text-xs text-blue-700">Confidence</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-600">{
                recommendation.odds_data && recommendation.predicted_outcome.toLowerCase() === 'home' ? recommendation.odds_data?.home?.toFixed(2) :
                recommendation.odds_data && recommendation.predicted_outcome.toLowerCase() === 'draw' ? recommendation.odds_data?.draw?.toFixed(2) :
                recommendation.odds_data && recommendation.predicted_outcome.toLowerCase() === 'away' ? recommendation.odds_data?.away?.toFixed(2) : 'N/A'
              }</div>
              <div className="text-xs text-purple-700">Best Odds</div>
            </div>
          </div>
          
        </div>

        {/* Risk Warnings */}
        {(recommendation.confidence * 100 < 60 || (recommendation.ev || 0) * 100 < 10 || 
          recommendation.predicted_outcome === 'Draw') && (
          <div className="mb-4 p-3 bg-orange-50 border-2 border-orange-300 rounded-lg">
            <div className="flex items-start gap-2">
              <span className="text-orange-600 text-lg">⚠️</span>
              <div className="flex-1">
                <p className="text-sm font-semibold text-orange-900 mb-1">Risk Factors Present</p>
                <ul className="text-xs text-orange-800 space-y-1">
                  {recommendation.confidence * 100 < 60 && (
                    <li>• Lower confidence ({(recommendation.confidence * 100).toFixed(1)}%) - higher uncertainty</li>
                  )}
                  {(recommendation.ev || 0) * 100 < 10 && (
                    <li>• Low expected value ({((recommendation.ev || 0) * 100).toFixed(1)}%) - small edge</li>
                  )}
                  {recommendation.predicted_outcome === 'Draw' && (
                    <li>• Draw prediction - historically harder to predict accurately</li>
                  )}
                </ul>
                <p className="text-xs text-orange-900 mt-2 font-medium">
                  💡 Consider: Reduced stake, skip if uncertain, or wait for higher quality bets
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Personalized Stake Recommendation */}
        {recommendation.stake_recommendation && (
          <div className="mb-4 p-4 bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl border-2 border-purple-300">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <Calculator className="h-5 w-5 text-purple-600" />
                <span className="font-semibold text-purple-900">Recommended Stake</span>
              </div>
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                recommendation.stake_recommendation.risk_level === 'low' ? 'bg-green-100 text-green-700' :
                recommendation.stake_recommendation.risk_level === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                'bg-orange-100 text-orange-700'
              }`}>
                {recommendation.stake_recommendation.risk_level} risk
              </span>
            </div>
            <div className="flex items-baseline gap-2 mb-2">
              <span className="text-3xl font-bold text-purple-900">
                {recommendation.stake_recommendation.currency} ${recommendation.stake_recommendation.recommended_stake.toFixed(2)}
              </span>
              <span className="text-sm text-purple-700">
                ({recommendation.stake_recommendation.stake_percentage.toFixed(1)}% of bankroll)
              </span>
            </div>
            <p className="text-xs text-purple-700 mb-2">
              {recommendation.stake_recommendation.risk_explanation}
            </p>
            {recommendation.stake_recommendation.warnings.length > 0 && (
              <div className="mt-2 pt-2 border-t border-purple-200">
                {recommendation.stake_recommendation.warnings.map((warning, idx) => (
                  <p key={idx} className="text-xs text-orange-700 flex items-start gap-1">
                    <AlertTriangle className="h-3 w-3 mt-0.5 flex-shrink-0" />
                    <span>{warning}</span>
                  </p>
                ))}
              </div>
            )}
            <p className="text-xs text-purple-600 mt-2 italic">
              Using {recommendation.stake_recommendation.strategy.replace('_', ' ')} strategy
            </p>
          </div>
        )}
        
        {/* Quick Odds Comparison */}
        {recommendation.odds_data && (
          <div className="grid grid-cols-3 gap-2 mb-4">
            <div className={`p-3 rounded-lg border-2 transition-all duration-200 ${recommendation.predicted_outcome === 'Home' ? 'border-blue-500 bg-blue-50 shadow-sm' : 'border-gray-200 hover:border-gray-300'}`}>
              <div className="text-xs text-gray-600 mb-1">Home</div>
              <div className="text-lg font-bold text-blue-600">{recommendation.odds_data?.home?.toFixed(2) || 'N/A'}</div>
              <div className="text-xs text-gray-500 mt-1">{recommendation.bookmaker || 'Unknown'}</div>
              {recommendation.predicted_outcome === 'Home' && <div className="text-xs text-blue-600 font-medium mt-1 px-2 py-0.5 bg-blue-100 rounded-full">RECOMMENDED</div>}
            </div>
            <div className={`p-3 rounded-lg border-2 transition-all duration-200 ${recommendation.predicted_outcome === 'Draw' ? 'border-gray-500 bg-gray-50 shadow-sm' : 'border-gray-200 hover:border-gray-300'}`}>
              <div className="text-xs text-gray-600 mb-1">Draw</div>
              <div className="text-lg font-bold text-gray-600">{recommendation.odds_data?.draw?.toFixed(2) || 'N/A'}</div>
              <div className="text-xs text-gray-500 mt-1">{recommendation.bookmaker || 'Unknown'}</div>
              {recommendation.predicted_outcome === 'Draw' && <div className="text-xs text-gray-600 font-medium mt-1 px-2 py-0.5 bg-gray-100 rounded-full">RECOMMENDED</div>}
            </div>
            <div className={`p-3 rounded-lg border-2 transition-all duration-200 ${recommendation.predicted_outcome === 'Away' ? 'border-purple-500 bg-purple-50 shadow-sm' : 'border-gray-200 hover:border-gray-300'}`}>
              <div className="text-xs text-gray-600 mb-1">Away</div>
              <div className="text-lg font-bold text-purple-600">{recommendation.odds_data?.away?.toFixed(2) || 'N/A'}</div>
              <div className="text-xs text-gray-500 mt-1">{recommendation.bookmaker || 'Unknown'}</div>
              {recommendation.predicted_outcome === 'Away' && <div className="text-xs text-purple-600 font-medium mt-1 px-2 py-0.5 bg-purple-100 rounded-full">RECOMMENDED</div>}
            </div>
          </div>
        )}
        
      </div>


      {/* Enhanced Visual Probability Bars */}
      {recommendation.probabilities && (
        <div className="mb-4">
          <div className="space-y-2">
            <ProbabilityBar 
              label="Home" 
              percentage={Math.min(recommendation.probabilities.home * 100, 100)} 
              color="bg-blue-500" 
              isSelected={recommendation.predicted_outcome === 'Home'} 
            />
            <ProbabilityBar 
              label="Draw" 
              percentage={Math.min(recommendation.probabilities.draw * 100, 100)} 
              color="bg-gray-500" 
              isSelected={recommendation.predicted_outcome === 'Draw'} 
            />
            <ProbabilityBar 
              label="Away" 
              percentage={Math.min(recommendation.probabilities.away * 100, 100)} 
              color="bg-purple-500" 
              isSelected={recommendation.predicted_outcome === 'Away'} 
            />
          </div>
        </div>
      )}

          {/* Risk Level & Quick Actions */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              {(() => {
                const risk = getRiskLevel()
                const Icon = risk.icon
                return (
                  <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${risk.bgColor}`}>
                    <Icon className={`h-4 w-4 ${risk.color}`} />
                    <span className={`text-sm font-medium ${risk.color}`}>{risk.level}</span>
                  </div>
                )
              })()}
              <div className={`px-3 py-1 rounded-full ${
                recommendation.signal_quality === 'Strong' ? 'bg-green-100' :
                recommendation.signal_quality === 'Good' ? 'bg-blue-100' :
                recommendation.signal_quality === 'Moderate' ? 'bg-yellow-100' : 'bg-red-100'
              }`}>
                <span className={`text-sm font-medium ${
                  recommendation.signal_quality === 'Strong' ? 'text-green-700' :
                  recommendation.signal_quality === 'Good' ? 'text-blue-700' :
                  recommendation.signal_quality === 'Moderate' ? 'text-yellow-700' : 'text-red-700'
                }`}>
                  {recommendation.signal_quality || 'Weak'} Signal
                </span>
              </div>
            </div>
                 <button
                   onClick={() => setIsCalculatorOpen(true)}
                   className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                 >
                   <Calculator className="h-4 w-4" />
                   Calculate Stake
                 </button>
      </div>

          {/* League Accuracy Badge */}
          {recommendation.league_accuracy && (
            <div className="mb-6">
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-xl p-4 border border-blue-200">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <Target className="h-5 w-5 text-blue-600" />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-semibold text-gray-700">
                        {recommendation.league} Performance
                      </span>
                      <span className={`px-2 py-1 rounded-full text-xs font-bold ${
                        recommendation.league_accuracy.accuracy_percent >= 65 
                          ? 'text-green-700 bg-green-100' 
                          : recommendation.league_accuracy.accuracy_percent >= 55
                          ? 'text-yellow-700 bg-yellow-100'
                          : 'text-red-700 bg-red-100'
                      }`}>
                        {recommendation.league_accuracy.accuracy_percent}% accuracy
                      </span>
                    </div>
                    <div className="text-xs text-gray-600">
                      {recommendation.league_accuracy.correct_predictions} correct out of {recommendation.league_accuracy.total_predictions} predictions
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

      {/* Expanded Betting Details */}
      {isExpanded && (
        <div className="border-t border-gray-200 pt-6 mb-6">
          <h4 className="text-lg font-bold text-gray-900 mb-4">Betting Analysis</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-gray-50 rounded-xl p-4">
              <h5 className="text-sm font-semibold text-gray-700 mb-3">💰 Recommended Stake</h5>
              <div className="space-y-2">
                {recommendation.odds_data && 
                 ((recommendation.predicted_outcome.toLowerCase() === 'home' && recommendation.odds_data?.home) ||
                  (recommendation.predicted_outcome.toLowerCase() === 'draw' && recommendation.odds_data?.draw) ||
                  (recommendation.predicted_outcome.toLowerCase() === 'away' && recommendation.odds_data?.away)) && (
                  <div className="bg-white rounded-lg p-3 border border-gray-200">
                    <div className="text-xs text-gray-600 mb-1">Optimal Bet Size (Kelly Criterion)</div>
                    <div className="text-lg font-bold text-green-600">
                      ${(() => {
                        if (!recommendation.probabilities) return '0.00'
                        const outcome = recommendation.predicted_outcome.toLowerCase()
                        const probability = recommendation.probabilities[outcome as keyof typeof recommendation.probabilities]
                        const odds = outcome === 'home' ? recommendation.odds_data?.home! :
                                    outcome === 'draw' ? recommendation.odds_data?.draw! :
                                    recommendation.odds_data?.away!
                        
                        return calculateKellyStake(probability, odds).toFixed(2)
                      })()}
                    </div>
                    <div className="text-xs text-gray-500">Based on $1000 bankroll</div>
                  </div>
                )}
                <div className="bg-white rounded-lg p-3 border border-gray-200">
                  <div className="text-xs text-gray-600 mb-1">Risk Assessment</div>
                  <div className={`text-sm font-semibold ${
                    (() => {
                      const risk = getRiskLevel()
                      return risk.color
                    })()
                  }`}>
                    {(() => {
                      const risk = getRiskLevel()
                      return risk.level
                    })()}
                  </div>
                  <div className="text-xs text-gray-500">
                    {(() => {
                      const confidence = recommendation.confidence
                      const ev = recommendation.ev || 0
                      if (confidence >= 70 && ev >= 15) return 'High confidence with excellent value'
                      if (confidence >= 60 && ev >= 10) return 'Good confidence with solid value'
                      if (confidence >= 55 && ev >= 5) return 'Decent confidence with good value'
                      if (ev >= 20) return 'High value opportunity'
                      if (ev >= 10) return 'Good value opportunity'
                      return 'Moderate confidence bet'
                    })()}
                  </div>
                </div>
              </div>
            </div>
            <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-4 border border-blue-100">
              <h5 className="text-sm font-semibold text-blue-800 mb-3 flex items-center gap-2">
                <span className="text-lg">📊</span>
                Quick Insights
              </h5>
              
              {/* Key Betting Information */}
              <div className="space-y-3">
                <div className="bg-white rounded-lg p-3 border border-blue-200">
                  <div className="text-xs text-gray-600 mb-1">Prediction Summary</div>
                  <div className="text-sm text-gray-700 leading-relaxed">
                    {recommendation.explanation}
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-3">
                <div className="bg-white rounded-lg p-3 border border-blue-200">
                  <div className="text-xs text-gray-600 mb-1">Prediction Strength</div>
                  <div className={`text-sm font-semibold ${
                    recommendation.debug_info?.variance === 'Low' ? 'text-green-600' :
                    recommendation.debug_info?.variance === 'Medium' ? 'text-yellow-600' : 'text-red-600'
                  }`}>
                    {recommendation.debug_info?.variance === 'Low' ? 'High Confidence' :
                     recommendation.debug_info?.variance === 'Medium' ? 'Medium Confidence' : 'Low Confidence'}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {recommendation.debug_info?.model_consensus ? 
                      `Variance: ${(recommendation.debug_info.model_consensus.variance * 100).toFixed(2)}%` :
                      'Model agreement analysis'
                    }
                  </div>
                </div>
                  
                <div className="bg-white rounded-lg p-3 border border-blue-200">
                  <div className="text-xs text-gray-600 mb-1">Market Consensus</div>
                  <div className="text-sm font-semibold text-blue-600">
                    {recommendation.debug_info?.prediction_agreement || 'Unknown Agreement'}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {recommendation.debug_info?.model_consensus ? 
                      `Consensus: ${(recommendation.debug_info.model_consensus.home * 100).toFixed(1)}% Home` :
                      'Multiple model analysis'
                    }
                  </div>
                </div>
                </div>
                
                <div className="bg-white rounded-lg p-3 border border-blue-200">
                  <div className="text-xs text-gray-600 mb-1">Betting Edge</div>
                  <div className="text-sm font-semibold text-green-600">
                    {recommendation.ev && recommendation.ev > 0 ? `+${recommendation.ev.toFixed(1)}% Edge` : 'Negative Edge'}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {recommendation.ev && recommendation.ev > 20 ? 'Excellent Value' : 
                     recommendation.ev && recommendation.ev > 10 ? 'Good Value' : 
                     recommendation.ev && recommendation.ev > 0 ? 'Marginal Value' : 'Poor Value'} • Kelly: ${(() => {
                       if (!recommendation.probabilities) return '0'
                       const probability = recommendation.predicted_outcome === 'Home' ? recommendation.probabilities.home :
                                        recommendation.predicted_outcome === 'Draw' ? recommendation.probabilities.draw :
                                        recommendation.probabilities.away
                       const odds = recommendation.predicted_outcome === 'Home' ? recommendation.odds_data?.home :
                                   recommendation.predicted_outcome === 'Draw' ? recommendation.odds_data?.draw :
                                   recommendation.odds_data?.away
                       if (!odds || !probability) return '0'
                       const kelly = ((odds * probability) - 1) / (odds - 1)
                       const stake = Math.min(kelly * 1000, 400)
                       return stake.toFixed(0)
                     })()}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-between items-center mt-4">
        <button
          onClick={() => onViewDetails(recommendation.fixture_id)}
          className="group inline-flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-xl font-semibold transition-all duration-200 hover:scale-105"
        >
          View Details
          <ExternalLink className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
        </button>
        
            <div className={`flex items-center gap-2 text-sm px-3 py-2 rounded-lg font-medium ${
              recommendation.signal_quality === 'Strong' ? 'bg-green-100 text-green-700' :
              recommendation.signal_quality === 'Good' ? 'bg-blue-100 text-blue-700' :
              recommendation.signal_quality === 'Moderate' ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'
            }`}>
              <TrendingUp className="h-4 w-4" />
              <span>{recommendation.signal_quality || 'Weak'}</span>
            </div>
      </div>

      {/* Betting Calculator Modal */}
      <BettingCalculatorModal
        recommendation={recommendation}
        isOpen={isCalculatorOpen}
        onClose={() => setIsCalculatorOpen(false)}
      />
    </div>
  )
}
