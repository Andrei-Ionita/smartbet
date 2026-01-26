'use client'

import { Recommendation } from '@/src/types/recommendation'
import RecommendationCard from '../../components/RecommendationCard'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Calendar, Shield, Trophy } from 'lucide-react'

interface PredictionContentProps {
    recommendation: Recommendation
    leagueName: string
    homeTeam: string
    awayTeam: string
    kickoff: string
}

export default function PredictionContent({
    recommendation,
    leagueName,
    homeTeam,
    awayTeam,
    kickoff
}: PredictionContentProps) {
    const router = useRouter()

    const handleViewDetails = (interactionFixtureId: number) => {
        // We are already on the details page, so maybe scroll to specific section or do nothing
        console.log('Already on details for', interactionFixtureId)
    }

    // Format date for SEO text
    const dateObj = new Date(kickoff)
    const formattedDate = dateObj.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    })

    return (
        <div className="max-w-4xl mx-auto">
            {/* Breadcrumb / Back Navigation */}
            <div className="mb-6 flex items-center gap-2 text-sm text-gray-500">
                <Link href="/" className="hover:text-primary-600 flex items-center gap-1 transition-colors">
                    <ArrowLeft className="h-4 w-4" />
                    Home
                </Link>
                <span>/</span>
                <Link href="/explore" className="hover:text-primary-600 transition-colors">
                    Predictions
                </Link>
                <span>/</span>
                <span className="text-gray-900 font-medium truncate">
                    {homeTeam} vs {awayTeam}
                </span>
            </div>

            {/* SEO Header */}
            <div className="text-center mb-8">
                <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
                    {homeTeam} vs {awayTeam} Prediction & Betting Tips
                </h1>
                <div className="flex flex-wrap justify-center gap-4 text-gray-600 text-sm md:text-base">
                    <div className="flex items-center gap-2 bg-white px-4 py-2 rounded-full shadow-sm border border-gray-100">
                        <Trophy className="h-4 w-4 text-primary-500" />
                        <span className="font-medium">{leagueName}</span>
                    </div>
                    <div className="flex items-center gap-2 bg-white px-4 py-2 rounded-full shadow-sm border border-gray-100">
                        <Calendar className="h-4 w-4 text-primary-500" />
                        <span>{formattedDate}</span>
                    </div>
                    <div className="flex items-center gap-2 bg-white px-4 py-2 rounded-full shadow-sm border border-gray-100">
                        <Shield className="h-4 w-4 text-green-500" />
                        <span>AI Confidence: {Math.round(recommendation.confidence * 100)}%</span>
                    </div>
                </div>
            </div>

            {/* Main Card */}
            <div className="mb-12">
                <RecommendationCard
                    recommendation={recommendation}
                    onViewDetails={handleViewDetails}
                />
            </div>

            {/* SEO Content Section */}
            <div className="grid md:grid-cols-2 gap-8 mb-12">
                <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                    <h2 className="text-xl font-bold text-gray-900 mb-4">Match Analysis</h2>
                    <div className="prose prose-sm text-gray-600">
                        <p className="mb-4">
                            Our AI model has analyzed the upcoming match between <strong>{homeTeam}</strong> and <strong>{awayTeam}</strong> in the {leagueName}.
                            Arguments for the prediction include recent form, head-to-head records, and current market odds.
                        </p>
                        <p>
                            The system predicts a <strong>{Math.round(recommendation.confidence * 100)}% chance</strong> of a <strong>{recommendation.predicted_outcome}</strong> outcome.
                            {recommendation.ev && recommendation.ev > 0 && (
                                <span>
                                    {' '}Wait! We've also detected a <strong>{Math.round(recommendation.ev * 100)}% value edge</strong> against the bookmaker odds, making this a potentially profitable play.
                                </span>
                            )}
                        </p>
                    </div>
                </div>

                <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                    <h2 className="text-xl font-bold text-gray-900 mb-4">Key Stats</h2>
                    <ul className="space-y-3">
                        <li className="flex justify-between border-b border-gray-50 pb-2">
                            <span className="text-gray-600">Prediction</span>
                            <span className="font-bold text-gray-900">{recommendation.predicted_outcome}</span>
                        </li>
                        <li className="flex justify-between border-b border-gray-50 pb-2">
                            <span className="text-gray-600">Confidence</span>
                            <span className="font-bold text-primary-600">{Math.round(recommendation.confidence * 100)}%</span>
                        </li>
                        <li className="flex justify-between border-b border-gray-50 pb-2">
                            <span className="text-gray-600">Best Odds</span>
                            <span className="font-bold text-gray-900">{recommendation.odds?.toFixed(2) || 'N/A'}</span>
                        </li>
                        <li className="flex justify-between pb-2">
                            <span className="text-gray-600">League</span>
                            <span className="font-medium text-gray-900">{leagueName}</span>
                        </li>
                    </ul>
                </div>
            </div>

            {/* Disclaimer */}
            <div className="text-center text-xs text-gray-400 mt-12 mb-4">
                <p>Predictions are based on statistical analysis and machine learning. Gambling involves risk. Please gamble responsibly.</p>
            </div>
        </div>
    )
}
