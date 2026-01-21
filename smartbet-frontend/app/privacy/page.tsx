'use client'

import { Lock, Database, Cookie, Shield, Eye, Trash2, Mail } from 'lucide-react'
import Link from 'next/link'

export default function PrivacyPage() {
    return (
        <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="text-center mb-12">
                <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-full mb-4">
                    <Lock className="w-8 h-8 text-primary-600" />
                </div>
                <h1 className="text-3xl font-bold text-gray-900 mb-4">Privacy Policy</h1>
                <p className="text-gray-600">Last updated: January 2026</p>
            </div>

            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 space-y-8">

                {/* Introduction */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4">Introduction</h2>
                    <p className="text-gray-600 mb-4">
                        SmartBet ("we", "our", or "us") is committed to protecting your privacy.
                        This Privacy Policy explains how we collect, use, disclose, and safeguard your
                        information when you use our website and services.
                    </p>
                    <p className="text-gray-600">
                        Please read this policy carefully. By using our Service, you consent to the
                        collection and use of information in accordance with this policy.
                    </p>
                </section>

                {/* Information We Collect */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <Database className="w-5 h-5 text-primary-600" />
                        Information We Collect
                    </h2>

                    <h3 className="font-semibold text-gray-800 mb-2">Information You Provide</h3>
                    <ul className="list-disc list-inside text-gray-600 space-y-1 ml-4 mb-4">
                        <li>Email address (if you sign up for updates or create an account)</li>
                        <li>Account preferences and settings</li>
                        <li>Communications you send to us</li>
                    </ul>

                    <h3 className="font-semibold text-gray-800 mb-2">Automatically Collected Information</h3>
                    <ul className="list-disc list-inside text-gray-600 space-y-1 ml-4">
                        <li>Device information (browser type, operating system)</li>
                        <li>IP address and approximate location</li>
                        <li>Pages visited and features used</li>
                        <li>Time and date of visits</li>
                    </ul>
                </section>

                {/* How We Use Information */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <Eye className="w-5 h-5 text-primary-600" />
                        How We Use Your Information
                    </h2>
                    <p className="text-gray-600 mb-4">We use the information we collect to:</p>
                    <ul className="list-disc list-inside text-gray-600 space-y-1 ml-4">
                        <li>Provide and maintain our Service</li>
                        <li>Improve and personalize your experience</li>
                        <li>Send you updates and marketing communications (with your consent)</li>
                        <li>Respond to your inquiries and support requests</li>
                        <li>Analyze usage patterns to improve our predictions and features</li>
                        <li>Detect and prevent fraudulent activity</li>
                        <li>Comply with legal obligations</li>
                    </ul>
                </section>

                {/* Cookies */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <Cookie className="w-5 h-5 text-primary-600" />
                        Cookies and Tracking Technologies
                    </h2>
                    <p className="text-gray-600 mb-4">
                        We use cookies and similar tracking technologies to track activity on our Service
                        and store certain information. Types of cookies we use:
                    </p>

                    <div className="space-y-3 mb-4">
                        <div className="bg-gray-50 rounded-lg p-3">
                            <h4 className="font-medium text-gray-800">Essential Cookies</h4>
                            <p className="text-sm text-gray-600">Required for the website to function properly (e.g., age verification consent)</p>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-3">
                            <h4 className="font-medium text-gray-800">Preference Cookies</h4>
                            <p className="text-sm text-gray-600">Remember your settings and preferences</p>
                        </div>
                        <div className="bg-gray-50 rounded-lg p-3">
                            <h4 className="font-medium text-gray-800">Analytics Cookies</h4>
                            <p className="text-sm text-gray-600">Help us understand how visitors use our site</p>
                        </div>
                    </div>

                    <p className="text-gray-600">
                        You can configure your browser to refuse cookies or alert you when cookies are being sent.
                        However, some features may not function properly without cookies.
                    </p>
                </section>

                {/* Data Sharing */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <Shield className="w-5 h-5 text-primary-600" />
                        Data Sharing and Disclosure
                    </h2>
                    <p className="text-gray-600 mb-4">
                        We do NOT sell your personal information. We may share information only in the following cases:
                    </p>
                    <ul className="list-disc list-inside text-gray-600 space-y-2 ml-4">
                        <li>
                            <strong>Service Providers:</strong> Third parties who assist in operating our Service
                            (e.g., hosting, analytics)
                        </li>
                        <li>
                            <strong>Legal Requirements:</strong> When required by law or to respond to legal process
                        </li>
                        <li>
                            <strong>Protection:</strong> To protect the rights, property, or safety of SmartBet and our users
                        </li>
                        <li>
                            <strong>Business Transfers:</strong> In connection with a merger, acquisition, or sale of assets
                        </li>
                    </ul>
                </section>

                {/* Your Rights (GDPR) */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4">Your Rights</h2>
                    <p className="text-gray-600 mb-4">
                        Depending on your location, you may have certain rights regarding your personal data, including:
                    </p>
                    <div className="grid md:grid-cols-2 gap-3">
                        {[
                            { title: "Right to Access", desc: "Request a copy of your personal data" },
                            { title: "Right to Rectification", desc: "Request correction of inaccurate data" },
                            { title: "Right to Erasure", desc: "Request deletion of your data" },
                            { title: "Right to Portability", desc: "Request transfer of your data" },
                            { title: "Right to Object", desc: "Object to processing of your data" },
                            { title: "Right to Withdraw Consent", desc: "Withdraw consent at any time" },
                        ].map((right, index) => (
                            <div key={index} className="bg-gray-50 rounded-lg p-3">
                                <h4 className="font-medium text-gray-800">{right.title}</h4>
                                <p className="text-sm text-gray-600">{right.desc}</p>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Data Retention */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <Trash2 className="w-5 h-5 text-primary-600" />
                        Data Retention
                    </h2>
                    <p className="text-gray-600">
                        We retain your personal information only for as long as necessary to fulfill the purposes
                        outlined in this policy, unless a longer retention period is required by law.
                        When your data is no longer needed, we will securely delete or anonymize it.
                    </p>
                </section>

                {/* Security */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4">Data Security</h2>
                    <p className="text-gray-600">
                        We implement appropriate technical and organizational measures to protect your personal
                        information against unauthorized access, alteration, disclosure, or destruction.
                        However, no method of transmission over the Internet is 100% secure, and we cannot
                        guarantee absolute security.
                    </p>
                </section>

                {/* Children */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4">Children's Privacy</h2>
                    <p className="text-gray-600">
                        Our Service is not intended for individuals under 18 years of age. We do not knowingly
                        collect personal information from children. If you believe we have collected information
                        from a child, please contact us immediately.
                    </p>
                </section>

                {/* Contact */}
                <section>
                    <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
                        <Mail className="w-5 h-5 text-primary-600" />
                        Contact Us
                    </h2>
                    <p className="text-gray-600">
                        If you have questions about this Privacy Policy or wish to exercise your rights, contact us at:{' '}
                        <a href="mailto:privacy@smartbet.ai" className="text-primary-600 hover:underline">
                            privacy@smartbet.ai
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
