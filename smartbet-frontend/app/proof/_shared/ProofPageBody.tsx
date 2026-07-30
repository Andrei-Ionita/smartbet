import Link from 'next/link'

import type { ProofPayload } from './proofData'

/** Shared page body for both the claim route and the fixture route. */
export function UnpublishedState() {
  return (
    <div className="mx-auto max-w-xl px-4 py-16 text-center">
      <h1 className="text-2xl font-bold text-gray-900">Not published as a claim</h1>
      <p className="mt-3 text-gray-600">
        This prediction has not been published as an immutable BetGlitch claim.
      </p>
      <p className="mt-2 text-sm text-gray-500">
        We only publish proof for picks we have snapshotted and hashed before kickoff.
      </p>
      <Link href="/track-record" className="mt-6 inline-block font-semibold text-blue-700 hover:text-blue-900">
        Review the full public track record →
      </Link>
    </div>
  )
}

const STATUS_LABEL: Record<string, string> = {
  PENDING: 'Pick — pending',
  WON: 'Result — won',
  LOST: 'Result — lost',
  VOID: 'Void — no result',
  CANCELLED: 'Cancelled — no result',
}

export function ProofPageBody(
  { data, imageUrl, shareUrl, downloadName }:
  { data: ProofPayload; imageUrl: string; shareUrl: string; downloadName: string },
) {
  const p = data.pick
  const status = data.result?.status ?? 'PENDING'

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <img
        src={imageUrl}
        alt="BetGlitch published claim"
        width={1200}
        height={630}
        className="w-full rounded-2xl border border-gray-200 shadow-sm"
      />

      <p className="mt-5 text-sm font-semibold text-gray-800">{STATUS_LABEL[status]}</p>
      {status === 'PENDING' && (
        <p className="mt-1 text-sm text-gray-600">
          Published before kickoff. The result will be shown here after settlement—win or lose.
        </p>
      )}

      {/* The full audit trail: every value below is frozen in the claim. */}
      <dl className="mt-6 grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
        <Row label="Fixture" value={`${p.home_team} vs ${p.away_team}`} />
        <Row label="League" value={p.league} />
        <Row label="Kickoff" value={fmt(p.kickoff)} />
        <Row label="Market" value={`${p.market_type} — ${p.predicted_outcome}`} />
        <Row label="Recorded odds" value={p.odds != null ? String(p.odds) : 'n/a'} />
        <Row label="Bookmaker" value={p.bookmaker ?? 'n/a'} />
        <Row label="Odds market" value={p.odds_market ?? 'n/a'} />
        <Row label="Odds captured" value={fmt(p.odds_captured_at)} />
        <Row label="Prediction generated" value={fmt(p.prediction_logged_at)} />
        <Row label="Published" value={fmt(p.published_at)} />
        <Row label="Model score" value={`${p.model_score_percent}% (model score, not a calibrated probability)`} />
        <Row label="Claim ID" value={data.claim_id ?? 'n/a'} />
      </dl>

      <p className="mt-4 break-all font-mono text-[11px] leading-relaxed text-gray-500">
        SHA-256 ({data.claim_hash_version}): {data.claim_hash}
      </p>

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
