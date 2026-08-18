/**
 * Canonical price fields. Every surface that renders a price-derived number must
 * read `price_status` — not the shape or magnitude of `odds`. A number that
 * merely looks plausible does not prove it prices the intended market, which is
 * exactly how a second-half quote reached the homepage on 2026-07-29.
 */
import type { CanonicalPriceFields } from '@/app/lib/marketPricing'

export type { CanonicalPriceFields }

export interface ModelShortlistItem {
  fixture_id: number
  home_team: string
  away_team: string
  league: string
  kickoff: string
  leading_selection: string
  signal_strength: number
  signal_gap: number
  verified_price: number
  bookmaker: string | null
  bookmakers_checked: number
  price_age_hours: number | null
  supporting_models: number
  gem_gap_categories: string[]
  why_shortlisted: string[]
  why_not_gem: string[]
}

export interface Recommendation extends CanonicalPriceFields {
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
  bookmaker?: string
  gem?: {
    rank: number | null
    provider_implied_chance: number | null
    provider_baseline_price: number | null
    verified_price_advantage: number | null
    league_predictability: string | null
    league_hit_ratio: number | null
    predictive_power: string | null
    bookmakers_checked: number | null
    relative_price_spread: number | null
    price_age_hours: number | null
    correct_score_agrees: boolean
    double_chance_supports: boolean
    selection_basis: string
  } | null
  stake_recommendation?: {
    recommended_stake: number
    stake_percentage: number
    currency: string
    strategy: string
    risk_level: string
    risk_explanation: string
    warnings: string[]
  }
  probabilities?: {
    home: number
    draw: number
    away: number
  }
  odds_data?: {
    home: number | null
    draw: number | null
    away: number | null
    bookmaker: string
    home_bookmaker?: string | null
    draw_bookmaker?: string | null
    away_bookmaker?: string | null
  }
  ensemble_info?: {
    model_count: number
    consensus: number
    variance: number
    strategy: string
  }
  prediction_info?: {
    source: string
    confidence_level: string
    reliability_score: number
    data_quality: string
    confidence_interval?: {
      point_estimate: number
      lower_bound: number
      upper_bound: number
      interval_width: number
      interpretation: string
    }
  }
  debug_info?: {
    total_predictions?: number
    valid_predictions?: number
    strategy?: string
    consensus?: string
    variance?: string | number
    model_count?: number
    confidence_score?: number
    prediction_agreement?: string
    model_consensus?: {
      home: number
      draw: number
      away: number
      variance: number
    }
  }
  league_accuracy?: {
    accuracy_percent: number
    total_predictions: number
    correct_predictions: number
  } | null
  signal_quality?: 'Strong' | 'Good' | 'Moderate' | 'Weak'
  market_indicators?: {
    market_favorite: string
    market_implied_prob: string
    bookmaker_margin: string
    volume_estimate: string
    ai_vs_market: string
    value_opportunity: string
    odds_efficiency: string
  }

  // Two-Track Betting System
  bet_type?: 'safe' | 'value' | 'speculative'
  bet_label?: string
  recommendation_color?: string

  // Multi-Market Support (V3)
  best_market?: CanonicalPriceFields & {
    type: '1x2' | 'btts' | 'over_under_2.5' | 'double_chance'
    name: string  // Short name like "1X2", "BTTS", "O/U 2.5"
    display_name?: string  // Full name like "Match Result"
    predicted_outcome: string
    probability: number
    probability_gap: number
    odds: number | null
    expected_value: number | null
    market_score: number
    bookmaker?: string
  }
  all_markets?: Array<CanonicalPriceFields & {
    type: '1x2' | 'btts' | 'over_under_2.5' | 'double_chance'
    name: string
    predicted_outcome: string
    probability: number
    odds: number | null
    expected_value: number | null
    market_score: number
    bookmaker?: string
    is_recommended?: boolean  // True if passes EV/gap filters
  }>

  // New Enhanced Data Features
  teams_data?: {
    home: {
      id: number
      name: string
      logo_path?: string
      form?: string // "W,L,W,D,W"
      position?: number // League position
      points?: number
      matches_played?: number
      goals_scored?: number
      goals_conceded?: number
      injuries?: Array<{
        player_name: string
        reason: string
        type: 'Missing' | 'Questionable'
      }>
    }
    away: {
      id: number
      name: string
      logo_path?: string
      form?: string
      position?: number
      points?: number
      matches_played?: number
      goals_scored?: number
      goals_conceded?: number
      injuries?: Array<{
        player_name: string
        reason: string
        type: 'Missing' | 'Questionable'
      }>
    }
  }

  h2h_data?: {
    total_played: number
    home_wins: number
    away_wins: number
    draws: number
    last_5_results: Array<'Home' | 'Away' | 'Draw'>
    summary_text?: string // "Home won 3 of last 5 meetings"
  }

  lineups_data?: {
    status: 'Confirmed' | 'Predicted' | 'Unavailable'
    home_formation?: string
    away_formation?: string
    key_players_missing?: boolean
  }
}
