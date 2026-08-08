'use client'

import { useState } from 'react'
import { Mail, CheckCircle, Loader2, Sparkles } from 'lucide-react'
import { getSubscriberCaptureContext, storeSubscriberId } from '@/src/lib/marketing'
import { useLanguage } from '../contexts/LanguageContext'

/**
 * All visible newsletter copy, both languages. This component rendered
 * English-only defaults on the Romanian homepage — the same class of defect as
 * the StatusBadge lang-prop trap: a shared component with an English fallback
 * silently breaks the "no mixed-language surfaces" rule on every page that
 * embeds it.
 */
const CAPTURE_COPY = {
    en: {
        eyebrow: 'Public-commitment and verified-record updates',
        heroTitle: 'Follow the public commitments by email',
        heroDescription:
            'A weekly email covering the signals BetGlitch committed and how they settled. Wins and losses both.',
        defaultTitle: 'Get the weekly summary',
        defaultDescription: 'A weekly summary of public commitments and how they settled.',
        cta: 'Subscribe',
        placeholder: 'Enter your email...',
        joining: 'Joining...',
        subscribing: 'Subscribing...',
        successTitle: 'You’re in',
        noSpam: 'No spam. Unsubscribe anytime. We respect your inbox.',
        errorEmpty: 'Please enter your email',
        errorGeneric: 'Something went wrong',
        errorNetwork: 'Could not connect. Please try again.',
        thanks: 'Thank you for subscribing!',
    },
    ro: {
        eyebrow: 'Actualizări despre angajamentele publice și istoricul verificat',
        heroTitle: 'Urmărește angajamentele publice pe email',
        heroDescription:
            'Un email săptămânal despre semnalele angajate de BetGlitch și cum s-au încheiat. Și câștiguri, și pierderi.',
        defaultTitle: 'Primește rezumatul săptămânal',
        defaultDescription: 'Un rezumat săptămânal al angajamentelor publice și al rezultatelor lor.',
        cta: 'Abonează-te',
        placeholder: 'Introdu adresa de email...',
        joining: 'Se trimite...',
        subscribing: 'Se trimite...',
        successTitle: 'Te-ai abonat',
        noSpam: 'Fără spam. Te poți dezabona oricând. Îți respectăm inboxul.',
        errorEmpty: 'Te rugăm să introduci adresa de email',
        errorGeneric: 'Ceva nu a funcționat',
        errorNetwork: 'Conexiunea a eșuat. Încearcă din nou.',
        thanks: 'Mulțumim pentru abonare!',
    },
} as const

interface EmailCaptureProps {
    source?: string
    variant?: 'default' | 'compact' | 'hero'
    interests?: string[]
    leagueInterest?: string
    language?: string
    landingPage?: string
    title?: string
    description?: string
    buttonText?: string
}

