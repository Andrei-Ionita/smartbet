export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";

export interface Team {
  name: string;
}

export interface Match {
  home_team: Team;
  away_team: Team;
  league: string;
  kickoff_time: string; // ISO string format
}

export interface OddsSnapshot {
  odds_home: number;
  odds_draw: number;
  odds_away: number;
  bookmaker?: string;
}

export interface Score {
  predicted_outcome: string; // e.g., "HOME_WIN", "DRAW", "AWAY_WIN"
  expected_value: number; // Decimal, e.g., 0.072 for 7.2%
  confidence_level: ConfidenceLevel;
  odds_snapshot: OddsSnapshot;
}

export interface Prediction {
  id: string;
  match: Match;
  score: Score;
  explanation?: string; // Real explanation from backend model
}

// Legacy interface for backward compatibility during transition
export interface MatchDetails {
  teams: string; // e.g., "Team A vs Team B"
  league: string;
  kickoffTime: string; // ISO string format
} 