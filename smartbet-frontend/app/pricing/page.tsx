'use client'

import { useAuth } from '../contexts/AuthContext'
import Link from 'next/link'
import { Check, X, Zap, Calculator, Bell, Clock, BarChart3, Download } from 'lucide-react'

export default function PricingPage() {
    const { isAuthenticated, isPro } = useAuth()

    const features = [
        { name: 'Daily Predictions', free: '3 best picks', pro: 'All picks (10-20+)', icon: BarChart3 },
        { name: 'Prediction Access', free: '12-hour delay', pro: 'Real-time', icon: Clock },
        { name: 'Betting Calculator', free: false, pro: true, icon: Calculator },
        { name: 'Email Alerts', free: false, pro: true, icon: Bell },
        { name: 'Historical Export', free: false, pro: true, icon: Download },
        { name: 'Track Record', free: true, pro: true, icon: BarChart3 },
        { name: 'Confidence Scores', free: true, pro: true, icon: Check },
        { name: 'EV Analysis', free: true, pro: true, icon: Check },
    ]

    return (
        <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white py-12">
            <div className="max-w-5xl mx-auto px-4">
                {/* Header */}
                <div className="text-center mb-12">
                    <h1 className="text-4xl font-bold text-gray-900 mb-4">
                        Simple, Transparent Pricing
                    </h1>
                    <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                        Start free with our best picks. Upgrade to Pro for unlimited access to all predictions and tools.
                    </p>
                </div>

                {/* Pricing Cards */}
                <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
                    {/* Free Tier */}
                    <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-8">
                        <div className="text-center mb-6">
                            <h2 className="text-2xl font-bold text-gray-900">Free</h2>
                            <div className="mt-4">
                                <span className="text-4xl font-bold">€0</span>
                                <span className="text-gray-500">/month</span>
                            </div>
                            <p className="text-gray-600 mt-2">Perfect for trying us out</p>
                        </div>

                        <ul className="space-y-4 mb-8">
                            {features.map((feature) => (
                                <li key={feature.name} className="flex items-center gap-3">
                                    {typeof feature.free === 'boolean' ? (
                                        feature.free ? (
                                            <Check className="h-5 w-5 text-green-500 flex-shrink-0" />
                                        ) : (
                                            <X className="h-5 w-5 text-gray-300 flex-shrink-0" />
                                        )
                                    ) : (
                                        <Check className="h-5 w-5 text-green-500 flex-shrink-0" />
                                    )}
                                    <span className={typeof feature.free === 'boolean' && !feature.free ? 'text-gray-400' : 'text-gray-700'}>
                                        {feature.name}
                                        {typeof feature.free === 'string' && (
                                            <span className="text-sm text-gray-500 ml-1">({feature.free})</span>
                                        )}
                                    </span>
                                </li>
                            ))}
                        </ul>

                        {isAuthenticated ? (
                            <div className="text-center py-3 text-gray-500 bg-gray-50 rounded-lg">
                                Current Plan
                            </div>
                        ) : (
                            <Link
                                href="/register"
                                className="block w-full py-3 text-center font-semibold text-violet-600 border-2 border-violet-600 rounded-lg hover:bg-violet-50 transition-colors"
                            >
                                Get Started Free
                            </Link>
                        )}
                    </div>

                    {/* Pro Tier */}
                    <div className="bg-gradient-to-br from-violet-600 to-purple-700 rounded-2xl shadow-xl p-8 text-white relative overflow-hidden">
                        {/* Popular Badge */}
                        <div className="absolute top-4 right-4 bg-yellow-400 text-yellow-900 text-xs font-bold px-3 py-1 rounded-full">
                            MOST POPULAR
                        </div>

                        <div className="text-center mb-6">
                            <div className="flex items-center justify-center gap-2 mb-2">
                                <Zap className="h-6 w-6" />
                                <h2 className="text-2xl font-bold">Pro</h2>
                            </div>
                            <div className="mt-4">
                                <span className="text-4xl font-bold">€5</span>
                                <span className="text-violet-200">/month</span>
                            </div>
                            <p className="text-violet-200 mt-2">Everything you need to win</p>
                        </div>

                        <ul className="space-y-4 mb-8">
                            {features.map((feature) => (
                                <li key={feature.name} className="flex items-center gap-3">
                                    <Check className="h-5 w-5 text-green-300 flex-shrink-0" />
                                    <span>
                                        {feature.name}
                                        {typeof feature.pro === 'string' && (
                                            <span className="text-sm text-violet-200 ml-1">({feature.pro})</span>
                                        )}
                                    </span>
                                </li>
                            ))}
                        </ul>

                        {isPro ? (
                            <div className="text-center py-3 bg-white/20 rounded-lg">
                                ✓ You&apos;re on Pro
                            </div>
                        ) : isAuthenticated ? (
                            <button
                                className="block w-full py-3 text-center font-semibold bg-white text-violet-600 rounded-lg hover:bg-gray-50 transition-colors"
                            >
                                Upgrade Now
                            </button>
                        ) : (
                            <Link
                                href="/register"
                                className="block w-full py-3 text-center font-semibold bg-white text-violet-600 rounded-lg hover:bg-gray-50 transition-colors"
                            >
                                Start Free Trial
                            </Link>
                        )}

                        <p className="text-center text-sm text-violet-200 mt-4">
                            7-day free trial • Cancel anytime
                        </p>
                    </div>
                </div>

                {/* FAQ Section */}
                <div className="mt-16 max-w-3xl mx-auto">
                    <h2 className="text-2xl font-bold text-center text-gray-900 mb-8">
                        Frequently Asked Questions
                    </h2>
                    <div className="space-y-6">
                        <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
                            <h3 className="font-semibold text-gray-900 mb-2">Can I cancel anytime?</h3>
                            <p className="text-gray-600">Yes! You can cancel your subscription at any time. No questions asked, no hidden fees.</p>
                        </div>
                        <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
                            <h3 className="font-semibold text-gray-900 mb-2">What payment methods do you accept?</h3>
                            <p className="text-gray-600">We accept all major credit cards, debit cards, and PayPal through our secure payment partner.</p>
                        </div>
                        <div className="bg-white rounded-lg p-6 shadow-sm border border-gray-200">
                            <h3 className="font-semibold text-gray-900 mb-2">Is there a money-back guarantee?</h3>
                            <p className="text-gray-600">Yes! We offer a 30-day money-back guarantee. If you&apos;re not satisfied, we&apos;ll refund your payment.</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
