'use client';

import React from 'react';

interface StakeRecommendationProps {
  stakeRecommendation: {
    recommended_stake: number;
    stake_percentage: number;
    currency: string;
    strategy: string;
    risk_level: string;
    risk_explanation: string;
    warnings: string[];
  };
  compact?: boolean;
}

export default function StakeRecommendation({ stakeRecommendation, compact = false }: StakeRecommendationProps) {
  const { recommended_stake, stake_percentage, currency, strategy, risk_level, risk_explanation, warnings } = stakeRecommendation;

  const getRiskColor = (level: string) => {
    switch (level) {
      case 'low':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'high':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getRiskEmoji = (level: string) => {
    switch (level) {
      case 'low': return '✅';
      case 'medium': return '⚠️';
      case 'high': return '🔴';
      default: return 'ℹ️';
    }
  };

  const getStrategyLabel = (strategy: string) => {
    switch (strategy) {
      case 'kelly': return 'Full Kelly';
      case 'kelly_fractional': return '1/4 Kelly';
      case 'fixed_percentage': return 'Fixed %';
      case 'fixed_amount': return 'Fixed Amount';
      case 'confidence_scaled': return 'Confidence Scaled';
      default: return strategy;
    }
  };

  const formatCurrency = (amount: number, curr: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: curr,
      minimumFractionDigits: 2,
    }).format(amount);
  };

  if (compact) {
    return (
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-3 border border-blue-200">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-600 mb-1">Recommended Stake</p>
            <p className="text-2xl font-bold text-blue-900">
              {formatCurrency(recommended_stake, currency)}
            </p>
            <p className="text-xs text-gray-600 mt-1">
              {stake_percentage.toFixed(2)}% of bankroll · {getStrategyLabel(strategy)}
            </p>
          </div>
          <div className={`px-3 py-1.5 rounded-full border text-xs font-medium ${getRiskColor(risk_level)}`}>
            {getRiskEmoji(risk_level)} {risk_level}
          </div>
        </div>
        
        {warnings.length > 0 && (
          <div className="mt-2 pt-2 border-t border-blue-200">
            {warnings.map((warning, index) => (
              <p key={index} className="text-xs text-orange-700 flex items-start gap-1">
                <span>⚠️</span>
                <span>{warning}</span>
              </p>
            ))}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border-2 border-blue-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 px-4 py-3">
        <h3 className="text-white font-semibold flex items-center gap-2">
          <span>💰</span>
          <span>Stake Recommendation</span>
        </h3>
      </div>

      {/* Main Content */}
      <div className="p-4">
        {/* Recommended Stake */}
        <div className="text-center mb-4">
          <p className="text-sm text-gray-600 mb-2">Recommended Stake</p>
          <p className="text-4xl font-bold text-blue-900 mb-1">
            {formatCurrency(recommended_stake, currency)}
          </p>
          <p className="text-sm text-gray-600">
            {stake_percentage.toFixed(2)}% of your bankroll
          </p>
        </div>

        {/* Risk Level */}
        <div className="mb-4">
          <div className={`px-4 py-3 rounded-lg border ${getRiskColor(risk_level)}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="font-medium text-sm">
                {getRiskEmoji(risk_level)} Risk Level: {risk_level.charAt(0).toUpperCase() + risk_level.slice(1)}
              </span>
            </div>
            <p className="text-xs">{risk_explanation}</p>
          </div>
        </div>

        {/* Strategy */}
        <div className="bg-gray-50 rounded-lg p-3 mb-4">
          <p className="text-xs text-gray-600 mb-1">Staking Strategy</p>
          <p className="font-medium text-sm text-gray-900">{getStrategyLabel(strategy)}</p>
        </div>

        {/* Warnings */}
        {warnings.length > 0 && (
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
            <p className="text-sm font-medium text-orange-900 mb-2">⚠️ Warnings</p>
            <ul className="space-y-1">
              {warnings.map((warning, index) => (
                <li key={index} className="text-xs text-orange-800 flex items-start gap-2">
                  <span className="mt-0.5">•</span>
                  <span>{warning}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

