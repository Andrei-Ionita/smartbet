'use client';

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import BankrollSummaryCard from '../components/dashboard/BankrollSummaryCard';
import ActiveBetsList from '../components/dashboard/ActiveBetsList';
import PersonalizedRecommendations from '../components/dashboard/PersonalizedRecommendations';
import { LayoutDashboard, Wallet, TrendingUp, History } from 'lucide-react';

export default function DashboardPage() {
    const router = useRouter();
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        // Check for session
        const storedSessionId = localStorage.getItem('smartbet_session_id');
        if (!storedSessionId) {
            // Redirect to login or bankroll setup if no session
            router.push('/bankroll');
            return;
        }
        setSessionId(storedSessionId);
        setIsLoading(false);
    }, [router]);

    if (isLoading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 pb-12">
            {/* Dashboard Header */}
            <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-primary-100 rounded-lg">
                                <LayoutDashboard className="h-6 w-6 text-primary-600" />
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold text-gray-900">My Dashboard</h1>
                                <p className="text-sm text-gray-500">Welcome back to your betting portal</p>
                            </div>
                        </div>
                        <div className="flex gap-3">
                            <button
                                onClick={() => router.push('/bankroll')}
                                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                            >
                                <Wallet className="h-4 w-4" />
                                Manage Bankroll
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
                {/* Top Row: Bankroll & Quick Stats */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Bankroll Summary (Takes up 1/3) */}
                    <div className="lg:col-span-1">
                        {sessionId && <BankrollSummaryCard sessionId={sessionId} />}
                    </div>

                    {/* Active Bets (Takes up 2/3) */}
                    <div className="lg:col-span-2">
                        {sessionId && <ActiveBetsList sessionId={sessionId} />}
                    </div>
                </div>

                {/* Main Section: Personalized Recommendations */}
                <div>
                    <div className="flex items-center gap-2 mb-6">
                        <TrendingUp className="h-6 w-6 text-primary-600" />
                        <h2 className="text-xl font-bold text-gray-900">Your Smart Picks</h2>
                    </div>
                    {sessionId && <PersonalizedRecommendations sessionId={sessionId} />}
                </div>
            </div>
        </div>
    );
}
