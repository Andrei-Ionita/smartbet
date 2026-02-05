'use client'

import { useState, useEffect } from 'react'
import { Recommendation } from '../../src/types/recommendation'
import { X, Calculator, DollarSign, TrendingUp, AlertTriangle, Target, Save, Copy, Lock } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import Link from 'next/link'

interface BettingCalculatorModalProps {
  recommendation: Recommendation
  isOpen: boolean
  onClose: () => void
}

interface BettingStrategy {
  id: string
  name: string
  description: string
  color: string
  bgColor: string
}

interface StakeCalculation {
  strategy: string
  stake: number
  potentialWin: number
  potentialLoss: number
  roi: number
  risk: 'Low' | 'Medium' | 'High'
}

export default function BettingCalculatorModal({ recommendation, isOpen, onClose }: BettingCalculatorModalProps) {
  const { isPro, isAuthenticated } = useAuth()
  const [bankroll, setBankroll] = useState(1000)
  const [customStake, setCustomStake] = useState(0)
  const [selectedStrategy, setSelectedStrategy] = useState('kelly')
  const [savedScenarios, setSavedScenarios] = useState<Array<{
    id: string
    name: string
    bankroll: number
    stake: number
    strategy: string
    timestamp: string
  }>>([])

  const strategies: BettingStrategy[] = [
    {
      id: 'kelly',
      name: 'Kelly Criterion',
      description: 'Optimal stake based on probability and odds',
      color: 'text-blue-600',
      bgColor: 'bg-blue-50'
    },
    {
      id: 'fixed_percent',
      name: 'Fixed Percentage',
      description: 'Fixed percentage of bankroll (1-5%)',
      color: 'text-green-600',
      bgColor: 'bg-green-50'
    },
    {
      id: 'conservative',
      name: 'Conservative',
      description: 'Half Kelly or 1% bankroll (whichever is lower)',
      color: 'text-yellow-600',
      bgColor: 'bg-yellow-50'
    },
    {
      id: 'aggressive',
      name: 'Aggressive',
      description: 'Double Kelly (use with caution)',
      color: 'text-red-600',
      bgColor: 'bg-red-50'
    }
  ]

  // Calculate Kelly Criterion
  const calculateKelly = (probability: number, odds: number): number => {
    if (!odds || odds <= 0) return 0
    const b = odds - 1 // Net odds received on the wager
    const p = probability / 100 // Probability of winning
    const q = 1 - p // Probability of losing
    const kelly = (b * p - q) / b
    return Math.max(0, kelly) // Don't bet if Kelly is negative
  }

  // Calculate stake based on selected strategy
  const calculateStake = (strategy: string, bankroll: number): StakeCalculation => {
    const odds = recommendation.odds || 0
    const confidence = recommendation.confidence
    let stake = 0
    let risk: 'Low' | 'Medium' | 'High' = 'Medium'

    switch (strategy) {
      case 'kelly':
        const kellyPercent = calculateKelly(confidence, odds)
        stake = kellyPercent * bankroll
        risk = kellyPercent > 0.05 ? 'High' : kellyPercent > 0.02 ? 'Medium' : 'Low'
        break

      case 'fixed_percent':
        stake = bankroll * 0.02 // 2% fixed
        risk = 'Low'
        break

      case 'conservative':
        const kellyStake = calculateKelly(confidence, odds) * bankroll
        const fixedStake = bankroll * 0.01
        stake = Math.min(kellyStake * 0.5, fixedStake) // Half Kelly or 1%
        risk = 'Low'
        break

      case 'aggressive':
        const fullKelly = calculateKelly(confidence, odds) * bankroll
        stake = fullKelly * 2 // Double Kelly
        risk = 'High'
        break

      default:
        stake = 0
    }

    // Cap at 25% of bankroll for safety
    stake = Math.min(stake, bankroll * 0.25)

    const potentialWin = stake * (odds - 1)
    const potentialLoss = stake
    const roi = odds > 0 ? (potentialWin / potentialLoss) * 100 : 0

    return {
      strategy: strategies.find(s => s.id === strategy)?.name || 'Custom',
      stake: Math.round(stake * 100) / 100,
      potentialWin: Math.round(potentialWin * 100) / 100,
      potentialLoss: Math.round(potentialLoss * 100) / 100,
      roi: Math.round(roi * 100) / 100,
      risk
    }
  }

  const currentCalculation = calculateStake(selectedStrategy, bankroll)
  const customCalculation = customStake > 0 ? {
    strategy: 'Custom',
    stake: customStake,
    potentialWin: customStake * ((recommendation.odds || 0) - 1),
    potentialLoss: customStake,
    roi: recommendation.odds ? ((customStake * ((recommendation.odds || 0) - 1)) / customStake) * 100 : 0,
    risk: 'Medium' as const
  } : null

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'Low': return 'text-green-600 bg-green-100'
      case 'Medium': return 'text-yellow-600 bg-yellow-100'
      case 'High': return 'text-red-600 bg-red-100'
      default: return 'text-gray-600 bg-gray-100'
    }
  }

  const saveScenario = () => {
    const scenario = {
      id: Date.now().toString(),
      name: `${recommendation.home_team} vs ${recommendation.away_team}`,
      bankroll,
      stake: customStake || currentCalculation.stake,
      strategy: selectedStrategy,
      timestamp: new Date().toLocaleString()
    }
    setSavedScenarios(prev => [scenario, ...prev.slice(0, 4)]) // Keep last 5 scenarios
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
  }

  if (!isOpen) return null

  // Pro Gate: Show upgrade prompt for non-Pro users
  if (!isPro) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
        <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-8">
          <div className="flex justify-end">
            <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-lg">
              <X className="h-5 w-5 text-gray-500" />
            </button>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-gradient-to-br from-violet-500 to-purple-600 rounded-full flex items-center justify-center">
              <Lock className="w-8 h-8 text-white" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">
              Betting Calculator is a Pro Feature
            </h3>
            <p className="text-gray-600 mb-6">
              Unlock the betting calculator with Kelly Criterion, stake recommendations,
              and ROI analysis for just <span className="font-bold text-violet-600">€5/month</span>.
            </p>
            {isAuthenticated ? (
              <Link
                href="/pricing"
                className="inline-block w-full py-3 px-6 bg-gradient-to-r from-violet-600 to-purple-600 text-white font-semibold rounded-lg hover:from-violet-700 hover:to-purple-700 transition-all"
              >
                Upgrade to Pro - €5/month
              </Link>
            ) : (
              <>
                <Link
                  href="/register"
                  className="inline-block w-full py-3 px-6 bg-gradient-to-r from-violet-600 to-purple-600 text-white font-semibold rounded-lg hover:from-violet-700 hover:to-purple-700 transition-all"
                >
                  Sign Up for Pro - €5/month
                </Link>
                <p className="text-sm text-gray-500 mt-3">
                  Already have an account?{' '}
                  <Link href="/login" className="text-violet-600 hover:underline font-medium">Log in</Link>
                </p>
              </>
            )}
            <div className="mt-6 pt-4 border-t border-gray-200 text-left">
              <p className="text-xs text-gray-500 mb-2">Pro includes:</p>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex items-center gap-1"><span className="text-green-500">✓</span> Kelly Criterion</div>
                <div className="flex items-center gap-1"><span className="text-green-500">✓</span> All predictions</div>
                <div className="flex items-center gap-1"><span className="text-green-500">✓</span> Real-time access</div>
                <div className="flex items-center gap-1"><span className="text-green-500">✓</span> Email alerts</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Calculator className="h-6 w-6 text-blue-600" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-gray-900">Betting Calculator</h2>
              <p className="text-sm text-gray-600">
                {recommendation.home_team} vs {recommendation.away_team}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="h-5 w-5 text-gray-500" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Match Info */}
          <div className="bg-gray-50 rounded-xl p-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">Prediction:</span>
                <span className="ml-2 font-semibold">{recommendation.predicted_outcome}</span>
              </div>
              <div>
                <span className="text-gray-600">Confidence:</span>
                <span className="ml-2 font-semibold">{recommendation.confidence}%</span>
              </div>
              <div>
                <span className="text-gray-600">Odds:</span>
                <span className="ml-2 font-semibold">{recommendation.odds || 'N/A'}</span>
              </div>
              <div>
                <span className="text-gray-600">Expected Value:</span>
                <span className="ml-2 font-semibold">
                  {recommendation.ev ? `${recommendation.ev.toFixed(1)}%` : 'N/A'}
                </span>
              </div>
            </div>
          </div>

          {/* Bankroll Input */}
          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-700">Bankroll ($)</label>
            <div className="relative">
              <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="number"
                value={bankroll}
                onChange={(e) => setBankroll(Number(e.target.value))}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter your bankroll"
                min="0"
                step="0.01"
              />
            </div>
          </div>

          {/* Strategy Selection */}
          <div className="space-y-3">
            <label className="text-sm font-semibold text-gray-700">Stake Strategy</label>
            <div className="grid grid-cols-2 gap-3">
              {strategies.map((strategy) => (
                <button
                  key={strategy.id}
                  onClick={() => setSelectedStrategy(strategy.id)}
                  className={`p-3 rounded-lg border-2 transition-all ${selectedStrategy === strategy.id
                      ? `border-blue-500 ${strategy.bgColor}`
                      : 'border-gray-200 hover:border-gray-300'
                    }`}
                >
                  <div className="text-left">
                    <div className={`font-medium ${strategy.color}`}>{strategy.name}</div>
                    <div className="text-xs text-gray-600 mt-1">{strategy.description}</div>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Custom Stake Input */}
          <div className="space-y-2">
            <label className="text-sm font-semibold text-gray-700">Custom Stake ($) - Optional</label>
            <input
              type="number"
              value={customStake || ''}
              onChange={(e) => setCustomStake(Number(e.target.value) || 0)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Enter custom stake amount"
              min="0"
              step="0.01"
            />
          </div>

          {/* Calculation Results */}
          <div className="bg-blue-50 rounded-xl p-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Calculation Results</h3>

            {customCalculation ? (
              <div className="space-y-4">
                <div className="bg-white rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-medium text-gray-700">Custom Stake</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRiskColor(customCalculation.risk)}`}>
                      {customCalculation.risk} Risk
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Stake:</span>
                      <span className="ml-2 font-semibold">${customCalculation.stake}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Potential Win:</span>
                      <span className="ml-2 font-semibold text-green-600">${customCalculation.potentialWin}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Potential Loss:</span>
                      <span className="ml-2 font-semibold text-red-600">${customCalculation.potentialLoss}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">ROI:</span>
                      <span className="ml-2 font-semibold">{customCalculation.roi}%</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="bg-white rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-medium text-gray-700">{currentCalculation.strategy}</span>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getRiskColor(currentCalculation.risk)}`}>
                      {currentCalculation.risk} Risk
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600">Recommended Stake:</span>
                      <span className="ml-2 font-semibold text-blue-600">${currentCalculation.stake}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Potential Win:</span>
                      <span className="ml-2 font-semibold text-green-600">${currentCalculation.potentialWin}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">Potential Loss:</span>
                      <span className="ml-2 font-semibold text-red-600">${currentCalculation.potentialLoss}</span>
                    </div>
                    <div>
                      <span className="text-gray-600">ROI:</span>
                      <span className="ml-2 font-semibold">{currentCalculation.roi}%</span>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Risk Warning */}
          {currentCalculation.risk === 'High' && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-red-600 mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold text-red-800">High Risk Warning</h4>
                  <p className="text-sm text-red-700 mt-1">
                    This stake size is considered high risk. Consider using a more conservative strategy
                    or reducing your stake size to protect your bankroll.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={saveScenario}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              <Save className="h-4 w-4" />
              Save Scenario
            </button>
            <button
              onClick={() => copyToClipboard(`Stake: $${(customStake || currentCalculation.stake).toFixed(2)}, Potential Win: $${(customCalculation?.potentialWin || currentCalculation.potentialWin).toFixed(2)}, Risk: ${customCalculation?.risk || currentCalculation.risk}`)}
              className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors font-medium"
            >
              <Copy className="h-4 w-4" />
              Copy Details
            </button>
          </div>

          {/* Saved Scenarios */}
          {savedScenarios.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-gray-700">Recent Scenarios</h3>
              <div className="space-y-2">
                {savedScenarios.slice(0, 3).map((scenario) => (
                  <div key={scenario.id} className="bg-gray-50 rounded-lg p-3 text-sm">
                    <div className="flex justify-between items-start">
                      <div>
                        <div className="font-medium">{scenario.name}</div>
                        <div className="text-gray-600">Stake: ${scenario.stake} • {scenario.strategy}</div>
                      </div>
                      <div className="text-xs text-gray-500">{scenario.timestamp}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
