import Link from 'next/link'
import type { Metadata } from 'next'
import { fetchProof } from './proofData'

const APP_URL = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'

export async function generateMetadata(
  { params }: { params: { fixtureId: string } }
): Promise<Metadata> {
  const data = await fetchProof(params.fixtureId)
  if (!data) {
    return { title: 'Proof not found · BetGlitch' }
  }
  const p = data.pick
  const outcome = p.predicted_outcome.toUpperCase()
  const title = data.result.resolved
    ? `${p.home_team} vs ${p.away_team} — ${outcome} · verified result`
    : `${p.home_team} vs ${p.away_team} — ${outcome} · logged before kickoff`
  const description = `Every pick timestamped before kickoff, every result verified. Season ${data.record.wins}W–${data.record.losses}L · ${data.record.roi_percent >= 0 ? '+' : ''}${data.record.roi_percent}% ROI. We post our losses too.`
  // Next auto-adds og:image from opengraph-image.tsx; we set the rest.
  return {
    title,
    description,
    openGraph: { title, description, type: 'website', url: `${APP_URL}/proof/${params.fixtureId}` },
    twitter: { card: 'summary_large_image', title, description },
  }
}

export default async function ProofPage({ params }: { params: { fixtureId: string } }) {
  const data = await fetchProof(params.fixtureId)
  const imageUrl = `${APP_URL}/proof/${params.fixtureId}/opengraph-image`
  const shareUrl = `${APP_URL}/proof/${params.fixtureId}`

  if (!data) {
    return (
      <div className="mx-auto max-w-xl px-4 py-16 text-center">
        <h1 className="text-2xl font-bold text-gray-900">Proof not found</h1>
        <p className="mt-3 text-gray-600">This pick isn't in our published, recommended track record.</p>
        <Link href="/track-record" className="mt-6 inline-block font-semibold text-blue-700 hover:text-blue-900">
          Review the full public track record →
        </Link>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <img
        src={imageUrl}
        alt="BetGlitch verified proof card"
        width={1200}
        height={630}
        className="w-full rounded-2xl border border-gray-200 shadow-sm"
      />
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <a
          href={imageUrl}
          download={`betglitch-proof-${params.fixtureId}.png`}
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
        >
          Download PNG
        </a>
        <Link href="/track-record" className="text-sm font-semibold text-blue-700 hover:text-blue-900">
          See full track record →
        </Link>
      </div>
      <p className="mt-6 text-xs text-gray-500 break-all">Share link: {shareUrl}</p>
    </div>
  )
}
