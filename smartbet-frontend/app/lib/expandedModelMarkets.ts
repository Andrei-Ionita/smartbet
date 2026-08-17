import { expectedValue, priceMarket, type MarketPrice } from './marketPricing'
import type {
  OddsProvenance,
  OddsUnavailableReason,
  ProductMarket,
  SportMonksOdd,
  TeamContext,
} from './oddsSelection'

export interface ExpandedModelCandidate {
  market_type: ProductMarket
  type_id: number
  name: string
  display_name: string
  predicted_outcome: string
  canonical_outcome: string
  probability: number
  probability_gap: number
  odds: number | null
  expected_value: number | null
  price_status: MarketPrice['status']
  odds_provenance: OddsProvenance | null
  odds_unavailable_reason?: OddsUnavailableReason
  raw_predictions: Record<string, number>
  validation_status: 'shadow'
}

interface OutcomeDefinition {
  source: string
  canonical: string
  label: string
}

interface ExpandedDefinition {
  market: ProductMarket
  typeId: number
  name: string
  displayName: string
  outcomes: OutcomeDefinition[]
}

const DEFINITIONS: ExpandedDefinition[] = [
  {
    market: 'over_under_1.5', typeId: 234, name: 'O/U 1.5', displayName: 'Over/Under 1.5 Goals',
    outcomes: [
      { source: 'yes', canonical: 'over', label: 'Over 1.5' },
      { source: 'no', canonical: 'under', label: 'Under 1.5' },
    ],
  },
  {
    market: 'over_under_3.5', typeId: 236, name: 'O/U 3.5', displayName: 'Over/Under 3.5 Goals',
    outcomes: [
      { source: 'yes', canonical: 'over', label: 'Over 3.5' },
      { source: 'no', canonical: 'under', label: 'Under 3.5' },
    ],
  },
  {
    market: 'half_time_result', typeId: 233, name: 'HT 1X2', displayName: 'Half-time Result',
    outcomes: [
      { source: 'home', canonical: 'home', label: 'Home at half-time' },
      { source: 'draw', canonical: 'draw', label: 'Draw at half-time' },
      { source: 'away', canonical: 'away', label: 'Away at half-time' },
    ],
  },
  {
    market: 'first_team_to_score', typeId: 238, name: 'First goal', displayName: 'First Team to Score',
    outcomes: [
      { source: 'home', canonical: 'home', label: 'Home scores first' },
      { source: 'away', canonical: 'away', label: 'Away scores first' },
      { source: 'draw', canonical: 'none', label: 'No goals' },
    ],
  },
  {
    market: 'half_time_full_time', typeId: 232, name: 'HT/FT', displayName: 'Half-time / Full-time',
    outcomes: [
      { source: 'home_home', canonical: 'home_home', label: 'Home → Home' },
      { source: 'home_draw', canonical: 'home_draw', label: 'Home → Draw' },
      { source: 'home_away', canonical: 'home_away', label: 'Home → Away' },
      { source: 'draw_home', canonical: 'draw_home', label: 'Draw → Home' },
      { source: 'draw_draw', canonical: 'draw_draw', label: 'Draw → Draw' },
      { source: 'draw_away', canonical: 'draw_away', label: 'Draw → Away' },
      { source: 'away_home', canonical: 'away_home', label: 'Away → Home' },
      { source: 'away_draw', canonical: 'away_draw', label: 'Away → Draw' },
      { source: 'away_away', canonical: 'away_away', label: 'Away → Away' },
    ],
  },
]

const probability = (value: unknown): number | null => {
  const parsed = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(parsed) || parsed < 0) return null
  const normalized = parsed > 1 ? parsed / 100 : parsed
  return normalized >= 0 && normalized <= 1 ? normalized : null
}

