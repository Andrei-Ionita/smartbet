'use client'

import { FileText, AlertTriangle, Scale, Shield, Ban } from 'lucide-react'
import Link from 'next/link'

export default function TermsPage() {
    return (
        <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="text-center mb-12">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mb-4">
                    <FileText className="w-8 h-8 text-primary-600" />
                </div>
                <h1 className="text-3xl font-bold text-gray-900 mb-4">Terms of Service</h1>
                <p className="text-gray-600">Last updated: January 2026</p>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 space-y-8">

                {/* Agreement */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <Scale className="w-5 h-5 text-primary-600" />
                        1. Agreement to Terms
                    </h2>
                    <p className="text-gray-600 mb-4">
                        By accessing or using SmartBet ("the Service"), you agree to be bound by these Terms of Service.
                        If you do not agree to these terms, please do not use our Service.
                    </p>
                    <p className="text-gray-600">
                        We reserve the right to modify these terms at any time. Your continued use of the Service
                        following any changes constitutes acceptance of those changes.
                    </p>
                </section>

                {/* Service Description */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4">2. Service Description</h2>
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
                        <div className="flex gap-3">
                            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0" />
                            <p className="text-amber-800 text-sm">
                                <strong>SmartBet is NOT a betting operator, bookmaker, or gambling site.</strong> We do not
                                accept bets, wagers, deposits, or any form of payment for gambling purposes.
                            </p>
                        </div>
                    </div>
                    <p className="text-gray-600 mb-4">
                        SmartBet provides AI-powered sports predictions and data analysis for <strong>informational
                            and entertainment purposes only</strong>. Our service includes:
                    </p>
                    <ul className="list-disc list-inside text-gray-600 space-y-1 ml-4">
                        <li>Football match predictions and probability assessments</li>
                        <li>Historical performance data and statistics</li>
                        <li>Odds comparison and value analysis</li>
                        <li>Educational content about sports analytics</li>
                    </ul>
                </section>

                {/* User Responsibilities */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <Shield className="w-5 h-5 text-primary-600" />
                        3. User Responsibilities
                    </h2>
                    <p className="text-gray-600 mb-4">By using our Service, you represent and warrant that:</p>
                    <ul className="list-disc list-inside text-gray-600 space-y-2 ml-4">
                        <li>You are at least 18 years old (or the legal age in your jurisdiction)</li>
                        <li>You are legally permitted to access gambling-related content in your jurisdiction</li>
                        <li>You will comply with all applicable local, state, national, and international laws</li>
                        <li>You understand that our predictions are not guarantees and betting involves risk</li>
                        <li>You will not use our Service for any unlawful purpose</li>
                        <li>Any betting decisions you make are your own responsibility</li>
                    </ul>
                </section>

                {/* Disclaimer */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5 text-amber-500" />
                        4. Disclaimer of Warranties
                    </h2>
                    <p className="text-gray-600 mb-4">
                        THE SERVICE IS PROVIDED "AS IS" WITHOUT WARRANTIES OF ANY KIND, EXPRESS OR IMPLIED.
                        WE DO NOT GUARANTEE:
                    </p>
                    <ul className="list-disc list-inside text-gray-600 space-y-1 ml-4">
                        <li>The accuracy, completeness, or reliability of any predictions</li>
                        <li>That use of our predictions will result in profit</li>
                        <li>Uninterrupted or error-free operation of the Service</li>
                        <li>That our analysis reflects the most current data</li>
                    </ul>
                    <p className="text-gray-600 mt-4">
                        Past performance of our predictions is not indicative of future results.
                        Betting involves substantial risk of loss and is not suitable for everyone.
                    </p>
                </section>

                {/* Limitation of Liability */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4">5. Limitation of Liability</h2>
                    <p className="text-gray-600 mb-4">
                        To the fullest extent permitted by law, SmartBet and its affiliates shall not be liable for:
                    </p>
                    <ul className="list-disc list-inside text-gray-600 space-y-1 ml-4">
                        <li>Any financial losses incurred from betting based on our predictions</li>
                        <li>Any indirect, incidental, special, or consequential damages</li>
                        <li>Loss of profits, data, or other intangible losses</li>
                        <li>Any damages resulting from unauthorized access to your account</li>
                    </ul>
                </section>

                {/* Prohibited Uses */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <Ban className="w-5 h-5 text-red-500" />
                        6. Prohibited Uses
                    </h2>
                    <p className="text-gray-600 mb-4">You agree NOT to:</p>
                    <ul className="list-disc list-inside text-gray-600 space-y-1 ml-4">
                        <li>Use the Service if you are under 18 years old</li>
                        <li>Access the Service from a jurisdiction where gambling is prohibited</li>
                        <li>Resell or redistribute our predictions without permission</li>
                        <li>Attempt to reverse-engineer our prediction algorithms</li>
                        <li>Use automated systems to scrape or copy our content</li>
                        <li>Interfere with or disrupt the Service</li>
                    </ul>
                </section>

                {/* Intellectual Property */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4">7. Intellectual Property</h2>
                    <p className="text-gray-600">
                        All content, features, and functionality of the Service (including but not limited to text,
                        graphics, logos, algorithms, and software) are owned by SmartBet and are protected by
                        international copyright, trademark, and other intellectual property laws.
                    </p>
                </section>

                {/* Governing Law */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4">8. Governing Law</h2>
                    <p className="text-gray-600">
                        These Terms shall be governed by and construed in accordance with applicable laws.
                        Any disputes arising from these Terms or your use of the Service shall be subject
                        to the exclusive jurisdiction of the appropriate courts.
                    </p>
                </section>

                {/* Contact */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4">9. Contact Information</h2>
                    <p className="text-gray-600">
                        If you have any questions about these Terms of Service, please contact us at:{' '}
                        <a href="mailto:legal@smartbet.ai" className="text-primary-600 hover:underline">
                            legal@smartbet.ai
                        </a>
                    </p>
                </section>
            </div>

            {/* Footer */}
            <div className="text-center py-8">
                <Link href="/" className="text-primary-600 hover:text-primary-700 font-medium">
                    Return to Home
                </Link>
            </div>
        </div>
    )
}
