export interface Recommendation {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  predicted_outcome: 'Home' | 'Draw' | 'Away'
  confidence: number
  odds: number | null
  ev: number | null
  score: number
  explanation: string
  probabilities: {
    home: number
    draw: number
    away: number
  }
}

export interface RecommendationsResponse {
  recommendations: Recommendation[]
  total: number
  lastUpdated: string
}
