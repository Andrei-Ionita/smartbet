'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

interface BankrollData {
  session_id: string;
  initial_bankroll: number;
  current_bankroll: number;
  currency: string;
  risk_profile: string;
  total_profit_loss: number;
  roi_percent: number;
  total_bets_placed: number;
  is_daily_limit_reached: boolean;
  is_weekly_limit_reached: boolean;
  daily_loss_amount: number;
  weekly_loss_amount: number;
  daily_loss_limit: number | null;
  weekly_loss_limit: number | null;
}

export default function BankrollWidget() {
  const router = useRouter();
  const [bankroll, setBankroll] = useState<BankrollData | null>(null);
  const [loading, setLoading] = useState(true);
  const [showSetup, setShowSetup] = useState(false);

  useEffect(() => {
    loadBankroll();
  }, []);

  const loadBankroll = async () => {
    try {
      const sessionId = localStorage.getItem('smartbet_session_id');

      if (!sessionId) {
        setLoading(false);
        return;
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/bankroll/${sessionId}/`);
      const data = await response.json();

      if (response.ok && data.bankroll) {
        setBankroll(data.bankroll);
        localStorage.setItem('smartbet_bankroll', JSON.stringify(data.bankroll));
      }
    } catch (error) {
      console.error('Failed to load bankroll:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount: number, currency: string = 'USD') => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
      minimumFractionDigits: 2,
    }).format(amount);
  };

  const getRiskProfileEmoji = (profile: string) => {
    switch (profile) {
      case 'conservative': return '🛡️';
      case 'balanced': return '⚖️';
      case 'aggressive': return '🚀';
      default: return '⚖️';
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
        <div className="h-8 bg-gray-200 rounded w-3/4"></div>
      </div>
    );
  }

  if (!bankroll) {
    return (
      <div className="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg border-2 border-blue-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900 mb-1">
              💰 Bankroll Management
            </h3>
            <p className="text-sm text-gray-600">
              Set up your bankroll to get personalized stake recommendations
            </p>
          </div>
          <button
            onClick={() => setShowSetup(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          >
            Set Up
          </button>
        </div>
      </div>
    );
  }

  const profitLoss = bankroll.total_profit_loss;
  const profitLossPercentage = ((profitLoss / bankroll.initial_bankroll) * 100);
  const isProfitable = profitLoss >= 0;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 p-4">
        <div className="flex items-center justify-between text-white">
          <div>
            <p className="text-sm opacity-90">Your Bankroll</p>
            <p className="text-3xl font-bold">
              {formatCurrency(bankroll.current_bankroll, bankroll.currency)}
            </p>
          </div>
          <button
            onClick={() => router.push('/bankroll')}
            className="px-3 py-1.5 bg-white bg-opacity-20 rounded-lg hover:bg-opacity-30 transition-colors text-sm"
          >
            Details
          </button>
        </div>

        {/* Profit/Loss */}
        <div className="mt-3 flex items-center gap-2">
          <span
            className={`inline-flex items-center px-2 py-1 rounded text-sm font-medium ${isProfitable
              ? 'bg-green-400 bg-opacity-30 text-white'
              : 'bg-red-400 bg-opacity-30 text-white'
              }`}
          >
            {isProfitable ? '↑' : '↓'} {formatCurrency(Math.abs(profitLoss), bankroll.currency)}
            <span className="ml-1 opacity-90">({profitLossPercentage.toFixed(1)}%)</span>
          </span>
          <span className="text-white text-opacity-80 text-sm">
            {getRiskProfileEmoji(bankroll.risk_profile)} {bankroll.risk_profile}
          </span>
        </div>
      </div>

      {/* Stats */}
      <div className="p-4 grid grid-cols-2 gap-4">
        <div>
          <p className="text-xs text-gray-500 mb-1">ROI</p>
          <p className={`text-lg font-semibold ${bankroll.roi_percent >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
            {bankroll.roi_percent.toFixed(1)}%
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 mb-1">Total Bets</p>
          <p className="text-lg font-semibold text-gray-900">
            {bankroll.total_bets_placed}
          </p>
        </div>
      </div>

      {/* Limits Warning */}
      {(bankroll.is_daily_limit_reached || bankroll.is_weekly_limit_reached) && (
        <div className="px-4 pb-4">
          <div className="bg-red-50 border border-red-200 rounded-lg p-3">
            <p className="text-sm text-red-800 font-medium">
              ⚠️ {bankroll.is_daily_limit_reached ? 'Daily' : 'Weekly'} loss limit reached
            </p>
            <p className="text-xs text-red-600 mt-1">
              No more bets today to protect your bankroll
            </p>
          </div>
        </div>
      )}

      {/* Loss tracking */}
      {bankroll.daily_loss_limit && !bankroll.is_daily_limit_reached && (
        <div className="px-4 pb-4">
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center justify-between text-sm mb-1">
              <span className="text-gray-600">Today's Losses</span>
              <span className="font-medium text-gray-900">
                {formatCurrency(bankroll.daily_loss_amount, bankroll.currency)} / {formatCurrency(bankroll.daily_loss_limit, bankroll.currency)}
              </span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{
                  width: `${Math.min((bankroll.daily_loss_amount / bankroll.daily_loss_limit) * 100, 100)}%`
                }}
              ></div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

