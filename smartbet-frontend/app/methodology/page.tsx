import Link from 'next/link'
import type { Metadata } from 'next'

import { RANKING_POLICY, RANKING_VERSION } from '../lib/rankingPolicy'

export const metadata: Metadata = {
  title: 'Ranking methodology',
  description:
    'The exact parameters BetGlitch uses to rank outcomes, and the version stored with every published pick so results stay interpretable as the logic changes.',
}

function Param({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-4 border-b border-gray-100 py-2">
      <dt className="text-sm text-gray-600">{label}</dt>
      <dd className="font-mono text-sm text-gray-900">{value}</dd>
    </div>
  )
}

export default function MethodologyPage() {
  const p = RANKING_POLICY

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-10">
      <div className="mx-auto max-w-3xl">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          Ranking methodology
        </h1>
        <p className="mt-3 text-base leading-relaxed text-gray-700">
          BetGlitch does not train a predictive model. Generation 3 combines a
          specialist provider&apos;s fixture signal, its per-league model report
          card, its dedicated value-bet model and a verified bookmaker price.
          This page states the eligibility rule exactly and names the version
          that produced any given commitment.
        </p>
        <p className="mt-3 text-sm leading-relaxed text-gray-600">
          The purpose is not to make the process look sophisticated. It is to
          make every decision interpretable: what data was available, which
          rule ranked it, what price was recorded, what was missing and what
          the result later showed.
        </p>

        <div className="mt-6 rounded-xl border border-gray-300 bg-white p-5">
          <p className="text-xs uppercase tracking-wide text-gray-500">
            Current ranking version
          </p>
          <p className="mt-1 break-all font-mono text-lg font-bold text-gray-900">
            {RANKING_VERSION}
          </p>
          <p className="mt-2 text-sm leading-relaxed text-gray-700">
            This string is stamped onto every snapshot and every public
            commitment, and it sits inside the commitment&apos;s integrity hash
            — so it cannot be altered after the fact. It is{' '}
            <strong>derived from the parameters below</strong>, not typed by
            hand: change any of them and the version changes with them.
          </p>
          <p className="mt-2 text-xs leading-relaxed text-gray-500">
            Earlier commitments can carry the legacy label{' '}
            <code>consensus_ensemble</code>. That label is preserved rather
            than rewritten. New commitments use the derived version above.
          </p>
        </div>

        {/* The reviewer's actual objection: a record accumulated across silent
            changes to the selection logic is not one record, it is several
            blended together. */}
        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="text-sm font-bold uppercase tracking-wide text-gray-700">
            Why a version exists at all
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-gray-700">
            BetGlitch expects this logic to change — that is the point of
            measuring it in public. But if the rule changed silently, the
            growing record would blend several different systems into one
            average that describes none of them. Stamping the version means any
            future performance figure can be split by the exact rule that
            produced it, and a change of rule can never be hidden inside an
            aggregate.
          </p>
        </div>

        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="text-sm font-bold uppercase tracking-wide text-gray-700">
            Parameters in force
          </h2>
          <dl className="mt-3">
            <Param label="Markets eligible for value selection" value={p.markets.join(', ')} />
            <Param
              label="Confidence floor (leading outcome probability)"
              value={String(p.confidenceFloor)}
            />
            <Param
              label="Minimum gap to next outcome — draw"
              value={String(p.minimumGap.draw)}
            />
            <Param
              label="Minimum gap to next outcome — other"
              value={String(p.minimumGap.other)}
            />
            <Param label="Provider fixture must be predictable" value={p.fixturePredictableRequired ? 'yes' : 'no'} />
            <Param label="Allowed league predictability" value={p.allowedLeaguePredictability.join(', ')} />
            <Param label="Rejected predictive-power trend" value={p.rejectedPredictivePower.join(', ')} />
            <Param label="Active, outcome-aligned provider value bet" value={p.activeAlignedValueBetRequired ? 'required' : 'not required'} />
            <Param label="Correct-score distribution agrees with 1X2" value={p.correctScoreAgreementRequired ? 'required' : 'not required'} />
            <Param label="Leading double-chance leg contains selection" value={p.doubleChanceSupportRequired ? 'required' : 'not required'} />
            <Param label="Minimum canonical-price buffer above fair odd" value={`${p.minimumFairOddsBuffer * 100}%`} />
            <Param label="Minimum bookmakers quoting selection" value={String(p.minimumBookmakers)} />
            <Param label="Maximum relative price spread" value={`${p.maximumRelativePriceSpread * 100}%`} />
            <Param label="Maximum recorded price age" value={`${p.maximumPriceAgeHours} hours`} />
            <Param label="Maximum selections per run" value={String(p.maximumSelections)} />
            <Param label="Gem probability source" value={p.gemProbabilitySource} />
            <Param label="Gem payout source" value={p.gemPayoutSource} />
            <Param label="Gem primary ranking" value={p.gemPrimaryRanking} />
            <Param label="Selection rule" value={p.selection} />
          </dl>
        </div>

        <div className="mt-6 rounded-xl border border-emerald-200 bg-emerald-50 p-5">
          <h2 className="text-sm font-bold uppercase tracking-wide text-emerald-900">
            How qualified Gems are ordered
          </h2>
          <p className="mt-2 text-sm leading-relaxed text-emerald-950">
            Ranking happens only after every eligibility gate above has passed.
            The provider&apos;s baseline price supplies the external implied chance
            (<code>p = 1 / baseline price</code>), while the canonical quote
            supplies the verified payout. The primary balance is{' '}
            <code>(p × verified price − 1) / (verified price − 1)</code>.
          </p>
          <p className="mt-2 text-sm leading-relaxed text-emerald-950">
            This prevents a large price or a large price difference from winning
            the ranking automatically. It is a conservative ordering device,
            not a BetGlitch-calibrated probability, a stake size or betting
            advice. Provider quality, trend, hit ratio and price dispersion are
            deterministic tie-breakers.
          </p>
        </div>

        <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-5">
          <h2 className="text-sm font-bold uppercase tracking-wide text-amber-900">
            What these parameters do not give you
          </h2>
          <ul className="mt-2 space-y-2 text-sm leading-relaxed text-amber-900">
            <li>
              Provider agreement and a quoted edge are <strong>not a guarantee</strong>.
              A value candidate can lose, and a short run can be extremely poor.
            </li>
            <li>
              This exact generation has not yet accumulated enough settled,
              out-of-sample decisions to establish profitability. Its results
              must be judged separately from the earlier score-ranking method. The{' '}
              <Link href="/monitoring" className="font-semibold underline underline-offset-2">
                measured evidence
              </Link>{' '}
              is published and recomputed from live data.
            </li>
            <li>
              Other markets remain in the research evidence feed, but they are
              not promoted into betting selections until a market-specific
              value signal and enough forward evidence exist.
            </li>
            <li>
              The provider&apos;s fair odd and league report card are external model
              outputs, not BetGlitch guarantees. The public results are still
              the final test of whether this filtering works in practice.
            </li>
          </ul>
        </div>

        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="text-sm font-bold uppercase tracking-wide text-gray-700">
            How improvement is judged
          </h2>
          <ol className="mt-3 space-y-2 text-sm leading-relaxed text-gray-700">
            <li><strong>1. Preserve:</strong> freeze decisions under a named version before kickoff.</li>
            <li><strong>2. Measure:</strong> publish eligible wins and losses, score separation and pricing evidence.</li>
            <li><strong>3. Change:</strong> alter a rule only as a new version, never inside an existing record.</li>
            <li><strong>4. Compare:</strong> judge versions separately before claiming that one improved the evidence.</li>
          </ol>
        </div>

        <p className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm font-semibold">
          <Link href="/track-record" className="text-blue-700 underline underline-offset-2">
            Results →
          </Link>
          <Link href="/proof/anchors" className="text-blue-700 underline underline-offset-2">
            External timestamps →
          </Link>
          <Link href="/monitoring" className="text-blue-700 underline underline-offset-2">
            Measured separation →
          </Link>
          <Link href="/calibration" className="text-blue-700 underline underline-offset-2">
            Probability calibration →
          </Link>
        </p>
      </div>
    </div>
  )
}
