'use client'

import Link from 'next/link'
import { ACCOUNT_FEATURES_ENABLED, PAYMENTS_ENABLED } from '@/app/lib/commercialMode'
import Image from 'next/image'
import { Trophy, Mail, AlertTriangle } from 'lucide-react'
import { useLanguage } from '@/app/contexts/LanguageContext'
import { getCopy } from '@/app/lib/terminology'
import { PUBLIC_LEGAL_IDENTITY_COMPLETE, publicLegalIdentity } from '@/app/lib/publicLegalIdentity'

export default function Footer() {
    const currentYear = new Date().getFullYear()
    // The footer sits on every page, so it was the largest single block of
    // English left on a Romanian journey — including the legal notice, which
    // is the part a visitor most needs to be able to read.
    const { language } = useLanguage()
    const f = getCopy(language).footer

    return (
        <footer className="bg-white border-t border-gray-200 mt-auto">
            <div className="container mx-auto px-4 py-12">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
                    {/* Brand Section */}
                    <div className="col-span-1 md:col-span-1">
                        <Link href="/" className="flex items-center space-x-2 mb-4">
                            <div className="relative h-8 w-8">
                                <Image
                                    src="/images/logo-final-v6.png"
                                    alt="BetGlitch Logo"
                                    fill
                                    className="object-contain"
                                />
                            </div>
                            <span className="text-xl font-bold text-gray-900">BetGlitch</span>
                        </Link>
                        <p className="text-sm text-gray-600 mb-4 leading-relaxed">
                            {f.tagline}
                        </p>
                        {/* The Twitter and GitHub icons linked to a bare fragment,
                            so they were dead ends in the footer of every page.
                            Removed until there are real accounts to link to. The
                            remaining control is padded to a 44px touch target —
                            the bare icons measured 20x20. */}
                        <div className="flex -ml-2">
                            <a
                                href="mailto:support@betglitch.com"
                                className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-md text-gray-400 transition-colors hover:text-primary-600 hover:bg-gray-100"
                            >
                                <Mail className="h-5 w-5" />
                                <span className="sr-only">{f.emailSupport}</span>
                            </a>
                        </div>
                    </div>

                    {/* Quick Links */}
                    <div>
                        <h3 className="font-semibold text-gray-900 mb-4">{f.platform}</h3>
                        <ul className="space-y-2 text-sm">
                            <li>
                                <Link href="/explore" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    {f.explore}
                                </Link>
                            </li>
                            {ACCOUNT_FEATURES_ENABLED && (
                              <li>
                                  <Link href="/dashboard" className="text-gray-600 hover:text-primary-600 transition-colors">
                                      {f.dashboard}
                                  </Link>
                              </li>
                            )}
                            <li>
                                <Link href="/track-record" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    {f.trackRecord}
                                </Link>
                            </li>
                            {PAYMENTS_ENABLED && (
                              <li>
                                  <Link href="/pricing" className="text-gray-600 hover:text-primary-600 transition-colors">
                                      {f.pricing}
                                  </Link>
                              </li>
                            )}
                        </ul>
                    </div>

                    {/* Resources */}
                    <div>
                        <h3 className="font-semibold text-gray-900 mb-4">{f.resources}</h3>
                        <ul className="space-y-2 text-sm">
                            <li>
                                <Link href="/blog/how-betglitch-works" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    {f.howItWorks}
                                </Link>
                            </li>
                            <li>
                                <Link href="/blog" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    {f.blog}
                                </Link>
                            </li>
                            <li>
                                <Link href="/responsible-gambling" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    {f.responsibleGambling}
                                </Link>
                            </li>
                            <li>
                                <Link href="/about" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    {f.about}
                                </Link>
                            </li>
                        </ul>
                    </div>

                    {/* Legal */}
                    <div>
                        <h3 className="font-semibold text-gray-900 mb-4">{f.legal}</h3>
                        <ul className="space-y-2 text-sm">
                            <li>
                                <Link href="/terms" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    {f.terms}
                                </Link>
                            </li>
                            <li>
                                <Link href="/privacy" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    {f.privacy}
                                </Link>
                            </li>
                            <li>
                                <Link href="/disclaimer" className="text-gray-600 hover:text-primary-600 transition-colors">
                                    {f.disclaimer}
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
                            <p className="font-semibold text-gray-700 mb-2">{f.noticeTitle}</p>

                            <p className="mb-2">
                                <strong className="text-gray-700">{f.noticeOperatorStrong}</strong>
                                {f.noticeOperatorRest}
                                <strong>{f.noticeOperatorEmphasis}</strong>
                                {f.noticeOperatorTail}
                            </p>

                            <p className="mb-2">
                                <strong className="text-amber-600">{f.noticeRiskLabel}</strong>
                                {f.noticeRiskBody}
                            </p>

                            <p className="mb-2">
                                <strong className="text-gray-700">{f.noticeRegionalLabel}</strong>
                                {f.noticeRegionalBody}
                            </p>

                            <p>
                                {f.noticeHelp}{' '}
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
                            {f.ageNotice}
                        </p>
                    </div>
                </div>

                {/* Bottom Bar */}
                <div className="flex flex-col md:flex-row justify-between items-center pt-8 border-t border-gray-200 text-sm text-gray-500">
                    <div className="text-center md:text-left">
                        <p>&copy; {currentYear} {f.rights}</p>
                        {PUBLIC_LEGAL_IDENTITY_COMPLETE && (
                            <p className="mt-1 text-xs">
                                {publicLegalIdentity.operatorName} · {publicLegalIdentity.operatorAddress} ·{' '}
                                {publicLegalIdentity.operatorCountry}
                            </p>
                        )}
                    </div>
                    <div className="flex items-center gap-4 mt-4 md:mt-0">
                        <span className="flex items-center gap-2">
                            <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                            {f.operational}
                        </span>
                        <span>v0.9.0-beta</span>
                    </div>
                </div>
            </div>
        </footer>
    )
}
