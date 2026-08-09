import Link from 'next/link'

import TrackOnMount from '../../components/TrackOnMount'

import type { ProofPayload } from './proofData'
import {
  formatBookmaker, formatModelScore, formatOdds, formatSelection, formatUtc,
} from './format'

/** Shared page body for both the claim route and the fixture route. */
export function UnpublishedState() {
  return (
    <div className="mx-auto max-w-xl px-4 py-16 text-center">
      <h1 className="text-2xl font-bold text-gray-900">Not a public commitment</h1>
      <p className="mt-3 text-gray-600">
        This signal has not been committed to the public record as an immutable BetGlitch claim.
      </p>
      <p className="mt-2 text-sm text-gray-500">
        We only publish proof for signals we have snapshotted and hashed before kickoff.
      </p>
      <Link href="/track-record" className="mt-6 inline-block font-semibold text-blue-700 hover:text-blue-900">
        Review the full public track record →
      </Link>
    </div>
  )
}

// Must match the canonical states in app/components/StatusBadge.tsx. The page
// previously said "Pick — pending", which is a fourth spelling of a state the
// rest of the product now calls COMMITMENT — PENDING.
const STATUS_LABEL: Record<string, string> = {
  PENDING: 'COMMITMENT — PENDING',
  WON: 'RESULT — WON',
  LOST: 'RESULT — LOST',
  VOID: 'VOID',
  CANCELLED: 'CANCELLED',
}

