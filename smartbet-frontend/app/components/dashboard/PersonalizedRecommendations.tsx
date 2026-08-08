'use client';

import React, { useEffect, useState } from 'react';
import { TrendingUp } from 'lucide-react';

interface PersonalizedRecommendationsProps {
    sessionId: string;
}

/**
 * Only the fields the monitoring DTO actually publishes.
 *
 * `odds`, `expected_value` and `stake_recommendation` are gone: the proxy
 * stopped emitting prices and money (they were derived by string-matching the
 * outcome against the 1X2 board), and a stake figure sized from an
 * uncalibrated signal score is not a stake size.
 */
interface Recommendation {
    fixture_id: number;
    home_team: string;
    away_team: string;
    league: string;
    kickoff: string;
    predicted_outcome: string;
    confidence: number;
}

export default function PersonalizedRecommendations({ sessionId }: PersonalizedRecommendationsProps) {
    const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
    const [loading, setLoading] = useState(true);

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

    /* handlePlaceBet() is gone.
       It POSTed a "recommended_stake" to the bankroll ledger and confirmed
       with an alert reading "Bet placed successfully! $X on Home" — a
       one-click staking instruction sitting directly beneath a panel that
       says BetGlitch does not size stakes. The stake it posted was sized from
       the signal score, which is a relative ranking rather than a calibrated
       probability, so the figure never had a defensible basis. Recording a
       bet you actually placed belongs on the bankroll page, where YOU enter
       the stake and the price you got. */

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
                <h3 className="text-lg font-bold text-gray-900 mb-2">No live signals for you right now</h3>
                <p className="text-gray-500 mb-8 max-w-md mx-auto">
                    Nothing is ranked for your filters at the moment. Plenty of fixtures are still open to explore.
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
                                    <span className="bg-blue-100 text-blue-800 text-xs font-bold px-2 py-1 rounded">TOP RANKED</span>
                                )}
                            </div>
                            <div className="flex justify-between items-center">
                                <h3 className="font-bold text-gray-900">{rec.away_team}</h3>
                                {rec.predicted_outcome.toLowerCase() === 'away' && (
                                    <span className="bg-blue-100 text-blue-800 text-xs font-bold px-2 py-1 rounded">TOP RANKED</span>
                                )}
                            </div>
                        </div>

                        {/* Prediction Stats */}
                        <div className="grid grid-cols-2 gap-4 mb-6">
                            <div className="bg-gray-50 p-3 rounded-lg">
                                {/* Was "Confidence · 66%", which reads as the
                                    chance of the outcome. It is a ranking. */}
                                <p className="text-xs text-gray-500 mb-1">Signal score</p>
                                <div className="flex items-center gap-2">
                                    <div className="flex-1 bg-gray-200 rounded-full h-1.5">
                                        <div className="bg-blue-500 h-1.5 rounded-full" style={{ width: `${rec.confidence}%` }}></div>
                                    </div>
                                    <span className="text-sm font-bold text-gray-900">{rec.confidence.toFixed(0)} / 100</span>
                                </div>
                            </div>
                            <div className="bg-gray-50 p-3 rounded-lg">
                                {/* Was "Value (EV) · +8.4%" in green. EV is
                                    derived from the signal score, so no numeric
                                    value is published — only the status. */}
                                <p className="text-xs text-gray-500 mb-1">Value status</p>
                                <p className="text-sm text-gray-600">Not yet assessed</p>
                            </div>
                        </div>

                        {/* No stake figure.
                            This panel rendered a dollar "Recommended Stake" and
                            a bankroll percentage sized by a Kelly-family
                            strategy whose probability input is the signal score.
                            The signal score is a relative ranking, not a
                            calibrated probability, so a Kelly fraction built on
                            it is not a stake size — it is a number with the
                            shape of one. The same defect was removed from the
                            betting calculator; leaving it here would simply move
                            the advice to another surface. */}
                        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-6">
                            <p className="text-xs font-medium uppercase tracking-wide text-gray-600">
                                Stake sizing
                            </p>
                            <p className="mt-1 text-sm text-gray-600">
                                BetGlitch does not size stakes from a signal score. It is a
                                relative ranking, not a calibrated probability, so no staking
                                figure can honestly be derived from it. Any stake is your own
                                decision — you can lose everything you wager.
                            </p>
                        </div>

                        {/* Reading, not transacting. The old control was
                            "Place Bet $12.40" — a staking instruction. */}
                        <a
                            href={`/explore?fixture=${rec.fixture_id}`}
                            className="flex min-h-[44px] w-full items-center justify-center gap-2 rounded-lg border border-gray-300 px-4 py-3 font-medium text-gray-700 transition-colors hover:bg-gray-50"
                        >
                            View signal details
                        </a>
                    </div>
                </div>
            ))}
        </div>
    );
}
