/**
 * Proof data access. A card may ONLY ever render an immutable PublishedClaim.
 *
 * The stable public identity is the claim UUID (`/proof/claim/<uuid>`): a
 * fixture may eventually carry several claims for different markets. The
 * fixture route remains as a compatibility path and resolves to that fixture's
 * current (non-superseded) claim.
 */
export type ResultStatus = 'PENDING' | 'WON' | 'LOST' | 'VOID' | 'CANCELLED'

export interface ProofPayload {
  found: boolean
  /** True only for an immutable PublishedClaim snapshot. */
  published: boolean
  state: 'published' | 'unpublished'
  claim_id?: string | null
  claim_hash?: string | null
  claim_hash_version?: string | null
  /** False when the stored hash no longer matches the stored fields. */
  integrity_ok?: boolean
  /** Versions the OG image URL so each rendered state has its own cache identity. */
  card_cache_version?: string
  integrity_error?: string | null
  superseded?: boolean
  /**
   * External timestamp covering this claim, or null when it has not been
   * anchored yet. Null is a real state the page must show, never hidden: a
   * self-hosted hash alone is tamper-evidence, not third-party proof.
   */
  anchor?: {
    digest: string
    status: 'PENDING' | 'CONFIRMED'
    bitcoin_block_height: number | null
    anchored_at: string | null
    confirmed_at: string | null
    calendars: string[]
    claim_hash_at_anchor: string
    /** False means the claim changed after it was timestamped. */
    matches_current_hash: boolean
    proof_url: string
    detail_url: string
  } | null
  pick: {
    home_team: string
    away_team: string
    league: string
    market_type: string
    predicted_outcome: string
    odds: number | null
    /** Provider-derived model score, NOT a calibrated probability. */
    model_score_percent: number
    confidence: number
    bookmaker: string | null
    odds_market: string | null
    odds_line: number | null
    odds_captured_at: string | null
    /**
     * Hours between capturing the price and committing to it. Published
     * because a reviewer had to subtract two timestamps to discover a
     * committed price was six days old.
     */
    price_age_hours_at_publication?: number | null
    /** The ranking policy version that produced this selection. */
    ranking_version?: string | null
    kickoff: string
    prediction_logged_at: string
    published_at: string
  }
  result: {
    status: ResultStatus
    resolved: boolean
    actual_score_home?: number | null
    actual_score_away?: number | null
    was_correct?: boolean
    settled_at?: string
  }
  record: {
    wins: number
    losses: number
    roi_percent: number
    total_bets: number
    verified_record_only: boolean
  }
  note?: string
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function get(path: string): Promise<ProofPayload | null> {
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      // Revalidate hourly: a pending claim becomes a result after full-time.
      next: { revalidate: 3600 },
    })
    if (!res.ok) return null
    const data = (await res.json()) as ProofPayload
    // A fixture without an immutable published claim is NOT proof, and a claim
    // that fails its integrity check must never render as valid.
    // See docs/audit/gem-selector-diagnostics-2026-07-29.md (finding F7).
    if (!data.found || !data.published) return null
    if (data.integrity_ok === false) return null
    return data
  } catch {
    return null
  }
}

/** By stable claim UUID — the canonical public identity. */
export function fetchProofByClaim(claimId: string) {
  return get(`/api/proof/claim/${claimId}/`)
}

/** By fixture id — compatibility path; resolves the fixture's current claim. */
export function fetchProof(fixtureId: string) {
  return get(`/api/proof/${fixtureId}/`)
}

// Humanised "3h 28m before kickoff" (near-term) or "14d 16h before kickoff"
// (≥48h out); returns null if logged at/after kickoff.
export function beforeKickoffLabel(loggedAtIso: string, kickoffIso: string): string | null {
  const deltaMs = new Date(kickoffIso).getTime() - new Date(loggedAtIso).getTime()
  if (deltaMs <= 0) return null
  const mins = Math.floor(deltaMs / 60000)
  const totalHours = Math.floor(mins / 60)
  // Roll up to days for far-out picks — "352h 56m" reads slower than "14d 16h".
  if (totalHours >= 48) {
    const d = Math.floor(totalHours / 24)
    const h = totalHours % 24
    return `${d}d ${h}h before kickoff`
  }
  const m = mins % 60
  return totalHours > 0 ? `${totalHours}h ${m}m before kickoff` : `${m}m before kickoff`
}
