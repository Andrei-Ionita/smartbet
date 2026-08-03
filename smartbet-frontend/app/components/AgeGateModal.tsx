'use client'

import { useState, useEffect, useRef } from 'react'
import { Shield, AlertTriangle, CheckCircle2, ExternalLink } from 'lucide-react'

export default function AgeGateModal() {
    const [showModal, setShowModal] = useState(false)
    const dialogRef = useRef<HTMLDivElement>(null)
    const headingRef = useRef<HTMLHeadingElement>(null)
    const [isChecked, setIsChecked] = useState({
        age: false,
        terms: false,
        region: false
    })

    useEffect(() => {
        // Check if user has already accepted
        const consent = localStorage.getItem('smartbet_legal_consent')
        if (!consent) {
            setShowModal(true)
            // Prevent scrolling when modal is open
            document.body.style.overflow = 'hidden'
        }
        return () => {
            document.body.style.overflow = 'unset'
        }
    }, [])

    // This modal fronts every page, so it is the first thing a screen-reader
    // user meets. Without focus being moved into it, focus stays on <body> and
    // the reader keeps announcing the page behind the overlay as if reachable.
    useEffect(() => {
        if (showModal) headingRef.current?.focus()
    }, [showModal])

    // Keep Tab inside the gate. Deliberately NO Escape handler: this is a legal
    // acknowledgement, not a dismissible dialog, and Escape must not bypass it.
    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key !== 'Tab' || !dialogRef.current) return
        const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
            'a[href], button:not([disabled]), input, [tabindex]:not([tabindex="-1"])',
        )
        if (focusable.length === 0) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (e.shiftKey && document.activeElement === first) {
            e.preventDefault()
            last.focus()
        } else if (!e.shiftKey && document.activeElement === last) {
            e.preventDefault()
            first.focus()
        }
    }

    const allChecked = isChecked.age && isChecked.terms && isChecked.region

    const handleAccept = () => {
        if (allChecked) {
            localStorage.setItem('smartbet_legal_consent', JSON.stringify({
                accepted: true,
                timestamp: new Date().toISOString(),
                version: '1.0'
            }))
            setShowModal(false)
            document.body.style.overflow = 'unset'
        }
    }

    const handleDecline = () => {
        // Redirect to a safe page explaining why they can't proceed
        window.location.href = 'https://www.begambleaware.org/'
    }

    if (!showModal) return null

    return (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
            <div
                ref={dialogRef}
                onKeyDown={handleKeyDown}
                role="dialog"
                aria-modal="true"
                aria-labelledby="age-gate-title"
                aria-describedby="age-gate-desc"
                className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto"
            >
                {/* Header */}
                <div className="bg-gradient-to-r from-primary-600 to-primary-700 px-6 py-8 text-center rounded-t-2xl">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-white/20 rounded-full mb-4">
                        <Shield className="w-8 h-8 text-white" />
                    </div>
                    {/* h2, not h1: this overlays a page that already has its own
                        h1, and two h1s made every page report a duplicate. */}
                    <h2
                        id="age-gate-title"
                        ref={headingRef}
                        tabIndex={-1}
                        className="text-2xl font-bold text-white mb-2 outline-none"
                    >
                        Age Verification Required
                    </h2>
                    <p id="age-gate-desc" className="text-primary-100 text-sm">
                        Please confirm you meet the requirements to access BetGlitch
                    </p>
                </div>

                {/* Content */}
                <div className="p-6">
                    {/* Important Notice */}
                    <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6">
                        <div className="flex gap-3">
                            <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                            <div className="text-sm">
                                <p className="font-semibold text-amber-800 mb-1">Important Notice</p>
                                <p className="text-amber-700">
                                    BetGlitch provides sports predictions for <strong>informational and entertainment purposes only</strong>.
                                    We are <strong>NOT a betting operator</strong> and do not accept bets or wagers of any kind.
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Checkboxes */}
                    <div className="space-y-4 mb-6">
                        <label className="flex items-start gap-3 cursor-pointer group">
                            <input
                                type="checkbox"
                                checked={isChecked.age}
                                onChange={(e) => setIsChecked({ ...isChecked, age: e.target.checked })}
                                className="w-6 h-6 mt-0.5 flex-shrink-0 rounded border-gray-300 text-primary-600 focus:ring-primary-500 cursor-pointer"
                            />
                            <span className="text-sm text-gray-700 group-hover:text-gray-900">
                                I confirm that I am <strong>18 years of age or older</strong> (or the legal age in my jurisdiction)
                                and legally permitted to access gambling-related content.
                            </span>
                        </label>

                        <label className="flex items-start gap-3 cursor-pointer group">
                            <input
                                type="checkbox"
                                checked={isChecked.terms}
                                onChange={(e) => setIsChecked({ ...isChecked, terms: e.target.checked })}
                                className="w-6 h-6 mt-0.5 flex-shrink-0 rounded border-gray-300 text-primary-600 focus:ring-primary-500 cursor-pointer"
                            />
                            <span className="text-sm text-gray-700 group-hover:text-gray-900">
                                I understand that <strong>gambling involves risk</strong> and I should only bet what I can afford to lose.
                                Past performance does not guarantee future results.
                            </span>
                        </label>

                        <label className="flex items-start gap-3 cursor-pointer group">
                            <input
                                type="checkbox"
                                checked={isChecked.region}
                                onChange={(e) => setIsChecked({ ...isChecked, region: e.target.checked })}
                                className="w-6 h-6 mt-0.5 flex-shrink-0 rounded border-gray-300 text-primary-600 focus:ring-primary-500 cursor-pointer"
                            />
                            <span className="text-sm text-gray-700 group-hover:text-gray-900">
                                I acknowledge that <strong>gambling may be restricted or illegal</strong> in my jurisdiction and
                                it is my responsibility to ensure compliance with local laws before using this service.
                            </span>
                        </label>
                    </div>

                    {/* 18+ Badge */}
                    <div className="flex items-center justify-center gap-4 mb-6 py-4 border-y border-gray-100">
                        <div className="flex items-center justify-center w-12 h-12 bg-red-100 rounded-full border-2 border-red-500">
                            <span className="text-red-600 font-bold text-lg">18+</span>
                        </div>
                        <p className="text-xs text-gray-500 max-w-xs">
                            Access to BetGlitch is restricted to adults only. We promote responsible gambling.
                        </p>
                    </div>

                    {/* Buttons */}
                    <div className="flex gap-3">
                        <button
                            onClick={handleDecline}
                            className="flex-1 px-4 py-3 text-sm font-medium text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors"
                        >
                            Leave Site
                        </button>
                        <button
                            onClick={handleAccept}
                            disabled={!allChecked}
                            className={`flex-1 px-4 py-3 text-sm font-medium rounded-xl transition-all flex items-center justify-center gap-2
                                ${allChecked
                                    ? 'bg-primary-600 text-white hover:bg-primary-700 shadow-lg shadow-primary-600/30'
                                    : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                                }`}
                        >
                            {allChecked && <CheckCircle2 className="w-4 h-4" />}
                            Enter Site
                        </button>
                    </div>

                    {/* Footer Links */}
                    <div className="mt-6 pt-4 border-t border-gray-100 flex flex-wrap justify-center gap-4 text-xs text-gray-500">
                        <a href="/terms" className="hover:text-primary-600 flex items-center gap-1">
                            Terms of Service <ExternalLink className="w-3 h-3" />
                        </a>
                        <a href="/privacy" className="hover:text-primary-600 flex items-center gap-1">
                            Privacy Policy <ExternalLink className="w-3 h-3" />
                        </a>
                        <a href="/responsible-gambling" className="hover:text-primary-600 flex items-center gap-1">
                            Responsible Gambling <ExternalLink className="w-3 h-3" />
                        </a>
                    </div>
                </div>
            </div>
        </div>
    )
}
