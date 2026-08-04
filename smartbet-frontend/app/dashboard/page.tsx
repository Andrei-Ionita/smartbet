'use client';

/**
 * The dashboard is organised around what a person came here to do, not around
 * which widgets happen to exist.
 *
 * Two things were broken before this rewrite:
 *
 *  1. It redirected to /bankroll whenever `smartbet_session_id` was missing —
 *     and registration DELETES that key. A brand-new account could therefore
 *     never reach the dashboard at all; it bounced straight into bankroll
 *     setup with no explanation. Authentication now decides access, and the
 *     bankroll widgets simply wait for a bankroll.
 *  2. Disconnected widgets left a new user to infer the product from context.
 *     A first-session panel and an honest verified-record card now do that job.
 */

import React, { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import useSWR from 'swr';
import BankrollSummaryCard from '../components/dashboard/BankrollSummaryCard';
import ActiveBetsList from '../components/dashboard/ActiveBetsList';
import PersonalizedRecommendations from '../components/dashboard/PersonalizedRecommendations';
import OnboardingPanel from '../components/OnboardingPanel';
import EmptyState from '../components/EmptyState';
import { StatusBadge } from '../components/StatusBadge';
import { LayoutDashboard, Wallet } from 'lucide-react';

import { useLanguage } from '../contexts/LanguageContext';
import { useAuth } from '../contexts/AuthContext';
import { getCopy } from '../lib/terminology';
import { track } from '../lib/analytics';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function DashboardPage() {
    const router = useRouter();
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [ready, setReady] = useState(false);
    const { language } = useLanguage();
    const { isAuthenticated, isLoading: authLoading } = useAuth();
    const copy = getCopy(language);

    useEffect(() => {
        // A bankroll session is optional context, not an access requirement.
        setSessionId(localStorage.getItem('smartbet_session_id'));
        setReady(true);
        track('dashboard_visited', { surface: 'dashboard' });
    }, []);

    useEffect(() => {
        if (!authLoading && !isAuthenticated && ready && !sessionId) {
            router.push('/login');
        }
    }, [authLoading, isAuthenticated, ready, sessionId, router]);

    const { data: performanceData } = useSWR('/api/performance', fetcher, {
        refreshInterval: 120000,
    });
    const settledCount = performanceData?.data?.overall?.total_predictions ?? 0;

    if (!ready || authLoading) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center">
                <div
                    role="status"
                    aria-label="Loading dashboard"
                    className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"
                />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 pb-12">
            <div className="bg-white border-b border-gray-200">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-primary-100 rounded-lg">
                                <LayoutDashboard className="h-6 w-6 text-primary-600" />
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold text-gray-900">
                                    {copy.dashboard.title}
                                </h1>
                                <p className="text-sm text-gray-500">
                                    {copy.beta.primary}
                                </p>
                            </div>
                        </div>
                        <Link
                            href="/bankroll"
                            className="inline-flex min-h-[44px] items-center justify-center gap-2 rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
                        >
                            <Wallet className="h-4 w-4" />
                            {copy.dashboard.manageBankroll}
                        </Link>
                    </div>
                </div>
            </div>

            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <OnboardingPanel />

                {/* Verified-record status. Honest at zero rather than an empty
                    performance panel dominating the screen. */}
                <section
                    aria-labelledby="record-status"
                    className="mb-8 rounded-2xl border border-gray-200 bg-white p-6"
                >
                    <h2
                        id="record-status"
                        className="text-lg font-bold text-gray-900"
                    >
                        {copy.terms.verifiedRecord.label}
                    </h2>
                    {settledCount > 0 ? (
                        <div className="mt-3 flex flex-wrap items-center gap-4">
                            <p className="text-3xl font-bold text-gray-900">
                                {settledCount}
                            </p>
                            <p className="text-sm text-gray-600">
                                {copy.home.settledLabel}
                            </p>
                            <Link
                                href="/track-record"
                                className="ml-auto inline-flex min-h-[44px] items-center rounded-lg bg-gray-900 px-4 py-2 text-sm font-semibold text-white hover:bg-gray-700"
                            >
                                {copy.home.openRecord}
                            </Link>
                        </div>
                    ) : (
                        <div className="mt-3">
                            <p className="text-sm leading-relaxed text-gray-600">
                                {copy.dashboard.recordBuilding}
                            </p>
                            <div className="mt-4 flex flex-wrap gap-2">
                                <StatusBadge status="published_pending" size="sm" lang={language} />
                                <StatusBadge status="won" size="sm" lang={language} />
                                <StatusBadge status="lost" size="sm" lang={language} />
                            </div>
                            <Link
                                href="/track-record"
                                className="mt-4 inline-flex min-h-[44px] items-center rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50"
                            >
                                {copy.home.openRecord}
                            </Link>
                        </div>
                    )}
                </section>

                {sessionId ? (
                    <div className="space-y-8">
                        <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
                            <div className="lg:col-span-1">
                                <BankrollSummaryCard sessionId={sessionId} />
                            </div>
                            <div className="lg:col-span-2">
                                <ActiveBetsList sessionId={sessionId} />
                            </div>
                        </div>

                        <section aria-labelledby="dash-signals">
                            <div className="mb-4">
                                <StatusBadge status="live" size="sm" lang={language} />
                                <h2
                                    id="dash-signals"
                                    className="mt-2 text-xl font-bold text-gray-900"
                                >
                                    {copy.home.signalsHeading}
                                </h2>
                                <p className="mt-1 text-sm text-gray-600">
                                    {copy.terms.liveSignal.notInRecord}
                                </p>
                            </div>
                            <PersonalizedRecommendations sessionId={sessionId} />
                        </section>
                    </div>
                ) : (
                    <EmptyState state="first_dashboard" lang={language} />
                )}
            </div>
        </div>
    );
}
