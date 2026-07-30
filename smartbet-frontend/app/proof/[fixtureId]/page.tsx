import type { Metadata } from 'next'

import { ProofPageBody, UnpublishedState } from '../_shared/ProofPageBody'
import { fetchProof } from '../_shared/proofData'

const APP_URL = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'

/**
 * Compatibility path: /proof/<fixtureId> resolves the fixture's current
 * (non-superseded) claim. The STABLE public identity is
 * /proof/claim/<claim_uuid> — a fixture may eventually carry several claims for
 * different markets.
 */
export async function generateMetadata(
  { params }: { params: { fixtureId: string } },
): Promise<Metadata> {
  const data = await fetchProof(params.fixtureId)
  if (!data) return { title: 'Not published as a claim · BetGlitch' }

  const p = data.pick
  const outcome = p.predicted_outcome.toUpperCase()
  const status = data.result?.status ?? 'PENDING'
  const title = status === 'PENDING'
    ? `${p.home_team} vs ${p.away_team} — ${outcome} · published before kickoff`
    : `${p.home_team} vs ${p.away_team} — ${outcome} · settled ${status.toLowerCase()}`
  const description =
    'Published before kickoff and frozen with a SHA-256 integrity hash. '
    + 'The result is shown after settlement — win or lose.'

  // Canonicalise onto the stable claim URL when we know it.
  const canonical = data.claim_id
    ? `${APP_URL}/proof/claim/${data.claim_id}`
    : `${APP_URL}/proof/${params.fixtureId}`

  return {
    title,
    description,
    alternates: { canonical },
    openGraph: { title, description, type: 'website', url: canonical },
    twitter: { card: 'summary_large_image', title, description },
  }
}

export default async function ProofPage({ params }: { params: { fixtureId: string } }) {
  const data = await fetchProof(params.fixtureId)
  if (!data) return <UnpublishedState />

  return (
    <ProofPageBody
      data={data}
      imageUrl={`${APP_URL}/proof/${params.fixtureId}/opengraph-image`}
      shareUrl={
        data.claim_id
          ? `${APP_URL}/proof/claim/${data.claim_id}`
          : `${APP_URL}/proof/${params.fixtureId}`
      }
      downloadName={`betglitch-proof-${params.fixtureId}.png`}
    />
  )
}
