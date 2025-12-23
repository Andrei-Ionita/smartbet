'use client'

import { useState } from 'react'
import ModelPerformanceDashboard from '../components/ModelPerformanceDashboard'
import PredictionAccuracyTracker from '../components/PredictionAccuracyTracker'
import RecommendedPredictionsTable from '../components/RecommendedPredictionsTable'
import { BarChart3, Settings, TrendingUp, Target, Award, ShieldCheck } from 'lucide-react'
import { useLanguage } from '../contexts/LanguageContext';

export default function MonitoringPage() {
  const { t } = useLanguage();
  const [activeTab, setActiveTab] = useState<'dashboard' | 'accuracy' | 'recommended' | 'analytics' | 'settings'>('dashboard')

  const tabs = [
    { id: 'dashboard', label: t('monitoring.tabs.dashboard'), icon: ShieldCheck },
    { id: 'accuracy', label: t('monitoring.tabs.accuracy'), icon: Target },
    { id: 'recommended', label: t('monitoring.tabs.recommended'), icon: Award },
    { id: 'analytics', label: t('monitoring.tabs.analytics'), icon: BarChart3 },
    { id: 'settings', label: t('monitoring.tabs.settings'), icon: Settings }
  ]

  // Helper for replacing placeholders
  const formatString = (str: string, ...args: (string | number)[]) => {
    return str.replace(/{(\d+)}/g, (match, number) => {
      return typeof args[number] !== 'undefined' ? String(args[number]) : match;
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="bg-gradient-to-br from-blue-500 to-purple-600 w-12 h-12 rounded-2xl flex items-center justify-center">
              <TrendingUp className="h-6 w-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">{t('monitoring.title')}</h1>
              <p className="text-gray-600">{t('monitoring.subtitle')}</p>
            </div>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="bg-white rounded-2xl p-2 shadow-lg border border-gray-200 mb-8">
          <div className="flex space-x-2 overflow-x-auto">
            {tabs.map((tab) => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`flex items-center gap-2 px-4 py-3 rounded-xl font-medium transition-all duration-200 whitespace-nowrap ${activeTab === tab.id
                    ? 'bg-primary-100 text-primary-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`}
                >
                  <Icon className="h-4 w-4" />
                  {tab.label}
                </button>
              )
            })}
          </div>
        </div>

        {/* Tab Content */}
        <div className="space-y-8">
          {activeTab === 'dashboard' && (
            <div className="space-y-8">
              <ModelPerformanceDashboard />

              <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 text-center">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{t('monitoring.whyTrack.title')}</h3>
                <p className="text-gray-600 max-w-2xl mx-auto">
                  {t('monitoring.whyTrack.description')}
                </p>
              </div>
            </div>
          )}

          {activeTab === 'accuracy' && (
            <div className="space-y-6">
              <PredictionAccuracyTracker />
            </div>
          )}

          {activeTab === 'recommended' && (
            <div className="space-y-6">
              <RecommendedPredictionsTable />
            </div>
          )}

          {activeTab === 'analytics' && (
            <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-200">
              <h3 className="text-xl font-bold text-gray-900 mb-6">{t('monitoring.analytics.title')}</h3>
              <div className="text-center py-12">
                <BarChart3 className="h-16 w-16 text-gray-300 mx-auto mb-4" />
                <h4 className="text-lg font-semibold text-gray-700 mb-2">{t('monitoring.analytics.comingSoon')}</h4>
                <p className="text-gray-500">
                  {t('monitoring.analytics.description')}
                </p>
              </div>
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="bg-white rounded-2xl p-6 shadow-lg border border-gray-200">
              <h3 className="text-xl font-bold text-gray-900 mb-6">{t('monitoring.settings.title')}</h3>
              <div className="space-y-6">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {t('monitoring.settings.autoRefresh')}
                  </label>
                  <select className="w-full max-w-xs px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500">
                    <option value="5000">{formatString(t('monitoring.settings.seconds'), 5)}</option>
                    <option value="10000">{formatString(t('monitoring.settings.seconds'), 10)}</option>
                    <option value="30000">{formatString(t('monitoring.settings.seconds'), 30)}</option>
                    <option value="60000">{t('monitoring.settings.minute')}</option>
                  </select>
                </div>

                <div>
                  <label className="flex items-center gap-3">
                    <input type="checkbox" className="rounded" defaultChecked />
                    <span className="text-sm font-medium text-gray-700">{t('monitoring.settings.alerts')}</span>
                  </label>
                </div>

                <div>
                  <label className="flex items-center gap-3">
                    <input type="checkbox" className="rounded" defaultChecked />
                    <span className="text-sm font-medium text-gray-700">{t('monitoring.settings.logging')}</span>
                  </label>
                </div>

                <div>
                  <label className="flex items-center gap-3">
                    <input type="checkbox" className="rounded" />
                    <span className="text-sm font-medium text-gray-700">{t('monitoring.settings.errorTracking')}</span>
                  </label>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
