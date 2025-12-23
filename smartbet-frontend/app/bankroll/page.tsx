'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import BankrollSetupModal from '../components/BankrollSetupModal';
import { useLanguage } from '../contexts/LanguageContext';

interface BankrollData {
  session_id: string;
  initial_bankroll: number;
  current_bankroll: number;
  currency: string;
  risk_profile: string;
  staking_strategy: string;
  total_profit_loss: number;
  roi_percent: number;
  total_bets_placed: number;
  total_wagered: number;
  is_daily_limit_reached: boolean;
  is_weekly_limit_reached: boolean;
  daily_loss_amount: number;
  weekly_loss_amount: number;
  daily_loss_limit: number | null;
  weekly_loss_limit: number | null;
  max_stake_percentage: number;
  created_at: string;
}

interface TransactionData {
  id: number;
  transaction_type: string;
  match_description: string;
  selected_outcome: string;
  odds: number;
  stake_amount: number;
  profit_loss: number | null;
  status: string;
  created_at: string;
  settled_at: string | null;
}

interface StatsData {
  total_bets: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_profit: number;
  avg_profit_per_bet: number;
  bankroll_change: number;
  bankroll_change_pct: number;
  roi: number;
  pending_bets: number;
  pending_exposure: number;
}

export default function BankrollPage() {
  const router = useRouter();
  const { t } = useLanguage();
  const [bankroll, setBankroll] = useState<BankrollData | null>(null);
  const [stats, setStats] = useState<StatsData | null>(null);
  const [transactions, setTransactions] = useState<TransactionData[]>([]);
  const [loading, setLoading] = useState(true);
  const [showSetupModal, setShowSetupModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'transactions' | 'settings'>('overview');

  useEffect(() => {
    loadBankrollData();
  }, []);

  const loadBankrollData = async () => {
    try {
      const sessionId = localStorage.getItem('smartbet_session_id');

      if (!sessionId) {
        setShowSetupModal(true);
        setLoading(false);
        return;
      }

      // Load bankroll
      const bankrollResponse = await fetch(`/api/bankroll/${sessionId}/`);
      const bankrollData = await bankrollResponse.json();

      if (bankrollResponse.ok && bankrollData.bankroll) {
        setBankroll(bankrollData.bankroll);
      } else {
        setShowSetupModal(true);
        setLoading(false);
        return;
      }

      // Load stats
      const statsResponse = await fetch(`/api/bankroll/${sessionId}/stats/`);
      const statsData = await statsResponse.json();
      if (statsResponse.ok) {
        setStats(statsData.stats);
      }

      // Load transactions
      const transactionsResponse = await fetch(`/api/bankroll/${sessionId}/transactions/?limit=20`);
      const transactionsData = await transactionsResponse.json();
      if (transactionsResponse.ok) {
        setTransactions(transactionsData.transactions);
      }
    } catch (error) {
      console.error('Failed to load bankroll data:', error);
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

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
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
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="max-w-7xl mx-auto">
          <div className="animate-pulse space-y-4">
            <div className="h-12 bg-gray-200 rounded w-1/3"></div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-32 bg-gray-200 rounded"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!bankroll) {
    return (
      <>
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <div className="text-center">
            <div className="text-6xl mb-4">💰</div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              {t('bankroll.title')}
            </h1>
            <p className="text-gray-600 mb-6">
              {t('bankroll.subtitle')}
            </p>
            <button
              onClick={() => setShowSetupModal(true)}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              Get Started
            </button>
          </div>
        </div>
        <BankrollSetupModal
          isOpen={showSetupModal}
          onClose={() => router.push('/')}
          onSuccess={loadBankrollData}
        />
      </>
    );
  }

  const profitLoss = bankroll.total_profit_loss;
  const isProfitable = profitLoss >= 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <button
            onClick={() => router.push('/')}
            className="text-blue-600 hover:text-blue-700 mb-4 flex items-center gap-2 text-sm"
          >
            ← Back to Home
          </button>
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <span>💰</span>
            <span>{t('bankroll.page.title')}</span>
          </h1>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Tabs */}
        <div className="flex gap-2 mb-6 border-b border-gray-200">
          {(['overview', 'transactions', 'settings'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 font-medium text-sm border-b-2 transition-colors ${activeTab === tab
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-600 hover:text-gray-900'
                }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Main Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Current Bankroll */}
              <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-lg p-6 text-white">
                <p className="text-sm opacity-90 mb-2">{t('bankroll.page.currentBalance')}</p>
                <p className="text-4xl font-bold mb-2">
                  {formatCurrency(bankroll.current_bankroll, bankroll.currency)}
                </p>
                <p className="text-sm opacity-90">
                  Started with {formatCurrency(bankroll.initial_bankroll, bankroll.currency)}
                </p>
              </div>

              {/* Profit/Loss */}
              <div className={`rounded-lg p-6 ${isProfitable ? 'bg-green-50 border-2 border-green-200' : 'bg-red-50 border-2 border-red-200'
                }`}>
                <p className="text-sm text-gray-700 mb-2">{t('bankroll.page.totalProfit')}</p>
                <p className={`text-4xl font-bold mb-2 ${isProfitable ? 'text-green-700' : 'text-red-700'
                  }`}>
                  {isProfitable ? '+' : ''}{formatCurrency(profitLoss, bankroll.currency)}
                </p>
                <p className="text-sm text-gray-700">
                  {isProfitable ? '↑' : '↓'} {((profitLoss / bankroll.initial_bankroll) * 100).toFixed(1)}%
                </p>
              </div>

              {/* ROI */}
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <p className="text-sm text-gray-600 mb-2">{t('bankroll.page.roi')}</p>
                <p className={`text-4xl font-bold mb-2 ${bankroll.roi_percent >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                  {bankroll.roi_percent.toFixed(1)}%
                </p>
                <p className="text-sm text-gray-600">
                  {getRiskProfileEmoji(bankroll.risk_profile)} {t(`bankroll.riskProfiles.${bankroll.risk_profile as any}.label` as any) || bankroll.risk_profile}
                </p>
              </div>
            </div>

            {/* Performance Stats */}
            {stats && (
              <div className="bg-white rounded-lg border border-gray-200 p-6">
                <h2 className="text-xl font-bold text-gray-900 mb-4">{t('bankroll.page.stats.title')}</h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                  <div>
                    <p className="text-sm text-gray-600 mb-1">{t('bankroll.page.stats.totalBets')}</p>
                    <p className="text-2xl font-bold text-gray-900">{stats.total_bets}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-1">{t('bankroll.page.stats.winRate')}</p>
                    <p className="text-2xl font-bold text-gray-900">{stats.win_rate.toFixed(1)}%</p>
                    <p className="text-xs text-gray-500 mt-1">{stats.wins}W - {stats.losses}L</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-1">{t('bankroll.page.stats.avgProfit')}</p>
                    <p className={`text-2xl font-bold ${stats.avg_profit_per_bet >= 0 ? 'text-green-600' : 'text-red-600'
                      }`}>
                      {formatCurrency(stats.avg_profit_per_bet, bankroll.currency)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600 mb-1">{t('bankroll.page.stats.pending')}</p>
                    <p className="text-2xl font-bold text-gray-900">{stats.pending_bets}</p>
                    <p className="text-xs text-gray-500 mt-1">
                      {formatCurrency(stats.pending_exposure, bankroll.currency)} {t('bankroll.page.stats.atRisk')}
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Limits */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">{t('bankroll.page.limits.title')}</h2>
              <div className="space-y-4">
                {/* Daily Limit */}
                {bankroll.daily_loss_limit && (
                  <div>
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-gray-600">{t('bankroll.page.limits.daily')}</span>
                      <span className="font-medium text-gray-900">
                        {formatCurrency(bankroll.daily_loss_amount, bankroll.currency)} / {formatCurrency(bankroll.daily_loss_limit, bankroll.currency)}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div
                        className={`h-3 rounded-full transition-all ${bankroll.is_daily_limit_reached ? 'bg-red-600' : 'bg-blue-600'
                          }`}
                        style={{
                          width: `${Math.min((bankroll.daily_loss_amount / bankroll.daily_loss_limit) * 100, 100)}%`
                        }}
                      ></div>
                    </div>
                    {bankroll.is_daily_limit_reached && (
                      <p className="text-xs text-red-600 mt-1">⚠️ {t('bankroll.page.limits.daily')} {t('bankroll.page.limits.reached')}</p>
                    )}
                  </div>
                )}

                {/* Weekly Limit */}
                {bankroll.weekly_loss_limit && (
                  <div>
                    <div className="flex items-center justify-between text-sm mb-2">
                      <span className="text-gray-600">{t('bankroll.page.limits.weekly')}</span>
                      <span className="font-medium text-gray-900">
                        {formatCurrency(bankroll.weekly_loss_amount, bankroll.currency)} / {formatCurrency(bankroll.weekly_loss_limit, bankroll.currency)}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-3">
                      <div
                        className={`h-3 rounded-full transition-all ${bankroll.is_weekly_limit_reached ? 'bg-red-600' : 'bg-green-600'
                          }`}
                        style={{
                          width: `${Math.min((bankroll.weekly_loss_amount / bankroll.weekly_loss_limit) * 100, 100)}%`
                        }}
                      ></div>
                    </div>
                    {bankroll.is_weekly_limit_reached && (
                      <p className="text-xs text-red-600 mt-1">⚠️ {t('bankroll.page.limits.weekly')} {t('bankroll.page.limits.reached')}</p>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Recent Transactions */}
            <div className="bg-white rounded-lg border border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-gray-900">{t('bankroll.page.transactions.recent')}</h2>
                <button
                  onClick={() => setActiveTab('transactions')}
                  className="text-sm text-blue-600 hover:text-blue-700"
                >
                  {t('bankroll.page.transactions.viewAll')}
                </button>
              </div>
              <div className="space-y-3">
                {transactions.slice(0, 5).map((txn) => (
                  <div key={txn.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div className="flex-1">
                      <p className="font-medium text-sm text-gray-900">{txn.match_description || 'Bet'}</p>
                      <p className="text-xs text-gray-600 mt-1">
                        {txn.selected_outcome} @ {txn.odds.toFixed(2)} · {formatDate(txn.created_at)}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-medium text-sm text-gray-900">
                        {formatCurrency(txn.stake_amount, bankroll.currency)}
                      </p>
                      {txn.profit_loss !== null && (
                        <p className={`text-xs font-medium ${txn.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'
                          }`}>
                          {txn.profit_loss >= 0 ? '+' : ''}{formatCurrency(txn.profit_loss, bankroll.currency)}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
                {transactions.length === 0 && (
                  <p className="text-center text-gray-500 py-8">{t('bankroll.page.noTransactions')}</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Transactions Tab */}
        {activeTab === 'transactions' && (
          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <div className="p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">{t('bankroll.page.transactions.all')}</h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-y border-gray-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('bankroll.page.transactions.table.match')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('bankroll.page.transactions.table.outcome')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('bankroll.page.transactions.table.odds')}</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">{t('bankroll.page.transactions.table.stake')}</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">{t('bankroll.page.transactions.table.pl')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('bankroll.page.transactions.table.status')}</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">{t('bankroll.page.transactions.table.date')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {transactions.map((txn) => (
                    <tr key={txn.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 text-sm text-gray-900">{txn.match_description || '-'}</td>
                      <td className="px-6 py-4 text-sm text-gray-900">{txn.selected_outcome}</td>
                      <td className="px-6 py-4 text-sm text-gray-900">{txn.odds.toFixed(2)}</td>
                      <td className="px-6 py-4 text-sm text-gray-900 text-right">
                        {formatCurrency(txn.stake_amount, bankroll.currency)}
                      </td>
                      <td className="px-6 py-4 text-sm text-right">
                        {txn.profit_loss !== null ? (
                          <span className={`font-medium ${txn.profit_loss >= 0 ? 'text-green-600' : 'text-red-600'
                            }`}>
                            {txn.profit_loss >= 0 ? '+' : ''}{formatCurrency(txn.profit_loss, bankroll.currency)}
                          </span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm">
                        <span className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${txn.status === 'settled_won' ? 'bg-green-100 text-green-800' :
                          txn.status === 'settled_lost' ? 'bg-red-100 text-red-800' :
                            txn.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-gray-100 text-gray-800'
                          }`}>
                          {txn.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-600">
                        {formatDate(txn.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {transactions.length === 0 && (
                <div className="text-center py-12 text-gray-500">
                  {t('bankroll.page.noTransactions')}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Settings Tab */}
        {activeTab === 'settings' && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">{t('bankroll.page.settings.title')}</h2>
            <div className="space-y-6">
              <div>
                <p className="text-sm text-gray-600 mb-2">{t('bankroll.form.riskProfile')}</p>
                <p className="text-lg font-medium text-gray-900">
                  {getRiskProfileEmoji(bankroll.risk_profile)} {t(`bankroll.riskProfiles.${bankroll.risk_profile as any}.label` as any) || bankroll.risk_profile}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-2">{t('bankroll.form.stakingStrategy')}</p>
                <p className="text-lg font-medium text-gray-900">
                  {t(`bankroll.strategies.${bankroll.staking_strategy as any}.label` as any) || bankroll.staking_strategy.replace('_', ' ')}
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-600 mb-2">{t('bankroll.form.maxStake')}</p>
                <p className="text-lg font-medium text-gray-900">{bankroll.max_stake_percentage}% of bankroll</p>
              </div>
              <div className="pt-4 border-t">
                <p className="text-xs text-gray-500">
                  {t('bankroll.page.settings.accountCreated')}: {formatDate(bankroll.created_at)}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

