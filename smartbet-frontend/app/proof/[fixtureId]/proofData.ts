export interface ProofPayload {
  found: boolean
  /** True only for an immutable PublishedClaim snapshot. */
  published: boolean
  state: 'published' | 'unpublished'
  claim_id?: string | null
  claim_hash?: string | null
  pick: {
    home_team: string
    away_team: string
    league: string
    market_type: string
    predicted_outcome: string
    odds: number | null
    confidence: number
    kickoff: string
    prediction_logged_at: string
  }
  result:
    | { resolved: false }
    | { resolved: true; actual_score_home: number | null; actual_score_away: number | null; was_correct: boolean }
  record: { wins: number; losses: number; roi_percent: number }
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function fetchProof(fixtureId: string): Promise<ProofPayload | null> {
  try {
    const res = await fetch(`${API_BASE}/api/proof/${fixtureId}/`, {
      // Revalidate hourly: a pending pick becomes a result after full-time.
      next: { revalidate: 3600 },
    })
    if (!res.ok) return null
    const data = (await res.json()) as ProofPayload
    // A fixture without an immutable published claim is NOT proof. Returning
    // null here is what stops the page and the OG card from ever rendering
    // mutable prediction values under "logged before kickoff" language.
    // See docs/audit/gem-selector-diagnostics-2026-07-29.md (finding F7).
    return data.found && data.published ? data : null
  } catch {
    return null
  }
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
