'use client'

import { useState, useEffect } from 'react'
import {
    Trophy,
    TrendingUp,
    Target,
    CheckCircle,
    XCircle,
    Clock,
    ShieldCheck,
    ArrowRight
} from 'lucide-react'
import Link from 'next/link'
import { useLanguage } from '../contexts/LanguageContext'

interface AccuracyStats {
    overall: {
        total_predictions: number;
        correct_predictions: number;
        accuracy_percent: number;
    };
}

interface ROIStats {
    total_bets: number;
    roi_percent: number;
    total_profit_loss: number;
    win_rate: number;
    wins: number;
    losses: number;
    win_rate_percent?: number; // Optional fallback
}

export default function ModelPerformanceDashboard() {
    const { t } = useLanguage()
    const [accuracy, setAccuracy] = useState<AccuracyStats | null>(null)
    const [roi, setRoi] = useState<ROIStats | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await fetch('/api/transparency/dashboard/')
                const data = await response.json()
                if (data.success) {
                    setAccuracy(data.stats.overall_accuracy)
                    setRoi(data.stats.roi_simulation)
                }
            } catch (error) {
                console.error('Failed to fetch performance stats:', error)
            } finally {
                setLoading(false)
            }
        }
        fetchData()
    }, [])

    if (loading) {
        return (
            <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-100 animate-pulse">
                <div className="h-8 bg-gray-200 rounded w-1/3 mb-6"></div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div className="h-32 bg-gray-200 rounded-xl"></div>
                    <div className="h-32 bg-gray-200 rounded-xl"></div>
                    <div className="h-32 bg-gray-200 rounded-xl"></div>
                </div>
            </div>
        )
    }

    if (!accuracy || !roi) return null

    return (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            {/* Header with Trust Focus */}
            <div className="p-6 border-b border-gray-100 bg-gradient-to-r from-blue-50/50 to-transparent">
                <div className="flex items-center justify-between flex-wrap gap-4">
                    <div>
                        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                            <ShieldCheck className="h-6 w-6 text-blue-600" />
                            {t('dashboard.modelPerformance.title')}
                        </h2>
                        <p className="text-sm text-gray-600 mt-1">
                            {t('dashboard.modelPerformance.subtitle')}
                        </p>
                    </div>
                    <Link
                        href="/track-record"
                        className="group flex items-center gap-2 text-sm font-semibold text-blue-600 hover:text-blue-700 transition-colors"
                    >
                        {t('dashboard.modelPerformance.viewAuditLog')}
                        <ArrowRight className="h-4 w-4 group-hover:translate-x-0.5 transition-transform" />
                    </Link>
                </div>
            </div>

            {/* Main Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-gray-100">

                {/* Accuracy Stat */}
                <div className="p-6 hover:bg-gray-50/50 transition-colors">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-blue-100 rounded-lg">
                            <Target className="h-5 w-5 text-blue-600" />
                        </div>
                        <span className="text-sm font-medium text-gray-600">{t('trackRecord.stats.overallAccuracy')}</span>
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className="text-3xl font-bold text-gray-900">{accuracy.overall.accuracy_percent}%</span>
                        <span className="text-sm text-gray-500">correct</span>
                    </div>
                    <div className="mt-2 text-xs text-gray-500 flex items-center gap-1">
                        <CheckCircle className="h-3 w-3 text-green-500" />
                        {accuracy.overall.correct_predictions} wins
                        <span className="mx-1">•</span>
                        <XCircle className="h-3 w-3 text-red-500" />
                        {accuracy.overall.total_predictions - accuracy.overall.correct_predictions} losses
                    </div>
                </div>

                {/* ROI Stat */}
                <div className="p-6 hover:bg-gray-50/50 transition-colors">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-green-100 rounded-lg">
                            <TrendingUp className="h-5 w-5 text-green-600" />
                        </div>
                        <span className="text-sm font-medium text-gray-600">{t('trackRecord.stats.roi')}</span>
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className={`text-3xl font-bold ${roi.roi_percent >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {roi.roi_percent >= 0 ? '+' : ''}{roi.roi_percent}%
                        </span>
                        <span className="text-sm text-gray-500">yield</span>
                    </div>
                    <div className="mt-2 text-xs text-gray-500">
                        Based on flat staking strategy
                    </div>
                </div>

                {/* Total Profit Stat */}
                <div className="p-6 hover:bg-gray-50/50 transition-colors">
                    <div className="flex items-center gap-3 mb-2">
                        <div className="p-2 bg-purple-100 rounded-lg">
                            <Trophy className="h-5 w-5 text-purple-600" />
                        </div>
                        <span className="text-sm font-medium text-gray-600">Total Profit</span>
                    </div>
                    <div className="flex items-baseline gap-2">
                        <span className={`text-3xl font-bold ${roi.total_profit_loss >= 0 ? 'text-purple-600' : 'text-gray-600'}`}>
                            {roi.total_profit_loss >= 0 ? '+' : ''}${roi.total_profit_loss.toFixed(0)}
                        </span>
                        <span className="text-sm text-gray-500">net</span>
                    </div>
                    <div className="mt-2 text-xs text-gray-500">
                        From {roi.total_bets} verified recommendations
                    </div>
                </div>
            </div>

            {/* Trust Footer */}
            <div className="bg-gray-50 p-4 border-t border-gray-100">
                <div className="flex items-center justify-center gap-6 text-xs text-gray-500">
                    <span className="flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5" />
                        {t('trackRecord.transparency.points.timestamped')}
                    </span>
                    <span className="flex items-center gap-1.5">
                        <ShieldCheck className="h-3.5 w-3.5" />
                        {t('trackRecord.transparency.points.verified')}
                    </span>
                </div>
            </div>
        </div>
    )
}
