import { Metadata } from 'next'
import Link from 'next/link'
import { Shield, Target, BarChart3, Users, Zap, TrendingUp } from 'lucide-react'
import BreadcrumbSchema from '@/components/BreadcrumbSchema'
import {
  COVERAGE_HORIZON_DAYS,
  SEARCHABLE_COMPETITION_COUNT,
  SIGNAL_COMPETITION_COUNT,
  SUPPORTED_MARKET_COUNT,
} from '../lib/coverage'

export const metadata: Metadata = {
  title: 'About BetGlitch — how a signal becomes a public result',
  description:
    `A public football-signal lab. BetGlitch adds verified prices and available fixture context to provider data, versions its ranking rules, and keeps every eligible result visible.`,
  openGraph: {
    title: 'About BetGlitch — how a signal becomes a public result',
    description:
      'Every signal explained, every public commitment verifiable and every eligible result visible.',
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
    "description": `A public football-signal lab with verified prices, available fixture context, versioned ranking rules and a permanent result record.`,
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
            Every signal explained. Every commitment verifiable. Every eligible
            result visible — win or lose.
          </p>
        </div>

        {/* Why BetGlitch exists — the philosophy, stated before any mechanism. */}
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-200 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Why BetGlitch exists</h2>
          <p className="text-gray-700 leading-relaxed mb-4">
            Sports betting is full of confidence claims. We wanted something different:
            a system where decisions could be checked. Betting platforms usually show
            certainty — BetGlitch shows evidence. Too many prediction services hide
            their losing bets and inflate their track records. We do the opposite.
          </p>
          <p className="text-gray-700 leading-relaxed">
            BetGlitch generates far more live signals than it commits. When a
            signal <em>is</em> committed, it is frozen before kickoff with its
            selection, signal score, recorded odds and bookmaker, and it stays
            public afterwards whether it wins or loses. Our{' '}
            <Link href="/track-record" className="text-primary-600 hover:underline font-medium">
              verified record
            </Link>{' '}
            contains every eligible public commitment that has settled — never a filtered
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
                title: 'Provider data',
                body: 'A specialist football data provider supplies the probability vectors. BetGlitch does not train a predictive model of its own and does not claim to.',
              },
              {
                title: 'Filtering and ranking → live signal',
                body: 'BetGlitch filters and ranks those provider probabilities against recorded prices, producing a signal score. Every run is written to an append-only snapshot: a newer snapshot can supersede a signal, but no snapshot is ever edited or deleted.',
              },
              {
                title: 'Public commitment (automatic gate)',
                body: 'A fixed rule commits eligible snapshots before kickoff. Publication freezes the market, selection, signal score, recorded odds, bookmaker, methodology version and timestamps. Most snapshots are never committed.',
              },
              {
                title: 'Settlement (automatic)',
                body: 'After full-time, a public commitment is graded against the fields frozen at publication — not against anything that could have changed since. Results are inserted, never overwritten.',
              },
              {
                title: 'Verified record',
                body: 'Eligible settled public commitments form the only universe behind any public accuracy, ROI or win/loss figure.',
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
                term: 'Signal score',
                def: 'A relative ranking of BetGlitch’s preference among the available outcomes in one market, out of 100. It is not a calibrated probability and does not state the chance of an outcome occurring.',
              },
              {
                term: 'Implied probability',
                def: 'What a bookmaker’s price implies, before their margin. Derived from odds, not from BetGlitch.',
              },
              {
                term: 'Value status',
                def: 'Whether BetGlitch can assess the price at all. Without a verified market price, value cannot be assessed; with one, it is not yet assessed, because BetGlitch has no validated calibration to judge a price against. BetGlitch publishes no numeric expected value.',
              },
              {
                term: 'Realized ROI',
                def: 'Actual profit or loss across eligible settled public commitments, at the exact odds recorded at publication.',
              },
              {
                term: 'Verified result',
                def: 'The settled outcome of a public commitment, graded on its frozen fields.',
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
              <h3 className="font-bold text-gray-900 mb-2">Filtering and ranking</h3>
              <p className="text-sm text-gray-600">
                Provider probabilities are ranked against recorded prices, and a signal is surfaced only when
                it clears our filters. The score is a relative ranking, not a calibrated probability, and the
                selection logic changes only under a new public methodology version.
              </p>
            </div>
            <div className="text-center p-4">
              <div className="bg-green-100 w-14 h-14 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Zap className="h-7 w-7 text-green-600" />
              </div>
              <h3 className="font-bold text-gray-900 mb-2">One data provider</h3>
              <p className="text-sm text-gray-600">
                Probability data comes from a single specialist football data provider. There is no
                second model, no averaging of opinions and no model trained by BetGlitch — a signal
                is that provider&apos;s numbers put through our filters.
              </p>
            </div>
            <div className="text-center p-4">
              <div className="bg-purple-100 w-14 h-14 rounded-xl flex items-center justify-center mx-auto mb-4">
                <Target className="h-7 w-7 text-purple-600" />
              </div>
              <h3 className="font-bold text-gray-900 mb-2">Still being evaluated</h3>
              <p className="text-sm text-gray-600">
                BetGlitch has not demonstrated predictive or pricing edge, and does not publish
                calibrated probabilities, fair odds or bet/no-bet decisions. Whether the filtering
                adds value is what the public record is being built to test.
              </p>
            </div>
          </div>
        </div>

        {/* Said plainly, once, in its own block — a caveat buried in a
            methodology card is easy to miss. */}
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-200 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">What BetGlitch does not claim</h2>
          <ul className="space-y-2 text-gray-700">
            {[
              'BetGlitch does not build, train or own a predictive model. The probabilities come from a third-party provider.',
              'BetGlitch does not publish calibrated probabilities. The signal score is a relative ranking out of 100.',
              'BetGlitch has not demonstrated predictive or pricing edge. Both are still being evaluated in public.',
              'BetGlitch does not publish fair odds, minimum acceptable odds or bet/no-bet decisions.',
              'BetGlitch is not a bookmaker, does not accept bets, and does not size stakes for you.',
              'No output guarantees profit. You can lose all the money you wager.',
            ].map((claim) => (
              <li key={claim} className="flex gap-3">
                <span aria-hidden className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-gray-400" />
                <span className="text-sm leading-relaxed">{claim}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* The manifesto — the same authored text the homepage carries, plus
            the line that closes the philosophy. Confident, not defensive: the
            product can afford to expose uncertainty precisely because it does. */}
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-200 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            Evidence before confidence. Results before claims. Improvement by version.
          </h2>
          <div className="space-y-4 text-gray-700 leading-relaxed">
            <p>
              We publish the decisions we commit to before kickoff. We preserve the
              selection, price, methodology version, timestamp and proof. We keep every eligible result
              visible, including the losses.
            </p>
            <p>
              We continuously test signals, strategies and fixture context to
              understand what genuinely improves decision quality. Weak results and
              missing context are evidence too, so we publish them.
            </p>
            <p>
              We do not promise an edge or that every version will improve. We
              promise to name the rule, preserve the decision, publish the result
              and let the record decide what deserves to change.
            </p>
            <p className="font-semibold text-gray-900">
              We would rather show uncertainty honestly than manufacture confidence.
            </p>
          </div>
        </div>

        {/* Transparency */}
        <div className="bg-white rounded-2xl p-8 shadow-sm border border-gray-200 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Transparency First</h2>
          <div className="space-y-4">
            <div className="flex items-start gap-3">
              <Shield className="h-5 w-5 text-green-600 flex-shrink-0 mt-1" />
              <div>
                <h3 className="font-semibold text-gray-900">Public commitments stay public</h3>
                <p className="text-sm text-gray-600">A commitment is never withdrawn, re-priced or re-graded. Losses stay up next to the wins, at equal prominence.</p>
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
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Coverage</h2>
          <p className="text-gray-700 leading-relaxed mb-4">
            Two different numbers, because they measure two different things.{' '}
            <strong className="text-gray-900">{SEARCHABLE_COMPETITION_COUNT} competitions</strong> are indexed and
            searchable, including the Premier League, La Liga, Bundesliga, Serie A, Ligue 1, Eredivisie, domestic
            cups and the UEFA club tournaments. Of those,{' '}
            <strong className="text-gray-900">{SIGNAL_COMPETITION_COUNT}</strong> are swept for live signals — the
            UEFA tournaments are indexed but do not currently produce signals, so a fixture can be searchable
            without ever being ranked.
          </p>
          {/* flex-wrap: without it these three stats forced the page to 410px
              wide at a 320px viewport, so the whole of /about scrolled
              sideways on the narrowest phones. */}
          <div className="flex flex-wrap items-center gap-x-6 gap-y-3 text-sm text-gray-500 mt-6">
            <span className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-primary-600" />
              <strong className="text-gray-900">{SEARCHABLE_COMPETITION_COUNT}</strong> indexed competitions
            </span>
            <span className="flex items-center gap-2">
              <Target className="h-4 w-4 text-primary-600" />
              <strong className="text-gray-900">{SIGNAL_COMPETITION_COUNT}</strong> swept for signals
            </span>
            <span className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-primary-600" />
              <strong className="text-gray-900">{SUPPORTED_MARKET_COUNT}</strong> supported markets
            </span>
            <span className="flex items-center gap-2">
              <Users className="h-4 w-4 text-primary-600" />
              <strong className="text-gray-900">1</strong> data provider
            </span>
            <span className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-primary-600" />
              <strong className="text-gray-900">{COVERAGE_HORIZON_DAYS} days</strong> of fixture coverage
            </span>
          </div>
        </div>

        {/* Responsible Gambling */}
        <div className="bg-amber-50 border border-amber-200 rounded-2xl p-8 mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Responsible Gambling</h2>
          <p className="text-gray-700 leading-relaxed mb-4">
            BetGlitch is not a bookmaker and does not accept bets. Our outputs are informational
            signals, not advice, and no output guarantees profit. If you choose to bet, do so
            responsibly through licensed operators — you can lose all the money you wager, so never
            bet more than you can afford to lose.
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
              Explore signals
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
