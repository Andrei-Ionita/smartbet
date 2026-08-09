import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const runtime = 'nodejs'

/**
 * Verified performance, derived from the CLAIMS AUTHORITY.
 *
 * This route used to shell out — `exec('python .../get_performance_stats.py')`
 * — from the Next.js container. That container is a node:18-alpine image
 * built from smartbet-frontend alone: it has no Python, no Django project and
 * no database. The call therefore failed on every request, in production,
 * since the day it was deployed.
 *
 * The failure was silent and consequential. Four surfaces read this endpoint,
 * and each treats "no data" as zero — so on 2026-08-09, with six commitments
 * settled (two won, four lost), the homepage still announced "Building the
 * verified record from zero". The product was hiding its own first results.
 *
 * It now reads /api/proof/claims/, which is the documented sole public source
 * for published claims. Never the prediction feed, and never a fallback to it:
 * that distinction is the entire point of the verified record.
 *
 * Only SETTLED, integrity-valid claims count. Pending is not a result, and
 * void/cancelled are excluded from win-rate — the same rule the track-record
 * page states publicly.
 */

interface ClaimRow {
  claim_state?: string
  counts_towards_verified_record?: boolean
  integrity_ok?: boolean
  market_type?: string
}

const TERMINAL = new Set(['WON', 'LOST', 'VOID', 'CANCELLED'])

export async function GET() {
  const api = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  try {
    const response = await fetch(`${api}/api/proof/claims/?limit=200`, {
      cache: 'no-store',
    })
    if (!response.ok) throw new Error(`claims API ${response.status}`)

    const body = await response.json()
    const claims: ClaimRow[] = Array.isArray(body?.claims) ? body.claims : []

    const settled = claims.filter(
      (c) => TERMINAL.has(c.claim_state || '') && c.integrity_ok !== false,
    )
    const won = settled.filter((c) => c.claim_state === 'WON').length
    const lost = settled.filter((c) => c.claim_state === 'LOST').length
    const voided = settled.filter(
      (c) => c.claim_state === 'VOID' || c.claim_state === 'CANCELLED',
    ).length
    const pending = claims.filter((c) => c.claim_state === 'PENDING').length

    // Win rate over decided commitments only. Void and cancelled resolve to
    // no bet, so including them would understate both directions.
    const decided = won + lost
    const winRate = decided > 0 ? (100 * won) / decided : null

    return NextResponse.json({
      success: true,
      data: {
        overall: {
          // Settled commitments — the only universe behind any public figure.
          total_predictions: decided,
          won,
          lost,
          void_or_cancelled: voided,
          pending,
          // null, never 0: "no verified results yet" and "a 0% win rate" are
          // different statements and must not render identically.
          win_rate: winRate,
          // Deliberately absent: ROI and profit. They need a price that was
          // obtainable at publication, and the record is too young — and too
          // recently freed of stale prices — to support that claim.
        },
      },
      source: 'published_claims',
      timestamp: new Date().toISOString(),
    })
  } catch (error) {
    console.error('performance derivation failed:', error)
    // Fail loudly as an error, never as zeros. A zero here is indistinguishable
    // from "we have settled nothing", which is a claim about the record.
    return NextResponse.json(
      {
        success: false,
        error: 'Verified performance is temporarily unavailable.',
        data: null,
      },
      { status: 503 },
    )
  }
}
