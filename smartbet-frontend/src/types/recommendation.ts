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
  odds_data?: {
    home: number | null
    draw: number | null
    away: number | null
    bookmaker: string
  }
  ensemble_info?: {
    model_count: number
    consensus: number
    variance: number
    strategy: string
  }
  debug_info?: {
    total_predictions: number
    valid_predictions: number
    strategy: string
    consensus: number
    variance: number
    model_count: number
  }
  league_accuracy?: {
    accuracy_percent: number
    total_predictions: number
    correct_predictions: number
  } | null
}
