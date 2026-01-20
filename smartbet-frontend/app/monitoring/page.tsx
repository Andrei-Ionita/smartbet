'use client'

import RecommendedPredictionsTable from '../components/RecommendedPredictionsTable'
import { Award, TrendingUp } from 'lucide-react'
import { useLanguage } from '../contexts/LanguageContext';

export default function MonitoringPage() {
  const { t } = useLanguage();
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

        {/* History Table Only */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-6 border-b border-gray-100">
            <h3 className="text-xl font-bold text-gray-900 flex items-center gap-2">
              <Award className="h-5 w-5 text-blue-600" />
              {t('monitoring.tabs.recommended')}
            </h3>
          </div>
          <div className="p-6">
            <RecommendedPredictionsTable />
          </div>
        </div>
      </div>
    </div>
  )
}
