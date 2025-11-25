'use client';

import React, { useEffect, useState } from 'react';
import { Clock, ArrowRight } from 'lucide-react';

interface ActiveBetsListProps {
    sessionId: string;
}

interface Transaction {
    id: number;
    match_description: string;
    selected_outcome: string;
    odds: number;
    stake_amount: number;
    potential_return: number;
    created_at: string;
    status: string;
}

export default function ActiveBetsList({ sessionId }: ActiveBetsListProps) {
    const [bets, setBets] = useState<Transaction[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchActiveBets = async () => {
            try {
                const response = await fetch(`/api/bankroll/${sessionId}/transactions/?status=pending&limit=5`);
                const result = await response.json();
                if (result.transactions) {
                    setBets(result.transactions);
                }
            } catch (error) {
                console.error('Failed to fetch active bets:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchActiveBets();
    }, [sessionId]);

    if (loading) {
        return (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 h-full animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-1/3 mb-6"></div>
                <div className="space-y-4">
                    {[1, 2, 3].map((i) => (
                        <div key={i} className="h-16 bg-gray-100 rounded-lg"></div>
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 h-full flex flex-col">
            <div className="flex items-center justify-between mb-6">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                    <Clock className="h-5 w-5 text-gray-500" />
                    Active Bets
                    <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
                        {bets.length}
                    </span>
                </h3>
                <a href="/bankroll" className="text-sm text-primary-600 hover:text-primary-700 font-medium flex items-center gap-1">
                    View All <ArrowRight className="h-4 w-4" />
                </a>
            </div>

            {bets.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center py-8">
                    <div className="bg-gray-50 p-4 rounded-full mb-3">
                        <Clock className="h-8 w-8 text-gray-400" />
                    </div>
                    <p className="text-gray-900 font-medium">No active bets</p>
                    <p className="text-sm text-gray-500 mt-1">Check the recommendations below to place a bet!</p>
                </div>
            ) : (
                <div className="space-y-3">
                    {bets.map((bet) => (
                        <div key={bet.id} className="border border-gray-100 rounded-lg p-4 hover:bg-gray-50 transition-colors">
                            <div className="flex justify-between items-start mb-2">
                                <div>
                                    <p className="font-medium text-gray-900">{bet.match_description}</p>
                                    <p className="text-sm text-gray-500">
                                        {new Date(bet.created_at).toLocaleDateString()} • {new Date(bet.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                    </p>
                                </div>
                                <span className="bg-yellow-100 text-yellow-800 text-xs font-medium px-2 py-1 rounded">
                                    Pending
                                </span>
                            </div>
                            <div className="flex items-center justify-between text-sm">
                                <div className="flex items-center gap-3">
                                    <span className="font-medium text-gray-700">{bet.selected_outcome}</span>
                                    <span className="text-gray-400">@</span>
                                    <span className="font-medium text-gray-900">{bet.odds.toFixed(2)}</span>
                                </div>
                                <div className="text-right">
                                    <p className="text-gray-500">Stake: <span className="font-medium text-gray-900">${bet.stake_amount.toFixed(2)}</span></p>
                                    <p className="text-xs text-green-600 font-medium">Potential: +${(bet.potential_return - bet.stake_amount).toFixed(2)}</p>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}
