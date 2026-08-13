import Link from 'next/link'
import type { Metadata } from 'next'

export const dynamic = 'force-dynamic'

export const metadata: Metadata = {
  title: 'Verification details | BetGlitch',
  description:
    'Technical verification details for BetGlitch published picks, including integrity hashes and independent OpenTimestamps proofs.',
  alternates: { canonical: '/proof/anchors' },
}

interface Anchor {
  digest: string
  manifest_version: string
  claim_count: number
  calendars: string[]
  status: 'PENDING' | 'CONFIRMED'
  bitcoin_block_height: number | null
  created_at: string | null
  confirmed_at: string | null
  proof_url: string
  detail_url: string
}

async function getAnchors(): Promise<{ anchors: Anchor[]; error: boolean }> {
  const api = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  try {
    const res = await fetch(`${api}/api/proof/anchors/?limit=100`, {
      cache: 'no-store',
    })
    if (!res.ok) return { anchors: [], error: true }
    const data = await res.json()
    return { anchors: Array.isArray(data.anchors) ? data.anchors : [], error: false }
  } catch {
    return { anchors: [], error: true }
  }
}

const fmt = (iso: string | null) =>
  iso
    ? new Date(iso).toLocaleString('en-GB', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZone: 'UTC',
      }) + ' UTC'
    : '—'

export default async function AnchorsPage() {
  const { anchors, error } = await getAnchors()
  const api = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
  const confirmed = anchors.filter((a) => a.status === 'CONFIRMED').length

  return (
    <div className="min-h-screen bg-gray-50 px-4 py-10">
      <div className="mx-auto max-w-4xl">
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">
          Verification details
        </h1>
        <p className="mt-3 text-base leading-relaxed text-gray-700">
          BetGlitch hashes every published pick. On its own that only proves
          the record has not been edited — we compute the hash, we serve the
          record, so nothing stops us replacing both. This page closes that
          gap by handing the timestamp to parties who are not us.
        </p>

        {/* Say what is proven and what is not. This page exists because a
            reviewer correctly refused to accept a self-hosted hash as proof;
            it would be self-defeating to overstate what replaced it. */}
        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="text-sm font-bold uppercase tracking-wide text-gray-700">
            What this proves
          </h2>
          <ul className="mt-3 space-y-2 text-sm leading-relaxed text-gray-700">
            <li>
              <strong>Existence before a point in time.</strong> Each digest is
              submitted to independent OpenTimestamps calendars, which
              aggregate it into a Bitcoin transaction. Once confirmed, the
              proof shows the digest existed before that block — a fact
              BetGlitch cannot backdate, rewrite or withdraw.
            </li>
            <li>
              <strong>Taken before kickoff.</strong> Anchoring runs immediately
              after publication, while the fixtures are still hours away. A
              timestamp taken after the matches were played would prove nothing
              about foresight.
            </li>
            <li>
              <strong>Not our word for it.</strong> The digest is computed only
              from data the public claims API already serves, so you can
              rebuild it yourself and check it against the proof with the
              standard <code className="rounded bg-gray-100 px-1">ots</code>{' '}
              tool. No BetGlitch cooperation required.
            </li>
          </ul>
          <p className="mt-3 text-sm leading-relaxed text-gray-600">
            What it does <strong>not</strong> prove: that a published pick was a
            good bet. Timestamping fixes <em>when</em> we said something, never
            whether we were right. That is what the{' '}
            <Link href="/track-record" className="font-semibold text-blue-700 underline underline-offset-2">
              results page
            </Link>{' '}
            is for.
          </p>
        </div>

        <div className="mt-6 rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="text-sm font-bold uppercase tracking-wide text-gray-700">
            Verify it yourself
          </h2>
          <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-relaxed text-gray-700">
            <li>
              Fetch the claims:{' '}
              <code className="break-all rounded bg-gray-100 px-1">
                {api}/api/proof/claims/?limit=200
              </code>
            </li>
            <li>
              Build one line per claim as{' '}
              <code className="rounded bg-gray-100 px-1">
                &lt;claim_id&gt;:&lt;claim_hash&gt;
              </code>
              , sort the lines, prefix the manifest version line, and end with
              a newline. The anchor detail endpoint serves the exact manifest
              so you can diff against it.
            </li>
            <li>
              SHA-256 that text. It must equal the digest below.
            </li>
            <li>
              Download the proof and run{' '}
              <code className="rounded bg-gray-100 px-1">
                ots verify --digest &lt;digest&gt; proof.ots
              </code>
            </li>
          </ol>
        </div>

        <div className="mt-8 flex flex-wrap items-baseline gap-x-6 gap-y-1 text-sm text-gray-600">
          <span>
            <strong className="text-gray-900">{anchors.length}</strong> timestamps
          </span>
          <span>
            <strong className="text-gray-900">{confirmed}</strong> confirmed in Bitcoin
          </span>
          <span>
            <strong className="text-gray-900">
              {anchors.reduce((n, a) => n + (a.claim_count || 0), 0)}
            </strong>{' '}
            commitments covered
          </span>
        </div>

        {error ? (
          <p className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
            The timestamp log could not be loaded right now. The anchors
            themselves are unaffected — they live in public calendars and the
            Bitcoin chain, not only here.
          </p>
        ) : anchors.length === 0 ? (
          <p className="mt-6 rounded-xl border border-gray-200 bg-white p-4 text-sm text-gray-700">
            No commitments have been anchored yet. This page fills in on the
            next publication cycle.
          </p>
        ) : (
          <div className="mt-6 space-y-3">
            {anchors.map((anchor) => (
              <div
                key={anchor.digest}
                className="rounded-xl border border-gray-200 bg-white p-4"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${
                      anchor.status === 'CONFIRMED'
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-gray-100 text-gray-700'
                    }`}
                  >
                    {anchor.status === 'CONFIRMED'
                      ? `Bitcoin block ${anchor.bitcoin_block_height}`
                      : 'Submitted — awaiting Bitcoin block'}
                  </span>
                  <span className="text-xs text-gray-500">
                    {anchor.claim_count} commitment
                    {anchor.claim_count === 1 ? '' : 's'} · anchored{' '}
                    {fmt(anchor.created_at)}
                  </span>
                </div>

                <p className="mt-2 break-all font-mono text-[11px] leading-relaxed text-gray-600">
                  {anchor.digest}
                </p>

                <div className="mt-2 flex flex-wrap gap-4 text-xs font-semibold">
                  <a
                    href={`${api}${anchor.proof_url}`}
                    className="text-blue-700 hover:text-blue-900"
                  >
                    Download .ots proof
                  </a>
                  <a
                    href={`${api}${anchor.detail_url}`}
                    className="text-blue-700 hover:text-blue-900"
                  >
                    View manifest
                  </a>
                </div>

                {anchor.status === 'PENDING' && (
                  <p className="mt-2 text-xs leading-relaxed text-gray-500">
                    Calendars batch submissions before committing them to
                    Bitcoin, so a fresh timestamp stays pending for a few
                    hours. The digest is already recorded with the calendar
                    operators.
                  </p>
                )}
              </div>
            ))}
          </div>
        )}

        <p className="mt-8 text-sm text-gray-600">
          <Link href="/track-record" className="font-semibold text-blue-700 underline underline-offset-2">
            ← Back to the results
          </Link>
        </p>
      </div>
    </div>
  )
}
