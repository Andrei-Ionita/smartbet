'use client';

import React, { useEffect, useState } from 'react';
import { Wallet, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import { useRouter } from 'next/navigation';

interface BankrollSummaryProps {
    sessionId: string;
}

interface BankrollData {
    current_bankroll: number;
    currency: string;
    total_profit_loss: number;
    roi_percent: number;
    daily_loss_amount: number;
    daily_loss_limit: number | null;
    is_daily_limit_reached: boolean;
    risk_profile: string;
}

export default function BankrollSummaryCard({ sessionId }: BankrollSummaryProps) {
    const router = useRouter();
    const [data, setData] = useState<BankrollData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchBankroll = async () => {
            try {
                const response = await fetch(`/api/bankroll/${sessionId}/`);
                const result = await response.json();
                if (result.bankroll) {
                    setData(result.bankroll);
                }
            } catch (error) {
                console.error('Failed to fetch bankroll summary:', error);
            } finally {
                setLoading(false);
            }
        };

        fetchBankroll();
    }, [sessionId]);

    const formatCurrency = (amount: number, currency: string) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: currency,
        }).format(amount);
    };

    if (loading) {
        return (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 h-full animate-pulse">
                <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
                <div className="h-8 bg-gray-200 rounded w-3/4 mb-4"></div>
                <div className="h-4 bg-gray-200 rounded w-full"></div>
            </div>
        );
    }

    if (!data) return null;

    const isProfitable = data.total_profit_loss >= 0;

    return (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 h-full flex flex-col">
            <div className="flex items-center justify-between mb-6">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                    <Wallet className="h-5 w-5 text-gray-500" />
                    Bankroll Status
                </h3>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${data.risk_profile === 'aggressive' ? 'bg-red-100 text-red-800' :
                        data.risk_profile === 'balanced' ? 'bg-blue-100 text-blue-800' :
                            'bg-green-100 text-green-800'
                    }`}>
                    {data.risk_profile.charAt(0).toUpperCase() + data.risk_profile.slice(1)}
                </span>
            </div>

            <div className="mb-6">
                <p className="text-sm text-gray-500 mb-1">Available Balance</p>
                <p className="text-3xl font-bold text-gray-900">
                    {formatCurrency(data.current_bankroll, data.currency)}
                </p>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
                <div className={`p-3 rounded-lg ${isProfitable ? 'bg-green-50' : 'bg-red-50'}`}>
                    <p className="text-xs text-gray-600 mb-1">Total P/L</p>
                    <p className={`font-semibold ${isProfitable ? 'text-green-700' : 'text-red-700'}`}>
                        {isProfitable ? '+' : ''}{formatCurrency(data.total_profit_loss, data.currency)}
                    </p>
                </div>
                <div className="p-3 rounded-lg bg-gray-50">
                    <p className="text-xs text-gray-600 mb-1">ROI</p>
                    <p className={`font-semibold ${data.roi_percent >= 0 ? 'text-green-700' : 'text-red-700'}`}>
                        {data.roi_percent >= 0 ? '+' : ''}{data.roi_percent.toFixed(1)}%
                    </p>
                </div>
            </div>

            {data.daily_loss_limit && (
                <div className="mt-auto pt-4 border-t border-gray-100">
                    <div className="flex justify-between text-xs text-gray-500 mb-2">
                        <span>Daily Loss Limit</span>
                        <span>{formatCurrency(data.daily_loss_amount, data.currency)} / {formatCurrency(data.daily_loss_limit, data.currency)}</span>
                    </div>
                    <div className="w-full bg-gray-100 rounded-full h-2">
                        <div
                            className={`h-2 rounded-full transition-all ${data.is_daily_limit_reached ? 'bg-red-500' : 'bg-blue-500'}`}
                            style={{ width: `${Math.min((data.daily_loss_amount / data.daily_loss_limit) * 100, 100)}%` }}
                        />
                    </div>
                    {data.is_daily_limit_reached && (
                        <p className="text-xs text-red-600 mt-2 flex items-center gap-1">
                            <AlertTriangle className="h-3 w-3" />
                            Limit reached - betting paused
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}
