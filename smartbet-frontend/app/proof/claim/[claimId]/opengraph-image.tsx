import { fetchProofByClaim } from '../../_shared/proofData'
import { renderProofImage, size } from '../../_shared/proofCard'

export const runtime = 'nodejs'
export const alt = 'BetGlitch published claim'
export const contentType = 'image/png'
export { size }

export default async function Image({ params }: { params: { claimId: string } }) {
  return renderProofImage(await fetchProofByClaim(params.claimId))
}
