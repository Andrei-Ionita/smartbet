'use client';

import React, { useEffect, useState } from 'react';
import { TrendingUp, AlertCircle, CheckCircle2, DollarSign } from 'lucide-react';

interface PersonalizedRecommendationsProps {
    sessionId: string;
}

interface Recommendation {
    fixture_id: number;
    home_team: string;
    away_team: string;
    league: string;
    kickoff: string;
    predicted_outcome: string;
    confidence: number;
    expected_value: number;
    odds: number;
    explanation: string;
    stake_recommendation?: {
        recommended_stake: number;
        stake_percentage: number;
        currency: string;
        strategy: string;
        risk_level: string;
        risk_explanation: string;
        warnings: string[];
    };
}

export default function PersonalizedRecommendations({ sessionId }: PersonalizedRecommendationsProps) {
    const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
    const [loading, setLoading] = useState(true);
    const [placingBetId, setPlacingBetId] = useState<number | null>(null);

    useEffect(() => {
        const fetchRecommendations = async () => {
            try {
                // Fetch recommendations with session_id to get personalized stake calculations
                const response = await fetch(`/api/django/recommended-predictions?session_id=${sessionId}&limit=6`);
                const result = await response.json();
                if (result.success && result.data) {
                    setRecommendations(result.data);
                }
            } catch (error) {
                console.error('Failed to fetch recommendations:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchRecommendations();
    }, [sessionId]);

    const handlePlaceBet = async (rec: Recommendation) => {
        if (!rec.stake_recommendation) return;

        setPlacingBetId(rec.fixture_id);
        try {
            const response = await fetch('/api/bankroll/record-bet', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: sessionId,
                    fixture_id: rec.fixture_id,
                    selected_outcome: rec.predicted_outcome,
                    odds: rec.odds,
                    stake_amount: rec.stake_recommendation.recommended_stake,
                    match_description: `${rec.home_team} vs ${rec.away_team}`,
                    recommended_stake: rec.stake_recommendation.recommended_stake
                })
            });

            const result = await response.json();

            if (response.ok) {
                // Show success (you might want a toast notification here)
                alert(`Bet placed successfully! $${rec.stake_recommendation.recommended_stake} on ${rec.predicted_outcome}`);
                // Remove from list or mark as placed
                setRecommendations(prev => prev.filter(r => r.fixture_id !== rec.fixture_id));
            } else {
                alert(`Failed to place bet: ${result.error}`);
            }
        } catch (error) {
            console.error('Error placing bet:', error);
            alert('An error occurred while placing the bet');
        } finally {
            setPlacingBetId(null);
        }
    };

    if (loading) {
        return (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {[1, 2, 3].map((i) => (
                    <div key={i} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 h-64 animate-pulse">
                        <div className="h-4 bg-gray-200 rounded w-1/3 mb-4"></div>
                        <div className="h-8 bg-gray-200 rounded w-3/4 mb-6"></div>
                        <div className="h-32 bg-gray-100 rounded"></div>
                    </div>
                ))}
            </div>
        );
    }

    if (recommendations.length === 0) {
        return (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-12 text-center">
                <div className="bg-primary-50 p-4 rounded-full inline-block mb-4">
                    <TrendingUp className="h-8 w-8 text-primary-400" />
                </div>
                <h3 className="text-lg font-bold text-gray-900 mb-2">Ready to find your first bet?</h3>
                <p className="text-gray-500 mb-8 max-w-md mx-auto">
                    We don't have any personalized "Smart Picks" for you right now, but there are plenty of matches happening!
                </p>
                <div className="flex flex-col sm:flex-row gap-4 justify-center">
                    <a
                        href="/explore"
                        className="px-6 py-3 bg-primary-600 text-white font-medium rounded-lg hover:bg-primary-700 transition-colors flex items-center justify-center gap-2"
                    >
                        Explore All Fixtures
                    </a>
                    <a
                        href="/bankroll"
                        className="px-6 py-3 bg-white text-gray-700 font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
                    >
                        Adjust Bankroll Settings
                    </a>
                </div>
            </div>
        );
    }

    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {recommendations.map((rec) => (
                <div key={rec.fixture_id} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden hover:shadow-md transition-shadow">
                    {/* Header */}
                    <div className="p-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">{rec.league}</span>
                        <span className="text-xs text-gray-400">
                            {new Date(rec.kickoff).toLocaleDateString()} {new Date(rec.kickoff).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                    </div>

                    <div className="p-6">
                        {/* Match Info */}
                        <div className="mb-6">
                            <div className="flex justify-between items-center mb-2">
                                <h3 className="font-bold text-gray-900">{rec.home_team}</h3>
                                {rec.predicted_outcome.toLowerCase() === 'home' && (
                                    <span className="bg-blue-100 text-blue-800 text-xs font-bold px-2 py-1 rounded">PICK</span>
                                )}
                            </div>
                            <div className="flex justify-between items-center">
                                <h3 className="font-bold text-gray-900">{rec.away_team}</h3>
                                {rec.predicted_outcome.toLowerCase() === 'away' && (
                                    <span className="bg-blue-100 text-blue-800 text-xs font-bold px-2 py-1 rounded">PICK</span>
                                )}
                            </div>
                        </div>

                        {/* Prediction Stats */}
                        <div className="grid grid-cols-2 gap-4 mb-6">
                            <div className="bg-gray-50 p-3 rounded-lg">
                                <p className="text-xs text-gray-500 mb-1">Confidence</p>
                                <div className="flex items-center gap-2">
                                    <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                                        <div className="bg-green-500 h-1.5 rounded-full" style={{ width: `${rec.confidence}%` }}></div>
                                    </div>
                                    <span className="text-sm font-bold text-gray-900">{rec.confidence.toFixed(0)}%</span>
                                </div>
                            </div>
                            <div className="bg-gray-50 p-3 rounded-lg">
                                <p className="text-xs text-gray-500 mb-1">Value (EV)</p>
                                <p className="text-sm font-bold text-green-600">+{rec.expected_value?.toFixed(1)}%</p>
                            </div>
                        </div>

                        {/* Stake Recommendation */}
                        {rec.stake_recommendation ? (
                            <div className="bg-blue-50 border border-blue-100 rounded-lg p-4 mb-6">
                                <div className="flex justify-between items-start mb-2">
                                    <div>
                                        <p className="text-xs font-medium text-blue-800 uppercase tracking-wide">Recommended Stake</p>
                                        <p className="text-2xl font-bold text-blue-900">
                                            ${rec.stake_recommendation.recommended_stake.toFixed(2)}
                                        </p>
                                    </div>
                                    <span className="text-xs bg-blue-200 text-blue-800 px-2 py-1 rounded font-medium">
                                        {rec.stake_recommendation.stake_percentage.toFixed(1)}%
                                    </span>
                                </div>
                                <p className="text-xs text-blue-700 mb-2">
                                    Strategy: {rec.stake_recommendation.strategy.replace(/_/g, ' ')} ({rec.stake_recommendation.risk_level} risk)
                                </p>

                                {rec.stake_recommendation.warnings.length > 0 && (
                                    <div className="mt-2 pt-2 border-t border-blue-200">
                                        {rec.stake_recommendation.warnings.map((warning, idx) => (
                                            <p key={idx} className="text-xs text-orange-700 flex items-center gap-1">
                                                <AlertCircle className="h-3 w-3" /> {warning}
                                            </p>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ) : (
                            <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6 text-center">
                                <p className="text-sm text-gray-500">Set up your bankroll to see stake recommendations</p>
                            </div>
                        )}

                        {/* Action Button */}
                        <button
                            onClick={() => handlePlaceBet(rec)}
                            disabled={!rec.stake_recommendation || placingBetId === rec.fixture_id}
                            className="w-full py-3 px-4 bg-primary-600 hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
                        >
                            {placingBetId === rec.fixture_id ? (
                                <>
                                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                                    Placing Bet...
                                </>
                            ) : (
                                <>
                                    <DollarSign className="h-4 w-4" />
                                    Place Bet ${rec.stake_recommendation?.recommended_stake.toFixed(2) || '0.00'}
                                </>
                            )}
                        </button>
                    </div>
                </div>
            ))}
        </div>
    );
}
