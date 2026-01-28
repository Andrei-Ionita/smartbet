'use client'

import { useMemo } from 'react'
import { CheckCircle, XCircle, Clock, TrendingUp } from 'lucide-react'
import Link from 'next/link'
import useSWR from 'swr'

interface PredictionResult {
    id: number
    home_team: string
    away_team: string
    predicted_outcome: string
    actual_outcome?: string
    is_correct?: boolean
    confidence: number
    kickoff: string
    league: string
}

interface RecentResultsWidgetProps {
    language?: 'en' | 'ro'
}

const fetcher = (url: string) => fetch(url).then(res => res.json())

export default function RecentResultsWidget({ language = 'en' }: RecentResultsWidgetProps) {
    // Fetch recent predictions from track record API
    const { data, isLoading, error } = useSWR('/api/performance', fetcher, {
        refreshInterval: 120000,
    })

    // Extract recent completed predictions
    const recentResults = useMemo(() => {
        if (!data?.data?.predictions) return []

        return data.data.predictions
            .filter((p: any) => p.actual_outcome && p.actual_outcome !== 'pending')
            .slice(0, 10)
            .map((p: any) => ({
                id: p.id,
                home_team: p.home_team,
                away_team: p.away_team,
                predicted_outcome: p.predicted_outcome,
                actual_outcome: p.actual_outcome,
                is_correct: p.is_correct,
                confidence: p.confidence,
                kickoff: p.kickoff,
                league: p.league
            }))
    }, [data])

    const stats = useMemo(() => {
        if (recentResults.length === 0) return { wins: 0, losses: 0, rate: 0 }
        const wins = recentResults.filter((r: PredictionResult) => r.is_correct).length
        return {
            wins,
            losses: recentResults.length - wins,
            rate: Math.round((wins / recentResults.length) * 100)
        }
    }, [recentResults])

    if (isLoading) {
        return (
            <div className="bg-white rounded-xl border border-gray-200 p-4 animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-32 mb-4"></div>
                <div className="space-y-2">
                    {[...Array(5)].map((_, i) => (
                        <div key={i} className="h-8 bg-gray-100 rounded"></div>
                    ))}
                </div>
            </div>
        )
    }

    if (error || recentResults.length === 0) {
        return null // Hide widget if no data
    }

    const text = {
        en: {
            title: 'Recent Results',
            won: 'Won',
            lost: 'Lost',
            viewAll: 'View All',
            last10: 'Last 10 Predictions'
        },
        ro: {
            title: 'Rezultate Recente',
            won: 'Câștigat',
            lost: 'Pierdut',
            viewAll: 'Vezi Tot',
            last10: 'Ultimele 10 Predicții'
        }
    }

    const t = text[language]

    return (
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            {/* Header */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-4 py-3 border-b border-gray-200">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <TrendingUp className="h-4 w-4 text-blue-600" />
                        <span className="font-semibold text-gray-900 text-sm">{t.title}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs">
                        <span className="flex items-center gap-1 text-green-600 font-medium">
                            <CheckCircle className="h-3 w-3" />
                            {stats.wins} {t.won}
                        </span>
                        <span className="flex items-center gap-1 text-red-500 font-medium">
                            <XCircle className="h-3 w-3" />
                            {stats.losses} {t.lost}
                        </span>
                        <span className="text-blue-600 font-bold">
                            {stats.rate}%
                        </span>
                    </div>
                </div>
            </div>

            {/* Results Grid */}
            <div className="p-3">
                <div className="flex gap-1 flex-wrap">
                    {recentResults.map((result: PredictionResult, idx: number) => (
                        <div
                            key={result.id || idx}
                            className={`w-7 h-7 rounded-md flex items-center justify-center text-xs font-bold transition-all hover:scale-110 cursor-default ${result.is_correct
                                    ? 'bg-green-100 text-green-700 border border-green-200'
                                    : 'bg-red-100 text-red-600 border border-red-200'
                                }`}
                            title={`${result.home_team} vs ${result.away_team}: ${result.predicted_outcome} (${result.is_correct ? 'Won' : 'Lost'})`}
                        >
                            {result.is_correct ? '✓' : '✗'}
                        </div>
                    ))}
                </div>

                {/* Match details (last 5) */}
                <div className="mt-3 space-y-1.5">
                    {recentResults.slice(0, 5).map((result: PredictionResult, idx: number) => (
                        <div
                            key={result.id || idx}
                            className="flex items-center justify-between text-xs py-1.5 px-2 rounded-lg bg-gray-50 hover:bg-gray-100 transition-colors"
                        >
                            <div className="flex items-center gap-2 flex-1 min-w-0">
                                <span className={`w-5 h-5 rounded flex items-center justify-center text-[10px] font-bold ${result.is_correct
                                        ? 'bg-green-100 text-green-700'
                                        : 'bg-red-100 text-red-600'
                                    }`}>
                                    {result.is_correct ? '✓' : '✗'}
                                </span>
                                <span className="text-gray-700 truncate font-medium">
                                    {result.home_team} vs {result.away_team}
                                </span>
                            </div>
                            <span className="text-gray-500 text-[10px] uppercase ml-2">
                                {result.predicted_outcome}
                            </span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Footer */}
            <div className="px-4 py-2 border-t border-gray-100 bg-gray-50">
                <Link
                    href="/track-record"
                    className="text-xs text-blue-600 hover:text-blue-800 font-medium flex items-center justify-center gap-1 hover:underline"
                >
                    {t.viewAll}
                    <span className="text-gray-400">→</span>
                </Link>
            </div>
        </div>
    )
}