export function ProofPageBody(
  { data, imageUrl, shareUrl, downloadName }:
  { data: ProofPayload; imageUrl: string; shareUrl: string; downloadName: string },
) {
  const p = data.pick
  const status = data.result?.status ?? 'PENDING'

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <TrackOnMount event="published_proof_opened" surface="proof" />
      <img
        src={imageUrl}
        alt="BetGlitch public commitment"
        width={1200}
        height={630}
        className="w-full rounded-2xl border border-gray-200 shadow-sm"
      />

      <h1 className="mt-6 text-2xl font-bold leading-tight text-gray-900">
        {p.home_team} vs {p.away_team}
      </h1>

      <p className="mt-3 text-sm font-semibold text-gray-800">{STATUS_LABEL[status]}</p>
      {/* What this page IS: an accountability artifact, not an endorsement.
          "BetGlitch recommended this bet" is exactly the reading to prevent. */}
      <p className="mt-1 text-sm text-gray-600">
        This signal was committed to the public record before kickoff. Its
        selection, recorded price and publication timestamp are preserved so
        the eventual result can be evaluated without hindsight. A public
        commitment is not a claim of proven betting value.
      </p>
      {status === 'PENDING' ? (
        <p className="mt-1 text-sm text-gray-600">
          Awaiting settlement — not yet counted as a verified result.
        </p>
      ) : (
        <p className="mt-1 text-sm text-gray-600">
          This commitment has settled and is included in the verified record
          when eligible.
        </p>
      )}

      {/* The full audit trail: every value below is frozen in the claim. */}
      <dl className="mt-6 grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
        <Row label="Fixture" value={`${p.home_team} vs ${p.away_team}`} />
        <Row label="League" value={p.league} />
        <Row label="Kickoff" value={formatUtc(p.kickoff)} />
        <Row label="Market" value={formatSelection(p.market_type, p.predicted_outcome, { long: true })} />
        <Row label="Recorded odds" value={formatOdds(p.odds)} />
        <Row label="Bookmaker" value={formatBookmaker(p.bookmaker) ?? 'n/a'} />
        <Row label="Odds market" value={p.odds_market ?? 'n/a'} />
        <Row label="Odds captured" value={formatUtc(p.odds_captured_at)} />
        {/* How stale the price was at the moment we committed to it. A price
            captured days earlier proves where the number came from, but not
            that a bettor could still get it — so the age is stated outright
            rather than left as arithmetic for the reader. */}
        {typeof p.price_age_hours_at_publication === 'number' && (
          <Row
            label="Price age when committed"
            value={
              p.price_age_hours_at_publication < 1
                ? `${Math.round(p.price_age_hours_at_publication * 60)} minutes`
                : `${p.price_age_hours_at_publication.toFixed(1)} hours`
            }
          />
        )}
        <Row label="Prediction generated" value={formatUtc(p.prediction_logged_at)} />
        <Row label="Claim published" value={formatUtc(p.published_at)} />
        <Row label="Signal score at commitment" value={formatModelScore(p.model_score_percent)} />
        {/* Which rule produced this. Without it a record spanning changes
            to the ranking logic is several systems averaged together. */}
        {p.ranking_version && (
          <Row label="Ranking version" value={p.ranking_version} />
        )}
        <Row label="Claim ID" value={data.claim_id ?? 'n/a'} />
      </dl>

      {/* The frozen score, explained. This page is a server-rendered shareable
          artifact with no language context, so both languages are stated. */}
      <p className="mt-3 text-xs leading-relaxed text-gray-600">
        This is the signal score recorded when the commitment was published. It
        is a relative ranking, not a calibrated probability.
      </p>
      <p className="mt-1 text-xs leading-relaxed text-gray-500">
        Acesta este scorul de semnal înregistrat la publicarea angajamentului.
        Este o clasare relativă, nu o probabilitate calibrată.
      </p>

      <p className="mt-4 break-all font-mono text-[11px] leading-relaxed text-gray-500">
        SHA-256 ({data.claim_hash_version}): {data.claim_hash}
      </p>

      {/* What the hash does and does not prove.
          A skeptical reviewer (2026-08-08) pointed out that a self-hosted hash
          over self-hosted content is not independent proof: BetGlitch could in
          principle replace the content and recompute the hash. Correct — so
          the digest is now timestamped by parties who are not us, and this
          block reports the ACTUAL anchor state rather than asserting one. */}
      <div className="mt-4 rounded-lg border border-gray-200 bg-gray-50 p-3">
        <p className="text-xs font-semibold text-gray-800">
          What this hash proves
        </p>
        <p className="mt-1 text-xs leading-relaxed text-gray-600">
          It fixes the exact content of this commitment: change any recorded
          field and the hash stops matching, so silent edits are detectable.
          On its own it does <strong>not</strong> prove to a third party
          <em> when</em> the record existed — BetGlitch serves both the record
          and the hash.
        </p>

        {data.anchor ? (
          <>
            <p className="mt-2 text-xs leading-relaxed text-gray-600">
              {data.anchor.status === 'CONFIRMED' ? (
                <>
                  This commitment&apos;s digest is anchored in the Bitcoin
                  chain at block{' '}
                  <strong>{data.anchor.bitcoin_block_height}</strong>, via
                  independent OpenTimestamps calendars. That timestamp cannot
                  be backdated or withdrawn by BetGlitch.
                </>
              ) : (
                <>
                  This commitment&apos;s digest has been submitted to
                  independent OpenTimestamps calendars and is awaiting its
                  Bitcoin block — calendars batch submissions, so confirmation
                  takes a few hours. The operators already hold the digest.
                </>
              )}
            </p>
            {!data.anchor.matches_current_hash && (
              /* Loud on purpose. If this ever renders, the claim differs from
                 what was timestamped, and the anchored value is the evidence. */
              <p className="mt-2 rounded border border-red-300 bg-red-50 p-2 text-xs font-semibold text-red-900">
                This claim no longer matches the hash that was timestamped
                ({data.anchor.claim_hash_at_anchor}). Trust the anchored value,
                not this page.
              </p>
            )}
            <p className="mt-2 break-all font-mono text-[10px] leading-relaxed text-gray-500">
              Anchor digest: {data.anchor.digest}
            </p>
          </>
        ) : (
          <p className="mt-2 text-xs leading-relaxed text-gray-600">
            This commitment has not been externally timestamped yet. Anchoring
            runs on the next publication cycle, before kickoff.
          </p>
        )}

        <a
          href="/proof/anchors"
          className="mt-2 inline-block text-xs font-semibold text-blue-700 hover:text-blue-900"
        >
          How to verify this yourself →
        </a>
        {data.integrity?.canonical_payload && (
          <details className="mt-3 border-t border-gray-200 pt-3">
            <summary className="cursor-pointer text-xs font-semibold text-gray-700">
              Recompute the claim hash
            </summary>
            <p className="mt-2 text-xs leading-relaxed text-gray-600">
              Serialize the exact payload below as UTF-8 JSON with sorted keys
              and compact separators, then calculate SHA-256. The result must
              equal the claim hash shown above.
            </p>
            <pre className="mt-2 max-h-72 overflow-auto rounded bg-gray-950 p-3 text-[10px] leading-relaxed text-gray-100">
              {JSON.stringify(data.integrity.canonical_payload, null, 2)}
            </pre>
          </details>
        )}
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <a
          href={imageUrl}
          download={downloadName}
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
        >
          Download PNG
        </a>
        <Link href="/track-record" className="text-sm font-semibold text-blue-700 hover:text-blue-900">
          See full track record →
        </Link>
      </div>
      <p className="mt-6 break-all text-xs text-gray-500">Share link: {shareUrl}</p>
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col border-b border-gray-100 py-1.5">
      <dt className="text-xs uppercase tracking-wide text-gray-500">{label}</dt>
      <dd className="text-gray-900">{value}</dd>
    </div>
  )
}

function fmt(iso: string | null | undefined) {
  if (!iso) return 'n/a'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return String(iso)
  return d.toISOString().slice(0, 16).replace('T', ' ') + ' UTC'
}
