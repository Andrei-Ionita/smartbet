import type { Metadata } from 'next'

import { ProofPageBody, UnpublishedState } from '../../_shared/ProofPageBody'
import { fetchProofByClaim } from '../../_shared/proofData'

const APP_URL = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'

/**
 * The STABLE public proof identity: /proof/claim/<claim_uuid>.
 *
 * A fixture may eventually carry several claims (different markets), so the
 * claim UUID — not the fixture id — is canonical. Reads only frozen claim
 * fields from the immutable snapshot.
 */
export async function generateMetadata(
  { params }: { params: { claimId: string } },
): Promise<Metadata> {
  const data = await fetchProofByClaim(params.claimId)
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

  // Next derives its own og:image query hash from the opengraph-image MODULE
  // CONTENTS, so it does NOT change when settlement changes the data — a
  // crawler would keep serving the PENDING image forever. Override it with a
  // STATE-derived URL so PENDING and every settled state have distinct cache
  // identities. Previously cached URLs stay valid; the page simply stops
  // referencing them.
  const version = data.card_cache_version ?? 'v0'
  const imageUrl = `${APP_URL}/proof/claim/${params.claimId}/opengraph-image?state=${version}`
  const images = [{ url: imageUrl, width: 1200, height: 630, alt: 'BetGlitch published claim' }]

  return {
    title,
    description,
    openGraph: {
      title, description, type: 'website',
      url: `${APP_URL}/proof/claim/${params.claimId}`,
      images,
    },
    twitter: { card: 'summary_large_image', title, description, images },
  }
}

export default async function ClaimProofPage({ params }: { params: { claimId: string } }) {
  const data = await fetchProofByClaim(params.claimId)
  if (!data) return <UnpublishedState />

  return (
    <ProofPageBody
      data={data}
      imageUrl={`${APP_URL}/proof/claim/${params.claimId}/opengraph-image`}
      shareUrl={`${APP_URL}/proof/claim/${params.claimId}`}
      downloadName={`betglitch-claim-${params.claimId}.png`}
    />
  )
}
