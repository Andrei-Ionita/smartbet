export interface ProofPayload {
  found: boolean
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
    return data.found ? data : null
  } catch {
    return null
  }
}

// Humanised "3h 28m before kickoff"; returns null if logged at/after kickoff.
export function beforeKickoffLabel(loggedAtIso: string, kickoffIso: string): string | null {
  const deltaMs = new Date(kickoffIso).getTime() - new Date(loggedAtIso).getTime()
  if (deltaMs <= 0) return null
  const mins = Math.floor(deltaMs / 60000)
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return h > 0 ? `${h}h ${m}m before kickoff` : `${m}m before kickoff`
}
