'use client';

import React, { useState } from 'react';
import { useLanguage } from '../contexts/LanguageContext';

interface BankrollSetupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (bankroll: any) => void;
}

export default function BankrollSetupModal({ isOpen, onClose, onSuccess }: BankrollSetupModalProps) {
  const { t } = useLanguage();
  const [formData, setFormData] = useState({
    initialBankroll: '',
    currency: 'USD',
    riskProfile: 'balanced',
    stakingStrategy: 'kelly_fractional',
    dailyLossLimit: '',
    weeklyLossLimit: '',
    maxStakePercentage: '5',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const riskProfiles = [
    {
      value: 'conservative',
      label: t('bankroll.riskProfiles.conservative.label'),
      description: t('bankroll.riskProfiles.conservative.description'),
      emoji: '🛡️',
    },
    {
      value: 'balanced',
      label: t('bankroll.riskProfiles.balanced.label'),
      description: t('bankroll.riskProfiles.balanced.description'),
      emoji: '⚖️',
    },
    {
      value: 'aggressive',
      label: t('bankroll.riskProfiles.aggressive.label'),
      description: t('bankroll.riskProfiles.aggressive.description'),
      emoji: '🚀',
    },
  ];

  const stakingStrategies = [
    {
      value: 'kelly_fractional',
      label: t('bankroll.strategies.kelly_fractional.label'),
      description: t('bankroll.strategies.kelly_fractional.description'),
    },
    {
      value: 'kelly',
      label: t('bankroll.strategies.kelly.label'),
      description: t('bankroll.strategies.kelly.description'),
    },
    {
      value: 'fixed_percentage',
      label: t('bankroll.strategies.fixed_percentage.label'),
      description: t('bankroll.strategies.fixed_percentage.description'),
    },
    {
      value: 'fixed_amount',
      label: t('bankroll.strategies.fixed_amount.label'),
      description: t('bankroll.strategies.fixed_amount.description'),
    },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      // Generate session ID
      const sessionId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

      // Calculate suggested limits based on risk profile
      const initialAmount = parseFloat(formData.initialBankroll);
      let dailyLimit = formData.dailyLossLimit;
      let weeklyLimit = formData.weeklyLossLimit;

      if (!dailyLimit) {
        const dailyPct = formData.riskProfile === 'conservative' ? 0.05 :
          formData.riskProfile === 'balanced' ? 0.10 : 0.20;
        dailyLimit = (initialAmount * dailyPct).toFixed(2);
      }

      if (!weeklyLimit) {
        const weeklyPct = formData.riskProfile === 'conservative' ? 0.15 :
          formData.riskProfile === 'balanced' ? 0.25 : 0.40;
        weeklyLimit = (initialAmount * weeklyPct).toFixed(2);
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/bankroll/create/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          initial_bankroll: formData.initialBankroll,
          currency: formData.currency,
          risk_profile: formData.riskProfile,
          staking_strategy: formData.stakingStrategy,
          daily_loss_limit: dailyLimit,
          weekly_loss_limit: weeklyLimit,
          max_stake_percentage: parseFloat(formData.maxStakePercentage),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to create bankroll');
      }

      // Store session ID in localStorage
      localStorage.setItem('smartbet_session_id', sessionId);
      localStorage.setItem('smartbet_bankroll', JSON.stringify(data.bankroll));

      onSuccess(data.bankroll);
      onClose();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">
            💰 {t('bankroll.title')}
          </h2>
          <p className="text-gray-600 mb-6">
            {t('bankroll.subtitle')}
          </p>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Initial Bankroll */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('bankroll.form.initialBankroll')} *
              </label>
              <div className="flex gap-2">
                <select
                  value={formData.currency}
                  onChange={(e) => setFormData({ ...formData, currency: e.target.value })}
                  className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                  <option value="USD">USD $</option>
                  <option value="EUR">EUR €</option>
                  <option value="GBP">GBP £</option>
                </select>
                <input
                  type="number"
                  step="0.01"
                  required
                  value={formData.initialBankroll}
                  onChange={(e) => setFormData({ ...formData, initialBankroll: e.target.value })}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder="1000.00"
                />
              </div>
              <p className="mt-1 text-xs text-gray-500">
                {t('bankroll.form.initialBankrollHelp')}
              </p>
            </div>

            {/* Risk Profile */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('bankroll.form.riskProfile')} *
              </label>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {riskProfiles.map((profile) => (
                  <button
                    key={profile.value}
                    type="button"
                    onClick={() => setFormData({ ...formData, riskProfile: profile.value })}
                    className={`p-3 border-2 rounded-lg text-left transition-all ${formData.riskProfile === profile.value
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                      }`}
                  >
                    <div className="text-2xl mb-1">{profile.emoji}</div>
                    <div className="font-medium text-sm">{profile.label}</div>
                    <div className="text-xs text-gray-600 mt-1">{profile.description}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Staking Strategy */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('bankroll.form.stakingStrategy')} *
              </label>
              <select
                value={formData.stakingStrategy}
                onChange={(e) => setFormData({ ...formData, stakingStrategy: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              >
                {stakingStrategies.map((strategy) => (
                  <option key={strategy.value} value={strategy.value}>
                    {strategy.label} - {strategy.description}
                  </option>
                ))}
              </select>
            </div>

            {/* Loss Limits */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {t('bankroll.form.dailyLossLimit')}
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.dailyLossLimit}
                  onChange={(e) => setFormData({ ...formData, dailyLossLimit: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder={t('bankroll.form.autoCalculated')}
                />
                <p className="mt-1 text-xs text-gray-500">
                  {t('bankroll.form.dailyLossLimitHelp')}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  {t('bankroll.form.weeklyLossLimit')}
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={formData.weeklyLossLimit}
                  onChange={(e) => setFormData({ ...formData, weeklyLossLimit: e.target.value })}
                  className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  placeholder={t('bankroll.form.autoCalculated')}
                />
                <p className="mt-1 text-xs text-gray-500">
                  {t('bankroll.form.weeklyLossLimitHelp')}
                </p>
              </div>
            </div>

            {/* Max Stake */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                {t('bankroll.form.maxStake')} *
              </label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                max="25"
                required
                value={formData.maxStakePercentage}
                onChange={(e) => setFormData({ ...formData, maxStakePercentage: e.target.value })}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                {t('bankroll.form.maxStakeHelp')}
              </p>
            </div>

            {/* Actions */}
            <div className="flex gap-3 pt-4 border-t">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                disabled={isSubmitting}
              >
                {t('bankroll.form.cancel')}
              </button>
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400"
              >
                {isSubmitting ? t('bankroll.form.creating') : t('bankroll.form.create')}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

