import { Metadata } from 'next'
import Link from 'next/link'
import { Shield, Target, BarChart3, Users, Zap, TrendingUp } from 'lucide-react'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'

export const metadata: Metadata = {
  title: 'About BetGlitch — AI-Powered Football Predictions',
  description: 'Learn about BetGlitch, our mission, methodology, and commitment to transparent AI-powered football predictions across 27 European leagues.',
  openGraph: {
    title: 'About BetGlitch — AI-Powered Football Predictions',
    description: 'Our mission, methodology, and commitment to transparent AI-powered football predictions.',
    url: 'https://betglitch.com/about',
  },
}

export default function AboutPage() {
  const organizationSchema = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "BetGlitch",
    "url": "https://betglitch.com",
    "logo": "https://betglitch.com/images/logo-final-v6.png",
    "description": "AI-powered football predictions and betting insights for 27 European leagues.",
    "sameAs": [],
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50">
      <BreadcrumbSchema items={[
        { name: 'Home', url: 'https://betglitch.com' },
        { name: 'About', url: 'https://betglitch.com/about' },
      ]} />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationSchema) }}
      />
      <div className="max-w-4xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-4">About BetGlitch</h1>
          <p className="text-xl text-gray-600 max-w-2xl mx-auto leading-relaxed">
            We build AI systems that analyze football matches across 27 European leagues,
            providing data-driven predictions with full transparency.
          </p>
        </div>

        {/* Mission */}
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-200 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Our Mission</h2>
          <p className="text-gray-700 leading-relaxed mb-4">
            BetGlitch was built on a simple premise: sports prediction should be transparent, data-driven,
            and accountable. Too many prediction services hide their losing bets and inflate their track records.
            We do the opposite.
          </p>
          <p className="text-gray-700 leading-relaxed">
            Every prediction we make is timestamped before kickoff, published publicly, and verified against
            real results from third-party data sources. Our{' '}
            <Link href="/track-record" className="text-primary-600 hover:underline font-medium">
              track record page
            </Link>{' '}
            shows every call we have ever made — the wins and the losses.
          </p>
        </div>

        {/* Methodology */}
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-200 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Our Methodology</h2>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="text-center p-4">
              <div className="bg-blue-100 w-14 h-14 rounded-xl flex items-center justify-center mx-auto mb-4">
                <BarChart3 className="h-7 w-7 text-blue-600" />
              </div>
              <h3 className="font-bold text-gray-900 mb-2">3-Model Ensemble</h3>
              <p className="text-sm text-gray-600">
                Random Forest, XGBoost, and Neural Network models work together to produce consensus predictions
                with calibrated confidence scores.
              </p>
            </div>
            <div className="text-center p-4">
              <div className="bg-green-100 w-14 h-14 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Zap className="h-7 w-7 text-green-600" />
              </div>
              <h3 className="font-bold text-gray-900 mb-2">Real-Time Data</h3>
              <p className="text-sm text-gray-600">
                We process live data from premium sports data providers, refreshing predictions every 60 seconds
                as new information becomes available.
              </p>
            </div>
            <div className="text-center p-4">
              <div className="bg-purple-100 w-14 h-14 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Target className="h-7 w-7 text-purple-600" />
              </div>
              <h3 className="font-bold text-gray-900 mb-2">Value Detection</h3>
              <p className="text-sm text-gray-600">
                Our expected value analysis compares our probability estimates with bookmaker odds to identify
                genuine value opportunities.
              </p>
            </div>
          </div>
        </div>

        {/* Transparency */}
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-200 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Transparency First</h2>
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <Shield className="h-5 w-5 text-green-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-gray-900">Every prediction is public</h3>
                <p className="text-sm text-gray-600">No cherry-picking. Our track record includes every prediction, win or loss.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Shield className="h-5 w-5 text-green-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-gray-900">Timestamped before kickoff</h3>
                <p className="text-sm text-gray-600">Predictions are logged with timestamps before matches begin — no retroactive editing.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Shield className="h-5 w-5 text-green-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-gray-900">Third-party verified results</h3>
                <p className="text-sm text-gray-600">Match outcomes are verified against independent data sources, not self-reported.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Coverage */}
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-200 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">League Coverage</h2>
          <p className="text-gray-700 leading-relaxed mb-4">
            BetGlitch covers 27 European football leagues, including the Premier League, La Liga, Bundesliga,
            Serie A, Ligue 1, Eredivisie, and many more. Our models are trained on historical data
            specific to each league, accounting for differences in playing style, competitiveness, and home advantage.
          </p>
          <div className="flex items-center gap-6 text-sm text-gray-500 mt-6">
            <span className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-primary-600" />
              <strong className="text-gray-900">27</strong> leagues covered
            </span>
            <span className="flex items-center gap-2">
              <Users className="h-4 w-4 text-primary-600" />
              <strong className="text-gray-900">3</strong> AI models
            </span>
            <span className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-primary-600" />
              <strong className="text-gray-900">60s</strong> refresh rate
            </span>
          </div>
        </div>

        {/* Responsible Gambling */}
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Responsible Gambling</h2>
          <p className="text-gray-700 leading-relaxed mb-4">
            BetGlitch is not a betting operator. We provide data analysis for informational purposes.
            If you choose to bet, please do so responsibly through licensed operators. Never bet more
            than you can afford to lose.
          </p>
          <Link
            href="/responsible-gambling"
            className="inline-flex items-center gap-2 text-primary-600 hover:text-primary-700 font-medium"
          >
            <Shield className="h-4 w-4" />
            View our responsible gambling resources
          </Link>
        </div>

        {/* CTA */}
        <div className="text-center py-8">
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/explore"
              className="inline-flex items-center justify-center gap-2 bg-primary-600 text-white px-8 py-3 rounded-xl font-medium hover:bg-primary-700 transition-colors"
            >
              Explore Predictions
            </Link>
            <Link
              href="/track-record"
              className="inline-flex items-center justify-center gap-2 bg-white text-gray-700 px-8 py-3 rounded-xl font-medium border border-gray-200 hover:bg-gray-50 transition-colors"
            >
              View Track Record
            </Link>
            <Link
              href="/blog"
              className="inline-flex items-center justify-center gap-2 bg-white text-gray-700 px-8 py-3 rounded-xl font-medium border border-gray-200 hover:bg-gray-50 transition-colors"
            >
              Read Our Blog
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