export default function EmailCapture({
    source = 'homepage',
    variant = 'default',
    interests = ['weekly_picks'],
    leagueInterest = '',
    language,
    landingPage,
    title,
    description,
    buttonText,
}: EmailCaptureProps) {
    const [email, setEmail] = useState('')
    const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
    const [message, setMessage] = useState('')

    // Display language comes from the app context; the `language` prop stays
    // as the capture-context override some embedders pass for analytics.
    const { language: contextLanguage } = useLanguage()
    const displayLanguage = (language || contextLanguage) === 'ro' ? 'ro' : 'en'
    const words = CAPTURE_COPY[displayLanguage]

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!email.trim()) {
            setStatus('error')
            setMessage(words.errorEmpty)
            return
        }

        setStatus('loading')

        try {
            const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
            const context = getSubscriberCaptureContext({
                landingPage,
                language,
            })
            const response = await fetch(`${apiUrl}/api/subscribe/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    email,
                    source,
                    interests,
                    league_interest: leagueInterest,
                    ...context,
                }),
            })

            const data = await response.json()

            if (data.success) {
                setStatus('success')
                setMessage(data.message || words.thanks)
                setEmail('')
                storeSubscriberId(data.subscriber_id)
            } else {
                setStatus('error')
                setMessage(data.error || words.errorGeneric)
            }
        } catch (error) {
            setStatus('error')
            setMessage(words.errorNetwork)
        }
    }

    // Describes what actually arrives, in the product's own vocabulary. The
    // previous copy promised "our best picks" and implied an unverified crowd
    // ("Join bettors receiving…") — neither is supported by the record.
    const variantTitle = title || (variant === 'hero' ? words.heroTitle : words.defaultTitle)
    const variantDescription = description
        || (variant === 'hero' ? words.heroDescription : words.defaultDescription)
    const ctaLabel = buttonText || words.cta

    if (status === 'success') {
        return (
            <div className={`rounded-2xl p-6 ${variant === 'hero' ? 'bg-gradient-to-r from-green-500 to-emerald-600' : 'bg-green-50 border border-green-200'}`}>
                <div className="flex items-center gap-3">
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center ${variant === 'hero' ? 'bg-white/20' : 'bg-green-100'}`}>
                        <CheckCircle className={`h-6 w-6 ${variant === 'hero' ? 'text-white' : 'text-green-600'}`} />
                    </div>
                    <div>
                        <h3 className={`font-bold ${variant === 'hero' ? 'text-white' : 'text-green-800'}`}>
                            {words.successTitle}
                        </h3>
                        <p className={`text-sm ${variant === 'hero' ? 'text-white/90' : 'text-green-700'}`}>
                            {message}
                        </p>
                    </div>
                </div>
            </div>
        )
    }

    if (variant === 'hero') {
        return (
            <div className="bg-gradient-to-r from-primary-600 to-primary-700 rounded-2xl p-8 text-white">
                <div className="flex items-center gap-2 mb-3">
                    <Sparkles className="h-5 w-5" />
                    {/* Was "Free Weekly Tips" — BetGlitch does not send tips.
                        The email reports which picks were published and how
                        they settled, which is what this now says. */}
                    <span className="text-sm font-medium uppercase tracking-wide opacity-90">
                        {words.eyebrow}
                    </span>
                </div>
                <h3 className="text-2xl font-bold mb-2">
                    {variantTitle}
                </h3>
                <p className="text-white/80 mb-6">
                    {variantDescription}
                </p>

                <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
                    <div className="relative flex-1">
                        <Mail className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                        <input
                            type="email"
                            aria-label="Email address"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder={words.placeholder}
                            className="w-full pl-12 pr-4 py-4 rounded-xl bg-white text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-white/50"
                            disabled={status === 'loading'}
                        />
                    </div>
                    <button
                        type="submit"
                        disabled={status === 'loading'}
                        className="px-8 py-4 bg-white text-primary-600 font-bold rounded-xl hover:bg-gray-100 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                        {status === 'loading' ? (
                            <>
                                <Loader2 className="h-5 w-5 animate-spin" />
                                {words.joining}
                            </>
                        ) : (
                            ctaLabel
                        )}
                    </button>
                </form>

                {status === 'error' && (
                    <p className="mt-3 text-sm text-red-200">{message}</p>
                )}

                <p className="mt-4 text-xs text-white/60">
                    {words.noSpam}
                </p>
            </div>
        )
    }

    if (variant === 'compact') {
        return (
            <div className="bg-gray-50 rounded-xl p-4 border border-gray-200">
                <form onSubmit={handleSubmit} className="flex gap-2">
                    <input
                        type="email"
                            aria-label="Email address"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder={words.placeholder}
                        className="flex-1 px-4 py-2 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent text-sm"
                        disabled={status === 'loading'}
                    />
                    <button
                        type="submit"
                        disabled={status === 'loading'}
                        className="px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50"
                    >
                        {status === 'loading' ? <Loader2 className="h-4 w-4 animate-spin" /> : ctaLabel}
                    </button>
                </form>
                {status === 'error' && (
                    <p className="mt-2 text-xs text-red-600">{message}</p>
                )}
            </div>
        )
    }

    return (
        <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl p-6 border border-gray-200">
            <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-primary-100 rounded-full flex items-center justify-center">
                    <Mail className="h-5 w-5 text-primary-600" />
                </div>
                <div>
                    <h3 className="font-bold text-gray-900">{variantTitle}</h3>
                    <p className="text-sm text-gray-600">{variantDescription}</p>
                </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-3">
                <input
                    type="email"
                            aria-label="Email address"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder={words.placeholder}
                    className="w-full px-4 py-3 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    disabled={status === 'loading'}
                />
                <button
                    type="submit"
                    disabled={status === 'loading'}
                    className="w-full py-3 bg-primary-600 text-white font-medium rounded-xl hover:bg-primary-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                    {status === 'loading' ? (
                        <>
                            <Loader2 className="h-5 w-5 animate-spin" />
                            {words.subscribing}
                        </>
                    ) : (
                        ctaLabel
                    )}
                </button>
            </form>

            {status === 'error' && (
                <p className="mt-3 text-sm text-red-600">{message}</p>
            )}

            <p className="mt-3 text-xs text-gray-500 text-center">
                {words.noSpam}
            </p>
        </div>
    )
}
