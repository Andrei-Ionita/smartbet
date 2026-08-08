import Link from 'next/link'
import type { Metadata } from 'next'

import { RANKING_POLICY, RANKING_VERSION } from '../lib/rankingPolicy'

export const metadata: Metadata = {
  title: 'Ranking methodology',
  description:
    'The exact parameters BetGlitch uses to rank outcomes, and the version stamped onto every public commitment so the record stays interpretable as the logic changes.',
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
          BetGlitch does not train a predictive model. It takes probability data
          from a specialist football data provider, applies the parameters
          below, and surfaces one outcome per fixture. This page states those
          parameters exactly, and names the version that produced any given
          commitment.
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
            <Param label="Markets considered" value={p.markets.join(', ')} />
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
            <Param
              label="Minimum market score"
              value={String(p.minimumMarketScore)}
            />
            <Param
              label="Market score weights (gap / EV / confidence)"
              value={`${p.marketScore.weights.gap} / ${p.marketScore.weights.expectedValue} / ${p.marketScore.weights.confidence}`}
            />
            <Param
              label="Market score caps (gap / EV)"
              value={`${p.marketScore.caps.gap} / ${p.marketScore.caps.expectedValue}`}
            />
            <Param
              label="Form momentum applied"
              value={p.formMomentum.enabled ? 'yes' : 'no'}
            />
            <Param
              label="Form recency weights"
              value={p.formMomentum.recencyWeights.join(', ')}
            />
            <Param
              label="Form-adjusted output cap"
              value={String(p.formMomentum.outputCap)}
            />
            <Param label="Selection rule" value={p.selection} />
          </dl>
        </div>

        <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-5">
          <h2 className="text-sm font-bold uppercase tracking-wide text-amber-900">
            What these parameters do not give you
          </h2>
          <ul className="mt-2 space-y-2 text-sm leading-relaxed text-amber-900">
            <li>
              The form step multiplies one outcome&apos;s probability without
              renormalising the rest of the market, then caps the result. The
              output is therefore <strong>not a probability</strong>, which is
              why the signal score is described as a ranking everywhere.
            </li>
            <li>
              None of these thresholds has been shown to identify profitable
              bets. On 304 graded legacy calls the score separated correct from
              incorrect with an AUC of 0.554 — barely better than chance. The{' '}
              <Link href="/monitoring" className="font-semibold underline underline-offset-2">
                measured separation
              </Link>{' '}
              is published and recomputed from live data.
            </li>
            <li>
              A commitment is not a claim that a price is good. It records that
              BetGlitch stated an outcome in advance, under this exact rule.
            </li>
          </ul>
        </div>

        <p className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm font-semibold">
          <Link href="/track-record" className="text-blue-700 underline underline-offset-2">
            Verified record →
          </Link>
          <Link href="/proof/anchors" className="text-blue-700 underline underline-offset-2">
            External timestamps →
          </Link>
          <Link href="/monitoring" className="text-blue-700 underline underline-offset-2">
            Measured separation →
          </Link>
        </p>
      </div>
    </div>
  )
}
