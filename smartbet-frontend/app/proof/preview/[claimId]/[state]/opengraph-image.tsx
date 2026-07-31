import { notFound } from 'next/navigation'

import { fetchProofByClaim } from '../../../_shared/proofData'
import { renderProofImage, size } from '../../../_shared/proofCard'
import type { ProofPayload, ResultStatus } from '../../../_shared/proofData'

export const runtime = 'nodejs'
export const alt = 'BetGlitch card VISUAL PREVIEW — not a real settlement'
export const contentType = 'image/png'
export { size }

/**
 * STAFF VISUAL PREVIEW of every card state, for layout review before a real
 * fixture settles.
 *
 * It takes a REAL immutable claim and overlays SYNTHETIC settlement display
 * data. It never creates or modifies a PublishedClaimResult, never touches
 * public performance, and is noindex + not linked from anywhere public. The
 * production settlement lifecycle is still validated naturally.
 */
const SYNTHETIC: Record<string, ProofPayload['result']> = {
  pending: { status: 'PENDING', resolved: false },
  won: {
    status: 'WON', resolved: true, was_correct: true,
    actual_score_home: 2, actual_score_away: 1,
    settled_at: '2026-08-08T19:05:00+00:00',
  },
  lost: {
    status: 'LOST', resolved: true, was_correct: false,
    actual_score_home: 3, actual_score_away: 0,
    settled_at: '2026-08-08T19:05:00+00:00',
  },
  void: {
    status: 'VOID', resolved: false,
    settled_at: '2026-08-08T19:05:00+00:00',
  },
  cancelled: {
    status: 'CANCELLED', resolved: false,
    settled_at: '2026-08-08T19:05:00+00:00',
  },
}

export default async function Image(
  { params }: { params: { claimId: string; state: string } },
) {
  const synthetic = SYNTHETIC[params.state?.toLowerCase()]
  if (!synthetic) notFound()

  const data = await fetchProofByClaim(params.claimId)
  if (!data) notFound()

  // Exact production components; only the settlement display data is synthetic.
  return renderProofImage(
    { ...data, result: synthetic },
    { previewNotice: 'VISUAL PREVIEW — NOT A REAL SETTLEMENT' },
  )
}
