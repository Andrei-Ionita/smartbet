'use client'

import { Shield, Phone, Globe, AlertTriangle, Heart, HelpCircle, ExternalLink, CheckCircle } from 'lucide-react'
import Link from 'next/link'

export default function ResponsibleGamblingPage() {
    return (
        <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="text-center mb-12">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mb-4">
                    <Shield className="w-8 h-8 text-primary-600" />
                </div>
                <h1 className="text-3xl font-bold text-gray-900 mb-4">Responsible Gambling</h1>
                <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                    At SmartBet, we believe gambling should be an enjoyable activity, not a source of harm.
                    We are committed to promoting responsible gambling practices.
                </p>
            </div>

            {/* Important Notice */}
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 mb-8">
                <div className="flex gap-4">
                    <AlertTriangle className="w-6 h-6 text-amber-600 flex-shrink-0" />
                    <div>
                        <h2 className="font-semibold text-amber-800 mb-2">Important Reminder</h2>
                        <p className="text-amber-700">
                            SmartBet provides predictions for <strong>informational and entertainment purposes only</strong>.
                            We are NOT a betting operator and do not accept any bets or wagers.
                            If you choose to place bets based on our analysis, please do so responsibly through licensed operators.
                        </p>
                    </div>
                </div>
            </div>

            {/* Key Principles */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
                <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                    <Heart className="w-5 h-5 text-red-500" />
                    Key Principles of Responsible Gambling
                </h2>
                <div className="grid md:grid-cols-2 gap-4">
                    {[
                        "Only gamble with money you can afford to lose",
                        "Set a budget and stick to it",
                        "Never chase your losses",
                        "Take regular breaks from gambling",
                        "Don't gamble when upset, stressed, or under the influence",
                        "Balance gambling with other activities",
                        "Keep track of time and money spent",
                        "Never borrow money to gamble"
                    ].map((principle, index) => (
                        <div key={index} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
                            <CheckCircle className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />
                            <span className="text-sm text-gray-700">{principle}</span>
                        </div>
                    ))}
                </div>
            </div>

            {/* Warning Signs */}
            <div className="bg-red-50 border border-red-200 rounded-xl p-6 mb-8">
                <h2 className="text-xl font-bold text-red-800 mb-4 flex items-center gap-2">
                    <AlertTriangle className="w-5 h-5" />
                    Warning Signs of Problem Gambling
                </h2>
                <p className="text-red-700 mb-4">
                    If you recognize any of these signs in yourself or someone you know, it may be time to seek help:
                </p>
                <ul className="space-y-2 text-red-700">
                    <li className="flex items-start gap-2">
                        <span className="text-red-400">•</span>
                        Spending more money or time gambling than you can afford
                    </li>
                    <li className="flex items-start gap-2">
                        <span className="text-red-400">•</span>
                        Finding it hard to manage or stop gambling
                    </li>
                    <li className="flex items-start gap-2">
                        <span className="text-red-400">•</span>
                        Having arguments with family or friends about money and gambling
                    </li>
                    <li className="flex items-start gap-2">
                        <span className="text-red-400">•</span>
                        Losing interest in usual activities or hobbies
                    </li>
                    <li className="flex items-start gap-2">
                        <span className="text-red-400">•</span>
                        Thinking or talking about gambling all the time
                    </li>
                    <li className="flex items-start gap-2">
                        <span className="text-red-400">•</span>
                        Lying about gambling or hiding it from others
                    </li>
                    <li className="flex items-start gap-2">
                        <span className="text-red-400">•</span>
                        Chasing losses or gambling to escape problems
                    </li>
                    <li className="flex items-start gap-2">
                        <span className="text-red-400">•</span>
                        Neglecting work, school, or family responsibilities
                    </li>
                </ul>
            </div>

            {/* Help Resources */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
                <h2 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                    <HelpCircle className="w-5 h-5 text-primary-600" />
                    Get Help - Support Organizations
                </h2>
                <p className="text-gray-600 mb-6">
                    If you or someone you know is struggling with gambling, these organizations provide free, confidential support:
                </p>

                <div className="grid gap-4">
                    {/* GamCare */}
                    <div className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors">
                        <div className="flex items-start justify-between">
                            <div>
                                <h3 className="font-semibold text-gray-900">GamCare</h3>
                                <p className="text-sm text-gray-600 mb-2">UK's leading provider of gambling support</p>
                                <div className="flex items-center gap-4 text-sm">
                                    <span className="flex items-center gap-1 text-primary-600">
                                        <Phone className="w-4 h-4" />
                                        0808 8020 133
                                    </span>
                                    <span className="text-gray-400">24/7 Helpline</span>
                                </div>
                            </div>
                            <a href="https://www.gamcare.org.uk" target="_blank" rel="noopener noreferrer"
                                className="flex items-center gap-1 text-sm text-primary-600 hover:underline">
                                Visit <ExternalLink className="w-3 h-3" />
                            </a>
                        </div>
                    </div>

                    {/* BeGambleAware */}
                    <div className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors">
                        <div className="flex items-start justify-between">
                            <div>
                                <h3 className="font-semibold text-gray-900">BeGambleAware</h3>
                                <p className="text-sm text-gray-600 mb-2">Free, confidential advice and support</p>
                                <div className="flex items-center gap-4 text-sm">
                                    <span className="flex items-center gap-1 text-primary-600">
                                        <Globe className="w-4 h-4" />
                                        begambleaware.org
                                    </span>
                                </div>
                            </div>
                            <a href="https://www.begambleaware.org" target="_blank" rel="noopener noreferrer"
                                className="flex items-center gap-1 text-sm text-primary-600 hover:underline">
                                Visit <ExternalLink className="w-3 h-3" />
                            </a>
                        </div>
                    </div>

                    {/* Gambling Therapy */}
                    <div className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors">
                        <div className="flex items-start justify-between">
                            <div>
                                <h3 className="font-semibold text-gray-900">Gambling Therapy</h3>
                                <p className="text-sm text-gray-600 mb-2">Free online support in multiple languages</p>
                                <div className="flex items-center gap-4 text-sm">
                                    <span className="flex items-center gap-1 text-primary-600">
                                        <Globe className="w-4 h-4" />
                                        gamblingtherapy.org
                                    </span>
                                </div>
                            </div>
                            <a href="https://www.gamblingtherapy.org" target="_blank" rel="noopener noreferrer"
                                className="flex items-center gap-1 text-sm text-primary-600 hover:underline">
                                Visit <ExternalLink className="w-3 h-3" />
                            </a>
                        </div>
                    </div>

                    {/* Gamblers Anonymous */}
                    <div className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors">
                        <div className="flex items-start justify-between">
                            <div>
                                <h3 className="font-semibold text-gray-900">Gamblers Anonymous</h3>
                                <p className="text-sm text-gray-600 mb-2">Fellowship of men and women who share experience</p>
                                <div className="flex items-center gap-4 text-sm">
                                    <span className="flex items-center gap-1 text-primary-600">
                                        <Globe className="w-4 h-4" />
                                        gamblersanonymous.org
                                    </span>
                                </div>
                            </div>
                            <a href="https://www.gamblersanonymous.org" target="_blank" rel="noopener noreferrer"
                                className="flex items-center gap-1 text-sm text-primary-600 hover:underline">
                                Visit <ExternalLink className="w-3 h-3" />
                            </a>
                        </div>
                    </div>

                    {/* National Council on Problem Gambling (US) */}
                    <div className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 transition-colors">
                        <div className="flex items-start justify-between">
                            <div>
                                <h3 className="font-semibold text-gray-900">National Council on Problem Gambling (US)</h3>
                                <p className="text-sm text-gray-600 mb-2">US-based 24/7 confidential helpline</p>
                                <div className="flex items-center gap-4 text-sm">
                                    <span className="flex items-center gap-1 text-primary-600">
                                        <Phone className="w-4 h-4" />
                                        1-800-522-4700
                                    </span>
                                </div>
                            </div>
                            <a href="https://www.ncpgambling.org" target="_blank" rel="noopener noreferrer"
                                className="flex items-center gap-1 text-sm text-primary-600 hover:underline">
                                Visit <ExternalLink className="w-3 h-3" />
                            </a>
                        </div>
                    </div>
                </div>
            </div>

            {/* Self-Exclusion */}
            <div className="bg-gray-50 rounded-xl p-6 mb-8">
                <h2 className="text-xl font-bold text-gray-900 mb-4">Self-Exclusion Programs</h2>
                <p className="text-gray-600 mb-4">
                    Many betting operators offer self-exclusion programs that allow you to block yourself from gambling for a set period.
                    Contact your betting operator directly or use national self-exclusion schemes:
                </p>
                <ul className="space-y-2 text-gray-700">
                    <li className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-primary-500 rounded-full"></span>
                        <strong>GAMSTOP (UK)</strong> - Free self-exclusion from all UK licensed gambling sites
                    </li>
                    <li className="flex items-center gap-2">
                        <span className="w-2 h-2 bg-primary-500 rounded-full"></span>
                        <strong>BetBlocker</strong> - Free app to block gambling sites on your devices
                    </li>
                </ul>
            </div>

            {/* Footer CTA */}
            <div className="text-center py-8">
                <p className="text-gray-600 mb-4">
                    Remember: Gambling should be fun, not a way to make money or solve financial problems.
                </p>
                <Link href="/" className="inline-flex items-center gap-2 text-primary-600 hover:text-primary-700 font-medium">
                    Return to Home
                </Link>
            </div>
        </div>
    )
}
