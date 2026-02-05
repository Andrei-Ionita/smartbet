'use client';

import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import Link from 'next/link';

interface ProGateProps {
    children: React.ReactNode;
    feature?: string;
    showUpgradePrompt?: boolean;
}

/**
 * ProGate - Wrapper component to gate features for Pro users only
 * 
 * Usage:
 *   <ProGate feature="Betting Calculator">
 *     <BettingCalculatorContent />
 *   </ProGate>
 */
export function ProGate({ children, feature = 'This feature', showUpgradePrompt = true }: ProGateProps) {
    const { isPro, isAuthenticated } = useAuth();

    // Pro users see the content
    if (isPro) {
        return <>{children}</>;
    }

    // Free users see upgrade prompt
    if (showUpgradePrompt) {
        return (
            <div className="relative">
                {/* Blurred preview of content */}
                <div className="filter blur-sm pointer-events-none opacity-60">
                    {children}
                </div>

                {/* Upgrade overlay */}
                <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-b from-transparent via-white/80 to-white">
                    <div className="text-center p-6 bg-white rounded-xl shadow-lg border border-gray-200 max-w-sm">
                        <div className="w-12 h-12 mx-auto mb-4 bg-gradient-to-br from-violet-500 to-purple-600 rounded-full flex items-center justify-center">
                            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                            </svg>
                        </div>
                        <h3 className="text-lg font-semibold text-gray-900 mb-2">
                            {feature} is a Pro Feature
                        </h3>
                        <p className="text-sm text-gray-600 mb-4">
                            Upgrade to Pro for just <span className="font-bold text-violet-600">€5/month</span> to unlock all features.
                        </p>
                        {isAuthenticated ? (
                            <Link
                                href="/pricing"
                                className="inline-block w-full py-2 px-4 bg-gradient-to-r from-violet-600 to-purple-600 text-white font-medium rounded-lg hover:from-violet-700 hover:to-purple-700 transition-all"
                            >
                                Upgrade to Pro
                            </Link>
                        ) : (
                            <div className="space-y-2">
                                <Link
                                    href="/register"
                                    className="inline-block w-full py-2 px-4 bg-gradient-to-r from-violet-600 to-purple-600 text-white font-medium rounded-lg hover:from-violet-700 hover:to-purple-700 transition-all"
                                >
                                    Sign Up for Pro
                                </Link>
                                <p className="text-xs text-gray-500">
                                    Already have an account? <Link href="/login" className="text-violet-600 hover:underline">Log in</Link>
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        );
    }

    // If no upgrade prompt, just return null
    return null;
}

/**
 * ProBadge - Shows a small "PRO" badge for pro features
 */
export function ProBadge() {
    return (
        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-gradient-to-r from-violet-500 to-purple-600 text-white">
            PRO
        </span>
    );
}

/**
 * useProFeature - Hook to check if a Pro feature should be shown
 */
export function useProFeature() {
    const { isPro, tier, isAuthenticated } = useAuth();

    return {
        isPro,
        tier,
        isAuthenticated,
        canAccess: isPro,
        shouldShowUpgrade: !isPro && isAuthenticated,
        shouldShowSignup: !isPro && !isAuthenticated
    };
}
