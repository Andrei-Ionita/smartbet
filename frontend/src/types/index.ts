// Define the types for our betting suggestions
export interface BettingSuggestion {
  id: number;
  homeTeam: string;
  awayTeam: string;
  kickoff: string;
  league: string;
  recommendedBet: string;
  confidenceLevel: 'HIGH' | 'MEDIUM' | 'LOW';
  odds: {
    home: number;
    draw: number;
    away: number;
  };
  homeTeamScore: number;
  awayTeamScore: number;
  source: string;
} 