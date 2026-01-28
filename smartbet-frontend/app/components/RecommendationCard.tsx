'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Recommendation } from '../../src/types/recommendation'
import { ChevronDown, ChevronUp, ExternalLink, TrendingUp, TrendingDown, Target, AlertTriangle, CheckCircle, Calculator, ArrowRight, Lock, Info } from 'lucide-react'
import BettingCalculatorModal from './BettingCalculatorModal'
import BettingAcknowledgmentModal from './BettingAcknowledgmentModal'
import { generateMatchSlug } from '../../src/utils/seo-helpers'

import { useLanguage } from '../contexts/LanguageContext'

interface RecommendationCardProps {
  recommendation: Recommendation
  onViewDetails?: (fixtureId: number) => void
}

export default function RecommendationCard({ recommendation, onViewDetails }: RecommendationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const [isCalculatorOpen, setIsCalculatorOpen] = useState(false)
  const [showConfidenceTooltip, setShowConfidenceTooltip] = useState(false)
  const [showAcknowledgment, setShowAcknowledgment] = useState(false)
  const { t, language } = useLanguage()

  // Handler to open calculator - checks for acknowledgment first
  const handleOpenCalculator = () => {
    // Check if already acknowledged in this session
    const acknowledged = typeof window !== 'undefined' && sessionStorage.getItem('betting_acknowledged')
    if (acknowledged) {
      setIsCalculatorOpen(true)
    } else {
      setShowAcknowledgment(true)
    }
  }

  const handleAcknowledgmentConfirm = () => {
    setShowAcknowledgment(false)
    setIsCalculatorOpen(true)
  }

  const matchSlug = generateMatchSlug(
    recommendation.home_team,
    recommendation.away_team,
    recommendation.kickoff,
    recommendation.fixture_id,
    recommendation.league
  )

  // Calculate time until kickoff and time since prediction was logged
  const getTimeStatus = () => {
    const now = new Date()
    const kickoff = new Date(recommendation.kickoff)
    const hoursUntilKickoff = Math.floor((kickoff.getTime() - now.getTime()) / (1000 * 60 * 60))
    const isLocked = hoursUntilKickoff > 0 // Prediction is locked if match hasn't started

    // Format the time display
    let timeText = ''
    if (hoursUntilKickoff > 24) {
      const days = Math.floor(hoursUntilKickoff / 24)
      timeText = language === 'ro' ? `în ${days} zile` : `in ${days} days`
    } else if (hoursUntilKickoff > 0) {
      timeText = language === 'ro' ? `în ${hoursUntilKickoff}h` : `in ${hoursUntilKickoff}h`
    } else {
      timeText = language === 'ro' ? 'Live' : 'Live'
    }

    return { isLocked, hoursUntilKickoff, timeText }
  }

  // Get confidence breakdown explanation
  const getConfidenceBreakdown = () => {
    const modelCount = recommendation.ensemble_info?.model_count || recommendation.debug_info?.model_count || 3
    const consensus = recommendation.ensemble_info?.consensus || 0
    const variance = recommendation.debug_info?.variance || 'Medium'
    const ev = ((recommendation.ev || 0) * 100).toFixed(1)

    return {
      modelCount,
      modelAgreement: consensus > 0.8 ? 'Strong' : consensus > 0.6 ? 'Moderate' : 'Mixed',
      variance: typeof variance === 'string' ? variance : variance < 0.1 ? 'Low' : variance < 0.2 ? 'Medium' : 'High',
      evValue: ev,
      signalQuality: recommendation.signal_quality || 'Good'
    }
  }

  // Generate data-driven "Why This Pick" explanation
  const getWhyThisPick = () => {
    const reasons: string[] = []
    const confidence = recommendation.confidence * 100
    const ev = (recommendation.ev || 0) * 100
    const outcome = recommendation.predicted_outcome

    // Form-based reasons
    const homeForm = recommendation.teams_data?.home?.form
    const awayForm = recommendation.teams_data?.away?.form

    if (homeForm && typeof homeForm === 'string') {
      const wins = (homeForm.match(/W/g) || []).length
      if (outcome === 'Home' && wins >= 3) {
        reasons.push(language === 'ro'
          ? `${recommendation.home_team} are ${wins} victorii din ultimele 5 meciuri`
          : `${recommendation.home_team} has ${wins} wins in last 5 matches`)
      }
    }

    if (awayForm && typeof awayForm === 'string') {
      const wins = (awayForm.match(/W/g) || []).length
      if (outcome === 'Away' && wins >= 3) {
        reasons.push(language === 'ro'
          ? `${recommendation.away_team} are ${wins} victorii din ultimele 5 meciuri`
          : `${recommendation.away_team} has ${wins} wins in last 5 matches`)
      }
    }

    // Confidence-based reason
    if (confidence >= 70) {
      reasons.push(language === 'ro'
        ? 'Încredere ridicată: toate modelele AI sunt de acord'
        : 'High confidence: all AI models agree')
    } else if (confidence >= 60) {
      reasons.push(language === 'ro'
        ? 'Acord majoritar între modele AI'
        : 'Majority agreement across AI models')
    }

    // Value-based reason
    if (ev >= 15) {
      reasons.push(language === 'ro'
        ? `Valoare excelentă detectată (+${ev.toFixed(0)}% EV)`
        : `Excellent value detected (+${ev.toFixed(0)}% EV)`)
    } else if (ev >= 10) {
      reasons.push(language === 'ro'
        ? `Valoare bună la cote (+${ev.toFixed(0)}% EV)`
        : `Good odds value (+${ev.toFixed(0)}% EV)`)
    }

    // Signal quality reason
    if (recommendation.signal_quality === 'Strong') {
      reasons.push(language === 'ro'
        ? 'Semnal puternic: varianță scăzută între modele'
        : 'Strong signal: low variance across models')
    }

    // If no specific reasons, provide a generic one
    if (reasons.length === 0) {
      reasons.push(language === 'ro'
        ? `Predicție bazată pe analiză statistică și ${getConfidenceBreakdown().modelCount} modele AI`
        : `Prediction based on statistical analysis and ${getConfidenceBreakdown().modelCount} AI models`)
    }

    return reasons.slice(0, 3) // Return max 3 reasons
  }

  const timeStatus = getTimeStatus()


  const formatKickoff = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString(language === 'ro' ? 'ro-RO' : 'en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: language === 'en'
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

  // Get opportunity level based on confidence and EV
  // Combines prediction confidence with betting value to categorize opportunities
  const getOpportunityLevel = () => {
    // Priority 1: Use backend Two-Track label if available
    if (recommendation.bet_type) {
      if (recommendation.bet_type === 'safe') return {
        level: t('card.badges.safe_pick') || recommendation.bet_label || 'Safe Pick',
        color: 'text-green-600',
        bgColor: 'bg-green-100',
        icon: CheckCircle
      }
      if (recommendation.bet_type === 'value') return {
        level: t('card.badges.value_bet') || recommendation.bet_label || 'Value Bet',
        color: 'text-blue-600',
        bgColor: 'bg-blue-100',
        icon: TrendingUp
      }
    }

    const confidence = recommendation.confidence * 100 // Convert to percentage
    const ev = (recommendation.ev || 0) * 100 // Convert to percentage

    // Premium: High confidence + excellent value
    if (confidence >= 70 && ev >= 15) return {
      level: t('card.badges.premium'),
      color: 'text-green-600',
      bgColor: 'bg-green-100',
      icon: CheckCircle,
      description: 'High confidence with excellent value'
    }

    // Strong: Good confidence + good value
    if (confidence >= 60 && ev >= 10) return {
      level: t('card.badges.strong'),
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
      icon: CheckCircle,
      description: 'Good confidence with solid value'
    }

    // High Value: Exceptional EV regardless of confidence
    if (ev >= 20) return {
      level: t('card.badges.highValue'),
      color: 'text-purple-600',
      bgColor: 'bg-purple-100',
      icon: TrendingUp,
      description: 'Exceptional betting value detected'
    }

    // Good Value: Positive EV with reasonable confidence
    if (confidence >= 55 && ev >= 5) return {
      level: t('card.badges.goodValue'),
      color: 'text-blue-600',
      bgColor: 'bg-blue-100',
      icon: CheckCircle,
      description: 'Positive value with moderate confidence'
    }

    // Value Play: Good EV but lower confidence
    if (ev >= 10) return {
      level: t('card.badges.valuePlay'),
      color: 'text-cyan-600',
      bgColor: 'bg-cyan-100',
      icon: TrendingUp,
      description: 'Good value but higher uncertainty'
    }

    // Speculative: Lower confidence/value - proceed with caution
    return {
      level: t('card.badges.speculative'),
      color: 'text-orange-600',
      bgColor: 'bg-orange-100',
      icon: AlertTriangle,
      description: 'Lower confidence or value - smaller stakes recommended'
    }
  }

  // Helper for replacing placeholders in translation strings
  const formatString = (str: string, ...args: (string | number)[]) => {
    return str.replace(/{(\d+)}/g, (match, number) => {
      return typeof args[number] !== 'undefined' ? String(args[number]) : match;
    });
  };

  // ... (ProbabilityBar component remains same)

  return (
    <div className="group bg-white/95 backdrop-blur-sm rounded-xl border border-gray-200/60 p-5 hover:shadow-lg transition-all duration-300 hover:border-primary-300 hover:-translate-y-1 h-full">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        {/* ... (Team names logic remains same) */}
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className="text-sm font-medium text-primary-600 bg-primary-50 px-3 py-1 rounded-full">
              {recommendation.league}
            </span>
            <span className="text-xs bg-gray-100 text-gray-600 px-3 py-1 rounded-full font-medium">
              {formatKickoff(recommendation.kickoff)}
            </span>
            {/* Prediction Lock Badge - Shows prediction is locked before kickoff */}
            {timeStatus.isLocked && (
              <span className="text-xs font-medium px-2.5 py-1 rounded-full flex items-center gap-1.5 bg-emerald-100 text-emerald-700 border border-emerald-200">
                <Lock className="h-3 w-3" />
                {language === 'ro' ? 'Predicție blocată' : 'Locked'} • {timeStatus.timeText}
              </span>
            )}
            {/* Best Market Badge */}
            {recommendation.best_market && recommendation.best_market.type !== '1x2' && (
              <span className="text-xs font-medium px-2.5 py-1 rounded-full flex items-center gap-1.5 bg-gradient-to-r from-blue-500 to-indigo-500 text-white shadow-sm">
                <Target className="h-3 w-3" />
                {t('card.multiMarket.bestMarket')}: {recommendation.best_market.name}
              </span>
            )}
            {/* AI Model Agreement Dots */}
            {recommendation.confidence > 0 && (
              <span
                className="text-xs font-medium px-2.5 py-1 rounded-full flex items-center gap-1.5 bg-purple-50 text-purple-700 border border-purple-200"
                title={language === 'ro'
                  ? `${getConfidenceBreakdown().modelCount}/3 modele AI sunt de acord`
                  : `${getConfidenceBreakdown().modelCount}/3 AI models agree`}
              >
                <span className="flex gap-0.5">
                  {[...Array(3)].map((_, i) => (
                    <span
                      key={i}
                      className={`w-2 h-2 rounded-full ${i < getConfidenceBreakdown().modelCount
                        ? 'bg-purple-500'
                        : 'bg-purple-200'
                        }`}
                    />
                  ))}
                </span>
                <span className="text-[10px]">AI</span>
              </span>
            )}
          </div>
          <h3 className="text-lg font-bold text-gray-900 group-hover:text-primary-600 transition-colors leading-tight flex items-center gap-2">
            <Link href={matchSlug} className="flex items-center gap-2 hover:underline decoration-primary-300 decoration-2">
              <span className="flex items-center gap-1">
                {recommendation.home_team}
              </span>
              <span className="text-gray-400 text-sm">vs</span>
              <span className="flex items-center gap-1">
                {recommendation.away_team}
              </span>
            </Link>
          </h3>
        </div>
        {/* ... (Expand button remains same) */}
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
        {recommendation.confidence > 0 ? (
          <>
            <div className="flex items-center gap-4 mb-4">
              <span className={`text-lg font-bold px-4 py-2 rounded-xl ${getOutcomeColor(recommendation.predicted_outcome)} bg-gray-50`}>
                {recommendation.predicted_outcome === 'Home' ? t('card.outcomes.home') :
                  recommendation.predicted_outcome === 'Draw' ? t('card.outcomes.draw') :
                    recommendation.predicted_outcome === 'Away' ? t('card.outcomes.away') : recommendation.predicted_outcome}
              </span>
              <div className="flex-1">
                {/* Main confidence bar */}
                <div className="bg-gray-200 rounded-full h-4 shadow-inner mb-1">
                  <div
                    className="bg-gradient-to-r from-primary-500 to-blue-600 h-4 rounded-full transition-all duration-500 shadow-sm"
                    style={{ width: `${recommendation.confidence * 100}%` }}
                    aria-label={`Confidence: ${Math.round(recommendation.confidence * 100)}%`}
                  />
                </div>
                {/* Confidence interval indicator */}
                {recommendation.prediction_info?.confidence_interval && (
                  <div className="text-xs text-gray-500 flex items-center justify-between px-1">
                    <span>{recommendation.prediction_info.confidence_interval.lower_bound.toFixed(1)}%</span>
                    <span className="text-gray-400">95% CI</span>
                    <span>{recommendation.prediction_info.confidence_interval.upper_bound.toFixed(1)}%</span>
                  </div>
                )}
              </div>
              {/* Confidence with Info Tooltip */}
              <div className="relative">
                <button
                  onClick={() => setShowConfidenceTooltip(!showConfidenceTooltip)}
                  className="flex items-center gap-1 text-lg font-bold text-gray-700 min-w-[4rem] text-right hover:text-primary-600 transition-colors"
                  aria-label="Show confidence breakdown"
                >
                  {Math.round(recommendation.confidence * 100)}%
                  <Info className="h-4 w-4 text-gray-400 hover:text-primary-500" />
                </button>

                {/* Confidence Breakdown Tooltip */}
                {showConfidenceTooltip && (
                  <div className="absolute right-0 top-full mt-2 z-50 w-64 bg-white rounded-xl shadow-xl border border-gray-200 p-4 text-left">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-bold text-gray-900">
                        {language === 'ro' ? 'Cum am calculat' : 'How we calculated this'}
                      </span>
                      <button
                        onClick={() => setShowConfidenceTooltip(false)}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        ×
                      </button>
                    </div>
                    <div className="space-y-2 text-xs">
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">{language === 'ro' ? 'Acord modele AI' : 'AI Model Agreement'}</span>
                        <span className="font-medium text-gray-900 flex items-center gap-1">
                          {getConfidenceBreakdown().modelCount}/3
                          <span className={`px-1.5 py-0.5 rounded text-[10px] ${getConfidenceBreakdown().modelAgreement === 'Strong' ? 'bg-green-100 text-green-700' :
                            getConfidenceBreakdown().modelAgreement === 'Moderate' ? 'bg-yellow-100 text-yellow-700' :
                              'bg-orange-100 text-orange-700'
                            }`}>
                            {getConfidenceBreakdown().modelAgreement}
                          </span>
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">{language === 'ro' ? 'Valoare așteptată' : 'Expected Value'}</span>
                        <span className="font-medium text-green-600">+{getConfidenceBreakdown().evValue}%</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">{language === 'ro' ? 'Variație predicții' : 'Prediction Variance'}</span>
                        <span className={`font-medium ${getConfidenceBreakdown().variance === 'Low' ? 'text-green-600' :
                          getConfidenceBreakdown().variance === 'Medium' ? 'text-yellow-600' :
                            'text-red-600'
                          }`}>{getConfidenceBreakdown().variance}</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">{language === 'ro' ? 'Calitate semnal' : 'Signal Quality'}</span>
                        <span className={`font-medium ${getConfidenceBreakdown().signalQuality === 'Strong' ? 'text-green-600' :
                          getConfidenceBreakdown().signalQuality === 'Good' ? 'text-blue-600' :
                            'text-yellow-600'
                          }`}>{getConfidenceBreakdown().signalQuality}</span>
                      </div>
                    </div>
                    <div className="mt-3 pt-2 border-t border-gray-100">
                      <p className="text-[10px] text-gray-500">
                        {language === 'ro'
                          ? 'Bazat pe consens între 3 modele AI și date statistice'
                          : 'Based on consensus across 3 AI models and statistical data'}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Recent Form Section */}
            {(recommendation.teams_data?.home?.form || recommendation.teams_data?.away?.form) && (
              <div className="mb-4 bg-gray-50 rounded-lg p-3 border border-gray-200">
                <div className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">{t('card.recentForm')}</div>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-700 truncate max-w-[100px]">{recommendation.home_team}</span>
                    <div className="flex gap-0.5">
                      {(() => {
                        const formRaw = recommendation.teams_data?.home?.form
                        const formArray = (Array.isArray(formRaw) ? formRaw : typeof formRaw === 'string' ? formRaw.split('') : []) as string[]
                        return formArray.length > 0 ? formArray.slice(0, 5).map((item: any, i: number) => {
                          const res = typeof item === 'object' && item?.form ? item.form : item
                          return (
                            <span key={i} className={`w-5 h-5 flex items-center justify-center text-[10px] font-bold rounded ${res === 'W' ? 'bg-green-100 text-green-700' :
                              res === 'L' ? 'bg-red-100 text-red-700' :
                                'bg-gray-100 text-gray-600'
                              }`}>{res}</span>
                          )
                        }) : <span className="text-xs text-gray-400">N/A</span>
                      })()}
                    </div>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-gray-700 truncate max-w-[100px]">{recommendation.away_team}</span>
                    <div className="flex gap-0.5">
                      {(() => {
                        const formRaw = recommendation.teams_data?.away?.form
                        const formArray = (Array.isArray(formRaw) ? formRaw : typeof formRaw === 'string' ? formRaw.split('') : []) as string[]
                        return formArray.length > 0 ? formArray.slice(0, 5).map((item: any, i: number) => {
                          const res = typeof item === 'object' && item?.form ? item.form : item
                          return (
                            <span key={i} className={`w-5 h-5 flex items-center justify-center text-[10px] font-bold rounded ${res === 'W' ? 'bg-green-100 text-green-700' :
                              res === 'L' ? 'bg-red-100 text-red-700' :
                                'bg-gray-100 text-gray-600'
                              }`}>{res}</span>
                          )
                        }) : <span className="text-xs text-gray-400">N/A</span>
                      })()}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Why This Pick Section - Data-driven explanations */}
            <div className="mb-4 p-3 bg-gradient-to-r from-amber-50 to-yellow-50 rounded-lg border border-amber-200">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-amber-600">💡</span>
                <span className="text-xs font-bold text-amber-800 uppercase tracking-wide">
                  {language === 'ro' ? 'De ce această predicție' : 'Why This Pick'}
                </span>
              </div>
              <ul className="space-y-1">
                {getWhyThisPick().map((reason, idx) => (
                  <li key={idx} className="text-xs text-amber-900 flex items-start gap-2">
                    <span className="text-amber-500 mt-0.5">•</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="mb-4">
              <div className="flex items-center justify-between p-4 bg-gradient-to-r from-green-50 to-blue-50 rounded-xl border border-green-200 mb-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">+{((recommendation.ev || 0) * 100).toFixed(1)}%</div>
                  <div className="text-xs text-green-700">{t('card.expectedValue')}</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">{Math.round(recommendation.confidence * 100)}%</div>
                  <div className="text-xs text-blue-700">{t('card.confidence')}</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-purple-600">{
                    // Use recommendation.odds first (contains best_market.odds for multi-market)
                    recommendation.odds && recommendation.odds > 1 ? recommendation.odds.toFixed(2) :
                      // Fallback to odds_data for 1X2 markets
                      recommendation.odds_data && recommendation.predicted_outcome.toLowerCase() === 'home' ? recommendation.odds_data?.home?.toFixed(2) :
                        recommendation.odds_data && recommendation.predicted_outcome.toLowerCase() === 'draw' ? recommendation.odds_data?.draw?.toFixed(2) :
                          recommendation.odds_data && recommendation.predicted_outcome.toLowerCase() === 'away' ? recommendation.odds_data?.away?.toFixed(2) : 'N/A'
                  }</div>
                  <div className="text-xs text-purple-700 truncate max-w-[100px] mx-auto">
                    {recommendation.bookmaker && recommendation.bookmaker !== 'Unknown'
                      ? recommendation.bookmaker
                      : recommendation.odds_data?.bookmaker && recommendation.odds_data.bookmaker !== 'Unknown'
                        ? recommendation.odds_data.bookmaker
                        : recommendation.best_market?.bookmaker
                          ? recommendation.best_market.bookmaker
                          : recommendation.odds_data?.home_bookmaker
                            ? recommendation.odds_data.home_bookmaker
                            : t('card.bestOdds')}
                  </div>
                </div>
              </div>

              {/* Edge vs Market Comparison */}
              {recommendation.odds_data && (
                <div className="flex items-center justify-between p-3 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg border border-indigo-200">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-indigo-700">
                      {language === 'ro' ? 'Edge vs Piață' : 'Edge vs Market'}
                    </span>
                  </div>
                  <div className="flex items-center gap-3 text-xs">
                    {(() => {
                      const outcome = recommendation.predicted_outcome.toLowerCase()
                      const odds = outcome === 'home' ? recommendation.odds_data?.home :
                        outcome === 'draw' ? recommendation.odds_data?.draw :
                          recommendation.odds_data?.away
                      if (!odds) return null

                      const marketImplied = (1 / odds) * 100
                      const aiProb = recommendation.confidence * 100
                      const edge = aiProb - marketImplied

                      return (
                        <>
                          <span className="text-gray-600">
                            {language === 'ro' ? 'Piață' : 'Market'}: <span className="font-medium text-gray-800">{marketImplied.toFixed(0)}%</span>
                          </span>
                          <span className="text-gray-400">vs</span>
                          <span className="text-gray-600">
                            AI: <span className="font-medium text-indigo-700">{aiProb.toFixed(0)}%</span>
                          </span>
                          <span className={`px-2 py-0.5 rounded-full font-bold ${edge > 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-600'
                            }`}>
                            {edge > 0 ? '+' : ''}{edge.toFixed(0)}%
                          </span>
                        </>
                      )
                    })()}
                  </div>
                </div>
              )}
            </div>

            {/* Risk Warnings */}
            {(recommendation.confidence * 100 < 60 || (recommendation.ev || 0) * 100 < 10 ||
              recommendation.predicted_outcome === 'Draw') && (
                <div className="mb-4 p-3 bg-orange-50 border-2 border-orange-300 rounded-lg">
                  <div className="flex items-start gap-2">
                    <span className="text-orange-600 text-lg">⚠️</span>
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-orange-900 mb-1">{t('card.risk.title')}</p>
                      <ul className="text-xs text-orange-800 space-y-1">
                        {recommendation.confidence * 100 < 60 && (
                          <li>{formatString(t('card.riskMessages.lowerConfidence'), (recommendation.confidence * 100).toFixed(1))}</li>
                        )}
                        {(recommendation.ev || 0) * 100 < 10 && (
                          <li>{formatString(t('card.riskMessages.lowEV'), ((recommendation.ev || 0) * 100).toFixed(1))}</li>
                        )}
                        {recommendation.predicted_outcome === 'Draw' && (
                          <li>{t('card.riskMessages.drawPrediction')}</li>
                        )}
                      </ul>
                      <p className="text-xs text-orange-900 mt-2 font-medium">
                        💡 {t('card.risk.advice')}
                      </p>
                    </div>
                  </div>
                </div>
              )}
          </>
        ) : (
          <div className="mb-6 p-6 bg-gray-50 rounded-xl border border-gray-200 text-center">
            <div className="bg-white w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-3 shadow-sm">
              <Target className="h-6 w-6 text-gray-400" />
            </div>
            <h4 className="text-lg font-semibold text-gray-900 mb-1">{t('card.analysisPending.title')}</h4>
            <p className="text-sm text-gray-500 max-w-md mx-auto">
              {t('card.analysisPending.desc')}
            </p>
            {recommendation.odds_data && (
              <div className="mt-4 pt-4 border-t border-gray-200">
                <p className="text-xs font-medium text-gray-600 mb-2">{t('card.liveOdds')}</p>
                <div className="flex justify-center gap-4">
                  <div className="text-center">
                    <div className="text-lg font-bold text-gray-900">{recommendation.odds_data.home?.toFixed(2) || '-'}</div>
                    <div className="text-xs text-gray-500">{t('card.outcomes.home')}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-gray-900">{recommendation.odds_data.draw?.toFixed(2) || '-'}</div>
                    <div className="text-xs text-gray-500">{t('card.outcomes.draw')}</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-gray-900">{recommendation.odds_data.away?.toFixed(2) || '-'}</div>
                    <div className="text-xs text-gray-500">{t('card.outcomes.away')}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* All Available Markets Section */}
      {recommendation.all_markets && recommendation.all_markets.length >= 1 && isExpanded && (
        <div className="mb-4 p-4 bg-gradient-to-r from-gray-50 to-blue-50 rounded-xl border border-gray-200">
          <div className="flex items-center gap-2 mb-3">
            <Target className="h-4 w-4 text-blue-600" />
            <span className="font-semibold text-gray-800 text-sm">{t('card.multiMarket.allMarkets')}</span>
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
              {recommendation.all_markets.length} {t('card.multiMarket.options')}
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {recommendation.all_markets.map((market, idx) => (
              <div
                key={market.type}
                className={`p-2.5 rounded-lg text-center transition-all ${idx === 0
                  ? 'bg-white border-2 border-blue-400 shadow-sm'
                  : market.is_recommended
                    ? 'bg-white border border-green-300'
                    : 'bg-white/60 border border-gray-200 opacity-70'
                  }`}
              >
                <div className="text-xs font-medium text-gray-500 mb-0.5">{market.name}</div>
                <div className={`text-sm font-bold ${idx === 0 ? 'text-blue-700' : 'text-gray-700'}`}>
                  {market.predicted_outcome}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {(market.probability * 100).toFixed(0)}% • {market.odds > 1 ? market.odds.toFixed(2) : '-'}
                </div>
                {idx === 0 && (
                  <div className="text-xs text-green-600 font-medium mt-1">{t('card.multiMarket.starBest')}</div>
                )}
                {!market.is_recommended && idx !== 0 && (
                  <div className="text-xs text-gray-400 mt-1">{t('card.multiMarket.notRecommended')}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Personalized Stake Recommendation */}
      {recommendation.stake_recommendation && (
        <div className="mb-4 p-4 bg-gradient-to-r from-purple-50 to-blue-50 rounded-xl border-2 border-purple-300">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Calculator className="h-5 w-5 text-purple-600" />
              <span className="font-semibold text-purple-900">{t('card.stake.title')}</span>
            </div>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${recommendation.stake_recommendation.risk_level === 'low' ? 'bg-green-100 text-green-700' :
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
            <div className="text-xs text-gray-600 mb-1">{t('card.outcomes.home')}</div>
            <div className="text-lg font-bold text-blue-600">{recommendation.odds_data?.home?.toFixed(2) || 'N/A'}</div>
            <div className="text-xs text-gray-500 mt-1">{recommendation.odds_data?.home_bookmaker || recommendation.bookmaker || recommendation.odds_data?.bookmaker || 'Unknown'}</div>
            {recommendation.predicted_outcome === 'Home' && <div className="text-xs text-blue-600 font-medium mt-1 px-2 py-0.5 bg-blue-100 rounded-full">{t('card.badges.recommended')}</div>}
          </div>
          <div className={`p-3 rounded-lg border-2 transition-all duration-200 ${recommendation.predicted_outcome === 'Draw' ? 'border-gray-500 bg-gray-50 shadow-sm' : 'border-gray-200 hover:border-gray-300'}`}>
            <div className="text-xs text-gray-600 mb-1">{t('card.outcomes.draw')}</div>
            <div className="text-lg font-bold text-gray-600">{recommendation.odds_data?.draw?.toFixed(2) || 'N/A'}</div>
            <div className="text-xs text-gray-500 mt-1">{recommendation.odds_data?.draw_bookmaker || recommendation.bookmaker || recommendation.odds_data?.bookmaker || 'Unknown'}</div>
            {recommendation.predicted_outcome === 'Draw' && <div className="text-xs text-gray-600 font-medium mt-1 px-2 py-0.5 bg-gray-100 rounded-full">{t('card.badges.recommended')}</div>}
          </div>
          <div className={`p-3 rounded-lg border-2 transition-all duration-200 ${recommendation.predicted_outcome === 'Away' ? 'border-purple-500 bg-purple-50 shadow-sm' : 'border-gray-200 hover:border-gray-300'}`}>
            <div className="text-xs text-gray-600 mb-1">{t('card.outcomes.away')}</div>
            <div className="text-lg font-bold text-purple-600">{recommendation.odds_data?.away?.toFixed(2) || 'N/A'}</div>
            <div className="text-xs text-gray-500 mt-1">{recommendation.odds_data?.away_bookmaker || recommendation.bookmaker || recommendation.odds_data?.bookmaker || 'Unknown'}</div>
            {recommendation.predicted_outcome === 'Away' && <div className="text-xs text-purple-600 font-medium mt-1 px-2 py-0.5 bg-purple-100 rounded-full">{t('card.badges.recommended')}</div>}
          </div>
        </div>
      )}
      {/* Opportunity Level & Quick Actions */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          {(() => {
            const opportunity = getOpportunityLevel()
            const Icon = opportunity.icon
            return (
              <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${opportunity.bgColor}`} title={opportunity.description}>
                <Icon className={`h-4 w-4 ${opportunity.color}`} />
                <span className={`text-sm font-medium ${opportunity.color}`}>{opportunity.level}</span>
              </div>
            )
          })()}
        </div>
        <button
          onClick={() => setIsCalculatorOpen(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
        >
          <Calculator className="h-4 w-4" />
          {t('card.stake.calculate')}
        </button>
      </div>

      {/* View Full Analysis Link */}
      <div className="flex justify-center mb-6">
        <Link
          href={matchSlug}
          className="text-sm font-medium text-primary-600 hover:text-primary-700 flex items-center gap-1 hover:underline decoration-primary-300"
        >
          View Full Match Analysis <ArrowRight className="h-4 w-4" />
        </Link>
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
                  <span className={`px-2 py-1 rounded-full text-xs font-bold ${recommendation.league_accuracy.accuracy_percent >= 65
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
          <h4 className="text-lg font-bold text-gray-900 mb-4">{t('card.analysis.title')}</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-gray-50 rounded-xl p-4">
              <h5 className="text-sm font-semibold text-gray-700 mb-3">💰 {t('card.stake.title')}</h5>
              <div className="space-y-2">
                {recommendation.odds_data &&
                  ((recommendation.predicted_outcome.toLowerCase() === 'home' && recommendation.odds_data?.home) ||
                    (recommendation.predicted_outcome.toLowerCase() === 'draw' && recommendation.odds_data?.draw) ||
                    (recommendation.predicted_outcome.toLowerCase() === 'away' && recommendation.odds_data?.away)) && (
                    <div className="bg-white rounded-lg p-3 border border-gray-200">
                      <div className="text-xs text-gray-600 mb-1">{t('card.analysis.optimalBetSize')}</div>
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
                  <div className="text-xs text-gray-600 mb-1">{t('card.opportunity')}</div>
                  <div className={`text-sm font-semibold ${(() => {
                    const opportunity = getOpportunityLevel()
                    return opportunity.color
                  })()
                    }`}>
                    {(() => {
                      const opportunity = getOpportunityLevel()
                      return opportunity.level
                    })()}
                  </div>
                  <div className="text-xs text-gray-500">
                    {(() => {
                      const opportunity = getOpportunityLevel()
                      return opportunity.description
                    })()}
                  </div>
                </div>
              </div>
            </div>
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl p-4 border border-blue-100">
              <h5 className="text-sm font-semibold text-blue-800 mb-3 flex items-center gap-2">
                <span className="text-lg">📊</span>
                {t('card.analysis.quickInsights')}
              </h5>

              {/* Key Betting Information */}
              <div className="space-y-3">
                <div className="bg-white rounded-lg p-3 border border-blue-200">
                  <div className="text-xs text-gray-600 mb-1">{t('card.analysis.predictionSummary')}</div>
                  <div className="text-sm text-gray-700 leading-relaxed">
                    {recommendation.explanation}
                  </div>
                </div>

                <div className="bg-white rounded-lg p-3 border border-blue-200">
                  <div className="text-xs text-gray-600 mb-1">{t('card.analysis.predictionStrength')}</div>
                  <div className={`text-sm font-semibold ${recommendation.debug_info?.variance === 'Low' ? 'text-green-600' :
                    recommendation.debug_info?.variance === 'Medium' ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                    {recommendation.debug_info?.variance === 'Low' ? t('card.analysis.highConfidence') :
                      recommendation.debug_info?.variance === 'Medium' ? t('card.analysis.mediumConfidence') : t('card.analysis.lowConfidence')}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {recommendation.debug_info?.model_consensus ?
                      `Variance: ${(recommendation.debug_info.model_consensus.variance * 100).toFixed(2)}%` :
                      t('card.analysis.modelAgreementAnalysis')
                    }
                  </div>
                </div>

                <div className="bg-white rounded-lg p-3 border border-blue-200">
                  <div className="text-xs text-gray-600 mb-1">{t('card.analysis.bettingEdge')}</div>
                  <div className="text-sm font-semibold text-green-600">
                    {recommendation.ev && recommendation.ev > 0 ? `+${recommendation.ev.toFixed(1)}% ${t('card.analysis.edge')}` : t('card.analysis.negativeEdge')}
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {recommendation.ev && recommendation.ev > 20 ? t('card.analysis.excellentValue') :
                      recommendation.ev && recommendation.ev > 10 ? t('card.analysis.goodValue') :
                        recommendation.ev && recommendation.ev > 0 ? t('card.analysis.marginalValue') : t('card.analysis.poorValue')} • Kelly: ${(() => {
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

            {/* Market Indicators Section */}
            {recommendation.market_indicators && (
              <div className="mt-6 bg-gradient-to-br from-cyan-50 to-blue-50 rounded-xl p-4 border border-cyan-200">
                <h5 className="text-sm font-semibold text-cyan-800 mb-3 flex items-center gap-2">
                  <span className="text-lg">📈</span>
                  Market Analysis
                </h5>

                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div className="bg-white rounded-lg p-3 border border-cyan-100">
                    <div className="text-xs text-gray-600 mb-1">Market Favorite</div>
                    <div className="font-bold text-cyan-700">{recommendation.market_indicators.market_favorite}</div>
                    <div className="text-xs text-gray-500">{recommendation.market_indicators.market_implied_prob} implied</div>
                  </div>

                  <div className="bg-white rounded-lg p-3 border border-cyan-100">
                    <div className="text-xs text-gray-600 mb-1">AI vs Market</div>
                    <div className={`font-bold ${recommendation.market_indicators.ai_vs_market === 'Agreement' ? 'text-green-600' : 'text-orange-600'
                      }`}>
                      {recommendation.market_indicators.ai_vs_market}
                    </div>
                    <div className="text-xs text-gray-500">{recommendation.market_indicators.value_opportunity}</div>
                  </div>

                  <div className="bg-white rounded-lg p-3 border border-cyan-100">
                    <div className="text-xs text-gray-600 mb-1">Market Efficiency</div>
                    <div className="font-bold text-cyan-700">{recommendation.market_indicators.odds_efficiency}</div>
                    <div className="text-xs text-gray-500">Margin: {recommendation.market_indicators.bookmaker_margin}</div>
                  </div>

                  <div className="bg-white rounded-lg p-3 border border-cyan-100">
                    <div className="text-xs text-gray-600 mb-1">Trading Volume</div>
                    <div className={`font-bold ${recommendation.market_indicators.volume_estimate === 'High' ? 'text-green-600' :
                      recommendation.market_indicators.volume_estimate === 'Medium' ? 'text-blue-600' : 'text-gray-600'
                      }`}>
                      {recommendation.market_indicators.volume_estimate}
                    </div>
                    <div className="text-xs text-gray-500">Estimated activity</div>
                  </div>
                </div>

                <div className="mt-3 p-2 bg-cyan-100 rounded-lg">
                  <p className="text-xs text-cyan-800">
                    {recommendation.market_indicators.ai_vs_market === 'Disagreement' ?
                      '💡 AI disagrees with market - potential value opportunity!' :
                      '✓ AI aligns with market consensus'}
                  </p>
                </div>
              </div>
            )}

            {/* Why This Prediction? Section */}
            <div className="mt-6 bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl p-4 border border-purple-200">
              <h5 className="text-sm font-semibold text-purple-800 mb-3 flex items-center gap-2">
                <span className="text-lg">🤔</span>
                {t('card.analysis.whyPrediction')}
              </h5>

              <div className="space-y-3 text-sm text-gray-700">
                {/* Confidence Reasoning */}
                <div className="flex items-start gap-2">
                  <span className="text-purple-600 mt-0.5">•</span>
                  <div>
                    <span className="font-semibold">Prediction Confidence:</span>
                    {' '}
                    {(() => {
                      const conf = recommendation.confidence * 100
                      if (conf >= 70) return `High confidence (${conf.toFixed(1)}%) suggests strong underlying factors favoring ${recommendation.predicted_outcome}.`
                      if (conf >= 60) return `Good confidence (${conf.toFixed(1)}%) indicates a likely outcome for ${recommendation.predicted_outcome}.`
                      if (conf >= 50) return `Moderate confidence (${conf.toFixed(1)}%) - this is a competitive match with slight edge to ${recommendation.predicted_outcome}.`
                      return `Lower confidence (${conf.toFixed(1)}%) indicates this is a close match that could go either way.`
                    })()}
                  </div>
                </div>

                {/* Probability Distribution */}
                {recommendation.probabilities && (
                  <div className="flex items-start gap-2">
                    <span className="text-purple-600 mt-0.5">•</span>
                    <div>
                      <span className="font-semibold">Match Dynamics:</span>
                      {' '}
                      {(() => {
                        const probs = recommendation.probabilities
                        const sortedProbs = [
                          { outcome: 'Home', value: probs.home * 100 },
                          { outcome: 'Draw', value: probs.draw * 100 },
                          { outcome: 'Away', value: probs.away * 100 }
                        ].sort((a, b) => b.value - a.value)

                        const gap = sortedProbs[0].value - sortedProbs[1].value

                        if (gap >= 30) return `Clear favorite with ${gap.toFixed(1)}% margin over next likely outcome.`
                        if (gap >= 20) return `Strong favorite with ${gap.toFixed(1)}% advantage.`
                        if (gap >= 10) return `Moderate favorite with ${gap.toFixed(1)}% edge.`
                        return `Very competitive match with only ${gap.toFixed(1)}% separation between top outcomes.`
                      })()}
                    </div>
                  </div>
                )}

                {/* Value Reasoning */}
                {recommendation.odds_data && (
                  <div className="flex items-start gap-2">
                    <span className="text-purple-600 mt-0.5">•</span>
                    <div>
                      <span className="font-semibold">Betting Value:</span>
                      {' '}
                      {(() => {
                        const ev = (recommendation.ev || 0) * 100
                        const outcome = recommendation.predicted_outcome.toLowerCase()
                        const odds = outcome === 'home' ? recommendation.odds_data?.home :
                          outcome === 'draw' ? recommendation.odds_data?.draw :
                            recommendation.odds_data?.away
                        const prob = recommendation.probabilities ?
                          (outcome === 'home' ? recommendation.probabilities.home :
                            outcome === 'draw' ? recommendation.probabilities.draw :
                              recommendation.probabilities.away) * 100 : 0

                        if (!odds) return 'Odds not available for analysis.'
                        if (ev > 15) return `Market odds (${odds.toFixed(2)}) are significantly higher than implied probability (${(100 / odds).toFixed(1)}%) vs AI prediction (${prob.toFixed(1)}%), creating exceptional value.`
                        if (ev > 5) return `Current odds (${odds.toFixed(2)}) offer positive value compared to AI probability assessment (${prob.toFixed(1)}%).`
                        if (ev > 0) return `Slight value edge detected - odds (${odds.toFixed(2)}) marginally favor this bet.`
                        return `Current market odds (${odds.toFixed(2)}) don't offer positive expected value for this prediction.`
                      })()}
                    </div>
                  </div>
                )}

                {/* Data Source & Quality */}
                <div className="flex items-start gap-2">
                  <span className="text-purple-600 mt-0.5">•</span>
                  <div>
                    <span className="font-semibold">Data Source:</span>
                    {' '}
                    Prediction from SportMonks AI analyzing historical performance, recent form, head-to-head records, and statistical models.
                    {recommendation.signal_quality && (
                      <span className="ml-1">
                        Signal quality: <span className="font-semibold">{recommendation.signal_quality}</span>.
                      </span>
                    )}
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
          onClick={() => setIsExpanded(!isExpanded)}
          className="group inline-flex items-center gap-2 bg-primary-600 hover:bg-primary-700 text-white px-4 py-2 rounded-xl font-semibold transition-all duration-200 hover:scale-105"
        >
          {isExpanded ? t('card.hideAnalysis') : t('card.viewAnalysis')}
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 transition-transform" />
          ) : (
            <ChevronDown className="h-4 w-4 transition-transform" />
          )}
        </button>


      </div>

      {/* Betting Acknowledgment Modal */}
      <BettingAcknowledgmentModal
        isOpen={showAcknowledgment}
        onConfirm={handleAcknowledgmentConfirm}
        onClose={() => setShowAcknowledgment(false)}
        language={language as 'en' | 'ro'}
      />

      {/* Betting Calculator Modal */}
      <BettingCalculatorModal
        recommendation={recommendation}
        isOpen={isCalculatorOpen}
        onClose={() => setIsCalculatorOpen(false)}
      />
    </div>
  )
}
