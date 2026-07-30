import { fetchProof } from '../_shared/proofData'
import { renderProofImage, size } from '../_shared/proofCard'

export const runtime = 'nodejs'
export const alt = 'BetGlitch published claim'
export const contentType = 'image/png'
export { size }

// Compatibility path: resolves the fixture's current (non-superseded) claim.
// The stable identity is /proof/claim/<claim_uuid>.
export default async function Image({ params }: { params: { fixtureId: string } }) {
  return renderProofImage(await fetchProof(params.fixtureId))
}
