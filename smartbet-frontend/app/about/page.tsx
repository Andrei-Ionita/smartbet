import { Metadata } from 'next'
import Link from 'next/link'
import { Shield, Target, BarChart3, Users, Zap, TrendingUp } from 'lucide-react'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'

export const metadata: Metadata = {
  title: 'About BetGlitch — how a signal becomes a public result',
  description:
    'How BetGlitch works: live model signals across 27 European leagues, selected picks frozen before kickoff with their recorded odds, and a verified record built only from settled published picks.',
  openGraph: {
    title: 'About BetGlitch — how a signal becomes a public result',
    description:
      'Live model signals, picks frozen before kickoff with their recorded odds, and a verified record built only from settled published picks.',
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
    "description": "Football model signals for 27 European leagues, with selected picks frozen before kickoff and kept public after settlement.",
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
            BetGlitch generates far more model output than it publishes. When a
            pick <em>is</em> published, it is frozen before kickoff with its
            selection, model score, recorded odds and bookmaker, and it stays
            public afterwards whether it wins or loses. Our{' '}
            <Link href="/track-record" className="text-primary-600 hover:underline font-medium">
              verified record
            </Link>{' '}
            contains every published pick that has settled — never a filtered
            subset of them.
          </p>
        </div>

        {/* How a signal becomes a public result. The old page implied every
            prediction entered the record; it does not, and saying so plainly is
            more defensible than the stronger claim. */}
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-200 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            How a signal becomes a public result
          </h2>
          <ol className="space-y-4">
            {[
              {
                title: 'Live model signal',
                body: 'Every model run is written to an append-only snapshot. Signals are mutable in the sense that a newer snapshot can supersede them — but no snapshot is ever edited or deleted.',
              },
              {
                title: 'Published pick (optional)',
                body: 'BetGlitch selects some snapshots to publish. Publication freezes the market, selection, model score, recorded odds, bookmaker and timestamps. Most snapshots are never published.',
              },
              {
                title: 'Settlement (automatic)',
                body: 'After full-time, a published pick is graded against the fields frozen at publication — not against anything that could have changed since. Results are inserted, never overwritten.',
              },
              {
                title: 'Verified record',
                body: 'Settled, integrity-valid published picks form the only universe behind any public accuracy, ROI or win/loss figure.',
              },
            ].map((step, i) => (
              <li key={step.title} className="flex gap-4">
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gray-900 text-xs font-bold text-white">
                  {i + 1}
                </span>
                <div>
                  <h3 className="font-semibold text-gray-900">{step.title}</h3>
                  <p className="text-sm leading-relaxed text-gray-600">{step.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>

        {/* Four numbers people routinely conflate. */}
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-200 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            What the numbers mean
          </h2>
          <dl className="space-y-4">
            {[
              {
                term: 'Model score',
                def: 'A provider-derived confidence ranking. It is not a calibrated probability and should not be read as a percentage chance.',
              },
              {
                term: 'Implied probability',
                def: 'What a bookmaker’s price implies, before their margin. Derived from odds, not from our model.',
              },
              {
                term: 'Expected value',
                def: 'An estimate comparing a model score against a recorded price. An estimate is not a forecast of profit.',
              },
              {
                term: 'Realized ROI',
                def: 'Actual profit or loss across settled published picks, at the exact odds recorded at publication.',
              },
              {
                term: 'Verified result',
                def: 'The settled outcome of a published pick, graded on its frozen fields.',
              },
            ].map(({ term, def }) => (
              <div key={term}>
                <dt className="font-semibold text-gray-900">{term}</dt>
                <dd className="text-sm leading-relaxed text-gray-600">{def}</dd>
              </div>
            ))}
          </dl>
        </div>

        {/* Methodology */}
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-200 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Our Methodology</h2>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="text-center p-4">
              <div className="bg-blue-100 w-14 h-14 rounded-xl flex items-center justify-center mx-auto mb-4">
                <BarChart3 className="h-7 w-7 text-blue-600" />
              </div>
              <h3 className="font-bold text-gray-900 mb-2">Signal ranking</h3>
              <p className="text-sm text-gray-600">
                Provider probabilities are ranked against recorded prices, and a signal is surfaced only when
                it clears our filters. The score is a relative ranking, not a calibrated probability, and the
                selection logic keeps changing as we learn.
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
                Expected-value analysis compares a model score against the recorded bookmaker price. It is an
                estimate of value, not a forecast of profit.
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
                <h3 className="font-semibold text-gray-900">Published picks stay published</h3>
                <p className="text-sm text-gray-600">A published pick is never withdrawn, re-priced or re-graded. Losses stay up next to the wins, at equal prominence.</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Shield className="h-5 w-5 text-green-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-gray-900">Frozen before kickoff</h3>
                <p className="text-sm text-gray-600">Publication records the selection, odds, bookmaker and time before the match starts, and settlement grades that frozen copy.</p>
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
          {/* flex-wrap: without it these three stats forced the page to 410px
              wide at a 320px viewport, so the whole of /about scrolled
              sideways on the narrowest phones. */}
          <div className="flex flex-wrap items-center gap-x-6 gap-y-3 text-sm text-gray-500 mt-6">
            <span className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-primary-600" />
              <strong className="text-gray-900">27</strong> leagues covered
            </span>
            <span className="flex items-center gap-2">
              <Users className="h-4 w-4 text-primary-600" />
              <strong className="text-gray-900">1</strong> data provider
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
