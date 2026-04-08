'use client'

import Link from 'next/link'
import { ArrowRight, CheckCircle2, Shield, Sparkles, Target, Trophy } from 'lucide-react'
import EmailCapture from '../components/EmailCapture'
import MarketingEventTracker from '../components/MarketingEventTracker'

const features = [
  'Free weekly shortlist with our strongest model edges',
  'Public track record with verified outcomes and timestamped predictions',
  'Bankroll-focused commentary instead of hype-driven tipster messaging',
]

const premiumRoadmap = [
  'Daily premium shortlist with deeper rationale and filtering',
  'Priority alerts when new high-conviction spots appear',
  'Model notes, stake sizing context, and league-specific watchlists',
]

export default function PricingContent() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-emerald-50">
      <MarketingEventTracker
        eventName="pricing_viewed"
        source="pricing_page"
        metadata={{ tier: 'marketing_waitlist' }}
      />

      <div className="mx-auto max-w-5xl px-4 py-12">
        <div className="rounded-3xl border border-slate-200 bg-white/90 p-8 shadow-xl shadow-slate-200/40">
          <div className="grid gap-10 lg:grid-cols-[1.2fr_0.8fr]">
            <div>
              <div className="mb-4 inline-flex items-center gap-2 rounded-full bg-blue-100 px-4 py-2 text-sm font-semibold text-blue-700">
                <Sparkles className="h-4 w-4" />
                Early-access pricing funnel
              </div>
              <h1 className="max-w-2xl text-4xl font-bold tracking-tight text-slate-900 md:text-5xl">
                Start free, follow the proof, and join the premium tier when it is ready.
              </h1>
              <p className="mt-4 max-w-2xl text-lg leading-8 text-slate-600">
                The current funnel is intentionally simple: free picks build trust through transparent results, then the most engaged subscribers get first access to the paid tier.
              </p>

              <div className="mt-8 grid gap-4 md:grid-cols-3">
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                  <Shield className="h-6 w-6 text-blue-600" />
                  <h2 className="mt-3 font-semibold text-slate-900">Transparency first</h2>
                  <p className="mt-2 text-sm text-slate-600">Every serious marketing touchpoint points back to the public track record.</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                  <Target className="h-6 w-6 text-emerald-600" />
                  <h2 className="mt-3 font-semibold text-slate-900">Free tier habit</h2>
                  <p className="mt-2 text-sm text-slate-600">Subscribers get recurring proof-led picks before they ever see a paid upgrade.</p>
                </div>
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                  <Trophy className="h-6 w-6 text-amber-500" />
                  <h2 className="mt-3 font-semibold text-slate-900">Premium waitlist</h2>
                  <p className="mt-2 text-sm text-slate-600">The paid tier is staged carefully so the product proves itself before monetization ramps.</p>
                </div>
              </div>

              <div className="mt-8 grid gap-6 md:grid-cols-2">
                <section className="rounded-2xl border border-blue-100 bg-blue-50 p-6">
                  <h2 className="text-lg font-bold text-slate-900">What you get for free</h2>
                  <ul className="mt-4 space-y-3 text-sm text-slate-700">
                    {features.map((feature) => (
                      <li key={feature} className="flex items-start gap-2">
                        <CheckCircle2 className="mt-0.5 h-4 w-4 text-blue-600" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </section>

                <section className="rounded-2xl border border-emerald-100 bg-emerald-50 p-6">
                  <h2 className="text-lg font-bold text-slate-900">What premium is being built toward</h2>
                  <ul className="mt-4 space-y-3 text-sm text-slate-700">
                    {premiumRoadmap.map((feature) => (
                      <li key={feature} className="flex items-start gap-2">
                        <CheckCircle2 className="mt-0.5 h-4 w-4 text-emerald-600" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              </div>

              <div className="mt-8 flex flex-wrap gap-4 text-sm">
                <Link href="/track-record" className="inline-flex items-center gap-2 font-semibold text-blue-700 hover:text-blue-900">
                  Review the public track record
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link href="/explore" className="inline-flex items-center gap-2 font-semibold text-slate-700 hover:text-slate-900">
                  Explore live predictions
                  <ArrowRight className="h-4 w-4" />
                </Link>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-200 bg-slate-950 p-6 text-white shadow-lg">
              <p className="text-sm font-semibold uppercase tracking-[0.2em] text-emerald-300">Join the funnel</p>
              <h2 className="mt-3 text-2xl font-bold">Get the free picks now and reserve premium access.</h2>
              <p className="mt-3 text-sm leading-6 text-slate-300">
                The email list is the priority channel. Join it once and we will handle the welcome sequence, weekly picks, and premium launch updates automatically.
              </p>
              <div className="mt-6">
                <EmailCapture
                  source="pricing_page"
                  variant="default"
                  interests={['weekly_picks', 'premium_launch']}
                  title="Reserve your spot"
                  description="Free picks now. Premium early-access updates later."
                  buttonText="Join the list"
                />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