const candidateFromVector = (
  definition: ExpandedDefinition,
  payload: Record<string, unknown>,
  odds: SportMonksOdd[] | null | undefined,
  ctx: TeamContext,
): ExpandedModelCandidate | null => {
  const vector = definition.outcomes
    .map((outcome) => ({ ...outcome, probability: probability(payload[outcome.source]) }))
    .filter((outcome): outcome is OutcomeDefinition & { probability: number } => outcome.probability !== null)
  if (!vector.length) return null

  const total = vector.reduce((sum, outcome) => sum + outcome.probability, 0)
  if (!(total > 0)) return null
  const normalized = vector.map((outcome) => ({ ...outcome, probability: outcome.probability / total }))
  const ranked = [...normalized].sort((a, b) => b.probability - a.probability)
  const leader = ranked[0]
  const selected = priceMarket(odds, definition.market, leader.canonical, ctx)

  return {
    market_type: definition.market,
    type_id: definition.typeId,
    name: definition.name,
    display_name: definition.displayName,
    predicted_outcome: leader.label,
    canonical_outcome: leader.canonical,
    probability: leader.probability,
    probability_gap: leader.probability - (ranked[1]?.probability ?? 0),
    odds: selected.status === 'verified' ? selected.odds : null,
    expected_value: expectedValue(leader.probability, selected),
    price_status: selected.status,
    odds_provenance: selected.status === 'verified' ? selected.provenance : null,
    odds_unavailable_reason: selected.status === 'unavailable' ? selected.unavailable_reason : undefined,
    raw_predictions: Object.fromEntries(normalized.map((outcome) => [outcome.canonical, outcome.probability])),
    validation_status: 'shadow',
  }
}

const correctScoreCandidate = (
  predictions: any[],
  odds: SportMonksOdd[] | null | undefined,
  ctx: TeamContext,
): ExpandedModelCandidate | null => {
  const prediction = predictions.find((row) => row?.type_id === 240)
  const scores = prediction?.predictions?.scores
  if (!scores || typeof scores !== 'object') return null

  const vector = Object.entries(scores)
    .filter(([score]) => /^\d+-\d+$/.test(score))
    .map(([score, value]) => ({ score, probability: probability(value) }))
    .filter((row): row is { score: string; probability: number } => row.probability !== null)
  if (!vector.length) return null

  const ranked = [...vector].sort((a, b) => b.probability - a.probability)
  const leader = ranked[0]
  const selected = priceMarket(odds, 'correct_score', leader.score, ctx)

  return {
    market_type: 'correct_score',
    type_id: 240,
    name: 'Score',
    display_name: 'Correct Score',
    predicted_outcome: leader.score,
    canonical_outcome: leader.score,
    probability: leader.probability,
    probability_gap: leader.probability - (ranked[1]?.probability ?? 0),
    odds: selected.status === 'verified' ? selected.odds : null,
    expected_value: expectedValue(leader.probability, selected),
    price_status: selected.status,
    odds_provenance: selected.status === 'verified' ? selected.provenance : null,
    odds_unavailable_reason: selected.status === 'unavailable' ? selected.unavailable_reason : undefined,
    raw_predictions: Object.fromEntries(vector.map((row) => [row.score, row.probability])),
    validation_status: 'shadow',
  }
}

/**
 * Markets with direct prediction distributions and exact price mappings that
 * are not yet eligible for public Gems. They are scored on every fixture and
 * retained as shadow candidates until forward validation is sufficient.
 */
export function buildExpandedModelCandidates(
  predictions: unknown,
  odds: SportMonksOdd[] | null | undefined,
  ctx: TeamContext = {},
): ExpandedModelCandidate[] {
  const rows = Array.isArray(predictions) ? predictions : []
  const candidates = DEFINITIONS
    .map((definition) => {
      const prediction = rows.find((row: any) => row?.type_id === definition.typeId)
      return prediction?.predictions && typeof prediction.predictions === 'object'
        ? candidateFromVector(definition, prediction.predictions, odds, ctx)
        : null
    })
    .filter((candidate): candidate is ExpandedModelCandidate => candidate !== null)
  const score = correctScoreCandidate(rows, odds, ctx)
  if (score) candidates.push(score)
  return candidates
}
