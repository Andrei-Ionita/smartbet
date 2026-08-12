import { NextResponse } from 'next/server'
import { CURRENT_STRATEGY_VERSION } from '@/app/lib/currentStrategyRecord'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

/**
 * Current Gem-strategy performance, derived only from published claims.
 * Explore fixtures are never counted. Earlier ranking versions stay available
 * in the archive but are excluded because they do not measure today's policy.
 * Pending, void and cancelled claims are not wins or losses.
 */

interface ClaimRow {
  claim_state?: string
  counts_towards_verified_record?: boolean
  integrity_ok?: boolean
  market_type?: string
  ranking_version?: string | null
}

export async function GET() {
  const api = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  try {
    const response = await fetch(`${api}/api/proof/claims/?limit=200`, {
      cache: 'no-store',
    })
    if (!response.ok) throw new Error(`claims API ${response.status}`)

    const body = await response.json()
    const claims: ClaimRow[] = Array.isArray(body?.claims) ? body.claims : []

    // Homepage performance describes the strategy visitors can use today.
    // Earlier methodology versions remain in the archive, but mixing them
    // into this number would make old results appear to validate new logic.
    const currentClaims = claims.filter(
      (claim) => claim.ranking_version === CURRENT_STRATEGY_VERSION,
    )
    const settled = currentClaims.filter(
      (c) =>
        c.counts_towards_verified_record === true &&
        (c.claim_state === 'WON' || c.claim_state === 'LOST') &&
        c.integrity_ok !== false,
    )
    const won = settled.filter((c) => c.claim_state === 'WON').length
    const lost = settled.filter((c) => c.claim_state === 'LOST').length
    const voided = currentClaims.filter(
      (c) => c.claim_state === 'VOID' || c.claim_state === 'CANCELLED',
    ).length
    const pending = currentClaims.filter((c) => c.claim_state === 'PENDING').length

    // Win rate over decided commitments only. Void and cancelled resolve to
    // no bet, so including them would understate both directions.
    const decided = won + lost
    const winRate = decided > 0 ? (100 * won) / decided : null

    return NextResponse.json({
      success: true,
      data: {
        overall: {
          // Settled current-strategy Gems are the only universe behind this figure.
          total_predictions: decided,
          won,
          lost,
          void_or_cancelled: voided,
          pending,
          // null, never 0: "no current results yet" and "a 0% win rate" are
          // different statements and must not render identically.
          win_rate: winRate,
          // Deliberately absent: ROI and profit. They need a price that was
          // obtainable at publication, and the record is too young — and too
          // recently freed of stale prices — to support that claim.
        },
      },
      source: 'current_strategy_published_claims',
      ranking_version: CURRENT_STRATEGY_VERSION,
      timestamp: new Date().toISOString(),
    })
  } catch (error) {
    console.error('performance derivation failed:', error)
    // Fail loudly as an error, never as zeros. A zero here is indistinguishable
    // from "we have settled nothing", which is a claim about the record.
    return NextResponse.json(
      {
        success: false,
        error: 'Current-strategy results are temporarily unavailable.',
        data: null,
      },
      { status: 503 },
    )
  }
}
