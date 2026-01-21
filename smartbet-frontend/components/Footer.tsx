'use client'

import Link from 'next/link'
import { Trophy, Github, Twitter, Mail, AlertTriangle } from 'lucide-react'

export default function Footer() {
    const currentYear = new Date().getFullYear()

    return (
        <footer className="bg-white border-t border-gray-200 mt-auto">
            <div className="container mx-auto px-4 py-12">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
                    {/* Brand Section */}
                    <div className="col-span-1 md:col-span-1">
                        <Link href="/" className="flex items-center space-x-2 mb-4">
                            <Trophy className="h-6 w-6 text-primary-600" />
                            <span className="text-xl font-bold text-gray-900">SmartBet</span>
                        </Link>
                        <p className="text-sm text-gray-600 mb-4 leading-relaxed">
                            AI-powered football predictions and betting insights. We combine machine learning with real-time data to help you make smarter decisions.
                        </p>
                        <div className="flex space-x-4">
                            <a href="#" className="text-gray-400 hover:text-primary-600 transition-colors">
                                <Twitter className="h-5 w-5" />
                                <span className="sr-only">Twitter</span>
                            </a>
                            <a href="#" className="text-gray-400 hover:text-primary-600 transition-colors">
                                <Github className="h-5 w-5" />
                                <span className="sr-only">GitHub</span>
                            </a>
                            <a href="mailto:support@smartbet.com" className="text-gray-400 hover:text-primary-600 transition-colors">
                                <Mail className="h-5 w-5" />
                                <span className="sr-only">Email</span>
                            </a>
                        </div>
                    </div>

                    {/* Quick Links */}
                    <div>
                        <h3 className="font-semibold text-gray-900 mb-4">Platform</h3>
                        <ul className="space-y-2 text-sm">
                            <li>
                                <Link href="/explore" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    Explore Predictions
                                </Link>
                            </li>
                            <li>
                                <Link href="/dashboard" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    User Dashboard
                                </Link>
                            </li>
                            <li>
                                <Link href="/track-record" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    Track Record
                                </Link>
                            </li>
                            <li>
                                <Link href="/pricing" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    Pricing
                                </Link>
                            </li>
                        </ul>
                    </div>

                    {/* Resources */}
                    <div>
                        <h3 className="font-semibold text-gray-900 mb-4">Resources</h3>
                        <ul className="space-y-2 text-sm">
                            <li>
                                <Link href="/how-it-works" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    How It Works
                                </Link>
                            </li>
                            <li>
                                <Link href="/faq" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    FAQ
                                </Link>
                            </li>
                            <li>
                                <Link href="/responsible-gambling" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    Responsible Gambling
                                </Link>
                            </li>
                            <li>
                                <Link href="/api-docs" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    API Documentation
                                </Link>
                            </li>
                        </ul>
                    </div>

                    {/* Legal */}
                    <div>
                        <h3 className="font-semibold text-gray-900 mb-4">Legal</h3>
                        <ul className="space-y-2 text-sm">
                            <li>
                                <Link href="/terms" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    Terms of Service
                                </Link>
                            </li>
                            <li>
                                <Link href="/privacy" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    Privacy Policy
                                </Link>
                            </li>
                            <li>
                                <Link href="/disclaimer" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    Disclaimer
                                </Link>
                            </li>
                        </ul>
                    </div>
                </div>

                {/* Disclaimer Banner - Enhanced Legal Notice */}
                <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 mb-8">
                    <div className="flex items-start gap-3">
                        <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
                        <div className="text-xs text-gray-500 leading-relaxed">
                            <p className="font-semibold text-gray-700 mb-2">Important Legal Notice</p>

                            <p className="mb-2">
                                <strong className="text-gray-700">SmartBet is NOT a betting operator, bookmaker, or gambling site.</strong>{' '}
                                We do not accept bets, wagers, or deposits of any kind. Our predictions are provided for{' '}
                                <strong>informational and entertainment purposes only</strong> and should not be considered financial or betting advice.
                            </p>

                            <p className="mb-2">
                                <strong className="text-amber-600">Risk Warning:</strong> Betting involves significant risk, including the possible loss of your entire stake.
                                Past performance is not indicative of future results. Never bet more than you can afford to lose.
                            </p>

                            <p className="mb-2">
                                <strong className="text-gray-700">Regional Notice:</strong> Online gambling may be restricted or illegal in your jurisdiction.
                                It is your responsibility to ensure compliance with local laws before engaging in any gambling activity.
                            </p>

                            <p>
                                If you or someone you know has a gambling problem, please seek help:{' '}
                                <a href="https://www.begambleaware.org" target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">BeGambleAware.org</a>,{' '}
                                <a href="https://www.gamcare.org.uk" target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">GamCare</a>,{' '}
                                <a href="https://www.gamblingtherapy.org" target="_blank" rel="noopener noreferrer" className="text-primary-600 hover:underline">Gambling Therapy</a>
                            </p>
                        </div>
                    </div>

                    {/* 18+ Badge */}
                    <div className="flex items-center justify-center gap-4 mt-4 pt-4 border-t border-gray-200">
                        <div className="flex items-center justify-center w-10 h-10 bg-red-100 rounded-full border-2 border-red-500">
                            <span className="text-red-600 font-bold text-sm">18+</span>
                        </div>
                        <p className="text-xs text-gray-500">
                            This website is for adults only. You must be 18 years or older to use this service.
                        </p>
                    </div>
                </div>

                {/* Bottom Bar */}
                <div className="flex flex-col md:flex-row justify-between items-center pt-8 border-t border-gray-200 text-sm text-gray-500">
                    <p>&copy; {currentYear} SmartBet Analytics. All rights reserved.</p>
                    <div className="flex items-center gap-4 mt-4 md:mt-0">
                        <span className="flex items-center gap-2">
                            <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                            Systems Operational
                        </span>
                        <span>v0.9.0-beta</span>
                    </div>
                </div>
            </div>
        </footer>
    )
}
