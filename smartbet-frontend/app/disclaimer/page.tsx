'use client'

import { AlertTriangle, Ban, Globe, Scale, TrendingDown, Shield } from 'lucide-react'
import Link from 'next/link'

export default function DisclaimerPage() {
    return (
        <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="text-center mb-12">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-amber-100 rounded-full mb-4">
                    <AlertTriangle className="w-8 h-8 text-amber-600" />
                </div>
                <h1 className="text-3xl font-bold text-gray-900 mb-4">Disclaimer</h1>
                <p className="text-gray-600">Please read this disclaimer carefully before using SmartBet</p>
            </div>

            {/* Main Disclaimer Box */}
            <div className="bg-red-50 border-2 border-red-200 rounded-xl p-6 mb-8">
                <div className="flex gap-4">
                    <Ban className="w-8 h-8 text-red-600 flex-shrink-0" />
                    <div>
                        <h2 className="text-xl font-bold text-red-800 mb-3">SmartBet is NOT a Betting Operator</h2>
                        <p className="text-red-700 mb-4">
                            SmartBet does NOT accept bets, wagers, deposits, or any form of payment for gambling purposes.
                            We are NOT licensed as a bookmaker, betting exchange, or gambling operator in any jurisdiction.
                        </p>
                        <p className="text-red-700">
                            We are a <strong>data analytics and prediction service</strong> that provides sports predictions
                            for <strong>informational and entertainment purposes only</strong>.
                        </p>
                    </div>
                </div>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 space-y-8">

                {/* No Financial Advice */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <TrendingDown className="w-5 h-5 text-amber-500" />
                        No Financial or Betting Advice
                    </h2>
                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-4">
                        <p className="text-amber-800">
                            The predictions, analysis, and information provided by SmartBet do NOT constitute financial advice,
                            betting advice, or recommendations to place any wager.
                        </p>
                    </div>
                    <p className="text-gray-600 mb-4">
                        Any decision to bet based on our predictions is made entirely at your own risk and discretion.
                        We strongly encourage you to:
                    </p>
                    <ul className="list-disc list-inside text-gray-600 space-y-1 ml-4">
                        <li>Do your own research before placing any bets</li>
                        <li>Only bet with licensed and regulated operators</li>
                        <li>Never bet more than you can afford to lose</li>
                        <li>Seek professional advice if needed</li>
                    </ul>
                </section>

                {/* Accuracy Limitations */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4">Accuracy Limitations</h2>
                    <p className="text-gray-600 mb-4">
                        While we use advanced machine learning algorithms and real-time data to generate our predictions,
                        we make NO guarantees regarding:
                    </p>
                    <ul className="list-disc list-inside text-gray-600 space-y-1 ml-4 mb-4">
                        <li>The accuracy of any individual prediction</li>
                        <li>The completeness or timeliness of data</li>
                        <li>Past performance being indicative of future results</li>
                        <li>The profitability of following our predictions</li>
                    </ul>
                    <p className="text-gray-600">
                        Sports outcomes are inherently unpredictable. Even our highest-confidence predictions
                        can and will be wrong. Historical accuracy rates shown on our platform are for
                        informational purposes only and do not guarantee future performance.
                    </p>
                </section>

                {/* Risk Warning */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <AlertTriangle className="w-5 h-5 text-red-500" />
                        Risk Warning
                    </h2>
                    <div className="bg-red-50 border border-red-200 rounded-lg p-5">
                        <p className="text-red-800 font-medium mb-3">
                            GAMBLING INVOLVES SUBSTANTIAL RISK OF LOSS
                        </p>
                        <ul className="text-red-700 space-y-2">
                            <li>• You can lose some or all of your money</li>
                            <li>• Gambling can be addictive - please gamble responsibly</li>
                            <li>• Never chase losses or bet with money you cannot afford to lose</li>
                            <li>• Past performance is not a guarantee of future results</li>
                            <li>• The odds are always in favor of the bookmaker</li>
                        </ul>
                    </div>
                </section>

                {/* Age Restriction */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <Shield className="w-5 h-5 text-primary-600" />
                        Age Restriction
                    </h2>
                    <div className="flex items-center gap-4 mb-4">
                        <div className="flex items-center justify-center w-12 h-12 bg-red-100 rounded-full border-2 border-red-500">
                            <span className="text-red-600 font-bold">18+</span>
                        </div>
                        <p className="text-gray-600">
                            This website and its content are intended for adults only. You must be at least
                            18 years old (or the legal age in your jurisdiction) to access this service.
                        </p>
                    </div>
                    <p className="text-gray-600">
                        By using SmartBet, you confirm that you meet the minimum age requirement and are
                        legally permitted to access gambling-related content in your jurisdiction.
                    </p>
                </section>

                {/* Jurisdiction */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <Globe className="w-5 h-5 text-primary-600" />
                        Jurisdiction Notice
                    </h2>
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                        <p className="text-blue-800">
                            <strong>Online gambling laws vary by jurisdiction.</strong> It is YOUR responsibility
                            to ensure that your use of gambling services is legal in your location.
                        </p>
                    </div>
                    <p className="text-gray-600 mb-4">
                        SmartBet does not target any specific jurisdiction and makes no representations
                        regarding the legality of its service or gambling in any particular location.
                    </p>
                    <p className="text-gray-600">
                        If you are in a jurisdiction where gambling or accessing gambling-related content is
                        prohibited, you should not use this website. SmartBet is not responsible for any
                        violation of local laws.
                    </p>
                </section>

                {/* Liability */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <Scale className="w-5 h-5 text-primary-600" />
                        Limitation of Liability
                    </h2>
                    <p className="text-gray-600 mb-4">
                        To the maximum extent permitted by applicable law, SmartBet and its affiliates,
                        officers, employees, and agents shall NOT be liable for:
                    </p>
                    <ul className="list-disc list-inside text-gray-600 space-y-1 ml-4">
                        <li>Any financial losses incurred from betting based on our predictions</li>
                        <li>Any errors, inaccuracies, or omissions in our content</li>
                        <li>Any interruption or cessation of the service</li>
                        <li>Any damages arising from your reliance on our information</li>
                        <li>Any third-party actions, products, or services</li>
                    </ul>
                </section>

                {/* Third Party Links */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4">Third-Party Links</h2>
                    <p className="text-gray-600">
                        Our website may contain links to third-party websites or services. We are not
                        responsible for the content, privacy practices, or terms of service of any
                        third-party sites. The inclusion of any link does not imply endorsement by SmartBet.
                    </p>
                </section>

                {/* Changes */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4">Changes to This Disclaimer</h2>
                    <p className="text-gray-600">
                        We may update this disclaimer from time to time. Changes will be effective immediately
                        upon posting. Your continued use of the Service after changes constitutes acceptance
                        of the revised disclaimer.
                    </p>
                </section>
            </div>

            {/* Responsible Gambling Link */}
            <div className="bg-primary-50 border border-primary-200 rounded-xl p-6 mt-8 text-center">
                <p className="text-primary-800 mb-4">
                    If you or someone you know has a gambling problem, help is available.
                </p>
                <Link
                    href="/responsible-gambling"
                    className="inline-flex items-center gap-2 bg-primary-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-primary-700 transition-colors"
                >
                    <Shield className="w-5 h-5" />
                    Responsible Gambling Resources
                </Link>
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
